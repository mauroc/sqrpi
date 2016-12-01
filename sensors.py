# todo: correct with at-rest g coeffs 
import sys
import serial
import math
import operator
import time
import socket
import os
import math
import collections
from sense_hat import SenseHat

GPS_IP = "127.0.0.1"
GPS_PORT = 5005
MON_IP = "127.0.0.4"
MON_PORT = 5005
G=9.81


sense = SenseHat()
#os.remove('log_sec.txt')
f= open("log_sec.txt", "w")
f.write("time,temperature,pressure,humidity,pitch,roll,wave ht.\r\n")
samples = sum_x_sq = sum_y_sq = temperature = pressure = humidity = log = height = max_h = min_h = sum_h = sum_whts = crest = trough = avg_whts = 0
prev_t = time.time()  
hts    = collections.deque([0])
whts = collections.deque([0])

while True:
    time.sleep(.2)
    
    t = time.time()
    dt = t-prev_t
    prev_t = t
    samples += 1
    
    # read environmental values from sensor and integrate them (to calculete RMS)
    temperature += sense.get_temperature()
    pressure    += sense.get_pressure()
    humidity    += sense.get_humidity()
    
    # read acceleration from IMU 
    acceleration = sense.get_accelerometer_raw()
    
    # acceleration relative to boat's frame
    x = acceleration['x']
    y = acceleration['y']
    z = acceleration['z']            
    #print('x,y,z values: ',round(x,4),round(y,4),round(z,4))
    
    # calculate squares of accel. for pitch, roll and vertical. Used to calculate RMS values      	
    x_sq = x**2
    y_sq = y**2
    z_sq = z**2
    sum_x_sq += x_sq
    sum_y_sq += y_sq
    #print('squares: ',round(x_sq,4), round(y_sq,4), round(z_sq,4))
	
    # vertical non gravitational accel. relative to earth frame
    z_vert = math.sqrt(x_sq+y_sq+z_sq)-0.9718511
    #print('z_vert, dd', z_vert, dt)

    # double-integrate vert. accel. to calculate wave height
    delta = G*z_vert*dt*dt if abs(z_vert) > 0.01 else 0
    height += delta 
    print("delta, height:   "+str(delta)+', '+str(height))
    
    # crest or trough of wave?
    if (height < hts[-1] and crest  == 0): 
        crest = hts[-1]
    if (height > hts[-1] and trough == 0): 
        trough = hts[-1]
    
    # collect wave height and calculate moving average     
    n=10
    if crest and trough:
        wht =crest-trough
        whts.append(wht)
        drop = whts.popleft() if len(whts)>n else 0
        sum_whts += wht-drop
        avg_whts = sum_whts/n
        crest = trough = 0
        print('avg wave height:    '+str(avg_whts))
    
    # caclulate moving average of last n height samples to filter out high freq waves
    n=10
    hts.append(height)
    drop = hts.popleft() if len(hts)>n else 0
    sum_h += height-drop
    mav_h = sum_h/n


    if t-log > 5:
        pitch, roll = math.sqrt(sum_x_sq/samples), math.sqrt(sum_y_sq/samples)        
        temperature, pressure, humidity = temperature / samples, pressure / samples, humidity/samples
        
        log_str = str(t)+','+str(round(temperature,3))+','+str(round(pressure,3))+','+str(round(humidity,3))+','+str(round(pitch,4))+','+str(round(roll,4))+','+str(round(avg_whts,4)) 

        print(log_str)
        f.write(log_str+"\r\n")
	 
        log = t
        
        samples = sum_x_sq = sum_y_sq = crest = trough = 0  
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        nmea_str = "$SQPSR,"+str(temperature)+","+str(pressure)+''
        nmea_str_cs = format(reduce(operator.xor,map(ord,nmea_str),0),'X')
        nmea_str_cs = "0"+nmea_str_cs if len(nmea_str_cs) == 1 else nmea_str_cs
        nmea_str += "*"+nmea_str_cs+"\r\n"
        #sock.sendto( nmea_str, (GPS_IP, GPS_PORT))
        
        
f.close()
