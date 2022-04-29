import csv
import os
import time
import requests

csvreader = csv.reader(open('data.csv'))


URL = "http://localhost:5000/register_value"
data = dict()
data["account"] = "0x61f05811717c746e4dB23a6d787C5e9Ac078C09B"
headers = {'Content-Type': 'application/x-www-form-urlencoded'}

header = []
header = next(csvreader)

print(header)


def get_diff_in_s(current_timestamp, next_timestamp):
    return (float(next_timestamp) - float(current_timestamp))/1000


row = next(csvreader)
print(row)
while True:
    next_row = next(csvreader)
    current_timestamp = row[3]
    next_timestamp = next_row[3]
    while get_diff_in_s(current_timestamp, next_timestamp) < 5.0:
        next_row = next(csvreader)
        next_timestamp = next_row[3]

    print(row)
    active_power = row[1]
    current_timestamp = row[3]
    next_timestamp = next_row[3]
    data['value'] = active_power * 100
    # r = requests.post(url = URL, data = data, headers = headers)
    # print(r.text)
    # print(get_diff_in_s(current_timestamp, next_timestamp))
    time.sleep(get_diff_in_s(current_timestamp, next_timestamp))
    row = next_row
