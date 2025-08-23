#!/bin/bash
echo "*** run this if you get the *externally-managed-environment* in python when trying to install a package***"
# I tried creating a virtual environment but was getting errors installing sense_hat 

python3 -m pip config set global.break-system-packages true

