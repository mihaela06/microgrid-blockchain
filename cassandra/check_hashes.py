import os
import subprocess
import datetime
import hashlib

account = os.environ.get("PROSUMER_ACCOUNT")

with open("select_values.cql", "wt") as f:
    f.write("SELECT register_timestamp, hash, value FROM energy_data.registered_values WHERE account='" +
            account + "' ALLOW FILTERING;")


output = subprocess.run(
    "docker run --rm --network cassandra-net -v '" + os.environ.get("PWD") +
    "/cassandra/select_values.cql:/scripts/data.cql' -e CQLSH_HOST=prosumer1_cassandra_1 -e CQLSH_PORT=9042 -e CQLVERSION=3.4.5 nuvo/docker-cqlsh", shell=True, capture_output=True)

output = output.stdout.decode().split('\n')[6:-4]

values = []

for line in output:
    timestamp = line.split('|')[0].strip()
    timestamp = datetime.datetime.strptime(
        timestamp[:-12], '%Y-%m-%d %H:%M:%S').timestamp() + 3 * 3600
    timestamp = int(timestamp * 1000)
    hash = line.split('|')[1].strip()
    value = line.split('|')[2].strip()

    values.append({'timestamp': timestamp, 'hash': hash, 'value': value})

values = sorted(values, key=lambda d: d['timestamp'])
hash_str = "s" * 64

for d in values:
    print("at timestamp: ", d['timestamp'])
    print("hash stored: ", d['hash'])
    concat = str(d['timestamp']) + str(d['value']) + hash_str

    s = hashlib.sha3_256(concat.encode())

    hash_str = s.hexdigest()
    print("hash computed: ", hash_str)

if hash_str == values[-1]['hash']:
    print("Valid data")
    exit(0)
else:
    print("Invalid data")
    exit(1)
