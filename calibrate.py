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
    x = acceleration['x']-offset_x
    y = acceleration['y']-offset_y
    z = acceleration['z']-offset_z


    sum_x += x
    sum_y += y
    sum_z += z

    x_sq = x**2
    y_sq = y**2
    z_sq = z**2
    #print('squares: ',round(x_sq,4), round(y_sq,4), round(z_sq,4))

    # vertical non gravitational accel. relative to earth frame
    z_vert = math.sqrt(x_sq+y_sq+z_sq)
    sum_z_vert += z_vert

    offset_x, offset_y, offset_z, offset_z_vert = sum_x/samples, sum_y/samples, sum_z/samples, sum_z_vert/samples

    if samples %  10 == 0:
        print('x, y, z, z_vert, skew: : ',round(x,4),round(y,4),round(z,4), round(z_vert, 4), round(z-z_vert, 4) )

print("x , y, z, calibration factor", round(sum_x/samples,4), round(sum_y/ samples,4), round(sum_z/samples,4), round(sum_z_vert / samples,4))
