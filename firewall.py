import time
import socket
import urllib2
import json
import os
from influxdb import InfluxDBClient

db_host = '10.0.0.1'
port = 8086
user = 'influx'
password = 'password'
dbname = 'firewall'
client = InfluxDBClient(db_host, port, user, password, dbname)

def save_influx(line):
    json_body = [
        {
            "measurement": "wan-local-blocked",
            "tags": {
                "host": "router",
                #The Grafana map plugin requires the two letter country code to be a tag not a field
                "country": line.get("geo_code")
            },
            "fields": line
        }
    ]
    print("Write points: {0}".format(json_body))
    client.write_points(json_body)


def parse_line(line):
    # I seem to get a lot of entries that seem to be valid trafic coming in on 443/SSL (Netflix/Apple...)
    # I'm filtering them out because I'm not smart enough to know why the firewall is catching them
    if line and line.get("SPT") != '443':
        final_dict = {}
        final_dict['src_ip'] = line.get("SRC")
        final_dict['dest_port'] = line.get("DPT")
        #Do a reverse DNS lookup on the IP to try to get a domain name
        try:
            final_dict['rvs_dns'] = socket.gethostbyaddr(final_dict.get('src_ip'))[0]
        except:
            pass
        # Hit the freegeoip API to get a country / state code for the map
        try:
            response = urllib2.urlopen('http://freegeoip.net/json/'+final_dict.get('src_ip'))
            geo_data = json.load(response)
            final_dict['geo_code'] = str(geo_data.get("country_code"))
            if geo_data.get("country_code") == "US":
                final_dict['state'] = str(geo_data.get("region_code"))
        except:
            pass
        # Try to get a service name from the port number
        try:
            final_dict['service'] = socket.getservbyport(int(final_dict['dest_port']))
        except:
            pass
        save_influx(final_dict)

# Finds lines that match a log entry for the firewall rule "OUTSIDE-LOCAL"
#splits the, into key, value pairs in a dictionary
def process(line):
    final_dict = {}
    if "[OUTSIDE-LOCAL-default-D]" in line:
        line = line.replace("[OUTSIDE-LOCAL-default-D]", "")
        line = line.split(" ")
        for item in line:
            if "=" in item:
                item = item.split("=")
                final_dict[item[0]] = item[1]
        return final_dict

# Keeps track of the rotating log files and feeds new lines into the above
# https://stackoverflow.com/a/43547769
file_name = '/var/log/messages'
seek_end = True
while True:  # handle moved/truncated files by allowing to reopen
    with open(file_name) as f:
        if seek_end:  # reopened files must not seek end
            f.seek(0, 2)
        while True:  # line reading loop
            line = f.readline()
            if not line:
                try:
                    if f.tell() > os.path.getsize(file_name):
                        # rotation occurred (copytruncate/create)
                        f.close()
                        seek_end = False
                        break
                except Exception as e:
                    # rotation occurred but new file still not created
                    print e
                    pass  # wait 1 second and retry
                time.sleep(1)
            parse_line(process(line))
