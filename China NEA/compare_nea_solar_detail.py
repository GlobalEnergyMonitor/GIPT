import re
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
REFERENCE_CSV = BASE_DIR / "NEA_solar_detail.csv"
OUTPUTS_DIR = BASE_DIR / "outputs"
PUBLIC_DIR = BASE_DIR / "public"
PUBLIC_DATA_DIR = PUBLIC_DIR / "data"
SCRAPED_DIR = OUTPUTS_DIR / "clean_csv"
LOGS_DIR = OUTPUTS_DIR / "logs"
REPORTS_DIR = OUTPUTS_DIR / "comparison_reports"
RA_CROSSCHECK_DIR = OUTPUTS_DIR / "RA crosscheck"
RUN_SUMMARY_CSV = LOGS_DIR / "run_summary.csv"
PAGE_SUMMARY_CSV = LOGS_DIR / "page_summary_scraped.csv"

COMPARISON_OUT = RA_CROSSCHECK_DIR / "nea_solar_detail_comparison.csv"
SUMMARY_OUT = RA_CROSSCHECK_DIR / "nea_solar_detail_comparison_summary.csv"
DUPLICATES_OUT = RA_CROSSCHECK_DIR / "nea_solar_detail_comparison_duplicates.csv"
UNMATCHED_FILES_OUT = RA_CROSSCHECK_DIR / "nea_solar_detail_unmatched_clean_files.csv"
SCRAPED_WIDE_OUT = RA_CROSSCHECK_DIR / "scraped_clean_compiled_like_NEA_solar_detail.csv"
SCRAPED_WIDE_SIMPLE_OUT = RA_CROSSCHECK_DIR / "scraped_wide.csv"
PUBLIC_SCRAPED_WIDE_OUT = PUBLIC_DATA_DIR / "scraped_wide.csv"
EXCEL_OUT = RA_CROSSCHECK_DIR / "nea_solar_detail_crosscheck.xlsx"

TOLERANCE_GW = 0.01

CHECKPOINT_MONTH = {
    "q1": "03",
    "h1": "06",
    "q3": "09",
    "annual": "12",
}

CATEGORY_TO_SCRAPED_COLUMN = {
    "Total": "cum_capacity_total_10kw",
    "Utility-scale": "cum_capacity_utility_10kw",
    "Total distributed": "cum_capacity_distributed_10kw",
    "Households": "cum_capacity_residential_10kw",
}

CATEGORY_TO_NEW_SCRAPED_COLUMN = {
    "Total": "new_capacity_total_10kw",
    "Utility-scale": "new_capacity_utility_10kw",
    "Total distributed": "new_capacity_distributed_10kw",
    "Households": "new_capacity_residential_10kw",
}

DERIVED_PERIOD_RULES = {
    "201712": "201812",
    "202012": "202103",
}

CEP_201806_URL = (
    "https://chinaenergyportal.org/en/"
    "2018-q12-pv-installations-utility-and-distributed-by-province/"
)
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

AREA_ALIASES = {
    "Xinjiang Corps": "Xinjiang Production and Construction Corps",
    "XPCC": "Xinjiang Production and Construction Corps",
}


def write_csv_safely(df, path, **kwargs):
    try:
        df.to_csv(path, **kwargs)
        return path
    except PermissionError:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fallback = path.with_name(f"{path.stem}_{timestamp}{path.suffix}")
        df.to_csv(fallback, **kwargs)
        print(f"WARNING: {path} is locked; wrote {fallback} instead.")
        return fallback


def safe_slug(s):
    s = str(s) if s is not None else "unknown"
    s = re.sub(r"[^\w\-]+", "_", s)
    return s.strip("_")


def normalize_area(s):
    if pd.isna(s):
        return pd.NA
    s = str(s).strip()
    return AREA_ALIASES.get(s, s)


PROVINCE_CN_TO_EN = {
    "总计": "Total",
    "北京": "Beijing",
    "天津": "Tianjin",
    "河北": "Hebei",
    "山西": "Shanxi",
    "内蒙古": "Inner Mongolia",
    "辽宁": "Liaoning",
    "吉林": "Jilin",
    "黑龙江": "Heilongjiang",
    "上海": "Shanghai",
    "江苏": "Jiangsu",
    "浙江": "Zhejiang",
    "安徽": "Anhui",
    "福建": "Fujian",
    "江西": "Jiangxi",
    "山东": "Shandong",
    "河南": "Henan",
    "湖北": "Hubei",
    "湖南": "Hunan",
    "广东": "Guangdong",
    "广西": "Guangxi",
    "海南": "Hainan",
    "重庆": "Chongqing",
    "四川": "Sichuan",
    "贵州": "Guizhou",
    "云南": "Yunnan",
    "西藏": "Tibet",
    "陕西": "Shaanxi",
    "甘肃": "Gansu",
    "青海": "Qinghai",
    "宁夏": "Ningxia",
    "新疆": "Xinjiang",
    "新疆自治区": "Xinjiang",
    "新疆维吾尔自治区": "Xinjiang",
    "新疆兵团": "Xinjiang Production and Construction Corps",
}


CEP_AREA_ALIASES = {
    "Total": "Total",
    "Beijing": "Beijing",
    "Tianjin": "Tianjin",
    "Hebei": "Hebei",
    "Shanxi": "Shanxi",
    "Inner Mongolia": "Inner Mongolia",
    "Liaoning": "Liaoning",
    "Jilin": "Jilin",
    "Heilongjiang": "Heilongjiang",
    "Shanghai": "Shanghai",
    "Jiangsu": "Jiangsu",
    "Zhejiang": "Zhejiang",
    "Anhui": "Anhui",
    "Fujian": "Fujian",
    "Jiangxi": "Jiangxi",
    "Shandong": "Shandong",
    "Henan": "Henan",
    "Hubei": "Hubei",
    "Hunan": "Hunan",
    "Guangdong": "Guangdong",
    "Guangxi": "Guangxi",
    "Hainan": "Hainan",
    "Chongqing": "Chongqing",
    "Sichuan": "Sichuan",
    "Guizhou": "Guizhou",
    "Yunnan": "Yunnan",
    "Tibet": "Tibet",
    "Shaanxi": "Shaanxi",
    "Gansu": "Gansu",
    "Qinghai": "Qinghai",
    "Ningxia": "Ningxia",
    "Xinjiang": "Xinjiang",
    "XPCC": "Xinjiang Production and Construction Corps",
}


def normalize_province_cn(s):
    if pd.isna(s):
        return pd.NA
    s = str(s).strip()
    s = re.sub(r"\s+", "", s)
    return s


def normalize_checkpoint(s):
    s = str(s or "").strip().lower()
    if s in {"q3", "前三季度"}:
        return "q3"
    if s in {"h1", "上半年"}:
        return "h1"
    if s in {"q1", "一季度"}:
        return "q1"
    return "annual"


def make_period(year, checkpoint):
    checkpoint = normalize_checkpoint(checkpoint)
    month = CHECKPOINT_MONTH.get(checkpoint)
    if month is None:
        raise ValueError(f"Unknown checkpoint: {checkpoint}")
    return f"{int(year)}{month}"


def checkpoint_from_period(period):
    month = str(period)[-2:]
    for checkpoint, checkpoint_month in CHECKPOINT_MONTH.items():
        if checkpoint_month == month:
            return checkpoint
    return pd.NA


def infer_metadata_from_filename(path):
    stem = path.stem
    if stem.endswith("_clean"):
        stem = stem[:-6]

    publish_date = stem[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", stem) else None
    title = stem[11:] if publish_date and len(stem) > 11 else stem

    year_match = re.search(r"(20\d{2})年", title)
    year = int(year_match.group(1)) if year_match else pd.NA

    if "前三季度" in title:
        checkpoint = "q3"
    elif "上半年" in title:
        checkpoint = "h1"
    elif "一季度" in title:
        checkpoint = "q1"
    else:
        checkpoint = "annual"

    period = make_period(year, checkpoint) if not pd.isna(year) else pd.NA
    return {
        "publish_date": publish_date,
        "title": title,
        "year": year,
        "checkpoint": checkpoint,
        "period": period,
        "source_page_url": pd.NA,
        "metadata_source": "filename",
    }


def load_reference_long():
    ref = pd.read_csv(REFERENCE_CSV)
    period_cols = [c for c in ref.columns if re.fullmatch(r"\d{6}", str(c))]

    long = ref.melt(
        id_vars=["Area", "Category"],
        value_vars=period_cols,
        var_name="period",
        value_name="reference_gw",
    )
    long["reference_gw"] = pd.to_numeric(long["reference_gw"], errors="coerce")
    long = long.dropna(subset=["reference_gw"]).copy()
    long["area_key"] = long["Area"].apply(normalize_area)
    long["category"] = long["Category"].astype(str).str.strip()
    long = long.rename(columns={"Area": "reference_area"})
    return long[["period", "area_key", "category", "reference_area", "reference_gw"]]


def reference_format_info():
    ref = pd.read_csv(REFERENCE_CSV)
    period_cols = [c for c in ref.columns if re.fullmatch(r"\d{6}", str(c))]
    area_order = ref["Area"].drop_duplicates().tolist()
    category_order = ref["Category"].drop_duplicates().tolist()

    area_label_by_key = {}
    for area in area_order:
        area_key = normalize_area(area)
        area_label_by_key.setdefault(area_key, area)

    return {
        "period_cols": period_cols,
        "area_order": area_order,
        "category_order": category_order,
        "area_label_by_key": area_label_by_key,
    }


def metadata_rows():
    if RUN_SUMMARY_CSV.exists():
        meta = pd.read_csv(RUN_SUMMARY_CSV)
        source = "run_summary"
    elif PAGE_SUMMARY_CSV.exists():
        meta = pd.read_csv(PAGE_SUMMARY_CSV)
        source = "page_summary"
    else:
        return pd.DataFrame()

    meta["checkpoint"] = meta["checkpoint"].apply(normalize_checkpoint)
    meta["period"] = [
        make_period(year, checkpoint)
        for year, checkpoint in zip(meta["year"], meta["checkpoint"])
    ]
    meta["expected_clean_name"] = [
        f"{publish_date}_{safe_slug(title)[:80]}_clean.csv"
        for publish_date, title in zip(meta["publish_date"], meta["title"])
    ]
    meta["clean_path"] = meta["expected_clean_name"].apply(lambda name: SCRAPED_DIR / name)
    meta["metadata_source"] = source
    return meta


def discover_clean_files():
    records = []
    seen_paths = set()
    unmatched = []
    meta = metadata_rows()

    if not meta.empty:
        for row in meta.itertuples(index=False):
            clean_path = Path(row.clean_path)
            if clean_path.exists():
                records.append({
                    "path": clean_path,
                    "publish_date": row.publish_date,
                    "title": row.title,
                    "year": row.year,
                    "checkpoint": row.checkpoint,
                    "period": row.period,
                    "source_page_url": getattr(row, "source_page_url", pd.NA),
                    "metadata_source": row.metadata_source,
                })
                seen_paths.add(clean_path.resolve())

    for path in sorted(SCRAPED_DIR.glob("*_clean.csv")):
        if path.resolve() in seen_paths:
            continue
        inferred = infer_metadata_from_filename(path)
        inferred["path"] = path
        records.append(inferred)
        unmatched.append({"clean_file": path.name, **inferred})

    unmatched_df = pd.DataFrame(unmatched)
    write_csv_safely(
        unmatched_df,
        UNMATCHED_FILES_OUT,
        index=False,
        encoding="utf-8-sig",
    )
    return records, unmatched_df


def append_xinjiang_including_corps(df, value_cols):
    if df.empty:
        return df

    include_key = "Xinjiang (Including Corps)"
    component_keys = {"Xinjiang", "Xinjiang Production and Construction Corps"}
    base = df[~df["area_key"].eq(include_key)].copy()
    components = base[base["area_key"].isin(component_keys)].copy()
    if components.empty:
        return df

    group_cols = ["period", "year", "checkpoint", "category"]
    derived = (
        components
        .groupby(group_cols, dropna=False)[value_cols]
        .sum(min_count=1)
        .reset_index()
    )
    derived["area_key"] = include_key
    derived["province_cn"] = "新疆（含兵团）"
    derived["province_en"] = include_key
    derived["source_page_url"] = "derived: Xinjiang + Xinjiang Corps"
    derived["source_file"] = "derived_xinjiang_including_corps"

    ordered_cols = [c for c in df.columns if c in derived.columns]
    derived = derived[ordered_cols]
    return pd.concat([base, derived], ignore_index=True, sort=False)


def append_derived_periods_from_additions(scraped, additions):
    if scraped.empty or additions.empty:
        return scraped

    derived_parts = []
    for target_period, source_period in DERIVED_PERIOD_RULES.items():
        source_cumulative = scraped[scraped["period"].astype(str).eq(source_period)].copy()
        source_additions = additions[additions["period"].astype(str).eq(source_period)].copy()
        if source_cumulative.empty or source_additions.empty:
            continue

        merged = source_cumulative.merge(
            source_additions[
                ["area_key", "category", "scraped_addition_10kw", "scraped_addition_gw"]
            ],
            on=["area_key", "category"],
            how="inner",
        )
        merged = merged.dropna(subset=["scraped_10kw", "scraped_addition_10kw"]).copy()
        if merged.empty:
            continue

        merged["period"] = target_period
        merged["year"] = int(str(target_period)[:4])
        merged["checkpoint"] = checkpoint_from_period(target_period)
        merged["scraped_10kw"] = merged["scraped_10kw"] - merged["scraped_addition_10kw"]
        merged["scraped_gw"] = merged["scraped_10kw"] / 100
        merged["source_page_url"] = f"derived: {source_period} cumulative - {source_period} additions"
        merged["source_file"] = f"derived_{target_period}_from_{source_period}"
        derived_parts.append(merged[scraped.columns])

    if not derived_parts:
        return scraped

    derived = pd.concat(derived_parts, ignore_index=True)
    key_cols = ["period", "area_key", "category"]
    derived_keys = derived[key_cols].drop_duplicates()
    scraped_without_replaced = scraped.merge(
        derived_keys.assign(_replace=True),
        on=key_cols,
        how="left",
    )
    scraped_without_replaced = scraped_without_replaced[
        scraped_without_replaced["_replace"].isna()
    ].drop(columns=["_replace"])

    return pd.concat([scraped_without_replaced, derived], ignore_index=True, sort=False)


def clean_numeric_series(series):
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.replace(r"[^\d\.\-]", "", regex=True),
        errors="coerce",
    )


def find_cep_201806_table():
    response = requests.get(CEP_201806_URL, headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    for html_table in soup.find_all("table"):
        rows = []
        for tr in html_table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["th", "td"])]
            if cells:
                rows.append(cells)
        if not rows:
            continue

        width = max(len(row) for row in rows)
        padded = [row + [""] * (width - len(row)) for row in rows]
        table = pd.DataFrame(padded)
        valid_areas = set(CEP_AREA_ALIASES) | set(PROVINCE_CN_TO_EN)
        body = table[
            table.iloc[:, 0].astype(str).str.strip().isin(valid_areas)
        ].copy()
        if body.shape[0] >= 30 and body.shape[1] >= 5:
            return body.iloc[:, :5].reset_index(drop=True)

    raise ValueError(f"Could not find 201806 capacity table at {CEP_201806_URL}")


def normalize_cep_201806_columns(table):
    table = table.copy()
    out = pd.DataFrame({
        "area_raw": table.iloc[:, 0].astype(str).str.strip(),
        "cum_total_mw": clean_numeric_series(table.iloc[:, 1]),
        "cum_utility_mw": clean_numeric_series(table.iloc[:, 2]),
        "new_total_mw": clean_numeric_series(table.iloc[:, 3]),
        "new_utility_mw": clean_numeric_series(table.iloc[:, 4]),
    })
    out = out.dropna(subset=["cum_total_mw", "cum_utility_mw"], how="all").copy()
    out = out[out["area_raw"].notna() & ~out["area_raw"].str.lower().isin({"nan", ""})].copy()
    out["area_key"] = out["area_raw"].map(CEP_AREA_ALIASES)
    out["area_key"] = out["area_key"].fillna(out["area_raw"].map(PROVINCE_CN_TO_EN))
    out["province_cn"] = out["area_raw"]

    missing = sorted(out.loc[out["area_key"].isna(), "area_raw"].dropna().unique())
    if missing:
        raise ValueError(f"Unmapped 201806 China Energy Portal areas: {missing}")

    out["cum_distributed_mw"] = out["cum_total_mw"] - out["cum_utility_mw"]
    return out


def load_cep_201806_long():
    table = normalize_cep_201806_columns(find_cep_201806_table())
    records = []
    category_to_mw_col = {
        "Total": "cum_total_mw",
        "Utility-scale": "cum_utility_mw",
        "Total distributed": "cum_distributed_mw",
    }

    for category, mw_col in category_to_mw_col.items():
        part = table[["province_cn", "area_key", mw_col]].copy()
        part = part.rename(columns={mw_col: "mw"})
        part = part.dropna(subset=["mw"]).copy()
        part["period"] = "201806"
        part["year"] = 2018
        part["checkpoint"] = "h1"
        part["province_en"] = part["area_key"]
        part["category"] = category
        part["scraped_10kw"] = part["mw"] * 100
        part["scraped_gw"] = part["mw"] / 1000
        part["source_page_url"] = CEP_201806_URL
        part["source_file"] = "china_energy_portal_201806"
        records.append(part.drop(columns=["mw"]))

    return pd.concat(records, ignore_index=True)


def replace_period_rows(df, replacement, period):
    df = df[~df["period"].astype(str).eq(str(period))].copy()
    return pd.concat([df, replacement[df.columns]], ignore_index=True, sort=False)


def load_scraped_long():
    records = []
    addition_records = []
    files, unmatched = discover_clean_files()

    for item in files:
        path = Path(item["path"])
        df = pd.read_csv(path)

        missing_cols = [
            c for c in [
                "province_cn",
                "province_en",
                *CATEGORY_TO_SCRAPED_COLUMN.values(),
                *CATEGORY_TO_NEW_SCRAPED_COLUMN.values(),
            ]
            if c not in df.columns
        ]
        if missing_cols:
            raise ValueError(f"{path.name} is missing columns: {missing_cols}")

        for category, value_col in CATEGORY_TO_SCRAPED_COLUMN.items():
            part = df[["province_cn", "province_en", value_col]].copy()
            part = part.rename(columns={value_col: "scraped_10kw"})
            part["scraped_10kw"] = pd.to_numeric(part["scraped_10kw"], errors="coerce")
            part = part.dropna(subset=["scraped_10kw"]).copy()
            part["scraped_gw"] = part["scraped_10kw"] / 100
            part["category"] = category
            part["period"] = item["period"]
            part["year"] = item["year"]
            part["checkpoint"] = item["checkpoint"]
            part["source_page_url"] = item["source_page_url"]
            part["source_file"] = path.name
            part["area_key"] = part["province_en"].apply(normalize_area)
            records.append(part)

        for category, value_col in CATEGORY_TO_NEW_SCRAPED_COLUMN.items():
            part = df[["province_cn", "province_en", value_col]].copy()
            part = part.rename(columns={value_col: "scraped_addition_10kw"})
            part["scraped_addition_10kw"] = pd.to_numeric(
                part["scraped_addition_10kw"],
                errors="coerce",
            )
            part = part.dropna(subset=["scraped_addition_10kw"]).copy()
            part["scraped_addition_gw"] = part["scraped_addition_10kw"] / 100
            part["category"] = category
            part["period"] = item["period"]
            part["year"] = item["year"]
            part["checkpoint"] = item["checkpoint"]
            part["source_page_url"] = item["source_page_url"]
            part["source_file"] = path.name
            part["area_key"] = part["province_en"].apply(normalize_area)
            addition_records.append(part)

    if not records:
        return pd.DataFrame(), unmatched

    scraped = pd.concat(records, ignore_index=True)
    cols = [
        "period",
        "year",
        "checkpoint",
        "area_key",
        "province_cn",
        "province_en",
        "category",
        "scraped_10kw",
        "scraped_gw",
        "source_page_url",
        "source_file",
    ]
    scraped = scraped[cols]
    scraped = replace_period_rows(scraped, load_cep_201806_long(), "201806")
    scraped = append_xinjiang_including_corps(scraped, ["scraped_10kw", "scraped_gw"])

    if addition_records:
        additions = pd.concat(addition_records, ignore_index=True)
        additions = append_xinjiang_including_corps(
            additions,
            ["scraped_addition_10kw", "scraped_addition_gw"],
        )
        scraped = append_derived_periods_from_additions(scraped, additions)

    return scraped[cols], unmatched


def add_status(df):
    both = df["reference_gw"].notna() & df["scraped_gw"].notna()
    df["diff_gw"] = df["scraped_gw"] - df["reference_gw"]
    df["diff_10kw"] = df["diff_gw"] * 100
    df["abs_diff_gw"] = df["diff_gw"].abs()

    df["comparison_status"] = np.select(
        [
            both & (df["abs_diff_gw"] <= TOLERANCE_GW),
            both & (df["abs_diff_gw"] > TOLERANCE_GW),
            df["reference_gw"].notna() & df["scraped_gw"].isna(),
            df["reference_gw"].isna() & df["scraped_gw"].notna(),
        ],
        ["match", "different", "missing_scraped", "missing_reference"],
        default="unknown",
    )
    return df


def write_duplicate_report(scraped, reference):
    scraped_dupes = scraped[
        scraped.duplicated(["period", "area_key", "category"], keep=False)
    ].copy()
    scraped_dupes["dataset"] = "scraped"

    reference_dupes = reference[
        reference.duplicated(["period", "area_key", "category"], keep=False)
    ].copy()
    reference_dupes["dataset"] = "reference"

    duplicates = pd.concat([scraped_dupes, reference_dupes], ignore_index=True, sort=False)
    out_path = write_csv_safely(
        duplicates,
        DUPLICATES_OUT,
        index=False,
        encoding="utf-8-sig",
    )
    return duplicates, out_path


def build_scraped_wide(scraped):
    fmt = reference_format_info()
    period_cols = fmt["period_cols"]
    category_order = fmt["category_order"]
    area_label_by_key = fmt["area_label_by_key"]

    wide_source = scraped.drop_duplicates(["period", "area_key", "category"], keep="first").copy()
    wide_source["Area"] = [
        area_label_by_key.get(area_key, province_en)
        for area_key, province_en in zip(wide_source["area_key"], wide_source["province_en"])
    ]
    wide_source["Category"] = wide_source["category"]

    wide = wide_source.pivot_table(
        index=["Area", "Category"],
        columns="period",
        values="scraped_gw",
        aggfunc="first",
    ).reset_index()
    wide.columns.name = None

    scraped_period_cols = [c for c in wide.columns if re.fullmatch(r"\d{6}", str(c))]
    all_period_cols = period_cols + sorted(set(scraped_period_cols) - set(period_cols))
    for col in all_period_cols:
        if col not in wide.columns:
            wide[col] = pd.NA

    area_order = {
        area: idx
        for idx, area in enumerate(fmt["area_order"])
    }
    category_order_map = {
        category: idx
        for idx, category in enumerate(category_order)
    }
    wide["_area_order"] = wide["Area"].map(area_order).fillna(len(area_order))
    wide["_category_order"] = wide["Category"].map(category_order_map).fillna(len(category_order_map))
    wide = wide.sort_values(["_area_order", "Area", "_category_order", "Category"])

    wide = wide[["Area", "Category", *all_period_cols]]
    wide = wide.rename(columns={col: int(col) for col in all_period_cols})
    return wide


def autosize_excel_columns(writer):
    for worksheet in writer.sheets.values():
        for column_cells in worksheet.columns:
            values = [cell.value for cell in column_cells]
            max_len = max(len(str(value)) if value is not None else 0 for value in values)
            width = min(max(max_len + 2, 10), 45)
            worksheet.column_dimensions[column_cells[0].column_letter].width = width


def write_excel_report(comparison, summary, duplicates, unmatched, scraped_wide):
    different = comparison[comparison["comparison_status"].eq("different")].copy()
    missing_scraped = comparison[comparison["comparison_status"].eq("missing_scraped")].copy()
    missing_reference = comparison[comparison["comparison_status"].eq("missing_reference")].copy()

    out_path = EXCEL_OUT
    try:
        writer = pd.ExcelWriter(out_path, engine="openpyxl")
    except PermissionError:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = EXCEL_OUT.with_name(f"{EXCEL_OUT.stem}_{timestamp}{EXCEL_OUT.suffix}")
        print(f"WARNING: {EXCEL_OUT} is locked; wrote {out_path} instead.")
        writer = pd.ExcelWriter(out_path, engine="openpyxl")

    with writer:
        summary.to_excel(writer, sheet_name="summary", index=False)
        scraped_wide.to_excel(writer, sheet_name="scraped_wide", index=False)
        different.to_excel(writer, sheet_name="differences", index=False)
        missing_scraped.to_excel(writer, sheet_name="missing_scraped", index=False)
        missing_reference.to_excel(writer, sheet_name="missing_reference", index=False)
        duplicates.to_excel(writer, sheet_name="duplicates", index=False)
        unmatched.to_excel(writer, sheet_name="unmatched_files", index=False)
        comparison.to_excel(writer, sheet_name="all_comparisons", index=False)
        autosize_excel_columns(writer)

    return out_path


def main():
    RA_CROSSCHECK_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    reference = load_reference_long()
    scraped, unmatched = load_scraped_long()
    if scraped.empty:
        raise ValueError(f"No scraped clean CSV rows found in {SCRAPED_DIR}")

    duplicates, duplicates_out = write_duplicate_report(scraped, reference)
    scraped_wide = build_scraped_wide(scraped)
    scraped_wide_out = write_csv_safely(
        scraped_wide,
        SCRAPED_WIDE_OUT,
        index=False,
        encoding="utf-8-sig",
        float_format="%.6f",
    )
    scraped_wide_simple_out = write_csv_safely(
        scraped_wide,
        SCRAPED_WIDE_SIMPLE_OUT,
        index=False,
        encoding="utf-8-sig",
        float_format="%.6f",
    )
    public_scraped_wide_out = write_csv_safely(
        scraped_wide,
        PUBLIC_SCRAPED_WIDE_OUT,
        index=False,
        encoding="utf-8-sig",
        float_format="%.6f",
    )

    scraped_for_merge = scraped.drop_duplicates(["period", "area_key", "category"], keep="first")
    reference_for_merge = reference.drop_duplicates(["period", "area_key", "category"], keep="first")

    comparison = scraped_for_merge.merge(
        reference_for_merge,
        on=["period", "area_key", "category"],
        how="outer",
    )
    comparison = add_status(comparison)

    sort_cols = ["period", "comparison_status", "area_key", "category"]
    comparison = comparison.sort_values(sort_cols, na_position="last")
    comparison_out = write_csv_safely(
        comparison,
        COMPARISON_OUT,
        index=False,
        encoding="utf-8-sig",
    )

    summary = (
        comparison
        .groupby(["period", "comparison_status"], dropna=False)
        .agg(
            n_rows=("comparison_status", "size"),
            max_abs_diff_gw=("abs_diff_gw", "max"),
            mean_abs_diff_gw=("abs_diff_gw", "mean"),
        )
        .reset_index()
        .sort_values(["period", "comparison_status"])
    )
    summary_out = write_csv_safely(
        summary,
        SUMMARY_OUT,
        index=False,
        encoding="utf-8-sig",
    )
    excel_out = write_excel_report(comparison, summary, duplicates, unmatched, scraped_wide)

    print(f"Scraped rows compared: {len(scraped):,}")
    print(f"Reference rows compared: {len(reference):,}")
    print(f"Comparison written: {comparison_out}")
    print(f"Summary written: {summary_out}")
    print(f"Duplicates report written: {duplicates_out}")
    print(f"Unmatched clean-file report written: {UNMATCHED_FILES_OUT}")
    print(f"Scraped wide file written: {scraped_wide_out}")
    print(f"Scraped wide simple file written: {scraped_wide_simple_out}")
    print(f"Public scraped wide file written: {public_scraped_wide_out}")
    print(f"Excel workbook written: {excel_out}")
    print()
    print(summary.to_string(index=False))

    top_diffs = comparison[comparison["comparison_status"].eq("different")].copy()
    top_diffs = top_diffs.sort_values("abs_diff_gw", ascending=False).head(25)
    if not top_diffs.empty:
        print()
        print("Largest differences:")
        cols = [
            "period",
            "area_key",
            "category",
            "scraped_gw",
            "reference_gw",
            "diff_gw",
            "source_file",
        ]
        print(top_diffs[cols].to_string(index=False))

main()
