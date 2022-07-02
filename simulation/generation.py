import json
import os
import random

import numpy as np
import requests as re
from sqlalchemy import true

THRESHOLD = os.getenv('THRESHOLD')
MIDNIGHT_TIMESTAMP = os.getenv('MIDNIGHT_TIMESTAMP')  # 15.04.2019
RANDOM_SEED = os.getenv('RANDOM_SEED')
PROSUMER_NO = os.getenv('PROSUMER_NO')
CATEGORIES = ['Dish Washer', 'TV', 'Washing Machine']
PRIORITIES = {
    'Dish Washer': 4,
    'TV': 2,
    'Washing Machine': 5
}
INTERRUPTIBLE = {
    'Dish Washer': True,
    'TV': False,
    'Washing Machine': True
}
DOWNGRADEABLE = {
    'Dish Washer': False,
    'TV': False,
    'Washing Machine': False
}
PROGRAMMABLE = {
    'Dish Washer': True,
    'TV': False,
    'Washing Machine': True
}
AVERAGE_POWER = {
    'Dish Washer': 1500,
    'TV': 100,
    'Washing Machine': 2000
}
DURATION = {
    'Dish Washer': 90 * 60,
    'TV': 60 * 60,
    'Washing Machine': 150 * 60
}
BACKGROUND_FOLDER = "background"
APPLIANCES_FOLDER = "appliances"

THRESHOLD = 0.1
MIDNIGHT_TIMESTAMP = 1555286400  # 15.04.2019
RANDOM_SEED = 42
PROSUMER_NO = 1

# TODO import from config.py

random.seed(RANDOM_SEED)

reqs = []
api_url = "http://"+os.environ.get("SMART_HUB_HOST")+":8000/"


class Request:
    def __init__(self, method, endpoint, data):
        self.method = method
        self.endpoint = endpoint
        self.data = data

    def __str__(self):
        return self.method + "  " + self.endpoint + " " + str(self.data)


def req_add_appliance(name, model, category):
    global reqs
    reqs.append(Request("POST", "appliances", {
                "name": name, "model": model, "category": category}))


def req_add_program(appliance_name, name, averagePower, duration, priority, downgradeable, programmable, interruptible, generatesPower=False):
    global reqs
    endpoint = "appliances/" + appliance_name + "/programs"
    reqs.append(Request("POST", endpoint, {"name": name, "averagePower": averagePower, "duration": duration, "priority": priority,
                "downgradeable": downgradeable, "programmable": programmable, "interruptible": interruptible, "generatesPower": generatesPower}))


def req_start_task(appliance_name, program_name):
    global reqs
    endpoint = "appliances/" + appliance_name + "/tasks/start"
    reqs.append(Request("POST", endpoint, {"programName": program_name}))

def req_program_task(appliance_name, program_name):
    global reqs
    endpoint = "appliances/" + appliance_name + "/tasks/program"
    reqs.append(Request("POST", endpoint, {"programName": program_name}))

def generate_requests():
    print(os.environ.get("DYNAMIC"))
    if os.environ.get("DYNAMIC") == "true":
        dynamic_generation()
    else:
        static_generation()


def dynamic_generation():
    names = []
    name_counter = 2

    for category in CATEGORIES:
        path = os.path.join(os.path.dirname(
            os.path.realpath(__file__)), APPLIANCES_FOLDER)
        path = os.path.join(path, category)
        models = os.listdir(path)
        models = random.sample(models, k=min(3, len(models)))
        for model in models:
            init_name = model.split(" ")[0] + " " + category
            name = init_name
            while name in names:
                name = init_name + str(name_counter)
                name_counter += 1
            names.append(name)
            name_counter = 2
            req_add_appliance(name, model, category)
            model_path = os.path.join(path, model)
            programs = os.listdir(model_path)
            programs = random.sample(
                programs, k=random.randint(1, min(2, len(programs))))
            for program in programs:
                req_add_program(name, program, AVERAGE_POWER[category], DURATION[category], PRIORITIES[category],
                                DOWNGRADEABLE[category], PROGRAMMABLE[category], INTERRUPTIBLE[category], generatesPower=False)
                for i in range(random.randint(1, 2)):
                    req_program_task(name, program)

    # for r in reqs:
    #     print(r)

    for r in reqs:
        response = re.request(method=r.method, url=api_url +
                              r.endpoint, json=r.data, timeout=(1, 5))
        print(response)
        print(response.content)


def static_generation():
    config_path = os.path.join(os.path.dirname(
        os.path.realpath(__file__)), 'scenario')
    config_path = os.path.join(config_path, str(PROSUMER_NO))
    config_path = os.path.join(config_path, "config.json")
    config = json.load(open(config_path))
    for c in config['setup']:
        for a in config['setup'][c]:
            print(a, c)
            req_add_appliance(a, a, c)
            for p in config['setup'][c][a]:
                req_add_program(a, p['programName'], p['averagePower'], p['duration'], p['priority'],
                                p['downgradeable'], p['programmable'], p['interruptible'], p['generatesPower'])
    for task in config['tasks']:
        if task['offset'] > 0:
            req_program_task(task['appliance'], task['program'])
        else:
            req_start_task(task['appliance'], task['program'])

    for r in reqs:
        response = re.request(method=r.method, url=api_url +
                              r.endpoint, json=r.data)
        print(response)
        print(response.content)
