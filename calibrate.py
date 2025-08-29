# todo: correct with at-rest g coeffs 
import sys
import math
import time
import os
import math
from sense_hat import SenseHat

sense = SenseHat()
samples = sum_z_vert = sum_x = sum_y = sum_z = 0
offset_x = offset_y = offset_z = offset_z_vert = 0

while samples<200:

    samples += 1
    acceleration = sense.get_accelerometer_raw()
    x = acceleration['x']
    y = acceleration['y']
    z = acceleration['z']


    sum_x += x
    sum_y += y
    sum_z += z

    offset_x, offset_y, offset_z = sum_x/samples, sum_y/samples, sum_z/samples

    if samples %  10 == 0:
        print('x, y, z, z_vert, skew: : ',round(x,4),round(y,4),round(z,4) )

print("x , y, z, calibration factor", round(sum_x/samples,4), round(sum_y/ samples,4), round(sum_z/samples,4))
