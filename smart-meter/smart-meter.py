import csv
import os
import time
import requests

csvreader = csv.reader(open('data.csv'))


URL = "http://host_placeholder:5000/register_value"
data = dict()
headers = {'Content-Type': 'application/x-www-form-urlencoded'}

header = []
header = next(csvreader)

print(header)


def get_diff_in_s(current_timestamp, next_timestamp):
    return (float(next_timestamp) - float(current_timestamp))/1000


row = next(csvreader)
print(row)
while True:
    try:
        next_row = next(csvreader)
        current_timestamp = row[3]
        next_timestamp = next_row[3]
        while get_diff_in_s(current_timestamp, next_timestamp) < 10.0:
            next_row = next(csvreader)
            next_timestamp = next_row[3]

        print("new row", row)
        active_power = row[1]
        current_timestamp = row[3]
        next_timestamp = next_row[3]
        data['value'] = int(float(active_power) * 100)
        r = requests.post(url = URL, data = data, headers = headers)
        print("result", r.text)
        # print(get_diff_in_s(current_timestamp, next_timestamp))
        time.sleep(get_diff_in_s(current_timestamp, next_timestamp))
        row = next_row
    except Exception as err:
        print(err)
        time.sleep(10)
