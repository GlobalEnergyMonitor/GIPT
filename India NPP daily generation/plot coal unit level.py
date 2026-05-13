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
all_india=pd.read_csv("./CEA_DGR_data_16.03.26.csv")
all_india.index=pd.to_datetime(all_india['yyyymmdd'],format='%Y%m%d')

#MAPPINGS OF DAILY GENERATION REPORTS TO GIPT
crosswalk=pd.read_csv('./NPP_GIPT_crosswalk.csv')
crosswalk['concat']=crosswalk['DGR plant name']+crosswalk['DGR unit']
#crosswalk['concat']=crosswalk['Plant / Project name']+crosswalk['Unit / Phase name']

#MERGE USING NAME AND UNIT FOR COAL AND NUCLEAR (WITH UNITS) AND WITH NAME FOR HYDRO AND GAS/OIL (WITHOUT UNITS)
dgr2_all_with_units=pd.merge(dgr2_all[['name', 'unit', 'capacity', 'day gen','datetime', 'concat']],crosswalk[crosswalk.concat.notnull()],left_on='concat',right_on='concat')
dgr2_all_without_units=pd.merge(dgr2_all[['name', 'unit', 'capacity', 'day gen','datetime']],crosswalk[crosswalk.concat.isnull()].drop_duplicates(subset=['DGR plant name'], keep='first'),left_on='name',right_on='DGR plant name',how='left')
dgr2_all_with_units.index=pd.to_datetime(dgr2_all_with_units['datetime'],format='%Y-%m-%d')
dgr2_all_without_units.index=pd.to_datetime(dgr2_all_without_units['datetime'],format='%Y-%m-%d')

dgr2_all_with_units=dgr2_all_with_units.drop('datetime',axis=1)
dgr2_all_with_units['concat2']=dgr2_all_with_units['Plant / Project name']+dgr2_all_with_units['Unit / Phase name']

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


dgr2_all_with_units['full gen']=(dgr2_all_with_units['capacity']/1000)*24



import pandas as pd
import matplotlib.pyplot as plt
def plot_series_by_day_of_year(s,drop_leap_day=True,title=None,figsize=(8,6),agg="mean"):
    s=s.copy()
    if not isinstance(s.index,pd.DatetimeIndex):
        raise ValueError("Series must have DatetimeIndex")
    s=s.sort_index()
    df=s.to_frame(name="value")
    df["year"]=df.index.year
    if drop_leap_day:
        df=df[~((df.index.month==2)&(df.index.day==29))].copy()
    df["doy"]=df.index.dayofyear
    if drop_leap_day:
        leap_year=df.index.is_leap_year
        after_feb28=df.index.month>2
        df.loc[leap_year&after_feb28,"doy"]=df.loc[leap_year&after_feb28,"doy"]-1
    if agg=="mean":
        df=df.groupby(["year","doy"],as_index=False)["value"].mean()
    elif agg=="sum":
        df=df.groupby(["year","doy"],as_index=False)["value"].sum()
    else:
        df=df.groupby(["year","doy"],as_index=False)["value"].agg(agg)
    wide=df.pivot(index="doy",columns="year",values="value").sort_index()
    ax=wide.plot(figsize=figsize,linewidth=1,alpha=0.9)
    ax.set_xlabel("Day of year (1–365)")
    ax.set_ylabel(s.name if s.name else "value")
    ax.set_title(title or f"{s.name if s.name else 'Series'} by day-of-year (each line = year)")
    ax.grid(True,alpha=0.2)
    plt.tight_layout()
    plt.show()
    return wide

plot_series_by_day_of_year(dgr2_all_with_units[(dgr2_all_with_units['Type']=='coal')]['day gen'].resample('d').sum()['2024':])


def aggregate_all(df,freq,how="sum",id_col="concat2",fill_value=0):
    import pandas as pd
    d=df.copy()
    if not isinstance(d.index,pd.DatetimeIndex): raise TypeError("df.index must be a DatetimeIndex")
    d.index=pd.to_datetime(d.index).normalize()
    d[id_col]=d[id_col].astype(str).str.strip()
    value_cols=[c for c in d.columns if c!=id_col]
    d[value_cols]=d[value_cols].apply(pd.to_numeric,errors="coerce")
    # collapse to daily per concat first (removes duplicates safely)
    daily=d.groupby([id_col,d.index])[value_cols].sum()
    daily.index=daily.index.set_names([id_col,"date"])
    # enforce complete daily grid PER concat (this is what prevents “gaps” later)
    full_days=pd.date_range(d.index.min(),d.index.max(),freq="D")
    full_index=pd.MultiIndex.from_product([daily.index.get_level_values(0).unique(),full_days],names=[id_col,"date"])
    daily=daily.reindex(full_index)
    if fill_value is not None: daily=daily.fillna(fill_value)
    # resample the daily grid to ANY freq (bins are now complete and aligned)
    agg=daily.groupby(level=0).resample(freq,level=1).agg(how)
    agg.index=agg.index.set_names([id_col,"datetime"])
    out=agg.reset_index()
    return out

def plot_heatmap(agg_df,value_col,id_col="concat2",date_col="datetime",row_order=None,cmap="magma",vmin=None,vmax=None,figscale_y=0.1,max_xticks=12):
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    d=agg_df.copy()
    d[date_col]=pd.to_datetime(d[date_col],errors="coerce")
    d=d.loc[d[date_col].notna()].copy()
    mat=d.pivot(index=id_col,columns=date_col,values=value_col).sort_index(axis=1)
    if row_order is not None: mat=mat.reindex(row_order)
    mat = mat.rolling(window=5, axis=1, center=True).mean()
    Z=mat.to_numpy()
    n_rows,n_cols=Z.shape
    fig_h=7#max(6,n_rows*figscale_y)
    fig_w=12#max(12,n_cols*0.25)
    fig,ax=plt.subplots(figsize=(fig_w,fig_h))
    im=ax.imshow(Z,aspect="auto",origin="upper",interpolation="nearest",cmap=cmap,vmin=vmin,vmax=vmax)
    ax.set_yticks(np.arange(n_rows))
    ax.set_yticklabels(mat.index,fontsize=8)
    labels=[c.strftime("%Y-%m-%d") for c in mat.columns]
    step=max(1,int(np.ceil(len(labels)/max_xticks)))
    ax.set_xticks(np.arange(0,len(labels),step))
    ax.set_xticklabels(labels[::step],rotation=0)
    plt.colorbar(im,ax=ax,pad=0.02,shrink=0.6,label=value_col)
    plt.tight_layout()
    plt.show()


df=dgr2_all_with_units[(dgr2_all_with_units['State']=='Gujarat')&(dgr2_all_with_units['Type']=='coal')]#.loc['2023':'2025']

freq="3D"
grouped=aggregate_all(df,freq=freq,how="sum",fill_value=0)
grouped['cf']=grouped['day gen']/grouped['full gen']


row_order=grouped.groupby("concat2")["day gen"].sum().sort_values(ascending=False).index
plot_heatmap(grouped,value_col="cf",row_order=row_order,cmap="magma")#,vmin=0,vmax=1)

z=df.resample('d')['day gen'].sum()/df.resample('d')['full gen'].sum()

zz=z.rolling(
    window=25,        # number of time bins
    center=True,     # preserve phase
    min_periods=1    # don’t drop edges
).mean()


# 1) aggregate + compute CF (your step)
freq="20D"
grouped = aggregate_all(df, freq=freq, how="sum", fill_value=0)
grouped["datetime"] = pd.to_datetime(grouped["datetime"])
grouped["cf"] = grouped["day gen"] / grouped["full gen"]
grouped["cf"] = grouped["cf"].clip(0, 1)  # optional but usually sensible

# 2) pivot to matrix: rows=concat, cols=time
mat = grouped.pivot(index="concat2", columns="datetime", values="cf").sort_index(axis=1)

# 3) normalize (pick ONE)
mat_demean = mat.sub(mat.mean(axis=1), axis=0)          # recommended first
mat_rel   = mat.div(mat.mean(axis=1), axis=0)         # relative to mean (optional)
mat_z     = mat_demean.div(mat.std(axis=1), axis=0)   # for clustering (optional)

# 4) smooth in time (choose window in bins; for 20D bins, 3 ≈ 60 days)
mat_smooth = mat_z.rolling(window=3, axis=1, center=True, min_periods=1).mean()

# 5) (optional) back to long form to merge/plot elsewhere
grouped_norm_smooth = (
    mat_smooth.stack()
    .rename("cf_norm_smooth")
    .reset_index()
)


row_order=grouped_norm_smooth.groupby("concat2")["cf_norm_smooth"].sum().sort_values(ascending=False).index

plot_heatmap(grouped_norm_smooth,value_col="cf_norm_smooth",row_order=row_order,cmap="magma",vmin=0,vmax=.25)




