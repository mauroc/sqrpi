# TODO some sentences (true wind) report 0s, which alter the averages. Find a way to eliminate those variables from the .mean()

import socket
import pynmea2 as nmea
import json
import time
from collections import defaultdict
import numpy as np
import sys
import math
import pdb

config=json.loads(open('settings.json','r').read())
UDP_IP 	= config['ipmux_addr']  # destination of NMEA UDP messages 
UDP_PORT	= config['ipmux_port'] 
Rec_interval = 60 # secs

print(f"UDP Receiver listening on {UDP_IP}:{UDP_PORT}")

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind the socket to the specified address and port
sock.bind((UDP_IP, UDP_PORT))


rec={}

def gll(msg):
    lat = float(msg.lat)/100 if msg.lat_dir == "N"  else -float(msg.lat)/100
    lon = float(msg.lon)/100 if msg.lon_dir == "E"  else -float(msg.lon)/100
    rec['lat'] = lat # we only record the last latitude
    rec['lon'] = lon # we only record the last longitude
    return 

def hdg(msg):
    # add the heading to the end of the headings array in rec
    rec["heading_ar"] = np.append(rec.get("heading_ar", np.empty(0) ), float(msg.heading))

def hdm(msg):
    # magnetic heading
    rec["mag_heading_ar"] = np.append(rec.get("mag_heading_ar", np.empty(0) ), float(msg.heading))

def hdt(msg):
    # magnetic heading
    rec["true_heading_ar"] = np.append(rec.get("true_heading_ar", np.empty(0) ), float(msg.heading))

def vhw(msg):
    # water speed and heading
    rec["true_heading_ar"] = np.append(rec.get("true_heading_ar", np.empty(0) ), float(msg.water_speed_knots))

def mwv(msg):
    # Wind speed and Angle
    rec["wind_angle_ar"] = np.append(rec.get("wind_angle_ar", np.empty(0) ), float(msg.wind_angle))
    rec["wind_speed_ar"] = np.append(rec.get("wind_speed_ar", np.empty(0) ), float(msg.wind_speed))
    
def dbt(msg):
    # Depth
    rec["depth_feet_ar"] = np.append(rec.get("depth_feet_ar", np.empty(0) ), float(msg.depth_feet))
    rec["depth_meters_ar"] = np.append(rec.get("depth_meters_ar", np.empty(0) ), float(msg.depth_meters))

def vtg(msg):
    # Course Over Ground and Ground Speed
    rec["spd_over_grnd_kts_ar"] = np.append(rec.get("spd_over_grnd_kts_ar", np.empty(0) ), float(msg.spd_over_grnd_kts))
    rec["true_track_ar"] = np.append(rec.get("true_track_ar", np.empty(0) ), float(msg.true_track))

def mtw(msg):
    # Mean temperature of water
    rec["temperature_ar"] = np.append(rec.get("temperature_ar", np.empty(0) ), float(msg.temperature))

def ang_mean(angles, degrees=True):
    """
    Compute the average of a list of angles.
    
    :param angles: list of angles (degrees if degrees=True, else radians)
    :param degrees: whether input/output are in degrees
    :return: average angle
    """
    if degrees:
        # convert to radians
        angles = [math.radians(a) for a in angles]
    
    # Step 1 & 2: mean x and y components
    x = sum(math.cos(a) for a in angles) / len(angles)
    y = sum(math.sin(a) for a in angles) / len(angles)
    
    # Step 3: back to angle
    avg = math.atan2(y, x)
    
    if degrees:
        avg = math.degrees(avg)
    
    # Normalize to [0, 360) or [0, 2π)
    if avg < 0:
        avg += 360 if degrees else 2*math.pi
    
    return avg

def read_file():
    file = open('nmealogs.txt', encoding='utf-8')
    
    for line in file.readlines():
        try:
            msg = nmea.parse(line)
            print(repr(msg))
        except nmea.ParseError as e:
            print('Parse error: {}'.format(e))
            continue

current_module = sys.modules[__name__]
file = open('nmealogs.txt', encoding='utf-8')

t0 = time.time()
#while True:

#pdb.set_trace()
for line in file.readlines():
    #create record object
    # Receive data (up to 1024 bytes) and sender's address
    #data,addr = sock.recvfrom(1024)
    message = nmea.parse(line)

    elapsed = time.time() - t0

    #if elapsed time > Rec_interval
    #   calculate averages 
    #   save rec to CSV
    #   reset rec
    #   reset timer
    #   continue

    # Decode the received bytes to a string (assuming UTF-8 encoding)
    #message = nmea.parse(data.decode('utf-8'))
    
    #print(f"Decoded message: '{message}' from {addr}")
    print(f"Decoded message: '{message}' from file")

    msg_type = message.sentence_type.lower()

    if hasattr(current_module, msg_type):
        func_name = getattr(current_module, msg_type)
        func_name(message)
    else:
        print('undefined message type: ', msg_type)
    
    #print(rec)

header = 'lat,lon,sog_kts,cog,hdg,hdg_mag,hdg_true,wind_sp_kts,wind_angle,depth_ft,depth_m,water_temp_c'

print(header)

rec_str  = f'{round(rec["lat"],3)},{round(rec["lon"],3)},' 
rec_str += f'{round(rec["spd_over_grnd_kts_ar"].mean(),3)},{round(ang_mean(rec["true_track_ar"])) },'
rec_str += f'{round(ang_mean(rec["heading_ar"]))},{round(ang_mean(rec["mag_heading_ar"]))},{round(ang_mean(rec["true_heading_ar"]))},'
rec_str += f'{round(rec["wind_speed_ar"].mean(),2)},{round(ang_mean(rec["wind_angle_ar"]))},'
rec_str += f'{round(rec["depth_feet_ar"].mean(),2)},{round(rec["depth_meters_ar"].mean(),2)},'
rec_str += f'{round(rec["temperature_ar"].mean())}'



print(rec_str)