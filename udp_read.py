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
import os

config=json.loads(open('settings.json','r').read())
UDP_IP 	= config['ipmux_addr']  # destination of NMEA UDP messages 
UDP_PORT	= int(config['ipmux_port']) 
Rec_interval = 60 # secs
Log_filename    = "log_nmea.csv"
File_header = """timestamp,lat,lon,sog_kts,cog,hdg,hdg_mag,hdg_true,wind_sp_kts,wind_angle,depth_ft,depth_m,water_temp_c\r\n"""
Current_module = sys.modules[__name__]

print(f"UDP Receiver listening on {UDP_IP}:{UDP_PORT}")

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
# Bind the socket to the specified address and port
sock.bind(("", UDP_PORT))

#rec={}

rec = defaultdict(lambda: 0)

def gll(msg):
    lat_enc = float(msg.lat)/100 if msg.lat_dir == "N"  else -float(msg.lat)/100
    lon_enc = float(msg.lon)/100 if msg.lon_dir == "E"  else -float(msg.lon)/100
    lat = int(lat_enc) + (lat_enc % int(lat_enc))/0.6
    lon = int(lon_enc) + (lon_enc % int(lon_enc))/0.6
    rec['lat'] = lat # we only record the last latitude
    rec['lon'] = lon # we only record the last longitude
    return 

def hdg(msg):
    # add the heading to the end of the headings array in rec
    rec["heading_ar"]  = np.append(rec.get("heading_ar", np.empty(0) ), float(msg.heading))

def hdm(msg):
    # magnetic heading
    rec["mag_heading_ar"]  = np.append(rec.get("mag_heading_ar", np.empty(0) ), float(msg.heading))

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
    
    # Step 1 & 2: mean x and y 
    angles = [item for item in angles if item != 0] # HDT produces a lot of 0 readings 
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

def ang_mean_np(angles, degrees=True):
    """
    Compute the average of a list/array of angles using NumPy.
    
    :param angles: array-like, angles (degrees if degrees=True, else radians)
    :param degrees: whether input/output are in degrees
    :return: average angle
    """
    angles = np.asarray(angles)
    
    if degrees:
        # convert to radians
        angles = np.deg2rad(angles)
    
    # Step 1 & 2: mean x and y components
    x = np.mean(np.cos(angles))
    y = np.mean(np.sin(angles))
    
    # Step 3: back to angle
    avg = np.arctan2(y, x)
    
    if degrees:
        avg = np.rad2deg(avg)
    
    # Normalize to [0, 360) or [0, 2π)
    if avg < 0:
        avg += 360 if degrees else 2*np.pi
    
    return avg
    
def read_file():
    file = open('nmealogs.txt', encoding='utf-8')
    
    for line in file.readlines():
        try:
            msg = nmea.parse(line)
        except nmea.ParseError as e:
            print('Parse error: {}'.format(e))
            continue

#pdb.set_trace()
# initialize log file
print(File_header)
append_data = os.path.exists(Log_filename)
f =  open(Log_filename, "a") # append to exising file
if not append_data:
	f.write(File_header)

#file = open('vdr_20250914.txt', encoding='utf-8') # debug mode: use to test messages from file
t0 = time.time()

while True:
#for data_str in file.readlines(): #debug mode
    
    # Receive data (up to 1024 bytes) and sender's address
    data,addr = sock.recvfrom(1024)    # comment in debug mode
    data_str=data.decode('utf-8')      # comment in debug mode

    if data_str[0]=="!":
        continue

    # Decode the received bytes to a string (assuming UTF-8 encoding)
    try:
        message = nmea.parse(data_str)
        print(f"Parsed message: {message}")
    except:
        print("Parsing Error ******************", data_str )

    msg_type = message.sentence_type.lower()

    if hasattr(Current_module, msg_type):
        # call the decoding function corresponding to the message_type
        decoder = getattr(Current_module, msg_type)
        try:
           decoder(message)
        except:
           print("Decoding Error *********************")
    else:
        print('undefined message type: ', msg_type)
    
    elapsed = time.time() - t0
    if elapsed > Rec_interval:
        # Once every Rec_interval (e.g. 1 minute), create the CSV record
        try:
            rec_str  = f'{round(time.time(),3)},'
            rec_str += f'{round(rec["lat"],5)},{round(rec["lon"],5)},' 
            rec_str += f'{round(rec["spd_over_grnd_kts_ar"].mean(),3)},{round(ang_mean(rec["true_track_ar"])) },'
            rec_str += f'{round(ang_mean(rec["heading_ar"]))},{round(ang_mean(rec["mag_heading_ar"]))},{round(ang_mean(rec["true_heading_ar"]))},'
            rec_str += f'{round(rec["wind_speed_ar"].mean(),2)},{round(ang_mean(rec["wind_angle_ar"]))},'
            rec_str += f'{round(rec["depth_feet_ar"].mean(),2)},{round( rec["depth_meters_ar"  ].mean(),2)},'
            rec_str += f'{round(rec["temperature_ar"].mean())}'
        except:
            print("Output error *********************")
        # save record to CSV file
        print(rec_str)
        f.write(rec_str+"\r\n")
        f.flush()

        #rec={}
        rec.clear()
        t0 = time.time()

#print("true heading", rec["true_heading_ar"], ang_mean(rec["true_heading_ar"]))
#print("mag heading", rec["mag_heading_ar"], ang_mean(rec["mag_heading_ar"]))


