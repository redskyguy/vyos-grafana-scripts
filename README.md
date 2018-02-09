# Python Scripts for Pushing VyOS data into InfluxDB/Grafana

Note, all of these scrips require the InfluxDB Python Connector

https://github.com/influxdata/influxdb-python

However, the connector doesn't work with the version of Python that comes on the current release of VyOS (Python 2.6). To get it working, in line_protocol.py, edit lines 69 & 77 to read

`return "\"{0}\"".format(value`
