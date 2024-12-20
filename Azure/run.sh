#!/bin/bash

cd /home/azureuser/projekt || exit
source venv/bin/activate
nohup python app.py > log_app.log 2>&1 &
sleep 5
nohup python mqtt_mail.py > log_mqtt.log 2>&1 &

