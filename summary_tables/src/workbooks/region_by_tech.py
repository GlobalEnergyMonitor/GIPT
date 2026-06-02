"""Power capacity by region and technology, grouped by status.

Target sheet: "Power capacity by region and technology, grouped by status".
One tab per status; each tab is region/subregion (rows) x technology (columns).
Bi-national hydropower is split so partner capacities are attributed correctly.
Original notebook cells 6-7.
"""

import pandas as pd

from .. import config, sheets
from ..hydro import split_hydro_by_region
from ..tables import ensure_dimensions

SHEET_KEY = config.SPREADSHEET_KEYS["region_by_tech"]
ANCHOR = "B6"

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

# Non-hydro technologies are taken from the plain per-type aggregation; the
# hydropower column is taken from the bi-national split instead.
_NON_HYDRO = ["coal", "oil/gas", "utility-scale solar", "solar dist", "wind",
              "nuclear", "bioenergy", "geothermal"]


def capacity_for_status(gipt, status):
    """Region/subregion x technology capacity for a single status."""
    filt = gipt[gipt.Status == status]

    # Hydropower, bi-national split, aggregated by region and by subregion.
    hydro = split_hydro_by_region(filt)
    hydro_combined = pd.concat([
        hydro.groupby(["Region", "Type"])["Capacity (MW)"].sum().unstack(fill_value=0.0),
        hydro.groupby(["Subregion", "Type"])["Capacity (MW)"].sum().unstack(fill_value=0.0),
    ])
    hydro_df = ensure_dimensions(hydro_combined, config.REGIONS_AND_SUBREGIONS, ["hydropower"])

    # Every technology, aggregated by region and by subregion.
    all_combined = pd.concat([
        filt.groupby(["Region", "Type"])["Capacity (MW)"].sum().unstack(fill_value=0.0),
        filt.groupby(["Subregion", "Type"])["Capacity (MW)"].sum().unstack(fill_value=0.0),
    ])
    all_df = ensure_dimensions(all_combined, config.REGIONS_AND_SUBREGIONS, config.TYPES)

    # Hydropower from the split frame; all other techs from the plain aggregation.
    combined = hydro_df.add(all_df[_NON_HYDRO], fill_value=0.0)
    result = combined[OUTPUT_TECHS]
    result.index.name = status
    return result


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
    print(f"region_by_tech -> sheet {SHEET_KEY}")
    present = [r for r in config.WORLD_REGIONS if r in next(iter(frames.values())).index]
    for tab, df in frames.items():
        world_total = df.loc[present].to_numpy().sum()
        print(f"  {tab:<18} {df.shape[0]}x{df.shape[1]}  world total {world_total:>14,.0f} MW")
    if write:
        print("writing to sheet...")
        push(frames, gc=gc)
    else:
        print("(dry run - pass write=True to push to the sheet)")
    return frames
