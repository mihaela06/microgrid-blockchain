import os

START_TIMESTAMP = int(os.environ.get('START_TIMESTAMP'))
FREQ = 10  # in seconds
THRESHOLD = 0.1
RANDOM_SEED = 42
PROSUMER_NO = os.environ.get('PROSUMER_ID')
BATCH_SIZE = 12
if os.environ.get("DYNAMIC"):
    DYNAMIC = True
else:
    DYNAMIC = False

# TODO from os.environ
# TODO generation random or from preconfigured configuration of appliances