#!/bin/bash

sleep 15
cd /home/rpi/projekt || exit
source venv/bin/activate
nohup python mqtt_relay.py > log_app.log 2>&1 &
