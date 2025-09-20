import numpy as np
import math
from datetime import datetime
import time
import os
from scipy.ndimage import gaussian_filter1d
import pdb

Log_filename    = "log_nmea.csv"
G = 9.81

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

def archive_files(f, file_header):
	""" Copy log_file to an archive file with today's date """
	f.close()
	archive_filename="log_sec"+ datetime.today.strftime("_%Y_%m_%d")+".csv"
	os.system("cp {0} {1}".format(Log_filename,archive_filename))	
	f =  open(Log_filename, "w")
	f.write(file_header)					
	return False
     
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

def heave(freqs, amp_spec):
	""" 
	Convert acceleration spectrum to heave (=vertical displacement) spectrum  by 2nd integration (ref3) 
	Return displacement array (units: m)
	"""
	heave_spectrum = np.zeros_like(amp_spec)
	nonzero = freqs > 0

	heave_spectrum[nonzero] = amp_spec[nonzero] / ((2 * math.pi * freqs[nonzero])**2 )

	return  heave_spectrum

def transform(signal, sample_rate, min_period, max_period):
    """
	Transform samples signal into frequency domain. Return n-sized arrays of Frequencies (Hz) and Complex Spectrum
	"""
    #min_freq = 1/max_period
    #max_freq = 1/min_period

    n=len(signal)
    # Fast Fourier transform of signal
    wf = np.fft.fft(signal)

    # identify corresponding frequency values, in Hertz, for x axis array 
    n_freqs = np.fft.fftfreq( n , 1/sample_rate) 
	
	# the fft returns both positive and negative frequencies, up to 1/2 of the sampling rate (Nyquist theorem) 
	# We need to eliminate negative frequencies and only analyse freqs in our range of interest
	# to limit effects of high-freq sensor noise (e.g. period > 2 sec) and DC and low-freq "blow-up"
	# (ref 3)
    mask 	= ((n_freqs >= 1/max_period) & (n_freqs <= 1/min_period)) 
    freqs 	= n_freqs[mask]
    af 		= wf[mask]

	# Normalize by N to recover amplitudes in m/s²
    accels = af / n

	# return amplitude spectrum (m/s²), i.e. the module of complex array
	# Factor 2 for one-sided spectrum (except DC/Nyquist)
    acc_spectrum = 2 * abs(accels)   
    return  freqs, acc_spectrum

def calc_swh(freqs, df, acc_spectrum, heave_spectrum):

    """ 
    Calculate nondirectional wave action main parameters. Return Significant Wave Height (m), Dominant Period) (s), Modal Period (s), Average Period (s)
    """

    # TODO need to figure out a way to aliminate the effects of low-frequency blow-up

    # Modal Period
    # Smooth the spectrum for more accurate identification of modal point
    gauss = gaussian_filter1d(acc_spectrum, sigma=2)
    max_index = np.argmax(gauss)
    
    # find highest point (mode) in the frequency 
    modal_frequency = freqs[max_index] 
    modal_period = 1/modal_frequency

    # spectral density (ref2)
    psd = (heave_spectrum**2)/freqs 	# Power SD (m2/hz)
    asd = np.sqrt(psd) 			# Amplitude SD (m/Hz^1/2)

    # Dominant period (ref2)
    max_index = np.argmax(psd)
    dominant_period = 1/freqs[max_index]

    # zeroth moment (m₀), or the area under the nondirectional wave spectrum curve, representing the total variance of the wave elevation. 
    low_cutoff = 2 # TODO experimenting with limiting impact of low-freq blow up on SFW calc
    m0  = sum(psd[low_cutoff:]*df) 

    # Average period (ref 2)
    freqs2=freqs**2
    m2=sum(np.multiply(psd,freqs2)*df)
    avg_period = math.sqrt(m0/m2)
    
    # SWH is the average of the highest one-third of the waves (ref 2). NDBC calculates SWH from the m0
    # note that this is **wave** height, so trough to crest (twice the amplitude)
    sig_wave_height = 4 * math.sqrt(m0)

    return sig_wave_height, dominant_period, modal_period, avg_period

def inv_rao(heaves,freqs, vessel_lw, avg_pitch, avg_roll):
    """ 
    Returns an array of heave adjusted to account for vessel RAO (Response Amplitude Operator => amplitude of transfer function of wave/boat system) 
    """
         
    # ref1: https://icce-ojs-tamu.tdl.org/icce/article/download/3779/3462?utm_source=chatgpt.com
    # ref 2 https://chatgpt.com/share/68cc2242-d6fc-8006-b7b4-194b2da0e85a

    def wl_to_period(wl):
         """ Convert wavelength to period using the formula for deep water at ref 2 """
         return math.sqrt(2 * np.pi * wl/G) 

    # define a frequency range to which to apply a correction factor. Based on ref, RAO is corrected to an approximated average value
    # in the wavelength range of 2*vessel_lw to 5*vessel_lw , and is assumed to be =1 for greater wavelengths. 
    short_per = wl_to_period( 1 * vessel_lw)
    long_per  = wl_to_period( 5 * vessel_lw)

    # correction factor depends on direction of waves relative to boat. We use the ratio avg_roll/pitch as an indicator of whether broadside
    # component is prevailing 
    waves_broadside = avg_roll/avg_pitch > 2
    mask = (freqs >= 1/long_per) & (freqs <= 1/short_per)

    # since we are using vessel heave to estimate wave height (wave_heave = vessel_heave / RAO) 
    # the corrections are > 1 if wave direction causes vessel to heave less (head on), and < 1 if broadside. 
    heaves[mask] *= 0.9 if waves_broadside else 1.1
    
    return heaves
