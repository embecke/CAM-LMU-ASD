'''
This file can be modified to run in a loop such that all the days' required sleep stats are obtained at once - just need to put everything below in a for loop and enter the filenames correctly. 
But in order to visualise and be able to explore the code, it is currently designed to process one day's files at a time. 
'''
#Uncomment the below line if you are running this file for the first time
#pip install --upgrade yasa

#import the eeg data as an edf file. Enter the filepath/filename
import mne
raw = mne.io.read_raw_edf(r":C\Users\becke\Documents\PhD_NEVIA\Data_STREAM\Analysis\LMU_STREAM_HC_009\11062025_n01_12062025_d\Night01_HC_009_11062025_12062025\E00recordingR000_EDF\dev1.edf", preload=True)
raw

chan = raw.ch_names
print(chan)

#downsample from 250Hz to 100Hz to speed up calculation
print(raw.info['sfreq'])
raw.resample(100)
sf = raw.info['sfreq']
sf

#bandpass filter to get rid of line frequency. Also there isn't much useful information beyond this frequency
raw.filter(0.3, 45)

#optional - just to see data shape
data = raw.get_data(units="uV")
print(data.shape)

#import the hypnogram text modified by the code block in matlab as a pandas dataframe
import pandas as pd
hypno = pd.read_csv(r"C:\Users\Ananya Rao\Documents\project_files\09_12\0912_modified_hypnogram.csv", squeeze=True)
hypno

#visualise the hypnogram 
import yasa
yasa.plot_hypnogram(hypno);

#Obtain sleep statistics and store it in a variable. Since the hypnogram provides 1 value (sleep stage) for every 30 second epoch, sampling frequency is 1/30
sleep_stat = yasa.sleep_statistics(hypno, sf_hyp=1/30)
sleep_stat

#send the sleep statistics to an output file of choice in csv format. This will be used by the next code blocks in matlab for analyses
import csv
with open(r"C:\Users\Ananya Rao\Documents\project_files\09_12\sleep_stats.csv", 'w') as csv_file:  
    writer = csv.writer(csv_file)
    for key, value in sleep_stat.items():
        writer.writerow([key, value])     
        
#After this, go back to matlab and continue from where you left off        
