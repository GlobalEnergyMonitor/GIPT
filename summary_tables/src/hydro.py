"""Bi-national hydropower handling.

Some hydropower projects span two countries. In the GIPT each is a single row
carrying the two partner countries and their split capacities in dedicated
columns. For any aggregation by country or region we need such a project counted
under *both* partners, each with its own share.

:func:`build_hydro_adjusted` reshapes the whole GIPT into a long frame where
every bi-national hydro project becomes two rows (one per partner) and every
other row is kept as-is. This mirrors the original notebook's
``gipt_hydro_adjust`` and is used by the region/country x status tables.
"""

import pandas as pd

# Source columns describing the two hydro partners.
_C1 = "Country/area 1 (hydropower only)"
_C1_CAP = "Country/area 1 Capacity (MW) (hydropower only)"
_C2 = "Country/area 2 (hydropower only)"
_C2_CAP = "Country/area 2 Capacity (MW) (hydropower only)"

# Columns carried through the reshape, in output order.
_CARRY_COLS = ["Country/area", "Capacity (MW)", "Type", "Region", "Subregion", "Status"]


def build_hydro_adjusted(gipt):
    """Return a long-form copy of ``gipt`` with bi-national hydro split by country.

    Rows whose second hydro country is null (i.e. every non-bi-national project,
    hydro or not) are kept with their own ``Capacity (MW)``. Rows with a second
    hydro country are replaced by two rows: one per partner country, each using
    that partner's split capacity.
    """
    is_binational = gipt[_C2].notnull()

    mono = gipt.loc[~is_binational, _CARRY_COLS]

    binational = gipt.loc[is_binational]
    partner1 = binational[[_C1, _C1_CAP, "Type", "Region", "Subregion", "Status"]].copy()
    partner2 = binational[[_C2, _C2_CAP, "Type", "Region", "Subregion", "Status"]].copy()
    partner1.columns = _CARRY_COLS
    partner2.columns = _CARRY_COLS

    return pd.concat([mono, partner1, partner2])


def split_hydro_by_region(df):
    """Hydropower rows reshaped for region/subregion aggregation (cell 6 logic).

    Mono projects use their country-1 capacity; bi-national projects contribute
    each partner's capacity, both attributed to the *project's* own region and
    subregion. Returns hydropower-only rows with Region, Subregion, Type,
    Capacity (MW).
    """
    mono = df[df[_C2].isnull()]
    binational = df[df[_C2].notnull()]

    cols = ["Region", "Subregion", "Type"]
    mono_part = mono[cols + [_C1_CAP]].rename(columns={_C1_CAP: "Capacity (MW)"})
    partner1 = binational[cols + [_C2_CAP]].rename(columns={_C2_CAP: "Capacity (MW)"})
    partner2 = binational[cols + [_C1_CAP]].rename(columns={_C1_CAP: "Capacity (MW)"})

    out = pd.concat([mono_part, partner1, partner2])
    return out[out["Type"] == "hydropower"]


def split_hydro_by_country(df):
    """Hydropower rows reshaped for country aggregation (cell 8 logic).

    Mono projects keep their Country/area, valued at the country-1 hydro
    capacity; bi-national projects become two rows, one under each partner
    country with that partner's capacity. Returns hydropower-only rows with
    Country/area, Capacity (MW).
    """
    mono = df[df[_C2].isnull()]
    binational = df[df[_C2].notnull()]

    mono_part = mono[["Country/area", "Type", _C1_CAP]].rename(columns={_C1_CAP: "Capacity (MW)"})
    partner1 = binational[[_C2, _C2_CAP, "Type"]].rename(
        columns={_C2: "Country/area", _C2_CAP: "Capacity (MW)"})
    partner2 = binational[[_C1, _C1_CAP, "Type"]].rename(
        columns={_C1: "Country/area", _C1_CAP: "Capacity (MW)"})

    out = pd.concat([mono_part, partner1, partner2])
    return out[out["Type"] == "hydropower"]
