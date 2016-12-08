


import math
#from scipy.fftpack import fft, rfft
from numpy import fft,array	
import pylab as pl

n=100
signal=[0]*n

T=12
amp=1

for t in range(len(signal)):
    signal[t]=amp*math.sin(2*math.pi/T*t)    

spectrum=fft.fft(signal)

spectrum[1].real # real component
spectrum[1].imag # imaginary component 
abs(spectrum[1]) # module

freqs=fft.fftfreq(n)  # frequency values in spectrum

for i in spectrum:
   print(str(freqs[i])+','+str(abs(spectrum[i])))

plot(freqs, spectrum)



