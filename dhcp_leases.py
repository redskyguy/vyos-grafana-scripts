import time
from influxdb import InfluxDBClient

db_host = '10.0.0.1'
port = 8086
user = 'influx'
password = 'password'
dbname = 'dhcp-leases'
client = InfluxDBClient(db_host, port, user, password, dbname)

# Reads the /config/dhcpd.leases file

def save_influx(line):
    json_body = [
        {
            "measurement": "active-lease",
            "tags": {
                "host": "router",
            },
            "fields": line
        }
    ]
    print("Write points: {0}".format(json_body))
    client.write_points(json_body)

while True:
    leases = open('/config/dhcpd.leases','r')
    leases_final_dict = {}
    for line in leases:
        # Entry Starts with a "{"
        if "{" in line:
            lease_dict = {}
            lease_dict['ip'] = line.replace("lease ", "").replace(" {", "")[:-1]

        # Find Hostname and clean the data
        if "client-hostname" in line:
            lease_dict['hostname'] = line.replace(" client-hostname ", "").replace(" ", "").replace('"',"").replace(";","")[:-1]

        # Find MAC and clean the data
        if "hardware ethernet" in line:
            lease_dict['mac'] = line.replace(" hardware ethernet ", "").replace(" ", "").replace('"',"").replace(";","")[:-1]

        # I only care about active leases right now...
        if "binding state active" in line:
            lease_dict['active'] = True

        # Find the lease end time and clean the data
        if "ends" in line:
            lease_dict['expires'] = line.replace(" ends ", "").replace("", "").replace('"',"").replace(";","")[3:-1]

        # End of Entry
        if "}" in line:
            # The dhcpd.leases can sometimes contain multiple declaration for the same lease
            # This keeps track of them by the ip/mac and makes sure only the last entry is saved
            # Info here: https://linux.die.net/man/5/dhcpd.leases
            leases_final_dict[lease_dict['ip']+lease_dict['mac']] = lease_dict
            print lease_dict
    leases.close()
    client.drop_database("dhcp-leases")
    client.create_database("dhcp-leases")
    for lease in leases_final_dict.values():
        if lease.get('active'):
            save_influx(lease)
    time.sleep(30)
