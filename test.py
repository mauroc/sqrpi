# todo: correct with at-rest g coeffs 
import sys
import math
import time
import os
import math
from sense_hat import SenseHat
import time

sense = SenseHat()
samples = sum_z_vert = sum_x = sum_y = sum_z = 0

while samples<200:
    samples+=1
    #gyros = sense.get_gyroscope_raw()
    gyros = sense.get_orientation_degrees()
    acceleration = sense.get_accelerometer_raw()
    print(acceleration)
    time.sleep(.5)
