import numpy as np
import math
from datetime import datetime
import time
import os

Log_filename    = "log_nmea.csv"

def delete_old_files(directory, days=3):
     
	"""
	Deletes files in the given directory that are older than 'days' days.
	"""
	now = time.time()
	cutoff = now - (days * 86400)  # 86400 seconds = 1 day
	if not os.path.isdir(directory):
		print(f"Error: {directory} is not a valid directory")
		return
	for filename in os.listdir(directory):
		filepath = os.path.join(directory, filename)
		# Only delete files, not directories
		if os.path.isfile(filepath):
			file_mtime = os.path.getmtime(filepath)
			if file_mtime < cutoff:
				print(f"Deleting: {filepath}")
				os.remove(filepath)

def save_arrays(npy_dir, freqs, signal, acc_spectrum, heave_spectrum):
	""" Save signal, spectrum arrays etc. to a .npy file for debugging/analysis"""
	now = datetime.now().strftime("_%Y_%m_%d_%H_%M")
	np.save(f'{npy_dir}signal{now}', signal)
	np.save(f'{npy_dir}amp_spec{now}', acc_spectrum)
	np.save(f'{npy_dir}heave_spectrum{now}', heave_spectrum)
	np.save(f'{npy_dir}freqs{now}', freqs)
	delete_old_files(npy_dir, days=3)

def archive_files(f):
	""" Copy log_file to an archive file with today's date """
	f.close()
	archive_filename="log_sec"+today.strftime("_%Y_%m_%d")+".csv"
	os.system("cp {0} {1}".format(Log_filename,archive_filename))	
	f =  open(Log_filename, "w")
	f.write(File_header)					
	archive_flag = False
     
def moving_average(series, n=3):
    """ 
    Calculate center moving average of time series 
    """
    ret = np.cumsum(series, dtype=float)
    ret[n:] = ret[n:] - ret[:-n]
    return ret[n - 1:] / n

def remove_outliers(sensor_data, sigma=0.25):
    """ 
    Eliminate likely sensor errors (outliers outside of sigma). Return Series not containing samples that 
    exceed +- sigma
    """
    # Compute mean and std
    mean = sensor_data.mean()
    std = sensor_data.std()
    # Define thresholds
    lower = mean - sigma * std
    upper = mean + sigma * std
    # Apply mask
    return sensor_data[(sensor_data >= lower) & (sensor_data <= upper)]

def nearest_fix(log_time, look_back=180):
    """ 
    Find the coordinates at the given time based on the UDP stream (if available) 
    """
    
    last_rec = ""
    # open the nmea log file and find the last record
    try:
        with open(Log_filename, 'r') as f:
            lines = f.readlines()
            if lines:
                last_rec = lines[-1].strip()  # Remove trailing newline
            else:
                last_rec = None
    except FileNotFoundError:
        return None
    
    if last_rec:
        # if nmea timestamp is within sample window, return lat/lon
        parts = last_rec.split(',')
        timestamp = float(parts[0])
        if abs(timestamp - log_time ) <= look_back:
            # available coords are near enough
            return float(parts[1]), float(parts[2])
        else: 
            return None
    else:
        return None
    
