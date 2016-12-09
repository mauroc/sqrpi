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
offset_x =  -0.004296421259175986
offset_y =  0.06696801705658435
offset_z =  0.9755681986808777
offset_z2 = 0.978225246624319

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

    x_sq = x**2
    y_sq = y**2
    z_sq = z**2
    # vertical non gravitational accel. relative to earth frame
    z_vert = math.sqrt(x_sq+y_sq+z_sq)

    #vert_acc=G*(z-offset_z)
    vert_acc=G*(offset_z2-z_vert)

    signal[samples]=vert_acc
    
    log_msg = str(samples)+', '+str(round(t-t0,4))+', '+str(round(vert_acc,4)) 
    print(log_msg)
    
    #if vert_acc > 0.4:
        #print('----------------------------')
        #print(x,y,z)	

    f.write(log_msg+'\r\n')

    samples += 1

    if t-log > window:
        log = t
        
        wf=fft.fft(signal)
        spectrum = wf[valid_range[0]:valid_range[-1]]

	for i in range(len(spectrum)):
            spectrum[i]=abs(spectrum[i])/n*2

	avg_value = sum(spectrum)/len(spectrum)
	max_value = max(spectrum)
	max_index = spectrum.tolist().index(max_value)

        # calculate total accel amplitude for main freq component
	i=1
	amp_main_freq = max_value
	while max_index+i <= len(spectrum)-1 and max_index-i >= 0 and (spectrum[max_index+i]>avg_value or spectrum[max_index-i]>avg_value):
	    amp_main_freq += spectrum[max_index+i]  if spectrum[max_index+i] > avg_value else 0
	    amp_main_freq += spectrum[max_index-i]  if spectrum[max_index-i] > avg_value else 0
	    i+=1

	main_period = n/((max_index+valid_range[0])*int(sample_rate)) # in secs
	print('main period: '+str(main_period)+', estimated wave height (c_to_t): '+str(round(2*amp_main_freq/((Pi2/main_period)**2),4)))

	freqs=fft.fftfreq(n)  # frequency values in spectrum
        
        freqs[i] = freqs[i]*sample_rate

	#pl.plot(freqs[0:n/2], spectrum[0:n/2])
	pl.plot(freqs[valid_range[0]:valid_range[-1]], spectrum)
	pl.show()
	pl.plot(signal)
	pl.show()
        clean_signal=fft.ifft(ws) 
	clean_signal = [x * n/2 for x in clean_signal]
        pl.plot(clean_signal[0:n/2])
        pl.show()

        samples = 0  
        for i in range(len(signal)):
            signal[i]=0 
        
f.close()
