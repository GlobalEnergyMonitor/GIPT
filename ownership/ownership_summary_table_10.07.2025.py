import pandas
import numpy as np
import numpy
from numpy import *
import re 
import pandas as pd
'''
Used to make the summary table: https://docs.google.com/spreadsheets/d/1_u4z5OgnCaXjvru-vlhw17q-tmRpqvr1ujaoLlJc9Nc/edit?gid=158050170#gid=158050170

This summary table is not yet public

The processing steps:
1) Load GIPT
2) Adjust solar capacity to AC values (as is standard in reporting summarized solar)
3) Loop technologies and status, applying a helper function that apportions ownership:
	a) according to the [%] share in the 'Parent' field for combustion trackers and 'Owner' field for non combustion
	b) gap filling where any entity lacks a % share by equally sharing the remaining share of the total
	c) filling any blanks in Parent entity with 'unknown'
4) Makes a few labelling and formatting adjustments to the resulting dataframe
'''

# ----- LOAD THE GIPT (TAKES 1-2MINS)
gipt=pandas.read_excel('./Global Integrated Power April 2025.xlsx',sheet_name='Power facilities')

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

# ----- CONVERT SOLAR ALL TO MWac FOR SUMMARY TABLES (TAKES 3-4 MINS)
# ----- DIRECT COPY PASTE FORM: https://github.com/GlobalEnergyMonitor/Renewables_Others/blob/main/SolarCode/ConvertToMWac.py
# ----- ***NOTE*** BE SURE TO USE LATEST SOLAR TRACKER FILE

df_file="./Global-Solar-Power-Tracker-February-2025.xlsx"

dfs=[pandas.read_excel(df_file, sheet_name=i) for i in ['20 MW+','1-20 MW']]
df = pandas.concat(dfs).reset_index()

# this is the conversion between DC to AC. Value from TransitionZero
conversionFactor = 0.87

# this is the minimum count number in order to use country or subregion value rather than subregion or region value
minval = 30

# save original capacity to a new column
df['Capacity (MW) orig'] = df['Capacity (MW)']

# if capacity rating is DC, convert to AC
df.loc[df['Capacity Rating'] == 'MWp/dc', 'Capacity (MW)'] = df['Capacity (MW) orig']*conversionFactor

# if capacity rating is unknown convert the value based on the probability it's MWac based on the country/subregion/region

# I think we don't want to have government datasets biasing this, so we won't include projects that have an other location or phase ID that's not WEPP or WikiSolar
## replace nans with blanks
df.fillna("", inplace=True)
## loop through every Other IDs location and Other IDs phase and remove WEPP & WKSL so that we can ignore anything with an entry in the Other IDs columns
for index, row in df.iterrows():
    loc_id = row['Other IDs (location)']
    phase_id = row['Other IDs (unit/phase)']
    # split the ID by commas
    loc_id_list = loc_id.split(",")
    phase_id_list = phase_id.split(",")
    # create a temporary list
    loc_tmp_lst = []
    phase_tmp_lst = []
    # remove any location ID that start with WEPP or WKSL
    for id in loc_id_list:
        id = id.strip()
        if id.startswith("WEPP") | id.startswith("WKSL"):
            pass
        else:
            loc_tmp_lst.append(id)
    # remove any location ID that start with WEPP
    for id in phase_id_list:
        id = id.strip()
        if id.startswith("WEPP") | id.startswith("WKSL"):
            pass
        else:
            phase_tmp_lst.append(id)
    # join tmp_lst together as a comma delimited string
    new_loc_id = ",".join(map(str, loc_tmp_lst))
    new_phase_id = ",".join(map(str, phase_tmp_lst))
    # write this to the dataframe row
    df.loc[index, 'Other IDs (location)'] = new_loc_id
    df.loc[index, 'Other IDs (unit/phase)'] = new_phase_id

## compute liklihood based on the region
regions = df['Region'].unique().tolist()
region_prob = []
for region in regions:
    countsac = len(df[(df['Region'] == region) & (df['Capacity Rating'] == 'MWac') & (df['Other IDs (unit/phase)'] == '') & (df['Other IDs (location)'] == '')])
    countsdc = len(df[(df['Region'] == region) & (df['Capacity Rating'] == 'MWp/dc') & (df['Other IDs (unit/phase)'] == '') & (df['Other IDs (location)'] == '')])
    region_prob.append(countsac/(countsac+countsdc))

## compute liklihood based on the sub-region. If ac+dc counts are less than minval use region numbers
subregions = df['Subregion'].unique().tolist()
subregion_prob = []
for subregion in subregions:
    countsac = len(df[(df['Subregion'] == subregion) & (df['Capacity Rating'] == 'MWac') & (
                df['Other IDs (unit/phase)'] == '') & (df['Other IDs (location)'] == '')])
    countsdc = len(df[(df['Subregion'] == subregion) & (df['Capacity Rating'] == 'MWp/dc') & (
                df['Other IDs (unit/phase)'] == '') & (df['Other IDs (location)'] == '')])
    if countsac+countsdc >= minval:
        subregion_prob.append(countsac / (countsac + countsdc))
    else:
        # get the region associated with subregions
        rgn = df.loc[df['Subregion'] == subregion, 'Region'].iloc[0]
        # find that region's probability
        idx = regions.index(rgn)
        subregion_prob.append(region_prob[idx])


## compute liklihood based on the country. If ac+dc counts are less than 50 use subregion numbers
countries = df['Country/Area'].unique().tolist()
country_prob = []
for country in countries:
    countsac = len(df[(df['Country/Area'] == country) & (df['Capacity Rating'] == 'MWac') & (
                df['Other IDs (unit/phase)'] == '') & (df['Other IDs (location)'] == '')])
    countsdc = len(df[(df['Country/Area'] == country) & (df['Capacity Rating'] == 'MWp/dc') & (
                df['Other IDs (unit/phase)'] == '') & (df['Other IDs (location)'] == '')])
    if countsac+countsdc >= minval:
        country_prob.append(countsac / (countsac + countsdc))
    else:
        # get the subregion associated with country
        subr = df.loc[df['Country/Area'] == country, 'Subregion'].iloc[0]
        # find that region's probability
        idx = subregions.index(subr)
        country_prob.append(subregion_prob[idx])

# Adjust 'unknown' capacities to MWac
for index, row in df.iterrows():
    if row['Capacity Rating'] == 'unknown':
        idx = countries.index(row['Country/Area'])
        df.at[index, 'Capacity (MW)'] = ((1-conversionFactor)*country_prob[idx] + conversionFactor)*row['Capacity (MW) orig']

# save original capacity rating to a new column and set capacity rating to MWac
df['Capacity Rating orig'] = df['Capacity Rating']
df['Capacity Rating'] = 'MWac'

#Replace gipt capacity values for solar with AC converted values
gipt=gipt.set_index('GEM unit/phase ID')
gipt.loc[df['GEM phase ID'],'Capacity (MW)']=df['Capacity (MW)'].values

# ----- SUMMARY OF CAPACITY PER PARENT/OWNER
# ----- FIRST HANDLE COMBUSTION 'PARENTS' IN A BIG LOOP

# Helper function to parse owners and calculate proportional shares
def parse_parent_with_percentages(row):
    owners_raw = str(row["Parent"])
    capacity = row["Capacity (MW)"]
    # Find all owners and optional percentages
    pattern = r'([^;\[]+?)(?:\s*\[\s*(\d+(?:\.\d+)?)\s*%\s*\])?(?:;|$)'
    matches = re.findall(pattern, owners_raw)
    owners = []
    total_percent = 0
    percent_info = []
    for owner, pct in matches:
        owner = owner.strip()
        if pct:
            percent = float(pct)
            total_percent += percent
            percent_info.append((owner, percent))
        else:
            owners.append(owner)
    # Normalize capacity by percentage or equally split if no percentages
    result = []
    if percent_info:
        for owner, percent in percent_info:
            share = capacity * (percent / 100)
            result.append({
                "Country/area": row["Country/area"],
                "Parent": owner,
                "Capacity (MW)": share
            })
    elif owners:
        share = capacity / len(owners)
        for owner in owners:
            result.append({
                "Country/area": row["Country/area"],
                "Parent": owner,
                "Capacity (MW)": share
            })
    return result

res=[]
for tech in ['coal','oil/gas']:
	for status,status_name in zip([['operating'],['construction'],['pre-construction'],['announced'],['construction','pre-construction','announced']],['operating','construction','pre-construction','announced','in-dev']):
		df_tmp=gipt[(gipt.Type==tech)&(gipt.Status.isin(status))]
		df_tmp.loc[df_tmp.Parent.isnull(),'Parent']='unknown'
		# Expand rows using the helper function
		tmp_rows = []
		for _, row in df_tmp.iterrows():
		    tmp_rows.extend(parse_parent_with_percentages(row))
		df_tmp_expanded = pandas.DataFrame(tmp_rows)
		# Aggregate capacity
		df_tmp_aggregated = df_tmp_expanded.groupby(["Country/area", "Parent"], as_index=False)["Capacity (MW)"].sum()
		# Add rank per country
		df_tmp_aggregated["Rank"] = df_tmp_aggregated.groupby("Country/area")["Capacity (MW)"].rank(method="dense", ascending=False).astype(int)
		# Sort
		df_tmp_aggregated.sort_values(by=["Country/area", "Rank"], inplace=True)
		# Calculate percentage of total capacity per country
		df_tmp_aggregated["Total Capacity (MW)"] = df_tmp_aggregated.groupby("Country/area")["Capacity (MW)"].transform("sum")
		df_tmp_aggregated["Percentage of Total Capacity (%)"] = (df_tmp_aggregated["Capacity (MW)"] / df_tmp_aggregated["Total Capacity (MW)"])
		# Calculate cumulative percentage of total capacity per country
		df_tmp_aggregated["Cumulative Percentage (%)"] = df_tmp_aggregated.groupby("Country/area")["Percentage of Total Capacity (%)"].cumsum()
		# Sort again for clarity
		df_tmp_aggregated.sort_values(by=["Country/area", "Rank"], inplace=True)
		# Add some indexing/categories
		df_tmp_aggregated['Technology']=tech
		df_tmp_aggregated['Status']=status_name
		# Repeat sets above but aggregating globally
		global_df_tmp_aggregated=df_tmp_aggregated.groupby(['Parent', 'Technology']).agg({'Capacity (MW)': 'sum',}).reset_index().sort_values('Capacity (MW)',ascending=False)
		global_df_tmp_aggregated['Country/area']='Global'
		global_df_tmp_aggregated["Total Capacity (MW)"] = global_df_tmp_aggregated.groupby("Country/area")["Capacity (MW)"].transform("sum")
		global_df_tmp_aggregated["Percentage of Total Capacity (%)"] = (global_df_tmp_aggregated["Capacity (MW)"] / global_df_tmp_aggregated["Total Capacity (MW)"])
		global_df_tmp_aggregated["Cumulative Percentage (%)"] = global_df_tmp_aggregated.groupby("Country/area")["Percentage of Total Capacity (%)"].cumsum()
		global_df_tmp_aggregated=global_df_tmp_aggregated[global_df_tmp_aggregated['Capacity (MW)']!=0.]
		global_df_tmp_aggregated['Rank']=global_df_tmp_aggregated['Capacity (MW)'].rank(method="dense", ascending=False).astype(int)
		global_df_tmp_aggregated['Status']=status_name
		# Stick togther country and global outputs per technology
		res.append(pandas.concat([global_df_tmp_aggregated,df_tmp_aggregated]))

out1=pandas.concat(res)
out1["Technology"] = out1["Technology"].str.title()


# ----- NOW HANDLE NON-COMBUSTION 'OWNERS' IN A BIG LOOP

# Helper function to parse owners and calculate proportional shares
def parse_owners_with_percentages(row):
    owners_raw = str(row["Owner"])
    capacity = row["Capacity (MW)"]
    # Find all owners and optional percentages
    pattern = r'([^;\[]+?)(?:\s*\[\s*(\d+(?:\.\d+)?)\s*%\s*\])?(?:;|$)'
    matches = re.findall(pattern, owners_raw)
    owners = []
    total_percent = 0
    percent_info = []
    for owner, pct in matches:
        owner = owner.strip()
        if pct:
            percent = float(pct)
            total_percent += percent
            percent_info.append((owner, percent))
        else:
            owners.append(owner)
    # Normalize capacity by percentage or equally split if no percentages
    result = []
    if percent_info:
        for owner, percent in percent_info:
            share = capacity * (percent / 100)
            result.append({
                "Country/area": row["Country/area"],
                "Owner": owner,
                "Capacity (MW)": share
            })
    elif owners:
        share = capacity / len(owners)
        for owner in owners:
            result.append({
                "Country/area": row["Country/area"],
                "Owner": owner,
                "Capacity (MW)": share
            })
    return result


res2=[]
for tech in ['solar','wind','hydropower','bioenergy','geothermal','nuclear']:
	for status,status_name in zip([['operating'],['construction'],['pre-construction'],['announced'],['construction','pre-construction','announced']],['operating','construction','pre-construction','announced','in-dev']):
		df_tmp=gipt[(gipt.Type==tech)&(gipt.Status.isin(status))]
		df_tmp.loc[df_tmp.Owner.isnull(),'Owner']='unknown'
		# Expand rows using the helper function
		tmp_rows = []
		for _, row in df_tmp.iterrows():
		    tmp_rows.extend(parse_owners_with_percentages(row))
		df_tmp_expanded = pandas.DataFrame(tmp_rows)
		# Aggregate capacity
		df_tmp_aggregated = df_tmp_expanded.groupby(["Country/area", "Owner"], as_index=False)["Capacity (MW)"].sum()
		# Add rank per country
		df_tmp_aggregated["Rank"] = df_tmp_aggregated.groupby("Country/area")["Capacity (MW)"].rank(method="dense", ascending=False).astype(int)
		# Sort
		df_tmp_aggregated.sort_values(by=["Country/area", "Rank"], inplace=True)
		# Calculate percentage of total capacity per country
		df_tmp_aggregated["Total Capacity (MW)"] = df_tmp_aggregated.groupby("Country/area")["Capacity (MW)"].transform("sum")
		df_tmp_aggregated["Percentage of Total Capacity (%)"] = (df_tmp_aggregated["Capacity (MW)"] / df_tmp_aggregated["Total Capacity (MW)"])
		# Calculate cumulative percentage of total capacity per country
		df_tmp_aggregated["Cumulative Percentage (%)"] = df_tmp_aggregated.groupby("Country/area")["Percentage of Total Capacity (%)"].cumsum()
		# Sort again for clarity
		df_tmp_aggregated.sort_values(by=["Country/area", "Rank"], inplace=True)
		df_tmp_aggregated['Technology']=tech
		df_tmp_aggregated['Status']=status_name
		# Repeat sets above but aggregating globally
		global_df_tmp_aggregated=df_tmp_aggregated.groupby(['Owner', 'Technology']).agg({'Capacity (MW)': 'sum',}).reset_index().sort_values('Capacity (MW)',ascending=False)
		global_df_tmp_aggregated['Country/area']='Global'
		global_df_tmp_aggregated["Total Capacity (MW)"] = global_df_tmp_aggregated.groupby("Country/area")["Capacity (MW)"].transform("sum")
		global_df_tmp_aggregated["Percentage of Total Capacity (%)"] = (global_df_tmp_aggregated["Capacity (MW)"] / global_df_tmp_aggregated["Total Capacity (MW)"])
		global_df_tmp_aggregated["Cumulative Percentage (%)"] = global_df_tmp_aggregated.groupby("Country/area")["Percentage of Total Capacity (%)"].cumsum()
		global_df_tmp_aggregated=global_df_tmp_aggregated[global_df_tmp_aggregated['Capacity (MW)']!=0.]
		global_df_tmp_aggregated['Rank']=global_df_tmp_aggregated['Capacity (MW)'].rank(method="dense", ascending=False).astype(int)
		global_df_tmp_aggregated['Status']=status_name
		# Stick togther country and global outputs per technology
		res2.append(pandas.concat([global_df_tmp_aggregated,df_tmp_aggregated]))

out2=pandas.concat(res2)
out2["Technology"] = out2["Technology"].str.title()

# RENAME TO ALLOW STICKING TOGETHER OF DATAFRAMES
out2.rename(columns={'Owner': 'Parent'}, inplace=True)

# STICK TOGETHER DATAFRAMES
owners_df=pandas.concat([out1,out2])[['Technology','Country/area','Status','Parent','Capacity (MW)','Rank','Percentage of Total Capacity (%)','Cumulative Percentage (%)']]

# RENAME SOME THINGS

owners_df['Status'] = owners_df['Status'].replace({
    'operating': 'Operating',
    'pre-construction': 'Pre-construction',
    'construction':'Construction',
    'announced':'Announced',
    'in-dev':'Construction+Pre-construction+Announced'
})

owners_df.to_csv('./ownership_summary_table.csv',encoding='utf-8-sig',index=False)


