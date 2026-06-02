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
