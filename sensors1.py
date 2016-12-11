import sys
import math
import operator
import time
import collections
import serial
import socket
import os
import json

from sense_hat import SenseHat
from numpy import fft,array	
import pylab as pl # sudo apt-get install python-matplotlib

# Initialize constants
G				= 8.81
Pi2 			= 2*math.pi
In_mercury_bar 	= 29.53
Ft_mt       	= 3.28
Display_charts 	= False

# load settings
def format_nmea(payload):
    nmea_str_cs = format(reduce(operator.xor,map(ord,payload),0),'X')
    nmea_str_cs = "0"+nmea_str_cs if len(nmea_str_cs) == 1 else nmea_str_cs
    nmea_str = '$'+payload+"*"+nmea_str_cs+"\r\n"
    return nmea_str

config=json.loads(open('settings.json','r').read())

window 		= config['window'] 		# length of observation cycle (in secs)
sample_rate = config['sample_rate'] # hz
offset_z 	= config['offset_z'] 	# 0.978225246624319 # run calibrate.py to update this value, with sensor board resting as horizontal as possible
ipmux_addr 	= config['ipmux_addr']  # destination of NMEA UDP messages 
ipmux_port	= config['ipmux_port'] 

sample_period 	= 1.0/sample_rate
n = int(window*sample_rate) 		# length of the signal array
min_wave_period = 2  				# secs
max_wave_period = 20 				# secs
min_nyq_freq 	= n/(max_wave_period*int(sample_rate)) 
max_nyq_freq 	= n/(min_wave_period*int(sample_rate)) 

# initialize the sensor and log files
sense = SenseHat()
f=  open("log_sec.csv", "w")
f.write("""time,temperature,pressure,humidity,pitch,roll,wave height,wave period\r\n""")

signal=[0]*n
log = prev_t = t0 = time.time()  
samples = temperature = pressure = humidity = sum_x_sq = sum_y_sq = 0

while True:
    time.sleep(sample_period)
    
    t = time.time()
    dt = t-prev_t
    prev_t = t
      
    # read acceleration from IMU 
    acceleration = sense.get_accelerometer_raw()
    
    # acceleration relative to boat's frame
    x = acceleration['x']
    y = acceleration['y']
    z = acceleration['z']   
    temperature += sense.get_temperature()
    pressure    += sense.get_pressure()
    humidity    += sense.get_humidity()         
    #print('x,y,z values: ',round(x,4),round(y,4),round(z,4))

    # calc vertical non gravitational accel. relative to earth frame
    x_sq = x**2
    y_sq = y**2
    z_sq = z**2
    sum_x_sq += x_sq
    sum_y_sq += y_sq

    z_vert = math.sqrt(x_sq+y_sq+z_sq)
    vert_acc=G*(offset_z-z_vert)

    signal[samples]=vert_acc
    
    log_msg = str(samples)+', '+str(round(t-t0,4))+', '+str(round(vert_acc,4)) 
    #print(log_msg)   
    #f.write(log_msg+'\r\n')

    samples += 1

    if t-log > window:

		pitch, roll = math.degrees(math.asin(math.sqrt(sum_x_sq/samples))), math.degrees(math.asin(math.sqrt(sum_y_sq/samples)))
		temperature, pressure, humidity = temperature / samples, pressure / samples, humidity/samples

		# complete Fast Fourier transform of signal        
		wf=fft.fft(signal)

		# limit analysis to typical wave periods (e.g. between 2 and 20 secs)
		spectrum = wf[min_nyq_freq:max_nyq_freq]

		# replace complex numbers with real numbers
		[ abs(x)/n for x in spectrum ]

		#for i in range(len(spectrum)):
		#        spectrum[i]=abs(spectrum[i])/n*2
		#        #print(str(i)+', '+str(round(spectrum[i],4)) )

		# identiy main frequency component
		avg_value = sum(spectrum)/len(spectrum)
		max_value = max(spectrum)
		max_index = spectrum.tolist().index(max_value)

		if avg_value > 0.005:
			# calculate total accel amplitude for main freq component (attempting to identify lateral a valid bandwidth of main component)
			i=1
			amp_main_freq = max_value
			while max_index+i <= len(spectrum)-1 and max_index-i >= 0 and (spectrum[max_index+i]>avg_value or spectrum[max_index-i]>avg_value):
				amp_main_freq += spectrum[max_index+i]  if spectrum[max_index+i] > avg_value else 0
				amp_main_freq += spectrum[max_index-i]  if spectrum[max_index-i] > avg_value else 0
				i+=1

			# period in secs of main component
			main_period = float(n)/(float(max_index+min_nyq_freq)*sample_rate)
		
			#estimate average wave height for main freq component
			estimated_wave_height = 2*amp_main_freq/((Pi2/main_period)**2) # accel amplitude / (2*Pi/T)^2 (=double sine integral constant) * 2 (=crest to trough)
		else:
			estimated_wave_height=0
			main_period=0

		#print('main period: '+str(round(main_period,4))+'sec., estimated wave height: '+str(round(estimated_wave_height,4))+' mt.' )
	
		if Display_charts:
			freqs=fft.fftfreq(n)  # identify corrsesponding frequency values for x axis array (cycles/sample_units)
		
			freqs = [x*sample_rate for x in freqs] # convert to hertz

			pl.plot(freqs[min_nyq_freq:max_nyq_freq], spectrum)
			pl.show()
			pl.plot(signal)
			pl.show()
			clean_signal=fft.ifft(wf) 
			clean_signal = [x * n/2 for x in clean_signal]
			pl.plot(clean_signal[0:n/2])
			pl.show()

		# write variables to log file
		log_str = str(t)+','+str(round(temperature,3))+','+str(round(pressure,3))+','+str(round(humidity,3))+','+str(round(pitch,4))+','\
			+str(round(roll,4)) +','+str(round(estimated_wave_height,4))+','+str(round(main_period,4))  
		print(log_str)
		f.write(log_str+"\r\n")
		f.flush()


		# send variables to NMEA IP address (using obsolete NMEA deprecated MDA for backward compativility on OpenCPN)
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		payload = "RPMDA,"+str(round(pressure/1000*In_mercury_bar,4))+",I,"+str(round(pressure/1000,4))+',B,'+str(round(temperature,4))+',C,'+str(round(humidity,4))+',,,,,,,,,,,,,'
		nmea_str = format_nmea(payload) 
		print(nmea_str)
		sock.sendto( nmea_str, (ipmux_addr, ipmux_port))
        
        # send pitch and roll (rms values) and wave height to NMEA
		payload = "RPXDR,A,"+str(round(pitch,4))+",D,rpi-pitch,A,"+str(round(roll,4))+",D,rpi-roll"   
		nmea_str = format_nmea(payload) 
		print(nmea_str)
		sock.sendto( nmea_str, (ipmux_addr, ipmux_port))

		payload = "RPMWH,"+str(round(estimated_wave_height*Ft_mt,4))+",F,"+str(round(estimated_wave_height,4))+",M"
		nmea_str = format_nmea(payload) 
		print(nmea_str)
		sock.sendto( nmea_str, (ipmux_addr, ipmux_port))

		# reset variables for new loop
		signal = [0 for x in signal] 
		log = t
		samples = sum_x_sq = sum_y_sq = temperature = pressure = humidity = 0  

f.close()

