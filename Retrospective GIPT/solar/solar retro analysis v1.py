import pandas
import numpy as np
import glob
from flatten_json import flatten_json
import json
import pandas
import numpy
from numpy import *
from json import loads, dumps
import re 
import pandas as pd
import math

## ---- TRACKING PAST STATUS CHANGES IN SOLAR PROJECTS:

## ---- LOAD IN 6 X PAST SOLAR TRACKERS
#FEB 2025
solar_feb_2025_20plus=pandas.read_excel("./Retrospective GIPT/solar/Global-Solar-Power-Tracker-February-2025.xlsx",'20 MW+')
solar_feb_2025_1_20=pandas.read_excel("./Retrospective GIPT/solar/Global-Solar-Power-Tracker-February-2025.xlsx","1-20 MW")
solar_feb_2025=pandas.concat([solar_feb_2025_20plus,solar_feb_2025_1_20])
# Drop duplicated units (sometimes above/below threshold contain the same units)
solar_feb_2025 = solar_feb_2025[~solar_feb_2025['GEM phase ID'].duplicated(keep=False)]

#JUNE 2024
solar_jun_2024_20plus=pandas.read_excel("./Retrospective GIPT/solar/Global-Solar-Power-Tracker-June-2024.xlsx",'20 MW+')
solar_jun_2024_1_20=pandas.read_excel("./Retrospective GIPT/solar/Global-Solar-Power-Tracker-June-2024.xlsx","1-20 MW")
solar_jun_2024=pandas.concat([solar_jun_2024_20plus,solar_jun_2024_1_20])
# Drop duplicated units (sometimes above/below threshold contain the same units)
solar_jun_2024 = solar_jun_2024[~solar_jun_2024['GEM phase ID'].duplicated(keep=False)]

#DEC 2023
solar_dec_2023_20plus=pandas.read_excel("./Retrospective GIPT/solar/Global-Solar-Power-Tracker-December-2023.xlsx",'Large Utility-Scale')
solar_dec_2023_med=pandas.read_excel("./Retrospective GIPT/solar/Global-Solar-Power-Tracker-December-2023.xlsx","Medium Utility-Scale")
solar_dec_2023_sub=pandas.read_excel("./Retrospective GIPT/solar/Global-Solar-Power-Tracker-December-2023.xlsx","Below Threshold")
solar_dec_2023=pandas.concat([solar_dec_2023_20plus,solar_dec_2023_med,solar_dec_2023_sub])
solar_dec_2023['GEM phase ID'] = solar_dec_2023['GEM phase ID'].str[1:]
solar_dec_2023['GEM phase ID']='G100000'+solar_dec_2023['GEM phase ID']
# Drop duplicated units (sometimes above/below threshold contain the same units)
solar_dec_2023 = solar_dec_2023[~solar_dec_2023['GEM phase ID'].duplicated(keep=False)]

#MAY 2023
solar_may_2023_20plus=pandas.read_excel("./Retrospective GIPT/solar/Global-Solar-Power-Tracker-May-2023.xlsx",'Data')
solar_may_2023_sub=pandas.read_excel("./Retrospective GIPT/solar/Global-Solar-Power-Tracker-May-2023.xlsx","Below Threshold")
solar_may_2023=pandas.concat([solar_may_2023_20plus,solar_may_2023_sub])
solar_may_2023['GEM phase ID'] = solar_may_2023['GEM phase ID'].str[1:]
solar_may_2023['GEM phase ID']='G100000'+solar_may_2023['GEM phase ID']
# Drop duplicated units (sometimes above/below threshold contain the same units)
solar_may_2023 = solar_may_2023[~solar_may_2023['GEM phase ID'].duplicated(keep=False)]

#JAN 2023
solar_jan_2023_20plus=pandas.read_excel("./Retrospective GIPT/solar/Global-Solar-Power-Tracker-January-2023.xlsx",'Data')
solar_jan_2023_sub=pandas.read_excel("./Retrospective GIPT/solar/Global-Solar-Power-Tracker-January-2023.xlsx","Below Threshold")
solar_jan_2023=pandas.concat([solar_jan_2023_20plus,solar_jan_2023_sub])
solar_jan_2023['GEM phase ID'] = solar_jan_2023['GEM phase ID'].str[1:]
solar_jan_2023['GEM phase ID']='G100000'+solar_jan_2023['GEM phase ID']
# Drop duplicated units (sometimes above/below threshold contain the same units)
solar_jan_2023 = solar_jan_2023[~solar_jan_2023['GEM phase ID'].duplicated(keep=False)]

#MAY 2022
solar_may_2022=pandas.read_excel("./Retrospective GIPT/solar/Global-Solar-Power-Tracker-May-2022.xlsx",'Data')
solar_may_2022['Status'] = solar_may_2022['Status'].replace('development', 'pre-construction')
solar_may_2022['GEM phase ID'] = solar_may_2022['GEM phase ID'].str[1:]
solar_may_2022['GEM phase ID']='G100000'+solar_may_2022['GEM phase ID']
# Drop duplicated units (sometimes above/below threshold contain the same units)
solar_may_2022 = solar_may_2022[~solar_may_2022['GEM phase ID'].duplicated(keep=False)]

## ---- Build up lists of units that are common to each interation of past trackers
'''
Note that this excludes units that get deleted in later tracker editions and so would only have partial tracker history
i.e., only the history of units in most recent tracker are traced, deleted units with partial history are not.
Note, that this also excludes units with changing unit ids. This is a harmonisation issue affecting all power trackers to greater/lesser extent.
'''
solar_feb_2025_solar_jun_2024=list(set(solar_feb_2025['GEM phase ID'])&set(solar_jun_2024['GEM phase ID']))
solar_feb_2025_solar_dec_2023=list(set(solar_feb_2025['GEM phase ID'])&set(solar_jun_2024['GEM phase ID'])&set(solar_dec_2023['GEM phase ID']))
solar_feb_2025_solar_may_2023=list(set(solar_feb_2025['GEM phase ID'])&set(solar_jun_2024['GEM phase ID'])&set(solar_dec_2023['GEM phase ID'])&set(solar_may_2023['GEM phase ID']))
solar_feb_2025_solar_jan_2023=list(set(solar_feb_2025['GEM phase ID'])&set(solar_jun_2024['GEM phase ID'])&set(solar_dec_2023['GEM phase ID'])&set(solar_may_2023['GEM phase ID'])&set(solar_jan_2023['GEM phase ID']))
solar_feb_2025_solar_may_2022=list(set(solar_feb_2025['GEM phase ID'])&set(solar_jun_2024['GEM phase ID'])&set(solar_dec_2023['GEM phase ID'])&set(solar_may_2023['GEM phase ID'])&set(solar_jan_2023['GEM phase ID'])&set(solar_may_2022['GEM phase ID']))

# New status columns
solar_feb_2025['Status Feb 2025']=np.nan
solar_feb_2025['Status Jun 2024']=np.nan
solar_feb_2025['Status Dec 2023']=np.nan
solar_feb_2025['Status May 2023']=np.nan
solar_feb_2025['Status Jan 2023']=np.nan
solar_feb_2025['Status May 2022']=np.nan
#Re-index
solar_feb_2025=solar_feb_2025.set_index('GEM phase ID')
solar_jun_2024=solar_jun_2024.set_index('GEM phase ID')
solar_dec_2023=solar_dec_2023.set_index('GEM phase ID')
solar_may_2023=solar_may_2023.set_index('GEM phase ID')
solar_jan_2023=solar_jan_2023.set_index('GEM phase ID')
solar_may_2022=solar_may_2022.set_index('GEM phase ID')
#Find and assign past statuses to relevant new status columns
solar_feb_2025['Status Feb 2025']=solar_feb_2025['Status']
solar_feb_2025.loc[solar_feb_2025_solar_jun_2024,'Status Jun 2024']=solar_jun_2024.loc[solar_feb_2025_solar_jun_2024,'Status']
solar_feb_2025.loc[solar_feb_2025_solar_dec_2023,'Status Dec 2023']=solar_dec_2023.loc[solar_feb_2025_solar_dec_2023,'Status']
solar_feb_2025.loc[solar_feb_2025_solar_may_2023,'Status May 2023']=solar_may_2023.loc[solar_feb_2025_solar_may_2023,'Status']
solar_feb_2025.loc[solar_feb_2025_solar_jan_2023,'Status Jan 2023']=solar_jan_2023.loc[solar_feb_2025_solar_jan_2023,'Status']
solar_feb_2025.loc[solar_feb_2025_solar_may_2022,'Status May 2022']=solar_may_2022.loc[solar_feb_2025_solar_may_2022,'Status']

## ---- Combine 'Past Statuses' in a new column as a big list ('nan' values where projects didn't exisit in previous trackers)
## ---- e.g. ['pre-construction', 'pre-construction', 'pre-construction', 'shelved', 'shelved - inferred 2 y', 'cancelled - inferred 4 y']
solar_feb_2025['Past Statuses'] = solar_feb_2025[['Status May 2022','Status Jan 2023','Status May 2023','Status Dec 2023','Status Jun 2024','Status Feb 2025']].values.tolist()

## Count the most common 'Past Statuses' (as expected, [nan, nan, nan, nan, nan, operating], is the most common, as many new operatign projects added in latest GSPT edition)
counts = solar_feb_2025['Past Statuses'].apply(tuple).value_counts()

# Convert index back to list for clarity
counts.index = counts.index.map(list)
#counts.to_csv("./counts.csv")

## ---- DESCRIPTIVE STATS:

## How many units don't change status?
def count_distinct_strings(strings):
    # Keep only valid strings, exclude NaNs and non-string values
    filtered = [s for s in strings if isinstance(s, str) and s.lower() != 'nan']
    return len(set(filtered))

#89% of units don't change status
pandas.DataFrame(counts).loc[(counts.reset_index()['Past Statuses'].apply(count_distinct_strings)==1).values]['count'].sum()/len(solar_feb_2025)

## ---- HOW MANY UNITS HAVE FULL 'STATUS HISTORY'
def count_nans(status_list):
    if isinstance(status_list, list):
        return sum(1 for s in status_list if s != s)  # NaN is the only value that is not equal to itself
    return 0

#12% of projects appear in all 6 editions of the solar tracker
pandas.DataFrame(counts).loc[(counts.reset_index()['Past Statuses'].apply(count_nans)==0).values]['count'].sum()/len(solar_feb_2025)
#39% appear in the last 4 editions.
pandas.DataFrame(counts).loc[(counts.reset_index()['Past Statuses'].apply(count_nans)<=2).values]['count'].sum()/len(solar_feb_2025)

# filter units where there's at least one change in status
pandas.DataFrame(counts).loc[(counts.reset_index()['Past Statuses'].apply(count_distinct_strings)!=1).values]
# 

## ---- ANALYSIS OF CHANGES OVER TIME:

## ---- 1: how long is the construction phase?

df_statuses=counts.reset_index()

# define required strings
required_statuses = {'construction', 'pre-construction', 'operating'}

# Check if all required statuses are present
def contains_all_required(status_list):
    if isinstance(status_list, list):
        return required_statuses.issubset(set(status_list))
    return False

# Filter for units that have status history containing: 'construction', 'pre-construction', 'operating'
matching_rows = df_statuses[df_statuses['Past Statuses'].apply(contains_all_required)]

# Count instances of 'construction'
matching_rows['construction_count'] = matching_rows['Past Statuses'].apply(lambda lst: sum(1 for status in lst if status == 'construction'))


#2: how long is the pre-construction phase?

#3: how often do projects get cancelled or shelved after becoming announced/pre-construction/construction/operating

#4: what proportion of projects go operational each year?




## ---- MAIN PERMUTATIONS

#classic route
construction > operating
pre-construction > construction > operating
announced > pre-construction > construction > operating

#skipped route
pre-construction > operating
announced > operating
announced > construction > operating

#cancelled route
construction > cancelled
pre-construction > cancelled
announced > cancelled
construction > shelved
pre-construction > shelved
announced > shelved


















