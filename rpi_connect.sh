#!/bin/bash
# Not used
# tried the approach of running visual code on the laptop to edit the .py files on the RPI while running the python session
# on the headless Rpi5 via ssh. Everything works until I realized that the SenseHat is not available on the Laptop (!!!) so I can't use
# Code to debug.  Reverting to editing directly on the Rpi on the "head-ful" RPI  
sshfs -o uid=$(id -u mauro),gid=$(id -g mauro) mauro@192.168.86.209:/home/mauro/sqrpi/ /home/mauro/sqrpi/remote_dir
