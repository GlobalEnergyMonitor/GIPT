# China NEA Solar PV Data

This folder contains a working pipeline for collecting, cleaning, checking, and visualizing provincial solar PV capacity data for China.

The core source is the National Energy Administration (NEA) provincial solar PV [table](nea_provincial_pv_source_pages_structured_2016_2025.csv) series. The workflow also uses selected supporting sources where needed to fill or cross-check historical gaps, such as [China Energy Portal for 2018 H1 data](https://chinaenergyportal.org/en/2018-q12-pv-installations-utility-and-distributed-by-province/).

## Main Workflow

- `process.py` scrapes NEA source pages, downloads and stitches table images, extracts tables with OCR/OpenAI Vision or inline HTML parsing, cleans province-level values, and writes review files.
- `compare_nea_solar_detail.py` compares cleaned scraped outputs against the existing reference dataset, builds cross-check reports, and compiles the cleaned data into a wide format.
- `beta page/` contains a beta visualization page for exploring provincial PV capacity by period, province, and installation type.

## Key Outputs

The most important compiled output is:

`RA crosscheck/scraped_wide.csv`

This is the wide-format dataset used by the beta visualization page. Rows are area/category pairs, and period columns are formatted as `YYYYMM`.

Other useful outputs include:

- `clean_csv/`: cleaned per-source-page CSV files.
- `review_workbooks/`: Excel workbooks for manual review of each extraction.
- `logs/run_summary.csv`: status log for batch extraction runs.
- `RA crosscheck/nea_solar_detail_crosscheck.xlsx`: comparison workbook for checking scraped data against the reference file.

## Beta Visualization

The `beta page/` folder contains a beta visualization webpage intended to be hosted publicly with GitHub Pages. It loads `scraped_wide.csv` and renders summary stats, narrative bullets, charts, and a schematic province map of solar PV capacity and installation type.
