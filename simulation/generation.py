import os
import pandas as pd
import datetime
import calendar
import matplotlib.pyplot as plt

THRESHOLD = os.getenv('THRESHOLD')
MIDNIGHT_TIMESTAMP = os.getenv('MIDNIGHT_TIMESTAMP')  # 15.04.2019
RANDOM_SEED = os.getenv('RANDOM_SEED')
PROSUMER_NO = os.getenv('PROSUMER_NO')
BACKGROUND_FOLDER = "background"

THRESHOLD = 0.1
MIDNIGHT_TIMESTAMP = 1555286400  # 15.04.2019
RANDOM_SEED = 42
PROSUMER_NO = 10

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

plt.plot(background_df.value)
