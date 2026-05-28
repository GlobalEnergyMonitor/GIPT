# China NEA Solar PV Data

This folder contains a working pipeline for collecting, cleaning, checking, and visualizing provincial solar PV capacity data for China.

The core source is the National Energy Administration (NEA) provincial solar PV [table](nea_provincial_pv_source_pages_structured_2016_2026.csv) series. The workflow also uses selected supporting sources where needed to fill or cross-check historical gaps, such as [China Energy Portal for 2018 H1 data](https://chinaenergyportal.org/en/2018-q12-pv-installations-utility-and-distributed-by-province/).

## Main Workflow

- `process.py` scrapes NEA source pages, downloads and stitches table images, extracts tables with OCR/OpenAI Vision or inline HTML parsing, cleans province-level values, and writes review files.
- `compare_nea_solar_detail.py` compares cleaned scraped outputs against the existing reference dataset, builds cross-check reports, and compiles the cleaned data into a wide format.
- `public/` contains the static files deployed to GitHub Pages, including the beta visualization page.

## Key Outputs

Generated pipeline artifacts are grouped under `outputs/` to keep the project root tidy.

The most important compiled output is:

`outputs/RA crosscheck/scraped_wide.csv`

This is the wide-format dataset used by the beta visualization page. Rows are area/category pairs, and period columns are formatted as `YYYYMM`.

Other useful outputs include:

- `outputs/clean_csv/`: cleaned per-source-page CSV files.
- `outputs/review_workbooks/`: Excel workbooks for manual review of each extraction.
- `outputs/logs/run_summary.csv`: status log for batch extraction runs.
- `outputs/RA crosscheck/nea_solar_detail_crosscheck.xlsx`: comparison workbook for checking scraped data against the reference file.
- `public/data/scraped_wide.csv`: deployable copy of the wide dataset used by the GitHub Pages site.

## Beta Visualization

The `public/beta/` folder contains the deployed beta visualization webpage and is the source of truth for webpage edits. It loads `public/data/scraped_wide.csv` and renders summary stats, narrative bullets, charts, and a schematic province map of solar PV capacity and installation type.

## GitHub Pages

This repo is set up to deploy the `China NEA/public/` folder with a GitHub Actions workflow at the repository root. On a public repository, this works with regular GitHub Free.

After pushing to `main`, enable Pages in GitHub:

1. Go to `Settings -> Pages`.
2. Set `Build and deployment` source to `GitHub Actions`.
3. Run or wait for the `Deploy Pages` workflow.

The beta page will be available at:

`https://<your-username>.github.io/<repo-name>/beta/`

Additional pages can sit beside it under `public/`, for example `public/another-page/` would deploy to `/another-page/`.
