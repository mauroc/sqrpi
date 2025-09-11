#!/bin/bash

#  ********************************** this was added to systemd autostart on Rpi4 ********************************************
#  check with 'systemctl status jupyterlab'

# allow all origins and all ips in the config file when installing on a new machine in order for this server to be accessed on the lan
# also open port 8889 on UFW. 
# sudo ufw enable 8889
# see meail note

#jupyter notebook --allow-root --no-browser --port=8889  # notebook classic is still installed so this shourl run if needed
jupyter lab --allow-root --no-browser --ip=0.0.0.0 --port=8889
