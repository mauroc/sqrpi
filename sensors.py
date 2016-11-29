import sys
import serial
import math
import operator
import time
import socket
import os
import math
from sense_hat import SenseHat

GPS_IP = "127.0.0.1"
GPS_PORT = 5005

MON_IP = "127.0.0.4"
MON_PORT = 5005

sense = SenseHat()
f= open("log_sec.txt". "w")
f.write("time,temperature,pressure,humidity,x_acc,y_acc,z_acc")
x_acc = y_acc = z_acc = temperature = pressure = humidity = 0  

while True
    hack = time.time()
    samples += 1
    
    temperature += sense.get_temperature()
    humidity    += sense.get_humidity()
    pressure    += sense.get_pressure()

    z_acc += z**2
    y_acc += y**2
    x_acc += x**2
    
    if hack-log > 10
        x_acc, y_acc, z_acc = math.sqrt(x_acc/samples), math.sqrt(y_acc/samples), math.sqrt(z_acc/samples)        
        temperature, pressure, humidity = temperature / samples, pressure / samples, humidity/samples
        
        f.write(str(time.time()) + ',' + str(temperature) + ',' + str(pressure)  + ',' + str(humidity) + ',' + str(x_acc) + ',' + str(y_acc) + ',' + str(z_acc)  )
        log = hack
        
        samples, x_acc = y_acc = z_acc = temperature = pressure = humidity = 0  
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        nmea_str = "$SQPSR,"+str(temperature)+","+str(pressure)+''
        nmea_str_cs = format(reduce(operator.xor,map(ord,nmea_str),0),'X')
        nmea_str_cs = "0"+nmea_str_cs if len(nmea_str_cs) == 1 else nmea_str_cs
        nmea_str += "*"+nmea_str_cs+"\r\n"
        sock.sendto( nmea_str, (GPS_IP, GPS_PORT))
        
        