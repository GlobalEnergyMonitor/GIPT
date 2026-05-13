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

for year in range(2026,2027):
	for month in range(2,4):
		for day in range(1,monthrange(year, month)[1]+1):
			if len(glob.glob((output_directory+"/"+str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)+".xls")))==0:
				try:
					url="https://npp.gov.in/public-reports/cea/daily/dgr/"+str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)+"/dgr2-"+str(year)+"-"+str(month).zfill(2)+"-"+str(day).zfill(2)+".xls"
					filename = wget.download(url, out=output_directory+"/"+str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)+".xls")
				except Exception:
					str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)


import os
import time
from calendar import monthrange
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import glob

# DOWNLOAD DAILY XLS FILES (NPP) with headers + retries
output_directory = "./raw NPP data/"
os.makedirs(output_directory, exist_ok=True)

# --- Requests session with retries ---
session = requests.Session()

retry = Retry(
    total=6,
    connect=6,
    read=6,
    backoff_factor=1.0,                 # 1s, 2s, 4s, 8s...
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=("GET",),
    raise_on_status=False,
)
adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)
session.mount("http://", adapter)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "*/*",
    "Accept-Language": "en-GB,en;q=0.9",
    # Sometimes helps with bot checks:
    "Referer": "https://npp.gov.in/publishedReports",
    "Connection": "keep-alive",
}

def download_file(url: str, out_path: str, timeout=(10, 60)) -> tuple[bool, str]:
    """
    Returns (ok, msg). Streams content to disk; handles common transient failures.
    """
    try:
        with session.get(url, headers=headers, stream=True, timeout=timeout) as r:
            if r.status_code == 404:
                return False, "404 not found"
            if r.status_code >= 400:
                return False, f"HTTP {r.status_code}"
            # Some servers return HTML error pages with 200; guard a bit:
            ctype = (r.headers.get("Content-Type") or "").lower()
            if "text/html" in ctype:
                return False, "got HTML (blocked/redirect?)"
            tmp_path = out_path + ".part"
            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 64):
                    if chunk:
                        f.write(chunk)
            os.replace(tmp_path, out_path)
            return True, "ok"
    except requests.exceptions.RequestException as e:
        return False, f"request error: {e!r}"

# --- Main loop ---
for year in range(2026, 2027):
    for month in range(1, 3):
        for day in range(1, monthrange(year, month)[1] + 1):
            out_file = os.path.join(
                output_directory,
                f"{day:02d}-{month:02d}-{year}.xls"
            )
            if len(glob.glob(out_file)) == 0:
                url = (
                    "https://npp.gov.in/public-reports/cea/daily/dgr/"
                    f"{day:02d}-{month:02d}-{year}/"
                    f"dgr2-{year}-{month:02d}-{day:02d}.xls"
                )
                ok, msg = download_file(url, out_file)
                if not ok:
                    # Log failures so you can inspect patterns later
                    print(f"FAIL {day:02d}-{month:02d}-{year} | {msg} | {url}")
                    # If you're getting lots of resets, slow down a bit more:
                    time.sleep(2.0)
                else:
                    print(f"OK   {day:02d}-{month:02d}-{year} -> {out_file}")
                # Be polite to the server (helps avoid 429 / resets)
                time.sleep(0.4)




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

z=tabula.read_pdf("https://cea.nic.in/wp-content/uploads/2020/05/exe_summary-01-9.pdf",
					    pages="4",
					    multiple_tables=True,
					    lattice=True
					)[0]['Targets']


https://cea.nic.in/wp-content/uploads/2020/05/exe_summary-01-1.pdf

[2007 - 1]
[2008 - 2]
[2009 - 3]
[2010 - 4]
[2011 - 5]
[2012 - 6]
[2013 - 7]
[2014 - 8]

https://cea.nic.in/wp-content/uploads/2020/05/exe_summary-12-8.pdf

for y,year in zip(list(range(1,9)),range(2007,2015)):
	for month in range(1,13):
		tabula.read_pdf("https://cea.nic.in/wp-content/uploads/2020/05/exe_summary-"+str(month).zfill(2)+"-"+str(y)+".pdf",
					    pages="4",
					    multiple_tables=True,
					    lattice=True
					)[0]['Targets']


from urllib.request import urlretrieve


for y,year in zip(list(range(1,9)),range(2007,2015)):
	for month in range(1,13):
		urlretrieve("https://cea.nic.in/wp-content/uploads/2020/05/exe_summary-"+str(month).zfill(2)+"-"+str(y)+".pdf", "C:/Users/james/Downloads/"+str(year)+"-"+str(month).zfill(2)+".pdf")






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
for year in range(2026,2027):
	for month in range(2,4):
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
					try:
						df=df[~df[2].str.contains(pattern, case=False, na=False)]
					except Exception:
						pass
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
					#
					df=df[~((df[0].isnull())&(df[1].isnull()))]
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
						try:
							df=df[~df[2].str.contains(pattern, case=False, na=False)]
						except Exception:
							pass
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
for year in range(2017,2027):
	for month in range(1,13):
		for day in range(1,monthrange(year, month)[1]+1):
			try:
				res.append(pd.read_csv(output_directory+"/"+str(day).zfill(2)+"-"+str(month).zfill(2)+"-"+str(year)+".csv"))
			except Exception:
				pass

# CONCAT ALL DAILY FILES
dgr2_all=pd.concat(res)
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

dgr2_all["unit"] = dgr2_all["unit"].apply(format_unit)
dgr2_all['concat']=dgr2_all['name']+dgr2_all['unit']


del res
import gc
gc.collect()

#STRIP OUT NULL VALUES FROM COLUMN: 'name'
dgr2_all=dgr2_all[dgr2_all.name.notnull()]
#SET 'unit' TO STRING (np.na becomes NAN)
dgr2_all['unit'] = dgr2_all['unit'].astype("string")
#SET 'outage_status' TO STRING
dgr2_all['outage_status'] = dgr2_all['outage_status'].replace(' ', np.nan).astype("string")
#SET 'concat' TO STRING (np.na becomes NAN)
dgr2_all['concat'] = dgr2_all['concat'].astype("string")


# #TO DO - SORT ADDITIONAL FIELDS
# #'cap under outage' KORADI TPS  issue
# dgr2_all['cap under outage']
# #outage_day_time
# dgr2_all['outage_day_time']
# #expected_resync
# dgr2_all['expected_resync']
# #remarks
# dgr2_all['remarks']

# sample = dgr2_all.sample(1000000, random_state=0)  # or smaller

# for col in sample.select_dtypes(include=['object']).columns:
#     types = sample[col].map(type).value_counts()
#     if len(types) > 1:
#         print(f"\nColumn: {col}")
#         print(types)


dgr2_all[['name', 'unit', 'outage_status', 'capacity', 'day prog', 'day gen', 'datetime', 'concat']].to_parquet('./npp_daily_generation.parquet', compression="snappy", index=False)



#MAPPINGS OF DAILY GENERATION REPORTS TO GEM HYDRO DATA
crosswalk=pd.read_csv('./NPP_GIPT_crosswalk.csv')
crosswalk['concat']=crosswalk['DGR plant name']+crosswalk['DGR unit']
#CHECK FOR ANY MISSING PLANTS IN THE DGR DATA BUT NOT IN GEM MAPPINGS FILE
units_in_dgr2 = dgr2_all.drop_duplicates(subset=['concat'], keep='first')

res2=[]

my_list = list((set(units_in_dgr2.concat)-set(list(crosswalk['concat']))))

# Replace pd.NA with None
cleaned = [None if pd.isna(x) else x for x in my_list]

sorted_list = sorted(cleaned, key=lambda x: (x is None, x))

for i in sorted_list:
	res2.append([i,(len(dgr2_all[dgr2_all.concat==i])),dgr2_all[dgr2_all.concat==i]['day gen'].sum()])


pd.DataFrame(res2).to_csv('C:/Users/james/Documents/GEM/GIPT/India/missing_4.csv')




########################################################################################
#
# ANALYSE THE DATA TIME SERIES, MATCH WITH GIPT, AND SENSE CHECK AGAINST DAILY AGGREGATE GENERATION PER SOURCE
#
########################################################################################

import pandas as pd 
from pylab import *

#LOAD DGR DATA
dgr2_all=pd.read_parquet('./npp_daily_generation.parquet')

# SENSE CHECK AGAINST CEA AGGREGATED DATA
all_india=pd.read_csv("./CEA_DGR_data_11.12.25.csv")
all_india.index=pd.to_datetime(all_india['yyyymmdd'],format='%Y%m%d')

#MAPPINGS OF DAILY GENERATION REPORTS TO GIPT
crosswalk=pd.read_csv('./NPP_GIPT_crosswalk.csv')
crosswalk['concat']=crosswalk['DGR plant name']+crosswalk['DGR unit']

#MERGE USING NAME AND UNIT FOR COAL AND NUCLEAR (WITH UNITS) AND WITH NAME FOR HYDRO AND GAS/OIL (WITHOUT UNITS)
dgr2_all_with_units=pd.merge(dgr2_all[['name', 'unit', 'capacity', 'day gen','datetime', 'concat']],crosswalk[crosswalk.concat.notnull()],left_on='concat',right_on='concat')
dgr2_all_without_units=pd.merge(dgr2_all[['name', 'unit', 'capacity', 'day gen','datetime']],crosswalk[crosswalk.concat.isnull()].drop_duplicates(subset=['DGR plant name'], keep='first'),left_on='name',right_on='DGR plant name',how='left')
dgr2_all_with_units.index=pd.to_datetime(dgr2_all_with_units['datetime'],format='%Y-%m-%d')
dgr2_all_without_units.index=pd.to_datetime(dgr2_all_without_units['datetime'],format='%Y-%m-%d')

#PLOT TIMESERIES COAL AND LIGNITE
dgr2_all_with_units[(dgr2_all_with_units['Type']=='coal')]['day gen'].resample('d').sum().plot(c='r')
all_india[['CEA.DGR.COL','CEA.DGR.LIG']].resample('d').sum().sum(axis=1).plot(c='b')

#PLOT TIMESERIES OF NUCLEAR
dgr2_all_with_units[dgr2_all_with_units['Type']=='nuclear']['day gen'].resample('d').sum().plot(c='r')
all_india[['CEA.DGR.NUC']].resample('d').sum().sum(axis=1).plot(c='b')

#PLOT TIMESERIES OF HYDRO
dgr2_all_without_units[dgr2_all_without_units['Type']=='hydropower']['day gen'].resample('d').sum().plot(c='r')
all_india[['CEA.DGR.HYD']].resample('d').sum().sum(axis=1).plot(c='b')
	
#PLOT TIMESERIES OF GAS/OIL
dgr2_all_without_units[dgr2_all_without_units['Type']=='oil/gas']['day gen'].resample('d').sum().plot(c='r')
all_india[['CEA.DGR.GAS', 'CEA.DGR.DIE']].resample('d').sum().sum(axis=1).plot(c='b')


########################################################################################
#
# ANALYSE COAL AT UNIT LEVEL
#
########################################################################################


#in 2025, which states increase/decrease coal geenration?
z=dgr2_all_with_units[(dgr2_all_with_units['Type']=='coal')].groupby('State').resample('A')['day gen'].sum().reset_index()
z['diff']=z.groupby(["State"])["day gen"].diff()
z[z['datetime'].dt.year==2025].sort_values('diff')#,ascending=False)



#which are the top units in a given state for coal generation??
_2024=dgr2_all_with_units[(dgr2_all_with_units.index.year==2024)&(dgr2_all_with_units['State']=='Gujarat')&(dgr2_all_with_units['Type']=='coal')][['concat','day gen']].groupby(['concat']).resample('A')['day gen'].sum().reset_index()[['concat','day gen']].set_index('concat')
_2025=dgr2_all_with_units[(dgr2_all_with_units.index.year==2025)&(dgr2_all_with_units['State']=='Gujarat')&(dgr2_all_with_units['Type']=='coal')][['concat','day gen']].groupby(['concat']).resample('A')['day gen'].sum().reset_index()[['concat','day gen']].set_index('concat')


#in 2025, did all units backdown, or where there winners and losers?
#which plants are persistently 












#dgr2_all_with_units['concat']=dgr2_all_with_units['Plant / Project name']+dgr2_all_with_units['Unit / Phase name']

dgr2_all_with_units[(dgr2_all_with_units['State']=='Gujarat')&(dgr2_all_with_units['Type']=='coal')].resample('A')['day gen'].sum()




zz=dgr2_all_with_units[(dgr2_all_with_units['State']=='Rajasthan')&(dgr2_all_with_units['Type']=='coal')][['concat','day gen']].groupby(['concat']).resample('A')['day gen'].sum()



((zz.reset_index()[zz.reset_index().datetime.dt.year==2025].set_index('concat')['day gen']-zz.reset_index()[zz.reset_index().datetime.dt.year==2024].set_index('concat')['day gen']).sort_values())/zz.reset_index()[zz.reset_index().datetime.dt.year==2024].set_index('concat')['day gen']


zz.reset_index()[zz.reset_index().datetime.dt.year==2025].sort_values(by='day gen',ascending=False)['day gen'].sum()


zz.reset_index().sort_values(by='day gen')






s=pd.read_csv("C:/Users/james/Downloads/esk_edit.csv")

# Parse datetime column (AM/PM format)
s["datetime"] = pd.to_datetime(
    s["Date Time Hour Beginning"],
    format="%d/%m/%Y %H:%M")

# Set DatetimeIndex
s = (
    s.drop(columns="Date Time Hour Beginning")
      .set_index("datetime")
      .sort_index()
)

s[" Thermal Generation "] = (
    s[" Thermal Generation "]
      .astype(str)
      .str.replace(",", "", regex=False)
      .str.strip()
      .astype(float)
)



s24 = s[s.index.year == 2024]
s25 = s[' Thermal Generation '].dropna()[s[' Thermal Generation '].dropna().index.year == 2025]
# collapse to one value per calendar day-of-year (handles duplicates)
g24 = s24.groupby(s24.index.strftime('%m-%d')).sum()
g25 = s25.groupby(s25.index.strftime('%m-%d')).sum()
# keep only days present in BOTH years
common = g24.index.intersection(g25.index)
(g25.loc[common] - g24.loc[common][' Thermal Generation ']).sum()



s[' Thermal Generation '].dropna().resample('m').sum()

#1: Coal generation fell nationwide in 2025 in India: waterfall plot

all_india=pd.read_csv("./POSOCO_data.csv")
all_india.index=pd.to_datetime(all_india['yyyymmdd'],format='%Y%m%d')

tmp=all_india[['India: Total','India: Coal', 'India: Lignite','India: Nuclear', 'India: Gas', 'India: RES','India: SolarGen','India: WindGen','India: HydroGen']]['2024':]
tmp['India: OtherRE']=tmp['India: RES']-(tmp['India: SolarGen']+tmp['India: WindGen'])
d24 = tmp[tmp.index.year == 2024].assign(md=lambda x: x.index.strftime('%m-%d')).set_index('md')
d25 = tmp[tmp.index.year == 2025].assign(md=lambda x: x.index.strftime('%m-%d')).set_index('md')
common = d24.index.intersection(d25.index)
total_diff = (d25.loc[common] - d24.loc[common]).sum()
total_diff=total_diff.loc[['India: Total','India: Coal', 'India: Lignite',  'India: Nuclear', 'India: Gas', 'India: SolarGen', 'India: WindGen','India: HydroGen', 'India: OtherRE']]
total_diff.index=['Total','Coal', 'Lignite',  'Nuclear', 'Gas', 'Solar', 'Wind','Hydro', 'OtherRE']
(total_diff.loc[['Solar', 'Wind','Hydro', 'OtherRE','Coal', 'Lignite','Gas','Nuclear','Total']]/1000).to_csv('./nation_gen_waterfall_v1.csv')


#NITI AYOG GENERATION DATA
s=pd.read_excel("C:/Users/james/Downloads/Electricity_Power_Generation_1766139815122.xlsx")
s=s.iloc[0].T[1:].astype(float)
s.index=pd.to_datetime(s.index,format='%Y-%m')
(s.resample('A').sum()/1000).to_csv("C:/Users/james/Downloads/gen.csv")

#robbie capacity factor

s=pd.read_csv("C:/Users/james/Downloads/capacity_utilisation_MA_data.csv")
s.index=pd.to_datetime(s['YYYYMM'],format='%Y%m')


(s['Coal/Lignite'].resample('A').mean()).to_csv("C:/Users/james/Downloads/gen.csv")




# 2: CHANGE IN COAL GENRATION BY STATE
type='coal'
res=[]
for state in dgr2_all_with_units.State.unique():
	try:
		s=dgr2_all_with_units[(dgr2_all_with_units['State']==state)&(dgr2_all_with_units['Type']==type)].groupby('datetime')['day gen'].sum().loc['2024':]
		s.index=pd.to_datetime(tmp.index)
		s24 = s[s.index.year == 2024]
		s25 = s[s.index.year == 2025]
		# collapse to one value per calendar day-of-year (handles duplicates)
		g24 = s24.groupby(s24.index.strftime('%m-%d')).sum()
		g25 = s25.groupby(s25.index.strftime('%m-%d')).sum()
		# keep only days present in BOTH years
		common = g24.index.intersection(g25.index)
		# total difference across common days (2025 - 2024)
		res.append([state,(g25.loc[common] - g24.loc[common]).sum()])
	except Exception:
		state

pandas.DataFrame(res).sort_values(by=1)


# 3: CHANGE IN TOTAL GENERATION PER STATE (CHECK COAL FALL WASN'T JUST TOTAL GENERATION FALLING)
niti=pd.read_csv("./niti.csv")
niti[(niti['State']==state)].to_csv('./tmp.csv')
res=[]
for state in niti.State.unique():
	try:
		s=niti[(niti['State']==state)&(niti['Parameter']=='Total')].iloc[:,2:].T.astype(float)#groupby('datetime')['day gen'].sum().loc['2024':]
		s.index=pd.to_datetime(s.index)
		s24 = s[s.index.year == 2024]
		s25 = s[s.index.year == 2025]
		# collapse to one value per calendar day-of-year (handles duplicates)
		g24 = s24.groupby(s24.index.strftime('%m-%d')).sum()
		g25 = s25.groupby(s25.index.strftime('%m-%d')).sum()
		# keep only days present in BOTH years
		common = g24.index.intersection(g25.index)
		# total difference across common days (2025 - 2024)
		res.append([state,(g25.loc[common] - g24.loc[common]).sum().iloc[0]])
	except Exception:
		state

pandas.DataFrame(res).sort_values(by=1)


#STACKED BAR CHART NET CHANGE PLOT
import pandas as pd
df1 = pd.read_csv("./niti.csv")
df2= pd.read_csv("./niti_nov25.csv")

for df in (df1, df2):
    df['Parameter'] = df['Parameter'].str.strip().str.lower()
    df['State'] = df['State'].str.strip().str.lower()


df = df1.merge(
    df2,
    on=['Parameter', 'State'],
    how='left',
    suffixes=('_old', '_nov25')
)


df[df.Parameter=='coal - generation (in mu)']

# Identify monthly columns (YYYY-MM)
month_cols = [c for c in df.columns if "-" in c and c[:4].isdigit()]

# Convert ONLY month columns to numeric
df[month_cols] = df[month_cols].apply(pd.to_numeric, errors="coerce")

# Jan–Oct monthly columns for each year (only months common to both years)
cols_2024 = [c for c in df.columns if c.startswith("2024-") and int(c.split("-")[1]) <= 11]
cols_2025 = [c for c in df.columns if c.startswith("2025-") and int(c.split("-")[1]) <= 11]

# Row-wise sums for Jan–Oct
df["sum_2024_JanOct"] = df[cols_2024].sum(axis=1, numeric_only=True)
df["sum_2025_JanOct"] = df[cols_2025].sum(axis=1, numeric_only=True)

# Difference (2025 - 2024) for common months
df["diff_2025_vs_2024"] = df["sum_2025_JanOct"] - df["sum_2024_JanOct"]

df["Parameter"] = df["Parameter"].str.replace(" - Generation (in MU)", "", regex=False)
df.loc[df['Parameter']=='Total',"diff_2025_vs_2024"]=df.loc[df['Parameter']=='Total',"diff_2025_vs_2024"]#/-1

#df[['Parameter','State',"diff_2025_vs_2024"]].to_csv('./state_gen_waterfall_v1.csv')

df['Parameter'] = df['Parameter'].str.replace(' - generation (in mu)', '', regex=False)

zz=df[['Parameter','State',"diff_2025_vs_2024"]].pivot_table(columns='Parameter',values='diff_2025_vs_2024',index='State')
zz['net']=zz.sum(axis=1)
zz['hydro']=zz['hydro']+zz['small-hydro']
zz=zz[['bio power', 'coal', 'hydro', 'nuclear', 'oil & gas','solar', 'wind', 'net']]
zz=zz.reset_index()
states = [
    "haryana",
    "maharashtra",
    "west bengal",
    "bihar",
    "punjab",
    "madhya pradesh",
    "jharkhand",
    "gujarat",
    "uttar pradesh",
    "telangana",
    "tamil nadu",
    "odisha",
    "chhattisgarh",
    "andhra pradesh",
    "karnataka",
    "rajasthan",
]

zzz=zz[~zz.State.isin(states)].sum(axis=0)
zzz.State='Others'
tmp=pandas.concat([zz[zz.State.isin(states)],pandas.DataFrame(zzz).T],axis=0).sort_values(by='net')
tmp['State'] = tmp['State'].str.title()
tmp.columns=['State', 'Bioenergy', 'Coal', 'Hydropower', 'Nuclear', 'Oil/gas', 'Solar','Wind', 'net']
tmp.to_csv('./state_gen_net_v1.csv')




z=df[['Parameter','State',"diff_2025_vs_2024","sum_2024_JanOct"]]

zz=z[z.Parameter.isin(['Total'])]
zz['%']=z[z.Parameter.isin(['Total'])]['diff_2025_vs_2024']/z[z.Parameter.isin(['Total'])]['sum_2024_JanOct']
zz.sort_values(by='diff_2025_vs_2024')

zz=z[z.Parameter.isin(['Total'])].pivot_table(columns='Parameter',values='diff_2025_vs_2024',index='State')

zz=z[z.Parameter.isin(['Total','Coal','Solar','Wind'])].pivot_table(columns='Parameter',values='diff_2025_vs_2024',index='State')
zz['solar+wind']=zz['Solar']+zz['Wind']
zz.sort_values(by='solar+wind')[::-1]

# total generation per state:
df = pd.read_csv("./niti.csv")
df=df[df.Parameter=='Total']
cols_2024 = [c for c in df.columns if c.startswith("2025-") and int(c.split("-")[1]) <= 10]
pd.DataFrame([df[df.Parameter=='Total'].State,df[cols_2024].astype(float).sum(axis=1, numeric_only=True)]).T.sort_values(by='Unnamed 0').set_index('State')[::-1]
# change in total generation per state and total coal generation per state



#################################
#CHINA STACKED BAR CHART NET CHANGE BY PROVINCE

thermal=pd.read_excel("C:/Users/james/Documents/GEM/GIPT/BRICS India 2026/china_gen_national.xlsx",'Thermal').set_index('100 million KWh')*100
hydro=pd.read_excel("C:/Users/james/Documents/GEM/GIPT/BRICS India 2026/china_gen_national.xlsx",'Hydro').set_index('100 million KWh')*100
nuclear=pd.read_excel("C:/Users/james/Documents/GEM/GIPT/BRICS India 2026/china_gen_national.xlsx",'Nuclear').set_index('100 million KWh')*100
wind=pd.read_excel("C:/Users/james/Documents/GEM/GIPT/BRICS India 2026/china_gen_national.xlsx",'Wind').set_index('100 million KWh')*100
solar=pd.read_excel("C:/Users/james/Documents/GEM/GIPT/BRICS India 2026/china_gen_national.xlsx",'Solar').set_index('10000KWh')*1e-05

thermal.columns = pd.to_datetime(thermal.columns)
hydro.columns = pd.to_datetime(hydro.columns)
wind.columns = pd.to_datetime(wind.columns)
nuclear.columns = pd.to_datetime(nuclear.columns)
solar.columns = pd.to_datetime(solar.columns)


zz=pandas.concat([thermal['2025/11/01'],hydro['2025/11/01'],nuclear['2025/11/01'],wind['2025/11/01'],solar['2025/11/01']],axis=1)
zz.columns=['Thermal','Hydro','Nuclear','Wind','Solar']
aa=pandas.concat([thermal['2024/11/01'],hydro['2024/11/01'],nuclear['2024/11/01'],wind['2024/11/01'],solar['2024/11/01']],axis=1)
aa.columns=['Thermal','Hydro','Nuclear','Wind','Solar']
qq=zz-aa
qq['net']=qq.sum(axis=1)
qq.sort_values('net').to_csv("C:/Users/james/Documents/GEM/GIPT/BRICS India 2026/china_gen_national.csv")




#################################
#USA STACKED BAR CHART NET CHANGE BY PROVINCE


gas=pd.read_excel("C:/Users/james/Downloads/table_1_07_b.xlsx",skiprows=5).iloc[:-1,:3]#1000 MWh
coal=pd.read_excel("C:/Users/james/Downloads/table_1_04_b.xlsx",skiprows=5).iloc[:-1,:3]#1000 MWh
total=pd.read_excel("C:/Users/james/Downloads/table_1_03_b.xlsx",skiprows=5).iloc[:-1,:3]#1000 MWh
solar=pd.read_excel("C:/Users/james/Downloads/table_1_17_b.xlsx",skiprows=5).iloc[:-1,:3]#1000 MWh
wind=pd.read_excel("C:/Users/james/Downloads/table_1_14_b.xlsx",skiprows=5).iloc[:-1,:3]#1000 MWh


Other1=total['October 2025 YTD']-(gas['October 2025 YTD']+coal['October 2025 YTD']+solar['October 2025 YTD']+wind['October 2025 YTD'])
Other2=total['October 2024 YTD']-(gas['October 2024 YTD']+coal['October 2024 YTD']+solar['October 2024 YTD']+wind['October 2024 YTD'])
other=pandas.concat([Other1,Other2],axis=1)
other.columns=['October 2025 YTD','October 2024 YTD']
other.index=total['Census Division\nand State']

gas['2025 change']=gas['October 2025 YTD']-gas['October 2024 YTD']
coal['2025 change']=coal['October 2025 YTD']-coal['October 2024 YTD']
total['2025 change']=total['October 2025 YTD']-total['October 2024 YTD']
solar['2025 change']=solar['October 2025 YTD']-solar['October 2024 YTD']
wind['2025 change']=wind['October 2025 YTD']-wind['October 2024 YTD']
other['2025 change']=other['October 2025 YTD']-other['October 2024 YTD']

gas=gas.set_index('Census Division\nand State')
coal=coal.set_index('Census Division\nand State')
total=total.set_index('Census Division\nand State')
solar=solar.set_index('Census Division\nand State')
wind=wind.set_index('Census Division\nand State')

zz=pandas.concat([gas['2025 change'],coal['2025 change'],solar['2025 change'],wind['2025 change'],other['2025 change'],total['2025 change']],axis=1)
zz.columns=['Gas','Coal','Solar','Wind','Other','Total']


states = [
    "Alabama",
    "Alaska",
    "Arizona",
    "Arkansas",
    "California",
    "Colorado",
    "Connecticut",
    "Delaware",
    "Florida",
    "Georgia",
    "Hawaii",
    "Idaho",
    "Illinois",
    "Indiana",
    "Iowa",
    "Kansas",
    "Kentucky",
    "Louisiana",
    "Maine",
    "Maryland",
    "Massachusetts",
    "Michigan",
    "Minnesota",
    "Mississippi",
    "Missouri",
    "Montana",
    "Nebraska",
    "Nevada",
    "New Hampshire",
    "New Jersey",
    "New Mexico",
    "New York",
    "North Carolina",
    "North Dakota",
    "Ohio",
    "Oklahoma",
    "Oregon",
    "Pennsylvania",
    "Rhode Island",
    "South Carolina",
    "South Dakota",
    "Tennessee",
    "Texas",
    "Utah",
    "Vermont",
    "Virginia",
    "Washington",
    "West Virginia",
    "Wisconsin",
    "Wyoming",
]



zz.loc[states].sort_values('Coal').to_csv("C:/Users/james/Documents/GEM/GIPT/BRICS India 2026/USA_gen_national.csv")











q=pd.read_csv("C:/Users/james/Downloads/ESK17800.csv")
q.index=pandas.to_datetime(q.index)


q['Pumped Water SCO Pumping'].loc['2025'].sum()


q['Wind'].resample('A').sum()
q['International Imports'].resample('A').sum()


# 1a: monthly coal generation per state index at december 2024 value
(['Delhi', 'Haryana', 'Punjab', 'Rajasthan', 'Uttar Pradesh',
       'Chhatisgarh', 'Gujarat', 'Madhya Pradesh', 'Maharashtra',
       'Andhra Pradesh', 'Karnataka', 'Tamil Nadu', 'Telangana', 'Bihar',
       'Jharkhand', 'Odisha', 'West Bengal', 'Assam']

'Rajasthan', 'Gujarat', 'Tamil Nadu',
 'Uttar Pradesh',      'Chhatisgarh', 'Gujarat', 'Madhya Pradesh', 'Maharashtra',
       'Andhra Pradesh', 'Karnataka', 'Tamil Nadu', 'Telangana', 'Bihar',
       'Jharkhand', 'Odisha', 'West Bengal', 'Assam']



type='coal'
index_to='2024/12/31'

tmp=[]

for state in ['Rajasthan', 'Gujarat', 'Tamil Nadu']:#dgr2_all_with_units.State.unique():
	try:
		z=dgr2_all_with_units[(dgr2_all_with_units['State']==state)&(dgr2_all_with_units['Type']==type)].groupby('datetime')['day gen'].sum()
		z.index=pd.to_datetime(z.index,format='%Y-%m-%d')
		z=z.resample('d').sum()/z.resample('d').sum().loc[index_to]
		z=z.rename(state)
		tmp.append(z.rolling(window='30D').mean())
	except Exception:
		state



for i in tmp:
	i.plot(alpha=.5)



#2 CAPACITY FACTOR PER STATE

state='Rajasthan'
type='coal'
dgr2_all_with_units['full gen']=(dgr2_all_with_units['capacity']/1000)*24

z=dgr2_all_with_units[(dgr2_all_with_units['State']==state)&(dgr2_all_with_units['Type']==type)].groupby('datetime')[['day gen','full gen']].sum()
z['cf']=z['day gen']/z['full gen']
z.loc[z['cf']>1,'cf']=1.0
z.index=pd.to_datetime(z.index,format='%Y-%m-%d')
z['cf'].resample('d').mean().plot(c='r')


states = [
    "Chhatisgarh",
    "Uttar Pradesh",
    "Madhya Pradesh",
    "Maharashtra",
    "West Bengal",
    "Gujarat",
    "Tamil Nadu",
    "Andhra Pradesh",
    "Odisha",
    "Rajasthan",
    "Bihar",
    "Telangana",
    "Karnataka",
    "Jharkhand",
    "Punjab",
]


fig, axes = plt.subplots(4, 4, figsize=(10, 6), sharex=True)
axes = axes.flatten()

for ax, state in zip(axes, states):
	z=dgr2_all_with_units[(dgr2_all_with_units['State']==state)&(dgr2_all_with_units['Type']==type)].groupby('datetime')[['day gen','full gen']].sum()
	z['cf']=z['day gen']/z['full gen']
	z.loc[z['cf']>1,'cf']=1.0
	z.index=pd.to_datetime(z.index,format='%Y-%m-%d')
	ax.plot(z.resample('3m').mean().index, z.resample('3m').mean()["cf"].values)
	ax.set_title(state)
	ax.grid(True, which="both", linewidth=0.5, alpha=0.3)

for ax in axes[len(states):]:
    ax.axis("off")

plt.tight_layout()
plt.show()






dgr2_all_with_units[(dgr2_all_with_units['DGR plant name'].str.contains('Mundra Thermal Power Project (Adani)', case=False, na=False, regex=False))]['day gen'].resample('m').sum().plot(c='r')


zz=dgr2_all_with_units[(dgr2_all_with_units['Plant / Project name'].str.contains('Adani', case=False, na=False, regex=False))]

zz[(zz['Plant / Project name'].str.contains('Mundra Thermal Power Project (Adani)', case=False, na=False, regex=False))]['day gen'].resample('m').sum().plot(c='r')



##COAL GEENRATION BY STATE
state='Karnataka'
type='coal'

z=dgr2_all_with_units[(dgr2_all_with_units['State']==state)&(dgr2_all_with_units['Type']==type)].groupby('datetime')['day gen'].sum()

z.index=pd.to_datetime(z.index,format='%Y-%m-%d')
z.resample('w').sum().plot(c='r')







dgr2_all_with_units[(dgr2_all_with_units['Plant / Project name'].str.contains('kota', case=False, na=False, regex=False))][['day gen','unit']].reset_index().pivot_table(
    columns='unit',
    values='day gen',
    index='datetime'
).resample('Q').sum().plot()



['Chhabra Thermal Power Station', 'Giral power station',
       'Kalisindh Thermal Power Station', 'Kota power station',
       'Suratgarh Super Thermal Power Station',
       'JSW Barmer Jalipa Kapurdi power station',
       'Kawai Thermal Power Project', 'Barsingsar Thermal Power Project',
       'Ajmer power station']


z=dgr2_all_with_units[(dgr2_all_with_units['Plant / Project name'].str.contains('kota', case=False, na=False, regex=False))]['day gen'].resample('m').sum()/((1240/1000)*24*dgr2_all_with_units[(dgr2_all_with_units['Plant / Project name'].str.contains('kota', case=False, na=False, regex=False))]['day gen'].resample('m').sum().index.daysinmonth)




dgr2_all_with_units['full gen']=(dgr2_all_with_units['capacity']/1000)*24



# Separate numeric and string columns
num_cols = ['capacity', 'day gen','full gen']
str_cols = ['name', 'unit', 'datetime', 'concat', 'Region',
       'State', 'Sector', 'Type', 'Plant / Project name', 'Unit / Phase name',
       'GEM unit/phase ID', 'Status', 'units combined', 'DGR plant name',
       'DGR unit', 'Notes']

# Group by unit (concat), resample monthly, aggregate
monthly_grouped = (
    dgr2_all_with_units
    .groupby('concat')  # group by unit
    .resample('M')      # resample by month
    .agg({**{col: 'sum' for col in num_cols}, **{col: 'first' for col in str_cols}})
)


monthly_grouped['cf']=monthly_grouped['day gen']/monthly_grouped['full gen']
monthly_grouped.loc[monthly_grouped['cf']>1,'cf']=1.0


qq = monthly_grouped[['cf']].reset_index().pivot_table(
    columns='concat',
    values='cf',
    index='datetime'
).stack(dropna=True).reset_index()
qq.columns = ["date", "unit", "value"]


fig, ax = plt.subplots(figsize=(12, 4))

# Group values by month
groups = [g["value"].values for _, g in qq.groupby("date")]

# Positions along x-axis
positions = range(len(groups))

ax.boxplot(
    groups,
    positions=positions,
    widths=0.6,
    showfliers=False  # optional: hides extreme outliers
)

# X-axis labels
dates = qq["date"].drop_duplicates().sort_values()
labels = [d.strftime("%Y-%m") for d in dates]

ax.set_xticks(positions[::6])                 # label every 6 months
ax.set_xticklabels(labels[::6], rotation=45)

ax.set_xlabel("Month")
ax.set_ylabel("Equivalent value")
ax.set_title("Monthly distribution across generating units")

plt.tight_layout()
plt.show()



import pandas as pd
import matplotlib.pyplot as plt

# df: index = datetime (monthly), columns = units

mean_ts = qq.mean(axis=1, skipna=True)

mean_ts.plot(figsize=(12, 4))
plt.xlabel("Month")
plt.ylabel("Mean equivalent value")
plt.title("Monthly mean across units")
plt.tight_layout()
plt.show()



