import asyncio
import calendar
import datetime
import os
import random
import time

import pandas as pd
import pika
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorClient
import hashlib

from .config import (BATCH_SIZE, DYNAMIC, FREQ, PROSUMER_NO, RANDOM_SEED,
                     START_TIMESTAMP, THRESHOLD)
from .generation import generate_requests
from .models import (APPLIANCES_DB, BATTERIES_DB, DR_DB, ENERGY_DATA_DB,
                     PROGRAMS_DB, TASKS_DB, EnergyData, State)

SURPLUS = 1
SHORTAGE = -1
IN_BOUNDS = 0
BACKGROUND_FOLDER = "background"
BASELINE_FOLDER = "baseline"

# TODO uncomment dynamic
# if DYNAMIC:
#     BASELINE_FOLDER = "baseline"
# else:
#     BASELINE_FOLDER = "scenario/baseline"


random.seed(RANDOM_SEED)

mongodb_client = AsyncIOMotorClient(
    "mongodb://root:password@"+os.environ.get("MONGO_HOST")+":27017/?retryWrites=true&w=majority&uuidRepresentation=standard")
mongodb = mongodb_client["hub"]

task_file = {}
background_df = None
baseline_df = None
time_counter = 0
data = dict()
headers = {'Content-Type': 'application/x-www-form-urlencoded'}

BACKEND_URL = "http://" + os.environ.get("BACKEND_HOST") + ":5000"

rabbit_message = None
hash_index = 0
hash_str = "s" * 64


def send_hash():
    if rabbit_message is not None:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=os.environ.get('RABBIT_MQ_HOST')))
        channel = connection.channel()
        channel.basic_publish(exchange='',
                              routing_key='data_queue',
                              body=rabbit_message)
        connection.close()


def get_hash(timestamp, value):
    global hash_index
    global hash_str

    concat = str(timestamp) + str(value) + hash_str

    s = hashlib.sha3_256(concat.encode())

    hash_str = s.hexdigest()
    hash_index += 1
    if hash_index == FREQ:
        hash_index = 0


def read_background():
    global background_df
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

    background_df = pd.read_csv(os.path.join(
        month_path, str(PROSUMER_NO) + ".csv"))
    background_df['timestamp'] = pd.to_datetime(
        background_df['timestamp'], unit='s')
    dt = datetime.datetime(year=int(year), month=int(month), day=int(day))
    start = pd.to_datetime(calendar.timegm(dt.timetuple()), unit='s')
    dt = datetime.datetime(year=int(year), month=int(month), day=int(day) + 1)
    stop = pd.to_datetime(calendar.timegm(dt.timetuple()), unit='s')
    background_df = background_df.loc[(background_df['timestamp'] >= start)
                                      & (background_df['timestamp'] < stop)]
    background_df = background_df.set_index('timestamp')
    background_df = background_df.resample('%dS' % FREQ).ffill()


def read_baseline():
    global baseline_df
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

    baseline_df = pd.read_csv(os.path.join(
        month_path, str(PROSUMER_NO) + ".csv"))
    baseline_df['timestamp'] = pd.to_datetime(
        baseline_df['timestamp'], unit='s')
    dt = datetime.datetime(year=int(year), month=int(month), day=int(day))
    start = pd.to_datetime(calendar.timegm(dt.timetuple()), unit='s')
    dt = datetime.datetime(year=int(year), month=int(month), day=int(day) + 1)
    stop = pd.to_datetime(calendar.timegm(dt.timetuple()), unit='s')
    baseline_df = baseline_df.loc[(baseline_df['timestamp'] >= start)
                                  & (baseline_df['timestamp'] < stop)]
    baseline_df = baseline_df.set_index('timestamp')
    baseline_df = baseline_df.resample('%dS' % FREQ).ffill()


async def getDowngradeDifference(appliance, program):
    index = appliance["programs"].index(program["name"])
    if index < 1:
        # raise Exception("Program not downgradeable")
        return 0, program
    new_program = await mongodb[PROGRAMS_DB].find_one(
        {"name": appliance["programs"][index-1]})
    return program["averagePower"] - new_program["averagePower"], new_program


async def getUpgradeDifference(appliance, program):
    index = appliance["programs"].index(program["name"])
    if index == len(appliance["programs"]) - 1:
        # raise Exception("Program not upgradeable")
        return 0, program
    new_program = await mongodb[PROGRAMS_DB].find_one(
        {"name": appliance["programs"][index+1]})
    return new_program["averagePower"] - program["averagePower"], new_program


def updowngradeTask(task, new_program, appliance, task_file):
    print("Program changed ", task["programName"], " -> ", new_program["name"])
    task_file[task["_id"]] = None
    task["programName"] = new_program["name"]
    task["currentPower"] = new_program["averagePower"]
    findFile(task, new_program, appliance, task_file)


def pauseTask(task):
    print(task["_id"], " paused")
    task["state"] = State.Paused.value


def resumeTask(task, program, appliance, task_file):
    print(task["_id"], " resumed")
    task["state"] = State.InProgress.value
    findFile(task, program, appliance, task_file)


def startTask(task, program, appliance, task_file):
    print(task["_id"], " started")
    task["state"] = State.InProgress.value
    appliance["currentTask"] = task["_id"]
    findFile(task, program, appliance, task_file)
    mongodb[APPLIANCES_DB].update_one(
        {"name": appliance["name"]}, {"$set": {"currentTask": task["_id"]}}
    )


def checksThreshold(actualConsume, desiredConsume, threshold):
    if abs(actualConsume - desiredConsume) <= threshold * desiredConsume:
        return IN_BOUNDS, abs(actualConsume - desiredConsume)
    if actualConsume - desiredConsume > threshold * desiredConsume:
        return SURPLUS, abs(actualConsume - desiredConsume)
    return SHORTAGE, abs(actualConsume - desiredConsume)


def findFile(task, program, appliance, task_file):
    path = os.path.join(os.path.dirname(
        os.path.realpath(__file__)), "appliances")
    path = os.path.join(path, appliance["category"])
    path = os.path.join(path, appliance["model"])

    generates = program["generatesPower"]
    if os.path.isdir(path):
        if program["generatesPower"] is False:
            path = os.path.join(path, task["programName"])
            if not os.path.isdir(path):
                task_file[task["_id"]] = {
                    "in_use": True, "generatesPower": generates}
            else:
                files = os.listdir(path)
                if DYNAMIC:
                    files_no = len(files)
                    file_no = random.randint(0, files_no - 1)
                    filename = files[file_no]
                else:
                    filename = files[0]
                df = pd.read_csv(
                    os.path.join(path, filename))
                df = df.iloc[::FREQ]
                task_file[task["_id"]] = {
                    "data": df, "counter": 0, "in_use": True, "generatesPower": generates}
                task["remainingTime"] = len(
                    task_file[task["_id"]]["data"].index)
        else:
            filename = datetime.date.fromtimestamp(
                START_TIMESTAMP - int(365.25 * 3600 * 24)).strftime('%Y%m%d') + ".csv"  # one year before
            df = pd.read_csv(
                os.path.join(path, filename))
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
            df = df.resample('%dS' % FREQ).ffill()
            task_file[task["_id"]] = {
                "data": df, "counter": 0, "in_use": True, "generatesPower": generates}
            task["remainingTime"] = len(
                task_file[task["_id"]]["data"].index)
    else:
        task_file[task["_id"]] = {
            "in_use": True, "generatesPower": generates}


def send_baseline(values):
    data = {'baseline': values}
    requests.post(BACKEND_URL +
                  "/register_baseline", data=data, headers=headers)
    print("Registered baseline: ", values)


async def tick():
    global time_counter
    start_tick = datetime.datetime.now()
    print("Tick! The time is: %s" % start_tick)

    for task in task_file:
        if task_file[task] is not None:
            task_file[task]["in_use"] = False

    counter = None
    signal = None
    desired_value = None

    db_signal = await mongodb[DR_DB].find().to_list(length=10)
    print(db_signal)
    if len(db_signal) > 0:
        counter = db_signal[0]["counter"]
        signal = []
        for i in db_signal[0]["values"]:
            signal.append(float(i))

    background_value = background_df['value'][time_counter]
    consume_value = background_value
    if time_counter % BATCH_SIZE == 0:
        send_baseline(baseline_df['value']
                      [time_counter:time_counter+BATCH_SIZE].values)

    db_tasks = await mongodb[TASKS_DB].find().to_list(length=1000)
    initial_states = {}
    for task in db_tasks:
        initial_states[task["_id"]] = task["state"]

    db_batteries = await mongodb[BATTERIES_DB].find().to_list(length=1000)

    appliances = {}
    programs = {}
    appliances_dict = {}
    batteries_dict = {}

    for task in db_tasks:

        appliance = await mongodb[APPLIANCES_DB].find_one({"tasks": task["_id"]})
        appliances[task["_id"]] = appliance
        program = await mongodb[PROGRAMS_DB].find_one({"applianceId": appliance["_id"], "name": task["programName"]})
        programs[task["_id"]] = program

        # add new in progress tasks in task_file and their randomly chosen file - if appliable

        if task["_id"] not in task_file and task["state"] == State.InProgress.value:
            findFile(task, program, appliance, task_file)

        # calculate total consumption

        if task["state"] == State.InProgress.value:
            if task_file[task["_id"]]["generatesPower"] is False:
                consume_value += task["currentPower"]
            else:
                consume_value -= task["currentPower"]

            appliances_dict[appliance["_id"]] = task["currentPower"]

    for battery in db_batteries:
        if battery["connected"] is True:
            if battery["currentRate"] > 0:
                # charging
                charged = battery["currentRate"]
                if battery["maxCapacity"] - battery["currentCapacity"] < charged:
                    charged = battery["maxCapacity"] - \
                        battery["currentCapacity"]
                battery["currentRate"] = charged
                battery["currentCapacity"] += charged
                consume_value += charged
            else:
                # discharging
                discharged = battery["currentRate"]
                if battery["currentCapacity"] < 0 - discharged:
                    discharged = 0 - battery["currentCapacity"]
                battery["currentRate"] = discharged
                battery["currentCapacity"] += discharged
                consume_value += discharged
            batteries_dict[battery["_id"]] = {
                "rate": battery["currentRate"], "capacity": battery["currentCapacity"]}

    # if DR signal exists, check compliance and modify tasks

    if signal is not None:
        desired_value = signal[counter]

        print("Desired value ", desired_value)
        print("Signal ", signal, counter)
        if counter + 1 == len(signal):
            _ = await mongodb[DR_DB].delete_one({"counter": counter})
        else:
            _ = await mongodb[DR_DB].update_one(
                {"counter": counter}, {"$set": {"counter": counter + 1}}
            )

        if not desired_value:
            desired_value = 0

        check, current_diff = checksThreshold(
            consume_value, desired_value, THRESHOLD)

        if check != IN_BOUNDS:
            balanced = False

            # balance by charging/discharging batteries
            for battery in db_batteries:
                if balanced:
                    break
                if battery["connected"] is True:
                    old_rate = battery["currentRate"]
                    consume_without = consume_value - old_rate
                    imbalance = desired_value - consume_without
                    if imbalance < 0:
                        # discharging
                        dischargeRate = battery["maxDischargeRate"]
                        if dischargeRate > battery["currentCapacity"]:
                            dischargeRate = battery["currentCapacity"]
                        if dischargeRate > abs(imbalance):
                            dischargeRate = abs(imbalance)
                        battery["currentRate"] = 0 - dischargeRate
                        new_consume_to_be = consume_without - dischargeRate
                        new_check, new_diff = checksThreshold(
                            new_consume_to_be, desired_value, THRESHOLD)
                        if new_check == IN_BOUNDS:
                            balanced = True
                            break
                    else:
                        # charging
                        chargeRate = battery["maxChargeRate"]
                        if chargeRate > battery["maxCapacity"] - battery["currentCapacity"]:
                            chargeRate = battery["maxCapacity"] - \
                                battery["currentCapacity"]
                        if chargeRate > imbalance:
                            chargeRate = imbalance
                        battery["currentRate"] = chargeRate
                        new_consume_to_be = consume_without + chargeRate
                        new_check, new_diff = checksThreshold(
                            new_consume_to_be, desired_value, THRESHOLD)
                        if new_check == IN_BOUNDS:
                            balanced = True
                            break

            if check == SURPLUS:
                print("Surplus")

                # decrease consume by downgrading
                for priority in range(1, 6):
                    if balanced:
                        break
                    for task in db_tasks:
                        if balanced:
                            break
                        appliance = appliances[task["_id"]]
                        if appliance["currentTask"] == task["_id"]:
                            program = programs[task["_id"]]
                            if program["priority"] == priority:
                                if program["downgradeable"]:
                                    print(program["name"])
                                    diff, new_program = await getDowngradeDifference(
                                        appliance, program)
                                    new_consume_to_be = consume_value - diff
                                    new_check, new_diff = checksThreshold(
                                        new_consume_to_be, desired_value, THRESHOLD)
                                    if new_diff < current_diff:
                                        updowngradeTask(
                                            task, new_program, appliance, task_file)
                                    if new_check == IN_BOUNDS:
                                        balanced = True
                                        break

                # decrease consume by interrupting
                for priority in range(1, 6):
                    if balanced:
                        break
                    for task in db_tasks:
                        if balanced:
                            break
                        if task["state"] == State.InProgress.value:
                            appliance = appliances[task["_id"]]
                            if appliance["currentTask"] == task["_id"]:
                                program = programs[task["_id"]]
                                if program["priority"] == priority:
                                    new_consume_to_be = consume_value - \
                                        task["currentPower"]
                                    new_check, new_diff = checksThreshold(
                                        new_consume_to_be, desired_value, THRESHOLD)
                                    if new_diff < current_diff:
                                        pauseTask(task)
                                    if new_check == IN_BOUNDS:
                                        balanced = True
                                        break

            elif check == SHORTAGE:
                print("Shortage")

                # increase consume by resuming
                for priority in range(5, 0, -1):
                    if balanced:
                        break
                    for task in db_tasks:
                        if balanced:
                            break
                        if task["state"] == State.Paused.value:
                            appliance = appliances[task["_id"]]
                            if appliance["currentTask"] == task["_id"]:
                                program = programs[task["_id"]]
                                if program["priority"] == priority:
                                    new_consume_to_be = consume_value + \
                                        task["currentPower"]
                                    new_check, new_diff = checksThreshold(
                                        new_consume_to_be, desired_value, THRESHOLD)
                                    if new_diff < current_diff:
                                        resumeTask(task, program,
                                                   appliance, task_file)
                                    if new_check == IN_BOUNDS:
                                        balanced = True
                                        break

                # increase consume by programming
                for priority in range(5, 0, -1):
                    if balanced:
                        break
                    for task in db_tasks:
                        if balanced:
                            break
                        if task["state"] == State.Pending.value:
                            appliance = appliances[task["_id"]]
                            if appliance["currentTask"] is None:
                                program = programs[task["_id"]]
                                if program["priority"] == priority:
                                    new_consume_to_be = consume_value + \
                                        task["currentPower"]
                                    print(
                                        f"Found pending task with priority {priority} of program {program}, new consume {new_consume_to_be}")
                                    new_check, new_diff = checksThreshold(
                                        new_consume_to_be, desired_value, THRESHOLD)
                                    if new_diff < current_diff:
                                        startTask(task, program,
                                                  appliance, task_file)
                                    if new_check == IN_BOUNDS:
                                        balanced = True
                                        break

                # increase consume by upgrading
                for priority in range(5, 0, -1):
                    if balanced:
                        break
                    for task in db_tasks:
                        if balanced:
                            break
                        appliance = appliances[task["_id"]]
                        if appliance["currentTask"] == task["_id"]:
                            program = programs[task["_id"]]
                            if program["priority"] == priority:
                                diff, new_program = await getUpgradeDifference(
                                    appliance, program)
                                new_consume_to_be = consume_value + diff
                                new_check, new_diff = checksThreshold(
                                    new_consume_to_be, desired_value, THRESHOLD)
                                if new_diff < current_diff:
                                    updowngradeTask(
                                        task, new_program, appliance, task_file)
                                if new_check == IN_BOUNDS:
                                    balanced = True
                                    break

    for task in db_tasks:
        if task["state"] == State.InProgress.value:
            if task["remainingTime"] != -1:
                task["remainingTime"] -= 1
            if "data" in task_file[task["_id"]]:
                task["currentPower"] = task_file[task["_id"]
                                                 ]["data"]["value"].values[task_file[task["_id"]]["counter"]]
                task_file[task["_id"]]["counter"] += 1
                if task_file[task["_id"]]["counter"] == len(
                        task_file[task["_id"]]["data"].index):
                    task_file[task["_id"]]["counter"] = 0
            task_file[task["_id"]]["in_use"] = True
            if task["remainingTime"] == 0:
                task["state"] = State.Finished.value
                appliance = await mongodb[APPLIANCES_DB].find_one({"currentTask": task["_id"]})
                appliance["currentTask"] = None
                _ = await mongodb[APPLIANCES_DB].update_one(
                    {"name": appliance["name"]}, {"$set": appliance}
                )
                del task_file[task["_id"]]

        _ = await mongodb["tasks"].update_one(
            {"_id": task["_id"], "state": initial_states[task["_id"]]}, {
                "$set": task}
        )

        if task["_id"] in task_file and task["state"] == State.Paused.value:
            task_file[task["_id"]]["in_use"] = True

    for battery in db_batteries:
        _ = await mongodb[BATTERIES_DB].update_one(
            {"name": battery["name"]}, {"$set": {
                "currentCapacity": battery["currentCapacity"],
                "currentRate": battery["currentRate"]}}
        )

    to_be_del = []
    for task in task_file:
        if task_file[task] is not None:
            if task_file[task]["in_use"] == False:
                to_be_del.append(task)

    for task in to_be_del:
        del task_file[task]

    data['value'] = int(consume_value)
    requests.post(BACKEND_URL +
                  "/register_value", data=data, headers=headers)
    get_hash((START_TIMESTAMP + time_counter * FREQ)*1000, int(consume_value))

    global rabbit_message
    rabbit_message = str((START_TIMESTAMP + time_counter * FREQ)*1000) + ";" + \
        os.environ.get("PROSUMER_ACCOUNT") + ";" + \
        hash_str + ";" + \
        str(int(consume_value))

    send_hash()

    if hash_index == 0:
        hash_data = {'hash': hash_str}
        requests.post(BACKEND_URL +
                      "/register_hash", data=hash_data, headers=headers)
        print("Registered hash: ", hash_str)

    print("Registered value: ", int(consume_value))

    energyData = jsonable_encoder(EnergyData(ts=START_TIMESTAMP + time_counter * FREQ, total=consume_value, background=background_value,
                                             appliances=appliances_dict, batteries=batteries_dict, current_dr=desired_value))
    time_counter += 1
    # print(energyData)
    _ = mongodb[ENERGY_DATA_DB].insert_one(energyData)

    stop_tick = datetime.datetime.now()
    print("Tock! The time is: %s" % stop_tick)
    print("Elapsed ", stop_tick - start_tick, " seconds.")


def main():
    time.sleep(30)
    read_background()
    read_baseline()
    generate_requests()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(tick, "interval", seconds=FREQ)
    scheduler.start()

    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
