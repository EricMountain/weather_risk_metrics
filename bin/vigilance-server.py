#!/usr/bin/python3

from prometheus_client import start_http_server, Gauge
import urllib.request
import random
import datetime
import re
import time

test = False

risks = ["vent violent", "pluie-innondation", "orages", "innondation", "neige-verglas", "canicule", "grand-froid", "avalanches", "vagues-submersion"]

def getTimeHash():
    d = datetime.datetime.now()
    return d.year*365*24*60+d.month*30*24*60+d.day*24*60+d.hour*60+d.minute

def getVigilanceData():
    url = "http://www.vigimeteo.com/data/NXFR49_LFPW_.xml?{}".format(getTimeHash())
    if test:
        stream = open('test/jaune-vent-violent+littoral-vagues.xml')
    else:
        stream = urllib.request.urlopen(url)
    regex = r'<PHENOMENE departement="(?P<dept>\w+)" phenomene="(?P<risk>\d+)" couleur="(?P<level>\d)" dateDebutEvtTU="(?P<start>\d{14})" dateFinEvtTU="(?P<end>\d{14})"/>'
    pattern = re.compile(regex)
    results = []
    for line in stream:
        try:
            line = line.decode('utf-8')
        except AttributeError:
            pass
        matches = pattern.match(line)
        if matches:
            results.append(matches.groupdict())
    return results

def latestVigilanceMetrics(gauge=Gauge):
    for result in getVigilanceData():
        gauge.labels(dept=result['dept'], risk=risks[int(result['risk'])-1], startZ=result['start'], endZ=result['end']).set(int(result['level']))

# Create a metric to track time spent and requests made.
gauge = Gauge('meteorological_risk', 'Weather risk', ['dept', 'risk', 'startZ', 'endZ'])

if __name__ == '__main__':
    # Start up the server to expose the metrics.
    start_http_server(9696)
    while True:
        latestVigilanceMetrics(gauge)
        time.sleep(3600)
