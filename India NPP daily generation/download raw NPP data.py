########################################################################################
#
# DOWNLOAD 'DGR-2' REPORT FROM NATIONAL POWER PORTAL
# DAILY GRID CONNECTED GENERATION FOR COAL, HYDRO, NUCELAR, GAS/DIESEL
#
########################################################################################

import wget
from calendar import monthrange,month_name
import glob

#DOWNLOAD DAILY PDF FILES (Sept 2017- April 2018)
output_directory='./raw NPP data/'
for year, month in [(y, m) for y in (2017, 2018) for m in range(1, 13) if (y == 2017 and m >= 9) or (y == 2018 and m <= 4)]:
	for day in range(1,monthrange(year, month)[1]+1):
		if len(glob.glob((output_directory+"/"+str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)+".pdf")))==0:
			try:
				url="https://npp.gov.in/public-reports/cea/daily/dgr/"+str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)+"/dgr2-"+str(year)+"-"+str(month).zfill(2)+"-"+str(day).zfill(2)+".pdf"
				filename = wget.download(url, out=output_directory+"/"+str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)+".pdf")
			except Exception:
				str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)


#DOWNLOAD DAILY XLS FILES
output_directory='./raw NPP data/'

for year in range(2018,2026):
	for month in range(1,13):
		for day in range(1,monthrange(year, month)[1]+1):
			if len(glob.glob((output_directory+"/"+str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)+".xls")))==0:
				try:
					url="https://npp.gov.in/public-reports/cea/daily/dgr/"+str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)+"/dgr2-"+str(year)+"-"+str(month).zfill(2)+"-"+str(day).zfill(2)+".xls"
					filename = wget.download(url, out=output_directory+"/"+str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)+".xls")
				except Exception:
					str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)




########################################################################################
#
# FIRST CONVERT PDFS TO EXCEL
#
########################################################################################

import numpy as np
import xlrd
import re
import tabula
import pandas as pd 

#(1) GET ROWS OF PLANT AND UNIT WITH DATA. DONT INCLUDE STATE TOTALS. JUST EACH PLANT/UNIT

INDIA_REGIONS = [
    # States
    "ANDHRA PRADESH",
    "ARUNACHAL PRADESH",
    "ASSAM",
    "BIHAR",
    "CHHATTISGARH",
    "GOA",
    "GUJARAT",
    "HARYANA",
    "HIMACHAL PRADESH",
    "JHARKHAND",
    "KARNATAKA",
    "KERALA",
    "MADHYA PRADESH",
    #"MAHARASHTRA",
    "MANIPUR",
    "MEGHALAYA",
    "MIZORAM",
    "NAGALAND",
    "ODISHA",
    "PUNJAB",
    #"RAJASTHAN",
    "SIKKIM",
    "TAMIL NADU",
    "TELANGANA",
    "TRIPURA",
    "UTTAR PRADESH",
    "UTTARAKHAND",
    "WEST BENGAL",
    # Union Territories
    "ANDAMAN AND NICOBAR ISLANDS",
    "CHANDIGARH",
    "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "DELHI",
    "JAMMU AND KASHMIR",
    "LADAKH",
    "LAKSHADWEEP",
    "PUDUCHERRY",
    "ANDAMAN & NICOBAR ISLANDS",
    "BHUTAN IMP.",
	"BHUTAN"
]
exclusions=['POWER STATION','REGION WISE, STATE WISE, SECTOR WISE','NORTHERN','SOUTHERN','WESTERN','EASTERN','NORTH EASTERN','REGION TOTAL','STATE TOTAL','SECTOR: ','SECTOR:','TYPE:','REGION WISE','POWER STATION','Remarks:-','Report Version :-','THER (GT)', 'HYDRO', 'NUCLEAR', 'THER (DG)','STATE SECTOR', 'PVT SECTOR', 'CENTRAL SECTOR','THER (GT)','THERMAL']+INDIA_REGIONS


##FOR PDFS

output_directory='./parsed NPP data/'

for year, month in [(y, m) for y in (2017, 2018) for m in range(1, 13) if (y == 2017 and m >= 9) or (y == 2018 and m <= 4)]:
		for day in range(1,monthrange(year, month)[1]+1):
			if len(glob.glob((output_directory+"/"+str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)+".csv")))==0:
				try:
					# LOOP PDF FILES
					dfs = tabula.read_pdf(
					    "https://npp.gov.in/public-reports/cea/daily/dgr/"+str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)+"/dgr2-"+str(year)+"-"+str(month).zfill(2)+"-"+str(day).zfill(2)+".pdf",
					    pages="all",
					    multiple_tables=True,
					    lattice=True
					)
					df = pd.concat([i[2:] for i in dfs], ignore_index=True)
					df.columns = [i for i in range(len(df.columns))]
					# CLEAN PDF FILES
					df = df.replace("", np.nan)
					patterns = [rf"(?<!\()(\b{re.escape(word)}\b)(?!\))" for word in exclusions]
					#pattern = "|".join(exclusions)
					pattern = "|".join(re.escape(x) for x in exclusions)
					df=df[~df[0].str.contains(pattern, case=False, na=False)]
					df=df[df[0].notnull()]
					df=df[~df.iloc[:, 1:].isna().all(axis=1)]
					df.insert(loc=1, column="NEW_COL", value=np.nan)
					flags = {"S", "L", "P", "*"}
					NEW_COL_POS = df.columns.get_loc("NEW_COL")
					def is_flag(val):
					    return isinstance(val, str) and val.strip() in flags
					def is_blank(val):
					    if val is None:
					        return True
					    if isinstance(val, float) and np.isnan(val):
					        return True
					    if isinstance(val, str) and val.strip() == "":
					        return True
					    return False
					def fix_row(row):
					    row = row.copy()
					    newcol_val = row.iloc[NEW_COL_POS]
					    # If NEW_COL already has a flag, leave the row as-is
					    if is_flag(newcol_val):
					        return row
					    # Look to the right of NEW_COL
					    right = row.iloc[NEW_COL_POS+1:]
					    # 1) First try to find a FLAG to move into NEW_COL
					    for idx, val in right.items():
					        if is_flag(val):
					            # Put the flag in NEW_COL
					            row.iloc[NEW_COL_POS] = val.strip()
					            # Shift everything to the right of NEW_COL left by one,
					            # dropping the original flag cell
					            shifted = [v for j, v in right.items() if j != idx]
					            shifted.append(np.nan)
					            row.iloc[NEW_COL_POS+1:] = shifted
					            return row
					    # 2) If no flag found, try to find a BLANK to drop & shift
					    for idx, val in right.items():
					        if is_blank(val):
					            # NEW_COL stays whatever it was (likely blank),
					            # but we drop this blank cell and shift others left
					            shifted = [v for j, v in right.items() if j != idx]
					            shifted.append(np.nan)
					            row.iloc[NEW_COL_POS+1:] = shifted
					            return row
					    # No flag and no blank to fix → leave row unchanged
					    return row
					df = df.apply(fix_row, axis=1)
					def split_unit(value):
					    """
					    If the value starts with 'Unit', split into ('Unit', number/label).
					    Otherwise return (value, '').
					    """
					    if not isinstance(value, str):
					        return value, ""
					    value = value.strip()
					    # regex: match "Unit" at start, capture the rest (numbers/letters)
					    m = re.match(r"^Unit\s*(.*)$", value, flags=re.IGNORECASE)
					    if m:
					        unit_number = m.group(1).strip()  # may be '' if no number
					        return "Unit", unit_number
					    else:
					        return value, np.nan
					# Apply to col 0, expand into two new columns
					df[["col0_label", "col0_unit_num"]] = df[0].apply(split_unit).apply(pd.Series)
					# Work on column 1
					s = df.iloc[:, 0]
					# Find rows where the value contains "Unit" (Unit, Unit1, Unit 2, etc.)
					mask = s.astype(str).str.contains(r"\bUnit", case=False, na=False)
					# Set those to NaN, then forward-fill from the previous value
					s_clean = s.mask(mask)
					s_clean = s_clean.ffill()
					# Put back into the dataframe
					df.iloc[:, 0] = s_clean
					# Make sure we’re working from the current state
					# and that col0_unit_num is string-comparable
					s = df["col0_unit_num"].astype(str).str.strip()
					# Indices where col0_unit_num == "1"
					idx_ones = df.index[s == "1"]
					# Indices immediately before those
					idx_prev = idx_ones - 1
					# Keep only those that actually exist in the current df.index
					idx_prev_valid = idx_prev[idx_prev.isin(df.index)]
					# Drop them
					df = df.drop(idx_prev_valid).reset_index(drop=True)
					df=df.dropna(axis=1, how="all")
					#rename
					df.columns=['name','outage_status','capacity','day prog','day gen','month cumm prog','month cumm gen','coal stock','cap under outage','outage_day_time','expected_resync','remarks','col0_label','unit']
					df['datetime']=pd.to_datetime(str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year),format='%d-%m-%Y')
					df=df[['name','unit','outage_status','capacity','day prog','day gen','month cumm prog','month cumm gen','coal stock','cap under outage','outage_day_time','expected_resync','remarks','datetime']]
					df.to_csv(output_directory+"/"+str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)+".csv",index=False)
				except Exception:
					"fail: "+str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)




########################################################################################
#
# PARSE XLS FILES
#
########################################################################################

input_directory='./raw NPP data'
output_directory='./parsed NPP data/'

import warnings
warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.filterwarnings(
    "ignore",
    message="This pattern is interpreted as a regular expression, and has match groups",
    category=UserWarning,
)


res=[]
for year in range(2018,2019):
	for month in range(12,13):
		for day in range(1,monthrange(year, month)[1]+1):
			if len(glob.glob((input_directory+"/"+str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)+".xls")))>0:
				try:
					# Open .xls (must use xlrd==1.2.0 for old .xls support)
					book = xlrd.open_workbook(input_directory+"/"+str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)+".xls", formatting_info=True)
					sheet = book.sheet_by_index(0)
					# Start with an empty matrix
					data = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(2,sheet.nrows)]
					for (rlo, rhi, clo, chi) in sheet.merged_cells:
					    # leave only the top-left value, rest as is (blank)
					    for r in range(rlo+1, rhi):
					        for c in range(clo, chi):
					            data[r][c] = np.nan   # or None
					# Load into pandas
					df = pd.DataFrame(data).iloc[1:].reset_index(drop=True)
					df = df.replace("", np.nan)
					pattern = "|".join(re.escape(x) for x in exclusions)
					df=df[~df[0].str.contains(pattern, case=False, na=False)]
					df=df[~df[1].str.contains(pattern, case=False, na=False)]
					df=df[~df[2].str.contains(pattern, case=False, na=False)]
					df=df[~df.iloc[:, 1:].isna().all(axis=1)]
					s = df[2].astype("string")
					mask = False
					for w in exclusions:
					    mask = mask | s.str.contains(w, case=False, na=False, regex=False)
					df = df[~mask]
					s = df[3].astype("string")
					mask = False
					for w in exclusions:
					    mask = mask | s.str.contains(w, case=False, na=False, regex=False)
					df = df[~mask]
					s = df[4].astype("string")
					mask = False
					for w in exclusions:
					    mask = mask | s.str.contains(w, case=False, na=False, regex=False)
					df = df[~mask]
					df=df[~df[2].astype(str).str.contains(pattern, case=False, na=False, regex=False)]
					df=df[~df[3].str.contains(pattern, case=False, na=False)]
					df=df.dropna(axis=1, how="all")
					df = df.set_axis(range(df.shape[1]), axis=1)
					# Treat "Unit" as missing
					df[0] = df[0].replace("Unit", pd.NA)
					# Forward fill with last non-null value
					df[0] = df[0].ffill()
					df.columns=['name','unit','outage_status','capacity','day prog','day gen','month cumm prog','month cumm gen','coal stock','cap under outage','outage_day_time','expected_resync','remarks']
					df=df[df.name.notnull()]
					#df['unit']='Unit '+df['unit'].astype(int).astype(str)
					df["unit"] = df["unit"].where(df["unit"].isna(),"Unit " + df["unit"].dropna().astype(int).astype(str))
					df['datetime']=pd.to_datetime(str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year),format='%d-%m-%Y')
					df.to_csv(output_directory+"/"+str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)+".csv",index=False)
					res.append(df)
				except Exception:
					try:
						# Open .xls (must use xlrd==1.2.0 for old .xls support)
						book = xlrd.open_workbook(input_directory+"/"+str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)+".xls", formatting_info=True)
						sheet = book.sheet_by_index(0)
						# Start with an empty matrix
						data = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
						for (rlo, rhi, clo, chi) in sheet.merged_cells:
						    # leave only the top-left value, rest as is (blank)
						    for r in range(rlo+1, rhi):
						        for c in range(clo, chi):
						            data[r][c] = np.nan   # or None
						# Load into pandas
						df = pd.DataFrame(data).iloc[1:].reset_index(drop=True)
						df = df.replace("", np.nan)
						pattern = "|".join(re.escape(x) for x in exclusions)
						df=df[~df[0].str.contains(pattern, case=False, na=False)]
						df=df[~df[1].str.contains(pattern, case=False, na=False)]
						df=df[~df[2].str.contains(pattern, case=False, na=False)]
						s = df[2].astype("string")
						mask = False
						for w in exclusions:
						    mask = mask | s.str.contains(w, case=False, na=False, regex=False)
						df = df[~mask]
						s = df[3].astype("string")
						mask = False
						for w in exclusions:
						    mask = mask | s.str.contains(w, case=False, na=False, regex=False)
						df = df[~mask]
						s = df[4].astype("string")
						mask = False
						for w in exclusions:
						    mask = mask | s.str.contains(w, case=False, na=False, regex=False)
						df = df[~mask]
						df=df[~df[2].astype(str).str.contains(pattern, case=False, na=False, regex=False)]
						#df=df[~df[3].str.contains(pattern, case=False, na=False)]
						df=df.dropna(axis=1, how="all")
						df = df.set_axis(range(df.shape[1]), axis=1)
						# Treat "Unit" as missing
						df[0] = df[0].replace("Unit", pd.NA)
						# Forward fill with last non-null value
						df[0] = df[0].ffill()
						df.columns=['name','unit','outage_status','capacity','day prog','day gen','month cumm prog','month cumm gen','coal stock','cap under outage','outage_day_time','expected_resync','remarks']
						df=df[df.name.notnull()]
						#df['unit']='Unit '+df['unit'].astype(int).astype(str)
						df["unit"] = df["unit"].where(df["unit"].isna(),"Unit " + df["unit"].dropna().astype(int).astype(str))
						df['datetime']=pd.to_datetime(str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year),format='%d-%m-%Y')
						df.to_csv(output_directory+"/"+str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)+".csv",index=False)
						res.append(df)
					except Exception:
						str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)
			else:
				pass		


########################################################################################
#
# ASSEMBLE FILES AS SINGLE CSV
#
########################################################################################

res=[]
for year in range(2017,2026):
	for month in range(1,13):
		for day in range(1,monthrange(year, month)[1]+1):
			try:
				res.append(pd.read_csv(output_directory+"/"+str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)+".csv"))
			except Exception:
				pass

# CONCAT ALL DAILY FILES
dgr2_all_i=pd.concat(res)
def format_unit(x):
    # Ignore strings (already processed)
    if isinstance(x, str):
        return x
    # Ignore NaN
    if pd.isna(x):
        return x
    # Try integer conversion for whole numbers
    try:
        xi = int(x)
        if xi == x:
            return f"Unit {xi}"      # 1.0 → Unit 1
    except:
        pass
    # For non-integers like 2.5
    return f"Unit {x}"

dgr2_all_i["unit"] = dgr2_all_i["unit"].apply(format_unit)
dgr2_all_i['concat']=dgr2_all_i['name']+dgr2_all_i['unit']


del res
import gc
gc.collect()

#STRIP OUT NULL VALUES FROM COLUMN: 'name'
dgr2_all_i=dgr2_all_i[dgr2_all_i.name.notnull()]
#SET 'unit' TO STRING (np.na becomes NAN)
dgr2_all_i['unit'] = dgr2_all_i['unit'].astype("string")
#SET 'outage_status' TO STRING
dgr2_all_i['outage_status'] = dgr2_all_i['outage_status'].replace(' ', np.nan).astype("string")
#SET 'concat' TO STRING (np.na becomes NAN)
dgr2_all_i['concat'] = dgr2_all_i['concat'].astype("string")


# #TO DO - SORT ADDITIONAL FIELDS
# #'cap under outage' KORADI TPS  issue
# dgr2_all_i['cap under outage']
# #outage_day_time
# dgr2_all_i['outage_day_time']
# #expected_resync
# dgr2_all_i['expected_resync']
# #remarks
# dgr2_all_i['remarks']

# sample = dgr2_all_i.sample(1000000, random_state=0)  # or smaller

# for col in sample.select_dtypes(include=['object']).columns:
#     types = sample[col].map(type).value_counts()
#     if len(types) > 1:
#         print(f"\nColumn: {col}")
#         print(types)


dgr2_all_i[['name', 'unit', 'outage_status', 'capacity', 'day prog', 'day gen', 'datetime', 'concat']].to_parquet('./npp_daily_generation.parquet', compression="snappy", index=False)



dgr2_all_i=pd.read_parquet('./npp_daily_generation.parquet')







#MAPPINGS OF DAILY GENERATION REPORTS TO GEM HYDRO DATA
mappings2=pd.read_csv('./NPP_GIPT_crosswalk.csv')
mappings2['concat']=mappings2['DGR plant name']+mappings2['DGR unit']

# ANALYSE THE DATA TIME SERIES






#dgr2_all.index=pandas.to_datetime(dgr2_all['datetime'],format='%Y-%m-%d')
dgr2_all=pd.merge(dgr2_all_i[['name', 'unit', 'capacity', 'day gen','datetime', 'concat']],mappings2[mappings2.concat.notnull()],left_on='concat',right_on='concat')
dgr2_all.index=pd.to_datetime(dgr2_all['datetime'],format='%Y-%m-%d')


# SENSE CHECK AGAINST CEA AGGREGATED DATA
all_india=pd.read_csv("C:/Users/james/Documents/GEM/GIPT/India/robbie/CEA_DGR_data (2).csv")
all_india.index=pd.to_datetime(all_india['yyyymmdd'],format='%Y%m%d')


dgr2_all[(dgr2_all['Type']=='coal')]['day gen'].resample('d').sum().plot(c='r')
all_india[['CEA.DGR.COL','CEA.DGR.LIG']].resample('d').sum().sum(axis=1).plot(c='b')

dgr2_all[dgr2_all['Type']=='nuclear']['day gen'].resample('d').sum().plot(c='r')
all_india[['CEA.DGR.NUC']].resample('d').sum().sum(axis=1).plot(c='b')



mappings2=pandas.read_excel('C:/Users/james/Documents/GEM/GIPT/India/mappings_GEM_dgr2_v2.xlsx','mappings_GEM_dgr2').drop_duplicates(subset=['DGR plant name'], keep='first')

# ANALYSE THE DATA TIME SERIES
dgr2_all=pandas.merge(dgr2_all,mappings2,left_on='name',right_on='DGR plant name',how='left')
dgr2_all.index=pandas.to_datetime(dgr2_all['datetime'],format='%Y-%m-%d')

# SENSE CHECK AGAINST CEA AGGREGATED DATA
all_india=pandas.read_csv("C:/Users/james/Documents/GEM/GIPT/India/robbie/CEA_DGR_data (2).csv")
all_india.index=pandas.to_datetime(all_india['yyyymmdd'],format='%Y%m%d')


dgr2_all[(dgr2_all['DGR plant name'].notnull())]['day gen'].resample('d').sum().plot(c='r')
all_india[['CEA.DGR.HYD']].resample('d').sum().sum(axis=1).plot(c='b')



# ANALYSE THE DATA TIME SERIES
dgr2_all=pandas.merge(dgr2_all,mappings2,left_on='name',right_on='DGR plant name',how='left')
dgr2_all.index=pandas.to_datetime(dgr2_all['datetime'],format='%Y-%m-%d')

dgr2_all[dgr2_all['Type']=='oil/gas']['day gen'].resample('d').sum().plot(c='r')
all_india[['CEA.DGR.GAS', 'CEA.DGR.DIE']].resample('d').sum().sum(axis=1).plot(c='b')

