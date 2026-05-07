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
gipt=pandas.read_excel('./Global Integrated Power March 2026 II.xlsx',sheet_name='Power facilities')

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

df_file="./Global-Solar-Power-Tracker-February-2026.xlsx"

df=pandas.read_excel(df_file, 'Utility-Scale (1 MW+)')

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
gipt.loc[df['GEM phase ID'],'Capacity rating (solar only)']=df['Capacity (MW)'].values

# ----- SUMMARY OF CAPACITY PER PARENT/OWNER
# ----- FIRST HANDLE COMBUSTION 'PARENTS' IN A BIG LOOP

# Helper function to parse owners and calculate proportional shares
def parse_parent_with_percentages(row):
    owners_raw = str(row["Parent(s)"])
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
                "Parent(s)": owner,
                "Capacity (MW)": share
            })
    elif owners:
        share = capacity / len(owners)
        for owner in owners:
            result.append({
                "Country/area": row["Country/area"],
                "Parent(s)": owner,
                "Capacity (MW)": share
            })
    return result

res=[]
for tech in ['coal','oil/gas']:
	for status,status_name in zip([['operating'],['construction'],['pre-construction'],['announced'],['construction','pre-construction','announced']],['operating','construction','pre-construction','announced','in-dev']):
		df_tmp=gipt[(gipt.Type==tech)&(gipt.Status.isin(status))]
		df_tmp.loc[df_tmp['Parent(s)'].isnull(),'Parent(s)']='unknown'
		# Expand rows using the helper function
		tmp_rows = []
		for _, row in df_tmp.iterrows():
		    tmp_rows.extend(parse_parent_with_percentages(row))
		df_tmp_expanded = pandas.DataFrame(tmp_rows)
		# Aggregate capacity
		df_tmp_aggregated = df_tmp_expanded.groupby(["Country/area", "Parent(s)"], as_index=False)["Capacity (MW)"].sum()
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
		global_df_tmp_aggregated=df_tmp_aggregated.groupby(['Parent(s)', 'Technology']).agg({'Capacity (MW)': 'sum',}).reset_index().sort_values('Capacity (MW)',ascending=False)
		global_df_tmp_aggregated['Country/area']='World'
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
    owners_raw = str(row["Owner(s)"])
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
                "Owner(s)": owner,
                "Capacity (MW)": share
            })
    elif owners:
        share = capacity / len(owners)
        for owner in owners:
            result.append({
                "Country/area": row["Country/area"],
                "Owner(s)": owner,
                "Capacity (MW)": share
            })
    return result


res2=[]
for tech in ['utility-scale solar','wind','hydropower','bioenergy','geothermal','nuclear']:
	for status,status_name in zip([['operating'],['construction'],['pre-construction'],['announced'],['construction','pre-construction','announced']],['operating','construction','pre-construction','announced','in-dev']):
		df_tmp=gipt[(gipt.Type==tech)&(gipt.Status.isin(status))]
		df_tmp.loc[df_tmp['Owner(s)'].isnull(),'Owner(s)']='unknown'
		# Expand rows using the helper function
		tmp_rows = []
		for _, row in df_tmp.iterrows():
		    tmp_rows.extend(parse_owners_with_percentages(row))
		df_tmp_expanded = pandas.DataFrame(tmp_rows)
		# Aggregate capacity
		df_tmp_aggregated = df_tmp_expanded.groupby(["Country/area", "Owner(s)"], as_index=False)["Capacity (MW)"].sum()
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
		global_df_tmp_aggregated=df_tmp_aggregated.groupby(['Owner(s)', 'Technology']).agg({'Capacity (MW)': 'sum',}).reset_index().sort_values('Capacity (MW)',ascending=False)
		global_df_tmp_aggregated['Country/area']='World'
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
out2.rename(columns={'Owner(s)': 'Parent(s)'}, inplace=True)

# STICK TOGETHER DATAFRAMES
owners_df=pandas.concat([out1,out2])[['Technology','Country/area','Status','Parent(s)','Capacity (MW)','Rank','Percentage of Total Capacity (%)','Cumulative Percentage (%)']]

# RENAME SOME THINGS

owners_df['Status'] = owners_df['Status'].replace({
    'operating': 'Operating',
    'pre-construction': 'Pre-construction',
    'construction':'Construction',
    'announced':'Announced',
    'in-dev':'Construction+Pre-construction+Announced'
})

#owners_df['Capacity (MW)']=owners_df['Capacity (MW)']/1000
#owners_df=owners_df.rename(columns={"Capacity (MW)": "Capacity (GW)"})
owners_df.to_csv('./ownership_summary_table.csv',encoding='utf-8-sig',index=False)



#####################################################################################
##
## THIS SECTION CONVERTS owners_df INTO FORMAT THAT'S FILTERABLE IN PUBLIC SUMMARY TABLE
##
#####################################################################################

# -----------------------------
# file paths
# -----------------------------
input_file = "ownership_summary_table.csv"
output_file = "./capacity_by_owner_public_from_summary_long.xlsx"

# -----------------------------
# read data
# -----------------------------
#df = pd.read_csv(input_file)

# read long table
df = owners_df.copy()

# -----------------------------
# optional cleanup
# -----------------------------
text_cols = ["Country/area", "Technology", "Status", "Parent(s)"]
for c in text_cols:
    if c in df.columns:
        df[c] = df[c].astype(str).str.strip()

# make numeric columns numeric where possible
num_cols = [
    "Rank",
    "Capacity (GW)",
    "Percentage of Total Capacity (%)",
    "Cumulative Percentage (%)"
]
for c in num_cols:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

# -----------------------------
# choose status order
# edit this if your exact labels differ
# -----------------------------
status_order = [
    "Operating",
    "Construction",
    "Pre-construction",
    "Announced",
    "Construction+Pre-construction+Announced"
]

df["Status"] = pd.Categorical(df["Status"], categories=status_order, ordered=True)

# -----------------------------
# sort rows so tie ordering is stable
# this matters because Rank has ties
# -----------------------------
sort_cols = [
    "Country/area",
    "Technology",
    "Status",
    "Rank",
    "Capacity (GW)",
    "Parent(s)"
]
sort_ascending = [True, True, True, True, False, True]

df = df.sort_values(sort_cols, ascending=sort_ascending).reset_index(drop=True)

# -----------------------------
# create a unique row id inside each country + technology + status block
# this is the key fix: do NOT pivot on Rank because Rank has ties
# -----------------------------
df["row_id"] = (
    df.groupby(["Country/area", "Technology", "Status"])
      .cumcount() + 1
)

# -----------------------------
# pivot long -> wide
# -----------------------------
value_cols = [
    "Parent(s)",
    "Capacity (GW)",
    "Rank",
    "Percentage of Total Capacity (%)",
    "Cumulative Percentage (%)"
]

wide = df.pivot(
    index=["Country/area", "Technology", "row_id"],
    columns="Status",
    values=value_cols
).reset_index()

# -----------------------------
# flatten multiindex columns
# -----------------------------
pretty_value_names = {
    "Parent(s)": "Parent entity",
    "Capacity (GW)": "Capacity (GW)",
    "Rank": "Rank",
    "Percentage of Total Capacity (%)": "% of total capacity",
    "Cumulative Percentage (%)": "Cumulative %"
}

flat_cols = []
for col in wide.columns:
    if isinstance(col, tuple):
        left, right = col
        if right == "" or pd.isna(right):
            flat_cols.append(left)
        else:
            flat_cols.append(f"{right} - {pretty_value_names[left]}")
    else:
        flat_cols.append(col)

wide.columns = flat_cols

# -----------------------------
# optional: put columns in a neat order
# only keep columns that actually exist
# -----------------------------
desired_cols = [
    "Country/area",
    "Technology",
    "row_id",

    "Operating - Rank",
    "Operating - Parent entity",
    "Operating - Capacity (GW)",
    "Operating - % of total capacity",
    "Operating - Cumulative %",

    "Construction - Rank",
    "Construction - Parent entity",
    "Construction - Capacity (GW)",
    "Construction - % of total capacity",
    "Construction - Cumulative %",

    "Pre-construction - Rank",
    "Pre-construction - Parent entity",
    "Pre-construction - Capacity (GW)",
    "Pre-construction - % of total capacity",
    "Pre-construction - Cumulative %",

    "Announced - Rank",
    "Announced - Parent entity",
    "Announced - Capacity (GW)",
    "Announced - % of total capacity",
    "Announced - Cumulative %",

    "Construction+Pre-construction+Announced - Rank",
    "Construction+Pre-construction+Announced - Parent entity",
    "Construction+Pre-construction+Announced - Capacity (GW)",
    "Construction+Pre-construction+Announced - % of total capacity",
    "Construction+Pre-construction+Announced - Cumulative %",
]

wide = wide[[c for c in desired_cols if c in wide.columns]]

# ---------------------------------
# custom sort: force Global to top, then all others alphabetical
# ---------------------------------
wide["Country/area"] = wide["Country/area"].astype(str).str.strip()

# optional debug check
print([x for x in wide["Country/area"].dropna().unique() if "glob" in x.lower()])

# build explicit country order
other_countries = sorted([c for c in wide["Country/area"].dropna().unique() if c != "World"])
country_order = ["World"] + other_countries

wide["Country/area"] = pd.Categorical(
    wide["Country/area"],
    categories=country_order,
    ordered=True
)

wide = (
    wide.sort_values(
        by=["Country/area", "Technology", "row_id"],
        ascending=[True, True, True]
    )
    .drop(columns=["row_id"], errors="ignore")
    .reset_index(drop=True)
)

# turn Country/area back into plain text after sorting
wide["Country/area"] = wide["Country/area"].astype(str)

# -----------------------------
# write output
# -----------------------------
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    wide.to_excel(writer, sheet_name="Capacity by owner - public", index=False)


