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
    gyro_d = sense.get_orientation_degrees()

    x = acceleration['x']
    y = acceleration['y']
    z = acceleration['z']

    pitch_d = gyro_d['pitch']
    roll_d  = gyro_d['roll']

    sum_x += x
    sum_y += y
    sum_z += z

    offset_x, offset_y, offset_z = sum_x/samples, sum_y/samples, sum_z/samples

    if samples %  10 == 0:
        print('x: {} y: {} z: {} pitch_d: {}  roll_d: {}'.format(round(x,4),round(y,4),round(z,4), round(pitch_d, 2), round(roll_d, 2)) )

print("x: {} y: {} z: {} ".format(round(sum_x/samples,4), round(sum_y/ samples,4), round(sum_z/samples,4)))
