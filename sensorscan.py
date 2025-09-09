import sys
import math
import operator
import time
import datetime
import socket
import os
import json
from functools import reduce
import pynmea2 as nmea

from sense_hat import SenseHat
#from numpy import fft,array
import numpy as np
import pylab as pl # sudo apt-get install python-matplotlib
import pdb
from scipy.signal import detrend

# Initialize constants
G				= 9.81
Pi 			    = math.pi
In_mercury_bar 	= 29.53
Ft_mt       	= 3.28
Log_filename    = "log_sec.csv"
File_header		= """timestamp,date,time,temperature,pressure,humidity,avg_pitch,avg_roll,max_pitch,max_roll,wave_height,wave_period\r\n"""
Display_charts 	= False
Debug_on 		= False

# functions
def moving_average(a, n=3):
	""" Calculate moving ex-post average (backward/forward looking)"""
	ret = np.cumsum(a, dtype=float)
	ret[n:] = ret[n:] - ret[:-n]
	return ret[n - 1:] / n

def delete_old_files(directory, days=3):
	"""
	Deletes files in the given directory that are older than 'days' days.
	"""
	now = time.time()
	cutoff = now - (days * 86400)  # 86400 seconds = 1 day
	if not os.path.isdir(directory):
		print(f"Error: {directory} is not a valid directory")
		return
	for filename in os.listdir(directory):
		filepath = os.path.join(directory, filename)
		# Only delete files, not directories
		if os.path.isfile(filepath):
			file_mtime = os.path.getmtime(filepath)
			if file_mtime < cutoff:
				print(f"Deleting: {filepath}")
				os.remove(filepath)

def format_nmea(payload):
	# this can probably be replaced with pynmea2 
    nmea_str_cs = format(reduce(operator.xor,map(ord,payload),0),'X')
    nmea_str_cs = "0"+nmea_str_cs if len(nmea_str_cs) == 1 else nmea_str_cs
    nmea_str = '$'+payload+"*"+nmea_str_cs+"\r\n"
    return nmea_str

def send_to_nmea(pressure, temperature, humidity, pitch, roll, sig_wave_height):
	""" send variables to NMEA IP address (using obsolete NMEA deprecated MDA for backward compativility on OpenCPN)"""
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
    """ Returns acceleration adjusted to account for heave RAO (=transfer function of wave/boat system) """
    # Assumes head seas, high wavelength/loa ratio (>2)
    # Also, from ref[3] it looks like in our frequency range it can be assumed that the heave RAO can be assumed to be reasonably close to 1
    return accel/1

def disp_led_msg(vert_acc, pitch, roll):
	""" Alert user to excesive accel, pitch, roll values by showing different colors on the led matrix"""

	if abs(vert_acc) > 2:
		sense.clear(255,255,255)
	if abs(pitch) > Pi/10:
		sense.clear(255,0,0)
	if abs(roll) > Pi/6:
		sense.clear(0,0,255)

def disp_chart(x_values, y_values, title, xlabel, ylabel):
	title and pl.title(title)
	xlabel and pl.xlabel(xlabel)
	ylabel and pl.ylabel(ylabel)
	if y_values:
		pl.plot(x_values , y_values)
		pl.show()

def read_accel():
	"""
	Read values from senors and calculate vertical acceleration relative to the earth frame. 
	Return vertical, non gravitational accel relative to earth frame (in m/sec2)
	"""

	global temperature, pressure, humidity, pitch, roll, max_pitch, max_roll, min_pitch, min_roll, avg_pitch, avg_roll

	# read acceleration from IMU
	acceleration = sense.get_accelerometer_raw()
	gyro         = sense.get_orientation_radians()
	#gyro_deg = sense.get_orientation_degrees()
	temperature += sense.get_temperature()
	pressure    += sense.get_pressure()
	humidity    += sense.get_humidity()

	# accelerations relative to boat's frame
	x = acceleration['x']-offset_x
	y = acceleration['y']-offset_y
	z = acceleration['z']-offset_z
	# picth is positive when bow is up, roll is positive when starboard side is up
	pitch = gyro['pitch']
	roll  = gyro['roll']

	# calculate max, min, average pitch and roll
	max_pitch = max(max_pitch, pitch)
	min_pitch = min(min_pitch, pitch)
	max_roll = max(max_roll, roll)
	min_roll = min(min_roll, roll)
	avg_pitch += abs(pitch if pitch < Pi else (2*Pi - pitch))
	avg_roll  += abs(roll  if roll  < Pi else (roll - 2*Pi))

	# coeffs for Euler's tranformation 
	# (see ref 1)
	a = -math.sin(pitch)
	b = math.sin(roll)*math.cos(pitch)
	c = math.cos(roll)*math.cos(pitch)
	
	#vert_acc = G*(1 - (a*x + b*y + c*z))
	return G*(a*x + b*y + c*z)
	
def transform(signal):
	""" Transform samples signal into frequency domain. Return n-sized arrays of Frequencies (Hz) and Complex Spectrum"""

	# Fast Fourier transform of signal
	wf = np.fft.fft(signal)

	# identify corresponding frequency values, in Hertz, for x axis array 
	n_freqs = np.fft.fftfreq(n, 1/sample_rate) 
	
	# the fft returns both positive and negative frequencies, up to 1/2 of the sampling rate (Nyquist theorem) 
	# We need to eliminate negative frequencies and only analyse freqs in our range of interest
	# to limit effects of high-freq sensor noise (e.g. period > 2 sec) and DC and low-freq "blow-up"
	# (ref 3)
	mask 	= ((n_freqs >= min_freq) & (n_freqs <= max_freq)) 
	freqs 	= n_freqs[mask]
	af 		= wf[mask]

	# Normalize by N to recover amplitudes in m/s²
	accels = af / n

	# return amplitude spectrum (m/s²), i.e. the module of complex array
	# Factor 2 for one-sided spectrum (except DC/Nyquist)
	acc_spectrum = 2 * abs(accels)   
	return  freqs, acc_spectrum

def displacement(amp_spec):
	""" 
	Convert acceleration spectrum to heights (i.e. heave or displacement) by 2nd integration (ref3) 
	Return displacement array (units: m)
	"""
	heights = np.zeros_like(amp_spec)
	nonzero = freqs > 0

	heights[nonzero] = amp_spec[nonzero] / ((2 * math.pi * freqs[nonzero])**2 )

	return  heights

def save_arrays():
	""" Save signal, spectrum arrays etc. to a .npy file for debugging/analysis"""
	now = datetime.datetime.now().strftime("_%Y_%m_%d_%H_%M")
	npy_dir = 'npyfiles/'
	np.save(f'{npy_dir}signal{now}', signal)
	np.save(f'{npy_dir}amp_spec{now}', acc_spectrum)
	np.save(f'{npy_dir}heights{now}', heights)
	np.save(f'{npy_dir}freqs{now}', freqs)
	delete_old_files(npy_dir, days=3)

def calc_swh(acc_spectrum):
	""" Calculate wave action main parameters. Return Significant Wave Height (m), Dominant Period) (sec)"""

	# find index of highest waves using the moving average of *acceleration* spectrum . This is incorrect, in that it should be
	# done on heights spectrum, and it may wrongly identify higher frequency peaks which do not correspond to highest waves. 
	# TODO need to figure out a way to aliminate the effects of low-frequency blow-up
	avg_window = 4
	mavg_amp_spec = moving_average(acc_spectrum, avg_window)

	# find dominant period and max wave height 
	max_index = np.argmax(mavg_amp_spec) + int(avg_window/2) # the moving average array drops avg_window elements (1/2 on each side)
	dom_freq = freqs[max_index] 
	dom_period = 1/dom_freq

	# spectral density 
	psd = (heights**2)/freqs 	# Power SD (m2/hz)
	asd = np.sqrt(psd) 			# Amplitude SD (m/Hz^1/2)

	# zeroth moment (m₀), or the area under the nondirectional wave spectrum curve, representing the total variance of the wave elevation. 
	# TODO it is not clear if m0 uses **power** spectral density, or **amplitude** spectral density. Ref 2 only refers to spectral density.
	low_cutoff = 2 # experimenting with limiting impact of low-freq blow up on SFW calc
	
	#m0  = sum(psd[low_cutoff:]*df) # this seems to generate excessive heights in real-life test 
	m0  = sum(psd[low_cutoff:]*df) 
	
	# SWH is the average of the highest one-third of the waves (ref 2). NDBC calculates SWH from the m0
	# note that this is **wave** height, so trough to crest (twice the amplitude)
	sig_wave_height = 4 * math.sqrt(m0)

	return sig_wave_height,  dom_period

def archive_files(f):
	""" Copy log_file to an archive file with today's date """
	f.close()
	archive_filename="log_sec"+today.strftime("_%Y_%m_%d")+".csv"
	os.system("cp {0} {1}".format(Log_filename,archive_filename))	
	f =  open(Log_filename, "w")
	f.write(File_header)					
	archive_flag = False

# load settings
config=json.loads(open('settings.json','r').read())

# initialize global variables
window 		= config['window'] 		# length of observation frame (in secs)
sample_rate = config['sample_rate'] # Hz
offset_x	= config['offset_x']
offset_y	= config['offset_y']
offset_z 	= config['offset_z'] 	# run calibrate.py to update this value, with sensor board resting as horizontal as possible
fwd_nmea    = config['fwd_nmea']
ipmux_addr 	= config['ipmux_addr']  # destination of NMEA UDP messages 
ipmux_port	= config['ipmux_port'] 
pitch_on_y_axis	= config['pitch_on_y_axis'] # Rpi oriented with longest side parallel to fore-aft line of vessel (0) or perpendicular (1)

sample_period 	= 1.0/sample_rate
n = int(window*sample_rate) 		# length of the signal and the spectrum arrays

# Set frequency range and spectrum bandwidth. NOAA currently uses frequency bandwidths varying from 0.005 Hz at low frequencies 
# to 0.02 Hz at high frequencies. Older systems sum from 0.03 Hz to 0.40 Hz with a constant bandwidth of 0.01Hz.
# We are applying a simplified constant bandwidth approach since np.fft does not allow to define variable size frequency slots. 
df = float(sample_rate)/float(n)	# bandwidth of individual frequency slot in spectrum
min_wave_period = 4  				# secs. NOAA range: 0.0325 to 0.485 Hz -> 2 - 30 secs
max_wave_period = 25 				# secs
min_freq = 1/max_wave_period
max_freq = 1/min_wave_period

# the array that holds the time series 
signal = np.zeros(n) 

temperature = pressure = humidity = tot_elapsed = avg_pitch = avg_roll = pitch = roll = max_pitch = min_pitch = max_roll = min_roll = 0
archive_flag = False

# initialize the sensors
sense = SenseHat()

# debug settings
load_file = ""

# initialize log files
append_data = os.path.exists(Log_filename)
f =  open(Log_filename, "a") # append to exising file
if not append_data:
	f.write(File_header)

print("SenseHat for OpenCPN: v 0.1. Time window: {0} sec., Sample rate: {1}, Sending UDP datagrams to: {2}, port: {3}, Display_charts: {4}".format(window, sample_rate, ipmux_addr, \
	ipmux_port, Display_charts))
print("(Edit settings.json to update these settings)\n\n")
print(File_header+"-"*140)


# infinite loop ---------------------------------------------------------------------------------
log =  t = time.time()

#for i in range(1):
while True:

	# *** Data Collection Step ***
	if not Debug_on:
		# Read sensors every 1/sample_rate seconds and load them into the signal array
		for sample in range(n):
			t = time.time()
			
			sense.clear()

			vert_acc = read_accel()
			
			# use led matrix of sensehat to warn of excessive roll, pitch and vertical acc
			disp_led_msg(vert_acc, pitch, roll)

			# add to sample array
			signal[sample]=vert_acc
			
			# make sure the cycle executes once every 1/sample_time secs. Wait if needed
			elapsed_time = time.time()-t
			wait_time = 1/sample_rate - elapsed_time
			if wait_time>0:
				time.sleep(wait_time)
			tot_elapsed += time.time()-t

	else:
		load_file = input("Load existing samples file? (Enter to skip) ")
		if len(load_file)>0:
			signal = np.load(load_file)
		else:
			# Simulated signal
			tm = np.arange(n) / sample_rate
			signal = 2.0*np.sin(2*np.pi*0.05*tm) + 1*np.sin(2*np.pi*0.2*tm) + 0.05*np.random.randn(n)
	

	# *** Data Analysis Step ***

	sense.clear
	#pdb.set_trace()
	
	if pitch_on_y_axis:
		pitch, roll = roll, pitch

	# Calculate averages from cumulative values
	temperature, pressure, humidity, avg_pitch, avg_roll = temperature/n, pressure/n, humidity/n, avg_pitch/n, avg_roll/n

	# Reduce impact of linear trends (slow drift) in the signal
	signal = detrend(signal, type='linear')

	# Convert signal to frequency domain
	freqs, acc_spectrum = transform(signal)

	# Convert accelerations to heights (displacement)
	heights = displacement(acc_spectrum)

	# Apply dynamic response of vessel to wave action
	vectorized_rao = np.vectorize(rao) # enable an np array to operate a custom fucntion on all alements
	heights = vectorized_rao(heights, freqs)

	if len(load_file) == 0:
		# Save content of main arrays for debugging
		save_arrays()

	if acc_spectrum.mean() > 0.005:
		# Calculate main wave parameters
		sig_wave_height, dom_period =  calc_swh(acc_spectrum)
		print("Significant Wave Height: ", sig_wave_height)
	else:
		sig_wave_height=0
		dom_period=0

	if Display_charts:
		disp_chart([float(i)/float(sample_rate) for i in range(200,400)], signal[200:400], 'Signal', 'Secs', 'Accel (m/sec2)' )
		disp_chart(freqs, acc_spectrum,  'Acceleration Frequency Spectrum', 'freq (Hz)', 'accel (m/sec2)')
		disp_chart(freqs, heights, 'Displacement Frequency Spectrum', 'freq (Hz)', 'Height (m)')
		# clean_signal=np.fft.ifft(af) 
		# clean_signal = [x for x in clean_signal]
		# disp_chart(None, clean_signal, 'Inverse Trasform of filtered signal', None, None)

	# write variables to log file
	t_date = datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d')
	t_time = datetime.datetime.fromtimestamp(t).strftime('%H:%M:%S')
	max_roll  = max_roll  if abs(max_roll)  > abs(min_roll)  else min_roll
	max_pitch = max_pitch if abs(max_pitch) > abs(min_pitch) else min_pitch
	log_str =  f'{round(t,3)},{t_date},{t_time},{round(temperature)},{round(pressure)},{round(humidity)},'
	log_str += f'{round(math.degrees(avg_pitch))},{round(math.degrees(avg_roll))},{round(math.degrees(max_pitch))},{round(math.degrees(max_roll))},'
	log_str += f'{round(sig_wave_height,2)},{round(dom_period)}'	
	print(log_str)
	f.write(log_str+"\r\n")
	f.flush()
	
	#sense.show_message("Temp: {0} Press: {1} Hum: {2} Pith: {3} Roll: {4} SWH: {5} Per: {6}".format(temperature, pressure, humidity, pitch, roll, sig_wave_height, dom_period))
	if fwd_nmea:
		# send sensor data to UDP channel
		send_to_nmea(pressure, temperature, humidity, avg_pitch, avg_roll, sig_wave_height)

	# reset variables for new loop
	signal.fill(0) #= [0 for x in signal] 
	log = t
	temperature=pressure=humidity=tot_elapsed=max_pitch=max_roll=min_pitch=min_roll= 0  

	today = datetime.datetime.today()
	if today.weekday() == 0 and archive_flag:
		archive_files(f)
	elif today.weekday() != 0:
		archive_flag = True
			
sense.clear()
f.close()

