import math
#from scipy.fftpack import fft, rfft
from numpy import fft,array	
import pylab as pl # sudo apt-get install python-matplotlib

Pi2=2*math.pi

T=6
n=100*T
signal=[0]*n

amp=10


for t in range(len(signal)):
    signal[t]=amp*math.sin(Pi2/T*t)+amp/2*math.sin(Pi2/T/1.7*t)    

spectrum=fft.fft(signal)

spectrum[1].real # real component
spectrum[1].imag # imaginary component 
abs(spectrum[1]) # module

freqs=fft.fftfreq(n)  # frequency values in spectrum

#for i in spectrum:
#   print(str(freqs[i])+','+str(abs(spectrum[i])))

for i in range(len(spectrum)):
    spectrum[i]=abs(spectrum[i])/n*2

pl.plot(freqs[0:n/2], spectrum[0:n/2])
pl.show()



