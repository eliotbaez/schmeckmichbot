#!/usr/bin/python3
import os
import privateinfo
import urllib3
import time
import re
import psutil

lockfile = '/tmp/rates_updater.pid'
datafile = '/tmp/exchange_rates.json'

def getTimestamp (json_data):
    return int(re.search(r"\"timestamp\": ([0-9]+)", json_data).group(1)) 

def updateRates ():
    print("Retrieving currency exchange rates...\n")
    http = urllib3.PoolManager()
    rate_data = http.request("GET", "https://openexchangerates.org/api/latest.json?app_id=%s&base=USD" % privateinfo.OpenExchangeRates_appid).data.decode("utf-8")
    with open(datafile, 'w+') as f:
        f.write(rate_data)
    global lastRateRefreshTime
    lastRateRefreshTime = getTimestamp(rate_data) 
    print("Done.\n")
  
if __name__ == '__main__':
    try:
        try:
            with open(lockfile, 'r') as f:
                pid = int(f.read())
            
            if psutil.pid_exists(pid):
                print ('A process with PID %d is already updating rates...' % pid)
                exit(1)
            else:
                print ('PID %d is not running! Continuing...' % pid)
                os.remove(lockfile)
        except FileNotFoundError:
            # lockfile does not yet exist
            pass

        # make the lockfile!
        with open(lockfile, 'x') as f:
            f.write('%d\n' % os.getpid())
        
        # now we do the stuff until something goes wrong
        # initial exchange rate update:
        try:
            with open(datafile) as f:
                rate_data = f.read()
                lastRateRefreshTime = getTimestamp(rate_data)
        except FileNotFoundError:
            updateRates()
        
        while True:
            if time.time() - lastRateRefreshTime > 3600: # 1 hour
                updateRates()
            time.sleep(60)

    except:
        try:
            with open(lockfile, 'r') as f:
                pid = int(f.read())
            if pid == os.getpid():
                # remove lockfile only if this process made it
                os.remove(lockfile)
            else:
                raise
        except OSError:
            pass
        raise