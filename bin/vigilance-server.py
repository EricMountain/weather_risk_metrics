#!/usr/bin/python3

from prometheus_client import start_http_server, Gauge
import urllib.request
import random
from datetime import datetime
import re
import time

test = False

risks = ["vent violent", "pluie-inondation", "orages", "inondation", "neige-verglas", "canicule", "grand-froid", "avalanches", "vagues-submersion"]

def getTimeHash():
    d = datetime.now()
    return d.year*365*24*60+d.month*30*24*60+d.day*24*60+d.hour*60+d.minute

def getStream():
    url = "http://www.vigimeteo.com/data/NXFR49_LFPW_.xml?{}".format(getTimeHash())
    stream = None
    if test:
        stream = open('test/jaune-vent-violent+littoral-vagues.xml')
    else:
        try:
            stream = urllib.request.urlopen(url)
        except urllib.error.URLError as e:
            print(f'Error fetching URL: {e}')
            pass
    return stream

def getVigilanceData():
    regex = r'<PHENOMENE departement="(?P<dept>\w+)" phenomene="(?P<risk>\d+)" couleur="(?P<level>\d)" dateDebutEvtTU="(?P<start>\d{14})" dateFinEvtTU="(?P<end>\d{14})"/>'
    pattern = re.compile(regex)
    results = []

    stream = getStream()
    if stream is None: return results

    for line in stream:
        try:
            line = line.decode('utf-8')
        except AttributeError:
            pass
        matches = pattern.match(line)
        if matches:
            data = matches.groupdict()
            results.append(data)
    return results

def latestVigilanceMetrics(gauge=Gauge):
    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    for result in getVigilanceData():
        if result['end'] > now:
            gauge.labels(dept=result['dept'], risk=risks[int(result['risk'])-1], startZ=result['start'], endZ=result['end']).set(int(result['level']))
        else:
            try:
                gauge.remove(dept=result['dept'], risk=risks[int(result['risk'])-1], startZ=result['start'], endZ=result['end'])
            except ValueError as e:
                print(f'Warning: incorrect use of gauge.remove(): {e}')
                pass
            except TypeError:
                # Seems we get this if the label set hadn't already been defined, which can happen if
                # we handle an entry with an early end time before handling lines with end times beyond
                # now
                pass

# Create a metric to track time spent and requests made.
gauge = Gauge('meteorological_risk', 'Weather risk', ['dept', 'risk', 'startZ', 'endZ'])

if __name__ == '__main__':
    # Start up the server to expose the metrics.
    start_http_server(9696)
    while True:
        latestVigilanceMetrics(gauge)
        time.sleep(3600)
