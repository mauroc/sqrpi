import sys
import math
import operator
import time
import datetime
import collections
import serial
import socket
import os
import json
import random
from functools import reduce
#import operator

from sense_hat import SenseHat
from numpy import fft,array
import pylab as pl # sudo apt-get install python-matplotlib

# Initialize constants
#G				= 8.81 found this at this value and suspect it was a typo?
G				= 9.81
Pi2 			= 2*math.pi
In_mercury_bar 	= 29.53
Ft_mt       	= 3.28
Display_charts 	= True
Log_filename    = "log_sec.csv"
File_header		= """timestamp,date,time,temperature,pressure,humidity,avg_pitch_,avg_roll,wave height,wave period\r\n"""

# functions
def format_nmea(payload):
    nmea_str_cs = format(reduce(operator.xor,map(ord,payload),0),'X')
    nmea_str_cs = "0"+nmea_str_cs if len(nmea_str_cs) == 1 else nmea_str_cs
    nmea_str = '$'+payload+"*"+nmea_str_cs+"\r\n"
    return nmea_str

def send_to_nmea(pressure, temperature, humidity, pitch, roll, sig_wave_height):
	# send variables to NMEA IP address (using obsolete NMEA deprecated MDA for backward compativility on OpenCPN)
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	payload = "RPMDA,"+str(round(pressure/1000*In_mercury_bar,4))+",I,"+str(round(pressure/1000,4))+',B,'+str(round(temperature,4))+',C,'+str(round(humidity,4))+',,,,,,,,,,,,,'
	nmea_str = format_nmea(payload) 
	print(nmea_str)
	sock.sendto( nmea_str.encode('utf-8'), (ipmux_addr, ipmux_port))

	# send pitch and roll (rms values) and wave height to NMEA
	payload = "RPXDR,A,"+str(round(pitch,4))+",D,PTCH,A,"+str(round(roll,4))+",D,ROLL"   
	nmea_str = format_nmea(payload) 
	print(nmea_str)
	sock.sendto( nmea_str.encode('utf-8'), (ipmux_addr, ipmux_port))

	payload = "RPMWH,"+str(round(sig_wave_height*Ft_mt,4))+",F,"+str(round(sig_wave_height,4))+",M"
	nmea_str = format_nmea(payload) 
	print(nmea_str)
	sock.sendto( nmea_str.encode('utf-8'), (ipmux_addr, ipmux_port))

def rao(accel,freq):
    # returs acceleration adjusted to account for heave RAO (=transfer function of wave/boat system) 
    # Assumes head seas, high wavelength/loa ratio (>2)
    # Also, from ref[3] it looks like in our frequency range it can be assumed that the heave RAO can be assumed to be reasonably close to 1
    return accel/1

def disp_led_msg(vert_acc, pitch, roll):
	if abs(vert_acc) > 2:
		sense.clear(255,255,255)
	if abs(pitch) > math.pi/6:
		sense.clear(255,0,0)
	if abs(roll) > math.pi/6:
		sense.clear(0,0,255)

#sine   = lambda x: math.sin(x)
#cosine = lambda x: math.cos(x)

# load settings
config=json.loads(open('settings.json','r').read())

# initialize variables
window 		= config['window'] 		# length of observation frame (in secs)
sample_rate = config['sample_rate'] # Hz
offset_x	= config['offset_x']
offset_y	= config['offset_y']
offset_z 	= config['offset_z'] 	# 0.978225246624319 # run calibrate.py to update this value, with sensor board resting as horizontal as possible
ipmux_addr 	= config['ipmux_addr']  # destination of NMEA UDP messages 
ipmux_port	= config['ipmux_port'] 
pitch_on_y_axis	= config['pitch_on_y_axis'] # Rpi oriented with longest side parallel to fore-aft line of vessel (0) or perpendicular (1)

sample_period 	= 1.0/sample_rate
n = int(window*sample_rate) 		# length of the signal array

# We are applying a simplified constant bandwidth approach. NOAA currently uses requency bandwidths varying from 0.005 Hz at low frequencies 
# to 0.02 Hz at high frequencies. Older systems sum from 0.03 Hz to 0.40 Hz with a constant bandwidth of 0.01Hz.
df = float(sample_rate)/float(n)
min_wave_period = 2  				# secs. NOAA range: 0.0325 to 0.485 Hz -> 2 - 30 secs
max_wave_period = 30 				# secs
min_nyq_freq 	= int(n/(max_wave_period*int(sample_rate)))
max_nyq_freq 	= int(n/(min_wave_period*int(sample_rate)))

signal=[0]*n # the array that holds the time series 
log = prev_t = t0 = time.time()
samples = temperature = pressure = humidity = sum_x_sq = sum_y_sq = sum_dt = avg_pitch = avg_roll = 0
archive_flag = False

# initialize the sensor 
sense = SenseHat()

# initialize log files
f =  open(Log_filename, "a")
f.write(File_header)
print("SenseHat for OpenCPN: v 0.1. Time window: {0} sec., Sample rate: {1}, Sending UDP datagrams to: {2}, port: {3}, Display_charts: {4}".format(window, sample_rate, ipmux_addr, \
	ipmux_port, Display_charts))
print("(Edit settings.json to update these settings)")
print(File_header)

# infinite loop ---------------------------------------------------------------------------------
while True:
	time.sleep(sample_period)
	sense.clear()

	t = time.time()
	dt = t-prev_t
	sum_dt += dt
	prev_t = t

	# read acceleration from IMU
	acceleration = sense.get_accelerometer_raw()
	gyro         = sense.get_orientation_radians()
	gyro_deg = sense.get_orientation_degrees()
	temperature += sense.get_temperature()
	pressure    += sense.get_pressure()
	humidity    += sense.get_humidity()

	# accelerations relative to boat's frame
	x = acceleration['x']-offset_x
	y = acceleration['y']-offset_y
	z = acceleration['z']-offset_z
	pitch = gyro['pitch']
	roll  = gyro['roll']

	# calculate average pitch and roll
	avg_pitch += abs(pitch if pitch < math.pi else (2*math.pi-pitch))
	avg_roll  += abs(roll  if roll  < math.pi else (roll-2*math.pi))

	# coeffs for Euler's tranformation 
	# picth is positive when bow is up, roll is positive when starboard side is up
	# (see ref 1)
	a = -math.sin(pitch)
	b = math.sin(roll)*math.cos(pitch)
	c = math.cos(roll)*math.cos(pitch)
	
	# vertical, non gravitational accel relative to earth frame (in m/sec2)
	#vert_acc = G*(1 - (a*x + b*y + c*z))
	vert_acc = G*(a*x + b*y + c*z)
	disp_led_msg(vert_acc, pitch, roll)

	if (samples < n):
		# get another sample
		signal[samples]=vert_acc
		samples += 1
	else:
		# end of sampling window
		sense.clear
		act_sample_rate=sample_rate

		if pitch_on_y_axis:
			pitch, roll = roll, pitch

		temperature, pressure, humidity, avg_pitch, avg_roll = temperature/samples, pressure/samples, humidity/samples, avg_pitch/samples, avg_roll/samples

		# complete Fast Fourier transform of signal
		wf=fft.fft(signal)

		# identify corrsesponding frequency values for x axis array (cycles/sample_unit)
		n_freqs=fft.fftfreq(n)
		freqs=[n_freqs[i]*act_sample_rate for i in range(int(min_nyq_freq), int(max_nyq_freq))]   # freqs in hertz

		# limit analysis to typical wave periods to limit effects of high-freq sensor noise (e.g. period > 2 sec) and DC and low-freq "blow-up"
		# (ref 3)
		af = wf[min_nyq_freq:max_nyq_freq]

		#replace complex numbers with real numbers and calculate average accel (this could be performance-improved)
		accels=[abs(af[i])/n for i in range(0,len(af)) ]
		avg_acc = sum(accels)/(len(accels))
		heights = [0]*len(accels)

		max_value = max_index = m0 = 0
		for i in range(0,len(accels)):
			if accels[i] > avg_acc:
				# Displacement is the second integral of acceleration (ref 3)
				wave_displ = freqs[i]/((Pi2*freqs[i])**2)
				heights[i]= rao(accels[i],wave_displ)
				# identify main frequency component (amplitude & freq).
				if heights[i] > max_value:
					max_index = i
					max_value = heights[i]
				# 0-moment of wave heights. See ref 2
				m0 += heights[i]*df

		if max_index > 0 and avg_acc > 0.005:
			# calculate significant wave height. See ref 2 on how to calculate SWH from m0
			sig_wave_height = 2*4*math.sqrt(m0) # crest to trough

			print("sig_wave_height: "+str(sig_wave_height))

			# period in secs of main component
			dominant_period = float(n)/(float(max_index)*act_sample_rate)
			#print("max_nyq_freq {0} avg_acc{1} max_value{2} max_index{3} dominant_period {4} accels {5} heights {6} ".format(max_nyq_freq, avg_acc, max_value, max_index, dominant_period, accels, heights))
		else:
			sig_wave_height=0
			dominant_period=0

		if Display_charts:
			pl.title('Signal')
			pl.xlabel('secs')
			pl.ylabel('accel (m/sec2)')
			pl.plot([float(i)/float(act_sample_rate) for i in range(n)],signal)
			pl.show()

			pl.title('Acceleration Frequency Spectrum')
			pl.xlabel('freq (Hz)')
			pl.ylabel('accel (m/sec2)')
			pl.plot(freqs, accels)
			pl.show()

			pl.title('Displacement Frequency Spectrum')
			pl.xlabel('freq (Hz)')
			pl.ylabel('height (mt)')
			pl.plot(freqs, heights)
			pl.show()

			pl.title('Inverse Trasform of filtered signal')
			clean_signal=fft.ifft(af) 
			clean_signal = [x for x in clean_signal]
			pl.plot(clean_signal)
			pl.show()

			# savefig('foo.png') # rasterized 
			# savefig('foo.pdf') # vectorized
			# savefig('foo.png', bbox_inches='tight') #eliminate whitespaces at edge

		# write variables to log file
		t_date = datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d')
		t_time = datetime.datetime.fromtimestamp(t).strftime('%H:%M:%S')
		log_str = str(t)+','+t_date+','+t_time+','+str(round(temperature,3))+','+str(round(pressure,3))+','+str(round(humidity,3))+','+str(round(avg_pitch*180/math.pi,1))+','\
			+str(round(avg_roll*180/math.pi ,1)) +','+str(round(sig_wave_height,4))+','+str(round(dominant_period,4))  
		print(log_str)
		f.write(log_str+"\r\n")
		f.flush()
		
		#sense.show_message("Temp: {0} Press: {1} Hum: {2} Pith: {3} Roll: {4} SWH: {5} Per: {6}".format(temperature, pressure, humidity, pitch, roll, sig_wave_height, dominant_period))
		
		send_to_nmea(pressure, temperature, humidity, avg_pitch, avg_roll, sig_wave_height)

		# reset variables for new loop
		signal = [0 for x in signal] 
		log = t
		samples = sum_x_sq = sum_y_sq = temperature = pressure = humidity = sum_dt = 0  

		today = datetime.datetime.today()
		if today.weekday() == 0 and archive_flag:
			f.close()
			archive_filename="log_sec"+today.strftime("_%Y_%m_%d")+".csv"
			os.system("cp {0} {1}".format(Log_filename,archive_filename))	
			f =  open(Log_filename, "w")
			f.write(File_header)					
			archive_flag = False
		elif today.weekday() != 0:
			archive_flag = True
			

sense.clear()
f.close()

