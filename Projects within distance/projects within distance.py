'''
A FUNCTION TO SUBSET THE GIPT FOR PROJECTS WITHIN A CERTAIN DISTANCE FROM A SPECIFIED LATITUDE AND LONGITUDE
 
USAGE:

1) Point the 'gipt_file_location' to your copy of the latest GIPT file

2) Modify 'target_lat' and 'target_lon' to you chosen coordinates

3) Specify search radius in 'distance_km'; that is the distance from the specified coordiantes searched for projects

'''

# --- REQUIRED PACKAGES
import numpy as np
import pandas as pd
from pyproj import Geod

# ---- LOAD THE GIPT DATA
gipt_file_location= './Global Integrated Power September 2025 II.xlsx'
gipt=pandas.read_excel(gipt_file_location,sheet_name='Power facilities')

# ---- THE FUNCTION
_geod = Geod(ellps="WGS84")

def subset_by_radius_geodesic(
    df,
    target_lat,
    target_lon,
    distance_km,
    lat_col="Latitude",
    lon_col="Longitude",
    approx_col=None,
    include_approx=True,
    add_distance=True,
):
    """
    Return rows within distance_km of (target_lat, target_lon) using:
      1) bounding-box prefilter to speed things up
      2) exact WGS84 geodesic distances (vectorized via pyproj.Geod)
      3) optional inclusion/exclusion of approximate coordinates
    Parameters
    ----------
    df : pandas.DataFrame
        Input dataframe containing latitude, longitude, and optional approx_col. Including these as some trackers name these columns slightly differently
    target_lat, target_lon : float
        Reference latitude and longitude (degrees).
    distance_km : float
        Search radius distance in kilometers.
    lat_col, lon_col : str
        Column names for latitude and longitude. Including these as some trackers name these columns slightly differently
    approx_col : str or None
        Column indicating location accuracy (values may be 'Exact', 'Approximate', or blank/NaN).
        If None, no accuracy filtering is performed.
    include_approx : bool
        If False, exclude rows where accuracy is 'Approximate' or blank.
    add_distance : bool
        If True, add a 'dist_km' column with computed distance.
    Returns
    -------
    pandas.DataFrame
        Subset of rows within distance_km and matching location-accuracy filter.
    """
    if distance_km <= 0:
        return df.iloc[0:0].copy()
    # Drop rows missing coordinates
    dfx = df.dropna(subset=[lat_col, lon_col]).copy()
    if len(dfx) == 0:
        return dfx
    # --- Handle approximate coordinates if column provided ---
    if approx_col is not None and approx_col in dfx.columns:
        acc = dfx[approx_col].fillna("").str.strip().str.lower()
        is_approx = (acc != "exact")  # 'Approximate' or blank → True
        if not include_approx:
            dfx = dfx.loc[~is_approx]
        if len(dfx) == 0:
            return dfx
    # --- Bounding box prefilter ---
    dlat = distance_km / 111.0
    coslat = np.cos(np.radians(target_lat))
    coslat = np.clip(coslat, 1e-12, None)
    dlon = distance_km / (111.320 * coslat)
    lat_min, lat_max = target_lat - dlat, target_lat + dlat
    lon_min, lon_max = target_lon - dlon, target_lon + dlon
    def _norm_lon(arr):
        return (arr + 180.0) % 360.0 - 180.0
    lats = dfx[lat_col].to_numpy(dtype=float)
    lons = _norm_lon(dfx[lon_col].to_numpy(dtype=float))
    lon0n = _norm_lon(np.array([target_lon]))[0]
    lat_mask = (lats >= lat_min) & (lats <= lat_max)
    lon_min_n = _norm_lon(np.array([lon_min]))[0]
    lon_max_n = _norm_lon(np.array([lon_max]))[0]
    lon_mask = (lons >= lon_min_n) & (lons <= lon_max_n) if lon_min_n <= lon_max_n else (lons >= lon_min_n) | (lons <= lon_max_n)
    pre_mask = lat_mask & lon_mask
    if not np.any(pre_mask):
        return dfx.iloc[0:0].copy()
    cand = dfx.loc[pre_mask].copy()
    # --- Vectorized geodesic distance calculation (exact WGS84) ---
    lon_arr = cand[lon_col].to_numpy(dtype=float)
    lat_arr = cand[lat_col].to_numpy(dtype=float)
    _, _, dist_m = _geod.inv(
        np.full(lon_arr.shape, lon0n),
        np.full(lat_arr.shape, target_lat, dtype=float),
        _norm_lon(lon_arr),
        lat_arr
    )
    dist_km = dist_m / 1000.0
    within = dist_km <= distance_km
    if not np.any(within):
        return cand.iloc[0:0].copy()
    out = cand.loc[within].copy()
    if add_distance:
        out["dist_km"] = dist_km[within]
    out = out.reset_index(drop=True)
    return out

# ---- EXAMPLE USAGE: FIND PROJECTS WITHIN 100KM OF JAKARTA -6.175, 106.835
subset = subset_by_radius_geodesic(
    gipt, # the pandas dataframe to which we apply the function
    target_lat=-6.175, # the Latitude in decimal degrees from which the distance is calculated. Right click your desired location in Google maps to reveal exact lat/lon
    target_lon=106.835, # the Longitude in decimal degrees from which the distance is calculated. Right click your desired location in Google maps to reveal exact lat/lon
    distance_km=100, # All projects within 'X' km of the lat/lon above. Modify as you wish.
    include_approx=True, # True for inclusive of 'Approximate' and blank in the 'Location accuracy' column; or False to exclude these and only use 'Exact'
	lat_col="Latitude", # No need to change for GIPT
    lon_col="Longitude", # No need to change for GIPT
    approx_col="Location accuracy", # No need to change for GIPT
)

