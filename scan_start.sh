#!/bin/bash

# Launch the first Python program with nohup in the background
nohup python3 sensorscan.py > sensorscan.log 2>&1 &

# Launch the second Python program with nohup in the background
nohup python3 udp_read.py  > udp_read.log 2>&1 &

echo "Both Python programs launched in the background."
