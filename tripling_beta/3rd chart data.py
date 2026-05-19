
import json
import pandas
import numpy as np

z=pandas.read_json("https://api.iea.org/renewables/market?region=World")
HISTORICAL_YEARS = range(2010, 2026)
#tmp=pandas.DataFrame(z[(z['flow']=='Net additions')&(z['case']=='ACC')&z['year'].isin(range(2025,2031))]).groupby('product')['value'].sum()
#IEA utility-scale additions, DC
solar_ac=pandas.DataFrame(z[(z['flow']=='Net additions')&(z['case']=='ACC')&z['year'].isin(HISTORICAL_YEARS)&(z['product']=='PV utility-scale systems')]).value*.85
solar_ac.index=HISTORICAL_YEARS
onwind=pandas.DataFrame(z[(z['flow']=='Net additions')&(z['case']=='ACC')&z['year'].isin(HISTORICAL_YEARS)&(z['product']=='Onshore wind')]).value
onwind.index=HISTORICAL_YEARS
offwind=pandas.DataFrame(z[(z['flow']=='Net additions')&(z['case']=='ACC')&z['year'].isin(HISTORICAL_YEARS)&(z['product']=='Offshore wind')]).value
offwind.index=HISTORICAL_YEARS
hydro=pandas.DataFrame(z[(z['flow']=='Net additions')&(z['case']=='ACC')&z['year'].isin(HISTORICAL_YEARS)&(z['product']=='Hydro')]).value
hydro.index=HISTORICAL_YEARS
tmp=pandas.concat([solar_ac,onwind,offwind,hydro],axis=1)
tmp.columns=['Utility-scale solar','Onshore wind','Offshore wind','Hydro']
tmp.to_csv('./iea.csv')


pandas.concat([pandas.DataFrame(z[(z['flow']=='Net additions')&(z['case']=='ACC')&z['year'].isin(range(2010,2026))&(z['product']=='Solar PV')]).reset_index().value*.85,
pandas.DataFrame(z[(z['flow']=='Net additions')&(z['case']=='ACC')&z['year'].isin(range(2010,2026))&(z['product']=='PV utility-scale systems')]).reset_index().value*.85,
pandas.DataFrame(z[(z['flow']=='Net additions')&(z['case']=='ACC')&z['year'].isin(range(2010,2026))&(z['product']=='PV distributed systems')]).reset_index().value*.85,
pandas.DataFrame(z[(z['flow']=='Net additions')&(z['case']=='ACC')&z['year'].isin(range(2010,2026))&(z['product']=='Onshore wind')]).reset_index().value,
pandas.DataFrame(z[(z['flow']=='Net additions')&(z['case']=='ACC')&z['year'].isin(range(2010,2026))&(z['product']=='Offshore wind')]).reset_index().value],axis=1).to_csv('./iea_hist.csv')

pandas.concat([pandas.DataFrame(z[(z['flow']=='Capacity')&(z['case']=='ACC')&z['year'].isin(range(2010,2026))&(z['product']=='Solar PV')]).reset_index().value*.85,
pandas.DataFrame(z[(z['flow']=='Capacity')&(z['case']=='ACC')&z['year'].isin(range(2010,2026))&(z['product']=='PV utility-scale systems')]).reset_index().value*.85,
pandas.DataFrame(z[(z['flow']=='Capacity')&(z['case']=='ACC')&z['year'].isin(range(2010,2026))&(z['product']=='PV distributed systems')]).reset_index().value*.85,
pandas.DataFrame(z[(z['flow']=='Capacity')&(z['case']=='ACC')&z['year'].isin(range(2010,2026))&(z['product']=='Onshore wind')]).reset_index().value,
pandas.DataFrame(z[(z['flow']=='Capacity')&(z['case']=='ACC')&z['year'].isin(range(2010,2026))&(z['product']=='Offshore wind')]).reset_index().value],axis=1).to_csv('./iea_hist_cap.csv')

# Tripling pathway additions used in the final chart.
# Pull exact cells from tripling.xlsx, sheet "additions":
# C48:C52 = utility-scale solar, F48:F52 = onshore wind, G48:G52 = offshore wind, H48:H52 = hydropower.
tripling_additions=pandas.read_excel('./tripling.xlsx',sheet_name='additions',header=None)
tripling_additions=pandas.DataFrame({
    'Year': range(2026,2031),
    'Utility-scale solar': tripling_additions.iloc[47:52,2].to_numpy(),
    'Onshore wind': tripling_additions.iloc[47:52,5].to_numpy(),
    'Offshore wind': tripling_additions.iloc[47:52,6].to_numpy(),
    'Hydro': tripling_additions.iloc[47:52,7].to_numpy()
})
tripling_additions.to_csv('./tripling_additions.csv',index=False)

#GIPT data
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

status=['construction','pre-construction','announced']
type=['utility-scale solar']
solar=pandas.concat([gipt[(gipt['Start year'].isin([2026,2027,2028,2029,2030]))&(gipt.Status.isin(status))&(gipt.Type.isin(type))].groupby('Status')['Capacity (MW)'].sum()/1000,gipt[(gipt['Start year'].isnull())&(gipt.Status.isin(status))&(gipt.Type.isin(type))].groupby('Status')['Capacity (MW)'].sum()/1000],axis=1)
solar.columns=['pre-2030','unknown']
solar.index=['Announced','Construction','Pre-construction']
solar.loc['Total']=solar.sum(axis=0)
solar=solar.reset_index()
solar.index=['Utility-scale solar']*len(solar)

onwind=pandas.concat([gipt[(gipt['Start year'].isin([2026,2027,2028,2029,2030]))&(gipt.Status.isin(status))&(gipt.Technology.isin(['Onshore','Unknown']))].groupby('Status')['Capacity (MW)'].sum()/1000,gipt[(gipt['Start year'].isnull())&(gipt.Status.isin(status))&(gipt.Technology.isin(['Onshore','Unknown']))].groupby('Status')['Capacity (MW)'].sum()/1000],axis=1)
onwind.columns=['pre-2030','unknown']
onwind.index=['Announced','Construction','Pre-construction']
onwind.loc['Total']=onwind.sum(axis=0)
onwind=onwind.reset_index()
onwind.index=['Onshore wind']*len(onwind)

offwind=pandas.concat([gipt[(gipt['Start year'].isin([2026,2027,2028,2029,2030]))&(gipt.Status.isin(status))&(gipt.Technology.str.contains('Offshore'))].groupby('Status')['Capacity (MW)'].sum()/1000,gipt[(gipt['Start year'].isnull())&(gipt.Status.isin(status))&(gipt.Technology.str.contains('Offshore'))].groupby('Status')['Capacity (MW)'].sum()/1000],axis=1)
offwind.columns=['pre-2030','unknown']
offwind.index=['Announced','Construction','Pre-construction']
offwind.loc['Total']=offwind.sum(axis=0)
offwind=offwind.reset_index()
offwind.index=['Offshore wind']*len(offwind)

hydro_mask = (gipt.Type == 'hydropower') & ~gipt.Technology.str.contains('pumped', case=False, na=False)
hydro=pandas.concat([gipt[(gipt['Start year'].isin([2026,2027,2028,2029,2030]))&(gipt.Status.isin(status))&hydro_mask].groupby('Status')['Capacity (MW)'].sum()/1000,gipt[(gipt['Start year'].isnull())&(gipt.Status.isin(status))&hydro_mask].groupby('Status')['Capacity (MW)'].sum()/1000],axis=1)
hydro.columns=['pre-2030','unknown']
hydro=hydro.reindex(['announced','construction','pre-construction']).fillna(0)
hydro.index=['Announced','Construction','Pre-construction']
hydro.loc['Total']=hydro.sum(axis=0)
hydro=hydro.reset_index()
hydro.index=['Hydro']*len(hydro)

tmp=pandas.concat([solar,onwind,offwind,hydro],axis=0)
tmp.to_csv('./indev_total.csv')



status=['construction','pre-construction','announced']
type=['utility-scale solar']
solar=(gipt[(gipt['Start year'].isin([2026,2027,2028,2029,2030]))&(gipt.Status.isin(status))&(gipt.Type.isin(type))].groupby(['Status','Start year'])['Capacity (MW)'].sum()/1000).unstack()
solar=solar.reset_index()
solar.index=['Utility-scale solar']*len(solar)
#
onwind=(gipt[(gipt['Start year'].isin([2026,2027,2028,2029,2030]))&(gipt.Status.isin(status))&(gipt.Technology.isin(['Onshore','Unknown']))].groupby(['Status','Start year'])['Capacity (MW)'].sum()/1000).unstack()
onwind=onwind.reset_index()
onwind.index=['Onshore wind']*len(onwind)
#
offwind=(gipt[(gipt['Start year'].isin([2026,2027,2028,2029,2030]))&(gipt.Status.isin(status))&(gipt.Technology.str.contains('Offshore'))].groupby(['Status','Start year'])['Capacity (MW)'].sum()/1000).unstack()
offwind=offwind.reset_index()
offwind.index=['Offshore wind']*len(offwind)

hydro=(gipt[(gipt['Start year'].isin([2026,2027,2028,2029,2030]))&(gipt.Status.isin(status))&hydro_mask].groupby(['Status','Start year'])['Capacity (MW)'].sum()/1000).unstack()
hydro=hydro.reset_index()
hydro.index=['Hydro']*len(hydro)

tmp=pandas.concat([solar,onwind,offwind,hydro],axis=0)
tmp.to_csv('./indev_annual.csv')



