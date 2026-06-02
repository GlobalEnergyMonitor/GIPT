"""Light sense checks and run summaries.

Deliberately small: print enough to eyeball a run, and warn (not crash) when the
data contains a Type or Status the aggregations don't know about, since unknown
categories are silently dropped by the summary tables.
"""

from . import config


def summarise_gipt(data):
    """Print a quick profile of the prepared GIPT for a sanity check."""
    gipt = data.gipt
    print(f"Source : {data.gipt_file}")
    print(f"Rows   : {len(gipt):,}")
    print(f"Total  : {gipt['Capacity (MW)'].sum():,.0f} MW")
    print(f"Nulls  : {int(gipt['Capacity (MW)'].isna().sum())} blank capacities")

    print("\nCapacity (MW) by status:")
    _print_totals(gipt.groupby("Status")["Capacity (MW)"].sum())

    print("\nCapacity (MW) by type:")
    _print_totals(gipt.groupby("Type")["Capacity (MW)"].sum())

    _warn_unknown(gipt["Type"], config.TYPES, "Type")
    _warn_unknown(gipt["Status"], config.STATUSES, "Status")


def _print_totals(series):
    for name, value in series.sort_values(ascending=False).items():
        print(f"  {name:<22} {value:>15,.0f}")


def _warn_unknown(series, known, label):
    """Flag category values not in the expected list (they get dropped downstream)."""
    unknown = sorted(set(series.dropna().unique()) - set(known))
    if unknown:
        print(f"\n[warn] unrecognised {label} values (dropped by the summaries): {unknown}")
