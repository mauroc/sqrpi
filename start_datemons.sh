#!/bin/bash

#nohup python3  udp_read.py >/dev/null &
systemctl restart udp_read.service

#nohup python3 sensorscan.py >/dev/null &
systemctl restart sensorscan.service
