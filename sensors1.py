# todo: correct with at-rest g coeffs 
import sys
import math
#import operator
import time
import collections
from sense_hat import SenseHat

from numpy import fft,array	
import pylab as pl # sudo apt-get install python-matplotlib


sense = SenseHat()
f=  open("log_sec.csv", "w")
f.write("""time,temperature,pressure,humidity,pitch,roll,wave ht.\r\n""")

G=8.81
Pi2 = 2*math.pi
Offset_z2 = 0.978225246624319 # run calibrate.py to obtain this with sensor board resting as horizontal as possible

sample_rate = 	8.0 #hz
sample_period = 1.0/sample_rate

window = 60 # secs
n = int(window*sample_rate) #length of the signal array
min_wave_period = 2 #secs
max_wave_period = 20 #secs
valid_range = range(n/(max_wave_period*int(sample_rate)),n/(min_wave_period*int(sample_rate)))
signal=[0]*n

log = prev_t = t0 = time.time()  
samples = 0

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
    #print('x,y,z values: ',round(x,4),round(y,4),round(z,4))

    # calc vertical non gravitational accel. relative to earth frame
    x_sq = x**2
    y_sq = y**2
    z_sq = z**2
    z_vert = math.sqrt(x_sq+y_sq+z_sq)
    vert_acc=G*(Offset_z2-z_vert)

    signal[samples]=vert_acc
    
    log_msg = str(samples)+', '+str(round(t-t0,4))+', '+str(round(vert_acc,4)) 
    print(log_msg)
    
    f.write(log_msg+'\r\n')

    samples += 1

    if t-log > window:
        log = t

	# complete Fast Fourier transform of signal        
        wf=fft.fft(signal)

        # limit analysis to typical wave periods (e.g. between 2 and 20 secs)
        spectrum = wf[valid_range[0]:valid_range[-1]]

	# replace complex numbers with real numbers
	for i in range(len(spectrum)):
            spectrum[i]=abs(spectrum[i])/n*2

	# identiy main frequency component
	avg_value = sum(spectrum)/len(spectrum)
	max_value = max(spectrum)
	max_index = spectrum.tolist().index(max_value)

        # calculate total accel amplitude for main freq component (attempting to identify lateral a valid bandwidth of main component)
	i=1
	amp_main_freq = max_value
	while max_index+i <= len(spectrum)-1 and max_index-i >= 0 and (spectrum[max_index+i]>avg_value or spectrum[max_index-i]>avg_value):
	    amp_main_freq += spectrum[max_index+i]  if spectrum[max_index+i] > avg_value else 0
	    amp_main_freq += spectrum[max_index-i]  if spectrum[max_index-i] > avg_value else 0
	    i+=1

        # period in secs of main component
	main_period = n/((max_index+valid_range[0])*int(sample_rate)) 
        
        #estimate average wave height for main freq component
	estimated_wave_height = 2*amp_main_freq/((Pi2/main_period)**2) # accel amplitude / (2*Pi/T)^2 (=double sine integral constant) * 2 (=crest to trough)
	print('main period: '+str(main_period)+', estimated wave height: '+str(round(estimated_wave_height,4)))

	freqs=fft.fftfreq(n)  # identify corrsesponding frequency values for x axis array (periods/sample units)
        
        freqs[i] = freqs[i]*sample_rate # convert to hertz

	#pl.plot(freqs[0:n/2], spectrum[0:n/2])
	pl.plot(freqs[valid_range[0]:valid_range[-1]], spectrum)
	pl.show()
	pl.plot(signal)
	pl.show()
        clean_signal=fft.ifft(wf) 
	clean_signal = [x * n/2 for x in clean_signal]
        pl.plot(clean_signal[0:n/2])
        pl.show()

        samples = 0  
        for i in range(len(signal)):
            signal[i]=0 
        
f.close()
