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

'''
1) text config file (the sentence under the drop down)
2) tickers
3) chart #1: OPERATNG
4) chart #2: CONSTRUCTION
5) chart #3: DEVELOPMENT
6) chart #4: FOSSIL / NON-FOSSIL

'''

################################################################################################################################################
#0: LOAD THE GIPT DATA
gipt=pandas.read_excel('./Global-Integrated-Power-March-2026-II.xlsx',sheet_name='Power facilities')

#
## ADJUST 'not found' VALUES IN COMPILED EXCEL
gipt.loc[gipt['Capacity (MW)']=='not found','Capacity (MW)']=np.nan
## CHANGE 'Capacity' TO FLOATS
gipt['Capacity (MW)']=gipt['Capacity (MW)'].astype(float)
gipt['Capacity (MW)']=gipt['Capacity (MW)'].fillna(0.0)
# EXCLUDE MISSING START DATES 
gipt.loc[gipt['Start year']=='not found','Start year']=np.nan
gipt['Start year']=gipt['Start year'].astype(float)
gipt.loc[gipt['Retired year']=='not found','Retired year']=np.nan
gipt['Retired year']=gipt['Retired year'].astype(float)
gipt.loc[gipt.Status=='cancelled - inferred 4 y','Status']='cancelled'
gipt.loc[gipt.Status=='shelved - inferred 2 y','Status']='shelved'





iea_reg_map=pandas.read_excel("./iea_region_code.xlsx")
regions=['EU27','G7']
status=['construction','pre-construction','announced']
type=['wind','utility-scale solar','hydropower']
res=[]

#pre 2030
gipt[(gipt['Start year'].isin([2026,2027,2028,2029,2030]))&(gipt.Status.isin(status))&(gipt.Type.isin(type))&(gipt.Technology!='pumped storage')].groupby('Status')['Capacity (MW)'].sum()/1000
#undated
gipt[(gipt['Start year'].isnull())&(gipt.Status.isin(status))&(gipt.Type.isin(type))&(gipt.Technology!='pumped storage')].groupby('Status')['Capacity (MW)'].sum()/1000


#World
tmp=pandas.concat([gipt[(gipt['Start year'].isin([2026,2027,2028,2029,2030]))&(gipt.Status.isin(status))&(gipt.Type.isin(type))&(gipt.Technology!='pumped storage')].groupby('Status')['Capacity (MW)'].sum()/1000,gipt[(gipt['Start year'].isnull())&(gipt.Status.isin(status))&(gipt.Type.isin(type))&(gipt.Technology!='pumped storage')].groupby('Status')['Capacity (MW)'].sum()/1000],axis=1)
tmp.columns=['pre-2030','undated']

res.append(tmp)

#Regions
for reg in regions:
    names=list(iea_reg_map[iea_reg_map[reg]=='Yes'].gem_name.unique())
    tmp=pandas.concat([gipt[(gipt['Start year'].isin([2026,2027,2028,2029,2030]))&(gipt['Country/area'].isin(names))&(gipt.Status.isin(status))&(gipt.Type.isin(type))&(gipt.Technology!='pumped storage')].groupby('Status')['Capacity (MW)'].sum()/1000,gipt[(gipt['Start year'].isnull())&(gipt['Country/area'].isin(names))&(gipt.Status.isin(status))&(gipt.Type.isin(type))&(gipt.Technology!='pumped storage')].groupby('Status')['Capacity (MW)'].sum()/1000],axis=1)
    tmp.columns=['pre-2030','undated']
    res.append(tmp)

#Countries
for country in ['China','India']:
    tmp=pandas.concat([gipt[(gipt['Start year'].isin([2026,2027,2028,2029,2030]))&(gipt['Country/area']==country)&(gipt.Status.isin(status))&(gipt.Type.isin(type))&(gipt.Technology!='pumped storage')].groupby('Status')['Capacity (MW)'].sum()/1000,gipt[(gipt['Start year'].isnull())&(gipt['Country/area'].isin(names))&(gipt.Status.isin(status))&(gipt.Type.isin(type))&(gipt.Technology!='pumped storage')].groupby('Status')['Capacity (MW)'].sum()/1000],axis=1)
    tmp.columns=['pre-2030','undated']
    res.append(tmp)


