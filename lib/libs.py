import numpy as np

Log_filename    = "log_nmea.csv"

def moving_average(a, n=3):
    """ Calculate moving ex-post average (backward/forward looking)"""
    ret = np.cumsum(a, dtype=float)
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

def nearest_fix(log_time):
    """ Find the coordinates at the given time based on the UDP stream (if available) """
    
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
        if abs(timestamp - log_time ) <= 180.0:
            # available coords are near enough
            return float(parts[1]), float(parts[2])
        else: 
            return None
    else:
        return None
    