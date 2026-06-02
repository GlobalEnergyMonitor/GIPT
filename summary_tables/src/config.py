"""Central configuration — the things you change between monthly updates.

Kept in one place so values can't drift between modules. Tab names and per-tab
anchor cells are *not* here: they live in each workbook module, because they
vary with each sheet's layout.
"""

# --- Source files on the GEM Shared Drive (update these each month) ----------
# The monthly GIPT public-release compilation.
GIPT_FILE = "/content/drive/Shareddrives/GEM Shared Drive/Programs/Special and Multi-Program Projects/Global Integrated Power Tracker/GIPT public release files/Global Integrated Power March 2026 II.xlsx"

# The GSPT export, needed for the solar DC->AC harmonisation. Update when GSPT updates.
GSPT_FILE = "/content/drive/Shareddrives/GEM Shared Drive/Programs/Renewables & Other Power Program/Shared Wind and Solar Folder/Previous Updates/Wind and Solar Update v4b H2 2025/(Feb 2026) Launch Documents/Download Files/Global-Solar-Power-Tracker-February-2026.xlsx"

# Service-account JSON used by pygsheets to write the sheets. Lives on the
# Shared Drive — never commit it to git.
CREDS_FILE = "/content/drive/Shareddrives/GEM Shared Drive/Programs/Special and Multi-Program Projects/Global Integrated Power Tracker/Work in Progress/GDRIVE_API_CREDENTIALS.json"

# --- Worksheet names inside the source GIPT workbook -------------------------
GIPT_FACILITIES_SHEET = "Power facilities"
GIPT_REGIONS_SHEET = "Regions, area, and countries"

# --- Target Google Sheet keys (one per summary workbook) ---------------------
# Centralised so a key can't drift between a comment and the code (the original
# notebook had exactly that bug on country_by_year).
SPREADSHEET_KEYS = {
    "region_by_tech": "1yV7GYPO_2Sx2ZMrRIJ0q2iryuZjIb4oeWJTacsuRoi4",
    "country_by_tech": "1a1s9hHB9bw-WX_RgUDseTwq6ALqu3M_4P7iMkKHxlEA",
    "tech_by_status": "1tHwx9MRi7WhyzgqR9oZD78f2vMyFpLpZ0zcxcsmT-Io",
    "region_status_by_tech": "1fHZ2h47iqyy3tywtajQXNfMH0lJ4J5znVG3OxLL2JK0",
    "country_status_by_tech": "1XS9kjfssMYFqQ7uELf90YvDidUIYpHoCxuTVvCZZjZA",
    "region_by_year": "1mKNIvxmW3wBMX-0OT-BUGX2F_KqEqsyW0D0jLCmyzAg",
    # NOTE: in the original notebook the comment and the code disagreed on one
    # character of this key ('z' vs 'n'). This is the value the code ran with.
    # Worth confirming it opens the right sheet.
    "country_by_year": "1RJXc1oU569BAUUkeviR_l-Wz6HXX6mQTbxnZb-OfSPc",
    "retirements": "186LmHcdbZQXUS3CVJvXiwCpoMpouElidqHHD0lDrRvE",
    "ownership": "1h3kUE8XNR4qMK6ULeEAlVKsPgLY04mwsKLm2p456g4Q",
}

# --- Fixed vocabularies the aggregations expect ------------------------------
# Ordered region + subregion list used as the row layout of the region tables.
REGIONS_AND_SUBREGIONS = [
    "Africa", "Northern Africa", "Sub-Saharan Africa",
    "Americas", "Latin America and the Caribbean", "Northern America",
    "Asia", "Central Asia", "Eastern Asia", "South-eastern Asia",
    "Southern Asia", "Western Asia",
    "Europe", "Eastern Europe", "Northern Europe", "Southern Europe",
    "Western Europe",
    "Oceania", "Australia and New Zealand", "Melanesia", "Micronesia",
    "Polynesia",
]

# The five top-level regions (their subregions sum to the same total). Handy for
# quick reconciliation in run summaries.
WORLD_REGIONS = ["Africa", "Americas", "Asia", "Europe", "Oceania"]

# Technology types. TYPES includes distributed solar (used by the region/country
# x technology tables); TECHS excludes it (used everywhere else).
TYPES = ["coal", "oil/gas", "utility-scale solar", "solar dist", "wind",
         "nuclear", "hydropower", "bioenergy", "geothermal"]
TECHS = ["coal", "oil/gas", "utility-scale solar", "wind",
         "nuclear", "hydropower", "bioenergy", "geothermal"]

# All project statuses we expect after the prep remaps the 'inferred' ones.
STATUSES = ["announced", "pre-permit", "permitted", "pre-construction",
            "construction", "shelved", "operating", "mothballed",
            "cancelled", "retired", "inactive"]

# --- Year ranges for the time-series tables ----------------------------------
OPERATING_YEAR_MIN = 2000
OPERATING_YEAR_MAX = 2025          # reporting through year-end 2025
RETIREMENT_YEAR_MIN = 2026
RETIREMENT_YEAR_MAX = 2050
