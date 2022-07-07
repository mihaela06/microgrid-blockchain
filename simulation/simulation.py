import asyncio
import calendar
import datetime
import json
import os
import random
from threading import currentThread
import time
from enum import Enum

import numpy as np
import pandas as pd
import requests
from matplotlib import pyplot as plt

State = Enum("State", "Pending InProgress Paused Canceled Finished")


SURPLUS = 1
SHORTAGE = -1
IN_BOUNDS = 0
BACKGROUND_FOLDER = "scenario/background"
BASELINE_FOLDER = "scenario/baseline"

ids = ["1", "2", "6"]
FREQ = 10
RANDOM_SEED = 42

random.seed(RANDOM_SEED)

task_file = {}
background_df = None
df = None
time_counter = 0
data = dict()

START_TIMESTAMP = 1589500800
DRLEN = 12
THRESHOLD = 400

year = pd.to_datetime(START_TIMESTAMP, unit='s').year
month = pd.to_datetime(START_TIMESTAMP, unit='s').month
day = pd.to_datetime(START_TIMESTAMP, unit='s').day

grid_balance = 0


def secondsToString(x):
    m, s = divmod(x*10, 60)
    h, m = divmod(m, 60)
    return f'{h:d}:{m:02d}'


def read_background(id):
    year = datetime.date.fromtimestamp(
        START_TIMESTAMP).strftime('%Y')
    month = datetime.date.fromtimestamp(
        START_TIMESTAMP).strftime('%m')
    day = datetime.date.fromtimestamp(
        START_TIMESTAMP).strftime('%d')
    path = os.path.join(os.path.dirname(
        os.path.realpath(__file__)), BACKGROUND_FOLDER)
    year_path = os.path.join(path, year)
    month_path = os.path.join(year_path, month)

    df = pd.read_csv(os.path.join(
        month_path, id + ".csv"))
    df['timestamp'] = pd.to_datetime(
        df['timestamp'])
    dt = datetime.datetime(year=int(year), month=int(month), day=int(day))
    start = pd.to_datetime(calendar.timegm(dt.timetuple()), unit='s')
    dt = datetime.datetime(year=int(year), month=int(month), day=int(day) + 1)
    stop = pd.to_datetime(calendar.timegm(dt.timetuple()), unit='s')
    df = df.loc[(df['timestamp'] >= start)
                & (df['timestamp'] < stop)]
    df = df.set_index('timestamp')
    start = df.index.min().date()
    end = df.index.max().date() + pd.Timedelta(1, 'D')
    df = df.reindex(pd.date_range(start, end, freq='%dS' %
                    FREQ, inclusive='both')).fillna(method='ffill')

    return df.iloc[:-1, :]


def read_baseline(id):
    year = datetime.date.fromtimestamp(
        START_TIMESTAMP).strftime('%Y')
    month = datetime.date.fromtimestamp(
        START_TIMESTAMP).strftime('%m')
    day = datetime.date.fromtimestamp(
        START_TIMESTAMP).strftime('%d')
    path = os.path.join(os.path.dirname(
        os.path.realpath(__file__)), BASELINE_FOLDER)
    year_path = os.path.join(path, year)
    month_path = os.path.join(year_path, month)

    df = pd.read_csv(os.path.join(
        month_path, id + ".csv"))
    df['timestamp'] = pd.to_datetime(
        df['timestamp'])
    dt = datetime.datetime(year=int(year), month=int(month), day=int(day))
    start = pd.to_datetime(calendar.timegm(dt.timetuple()), unit='s')
    dt = datetime.datetime(year=int(year), month=int(month), day=int(day) + 1)
    stop = pd.to_datetime(calendar.timegm(dt.timetuple()), unit='s')
    df = df.loc[(df['timestamp'] >= start)
                & (df['timestamp'] < stop)]
    df = df.set_index('timestamp')
    start = df.index.min().date()
    end = df.index.max().date() + pd.Timedelta(1, 'D')
    df = df.reindex(pd.date_range(start, end, freq='%dS' %
                    FREQ, inclusive='both')).fillna(method='ffill')

    return df.iloc[:-1, :]


def get_task_values(id, task):
    config = json.load(open('scenario/' + id + '/config.json'))
    neg = 1
    try:
        file = 'appliances/' + task['category'] + '/' + task['appliance'] + '/' + task['program'] + '/' + os.listdir(
            'appliances/' + task['category'] + '/' + task['appliance'] + '/' + task['program'] + '/')[0]
    except:
        file = 'appliances/' + \
            task['category'] + '/' + task['appliance'] + '/' + \
            str(year - 1) + f'{month:02}' + f'{day:02}' + ".csv"
        neg = -1
    try:
        dft = pd.read_csv(file)
        if 'timestamp' in dft.columns.values:
            dft['timestamp'] = pd.to_datetime(dft['timestamp'])
            dft = dft.set_index('timestamp')
            start = dft.index.min().date()
            end = dft.index.max().date() + pd.Timedelta(1, 'D')
            dft = dft.reindex(pd.date_range(start, end, freq='%dS' %
                              FREQ, inclusive='both')).fillna(method='ffill')
        else:
            dft = dft.iloc[::FREQ, :]

        arr = dft['value'].values
    except:
        for p in config["setup"][task["category"]][task["appliance"]]:
            if p["programName"] == task['program']:
                if p['duration'] == -1:
                    arr = p["averagePower"] * np.ones(int(3600 * 24 / FREQ))
                else:
                    arr = p["averagePower"] * \
                        np.ones(int(p['duration'] / FREQ))
                if p['generatesPower'] == "True":
                    neg = -1
                else:
                    neg = 1
    return arr, neg


def read_config(id):
    config = json.load(open('scenario/' + id + '/config.json'))
    appliances = {}
    for c in config['setup']:
        for a in config['setup'][c]:
            appliances[a] = config['setup'][c][a]
    tasks = []
    for task in config['tasks']:
        obj = task
        arr, neg = get_task_values(id, task)
        task['values'] = arr
        task['counter'] = 0
        if len(arr) < 24 * 3600 / FREQ:
            task['state'] = State.Pending.value
        else:
            task['state'] = State.InProgress.value
        task['neg'] = neg
        task['lastpaused'] = 0
        tasks.append(task)
    batteries = []
    # if 'batteries' in config:
    #     for b in config['batteries']:
    #         batteries.append(
    #             Battery(b['name'], b['maxCapacity'], b['maxChargeRate'], b['maxDischargeRate']))
    return appliances, tasks, batteries


# TODO bateries in config

def checksThreshold(actualConsume, desiredConsume, threshold):
    if abs(actualConsume - desiredConsume) <= threshold:
        return IN_BOUNDS, abs(actualConsume - desiredConsume)
    if actualConsume - desiredConsume > threshold:
        return SURPLUS, abs(actualConsume - desiredConsume)
    return SHORTAGE, abs(actualConsume - desiredConsume)


class Battery:
    def __init__(self, name, maxCapacity, maxChargeRate, maxDischargeRate):
        self.maxCapacity = maxCapacity
        self.maxChargeRate = maxChargeRate
        self.maxDischargeRate = maxDischargeRate
        self.capacity = 0
        self.rate = 0
        self.history = []

    def charge(self, desired):
        desired -= self.rate
        if self.capacity < self.maxCapacity:
            possible = self.maxCapacity - self.capacity
            if possible > self.maxChargeRate:
                possible = self.maxChargeRate
            if possible > desired:
                possible = desired
        else:
            possible = 0
        self.capacity += possible
        self.rate = possible
        return possible

    def discharge(self, desired):
        desired -= self.rate
        if self.capacity > 0:
            possible = self.capacity
            if possible > self.maxDischargeRate:
                possible = self.maxDischargeRate
            if possible > desired:
                possible = desired
        else:
            possible = 0
        self.capacity -= possible
        self.rate = 0 - possible
        return possible


class Prosumer:
    def __init__(self, id, threshold) -> None:
        self.threshold = threshold
        self.id = id
        self.background = read_background(id)
        self.baseline = read_baseline(id)
        self.appliances,  self.tasks, self.batteries = read_config(id)
        self.dr = None
        self.drindex = None
        self.drhistory = []
        self.consume = []

    def getDowngradeDifference(self, appliance, program):
        for a in self.appliances:
            if a == appliance:
                for i in range(1, len(self.appliances[a])):
                    if self.appliances[a][i]['programName'] == program and self.appliances[a][i]['downgradeable'] == "True":
                        return self.appliances[a][i]['averagePower'] - self.appliances[a][i-1]['averagePower'], self.appliances[a][i-1]
        return None, None

    def getUpgradeDifference(self, appliance, program):
        for a in self.appliances:
            if a == appliance:
                for i in range(0, len(self.appliances[a]) - 1):
                    if self.appliances[a][i]['programName'] == program and self.appliances[a][i + 1]['downgradeable'] == "True":
                        return self.appliances[a][i + 1]['averagePower'] - self.appliances[a][i]['averagePower'], self.appliances[a][i+1]
        return None, None

    def changeTask(self, program, taskIndex):
        self.tasks[taskIndex]['program'] = program
        arr, neg = get_task_values(self.id, self.tasks[taskIndex])
        self.tasks[taskIndex]['values'] = arr

    def pauseTask(self, taskIndex):
        print(self.id, taskIndex,
              self.tasks[taskIndex]['appliance'], " paused")
        self.tasks[taskIndex]['state'] = State.Paused.value

    def resumeTask(self, taskIndex):
        print(self.id, taskIndex,
              self.tasks[taskIndex]['appliance'], " resumed")
        self.tasks[taskIndex]['state'] = State.InProgress.value

    def startTask(self, taskIndex):
        print(self.id, taskIndex,
              self.tasks[taskIndex]['appliance'], " started")
        self.tasks[taskIndex]['state'] = State.InProgress.value

    def finishTask(self, taskIndex):
        print(self.id, taskIndex,
              self.tasks[taskIndex]['appliance'], " finished")
        self.tasks[taskIndex]['state'] = State.Finished.value

    def registerDR(self, imbalance, index):
        if index + DRLEN >= 8640:
            return
        self.drindex = 0
        self.dr = []
        bv = self.baseline['value'].values
        for i in range(DRLEN):
            if bv[index + i] == 0:
                self.dr.append(0)
            else:
                self.dr.append(
                    bv[index + i] + (imbalance//bv[index + i]))

    def getProgram(self, program, appliance):
        for a in self.appliances:
            if a == appliance:
                for i in range(0, len(self.appliances[a])):
                    if self.appliances[a][i]['programName'] == program:
                        return self.appliances[a][i]

    def getActiveTask(self, appliance):
        for t in self.tasks:
            if t['appliance'] == appliance and t['state'] in [State.InProgress.value, State.Paused.value]:
                return t
        return None

    def tick(self, index):
        background_value = self.background['value'][index]
        actual_consume_value = background_value
        for task in self.tasks:
            if task['state'] == State.InProgress.value:
                actual_consume_value += task['neg'] * \
                    task['values'][task['counter']]
                task['counter'] += 1
                if task['counter'] == len(task['values']):
                    self.finishTask(self.tasks.index(task))

        for b in self.batteries:
            actual_consume_value += b.rate
            b.history.append(b.rate)
        consume_value = actual_consume_value
        desired_value = None

        balanced = False

        for priority in range(5, 0, -1):
            if balanced:
                break
            for task in self.tasks:
                if self.getProgram(task['program'], task['appliance'])['priority'] == priority and self.getActiveTask(task['appliance']) is None and task['state'] == State.Pending.value:
                    new_consume_to_be = consume_value + \
                        self.getProgram(task['program'], task['appliance'])[
                            'averagePower']

                    if consume_value < 0 and self.getProgram(task['program'], task['appliance'])[
                            'averagePower'] < THRESHOLD - grid_balance:
                        self.startTask(self.tasks.index(task))
                        print(index,
                              f"Found pending task with priority {priority} of program {task['program']}, new consume {new_consume_to_be}")
                        consume_value = new_consume_to_be

        if self.dr is not None:
            desired_value = self.dr[self.drindex]
            check, actual_current_diff = checksThreshold(
                consume_value, desired_value, self.threshold)
            current_diff = actual_current_diff
            # if self.id == "1":
            #     print(consume_value, desired_value)
            self.drindex += 1
            if self.drindex == len(self.dr):
                self.dr = None
                self.drindex = None

            balanced = False

            for priority in range(5, 0, -1):
                if balanced:
                    break
                for task in self.tasks:
                    if self.getProgram(task['program'], task['appliance'])['priority'] == priority and self.getActiveTask(task['appliance']) is None and task['state'] == State.Pending.value:
                        new_consume_to_be = consume_value + \
                            self.getProgram(task['program'], task['appliance'])[
                                'averagePower']

                        check, new_diff = checksThreshold(
                            new_consume_to_be, desired_value, self.threshold)
                        if new_diff < current_diff or consume_value < 0 - self.threshold:
                            self.startTask(self.tasks.index(task))
                            print(index,
                                  f"Found pending task with priority {priority} of program {task['program']}, new consume {new_consume_to_be}")
                            current_diff = new_diff
                            consume_value = new_consume_to_be
                        if check == IN_BOUNDS:
                            balanced = True
                            break

            # increase consume by resuming
            for priority in range(5, 0, -1):
                if balanced:
                    break
                for task in self.tasks:
                    if self.getProgram(task['program'], task['appliance'])['priority'] == priority and task['state'] == State.Paused.value:
                        new_consume_to_be = consume_value + \
                            task["values"][task["counter"]]
                        check, new_diff = checksThreshold(
                            new_consume_to_be, desired_value, self.threshold)
                        if new_diff < current_diff or consume_value < 0 - self.threshold:
                            self.resumeTask(self.tasks.index(task))
                            current_diff = new_diff
                            consume_value = new_consume_to_be
                        if check == IN_BOUNDS:
                            balanced = True
                            break

            check, actual_current_diff = checksThreshold(
                consume_value, desired_value, self.threshold)
            current_diff = actual_current_diff

            if check != IN_BOUNDS:
                if check == SURPLUS:
                    for b in self.batteries:
                        possible = b.discharge(current_diff)
                        new_consume_to_be = consume_value - possible
                        check, new_diff = checksThreshold(
                            new_consume_to_be, desired_value, self.threshold)
                        current_diff = new_diff
                        consume_value = new_consume_to_be
                        if check == IN_BOUNDS:
                            balanced = True
                            break

                    for priority in range(1, 6):
                        if balanced:
                            break
                        for task in self.tasks:
                            if self.getProgram(task['program'], task['appliance'])['priority'] == priority and task['state'] == State.InProgress.value:
                                diff, new_program = self.getDowngradeDifference(
                                    task['appliance'], task['program'])
                                if diff is not None:
                                    new_consume_to_be = consume_value - diff
                                    check, new_diff = checksThreshold(
                                        new_consume_to_be, desired_value, self.threshold)
                                    if new_diff < self.threshold:
                                        self.changeTask(
                                            new_program['programName'], self.tasks.index(task))
                                        current_diff = new_diff
                                        consume_value = new_consume_to_be
                                    if check == IN_BOUNDS:
                                        balanced = True
                                        break

                    for priority in range(1, 6):
                        if balanced:
                            break
                        for task in self.tasks:
                            if self.getProgram(task['program'], task['appliance'])['priority'] == priority and task['state'] == State.InProgress.value and self.getProgram(task['program'], task['appliance'])['interruptible'] == 'True':
                                new_consume_to_be = consume_value - \
                                    task["values"][task["counter"]]
                                check, new_diff = checksThreshold(
                                    new_consume_to_be, desired_value, self.threshold)
                                if new_diff < self.threshold and index - task['lastpaused'] > 0:
                                    self.pauseTask(self.tasks.index(task))
                                    task['lastpaused'] = index
                                    current_diff = new_diff
                                    consume_value = new_consume_to_be
                                if check == IN_BOUNDS:
                                    balanced = True
                                    break

                elif check == SHORTAGE:

                    for b in self.batteries:
                        possible = b.charge(current_diff)
                        new_consume_to_be = consume_value + possible
                        check, new_diff = checksThreshold(
                            new_consume_to_be, desired_value, self.threshold)
                        current_diff = new_diff
                        consume_value = new_consume_to_be
                        if check == IN_BOUNDS:
                            balanced = True
                            break
# increase consume by resuming
                    for priority in range(5, 0, -1):
                        if balanced:
                            break
                        for task in self.tasks:
                            if self.getProgram(task['program'], task['appliance'])['priority'] == priority and task['state'] == State.Paused.value:
                                new_consume_to_be = consume_value + \
                                    task["values"][task["counter"]]
                                check, new_diff = checksThreshold(
                                    new_consume_to_be, desired_value, self.threshold)
                                if new_diff < self.threshold:
                                    self.resumeTask(self.tasks.index(task))
                                    current_diff = new_diff
                                    consume_value = new_consume_to_be
                                if check == IN_BOUNDS:
                                    balanced = True
                                    break

            # increase consume by programming
                    for priority in range(5, 0, -1):
                        if balanced:
                            break
                        for task in self.tasks:
                            if self.getProgram(task['program'], task['appliance'])['priority'] == priority and self.getActiveTask(task['appliance']) is None and task['state'] == State.Pending.value:
                                new_consume_to_be = consume_value + \
                                    self.getProgram(task['program'], task['appliance'])[
                                        'averagePower']

                                check, new_diff = checksThreshold(
                                    new_consume_to_be, desired_value, self.threshold)
                                if new_diff < self.threshold:
                                    self.startTask(self.tasks.index(task))
                                    print(index,
                                          f"Found pending task with priority {priority} of program {task['program']}, new consume {new_consume_to_be}")
                                    current_diff = new_diff
                                    consume_value = new_consume_to_be
                                if check == IN_BOUNDS:
                                    balanced = True
                                    break
                    # increase consume by upgrading
                    for priority in range(5, 0, -1):
                        if balanced:
                            break
                        for task in self.tasks:
                            if self.getProgram(task['program'], task['appliance'])['priority'] == priority and task['state'] == State.InProgress.value:
                                diff, new_program = self.getUpgradeDifference(
                                    task['appliance'], task['program'])
                                if diff is not None:
                                    new_consume_to_be = consume_value + \
                                        task["values"][task["counter"]]
                                    check, new_diff = checksThreshold(
                                        new_consume_to_be, desired_value, self.threshold)
                                    if new_diff < self.threshold:
                                        self.changeTask(
                                            task['program'], self.tasks.index(task))
                                        current_diff = new_diff
                                        consume_value = new_consume_to_be
                                    if check == IN_BOUNDS:
                                        balanced = True
                                        break

        self.consume.append(actual_consume_value)
        self.drhistory.append(desired_value if desired_value else np.nan)
        return actual_consume_value


plt.rcParams['font.size'] = 20


def main():
    prosumers = []
    grid_total = []
    grid_baseline = np.zeros(3600*24//FREQ)
    i = 1
    for id in ids:
        prosumers.append(Prosumer(id, i * 50 + 250))
        i += 1

    dr_countdown = 0

    for i in range((3600 * 24)//FREQ):
        global grid_balance
        grid_balance = 0
        for p in prosumers:
            grid_balance += p.tick(i)
            if np.abs(grid_balance) > THRESHOLD and dr_countdown == 0:
                dr_countdown = 12
                for p in prosumers:
                    p.registerDR(grid_balance, i)
        grid_total.append(grid_balance)
        if dr_countdown > 0:
            dr_countdown -= 1

    plt.figure(figsize=(30, 10))

    time = [secondsToString(x) for x in range(0, 8640)]
    plt.figure(figsize=(30, 10))
    plt.xticks(ticks=range(0, 25*60, 60), labels=['00:00', '01:00', '02:00', '03:00', '04:00', '05:00', '06:00',
               '07:00', '08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '23:59'])
    plt.ylabel('Putere (W)')
    plt.title("Totalul puterii consumate în microrețea (sarcini programate dinamic)")

    for p in prosumers:
        grid_baseline += np.array(p.baseline['value'], dtype=float)

        plt.figure(figsize=(30, 10))

        print(len(p.consume))
        print(len(p.drhistory))
        plt.xticks(ticks=range(0, 25*60, 60), labels=['00:00', '01:00', '02:00', '03:00', '04:00', '05:00', '06:00',
                                                      '07:00', '08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '23:59'])

        plt.plot(time, p.consume, label="Putere consumată", linewidth=3)
        plt.plot(time, p.drhistory, label="Semnal DR", linewidth=5)
        initial = np.fromfile('1.txt', sep='\n')
        print(len(initial))
        init = initial[::10]
        plt.ylabel('Putere (W)')

        plt.plot(time, p.baseline['value'].values, label="Nivel referință")
        plt.plot(time, init, label="Nivel inițial", alpha=0.5)
        plt.fill_between(time, p.baseline['value'].values - np.ones(len(p.baseline)) * p.threshold,
                         p.baseline['value'].values +
                         np.ones(len(p.baseline)) * p.threshold,
                         alpha=0.1, label='Marjă acceptată consum')
        plt.legend()
        plt.ylabel('Putere (W)')

        plt.savefig(p.id + 'prosumer.png')
    plt.figure(figsize=(30, 10))

    print(len(grid_baseline))
    print(len(grid_total))

    plt.xticks(ticks=range(0, 25*60, 60), labels=['00:00', '01:00', '02:00', '03:00', '04:00', '05:00', '06:00',
               '07:00', '08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '23:59'])

    plt.plot(time, grid_total, label="Total")
    plt.plot(time, grid_baseline, label="Nivel referință")
    plt.ylim(-2500, 4500)
    plt.legend()
    plt.ylabel('Putere (W)')

    plt.title("Totalul puterii consumate în microrețea (sarcini dinamice)")

    plt.savefig('baseline with tasks.png')

    plt.figure(figsize=(30, 10))

    # for p in prosumers:

    #     for b in p.batteries:
    #         plt.plot(time, b.history)

    # plt.savefig('battery.png')

    for p in prosumers:
        print(len(p.tasks))
        for t in p.tasks:
            print(t['appliance'], len(t['values']), t['counter'])

    plt.figure(figsize=(30, 10))
    plt.xticks(ticks=range(0, 25*60, 60), labels=['00:00', '01:00', '02:00', '03:00', '04:00', '05:00', '06:00',
               '07:00', '08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '23:59'])
    plt.fill_between(time, np.abs(grid_total - grid_baseline), grid_baseline,
                     label="Difference between total grid power and baseline")
    plt.legend()
    plt.legend()
    plt.ylabel('Power (W)')
    plt.title("Grid imbalance")
    print("Accumulated imbalance: (kWh)",
          (abs(grid_total - grid_baseline)).sum() / (1000 * 3600))
    print("Peak to average power ratio: (dB)", 10 * 10 *
          np.log10(np.max(grid_total) / np.mean(grid_total)))
    print(np.max(grid_total), np.mean(grid_total))
    plt.savefig('imbalance with tasks.png')


if __name__ == "__main__":
    main()
