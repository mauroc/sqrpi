#!/bin/bash

# allow all origins and all ips in the config file when installing on a new machine in order for this server to be accessed on the lan
# also open port 8889 on UFW. 
# sudo ufw enable 8889
# see meail note
jupyter notebook --allow-root --no-browser --port=8889
