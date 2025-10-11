# todo: correct with at-rest g coeffs 
import sys
import math
import time
import os
import math
from sense_hat import SenseHat

sense = SenseHat()
samples = sum_z_vert = sum_x = sum_y = sum_z = sum_pitch = sum_roll = 0
offset_x = offset_y = offset_z = offset_z_vert = 0

while samples<200:

    samples += 1
    acceleration = sense.get_accelerometer_raw()
    gyro_d = sense.get_orientation_degrees()
    gyro = sense.get_orientation_radians()

    x = acceleration['x']
    y = acceleration['y']
    z = acceleration['z']-1

    pitch_d = gyro_d['pitch']
    roll_d  = gyro_d['roll'] 
    pitch = gyro['pitch']
    roll  = gyro['roll']

    sum_x += x
    sum_y += y
    sum_z += z
    sum_pitch += pitch
    sum_roll  += roll

    offset_x, offset_y, offset_z, offset_pitch, offset_roll = sum_x/samples, sum_y/samples, sum_z/samples, sum_pitch/samples, sum_roll/samples

    if samples %  10 == 0:
        print('ax: {} ay: {} az: {} pitch °: {}  roll °: {}    '.format(round(x,5),round(y,5),round(z,5), round(math.degrees(pitch), 3), round(math.degrees(roll), 3)) )

print('\nCalibration Settings: ')
print("offset x: {} offset y: {} offset z: {} offsed pitch ° {} offset roll ° {}"
      .format(round(sum_x/samples,5), round(sum_y/ samples,5), round(sum_z/samples,5), round(math.degrees(offset_pitch),2), round(math.degrees(offset_roll),2   )))
