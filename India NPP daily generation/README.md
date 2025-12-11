# India Daily Generation Data (NPP → GIPT Integration)

> ⚠️ **Note:** This repository is under active development.  
> Contents may change and some components are incomplete.

## Overview

This repository provides **daily generation data** for over 700 of India’s grid-connected **coal, lignite, large-scale hydropower, nuclear, and oil/gas generators**.

The primary data source is India’s **National Power Portal (NPP)**, which publishes daily generation reports:  
🔗 https://npp.gov.in/

Where necessary, files have been digitized and standardized into a consistent tabular format to ensure **machine readability**.

A **crosswalk** field is added to match individual generating units in the NPP dataset to Global Energy Monitor’s **Global Integrated Power Tracker (GIPT)**. This enables richer analysis using additional GIPT attributes such as unit location, commissioning year, and other metadata.

The archive spans **September 2017 to present**.

To verify that this unit level data is representative and complete, a comparison is made in the [.ipynb file](GIPT/India NPP daily generation/Analyze NPP.ipynb) against a separate data source for daily grid-connected generation (from the CEA, via https://robbieandrew.github.io/india/). The near perfect correspondence between the daily unit-level generation, summed across all units, and this a separate data source for aggregate generation across India is encouraging. It shows that GEM has near perfect coverage of grid-connected generating units. And that the sum of the unit level generation data compiled here is complete.

---

## Repository Structure

### `raw NPP data/`
Contains the original files downloaded from NPP:
- **PDF files** for *September 2017 – April 2018*
- **XLS files** from *May 2018 onward*

### `parsed NPP data/`
Contains standardized .csv files of the daily generation data.

### `npp_daily_generation.parquet`
The compiled daily **unit-level** generation dataset.  
> ⚠️ **Parquet file:** for space efficiency, as ~3.5 million rows is not feasible for a .csv (~500Mb)

### `npp_daily_generation.txt`
Metadata and field descriptions for `npp_daily_generation.parquet`.

### `NPP_GIPT_crosswalk.csv`
Mapping between **NPP unit names** and **GEM power facility names**.

### `CEA_DGR_data_11.12.25.csv`
Separate data source for daily grid-connected generation for all-India (from the CEA, via https://robbieandrew.github.io/india/)

### `Analyze NPP.ipynb` (Jupyter Notebook)
A walkthrough demonstrating:
- Loading `npp_daily_generation.parquet` into a pandas DataFrame  
- Merging with the GEM–GIPT crosswalk  
- Performing sanity checks by comparing against aggregate national generation  

---

## Known Data Gaps

Data is missing from the NPP archive (likely due to archiving issues) for the following dates:
- 22/09/2017
- 01/10/2017
- 02/10/2017
- 19/03/2020 to 31/05/2020

These records are not available from the source and therefore absent from the compiled dataset.

## To Do List

- [ ] add npp_daily_generation.txt metadata description
- [ ] Further manual checking of crosswalk
- [ ] Demonstrate use of GIPT crosswalk for data analysis, e.g., stratify plant capacity factor by unit age
- [ ] Add additional data fields available in daily files. Requires sorting out the datetime info for plants coming off/online
- [ ] Gas/diesel plant coverage/GEM matching still patchy, do we care?, it's a minor fuel, add this later
- [ ] Add method for handling ongoing updates
- [ ] Further sense checking: Monthly plant capacity factor data is also available from NPP. Check if this data corresponds with the daily files

