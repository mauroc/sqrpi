# todo: correct with at-rest g coeffs 
import sys
import math
import time
import os
import math
from sense_hat import SenseHat

sense = SenseHat()
samples = sum_z_vert = sum_x = sum_y = sum_z = 0

while samples<1000:
  
    samples += 1
    acceleration = sense.get_accelerometer_raw()
    x = acceleration['x']
    y = acceleration['y']
    z = acceleration['z']
    #print('x,y,z values: ',round(x,4),round(y,4),round(z,4))
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

print("x , y, z, calibration factor", sum_x/samples, sum_y/ samples, sum_z/samples, sum_z_vert / samples)
