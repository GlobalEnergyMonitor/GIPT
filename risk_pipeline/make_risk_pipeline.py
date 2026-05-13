import json
import time
from pathlib import Path

import numpy as np
import pandas as pd


# -------------------------------------------------------------------
# 0. User-editable settings
# -------------------------------------------------------------------

# This script assumes the project pipeline comes from the GIPT Excel export,
# using the same workbook structure and the same sheet name each time.
#
# When running the whole file, __file__ exists. When running selected code in
# an IDE/interactive console, __file__ may not exist. In that case, use the
# current folder if it already looks like risk_pipeline; otherwise use the
# risk_pipeline folder under the current working directory.
try:
    SCRIPT_DIR = Path(__file__).resolve().parent
except NameError:
    cwd = Path.cwd()
    if (cwd / "Global-Integrated-Power-March-2026-II.xlsx").exists():
        SCRIPT_DIR = cwd
    else:
        SCRIPT_DIR = cwd / "risk_pipeline"

PROJECTS_PATH = SCRIPT_DIR / "Global-Integrated-Power-March-2026-II.xlsx"
PROJECTS_SHEET_NAME = "Power facilities"

BASE_ASSUMPTIONS_PATH = SCRIPT_DIR / "base_assumptions.csv"
GEO_MULTIPLIERS_PATH = SCRIPT_DIR / "geography_multipliers.csv"

PREPARED_OUTPUT = SCRIPT_DIR / "prepared_project_risk_inputs.csv"
ANNUAL_RUN_OUTPUT = SCRIPT_DIR / "simulated_annual_additions_by_run.csv"
ANNUAL_STATUS_SUMMARY_OUTPUT = SCRIPT_DIR / "simulated_annual_additions_by_status_summary.csv"
ANNUAL_STATUS_DATE_KNOWN_SUMMARY_OUTPUT = (
    SCRIPT_DIR / "simulated_annual_additions_by_status_date_known_summary.csv"
)
ANNUAL_TOTAL_SUMMARY_OUTPUT = SCRIPT_DIR / "simulated_annual_additions_total_summary.csv"
ANNUAL_TOTAL_BY_TECHNOLOGY_SUMMARY_OUTPUT = (
    SCRIPT_DIR / "simulated_annual_additions_total_by_technology_summary.csv"
)
ANNUAL_TOTAL_BY_TECHNOLOGY_DATE_KNOWN_SUMMARY_OUTPUT = (
    SCRIPT_DIR / "simulated_annual_additions_total_by_technology_date_known_summary.csv"
)
RISK_D3_OUTPUT = SCRIPT_DIR / "risk_adjusted_tripling_d3_data.json"

# Backwards-compatible alias in case older IDE selections refer to this name.
ANNUAL_TECH_TOTAL_SUMMARY_OUTPUT = ANNUAL_TOTAL_BY_TECHNOLOGY_SUMMARY_OUTPUT

SCENARIO = "central"
RUNS = 1000
RANDOM_SEED = 42

CURRENT_YEAR = 2026
START_YEAR = 2026
END_YEAR = 2030

STATUSES_TO_KEEP = ["construction", "pre-construction", "announced"]
TYPES_TO_KEEP = ["wind", "utility-scale solar", "hydropower"]

PROJECT_COLUMNS = [
    "GEM unit/phase ID",
    "Country/area",
    "Subregion",
    "Region",
    "Capacity (MW)",
    "Status",
    "Start year",
    "Type",
    "Technology",
]


# -------------------------------------------------------------------
# 1. Small helpers
# -------------------------------------------------------------------

def clean_text_col(s):
    """Trim whitespace while preserving missing values as pandas strings."""
    return s.astype("string").str.strip()


def normalize_key(s):
    """Create lower-case join keys so assumptions match consistently."""
    return clean_text_col(s).str.lower()


def clean_triangular_inputs(low, mode, high):
    """
    NumPy's triangular draw requires low <= mode <= high.

    This does not invent missing values. Missing assumptions are caught before
    simulation. It only fixes accidental ordering problems such as mode > max.
    """
    low = low.copy()
    mode = mode.copy()
    high = high.copy()

    high = np.maximum(high, low)
    mode = np.minimum(np.maximum(mode, low), high)

    return low, mode, high


def p10(x):
    return x.quantile(0.10)


def p50(x):
    return x.quantile(0.50)


def p90(x):
    return x.quantile(0.90)


# -------------------------------------------------------------------
# 2. Read input files
# -------------------------------------------------------------------

print(f"Reading project workbook: {PROJECTS_PATH}")
print(f"Sheet: {PROJECTS_SHEET_NAME}")

projects = pd.read_excel(
    PROJECTS_PATH,
    sheet_name=PROJECTS_SHEET_NAME,
    usecols=PROJECT_COLUMNS,
)

base = pd.read_csv(BASE_ASSUMPTIONS_PATH)
geo = pd.read_csv(GEO_MULTIPLIERS_PATH)


# -------------------------------------------------------------------
# 3. Validate required columns
# -------------------------------------------------------------------

missing_project_cols = [c for c in PROJECT_COLUMNS if c not in projects.columns]
if missing_project_cols:
    raise ValueError(f"Missing required project columns: {missing_project_cols}")

required_base_cols = [
    "scenario",
    "technology",
    "status",
    "date_known",
    "cancel_prob",
    "delay_min",
    "delay_mode",
    "delay_max",
    "undated_remaining_min",
    "undated_remaining_mode",
    "undated_remaining_max",
]

missing_base_cols = [c for c in required_base_cols if c not in base.columns]
if missing_base_cols:
    raise ValueError(f"Missing required base assumption columns: {missing_base_cols}")

required_geo_cols = [
    "geography_key",
    "technology",
    "cancel_multiplier",
    "delay_multiplier",
    "remaining_time_multiplier",
]

missing_geo_cols = [c for c in required_geo_cols if c not in geo.columns]
if missing_geo_cols:
    raise ValueError(f"Missing required geography multiplier columns: {missing_geo_cols}")


# -------------------------------------------------------------------
# 4. Clean and standardise project fields
# -------------------------------------------------------------------

for col in [
    "GEM unit/phase ID",
    "Country/area",
    "Subregion",
    "Region",
    "Status",
    "Type",
    "Technology",
]:
    projects[col] = clean_text_col(projects[col])

projects["Status"] = projects["Status"].str.lower()
projects["Type"] = projects["Type"].str.lower()

projects["Capacity (MW)"] = pd.to_numeric(projects["Capacity (MW)"], errors="coerce")
projects["Start year"] = pd.to_numeric(projects["Start year"], errors="coerce")

# Keep the technologies and statuses that are in this illustrative risk model.
projects = projects[
    projects["Type"].isin(TYPES_TO_KEEP)
    & projects["Status"].isin(STATUSES_TO_KEEP)
].copy()


# -------------------------------------------------------------------
# 5. Exclude pumped hydropower / storage
# -------------------------------------------------------------------

# Pumped hydro is storage, not generation capacity for this additions outlook.
pumped_mask = projects["Technology"].str.contains("pumped", case=False, na=False)
excluded_pumped = projects[pumped_mask].copy()

print(f"\nExcluding pumped hydropower/storage rows: {len(excluded_pumped):,}")
if len(excluded_pumped) > 0:
    print(
        excluded_pumped
        .groupby(["Type", "Technology"], dropna=False)
        .agg(
            rows=("GEM unit/phase ID", "count"),
            capacity_mw=("Capacity (MW)", "sum"),
        )
        .reset_index()
        .to_string(index=False)
    )

projects = projects[~pumped_mask].copy()


# -------------------------------------------------------------------
# 6. Derive model fields used for assumption matching
# -------------------------------------------------------------------

# date_known is based only on whether a Start year exists.
projects["date_known"] = np.where(projects["Start year"].notna(), "known", "unknown")

# Wind needs to be split into offshore/onshore using the Technology field.
# Utility-scale solar and hydropower keep their Type value.
type_key = normalize_key(projects["Type"])
technology_key_raw = normalize_key(projects["Technology"])

projects["model_technology"] = type_key

wind_mask = type_key.eq("wind")
offshore_mask = wind_mask & technology_key_raw.str.contains("off", na=False)
onshore_mask = wind_mask & ~technology_key_raw.str.contains("off", na=False)

projects.loc[offshore_mask, "model_technology"] = "offshore wind"
projects.loc[onshore_mask, "model_technology"] = "onshore wind"

# Join key used against base_assumptions.csv.
projects["technology_key"] = normalize_key(projects["model_technology"])

# Geography layer:
# - China has its own multiplier regardless of Region.
# - All other projects use their Region value.
projects["geography_key"] = np.where(
    projects["Country/area"].eq("China"),
    "China",
    projects["Region"],
)


# -------------------------------------------------------------------
# 7. Clean assumptions tables
# -------------------------------------------------------------------

base["scenario"] = normalize_key(base["scenario"])
base["technology"] = clean_text_col(base["technology"])
base["technology_key"] = normalize_key(base["technology"])
base["status"] = normalize_key(base["status"])
base["date_known"] = normalize_key(base["date_known"])

numeric_base_cols = [
    "cancel_prob",
    "delay_min",
    "delay_mode",
    "delay_max",
    "undated_remaining_min",
    "undated_remaining_mode",
    "undated_remaining_max",
]

for col in numeric_base_cols:
    base[col] = pd.to_numeric(base[col], errors="coerce")

geo["geography_key"] = clean_text_col(geo["geography_key"])
geo["technology"] = clean_text_col(geo["technology"])
geo["technology_key"] = normalize_key(geo["technology"])

numeric_geo_cols = [
    "cancel_multiplier",
    "delay_multiplier",
    "remaining_time_multiplier",
]

for col in numeric_geo_cols:
    geo[col] = pd.to_numeric(geo[col], errors="coerce")


# -------------------------------------------------------------------
# 8. Merge assumptions and geography multipliers
# -------------------------------------------------------------------

base_scenario = base[base["scenario"] == SCENARIO].copy()

if len(base_scenario) == 0:
    available_scenarios = sorted(base["scenario"].dropna().unique())
    raise ValueError(
        f"No rows found in base_assumptions.csv for scenario '{SCENARIO}'. "
        f"Available scenarios: {available_scenarios}"
    )

model_df = projects.merge(
    base_scenario,
    left_on=["technology_key", "Status", "date_known"],
    right_on=["technology_key", "status", "date_known"],
    how="left",
    validate="many_to_one",
)

model_df = model_df.merge(
    geo[
        [
            "geography_key",
            "technology_key",
            "cancel_multiplier",
            "delay_multiplier",
            "remaining_time_multiplier",
        ]
    ],
    on=["geography_key", "technology_key"],
    how="left",
    validate="many_to_one",
)


# -------------------------------------------------------------------
# 9. Apply geography multipliers
# -------------------------------------------------------------------

# Keep cancellation probability below 1 so every category has at least some
# chance of delivery in the illustrative model.
model_df["final_cancel_prob"] = (
    model_df["cancel_prob"] * model_df["cancel_multiplier"]
).clip(lower=0, upper=0.95)

for col in ["delay_min", "delay_mode", "delay_max"]:
    model_df[f"final_{col}"] = model_df[col] * model_df["delay_multiplier"]

for col in [
    "undated_remaining_min",
    "undated_remaining_mode",
    "undated_remaining_max",
]:
    model_df[f"final_{col}"] = (
        model_df[col] * model_df["remaining_time_multiplier"]
    )


# -------------------------------------------------------------------
# 10. Diagnostics before simulation
# -------------------------------------------------------------------

missing_assumptions = model_df[model_df["cancel_prob"].isna()]

if len(missing_assumptions) > 0:
    print("\nWARNING: Some projects did not match base assumptions.")
    print("Unmatched assumption combinations:")
    print(
        missing_assumptions
        .groupby(["model_technology", "Status", "date_known"], dropna=False)
        .agg(
            rows=("GEM unit/phase ID", "count"),
            capacity_mw=("Capacity (MW)", "sum"),
        )
        .reset_index()
        .sort_values(["rows", "capacity_mw"], ascending=False)
        .to_string(index=False)
    )

missing_geo = model_df[model_df["cancel_multiplier"].isna()]

if len(missing_geo) > 0:
    print("\nWARNING: Some projects did not match geography multipliers.")
    print(
        missing_geo
        .groupby(["geography_key", "Country/area", "model_technology"], dropna=False)
        .agg(
            rows=("GEM unit/phase ID", "count"),
            capacity_mw=("Capacity (MW)", "sum"),
        )
        .reset_index()
        .sort_values(["rows", "capacity_mw"], ascending=False)
        .to_string(index=False)
    )

missing_capacity = model_df[model_df["Capacity (MW)"].isna()]

if len(missing_capacity) > 0:
    print(f"\nWARNING: Missing/non-numeric capacity rows: {len(missing_capacity):,}")


# -------------------------------------------------------------------
# 11. Save prepared modelling table
# -------------------------------------------------------------------

keep_cols = [
    "GEM unit/phase ID",
    "Country/area",
    "Subregion",
    "Region",
    "geography_key",
    "Capacity (MW)",
    "Status",
    "Start year",
    "date_known",
    "Type",
    "Technology",
    "model_technology",
    "scenario",
    "cancel_prob",
    "cancel_multiplier",
    "final_cancel_prob",
    "delay_min",
    "delay_mode",
    "delay_max",
    "delay_multiplier",
    "final_delay_min",
    "final_delay_mode",
    "final_delay_max",
    "undated_remaining_min",
    "undated_remaining_mode",
    "undated_remaining_max",
    "remaining_time_multiplier",
    "final_undated_remaining_min",
    "final_undated_remaining_mode",
    "final_undated_remaining_max",
]

model_df[keep_cols].to_csv(PREPARED_OUTPUT, index=False)

print(f"\nPrepared modelling table saved to {PREPARED_OUTPUT}")
print(f"Rows: {len(model_df):,}")

print("\nModel technology categories found:")
print(model_df["model_technology"].value_counts(dropna=False).to_string())

print("\nDate-known split:")
print(model_df["date_known"].value_counts(dropna=False).to_string())

print("\nStatus split:")
print(model_df["Status"].value_counts(dropna=False).to_string())


# -------------------------------------------------------------------
# 12. Stop if inputs are not simulation-ready
# -------------------------------------------------------------------

# Known-date projects need a Start year and delay assumptions.
# Unknown-date projects need delay assumptions and remaining-time assumptions.
missing_core_sim_inputs = model_df[
    model_df[
        [
            "Capacity (MW)",
            "final_cancel_prob",
            "final_delay_min",
            "final_delay_mode",
            "final_delay_max",
        ]
    ].isna().any(axis=1)
]

missing_unknown_timing = model_df[
    model_df["date_known"].eq("unknown")
    & model_df[
        [
            "final_undated_remaining_min",
            "final_undated_remaining_mode",
            "final_undated_remaining_max",
        ]
    ].isna().any(axis=1)
]

missing_known_start = model_df[
    model_df["date_known"].eq("known") & model_df["Start year"].isna()
]

if (
    len(missing_core_sim_inputs) > 0
    or len(missing_unknown_timing) > 0
    or len(missing_known_start) > 0
):
    print("\nERROR: Prepared inputs are not simulation-ready.")
    print(f"Rows missing core simulation values: {len(missing_core_sim_inputs):,}")
    print(f"Unknown-date rows missing remaining-time assumptions: {len(missing_unknown_timing):,}")
    print(f"Known-date rows missing Start year: {len(missing_known_start):,}")
    raise ValueError("Fix missing assumptions/inputs before running simulation.")


# -------------------------------------------------------------------
# 13. Vectorised Monte Carlo simulation
# -------------------------------------------------------------------

start_time = time.time()
rng = np.random.default_rng(RANDOM_SEED)

annual_records = []
n = len(model_df)

# Pull columns into NumPy arrays once. The run loop stays over simulations,
# not over projects, which keeps the model fast for 30,000+ rows.
capacity = model_df["Capacity (MW)"].to_numpy(dtype=float)
cancel_prob = model_df["final_cancel_prob"].to_numpy(dtype=float)

date_known = model_df["date_known"].to_numpy(dtype=str)
known_mask = date_known == "known"
unknown_mask = date_known == "unknown"

start_year = model_df["Start year"].to_numpy(dtype=float)

delay_min = model_df["final_delay_min"].to_numpy(dtype=float)
delay_mode = model_df["final_delay_mode"].to_numpy(dtype=float)
delay_max = model_df["final_delay_max"].to_numpy(dtype=float)

undated_min = model_df["final_undated_remaining_min"].to_numpy(dtype=float)
undated_mode = model_df["final_undated_remaining_mode"].to_numpy(dtype=float)
undated_max = model_df["final_undated_remaining_max"].to_numpy(dtype=float)

status = model_df["Status"].to_numpy(dtype=str)
technology = model_df["model_technology"].to_numpy(dtype=str)
scenario = model_df["scenario"].to_numpy(dtype=str)

delay_min, delay_mode, delay_max = clean_triangular_inputs(
    delay_min,
    delay_mode,
    delay_max,
)

undated_min, undated_mode, undated_max = clean_triangular_inputs(
    undated_min,
    undated_mode,
    undated_max,
)

for run_id in range(1, RUNS + 1):
    # 1. Draw cancellation for every project.
    cancelled = rng.random(n) < cancel_prob

    # 2. Draw additional delay for every project.
    delay_draw = rng.triangular(delay_min, delay_mode, delay_max)
    delay_years = np.maximum(0, np.rint(delay_draw).astype(int))

    delivery_year = np.full(n, np.nan)

    # 3. Known-date projects: stated Start year plus sampled delay.
    valid_known = known_mask & ~cancelled & ~np.isnan(start_year)
    delivery_year[valid_known] = (
        start_year[valid_known] + delay_years[valid_known]
    )

    # 4. Unknown-date projects: current year plus remaining time plus delay.
    valid_unknown = unknown_mask & ~cancelled
    remaining_draw = np.full(n, np.nan)

    remaining_draw[valid_unknown] = rng.triangular(
        undated_min[valid_unknown],
        undated_mode[valid_unknown],
        undated_max[valid_unknown],
    )

    total_time_to_delivery = remaining_draw + delay_draw

    delivery_year[valid_unknown] = (
        CURRENT_YEAR
        + np.floor(np.maximum(0, total_time_to_delivery[valid_unknown]))
    )

    # 5. Keep only projects delivered inside the chart/model window.
    delivered_mask = (
        ~cancelled
        & ~np.isnan(delivery_year)
        & (delivery_year >= START_YEAR)
        & (delivery_year <= END_YEAR)
        & ~np.isnan(capacity)
    )

    if delivered_mask.sum() == 0:
        continue

    run_projects = pd.DataFrame({
        "scenario": scenario[delivered_mask],
        "run_id": run_id,
        "year": delivery_year[delivered_mask].astype(int),
        "status": status[delivered_mask],
        "model_technology": technology[delivered_mask],
        "date_known": date_known[delivered_mask],
        "capacity_mw": capacity[delivered_mask],
    })

    run_annual = (
        run_projects
        .groupby(
            ["scenario", "run_id", "year", "status", "model_technology", "date_known"],
            as_index=False,
        )["capacity_mw"]
        .sum()
    )

    annual_records.append(run_annual)


if len(annual_records) > 0:
    annual = pd.concat(annual_records, ignore_index=True)
else:
    annual = pd.DataFrame(
        columns=[
            "scenario",
            "run_id",
            "year",
            "status",
            "model_technology",
            "date_known",
            "capacity_mw",
        ]
    )

elapsed = time.time() - start_time
print(f"\nSimulation completed in {elapsed:.1f} seconds")
print(f"Runs: {RUNS:,}")
print(f"Projects per run: {n:,}")
print(f"Average seconds per run: {elapsed / RUNS:.4f}")


# -------------------------------------------------------------------
# 14. Fill missing run/year/status/technology combinations with zero
# -------------------------------------------------------------------

# Filling the complete grid matters for quantiles. If a technology/status has
# zero additions in a run, it should count as zero, not disappear from the run.
scenarios = sorted(model_df["scenario"].dropna().unique())
years = list(range(START_YEAR, END_YEAR + 1))
statuses = sorted(model_df["Status"].dropna().unique())
technologies = sorted(model_df["model_technology"].dropna().unique())
date_known_values = ["known", "unknown"]

full_index = pd.MultiIndex.from_product(
    [scenarios, range(1, RUNS + 1), years, statuses, technologies, date_known_values],
    names=["scenario", "run_id", "year", "status", "model_technology", "date_known"],
)

annual_full = (
    annual
    .set_index(["scenario", "run_id", "year", "status", "model_technology", "date_known"])
    .reindex(full_index, fill_value=0)
    .reset_index()
)


# -------------------------------------------------------------------
# 15. Summarise distributions
# -------------------------------------------------------------------

annual_status_date_known_summary = (
    annual_full
    .groupby(["scenario", "year", "status", "model_technology", "date_known"], as_index=False)
    .agg(
        mean_mw=("capacity_mw", "mean"),
        p10_mw=("capacity_mw", p10),
        p50_mw=("capacity_mw", p50),
        p90_mw=("capacity_mw", p90),
    )
)

annual_by_status = (
    annual_full
    .groupby(
        ["scenario", "run_id", "year", "status", "model_technology"],
        as_index=False,
    )["capacity_mw"]
    .sum()
)

annual_status_summary = (
    annual_by_status
    .groupby(["scenario", "year", "status", "model_technology"], as_index=False)
    .agg(
        mean_mw=("capacity_mw", "mean"),
        p10_mw=("capacity_mw", p10),
        p50_mw=("capacity_mw", p50),
        p90_mw=("capacity_mw", p90),
    )
)

annual_total = (
    annual_full
    .groupby(["scenario", "run_id", "year"], as_index=False)["capacity_mw"]
    .sum()
)

annual_total_summary = (
    annual_total
    .groupby(["scenario", "year"], as_index=False)
    .agg(
        mean_mw=("capacity_mw", "mean"),
        p10_mw=("capacity_mw", p10),
        p50_mw=("capacity_mw", p50),
        p90_mw=("capacity_mw", p90),
    )
)

annual_total_by_technology_date_known = (
    annual_full
    .groupby(
        ["scenario", "run_id", "year", "model_technology", "date_known"],
        as_index=False,
    )["capacity_mw"]
    .sum()
)

annual_total_by_technology_date_known_summary = (
    annual_total_by_technology_date_known
    .groupby(["scenario", "year", "model_technology", "date_known"], as_index=False)
    .agg(
        mean_mw=("capacity_mw", "mean"),
        p10_mw=("capacity_mw", p10),
        p50_mw=("capacity_mw", p50),
        p90_mw=("capacity_mw", p90),
    )
)

annual_total_by_technology = (
    annual_full
    .groupby(
        ["scenario", "run_id", "year", "model_technology"],
        as_index=False,
    )["capacity_mw"]
    .sum()
)

annual_total_by_technology_summary = (
    annual_total_by_technology
    .groupby(["scenario", "year", "model_technology"], as_index=False)
    .agg(
        mean_mw=("capacity_mw", "mean"),
        p10_mw=("capacity_mw", p10),
        p50_mw=("capacity_mw", p50),
        p90_mw=("capacity_mw", p90),
    )
)

# D3 square chart risk mode:
# Sum 2026-2030 annual deliveries by run, then take p50 by status and
# date_known. In the chart, "pre2030" means known Start year and "unknown"
# means unknown Start year.
risk_status_window = (
    annual_full
    .groupby(["scenario", "run_id", "status", "date_known"], as_index=False)["capacity_mw"]
    .sum()
)

risk_status_window_summary = (
    risk_status_window
    .groupby(["scenario", "status", "date_known"], as_index=False)
    .agg(p50_mw=("capacity_mw", p50))
)

risk_d3_data = {}

for scenario_name, scenario_rows in risk_status_window_summary.groupby("scenario"):
    d3_entry = {
        "construction": {"pre2030": 0, "unknown": 0},
        "preConstruction": {"pre2030": 0, "unknown": 0},
        "announced": {"pre2030": 0, "unknown": 0},
        "triplingGap": 0,
        "annotation": {
            "line1": "Risk-adjusted",
            "line2": "p50 projection"
        },
        "explainer": (
            "Risk-adjusted mode shows p50 Monte Carlo capacity delivered in "
            "2026-2030, split by projects with known versus unknown start years."
        )
    }

    for _, row in scenario_rows.iterrows():
        status_key = {
            "construction": "construction",
            "pre-construction": "preConstruction",
            "announced": "announced",
        }.get(row["status"])

        if status_key is None:
            continue

        date_key = "pre2030" if row["date_known"] == "known" else "unknown"
        d3_entry[status_key][date_key] = row["p50_mw"] / 1000

    risk_d3_data["Global"] = d3_entry


# -------------------------------------------------------------------
# 16. Save simulation outputs
# -------------------------------------------------------------------

annual_full.to_csv(ANNUAL_RUN_OUTPUT, index=False)
annual_status_summary.to_csv(ANNUAL_STATUS_SUMMARY_OUTPUT, index=False)
annual_status_date_known_summary.to_csv(
    ANNUAL_STATUS_DATE_KNOWN_SUMMARY_OUTPUT,
    index=False,
)
annual_total_summary.to_csv(ANNUAL_TOTAL_SUMMARY_OUTPUT, index=False)
annual_total_by_technology_summary.to_csv(
    ANNUAL_TOTAL_BY_TECHNOLOGY_SUMMARY_OUTPUT,
    index=False,
)
annual_total_by_technology_date_known_summary.to_csv(
    ANNUAL_TOTAL_BY_TECHNOLOGY_DATE_KNOWN_SUMMARY_OUTPUT,
    index=False,
)

with open(RISK_D3_OUTPUT, "w", encoding="utf-8") as f:
    json.dump(risk_d3_data, f, indent=2)

print(f"\nSaved: {ANNUAL_RUN_OUTPUT}")
print(f"Saved: {ANNUAL_STATUS_SUMMARY_OUTPUT}")
print(f"Saved: {ANNUAL_STATUS_DATE_KNOWN_SUMMARY_OUTPUT}")
print(f"Saved: {ANNUAL_TOTAL_SUMMARY_OUTPUT}")
print(f"Saved: {ANNUAL_TOTAL_BY_TECHNOLOGY_SUMMARY_OUTPUT}")
print(f"Saved: {ANNUAL_TOTAL_BY_TECHNOLOGY_DATE_KNOWN_SUMMARY_OUTPUT}")
print(f"Saved: {RISK_D3_OUTPUT}")
