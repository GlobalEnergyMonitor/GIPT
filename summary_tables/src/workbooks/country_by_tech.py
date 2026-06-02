"""Power capacity by country and technology, grouped by status.

Target sheet: "Power capacity by country and technology, grouped by status".
One tab per status; each tab is one row per country (with its region and
subregion) x technology. Bi-national hydropower is split between partner
countries. Original notebook cells 8-9.
"""

import numpy as np

from .. import config, sheets
from ..hydro import split_hydro_by_country

SHEET_KEY = config.SPREADSHEET_KEYS["country_by_tech"]
ANCHOR = "A6"
TITLE = "Power capacity by country and technology, grouped by status"

# Worksheet tab -> the project status it shows.
TAB_STATUS = {
    "Announced": "announced",
    "Pre-construction": "pre-construction",
    "Construction": "construction",
    "Shelved": "shelved",
    "Operating": "operating",
    "Mothballed": "mothballed",
    "Cancelled": "cancelled",
    "Retired": "retired",
}

# Technology columns written to the sheet, in order (distributed solar excluded).
OUTPUT_TECHS = ["coal", "oil/gas", "utility-scale solar", "wind",
                "nuclear", "hydropower", "bioenergy", "geothermal"]


def capacity_for_status(gipt, status):
    """One row per country x technology for a single status.

    Output columns: region, sub-region, Country/area, then the eight technologies.
    Every country in the GIPT appears (sorted), zero-filled where absent.
    """
    filt = gipt[gipt.Status == status]
    all_countries = np.sort(gipt["Country/area"].unique())

    # Hydropower, bi-national split, by country.
    hydro = split_hydro_by_country(filt)
    hydro_by_country = hydro.groupby(["Country/area", "Type"])["Capacity (MW)"].sum().unstack(fill_value=0.0)

    # Every technology, by country; then swap in the split hydropower.
    result = filt.groupby(["Country/area", "Type"])["Capacity (MW)"].sum().unstack(fill_value=0.0)
    result["hydropower"] = (hydro_by_country["hydropower"]
                            if "hydropower" in hydro_by_country.columns else 0.0)
    result["hydropower"] = result["hydropower"].fillna(0.0)

    # Pin to every country and the output technologies.
    for tech in OUTPUT_TECHS:
        if tech not in result.columns:
            result[tech] = 0.0
    result = result.reindex(index=all_countries, fill_value=0.0)[OUTPUT_TECHS]

    # Prepend region / sub-region from the GIPT.
    country_info = (gipt[["Country/area", "Region", "Subregion"]]
                    .drop_duplicates(subset="Country/area").set_index("Country/area"))
    result["region"] = result.index.map(country_info["Region"].get)
    result["sub-region"] = result.index.map(country_info["Subregion"].get)

    result.index.name = "Country/area"
    result = result.reset_index()
    return result[["region", "sub-region", "Country/area"] + OUTPUT_TECHS]


def build(data):
    """Return ``{tab: dataframe}`` for every status tab (pure, no I/O)."""
    return {tab: capacity_for_status(data.gipt, status)
            for tab, status in TAB_STATUS.items()}


def push(frames, gc=None, tabs=None):
    """Write the built frames to the Google Sheet (all tabs, or just ``tabs``)."""
    spreadsheet = sheets.open_sheet(SHEET_KEY, gc=gc)
    selected = frames if tabs is None else {t: frames[t] for t in tabs}
    for tab, df in selected.items():
        sheets.write_frame(spreadsheet, tab, df, ANCHOR)
        print(f"  wrote {tab} ({df.shape[0]}x{df.shape[1]}) at {ANCHOR}")


def run(data, write=False, gc=None):
    """Build, print a per-tab summary, optionally push, and return the frames."""
    frames = build(data)
    print(f"{TITLE}\n{sheets.url(SHEET_KEY)}")
    for tab, df in frames.items():
        total = df[OUTPUT_TECHS].to_numpy().sum()
        print(f"  {tab:<18} {df.shape[0]}x{df.shape[1]}  global total {total:>14,.0f} MW")
    if write:
        print("writing to sheet...")
        push(frames, gc=gc)
    else:
        print("(dry run - pass write=True to push)")
    return frames
