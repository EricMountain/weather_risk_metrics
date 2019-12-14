#!/usr/bin/python3

from prometheus_client import start_http_server, Gauge
import urllib.request
import random
from datetime import datetime
import re
import time

test = False
risks = ["vent violent", "pluie-inondation", "orages", "inondation", "neige-verglas", "canicule", "grand-froid", "avalanches", "vagues-submersion"]

# Maps a (dept, risk, startZ, endZ) tuple to the round in which it was last set
cache = {}

# Create metrics to track time spent and requests made.
gauge_full = Gauge('meteorological_risk_full', 'Weather risk', ['dept', 'risk', 'startZ', 'endZ'])
gauge = Gauge('meteorological_risk', 'Weather risk', ['dept', 'risk'])

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

def latestVigilanceMetrics(gauge=Gauge, cacheRound=int):
    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    deptRiskLevelMap = dict()
    for result in getVigilanceData():
        if result['end'] > now:
            level = int(result['level'])
        else:
            level = 0

        risk = risks[int(result['risk'])-1]
        key = (result['dept'], risk, result['start'], result['end'])
        cache[key] = cacheRound

        dept = result['dept']
        gauge_full.labels(dept=dept, risk=risk, startZ=result['start'], endZ=result['end']).set(level)

        if (dept, risk) not in deptRiskLevelMap:
            deptRiskLevelMap[(dept, risk)] = level
            gauge.labels(dept=dept, risk=risk).set(level)
        elif level > deptRiskLevelMap[(dept, risk)]:
            deptRiskLevelMap[(dept, risk)] = level
            gauge.labels(dept=dept, risk=risk).set(level)
            
        print(f'{key!r} --> {level}, added to cache with round {cacheRound}')

def checkDeadCacheEntries(gauge=Gauge, cacheRound=int):
    '''
    Checks if a particular combination has been dropped from the output
    produced by vigimeteo. We need to zero these entries else they will stay stuck
    at whatever their last value was.
    '''

    for key, value in list(cache.items()):
        if value != cacheRound:
            print(f'{key!r} --> {0}, deleting cache entry')
            gauge.labels(dept=key[0], risk=key[1], startZ=key[2], endZ=key[3]).set(0)
            del cache[key]

if __name__ == '__main__':
    # Start up the server to expose the metrics.
    start_http_server(9696)
    cacheRound = 0
    while True:
        cacheRound = 1 - cacheRound
        print(f'Starting new round… (index {cacheRound})')
        latestVigilanceMetrics(gauge, cacheRound)
        checkDeadCacheEntries(gauge, cacheRound)
        print('Round completed.')
        time.sleep(3600)
