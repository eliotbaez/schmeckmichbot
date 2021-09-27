#!/bin/sh

# A helper script to cleanly stop the rate updater process
cat /tmp/rates_updater.pid | xargs kill && rm /tmp/rates_updater.pid