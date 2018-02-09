import time
from influxdb import InfluxDBClient
import commands

db_host = '10.0.0.1'
port = 8086
user = 'influx'
password = 'password'
dbname = 'active-vpn-connections'
client = InfluxDBClient(db_host, port, user, password, dbname)

# Reads the output from the Perl script that runs when you call "show vnp remote access"
# Pasring CLI output wasn't my first choice, but looking at the Perl there didn't seem to be an easy way to get all this data in one place

def save_influx(line):
    json_body = [
        {
            "measurement": "connection",
            "tags": {
                "host": "router",
            },
            "fields": line
        }
    ]
    print("Write points: {0}".format(json_body))
    client.write_points(json_body)


while True:
    connections = []

    client.drop_database("active-vpn-connections")
    client.create_database("active-vpn-connections")
    output = commands.getstatusoutput('/opt/vyatta/sbin/vyatta-show-ravpn.pl')[1]
    output = output.split('\n')
    if len(output[0])>1: # If only one line is returned, assume no active connections
        del output [0:4] # Remove header rows
        # Assumes that each filed is a fixed width.
        # Looking at the Perl, I believe this is a safe assumption
        for line in output:
            connection = {}
            connection['user'] = line[0:16].replace(" ","")
            connection['type'] = line[16:22].replace(" ","")
            connection['interface'] = line[22:32].replace(" ","")
            connection['ip_address'] = line[32:50].replace(" ","")
            connection['tx_byte'] = line[50:58].replace(" ","")
            connection['rx_byte'] = line[58:65].replace(" ","")
            connection['connection_time'] = line[65:75].replace(" ","")

            connections.append(connection)
        for connection in connections:
            save_influx(connection)
    time.sleep(15)
