import socket
import pynmea2 as nmea
import json
import time
from collections import defaultdict

config=json.loads(open('settings.json','r').read())
UDP_IP 	= config['ipmux_addr']  # destination of NMEA UDP messages 
UDP_PORT	= config['ipmux_port'] 
Rec_interval = 60 # secs

print(f"UDP Receiver listening on {UDP_IP}:{UDP_PORT}")

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind the socket to the specified address and port
sock.bind((UDP_IP, UDP_PORT))



s1 ="$IIHDG,116.0,,,0,*7F"
s2 ="$IIHDM,116.0,M*24"
s3 ="$IIHDT,116.0,T*24"
s4 ="$IIMWV,136.5,R,3.2,N,A*3D"
s5 ="$IIDBT,11.7,f,3.57,M,1.95,F*2A"
s6 ="$IIMTW,0.2,C*21"

s7 ="$IIGLL,3751.578,N,12228.915,W,005440,A,A*4B"
s8 ="$IIVWR,136.5,R,3.2,N,1.7,M,5.9,K*43"
s9 ="$GPGGA,005417.00,3751.57887,N,12228.91201,W,2,10,1.28,-4.1,M,-29.7,M,,0000*4C"
s10="$IIBWC,005410,,,,0.0,T,0.0,M,0.00,N,,A*5E"

def gll(msg):
    lat = msg["lat"] if msg["lat_dir"] == "N"  else -msg["lat"]
    lon = msg["lon"] if msg["lon_dir"] == "E"  else -msg["lon_dir"]
    rec['lat'] = lat # we only record the last latitude
    rec['lon'] = lat # we only record the last longitude
    return 

def hdg(msg):
    rec["hdg_count"] = counter = rec.get("hdg_count",0)+1
    rec["heading"] = (rec.get("heading", 0)*(counter-1) + msg["heading"])/counter
    return


def read_file():
    file = open('nmealogs.txt', encoding='utf-8')
    
    for line in file.readlines():
        try:
            msg = nmea.parse(line)
            print(repr(msg))
        except nmea.ParseError as e:
            print('Parse error: {}'.format(e))
            continue

rec = {} #or defaultdict(int)
t0 = time.time()
while True:
    #create record object
    # Receive data (up to 1024 bytes) and sender's address
    data,addr = sock.recvfrom(1024)
    elapsed = time.time() - t0

    #if elapsed time > Rec_interval
    #   save rec to CSV
    #   reset rec
    #   reset timer
    #   continue

    # Decode the received bytes to a string (assuming UTF-8 encoding)
    message = nmea.parse(data.decode('utf-8'))
    print(f"Decoded message: '{message}' from {addr}")
    msg_type = message.sentence_type 
    if msg_type == 'GLL':
        # update record object with relevant attributes (avg, min, max etc)
        gll(message)
    elif msg_type == 'HDG':
        hdg(message)
        print()
    else:
        print()

