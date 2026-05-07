
####
'''
This notebook is a prototype pipeline for extracting provincial solar PV tables from NEA source pages.

The workflow has four main parts.
First, we scrape each NEA article page to capture basic metadata and the image URLs that contain the table.
Second, we download and stitch those images so each source page becomes one OCR-ready table image, even when the table was split across multiple images on the website.
Third, we run table OCR on that stitched image to get a raw machine-readable table.
Finally, we do a light cleaning and review pass: impose the expected schema, translate province names, convert OCR’d numeric text into numbers, and write out a review workbook that makes it easy to manually cross-check the results.

The blocks are split up on purpose. A new user should be able to run them one by one, inspect the outputs at each stage, and stop wherever something looks off. That matters here because NEA tables are similar but not perfectly identical across years and checkpoints, so debugging is easier when scraping, stitching, OCR, and cleaning are all visible as separate steps.

What the steps do:

Steps 1–2 set up the environment: imports, file paths, URLs, fixed schema, province translation map, and helper functions. This is the shared machinery the rest of the notebook relies on.

Step 3 scrapes the source pages and builds simple manifests, so you can see which pages were found, what metadata was extracted, and how many table images each page contains.

Step 4 downloads the raw image files and stitches them vertically where needed. This creates a consistent input for OCR and also gives you a useful visual checkpoint.

Step 5 initializes the OCR engine once, so it can be reused for multiple pages without repeated setup overhead.

Step 6 runs OCR on a single stitched page and saves the raw output to Excel. This is the first real extraction step, and it is where you confirm whether the table is being recognized properly.

Step 7 cleans that raw OCR output. It finds the start of the table body, applies the expected schema, translates province names, and converts value columns from OCR text to numeric form.

Step 8 builds a human-review version of the table. This includes English labels, expected Chinese labels, and the cleaned values in one place so you can visually compare the machine output against the source.

Step 9 adds light workbook formatting to make the review file easier to read.

Step 10 is a small batch loop that repeats the same process across multiple pages once the single-page flow is working. It is intentionally simple so that failures are easy to spot and debug.

'''
####

'''
conda create -n neaocr python=3.10 -y
conda activate neaocr

python -m pip install --upgrade pip
python -m pip install "numpy<2"
python -m pip install paddlepaddle==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
python -m pip install paddleocr opencv-python pillow beautifulsoup4 requests pandas

python -m pip install "img2table[paddle]"

python -c "import img2table; print('img2table ok')"
python -c "from img2table.document import Image; print('Image ok')"
python -c "from img2table.ocr import PaddleOCR; print('img2table PaddleOCR wrapper ok')"

'''





#1) Imports, paths, URLs, fixed schema, province map

import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
import cv2
from bs4 import BeautifulSoup
from PIL import Image as PILImage
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from img2table.document import Image as Img2TableImage
from img2table.ocr import PaddleOCR as Img2TablePaddleOCR
from img2table.tables.processing import common as img2table_common

# ============================================================
# USER-EDITABLE PATHS
# ============================================================
BASE_DIR = Path(r"C:\Users\james\Documents\GitHub\GIPT\China NEA")

RAW_IMAGES_DIR = BASE_DIR / "raw_images"
STITCHED_DIR = BASE_DIR / "stitched"
RAW_TABLES_DIR = BASE_DIR / "raw_tables_xlsx"
REVIEW_DIR = BASE_DIR / "review_workbooks"
CLEAN_CSV_DIR = BASE_DIR / "clean_csv"
LOGS_DIR = BASE_DIR / "logs"

for d in [BASE_DIR, RAW_IMAGES_DIR, STITCHED_DIR, RAW_TABLES_DIR, REVIEW_DIR, CLEAN_CSV_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ============================================================
# INPUT URLS
# ============================================================
URLS = [
    "https://www.nea.gov.cn/20260305/4216fa1274bd4b7f8da92090ba3999aa/c.html",
    "https://www.nea.gov.cn/20251112/35126d06a151461882b61d0a2e5706a6/c.html",
    "https://www.nea.gov.cn/20250811/b32802d80ef04148b704e6bc1cd51eb2/c.html",
    "https://www.nea.gov.cn/20250429/b78504d2e8a14b97bdcffb2c501b7393/c.html",
    "https://www.nea.gov.cn/20250221/f04452701c914d51a89d0c0ea6f4acd1/c.html",
    "https://www.nea.gov.cn/2024-11/01/c_1310787081.htm",
    "https://www.nea.gov.cn/2024-07/25/c_1310782757.htm",
    "https://www.nea.gov.cn/2024-05/06/c_1310773741.htm",
]

# optional: use a CSV instead of inline URLS
# should contain column 'url' or 'source_page_url'
URLS_CSV = None
# URLS_CSV = BASE_DIR / "nea_provincial_pv_source_pages_structured_2016_2025.csv"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

OCR_LANG = "ch"
MIN_CONFIDENCE = 50
TOTAL_LABEL = "总计"
EXPECTED_N_COLS = 9

# img2table can occasionally raise an opaque OpenCV error while looking for
# table titles above detected tables. Returning no contours is consistent with
# img2table's own empty-crop behavior and lets table extraction continue.
_ORIGINAL_GET_CONTOURS_CELL = img2table_common.get_contours_cell


def safe_get_contours_cell(*args, **kwargs):
    try:
        return _ORIGINAL_GET_CONTOURS_CELL(*args, **kwargs)
    except cv2.error as e:
        print(f"WARNING: img2table contour detection skipped after OpenCV error: {e}")
        return []


img2table_common.get_contours_cell = safe_get_contours_cell
if "img2table.tables.processing.text.titles" in sys.modules:
    sys.modules["img2table.tables.processing.text.titles"].get_contours_cell = safe_get_contours_cell

EXPECTED_EN = [
    "province_cn",
    "new_capacity_total_10kw",
    "new_capacity_utility_10kw",
    "new_capacity_distributed_10kw",
    "new_capacity_residential_10kw",
    "cum_capacity_total_10kw",
    "cum_capacity_utility_10kw",
    "cum_capacity_distributed_10kw",
    "cum_capacity_residential_10kw",
]

FRIENDLY_EN = [
    "Province (CN)",
    "New capacity total",
    "New utility-scale",
    "New distributed",
    "New residential",
    "Cumulative total",
    "Cumulative utility-scale",
    "Cumulative distributed",
    "Cumulative residential",
]

PROVINCE_EN_MAP = {
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
    "新疆兵团": "Xinjiang Production and Construction Corps",
    "新疆生产建设兵团": "Xinjiang Production and Construction Corps",
}


#2 Helper functions


def safe_slug(s):
    s = str(s) if s is not None else "unknown"
    s = re.sub(r"[^\w\-]+", "_", s)
    return s.strip("_")


def load_urls(urls=None, urls_csv=None):
    if urls_csv:
        df = pd.read_csv(urls_csv)
        if "url" in df.columns:
            return df["url"].dropna().tolist()
        if "source_page_url" in df.columns:
            return df["source_page_url"].dropna().tolist()
        raise ValueError("URLS_CSV must contain 'url' or 'source_page_url'")
    return list(urls or [])


def extract_page_metadata(html: str):
    text = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
    m_date = re.search(r"发布时间：\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", text)
    publish_date = m_date.group(1) if m_date else None
    m_unit = re.search(r"单位[:：]\s*([^\n]+)", text)
    unit = m_unit.group(1).strip() if m_unit else None
    return publish_date, unit


def infer_year_from_title_or_date(title, publish_date):
    if title:
        m = re.search(r"(20\d{2})年", title)
        if m:
            return int(m.group(1))
    if publish_date:
        return int(str(publish_date)[:4])
    return None


def infer_checkpoint(title):
    title = str(title or "")
    if "前三季度" in title:
        return "q3"
    if "上半年" in title:
        return "h1"
    if "一季度" in title:
        return "q1"
    return "annual"


def build_expected_cn_headers(year, checkpoint):
    if year is None:
        year = "UNKNOWN"
    if checkpoint == "q1":
        new_prefix = f"{year}年一季度新增并网容量"
        cum_prefix = f"截至{year}年3月底累计并网容量"
    elif checkpoint == "h1":
        new_prefix = f"{year}年上半年新增并网容量"
        cum_prefix = f"截至{year}年6月底累计并网容量"
    elif checkpoint == "q3":
        new_prefix = f"{year}年前三季度新增并网容量"
        cum_prefix = f"截至{year}年9月底累计并网容量"
    else:
        new_prefix = f"{year}年新增并网容量"
        cum_prefix = f"截至{year}年底累计并网容量"
    return [
        "省(区、市)",
        new_prefix,
        f"{new_prefix}_其中：集中式光伏电站",
        f"{new_prefix}_其中：分布式光伏",
        f"{new_prefix}_其中：户用光伏",
        cum_prefix,
        f"{cum_prefix}_其中：集中式光伏电站",
        f"{cum_prefix}_其中：分布式光伏",
        f"{cum_prefix}_其中：户用光伏",
    ]


def scrape_page(url: str):
    r = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding
    soup = BeautifulSoup(r.text, "html.parser")
    h1 = soup.find(["h1", "H1"])
    if h1:
        title = h1.get_text(" ", strip=True)
    else:
        title_tag = soup.find("title")
        title = title_tag.get_text(" ", strip=True) if title_tag else None
    publish_date, unit = extract_page_metadata(r.text)
    year = infer_year_from_title_or_date(title, publish_date)
    checkpoint = infer_checkpoint(title)
    image_urls = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("zoomfile")
        if not src:
            continue
        full_url = urljoin(url, src)
        if re.search(r"\.(png|jpg|jpeg|webp)(\?.*)?$", full_url, flags=re.I):
            image_urls.append(full_url)
    seen = set()
    image_urls = [x for x in image_urls if not (x in seen or seen.add(x))]
    return {
        "source_page_url": url,
        "title": title,
        "publish_date": publish_date,
        "year": year,
        "checkpoint": checkpoint,
        "unit": unit,
        "n_images": len(image_urls),
        "image_urls": image_urls,
    }


def download_image(url, out_path):
    r = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
    r.raise_for_status()
    out_path.write_bytes(r.content)
    return out_path


def open_image(path):
    return PILImage.open(path).convert("RGB")


def stitch_vertical(image_paths, out_path, bg_color=(255, 255, 255)):
    imgs = [open_image(p) for p in image_paths]
    max_width = max(img.width for img in imgs)
    total_height = sum(img.height for img in imgs)
    canvas = PILImage.new("RGB", (max_width, total_height), color=bg_color)
    y = 0
    for img in imgs:
        canvas.paste(img, (0, y))
        y += img.height
    canvas.save(out_path, quality=95)
    return out_path


def flatten_header(vals):
    out = []
    for v in vals:
        if pd.isna(v):
            continue
        s = str(v).replace("\n", "").strip()
        if not s:
            continue
        if not out or s != out[-1]:
            out.append(s)
    return "".join(out)


def normalize_province_name(x):
    if pd.isna(x):
        return x
    s = str(x).strip()
    s = s.replace(" ", "").replace("\n", "")
    s = s.replace("（", "(").replace("）", ")")
    return s


def to_float(x):
    if pd.isna(x):
        return pd.NA
    s = str(x).strip()
    if s == "":
        return pd.NA
    s = s.replace(",", "").replace("，", "")
    s = s.replace("O", "0").replace("o", "0")
    s = re.sub(r"[^\d\.\-]", "", s)
    if s in {"", ".", "-", "-."}:
        return pd.NA
    try:
        return float(s)
    except Exception:
        return pd.NA


def find_total_row_and_start_col(raw_df, total_label=TOTAL_LABEL, max_search_cols=4):
    for col_idx in range(min(max_search_cols, raw_df.shape[1])):
        ser = raw_df[col_idx].astype(str).str.strip()
        matches = raw_df.index[ser.eq(total_label)]
        if len(matches) > 0:
            return int(matches[0]), col_idx
    raise ValueError(f"Could not find total row labeled '{total_label}'.")


def autosize_worksheet(ws, max_width=35):
    for col in range(1, ws.max_column + 1):
        col_letter = get_column_letter(col)
        max_len = 0
        for row in ws.iter_rows(min_col=col, max_col=col, values_only=True):
            val = "" if row[0] is None else str(row[0])
            max_len = max(max_len, len(val))
        ws.column_dimensions[col_letter].width = min(max_len + 2, max_width)

def extract_inline_table_from_html(url: str):
    r = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding
    soup = BeautifulSoup(r.text, "html.parser")
    lines = [x.strip() for x in soup.get_text("\n").splitlines() if x.strip()]
    # find first total row
    start_idx = lines.index("总计")
    rows = []
    i = start_idx
    while i + 8 < len(lines):
        label = lines[i]
        vals = lines[i+1:i+9]
        if len(vals) < 8:
            break
        # stop once we leave the table body
        cleaned_vals = [re.sub(r"[^\d\.\-]", "", v) for v in vals]
        if not all(v != "" for v in cleaned_vals):
            break
        rows.append([label] + vals)
        i += 9
    return pd.DataFrame(rows)


#3) Scrape all source pages and build refs

urls = load_urls(URLS, URLS_CSV)
print(f"{len(urls)} urls loaded")

page_results = [scrape_page(url) for url in urls]

summary_df = pd.DataFrame([
    {
        "source_page_url": r["source_page_url"],
        "title": r["title"],
        "publish_date": r["publish_date"],
        "year": r["year"],
        "checkpoint": r["checkpoint"],
        "unit": r["unit"],
        "n_images": r["n_images"],
    }
    for r in page_results
])

summary_df["page_type"] = summary_df["n_images"].apply(
    lambda x: "image_table" if x > 0 else "inline_html_table"
)
print(summary_df[["publish_date", "year", "checkpoint", "n_images", "page_type", "title"]])

images_df = pd.DataFrame([
    {
        "source_page_url": r["source_page_url"],
        "title": r["title"],
        "publish_date": r["publish_date"],
        "year": r["year"],
        "checkpoint": r["checkpoint"],
        "unit": r["unit"],
        "image_order": i + 1,
        "image_url": img_url,
    }
    for r in page_results
    for i, img_url in enumerate(r["image_urls"])
])

summary_df.to_csv(LOGS_DIR / "page_summary_scraped.csv", index=False, encoding="utf-8-sig")
images_df.to_csv(LOGS_DIR / "image_manifest_scraped.csv", index=False, encoding="utf-8-sig")

print(summary_df)
print(images_df.head())


#4) Download raw images and stitch them
# Step 4 only applies to pages where n_images > 0.
# Inline HTML pages will not appear in images_df and will be handled later.

download_manifest_rows = []

for page_url, g in images_df.sort_values(["source_page_url", "image_order"]).groupby("source_page_url", sort=False):
    first = g.iloc[0]
    page_id = f"{first['publish_date']}_{safe_slug(first['title'])[:80]}"
    page_slug = safe_slug(page_id)
    page_raw_dir = RAW_IMAGES_DIR / page_slug
    page_raw_dir.mkdir(parents=True, exist_ok=True)
    local_paths = []
    for row in g.itertuples(index=False):
        ext = Path(urlparse(row.image_url).path).suffix.lower() or ".jpg"
        fname = f"{int(row.image_order):02d}{ext}"
        out_path = page_raw_dir / fname
        download_image(row.image_url, out_path)
        local_paths.append(out_path)
        download_manifest_rows.append({
            "source_page_url": row.source_page_url,
            "title": row.title,
            "publish_date": row.publish_date,
            "year": row.year,
            "checkpoint": row.checkpoint,
            "image_order": row.image_order,
            "image_url": row.image_url,
            "local_path": str(out_path),
        })
    stitched_path = STITCHED_DIR / f"{page_slug}_stitched.jpg"
    stitch_vertical(local_paths, stitched_path)
    print("saved stitched image:", stitched_path)

download_manifest_df = pd.DataFrame(download_manifest_rows)
download_manifest_df.to_csv(LOGS_DIR / "download_manifest.csv", index=False, encoding="utf-8-sig")


#5) initialize ocr (in theory, it doesn't like being run twice in single session, but probably fine eitherway)
ocr = Img2TablePaddleOCR(lang=OCR_LANG)
print("OCR initialized")


#6) Pick one page and run OCR to raw xlsx
PAGE_IDX = -3   # change to test pages one by one

page_meta = page_results[PAGE_IDX]
print(page_meta["title"])
print(page_meta["publish_date"], page_meta["checkpoint"], page_meta["n_images"])

page_id = f"{page_meta['publish_date']}_{safe_slug(page_meta['title'])[:80]}"
page_slug = safe_slug(page_id)

if page_meta["n_images"] > 0:
    stitched_path = STITCHED_DIR / f"{page_slug}_stitched.jpg"
    print(stitched_path)
    print(stitched_path.exists())
    t0 = time.time()
    doc = Img2TableImage(str(stitched_path))
    tables = doc.extract_tables(
        ocr=ocr,
        implicit_rows=True,
        implicit_columns=True,
        borderless_tables=False,
        min_confidence=MIN_CONFIDENCE,
    )
    print("n_tables:", len(tables))
    print("elapsed sec:", round(time.time() - t0, 2))
    table = tables[0]
    raw_df = table.df.copy()
else:
    t0 = time.time()
    raw_df = extract_inline_table_from_html(page_meta["source_page_url"])
    print("inline html rows:", len(raw_df))
    print("elapsed sec:", round(time.time() - t0, 2))

raw_table_xlsx = RAW_TABLES_DIR / f"{page_slug}_raw.xlsx"
raw_df.to_excel(raw_table_xlsx)

print("saved raw table:", raw_table_xlsx)
print(raw_df.head())




#7) Clean the raw xlsx and build review workbook

raw = pd.read_excel(raw_table_xlsx, header=None)

year = page_meta["year"]
checkpoint = page_meta["checkpoint"]
expected_cn = build_expected_cn_headers(year, checkpoint)

if page_meta["n_images"] > 0:
    data_start_idx, start_col = find_total_row_and_start_col(raw, total_label=TOTAL_LABEL, max_search_cols=4)
    header_start = max(0, data_start_idx - 5)
    header_rows = raw.iloc[header_start:data_start_idx, start_col:start_col + EXPECTED_N_COLS].copy()
    ocr_header_preview = pd.DataFrame({
        "col_position": range(1, EXPECTED_N_COLS + 1),
        "ocr_header_flat": [
            flatten_header(header_rows[c].tolist()) if c in header_rows.columns else ""
            for c in range(start_col, start_col + EXPECTED_N_COLS)
        ],
        "expected_cn": expected_cn,
        "expected_en": EXPECTED_EN,
        "friendly_en": FRIENDLY_EN,
    })
    body = raw.iloc[data_start_idx:, start_col:start_col + EXPECTED_N_COLS].copy()
    body.columns = expected_cn
else:
    # inline HTML pages already come out as 9 clean columns
    body = raw.iloc[:, :EXPECTED_N_COLS].copy()
    body.columns = expected_cn
    # no OCR header to inspect here, so just use expected labels as the preview
    ocr_header_preview = pd.DataFrame({
        "col_position": range(1, EXPECTED_N_COLS + 1),
        "ocr_header_flat": expected_cn,
        "expected_cn": expected_cn,
        "expected_en": EXPECTED_EN,
        "friendly_en": FRIENDLY_EN,
    })

body["省(区、市)"] = body["省(区、市)"].apply(normalize_province_name)
body["province_en"] = body["省(区、市)"].map(PROVINCE_EN_MAP)

for c in expected_cn[1:]:
    body[c] = body[c].apply(to_float)

clean = body.rename(columns=dict(zip(expected_cn, EXPECTED_EN)))
clean["province_translation_missing"] = clean["province_en"].isna()

clean = clean[
    ["province_cn", "province_en"]
    + EXPECTED_EN[1:]
    + ["province_translation_missing"]
]

print(clean.head())
print(ocr_header_preview)


#8) Build the review sheet and save workbook

review_cols = ["province_cn", "province_en"] + EXPECTED_EN[1:] + ["province_translation_missing"]

top_en = pd.DataFrame([{
    "province_cn": "Province (raw OCR CN)",
    "province_en": "Province (EN translation)",
    "new_capacity_total_10kw": "New capacity total",
    "new_capacity_utility_10kw": "New utility-scale",
    "new_capacity_distributed_10kw": "New distributed",
    "new_capacity_residential_10kw": "New residential",
    "cum_capacity_total_10kw": "Cumulative total",
    "cum_capacity_utility_10kw": "Cumulative utility-scale",
    "cum_capacity_distributed_10kw": "Cumulative distributed",
    "cum_capacity_residential_10kw": "Cumulative residential",
    "province_translation_missing": "Translation missing?",
}])

top_cn = pd.DataFrame([{
    "province_cn": expected_cn[0],
    "province_en": "英文省名",
    "new_capacity_total_10kw": expected_cn[1],
    "new_capacity_utility_10kw": expected_cn[2],
    "new_capacity_distributed_10kw": expected_cn[3],
    "new_capacity_residential_10kw": expected_cn[4],
    "cum_capacity_total_10kw": expected_cn[5],
    "cum_capacity_utility_10kw": expected_cn[6],
    "cum_capacity_distributed_10kw": expected_cn[7],
    "cum_capacity_residential_10kw": expected_cn[8],
    "province_translation_missing": "英文翻译缺失？",
}])

review_df = pd.concat(
    [top_en[review_cols], top_cn[review_cols], clean[review_cols]],
    ignore_index=True
)

review_xlsx = REVIEW_DIR / f"{page_slug}_review.xlsx"
clean_csv = CLEAN_CSV_DIR / f"{page_slug}_clean.csv"

with pd.ExcelWriter(review_xlsx, engine="openpyxl") as writer:
    raw.to_excel(writer, sheet_name="raw_ocr", index=False, header=False)
    ocr_header_preview.to_excel(writer, sheet_name="header_check", index=False)
    clean.to_excel(writer, sheet_name="clean", index=False)
    review_df.to_excel(writer, sheet_name="clean_review", index=False)

clean.to_csv(clean_csv, index=False, encoding="utf-8-sig")

print("saved review workbook:", review_xlsx)
print("saved clean csv:", clean_csv)


#9)  formatting for the review workbook

wb = load_workbook(review_xlsx)

ws = wb["header_check"]
for cell in ws[1]:
    cell.font = Font(bold=True)
    cell.fill = PatternFill("solid", fgColor="D9EAF7")

ws.freeze_panes = "A2"
autosize_worksheet(ws)

ws = wb["clean"]
for cell in ws[1]:
    cell.font = Font(bold=True)
    cell.fill = PatternFill("solid", fgColor="D9EAD3")

ws.freeze_panes = "A2"
autosize_worksheet(ws)

ws = wb["clean_review"]
for cell in ws[1]:
    cell.font = Font(bold=True)
    cell.fill = PatternFill("solid", fgColor="D9EAF7")

for cell in ws[2]:
    cell.font = Font(bold=True)
    cell.fill = PatternFill("solid", fgColor="FCE5CD")

ws.freeze_panes = "A3"
autosize_worksheet(ws)

ws = wb["raw_ocr"]
autosize_worksheet(ws, max_width=25)

ws = wb["clean"]
for col in range(3, 11):
    for row in range(2, ws.max_row + 1):
        ws.cell(row=row, column=col).number_format = "0.0"

ws = wb["clean_review"]
for col in range(3, 11):
    for row in range(4, ws.max_row + 1):
        ws.cell(row=row, column=col).number_format = "0.0"

wb.save(review_xlsx)
print("formatted:", review_xlsx)


#10) batch loop once one page looks good

run_rows = []

for PAGE_IDX in range(len(page_results)):
    try:
        page_meta = page_results[PAGE_IDX]
        page_id = f"{page_meta['publish_date']}_{safe_slug(page_meta['title'])[:80]}"
        page_slug = safe_slug(page_id)
        stitched_path = STITCHED_DIR / f"{page_slug}_stitched.jpg"
        raw_table_xlsx = RAW_TABLES_DIR / f"{page_slug}_raw.xlsx"
        review_xlsx = REVIEW_DIR / f"{page_slug}_review.xlsx"
        clean_csv = CLEAN_CSV_DIR / f"{page_slug}_clean.csv"
        print(f"\n[{PAGE_IDX}] {page_meta['title']}")
        t0 = time.time()
        expected_cn = build_expected_cn_headers(page_meta["year"], page_meta["checkpoint"])
        # ============================================================
        # EXTRACT RAW TABLE
        # ============================================================
        if page_meta["n_images"] > 0:
            # image-based table -> OCR route
            doc = Img2TableImage(str(stitched_path))
            tables = doc.extract_tables(
                ocr=ocr,
                implicit_rows=True,
                implicit_columns=True,
                borderless_tables=False,
                min_confidence=MIN_CONFIDENCE,
            )
            if len(tables) == 0:
                raise ValueError("No tables returned by OCR")
            table = tables[0]
            table.df.to_excel(raw_table_xlsx)   # keep same style as before
            raw = pd.read_excel(raw_table_xlsx, header=None)
            data_start_idx, start_col = find_total_row_and_start_col(
                raw,
                total_label=TOTAL_LABEL,
                max_search_cols=4
            )
            header_start = max(0, data_start_idx - 5)
            header_rows = raw.iloc[
                header_start:data_start_idx,
                start_col:start_col + EXPECTED_N_COLS
            ].copy()
            ocr_header_preview = pd.DataFrame({
                "col_position": range(1, EXPECTED_N_COLS + 1),
                "ocr_header_flat": [
                    flatten_header(header_rows[c].tolist()) if c in header_rows.columns else ""
                    for c in range(start_col, start_col + EXPECTED_N_COLS)
                ],
                "expected_cn": expected_cn,
                "expected_en": EXPECTED_EN,
                "friendly_en": FRIENDLY_EN,
            })
            body = raw.iloc[data_start_idx:, start_col:start_col + EXPECTED_N_COLS].copy()
            body.columns = expected_cn
        else:
            # inline HTML table -> direct text parsing route
            inline_df = extract_inline_table_from_html(page_meta["source_page_url"]).copy()
            if inline_df.shape[1] != EXPECTED_N_COLS:
                raise ValueError(
                    f"Inline HTML parser returned {inline_df.shape[1]} columns; expected {EXPECTED_N_COLS}"
                )
            # save a simple raw version for reference
            inline_df.to_excel(raw_table_xlsx, index=False, header=False)
            # this is what goes in the raw_ocr sheet
            raw = inline_df.copy()
            body = inline_df.copy()
            body.columns = expected_cn
            # no OCR header on inline pages, so just show expected headers
            ocr_header_preview = pd.DataFrame({
                "col_position": range(1, EXPECTED_N_COLS + 1),
                "ocr_header_flat": expected_cn,
                "expected_cn": expected_cn,
                "expected_en": EXPECTED_EN,
                "friendly_en": FRIENDLY_EN,
            })
        # ============================================================
        # CLEAN
        # ============================================================
        body["省(区、市)"] = body["省(区、市)"].apply(normalize_province_name)
        body["province_en"] = body["省(区、市)"].map(PROVINCE_EN_MAP)
        for c in expected_cn[1:]:
            body[c] = body[c].apply(to_float)
        clean = body.rename(columns=dict(zip(expected_cn, EXPECTED_EN)))
        clean["province_translation_missing"] = clean["province_en"].isna()
        clean = clean[
            ["province_cn", "province_en"]
            + EXPECTED_EN[1:]
            + ["province_translation_missing"]
        ]
        # ============================================================
        # BUILD REVIEW SHEET
        # ============================================================
        review_cols = ["province_cn", "province_en"] + EXPECTED_EN[1:] + ["province_translation_missing"]
        top_en = pd.DataFrame([{
            "province_cn": "Province (raw OCR CN)",
            "province_en": "Province (EN translation)",
            "new_capacity_total_10kw": "New capacity total",
            "new_capacity_utility_10kw": "New utility-scale",
            "new_capacity_distributed_10kw": "New distributed",
            "new_capacity_residential_10kw": "New residential",
            "cum_capacity_total_10kw": "Cumulative total",
            "cum_capacity_utility_10kw": "Cumulative utility-scale",
            "cum_capacity_distributed_10kw": "Cumulative distributed",
            "cum_capacity_residential_10kw": "Cumulative residential",
            "province_translation_missing": "Translation missing?",
        }])
        top_cn = pd.DataFrame([{
            "province_cn": expected_cn[0],
            "province_en": "英文省名",
            "new_capacity_total_10kw": expected_cn[1],
            "new_capacity_utility_10kw": expected_cn[2],
            "new_capacity_distributed_10kw": expected_cn[3],
            "new_capacity_residential_10kw": expected_cn[4],
            "cum_capacity_total_10kw": expected_cn[5],
            "cum_capacity_utility_10kw": expected_cn[6],
            "cum_capacity_distributed_10kw": expected_cn[7],
            "cum_capacity_residential_10kw": expected_cn[8],
            "province_translation_missing": "英文翻译缺失？",
        }])
        review_df = pd.concat(
            [top_en[review_cols], top_cn[review_cols], clean[review_cols]],
            ignore_index=True
        )
        with pd.ExcelWriter(review_xlsx, engine="openpyxl") as writer:
            raw.to_excel(writer, sheet_name="raw_ocr", index=False, header=False)
            ocr_header_preview.to_excel(writer, sheet_name="header_check", index=False)
            clean.to_excel(writer, sheet_name="clean", index=False)
            review_df.to_excel(writer, sheet_name="clean_review", index=False)
        clean.to_csv(clean_csv, index=False, encoding="utf-8-sig")
        run_rows.append({
            "source_page_url": page_meta["source_page_url"],
            "title": page_meta["title"],
            "publish_date": page_meta["publish_date"],
            "year": page_meta["year"],
            "checkpoint": page_meta["checkpoint"],
            "page_type": "image_table" if page_meta["n_images"] > 0 else "inline_html_table",
            "status": "ok",
            "n_rows_clean": len(clean),
            "n_missing_translations": int(clean["province_translation_missing"].sum()),
            "elapsed_sec": round(time.time() - t0, 2),
            "notes": "",
        })
    except Exception as e:
        run_rows.append({
            "source_page_url": page_meta["source_page_url"],
            "title": page_meta["title"],
            "publish_date": page_meta["publish_date"],
            "year": page_meta["year"],
            "checkpoint": page_meta["checkpoint"],
            "page_type": "image_table" if page_meta["n_images"] > 0 else "inline_html_table",
            "status": "failed",
            "n_rows_clean": pd.NA,
            "n_missing_translations": pd.NA,
            "elapsed_sec": pd.NA,
            "notes": str(e),
        })
        print("FAILED:", e)

run_summary_df = pd.DataFrame(run_rows)
run_summary_df.to_csv(LOGS_DIR / "run_summary.csv", index=False, encoding="utf-8-sig")
run_summary_df
