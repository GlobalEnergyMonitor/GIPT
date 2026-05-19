# GIPT Tripling Beta

This repository is an workspace for estimating risk-adjusted renewable power capacity additions from GEM's in-development project data.

The core question is:

> For each project currently in development, does it get delivered by 2030, and if so, in what year?

The current method uses a Monte Carlo simulation to move beyond a simple "known pipeline by stated start year" view. It creates an illustrative range of annual capacity additions from 2026 to 2030 while accounting for projects with unknown start years, development timescales, delays, cancellations, geography-specific risk adjustments, and a simple correlated delivery-risk layer.

The current setup has been developed in the context of monitoring global targets for tripling renewables, and so focuses on utility-scale solar, wind, and non-pumped hydropower in the period 2026-2030. A [test webpage for visualizing the results](https://globalenergymonitor.github.io/GIPT/tripling_beta/) is available through GitHub Pages, alongside a [diagnostics page](https://globalenergymonitor.github.io/GIPT/tripling_beta/diagnostics.html) for checking inputs, scenarios, and model outputs in more detail.

This is not a forecast of individual project delivery. It is an assumption-based modelling framework intended to show what could plausibly materialise from the current project pipeline under transparent assumptions.

⚠️ **Status:** ⚠️ this repository and methodology are under active development. The current methodology is interim and subject to change.

## What This Repository Does

The risk pipeline:

1. Reads the GIPT project-level data file.
2. Keeps relevant renewable power projects in construction, pre-construction, or announced status, including utility-scale solar, wind, and non-pumped hydropower.
3. Classifies projects into model technology groups, including splitting wind into onshore and offshore wind.
4. Applies cancellation, delay, and delivery-time assumptions.
5. Adjusts those assumptions using geography multipliers.
6. Applies a run-level global delivery shock through technology-specific cancellation and timing sensitivities.
7. Runs repeated simulations of project delivery outcomes.
8. Summarises annual additions by year, status, technology, and known/unknown start-year category.
9. Produces CSV and JSON outputs for analysis and visualisation.

The model currently focuses on:

- Utility-scale solar
- Onshore wind
- Offshore wind
- Hydropower

Pumped-storage hydropower rows are excluded before modelling because this workflow is aimed at generation capacity additions.

## Modelling Approach

Each row in the GIPT dataset represents an individual project, unit, or phase. The model handles rows differently depending on whether they have a known intended start or commissioning year.

### Projects With Known Start Years

For projects where `Start year` is known, the model:

1. Uses the stated `Start year` as the baseline delivery year.
2. Draws a cancellation outcome using the relevant cancellation probability.
3. If the project is not cancelled, samples a delay from a triangular distribution.
4. Adds the delay to the stated start year.
5. Counts the project's capacity in the adjusted delivery year if it falls between 2026 and 2030.

For example, a 500 MW offshore wind project in pre-construction with a stated start year of 2027 may be cancelled, delivered in 2027, delayed to 2028 or 2029, or pushed beyond the 2030 model window.

### Projects Without Known Start Years

For projects where `Start year` is missing, the model:

1. Draws a cancellation outcome using the relevant cancellation probability.
2. If the project is not cancelled, samples a plausible remaining time to delivery.
3. Samples an additional delay.
4. Estimates the delivery year from the current model year, currently 2026.
5. Counts the project's capacity in that year if it falls between 2026 and 2030.

For example, an undated utility-scale solar project in pre-construction may be assigned two remaining years plus one year of delay, producing an estimated delivery year of 2029.

Projects delivered after 2030 are not counted in the annual additions chart, but they are treated as delayed beyond the model window rather than necessarily cancelled.

## Inputs

The current risk pipeline is in [`risk_pipeline/make_risk_pipeline.py`](risk_pipeline/make_risk_pipeline.py). It uses four main input files.

### `risk_pipeline/Global-Integrated-Power-March-2026-II.xlsx`

This is the project-level GIPT dataset. The script currently reads the `Power facilities` sheet and expects these fields:

| Column | Purpose |
| --- | --- |
| `GEM unit/phase ID` | Unique project, unit, or phase identifier. |
| `Country/area` | Used for China-specific multipliers and diagnostics. |
| `Subregion` | Available for later aggregation or assumptions. |
| `Region` | Used for regional geography multipliers outside China. |
| `Capacity (MW)` | Capacity added if the project is delivered. |
| `Status` | Current development status: construction, pre-construction, or announced. |
| `Start year` | Intended commissioning/start year where known. Blank values are treated as unknown. |
| `Type` | Broad technology type. Current model keeps wind, utility-scale solar, and hydropower. |
| `Technology` | More detailed technology field, used to split onshore and offshore wind and exclude pumped hydro. |

### `risk_pipeline/base_assumptions.csv`

This file defines the base cancellation and timing assumptions by:

- Scenario
- Model technology
- Project status
- Whether the start year is known or unknown

The current model has three scenarios, `low`, `central`, and `high`, and four technology groups:

- `utility-scale solar`
- `onshore wind`
- `offshore wind`
- `hydropower`

The central scenario carries the main working assumptions. The low and high scenarios are first-pass directional variants and should be reviewed before being treated as final scenario definitions.

Wind rows are classified using the `Technology` field. If `Type` is wind and `Technology` contains `off`, the project is treated as offshore wind. Other wind rows are treated as onshore wind.

| Column | Purpose |
| --- | --- |
| `scenario` | Scenario name. Current values: `low`, `central`, and `high`. |
| `technology` | Model technology category. |
| `status` | Project status. |
| `date_known` | `known` or `unknown`, based on whether `Start year` exists. |
| `cancel_prob` | Probability that the project is cancelled. |
| `delay_min` | Minimum additional delay in years. |
| `delay_mode` | Most likely additional delay in years. |
| `delay_max` | Maximum additional delay in years. |
| `undated_remaining_min` | Minimum remaining years to delivery for undated projects. |
| `undated_remaining_mode` | Most likely remaining years to delivery for undated projects. |
| `undated_remaining_max` | Maximum remaining years to delivery for undated projects. |

Timing assumptions use triangular distributions because they are transparent and easy to review: minimum, most likely, and maximum.

### `risk_pipeline/geography_multipliers.csv`

This file adjusts the base assumptions for specific geographies and technologies.

The current approach uses:

- A specific geography key for China.
- GEM `Region` values for all other countries/areas.

| Column | Purpose |
| --- | --- |
| `scenario` | Scenario name, allowing geography multipliers to vary across low, central, and high cases. |
| `geography_key` | `China` or a GEM region such as Africa, Americas, Asia, Europe, or Oceania. |
| `technology` | Model technology category. |
| `cancel_multiplier` | Multiplier applied to base cancellation probability. |
| `delay_multiplier` | Multiplier applied to delay assumptions. |
| `remaining_time_multiplier` | Multiplier applied to remaining-time assumptions for undated projects. |

The final assumptions are calculated as:

- Final cancellation probability = base cancellation probability x geography cancellation multiplier
- Final delay assumptions = base delay assumptions x geography delay multiplier
- Final remaining-time assumptions = base remaining-time assumptions x geography remaining-time multiplier

This keeps the assumptions table manageable while still allowing geography-specific treatment.

### `risk_pipeline/correlated_risk_assumptions.csv`

This file adds a simple correlated delivery-risk layer. The idea is that projects are not fully independent: a bad global delivery environment can affect many projects at once, while different technologies may be more or less sensitive to that shared shock.

For each Monte Carlo run, the model draws one global delivery shock per scenario. That shock is then applied through technology-specific sensitivities:

- `cancel_sensitivity` controls how strongly the shock changes cancellation probabilities.
- `timing_sensitivity` controls how strongly the shock changes delay and remaining-time assumptions.
- `global_shock_std`, `shock_min`, and `shock_max` control the spread and bounds of the run-level shock.

Positive shocks represent worse delivery conditions, raising cancellation probabilities and lengthening timing assumptions. Negative shocks represent better delivery conditions. This means the uncertainty range now includes both project-level randomness and a first-pass representation of correlated delivery risk.

## Simulation Method

The current configuration is:

| Setting | Current value |
| --- | --- |
| Scenarios | `low`, `central`, `high` |
| Runs | `1000` |
| Random seed | `42` |
| Current model year | `2026` |
| Model window | `2026-2030` |

For each simulation run, the script first draws a global delivery-environment shock for each scenario. The shock is drawn from a normal distribution centred on zero, then clipped to the configured minimum and maximum. Cancellation probabilities are adjusted by each technology's `cancel_sensitivity`, while delay and remaining-time assumptions are adjusted by each technology's `timing_sensitivity`.

The script then draws cancellation and timing outcomes for every project. In this context, a "draw" means using the seeded random number generator to produce one possible outcome from the assumptions table.

`Cancellation` is modelled as a binary outcome. For each project, the script generates a random number between 0 and 1. If that number is less than the project's final cancellation probability, the project is treated as cancelled in that run. Otherwise, it remains eligible for delivery.

`Delays` and `remaining time to delivery` are sampled from triangular distributions. A triangular distribution is defined by three values: a minimum, a most likely value, and a maximum. The random sample is weighted toward the most likely value, so values near the mode are more likely than values near the minimum or maximum. This is different from choosing any value in the range with equal probability. For known-date projects, the sampled delay is added to the stated `Start year`. For unknown-date projects, the model samples both a remaining time to delivery and an additional delay, then adds these to the current model year.

After these run-level and project-level outcomes are drawn, the script aggregates delivered capacity by year, status, technology, and known/unknown start-year category.

The simulation is vectorised with NumPy so that the run loop operates over simulations rather than over individual projects. This keeps the model fast enough for repeated testing on a large project-level dataset.

## Outputs

The pipeline writes outputs into `risk_pipeline/`.

| Output | Description |
| --- | --- |
| `prepared_project_risk_inputs.csv` | Project-level modelling table after cleaning, technology classification, assumption matching, geography multiplier application, and correlated-risk matching. Useful for checking inputs before simulation. |
| `simulated_annual_additions_by_run.csv` | Raw Monte Carlo annual additions by scenario, run, year, status, technology, and known/unknown start-year category. |
| `simulated_annual_additions_by_status_summary.csv` | Summary by scenario, year, status, and technology, including mean, P10, P25, P50, P75, and P90. |
| `simulated_annual_additions_by_status_date_known_summary.csv` | Same as above, but retaining the known/unknown start-year split. |
| `simulated_annual_additions_total_summary.csv` | Total annual additions across all statuses and technologies, including mean, P10, P25, P50, P75, and P90. |
| `simulated_annual_additions_total_by_technology_summary.csv` | Annual totals by technology across all statuses. |
| `simulated_annual_additions_total_by_technology_date_known_summary.csv` | Annual totals by technology with the known/unknown start-year split retained. |
| `simulated_2026_2030_additions_by_status_summary.csv` | Cumulative 2026-2030 additions by scenario, status, and technology, used for the development-pipeline chart and diagnostics. |
| `simulated_2026_2030_additions_by_status_date_known_summary.csv` | Same cumulative 2026-2030 view, retaining the known/unknown start-year split. |
| `simulated_2026_2030_additions_total_by_technology_summary.csv` | Cumulative 2026-2030 additions by scenario and technology. |
| `risk_adjusted_tripling_d3_data.json` | Risk-adjusted summary of P50 additions over 2026-2030, retained for the current visualisation workflow. |

The root-level files `index.html`, `style.css`, `tripling-d3.js`, and `tripling-d3-data.json` support the public visualisation prototype, which currently presents the central scenario. The diagnostics files `diagnostics.html`, `diagnostics.css`, and `diagnostics.js` provide a separate GitHub Pages view for comparing scenarios, checking read-only input tables, and inspecting percentile ranges.

## How To Run

From the repository root:

```powershell
python risk_pipeline/make_risk_pipeline.py
```

The script expects the project workbook and assumption CSVs to be in `risk_pipeline/`. It requires Python packages used in the script, including `pandas`, `numpy`, and an Excel reader such as `openpyxl`.

Before using outputs, check the console diagnostics, `prepared_project_risk_inputs.csv`, and the diagnostics page for unmatched assumptions, unmatched geography multipliers, missing capacity values, or unexpected technology/status splits.

## Interpreting Results

The model outputs are best read as a distribution of plausible delivery outcomes under the current assumptions:

- `mean_mw` is the average simulated capacity across runs.
- `p10_mw`, `p25_mw`, `p50_mw`, `p75_mw`, and `p90_mw` describe the spread of outcomes across runs.
- Capacity is reported in MW in the CSV outputs.
- Projects outside the 2026-2030 delivery window are not included in annual additions for that chart window.

The outputs should be used to compare broad pipeline delivery pathways, not to make claims about whether a specific project will or will not be built.

## Critiques / Where The Model Is Weak

The current model relies on broad assumption buckets. Specifically, projects are grouped by technology, status, and whether they have a known start year, which captures the main drivers of delivery timing but treats very different projects within each bucket as if they have similar delivery risk.

The model accounts for typical development timelines by technology and status, but it does not yet account for how long an individual project has already remained in that status. As a result, newly announced undated projects and older stale undated projects get the same cancellation probability and the same remaining-time distribution if they share the same technology/status/date-known category.

The geography layer needs further refinement to dial in country/region-specific multipliers, as delivery risk varies due to many factors: market structure, grid constraints, permitting, policy environment, and financing conditions.

The model now partly captures correlated risk using a global delivery shock in each Monte Carlo run, with technology-specific sensitivities for cancellation and timing. This is still simplified: it does not yet distinguish between different kinds of shocks, such as global financing conditions, regional grid bottlenecks, country-specific policy disruption, or technology-specific supply-chain constraints. Probably it never can. But just to note that this will always be a crude assumption.

## Possible Modelling Extensions

- Refine how the low, central, and high delivery scenarios are presented and explained.
- Add project age/staleness-specific assumptions based on how long a project has been in its current status, assuming this can be determined from past tracker editions.
- Add country or market-level delivery multipliers beyond the current broad geography approach.
- Add annual build-rate constraints or cross checks so simulated additions do not exceed plausible deployment capacity.
- Calibrate assumptions against older GEM snapshots to see how projects historically moved from announced/pre-construction/construction to operating or cancelled.
- Extend the correlated-risk layer with regional, country, or technology-region shocks rather than one global delivery shock.
- Consider treatment of project size, since very large projects may face different delay/cancellation risk.
- Consider developer tracker record, for example brand new offshore with company vs. Orsted that already has offshore wind profile.
- Consider screening/cancellation multiplier for clustered/co-located projects.
- Consider a status-transition model that simulates movement from announced to pre-construction to construction to operating or cancelled, rather than one-shot estimate of delivery.

## Repository Map

| Path | Purpose |
| --- | --- |
| `risk_pipeline/make_risk_pipeline.py` | Main risk-adjusted additions pipeline. |
| `risk_pipeline/base_assumptions.csv` | Base cancellation, delay, and delivery-time assumptions by scenario. |
| `risk_pipeline/geography_multipliers.csv` | Scenario-specific geography and technology multipliers applied to base assumptions. |
| `risk_pipeline/correlated_risk_assumptions.csv` | Scenario and technology sensitivities for the run-level global delivery shock. |
| `risk_pipeline/*.csv` | Prepared inputs and simulation outputs. |
| `risk_pipeline/risk_adjusted_tripling_d3_data.json` | Risk-adjusted data prepared for the visualisation workflow. |
| `index.html`, `style.css`, `tripling-d3.js` | Public visualisation prototype. |
| `diagnostics.html`, `diagnostics.css`, `diagnostics.js` | Diagnostics page for reviewing assumptions, scenarios, and percentile outputs. |
| `tripling-d3-data.json` | Root-level data used by the visualisation prototype. |
