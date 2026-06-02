"""Load the GIPT source data and prepare it for the summary tables.

Consolidates the original notebook's prep cells (1-5):

* read the GIPT 'Power facilities' sheet and the region definitions;
* apply the standard capacity / sub-threshold / status adjustments;
* harmonise utility-scale solar capacity to MWac using the GSPT (the vectorised
  version of the conversion; the old slow loop has been dropped);
* append distributed solar from the GSPT;
* build the bi-national-hydro-adjusted frame used by the status tables.

Run :func:`load_gipt` once per session; every workbook updater then works off
the returned :class:`GiptData` without re-reading anything.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config
from .hydro import build_hydro_adjusted

# DC -> AC conversion factor for solar (value from TransitionZero).
SOLAR_DC_TO_AC = 0.87
# Minimum AC+DC sample size before an area uses its own observed ratio rather
# than falling back to its parent area's ratio.
SOLAR_MIN_SAMPLE = 30


@dataclass
class GiptData:
    """Prepared GIPT data shared by every workbook updater."""

    gipt: pd.DataFrame          # all facilities, adjusted, indexed by GEM unit/phase ID
    defs: pd.DataFrame          # custom-region definitions (G7, EU27, BRICS, ...)
    hydro_adjust: pd.DataFrame  # long form with bi-national hydro split by country
    gipt_file: str              # source path, for the run summary


def load_gipt(gipt_file=None, gspt_file=None):
    """Read and prepare the GIPT. See the module docstring for the steps."""
    gipt_file = gipt_file or config.GIPT_FILE
    gspt_file = gspt_file or config.GSPT_FILE

    gipt = pd.read_excel(gipt_file, sheet_name=config.GIPT_FACILITIES_SHEET)
    defs = pd.read_excel(gipt_file, sheet_name=config.GIPT_REGIONS_SHEET)

    gipt = _apply_adjustments(gipt)
    gipt = _harmonise_solar_to_ac(gipt, gspt_file)
    gipt = _append_distributed_solar(gipt, gspt_file)

    hydro_adjust = build_hydro_adjusted(gipt)

    return GiptData(gipt=gipt, defs=defs, hydro_adjust=hydro_adjust, gipt_file=gipt_file)


# --- prep steps --------------------------------------------------------------

def _apply_adjustments(gipt):
    """Capacity clean-up, sub-threshold removal, and status remaps (cell 2)."""
    # 'not found' capacities -> 0.0
    gipt.loc[gipt["Capacity (MW)"] == "not found", "Capacity (MW)"] = np.nan
    gipt["Capacity (MW)"] = gipt["Capacity (MW)"].astype(float).fillna(0.0)

    # Sub-threshold conventions: drop wind under 10 MW. (The bioenergy threshold
    # was removed Sept 2025 and the oil/gas threshold dropped March 2026, so
    # those are intentionally no longer applied.)
    gipt = gipt.drop(gipt[(gipt.Type == "wind") & (gipt["Capacity (MW)"] < 10)].index)

    # Collapse 'inferred' statuses onto their base status.
    gipt.loc[gipt.Status == "cancelled - inferred 4 y", "Status"] = "cancelled"
    gipt.loc[gipt.Status == "shelved - inferred 2 y", "Status"] = "shelved"

    return gipt


def _harmonise_solar_to_ac(gipt, gspt_file):
    """Replace utility-scale solar capacities with MWac-harmonised values (cell 4).

    Known DC ratings are converted with the fixed factor; 'unknown' ratings are
    scaled by the probability they are already AC, estimated from AC/DC counts
    at country level with fallback to subregion, then region.
    """
    df = pd.read_excel(gspt_file, sheet_name="Utility-Scale (1 MW+)")

    # Sub-1 MW projects are excluded before conversion (some would drop below
    # 1 MW afterwards, so this can't be done later).
    df = df[df["Capacity (MW)"] >= 1].copy()
    df["Capacity (MW) orig"] = df["Capacity (MW)"]

    for col in ["Other IDs (location)", "Other IDs (unit/phase)"]:
        df[col] = df[col].fillna("")

    # Known DC -> AC.
    mask_dc = df["Capacity Rating"].eq("MWp/dc")
    df.loc[mask_dc, "Capacity (MW)"] = df.loc[mask_dc, "Capacity (MW) orig"] * SOLAR_DC_TO_AC

    # Strip WEPP / WKSL ids so government-sourced records don't bias the AC/DC split.
    df["Other IDs (location)"] = df["Other IDs (location)"].apply(_strip_wepp_wksl)
    df["Other IDs (unit/phase)"] = df["Other IDs (unit/phase)"].apply(_strip_wepp_wksl)

    # Probability base: only rows with a known rating and no remaining other IDs.
    base = df[
        df["Other IDs (location)"].eq("")
        & df["Other IDs (unit/phase)"].eq("")
        & df["Capacity Rating"].isin(["MWac", "MWp/dc"])
    ].copy()

    region_prob = _ac_probability(base, "Region")
    subregion_prob = _ac_probability_with_fallback(base, df, "Subregion", "Region", region_prob)
    country_prob = _ac_probability_with_fallback(base, df, "Country/Area", "Subregion", subregion_prob)

    # Scale 'unknown' ratings by their AC probability.
    df["Capacity Rating orig"] = df["Capacity Rating"]
    unknown = df["Capacity Rating"].eq("unknown")
    prob = df["Country/Area"].map(country_prob).fillna(0.5)
    df.loc[unknown, "Capacity (MW)"] = (
        ((1 - SOLAR_DC_TO_AC) * prob[unknown] + SOLAR_DC_TO_AC)
        * df.loc[unknown, "Capacity (MW) orig"]
    )
    df["Capacity Rating"] = "MWac"

    # Write the harmonised solar capacities back into the GIPT.
    gipt = gipt.set_index("GEM unit/phase ID")
    gipt.loc[df["GEM phase ID"], "Capacity (MW)"] = df["Capacity (MW)"].values
    return gipt


def _append_distributed_solar(gipt, gspt_file):
    """Append distributed (<1 MW) solar as 'solar dist' rows (cell 5)."""
    dist = pd.read_excel(gspt_file, sheet_name="Distributed (<1 MW)")
    dist = dist[["Country/Area", "Capacity (MW)", "Status", "Subregion", "Region"]].copy()
    dist = dist.rename(columns={"Country/Area": "Country/area"})
    dist["Type"] = "solar dist"
    return pd.concat([gipt, dist])


# --- solar AC/DC probability helpers -----------------------------------------

def _strip_wepp_wksl(value):
    """Drop comma-separated IDs that start with WEPP or WKSL."""
    if not value:
        return ""
    parts = [p.strip() for p in value.split(",")]
    parts = [p for p in parts if p and not (p.startswith("WEPP") or p.startswith("WKSL"))]
    return ",".join(parts)


def _ac_counts(base, level):
    """AC and DC counts for each value of ``level`` (e.g. Region), plus their total."""
    counts = (
        base.groupby([level, "Capacity Rating"]).size()
        .unstack(fill_value=0)
        .reindex(columns=["MWac", "MWp/dc"], fill_value=0)
    )
    total = counts["MWac"] + counts["MWp/dc"]
    return counts, total


def _ac_probability(base, level):
    """P(AC) per area at one level; 50/50 where there are no counts."""
    counts, total = _ac_counts(base, level)
    return (counts["MWac"] / total).fillna(0.5)


def _ac_probability_with_fallback(base, df, level, parent_level, parent_prob):
    """P(AC) per area, falling back to the parent area where the sample is thin."""
    counts, total = _ac_counts(base, level)
    prob = counts["MWac"] / total

    area_to_parent = (
        df[[level, parent_level]].drop_duplicates(subset=[level])
        .set_index(level)[parent_level]
    )
    thin = total < SOLAR_MIN_SAMPLE
    prob.loc[thin] = area_to_parent.loc[thin.index[thin]].map(parent_prob).values
    return prob.fillna(0.5)
