-- Create a keyspace
CREATE KEYSPACE IF NOT EXISTS energy_data WITH REPLICATION = { 'class' : 'SimpleStrategy', 'replication_factor' : '1' };

-- Create a table
CREATE TABLE IF NOT EXISTS energy_data.registered_values (
account             TEXT,
value               INT,
register_timestamp  TIMESTAMP,
hash                TEXT,
PRIMARY KEY ((register_timestamp, account))
);