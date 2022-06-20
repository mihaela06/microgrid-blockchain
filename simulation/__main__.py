import asyncio
import datetime
import os
import random
import calendar

import pandas as pd
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from motor.motor_asyncio import AsyncIOMotorClient

from ..apps.smart_hub.models import (APPLIANCES_DB, BATTERIES_DB, DR_DB,
                                     PROGRAMS_DB, TASKS_DB, State)

THRESHOLD = 0.1
MIDNIGHT_TIMESTAMP = 1555286400  # 15.04.2019
RANDOM_SEED = 42
PROSUMER_NO = 10

SURPLUS = 1
SHORTAGE = -1
IN_BOUNDS = 0
BACKGROUND_FOLDER = "background"


random.seed(RANDOM_SEED)

mongodb_client = AsyncIOMotorClient(
    "mongodb+srv://admin:lXBtOnV2SELj3qkR@cluster0.ke5tapi.mongodb.net/bd?retryWrites=true&w=majority&uuidRepresentation=standard")
mongodb = mongodb_client["bd"]

task_file = {}
background_df = None
time_counter = 0


def read_background():
    global background_df
    year = datetime.date.fromtimestamp(
        MIDNIGHT_TIMESTAMP).strftime('%Y')
    month = datetime.date.fromtimestamp(
        MIDNIGHT_TIMESTAMP).strftime('%m')
    day = datetime.date.fromtimestamp(
        MIDNIGHT_TIMESTAMP).strftime('%d')
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
    background_df = background_df.resample('1S').ffill()


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
                files_no = len(files)
                file_no = random.randint(0, files_no - 1)
                filename = files[file_no]
                df = pd.read_csv(
                    os.path.join(path, filename))
                task_file[task["_id"]] = {
                    "data": df, "counter": 0, "in_use": True, "generatesPower": generates}
                task["remainingTime"] = len(
                    task_file[task["_id"]]["data"].index)
        else:
            filename = datetime.date.fromtimestamp(
                MIDNIGHT_TIMESTAMP).strftime('%Y%m%d') + ".csv"
            df = pd.read_csv(
                os.path.join(path, filename))
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
            df = df.resample('1S').ffill()
            task_file[task["_id"]] = {
                "data": df, "counter": 0, "in_use": True, "generatesPower": generates}
            task["remainingTime"] = len(
                task_file[task["_id"]]["data"].index)
    else:
        task_file[task["_id"]] = {
            "in_use": True, "generatesPower": generates}


async def tick():
    global time_counter
    print("Tick! The time is: %s" % datetime.datetime.now())

    for task in task_file:
        if task_file[task] is not None:
            task_file[task]["in_use"] = False

    counter = None
    signal = None

    db_signal = await mongodb[DR_DB].find().to_list(length=10)
    if len(db_signal) > 0:
        counter = db_signal[0]["counter"]
        signal = db_signal[0]["values"]

    consume_value = background_df['value'][time_counter]
    time_counter += 1

    db_tasks = await mongodb[TASKS_DB].find().to_list(length=1000)
    initial_states = {}
    for task in db_tasks:
        initial_states[task["_id"]] = task["state"]

    db_batteries = await mongodb[BATTERIES_DB].find().to_list(length=1000)

    appliances = {}
    programs = {}

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

        # if DR signal exists, check compliance and modify tasks

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

    if signal is not None:
        desired_value = signal[counter]
        print("Desired value ", desired_value)
        if counter + 1 == len(signal):
            _ = await mongodb[DR_DB].delete_one({"counter": counter})
        else:
            _ = await mongodb[DR_DB].update_one(
                {"counter": counter}, {"$set": {"counter": counter + 1}}
            )

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
                                                 ]["data"].value[task_file[task["_id"]]["counter"]]
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

    print("Consume:", consume_value, len(task_file))
    print("Tock! The time is: %s" % datetime.datetime.now())


def main():
    read_background()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(tick, "interval", seconds=2)
    scheduler.start()

    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
