"""
Title: <F12> Police Spotting Location Archiver
Author: Daniel Arakcheev
Date: January 26, 2022
"""

import json
from datetime import datetime
import requests
import pandas as pd
from datetime import timedelta
from dateutil import parser
import time
import os.path
import os
import psutil
import gc


# Constant for printing out the process's RAM usage
PRINT_RAM = False


"""
Prints the amount of RAM used by the given process in megabytes.
Args:
    process: process which needs to be analyzed
"""
def getRAM(process):
    if PRINT_RAM:
        print(str(round(process.memory_info().rss / 1000000, 1)) + "MB")
    

    
"""    
A class which is responsible for retreiving and archiving ways incident reports
"""
class PoPoDataArchiver:
    
    """
    The class contructor which sets several values below.
    Args:
        time:           time interval to wait between iterations (in minutes)
        bl:             bottom left corner of the bounding box from which the incidents are gathered
        tr:             top right corner of the bounding box from which the incidents are gathered
        log_file_path:  path to the log file where the incidents are recorded
    """ 
    def __init__(self, time, bl, tr, log_file_path):
        # time interval between new data batches
        self.interval = time
        self.bottomLeft = bl
        self.topRight = tr
        self.log_file_path = log_file_path
    

    """
    Determines which countries the records were detected in.
    Args:
        alertList: list of all incidents retreived
    Returns
        list of countries (string list)
    """
    def whichCountries(self, alertList):
        visited = []
        printNewLocs = False
        
        for x in alertList:
            if printNewLocs:
                if 'street' in x:
                    print(x['street'] + ", lat,long: "+ str(x['location']['y']) +", " + str(x['location']['x']))
                else:
                    print("no_street_name, lat,long: "+ str(x['location']['y']) +", " + str(x['location']['x']))
            
            if 'country' in x:
                country = x['country']
                if country not in visited:
                    visited.append(country)
                    
        return visited


    """
    Calls Wayz API and retreives incidents from specifies bounding box. Filters out police entries..
    Returns
        dataframe containing {date, x-coord, y-coord} of police spotting
    """
    def get_new_data(self):
        print("--- Getting new popo data ---")
        
        headers = {
            "referer": "https://www.waze.com/livemap",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36",
        }

        bottom =    self.bottomLeft[0]
        left =      self.bottomLeft[1]
        top =       self.topRight[0]
        right =     self.topRight[1]

        r = requests.get("https://www.waze.com/rtserver/web/TGeoRSS?left="+ str(left) + 
                                                                "&right=" + str(right) + 
                                                                "&bottom=" + str(bottom) + 
                                                                "&top=" + str(top),
                                                                headers=headers) 

        r.raise_for_status()
        alerts = r.json().get('alerts', [])
        alertsFiltered = filter(lambda x: x['type'] == 'POLICE', alerts)
        alertList = list(alertsFiltered)
        visited  = self.whichCountries(alertList)

        locations = map(lambda x: dict(lat = x['location']['y'], long = x['location']['x']), alertList)
        locations = list(locations)
        
        #put new alerts into df
        df_new = pd.DataFrame(locations, columns = ['lat','long'])
        timeStamp = datetime.now()
        df_new.insert(0, 'date', timeStamp)
        
        print(str(len(alertList)) +" entries found in " + str(visited) + " at " + timeStamp.strftime("%H:%M:%S"))
        return df_new
    

    """
    Filters the dataframe containing new alerts to remove redundant entries. (Cross checks with entries in the buffer.)
    Args:
        df_new_alerts: a dataframe of new alerts coming from the Wayz API call
    """
    def filter_df(self, df_new_alerts):
        print("--- Filtering incoming data ---")
        df_filtered = pd.DataFrame(columns = df_new_alerts.columns)
        
        df_new_alerts = df_new_alerts.reset_index()
        for index, row in df_new_alerts.iterrows():
            newCoords = row['lat'],row['long']
            if not (self.df_buffer[['lat','long']].values == newCoords).all(axis=1).any():
                #coordinates do not exist in 45min buffer, therefore not a duplicate
                df_filtered = pd.concat([df_filtered, row[1:].to_frame().T], ignore_index=True)
            else:
                #print("already exists: " + str(newCoords))
                continue
        #print(str(len(df_filtered)) + " new alerts!")
        return df_filtered

    
    """
    Appends new police alerts to the CSV log (saves to disk).
    Args:
        df_new: dataframe containing filtered new police alerts
    """
    def append_to_csv(self, df_new):
        print("--- Adding data to csv ---")
        print(str(len(df_new)) +" alerts were added to the CSV!")
        if len(df_new) == 0:
            return
        
        # if there exists a log file then append, else write to a new file
        m = 'a' if os.path.isfile(self.log_file_path) else 'w'
        df_new.to_csv(self.log_file_path, mode=m, header=False, index=False)
        

    """
    Creates the buffer and fills it with the entries from the past 45 min (from the CSV).
    Args:
        df_fromCSV: dataframe containing all the police alerts in the CSV log.       
    """
    def fillBuffer(self, df_fromCSV):
        print("--- Filling initial buffer ---")
        self.df_buffer = pd.DataFrame({'date': pd.Series(dtype='datetime64[ns]'),
                   'lat': pd.Series(dtype='float64'),
                   'long': pd.Series(dtype='float64')})
        
        #if there is no data in the csv return empty buffer
        if (len(df_fromCSV.index) == 0):
            print("CSV is empty")
            return

        curr_time = datetime.now()
        end_time = curr_time - timedelta(minutes = 45)
        print("[" + end_time.strftime("%H:%M:%S") +" -> "+ curr_time.strftime("%H:%M:%S") +"]")
        
        #iterate from bottom, get data from past 45 min
        for idx in reversed(df_fromCSV.index):
            row_time = df_fromCSV.loc[idx,'date']

            # append row if the time of the row is after the earliest mark (45 minutes ago)
            if end_time < row_time:
                self.df_buffer = pd.concat([self.df_buffer, df_fromCSV.iloc[idx].to_frame().T], ignore_index=True)
            else:
                print("breaking out, 45 min of alerts loaded")
                break
                #continue
        
        # reverse (to make chronological)
        self.df_buffer = self.df_buffer[::-1]
        # reset the indexes to incremement from 0...
        self.df_buffer.reset_index(drop=True, inplace=True)
        print("Buffer filled with "+ str(len(self.df_buffer)) +" alerts")


    """
    Updates the contents of the buffer to keep it up to date,
        1) Removes the expired entries (older than 45min)
        2) Adds new incoming filtered alerts
    Args:
        df_new: dataframe containing filtered new police alerts
    """
    def updateBuffer(self, df_new):
        print("--- Updating buffer ---")
        
        if (len(self.df_buffer.index) == 0):
            pd.concat([self.df_buffer, df_new], ignore_index=True)
            return

        #print(self.df_buffer.dtypes)
        first_time = self.df_buffer['date'].iloc[0]
        end_time = first_time + timedelta(minutes = self.interval)
        
        # find end of old chunk
        end_index = 0
        for index, row in self.df_buffer.iterrows():
            row_time = row['date']
            # end index (of row that is interval-minutes from the start)
            if row_time >= end_time:
                end_index = index
                break
        
        # remove old data
        df_trimmed_buf = self.df_buffer.iloc[end_index:]
        #add new filtered buffer data
        self.df_buffer = pd.concat([df_trimmed_buf, df_new], ignore_index=True) 
    

    """
    Main function which sets up the buffer and runs iterations. 
    Setup:
        1) Read in all the entries from the police log CSV into a dataframe.
        2) Fill the buffer to contain the latest 45 min of entries.
    Each iteration consists of
        1) Retreiving new police alerts
        2) Filtering the incoming alerts using the buffer (removing redundant entries)
        3) Updating the buffer with truly new entries
        4) Appending new entries to the police log CSV
        5) Sleep for given interval
    """
    def flow(self):
        # load in data from csv
        print("--- Loading data from CSV ---")
        if os.path.isfile(self.log_file_path):
            df_fromCSV = pd.read_csv(self.log_file_path, header = 0, names = ['date', 'lat', 'long'], parse_dates=['date'])
        else:
            df_fromCSV = pd.DataFrame(columns=['date', 'lat', 'long'])
        getRAM(process)

        self.df_buffer = 0
        # populate buffer (initially)
        self.fillBuffer(df_fromCSV)
        
        del df_fromCSV
        gc.collect()
        getRAM(process)
        print("Setup complete -------------------\n")

        itr = 1
        #for i in range(3):
        while(True):
            print("Iteration: " + str(itr))
            itr = itr + 1
            
            # get new data batch
            df_new_data = self.get_new_data()
            getRAM(process)
            # filter df_new_data
            df_filtered = self.filter_df(df_new_data)
            getRAM(process)
            # remove last timeframe of data from buffer
            self.updateBuffer(df_new_data)  
            
            # append df_filtered to csv
            self.append_to_csv(df_filtered)
            print("waiting {} minutes".format(self.interval))
            print("=========================\n")
            gc.collect()
            time.sleep(60 * self.interval)



"""            
==================================== Main function which runs the script. ====================================
"""
GLENCOE = [42.74681380133014, -81.70967190860165]
HEADLAKE = [44.71663527579326, -78.93324717924067]


if __name__ == "__main__":
    process = psutil.Process(os.getpid())

    print("started...")
    getRAM(process)
    interval = 5 # in minutes
    bottomLeft = GLENCOE
    topRight = HEADLAKE
    log_file_path = 'f12log.csv'

    a = PoPoDataArchiver(interval, bottomLeft, topRight, log_file_path)
    a.flow()

"""
PROD NOTES: 
- CHANGE TO WHILE LOOP
- CHANGE INTERVAL TO 5 MIN
- MAKE A CSV WITH THE SAME NAME IN VM
"""
