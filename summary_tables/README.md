# GIPT summary tables

Reads the monthly GIPT compilation (and the GSPT, for solar) from the GEM
Shared Drive, builds the public power-sector summary tables, and writes them to
Google Sheets with pygsheets.

## How it runs

Code lives here in GitHub; the **source data and the service-account
credentials live on the Shared Drive and are never committed**. You run it in
Google Colab: clone/pull this repo, mount Drive, load the data once, then update
each workbook independently. See [`run_summary_tables.ipynb`](run_summary_tables.ipynb).

## Layout

| Path | What it is |
|------|------------|
| `src/config.py` | The knobs you change between updates: source-file paths, credentials path, target sheet keys, category lists, year ranges. |
| `src/data.py` | `load_gipt()` — read + prepare the GIPT once per session. |
| `src/hydro.py` | Bi-national hydropower split, shared by the status tables. |
| `src/checks.py` | Light sense checks / run summaries. |
| `src/sheets.py` | pygsheets helpers *(added with the first workbook)*. |
| `src/workbooks/` | One module per Google Sheet *(added next)*. |
| `reference/` | The original notebook, kept for comparison. |

## Each monthly update

1. Point `src/config.py` at this month's GIPT and GSPT files.
2. `data = load_gipt()`, then eyeball `summarise_gipt(data)`.
3. For each workbook: `run(data, write=False)` to check the output, then
   `run(data, write=True)` to push it to the sheet.
