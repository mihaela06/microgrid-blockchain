import json
import os
import random
from datetime import datetime

import pika
from cassandra.cluster import Cluster

cassandra_nodes = []

for i in range(int(os.environ.get("NODES_NO"))):
    cassandra_nodes.append(f"prosumer{i+1}_cassandra_1")

print(os.environ.get("RABBIT_MQ_HOST"))

connection = pika.BlockingConnection(pika.ConnectionParameters(host=os.environ.get('RABBIT_MQ_HOST')))
channel = connection.channel()

def callback(ch, method, properties, body):
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' Processing...')

    body = body.decode()
    print(body)
    data = body.split(';')

    cluster = Cluster(cassandra_nodes, port=9042)
    session = cluster.connect('energy_data', wait_for_all_pools=True)
    session.execute('USE energy_data')

    query = "insert into registered_values (register_timestamp, account, hash, value) VALUES (" + \
        str(data[0]) + \
        ", '" + str(data[1]) + "', '" + \
        str(data[2]) + "', " + str(data[3]) + ")"
    print(query)
    session.execute(query)

    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' Processed !')


channel.basic_consume(queue='data_queue',
                      on_message_callback=callback, auto_ack=True)

print(' [*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()

