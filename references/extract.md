# Extract: PDFs, spreadsheets, documents, and the web

This reference is the extraction toolchain — match the input type to the right tool and recover a tidy long-form DataFrame, whatever the source format. It covers PDFs, tabular files (XLSX/CSV/Parquet/databases), structured documents (HTML/XML/JSON/DOCX), and live web scraping. This is the **Level 0** workhorse of the skill: nearly every liberation project starts here, and most use two or three of these tools in combination.

## Identify the input type

Start by classifying the input, then jump to the relevant part below. Defaults and fallbacks:

| Input type | Default tool | Fallback | Section |
|---|---|---|---|
| Born-digital PDF (text layer) | `pdfplumber` | `camelot` for grid pages | [pdfplumber](#pdfplumber--the-default-for-born-digital-pdfs) |
| Ruled PDF table (visible grid) | `camelot` (lattice) | `pdfplumber` | [camelot](#camelot--for-cleanly-ruled-tables) |
| Scanned / image-only PDF | `tesseract` via `pytesseract` | PaddleOCR / Surya / docling VLM | [tesseract](#tesseract--for-scanned-and-image-only-pdfs) |
| Clean XLSX | `pandas.read_excel` | `openpyxl` inspect | [Reading XLSX](#reading-xlsx) |
| Panel / merged-header XLSX | `openpyxl` (inspect, then block-parse) | manual block boundaries | [Patterns for awkward XLSX](#patterns-for-awkward-xlsx) |
| CSV | `pandas.read_csv` with explicit dtypes | `csv` module | [Reading CSV](#reading-csv) |
| Parquet | `pandas.read_parquet` (pyarrow) | `pyarrow.parquet` row groups | [Reading Parquet](#reading-parquet) |
| Database / SQL dump | `sqlalchemy` / `duckdb` | `sqlite3` | [Reading databases](#reading-databases) |
| HTML with `<table>` | `pandas.read_html` | `selectolax` | [HTML](#html) |
| HTML, no table (div/li layout) | `selectolax` (CSS selectors) | `lxml` XPath / BeautifulSoup | [selectolax](#selectolax-for-layout-as-tables-and-structured-non-table-content) |
| JSON (flat or nested) | `pd.json_normalize` | `json` streaming | [JSON](#json) |
| XML | `lxml` / `pd.read_xml` | `iterparse` streaming | [XML](#xml) |
| DOCX / RTF | pandoc → markdown | direct OOXML inspection | [Narrative documents](#narrative-documents-in-proprietary-formats--docx-rtf-and-the-markdown-as-intermediate-pattern) |
| Dynamic JS-rendered page | `playwright` | find the underlying JSON endpoint | [Dynamic pages](#dynamic-pages) |
| Recurring / iterative scrape | `requests` + `requests-cache` + `tenacity` | `httpx` + `hishel` | [Protocols](#protocols--when-you-do-need-to-fetch) |
| Multi-format corpus, end-to-end | `docling` / `kreuzberg` | per-format tools | [Modern unified extractors](#modern-unified-extractors--when-one-tool-is-enough) |

---

# Part 1 — PDF extraction

The tools — `pdfplumber`, `camelot`, `tesseract` via `pytesseract` — each excel at a different class of PDF, and most projects use two or three in combination.

## First: identify the PDF type

Classify the input before opening any extractor. Run this triage and write the result in the project's Survey notes.

```python
import pdfplumber

with pdfplumber.open(path) as pdf:
    page = pdf.pages[0]
    text = page.extract_text() or ""
    has_text_layer = len(text.strip()) > 20
    n_chars = len(page.chars)
    n_lines = len(page.lines) + len(page.rects)
    n_images = len(page.images)
```

| `has_text_layer` | `n_lines` | `n_images` | Diagnosis | Default tool |
|---|---|---|---|---|
| True | Many | Few | **Born-digital ruled table** | `camelot` (lattice) |
| True | Few/none | Few | **Born-digital text-positioned table** | `pdfplumber` |
| True | Some | Few | **Born-digital mixed** | `pdfplumber` first, `camelot` for grid pages |
| False | — | Many or full-page | **Scanned PDF (image-only)** | `tesseract` via `pytesseract` |
| True | — | Many | **Hybrid (scanned + text overlay)** | Inspect; usually `pdfplumber` works |

Sanity check: open the PDF in a viewer and try to **select and copy text** from a table cell. If you get the cell content, the text layer is good — use `pdfplumber` or `camelot`. If you get nothing or garbled glyphs, it's scanned and you need OCR.

## pdfplumber — the default for born-digital PDFs

[`pdfplumber`](https://github.com/jsvine/pdfplumber) is the workhorse. It exposes characters with positions, lines, rectangles, and curves, and offers a configurable table-detection pass that infers rows and columns from spatial layout. It is the right default whenever the PDF has a text layer. (Pdfplumber is built on [`pdfminer.six`](https://github.com/pdfminer/pdfminer.six), the community-maintained text-extraction engine — drop to pdfminer.six directly when pdfplumber's higher-level abstractions get in the way, but the rest of this section assumes the pdfplumber API.)

### Minimal idiomatic use

```python
import pdfplumber

with pdfplumber.open("data/original/agency/report.pdf") as pdf:
    rows = []
    for page in pdf.pages:
        for table in page.extract_tables() or []:
            rows.extend(table)
```

`page.extract_tables()` returns a list of lists (outer = tables on the page; inner = rows of cell strings). `page.extract_table()` returns just the first table.

The PDF also carries metadata via `pdf.metadata` — title, author, creator (authoring application), producer (library that wrote the bytes), creation/modification timestamps. None is load-bearing for extraction, but the *producer* field is useful provenance: when a multi-vintage series shifts from `"Microsoft Word"` to `"Adobe PDF Library"` mid-period, the parser usually needs a vintage branch shortly after. Worth copying into `provenance.csv`'s `extraction_notes` for the vintages where the source switched.

### When the default detection misfires

The default detector uses both lines and text positioning. When it's wrong it's usually wrong in one of these ways:

- **Splits one table into many** — usually because there are blank rows mid-table or section headers that look like table breaks. Pass `table_settings={"vertical_strategy": "lines", "horizontal_strategy": "text"}` to lean harder on rulings.
- **Merges two adjacent tables** — opposite cause; pass `{"vertical_strategy": "text", "horizontal_strategy": "text"}` or extract by cropping to a bounding box first.
- **Misses rows that wrap** — increase `snap_tolerance` and `text_tolerance` so wrapped lines aren't treated as new rows.
- **Hallucinates columns from spaced-out text** — pass explicit `explicit_vertical_lines` from inspecting `page.lines` and `page.rects`.

The configuration vocabulary is in [the pdfplumber README](https://github.com/jsvine/pdfplumber#extracting-tables) and [Unstract's pdfplumber guide](https://unstract.com/blog/guide-to-pdfplumber-text-and-table-extraction-capabilities/). Two patterns worth memorizing:

```python
# Bounding-box crop before extraction — when the page has a table plus headers/footers
bbox = (40, 100, page.width - 40, page.height - 80)
table = page.crop(bbox).extract_table()

# Use the lines you can see, ignore the inferred ones
table = page.extract_table({
    "vertical_strategy": "explicit",
    "horizontal_strategy": "lines",
    "explicit_vertical_lines": [v["x0"] for v in page.lines if v["height"] > 100],
})
```

### What pdfplumber struggles with

- **Tables that span multiple pages** — pdfplumber doesn't join them. Handle in your parser: detect a continuation header on each page, drop it, concatenate the row lists.
- **Multi-row column headers / merged header cells** — extracted as separate rows; flatten in the parser.
- **Panel-format tables** where the same logical row repeats blocks across pages — write a vintage-specific parser that knows the panel structure.
- **Cells with embedded line breaks** — pdfplumber returns the raw text including the newline; clean in the parser.

Boulder Public Data's older Statements of Vote (2005, 2007, 2009) are pdfplumber-extractable but with vintage-specific parsers per year. The 2009 SoV is bundled here as a test fixture.

## camelot — for cleanly ruled tables

[`camelot`](https://github.com/camelot-dev/camelot) is purpose-built for table extraction from born-digital PDFs and provides two modes:

- **Lattice mode** (`flavor="lattice"`) — detects ruled tables by finding line intersections. Outstanding when the table has visible grid lines; useless when it doesn't.
- **Stream mode** (`flavor="stream"`) — uses text positioning, similar to pdfplumber's default. Often worse than pdfplumber for stream-style tables; reach for camelot specifically for lattice.

### When to choose camelot over pdfplumber

- The table has clear horizontal AND vertical rulings forming a complete grid.
- pdfplumber's default detection is breaking on multi-row header cells (camelot handles these better via the grid).
- You need a quick accuracy report — camelot returns an `accuracy` and `whitespace` percentage per table that's useful for triaging which pages need manual review.

```python
import camelot

tables = camelot.read_pdf(
    "data/original/agency/report.pdf",
    pages="1-end",
    flavor="lattice",
)
for t in tables:
    print(t.page, t.parsing_report)  # accuracy, whitespace, order, page
    df = t.df  # pandas DataFrame
```

The [camelot test corpus](https://github.com/camelot-dev/camelot/tree/master/tests/files) contains documented examples of both lattice and stream cases — use them as fixtures when validating a new parser.

### camelot's quirks

- Requires `ghostscript` (lattice mode) — install via the system package manager. On macOS: `brew install ghostscript`. On Debian/Ubuntu: `apt install ghostscript`.
- Slow on long PDFs. If you only need a few pages, pass `pages="3,7,12"`.
- The `accuracy` metric is a useful triage signal but not a substitute for reconciliation against an authoritative total.

## tesseract — for scanned and image-only PDFs

When the PDF has no text layer (or a corrupt one): rasterize each page, OCR it with [Tesseract](https://github.com/tesseract-ocr/tesseract), then handle the output as text. Quality varies dramatically by document and is sensitive to preprocessing.

### Minimal idiomatic use — tesseract

```python
import pdf2image  # requires poppler
import pytesseract
from PIL import Image

images = pdf2image.convert_from_path("data/original/scan.pdf", dpi=300)
text_by_page = [pytesseract.image_to_string(img, lang="eng") for img in images]
```

For tabular layout recovery, use `image_to_data` and reconstruct rows by clustering on the `top` coordinate:

```python
import pytesseract
from pytesseract import Output

data = pytesseract.image_to_data(image, output_type=Output.DATAFRAME, lang="eng")
# data has columns: level, page_num, block_num, par_num, line_num, word_num,
# left, top, width, height, conf, text
data = data.dropna(subset=["text"]).query("conf > 30")
```

Cluster on `top` (within tolerance) to recover rows; cluster on `left` to recover columns.

### Preprocessing matters more than the OCR engine

Image quality at the input is the single biggest factor in OCR output quality. Standard fixes:

- **Resolution.** 300 dpi minimum, 400 dpi for small fonts. Below 200 dpi you will fight Tesseract for every digit.
- **Deskew.** Even a 1° rotation degrades accuracy noticeably. Use `cv2.minAreaRect` on the document's bounding contour or [`deskew`](https://pypi.org/project/deskew/).
- **Binarize.** `cv2.threshold` with Otsu's method or `cv2.adaptiveThreshold` for uneven lighting.
- **Despeckle.** A median filter (`cv2.medianBlur`) before thresholding helps with scanner noise.
- **Crop to content.** Margins waste OCR effort and confuse the layout analyzer.

### Tesseract gotchas

- **Numbers vs letters confusion.** "0" vs "O", "1" vs "I" vs "l". For numeric tables, restrict the character set with `--psm 6 -c tessedit_char_whitelist=0123456789.,-`.
- **PSM (Page Segmentation Mode) matters.** The default (`--psm 3`, "auto") is often wrong for tables. Try `--psm 6` (assume a single uniform block of text) or `--psm 11` (sparse text) when default OCR is fragmenting rows.
- **Language packs.** English is bundled; other languages require `tesseract-ocr-<lang>` system packages. If the document is multilingual, pass `lang="eng+spa"`.
- **Training a custom model** is rarely worth it for civic data; the [tesseract training guide](https://github.com/neiths/tesseract_training_guide) documents the path if you do need it.

OCR'd output should always be **flagged as such in provenance** (e.g., `extraction_quality = "ocr_tesseract"` in the provenance sidecar) so downstream users can apply extra skepticism.

### When tesseract isn't enough

Tesseract remains the default — bundled in every Linux distro, 100+ language packs, tunes well via PSM and character-whitelist flags. But several modern OCR engines outperform it on specific failure modes, in this order:

| If tesseract is failing on… | Try |
|---|---|
| **Degraded or low-resolution scans** where preprocessing isn't enough | [**PaddleOCR**](https://github.com/PaddlePaddle/PaddleOCR) — production-grade engine with 80+ languages; reliably better than tesseract on noisy or rotated scans. Heavier install (PaddlePaddle wheel) but the accuracy bump is usually worth it. Also the backend kreuzberg uses by default. |
| **Mixed printed + handwritten** or **complex layouts where reading order matters** | [**Surya**](https://github.com/VikParuchuri/surya) — newer (VikParuchuri); does OCR + line / paragraph / reading-order detection in one pass. Pure-Python install, fast on CPU. Strong on multi-column documents. |
| **High-throughput batch processing** where install simplicity beats peak accuracy | [**EasyOCR**](https://github.com/JaidedAI/EasyOCR) — `pip install easyocr` and you have a working multi-language OCR. Less tunable than tesseract, but the lowest-friction option when you just need text out of a thousand scans. |
| **Production deployment with a clean Python API** for documents (not just images) | [**docTR**](https://github.com/mindee/doctr) — explicit "alternative for Tesseract" from Mindee; ships text-detection + text-recognition models with a higher-level document API than tesseract exposes. Worth it for projects building a sustained OCR service. |

Two-tool combinations also help: **[`OCRmyPDF`](https://github.com/jbarlow83/OCRmyPDF) + pdfplumber** is the canonical pattern for a scanned-PDF corpus that needs to be searched *and* extracted. OCRmyPDF wraps tesseract (or any tool above) to add a text layer *to the PDF in place* — the scanned PDF becomes a born-digital PDF that pdfplumber can then parse normally. This collapses the otherwise-awkward "OCR the page, save text separately, re-attribute text to coordinates" three-step into one. The original is preserved (OCRmyPDF writes a sidecar `.ocr.pdf`), so the immutable-originals discipline holds.

Update `extraction_quality` in `provenance.csv` to name the engine used (`ocr_paddleocr`, `ocr_surya`, `ocrmypdf`, etc.) — downstream users apply different skepticism levels depending on which engine produced the text.

## Extracting images as evidence

PDFs aren't always text-with-tables. Court filings, incident reports, environmental impact assessments, and FOIA-released archives often carry images that *are* the evidence — exhibits, photographs, scanned signatures, maps. The principle: **if the image is referenced by the surface text, the image is part of the dataset**, not optional ephemera. Extract it, hash it, store it alongside the text under `data/original/<source>/<vintage>/_images/<page>-<index>.<ext>`, and add a `has_image` column or a sidecar `images.csv` keyed on `(source, vintage, page)` so a downstream reader can join from a processed-CSV row back to the exhibit it cites.

```python
# pdfplumber exposes pdf.pages[N].images — bounding boxes + the raw bytes
# behind each embedded image. The same image objects are also reachable
# from the PDF's resource dictionary via pdfminer.six or pypdf for projects
# that need image-format-preserving extraction.
```

Update `provenance.csv` with an `images_extracted` count per (source, vintage) so the audit can flag the drift case where a refresh suddenly stops emitting images (usually a parser regression or a publisher format change).

## Layout analysis — when tables aren't enough

For documents where the structure is not just tables but mixed layout (figures, multi-column text, sidebars), reach for:

- [**`docling`**](https://github.com/docling-project/docling) — the modern default for PDF understanding with mixed layout. Parses reading order, table structure, code blocks, formulas, and image classification into a unified `DoclingDocument` representation with Markdown / HTML / lossless JSON / DocTags exports. Native VLM support via [GraniteDocling](https://huggingface.co/ibm-granite/granite-docling-258M) handles scanned PDFs without a separate OCR pass. See [the documents part](#modern-unified-extractors--when-one-tool-is-enough) for the decision tree on docling vs per-format tools.
- [**`unstructured`**](https://github.com/Unstructured-IO/unstructured) for general document partitioning into typed blocks (Title, NarrativeText, Table, ListItem, …) — older incumbent, still fine but generally less capable than docling for PDFs.
- [**`layoutparser`**](https://github.com/Layout-Parser/layout-parser) for ML-based region detection if classical methods fail and you need lower-level control than docling exposes.

These are heavier dependencies. Reach for them only when the layout itself is the problem; for table-centric extraction, pdfplumber/camelot remain the default.

## Putting it together — a working extraction skeleton

```python
"""scripts/parsers/agency_2009_sov.py — example parser for a born-digital SoV PDF.

Pattern: a parser module exposes `parse(path: Path) -> pd.DataFrame` returning
a tidy long-form frame conforming to scripts.schema.LONG_COLUMNS, and is
called from scripts/clean.py for the relevant (source, vintage) tuple.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber
import pandas as pd

from scripts.schema import normalize_long


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def parse(path: Path) -> pd.DataFrame:
    """Parse a 2009-vintage Boulder County Statement of Vote PDF."""
    extracted_at = datetime.now(timezone.utc).isoformat()
    file_hash = _sha256(path)
    rows: list[dict] = []

    with pdfplumber.open(path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            tables = page.extract_tables({
                "vertical_strategy": "lines",
                "horizontal_strategy": "text",
                "snap_tolerance": 4,
            })
            for table in tables:
                if not table or len(table) < 2:
                    continue
                header, *body = table
                # ... vintage-specific cleaning here ...
                for body_row in body:
                    rows.append({
                        "source": "boulder_county_sov",
                        "vintage": 2009,
                        "page": page_idx + 1,
                        "source_file_sha256": file_hash,
                        "extracted_at": extracted_at,
                        # ... domain fields per scripts/schema.py ...
                    })

    return normalize_long(pd.DataFrame(rows))
```

A few patterns this skeleton illustrates that you should keep:

- **Hash the source file** on every parse run and emit it on every row (or, more economically, into the per-extract provenance sidecar). This makes downstream errors traceable to the exact input file.
- **`extracted_at` timestamp** — UTC ISO-8601. Required for provenance.
- **`vintage`** as a column — the data was published in a particular year, possibly with that year's quirks.
- **Vintage-specific parsing logic** is fine and expected. Resist the urge to write one parser that handles all years; you'll fight every special case forever. One parser per vintage, with shared helpers in `scripts/parsers/_normalize.py` (regex / string transforms; see [`pipeline.md`](pipeline.md#6-standardization-and-normalization)).
- **Return normalized long-form** at the boundary. The parser's job ends when it has produced a tidy DataFrame; the schema module's job is to validate it.

## Common failure modes — PDF

| Symptom | Likely cause | Fix |
|---|---|---|
| `page.extract_table()` returns `None` | No table detected on page | Crop to the table region; try lattice mode in camelot; if scanned, switch to OCR |
| Rows look right but one column is consistently empty | Column header text overlaps with a ruling; default detection split the column | Pass `explicit_vertical_lines` from inspecting `page.lines` |
| Numbers come out with a digit missing | Cell is very narrow and pdfplumber's text grouping is dropping characters | Reduce `text_tolerance` and `snap_tolerance`; or extract via `page.chars` directly and reconstruct |
| OCR text has "rn" where you expect "m" | Tesseract artifact on small fonts | Increase image resolution to 400 dpi; consider character whitelist if domain is numeric |
| Multi-page table has duplicate header rows in the output | No detection of repeated continuation headers | Detect by exact-match on the first row; drop on continuation pages |
| Two adjacent tables get merged | Default detection treated whitespace between as a row | Crop before extraction, one table at a time |
| `camelot` accuracy reports >95% but the data is wrong anyway | Table structure is irregular; camelot recovered the grid but the cells are mislabeled | Reconcile against authoritative totals (the `reconcile.py` pattern) — accuracy != correctness |

---

# Part 2 — Tabular inputs (XLSX, CSV, Parquet, databases)

A large fraction of public datasets are already tabular when published — XLSX from government portals, CSV from open-data sites, Parquet from data brokers, dumps from SQL databases. They are *technically* structured but often as hostile to reuse as PDFs: panel-format spreadsheets with merged headers, CSVs with inconsistent delimiters across years, schema drift, undocumented sentinel values, encoding bombs. This part covers reading these inputs reliably and surfacing structural problems early.

## Reading XLSX

[`pandas.read_excel`](https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html) (with the `openpyxl` engine for modern `.xlsx` and `xlrd` for legacy `.xls`) is the default. For 80% of well-formed spreadsheets it just works:

```python
import pandas as pd

df = pd.read_excel("data/original/agency/2024.xlsx", sheet_name="Data", header=0)
```

The 20% that doesn't is where civic data liberation lives. The diagnostic order when a spreadsheet doesn't yield cleanly:

### Inspect first, parse second

Before calling `read_excel`, open the file with `openpyxl` and look at the structure:

```python
import openpyxl

wb = openpyxl.load_workbook("data/original/agency/2024.xlsx", data_only=True)
for ws in wb.worksheets:
    print(ws.title, ws.dimensions, ws.max_row, ws.max_column)
    print("merged ranges:", [str(r) for r in ws.merged_cells.ranges][:5])
    # first 5 rows, raw
    for row in ws.iter_rows(min_row=1, max_row=5, values_only=True):
        print(row)
```

Note `data_only=True` — without it, cells containing formulas return the formula string, not the cached value. For pipelines that need the displayed values, `data_only=True` is essential.

What you are looking for:

- **Multiple sheets** — is the data split across years/categories by sheet?
- **Merged cells** — these break naive `read_excel`. The merged value lives in the top-left cell only; the others come back as `NaN`.
- **Header position** — is row 1 the header, or are there 3 rows of title and metadata above it?
- **Multi-row headers** — column meaning is determined by 2+ stacked rows, often combined with merging.
- **Panel format** — the same logical schema is repeated in rectangular blocks down the page (one block per region/year/category).
- **Sentinel values** — empty cells, `"-"`, `"N/A"`, `"."`, `999`, `9999` — what stands in for missing?
- **Trailing junk** — a totals row, footnotes, source citations below the data.

The Boulder County 2008 and 2010 Statement of Vote XLS files are real examples of panel format with merged headers: `precinct-ID ↔ candidate-column` alignment is irregular and required a vintage-specific parser even though the file is "structured."

### Patterns for awkward XLSX

**Multi-row header:**

```python
df = pd.read_excel(path, sheet_name="Data", header=[0, 1])
# columns is now a MultiIndex; flatten:
df.columns = [" / ".join(str(c) for c in tup if pd.notna(c)).strip()
              for tup in df.columns]
```

**Merged header cells forward-fill correctly:**

```python
# After read_excel, the merged value is only in the first column position.
# For a two-row header where row 0 has merged group names:
import pandas as pd

raw = pd.read_excel(path, header=None, nrows=5)
group = raw.iloc[0].ffill()       # forward-fill group across merged span
field = raw.iloc[1]
header = [f"{g} / {f}" for g, f in zip(group, field)]

df = pd.read_excel(path, header=None, skiprows=2)
df.columns = header
```

**Panel format (same schema repeated in blocks):**

The reliable approach is to read the sheet with `header=None` and find the block boundaries programmatically — usually by detecting the rows where a known marker (region name, year header, "Total" row) appears.

```python
raw = pd.read_excel(path, header=None, sheet_name="Data")
block_starts = raw[raw[0].astype(str).str.match(r"^20\d\d$")].index.tolist()
block_starts.append(len(raw))

frames = []
for start, end in zip(block_starts[:-1], block_starts[1:]):
    year = int(raw.iat[start, 0])
    block = raw.iloc[start + 1 : end].copy()
    block.columns = raw.iloc[start + 1].tolist()  # next row is the per-block header
    block = block.iloc[1:]
    block.insert(0, "year", year)
    frames.append(block)

df = pd.concat(frames, ignore_index=True)
```

**Sheet-per-year:**

```python
xls = pd.ExcelFile(path)
frames = []
for sheet in xls.sheet_names:
    if not sheet.isdigit():
        continue
    df = pd.read_excel(xls, sheet_name=sheet)
    df["year"] = int(sheet)
    frames.append(df)
df = pd.concat(frames, ignore_index=True)
```

### Legacy `.xls`

Use `engine="xlrd"`. Note that recent xlrd versions dropped `.xlsx` support; the engine choice in pandas tracks this. For old `.xls` files where the extension lies about the format (Boulder's 2013 SoV is actually XLSX with an `.xls` extension), let pandas auto-detect and pass `engine=None`, or pre-rename the file in `data/original/` with a note.

### Recompute before you trust formulas

When a publisher distributes an XLSX with cells whose values come from formulas, the file stores both the *formula* and the *last-computed value cached when the file was saved*. `pandas.read_excel(..., data_only=True)` reads the cached value — fast, but **stale if the source-of-truth formula and its cached value disagree**. Two ways to find out:

- *The source was edited but not recalculated before save.* Excel and LibreOffice both default to recalc-on-save, but agency exporters built on `openpyxl` (or hand-edited files) often skip this; the cached values silently lag the formula intent.
- *The formula references external workbooks or named ranges that don't resolve in your parser context.* The cached value is the last value seen on the publisher's machine; your environment can't reproduce it.

The general principle: **for any format that separates source-of-truth-expression from cached-value, recompute before parsing.** For XLSX specifically, headless LibreOffice in a `--calc --headless --convert-to xlsx` pass forces a full recalc and writes a normalized file the parser can trust. Document the recompute step in `provenance.csv`'s `extraction_notes` so downstream consumers know which values are publisher-as-saved vs project-recomputed; the two can diverge meaningfully when formulas pull from `INDIRECT()`, `OFFSET()`, or external links.

The same principle applies past XLSX — materialized database views with stale incremental updates, cached query results in BI tools, derived columns in CMS-backed datasets. Any time the file format distinguishes formula from result, the recompute step is part of the parser, not the consumer.

When the formulas themselves are *broken* in the source — visible as `#REF!`, `#DIV/0!`, `#VALUE!`, `#N/A`, `#NAME?` cells — the source has a data-quality problem worth surfacing rather than papering over. See [`pipeline.md#pre-extraction-bulletproofing`](pipeline.md#pre-extraction-bulletproofing) for the "format-native errors are quality signals" check that belongs in the bulletproofing pass.

## Reading CSV

`pandas.read_csv` is well known. Three patterns deserve naming because they trip up almost every project.

### Always declare dtypes for ID-like columns

```python
# WRONG — pandas will parse "07003" as int 7003, losing the leading zero
df = pd.read_csv(path)

# RIGHT — leading zeros preserved
df = pd.read_csv(path, dtype={"precinct_id": str, "zip": str, "fips": str})
```

This is the single most common silent bug in civic data work. Census FIPS codes, ZIP codes, precinct IDs, bill numbers — anything where the leading zero matters — needs explicit string typing.

### Explicit NA tokens

```python
df = pd.read_csv(path, na_values=["", "N/A", "n/a", ".", "--", "NULL", "999", "9999"])
```

Domain sentinels (`-9`, `9999`, `99999`) for missing values are common in government datasets. Document them in `docs/data-dictionary.md` and pass them via `na_values`.

### Encoding

Government CSVs are commonly Latin-1, Windows-1252, or UTF-8 with a BOM. If `pd.read_csv` raises a `UnicodeDecodeError`:

```python
# Try in order
for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
    try:
        df = pd.read_csv(path, encoding=enc)
        break
    except UnicodeDecodeError:
        continue
```

Capture the encoding that worked into provenance — it's a property of the source file that downstream users may need to know.

### Malformed rows

For CSVs with inconsistent column counts per row (e.g., agency exports with unescaped commas in free-text fields):

```python
df = pd.read_csv(path, on_bad_lines="warn")  # log and skip; not silent
# Or, for severe corruption, drop down to the csv module:
import csv
with open(path, newline="") as f:
    reader = csv.reader(f)
    rows = [row for row in reader if len(row) == EXPECTED_NCOLS]
```

If you have to drop rows, **count them and emit the count to the audit log**. Silent loss is the worst kind.

## Reading Parquet

Parquet is the friendly format. `pandas.read_parquet` (with `pyarrow` as the engine) just works:

```python
df = pd.read_parquet("data/original/dataset.parquet")
```

For very large files, read columns or row groups selectively rather than the whole file:

```python
import pyarrow.parquet as pq

# Schema inspection without reading data
schema = pq.read_schema(path)
print(schema)

# Read a subset of columns
df = pd.read_parquet(path, columns=["year", "unitid", "value"])

# Read row groups one at a time
pf = pq.ParquetFile(path)
for batch in pf.iter_batches(batch_size=100_000):
    chunk = batch.to_pandas()
    # process chunk
```

Parquet preserves dtypes — including nullable integers, datetimes, and categoricals — natively. When you write processed data to Parquet, dtype information survives round trips, which is one reason Parquet is the better long-term storage format than CSV for the `data/processed/` directory. Many liberation projects ship both: CSV for accessibility, Parquet for analyst use.

## Reading databases

When the source is a database dump (PostgreSQL, MySQL, SQL Server, SQLite), or a connection string for a live database:

```python
from sqlalchemy import create_engine
import pandas as pd

engine = create_engine("postgresql+psycopg://user:pw@host/db")
df = pd.read_sql("SELECT * FROM elections WHERE year >= 2010", engine)
```

For SQLite files (a common FOIA release format), no server needed:

```python
import sqlite3
import pandas as pd

with sqlite3.connect("data/original/foia/release.sqlite") as conn:
    tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
    df = pd.read_sql("SELECT * FROM voters", conn)
```

For ad-hoc exploration of large database dumps, [`duckdb`](https://duckdb.org/) is excellent: it can query CSV, Parquet, and SQLite files directly without a load step, and uses standard SQL.

```python
import duckdb

# Query a Parquet file directly
df = duckdb.sql(
    "SELECT year, COUNT(*) FROM 'data/original/big.parquet' GROUP BY year"
).df()

# Cross-format join in one query
df = duckdb.sql("""
    SELECT a.*, b.region
    FROM 'data/original/elections.csv' a
    LEFT JOIN 'data/original/precincts.parquet' b USING (precinct_id)
""").df()
```

DuckDB is particularly useful in `scripts/audit.py` for reconciliation queries that would be slow in pandas.

## Choosing the output format for `data/processed/`

A liberation project usually ships processed data in multiple formats. Defaults that work:

| Format | When | Why |
|---|---|---|
| **CSV** | Always | Universal accessibility; opens in any tool; the format readers expect when they download a dataset |
| **Parquet** | Always (alongside CSV) | Preserves dtypes; compact; fast to read for analyst-grade use |
| **JSON / JSONL** | When the data is genuinely nested | Better than flattening for irregularly-structured records |
| **SQLite** | When the dataset has multiple related tables | Single-file relational database; downloadable; queryable with any SQL tool |
| **DuckDB file** | For very large multi-table releases | Columnar storage in a single file; future-friendly |

A common emission pattern:

```python
# scripts/pipeline.py end
df.to_csv("data/processed/elections_tidy.csv", index=False)
df.to_parquet("data/processed/elections_tidy.parquet", index=False)
```

Both files have the same content but different downstream affordances. Document this in the README; many readers don't know what Parquet is and default to CSV.

## Dtype hygiene at the boundary

Whatever the input format, **coerce to canonical dtypes at the boundary of the parser** before returning the DataFrame. Use pandas's nullable dtypes (`Int64`, `Float64`, `string`, `boolean`) rather than the legacy numpy-backed types, because nullable dtypes preserve NA distinctly from 0 / empty-string / NaN:

```python
import pandas as pd

def _coerce(df: pd.DataFrame) -> pd.DataFrame:
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["count"] = pd.to_numeric(df["count"], errors="coerce").astype("Int64")
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce").astype("Float64")
    for col in ("source", "precinct_id", "contest", "candidate"):
        df[col] = df[col].astype("string")
    return df
```

This pays off downstream: pandera schemas validate cleanly, parquet write preserves the types, and analysts joining your data to theirs don't get surprised by `int64` columns silently turning into `float64` because of NAs.

## Common failure modes — tabular

| Symptom | Likely cause | Fix |
|---|---|---|
| Leading zeros stripped from IDs | pandas inferred numeric dtype | Pass `dtype={"id_column": str}` to `read_csv`/`read_excel` |
| `NaN` everywhere in a column after `read_excel` | Cells contain formulas, not values | Pass `data_only=True` to `openpyxl.load_workbook`, or pre-resolve formulas in Excel |
| `UnicodeDecodeError` | Encoding is not UTF-8 | Try `cp1252`, `latin-1`, `utf-8-sig` (BOM) |
| One row has wrong column count | Unescaped delimiter in a text field | `quoting=csv.QUOTE_ALL` if author's choice, or `on_bad_lines="warn"` to log + skip |
| Date column comes back as strings | pandas didn't infer datetime | `parse_dates=["date_col"]` or `pd.to_datetime` after read |
| Numeric column has trailing whitespace | Source has " 123" with leading space | `pd.to_numeric(s.str.strip(), errors="coerce")` |
| Same data, different schemas across years | Mid-period schema change | Vintage-specific parser, harmonize via concept catalog |
| Sentinel value `999` treated as a real number | Domain-specific NA token | Pass `na_values=[999, "999"]` to `read_csv` |

---

# Part 3 — HTML, XML, JSON, and proprietary documents

This part covers structured-document formats that aren't tabular but are usually trying to be: HTML pages with tables (or layout-as-tables), XML feeds and document formats (RSS, agency-specific schemas, GIS metadata), and JSON from APIs or document stores. The job is the same — recover a tidy long-form DataFrame — but the failure modes differ and the tooling is calmer. For *scraping* HTML pages (dynamic content, polite request rates, cached fetches), see [the scraping part](#part-4--web-scraping); this part assumes you already have the document on disk or in a string.

## The document-understanding design space

A liberation project chooses among per-format parsers (the rest of this part) and *unified document extractors* (modern libraries that handle many formats end-to-end). **What civic data actually faces**, framed against the [awesome-document-understanding](https://github.com/tstanislawek/awesome-document-understanding) catalog of document-AI research:

| Document type the source is | Civic examples | Default approach |
|---|---|---|
| **Born-digital structured** — XML, JSON, RSS, EDGAR / USPTO XBRL filings | Agency XML dumps, open-data portals, regulatory filings | `lxml`, `pd.read_xml`, `pd.json_normalize` — sections below |
| **Born-digital narrative HTML** — clean DOM with `<table>` or `<div>` rows | Agency dashboards, FOIA case logs, legislative records | `pandas.read_html` for tables; `selectolax` for layout-as-tables — sections below |
| **Born-digital PDF with text layer** — selectable text, possibly with tables | Statements of vote, annual reports, budget books | `pdfplumber` / `camelot` — see [the PDF part](#part-1--pdf-extraction) |
| **Scanned image PDF** — no text layer | Older Statements of Vote, scanned FOIA responses, faxed records | OCR via `tesseract` + `pdf2image`, or a VLM-based pipeline via `docling` |
| **Visually-rich documents** — layout *bears meaning* (a field's position on the page is part of its identity) | Invoices, applications, structured forms, agency cover sheets | `docling` (layout-aware) or a key-information-extraction model |
| **Mixed-media documents** — PDFs with embedded narrative + tables + footnotes + figures | Comprehensive plans, environmental impact statements, court opinions | `docling` for unified extraction with reading-order preserved; per-component decomposition if you need to attribute each row to a page region |

The awesome-document-understanding repo names additional research problems — *Key Information Extraction*, *Document Layout Analysis*, *Document Question Answering* — that civic-data work occasionally needs. The pragmatic rule: for QA-over-documents (asking natural-language questions of a corpus), step out of this skill's scope and into a RAG / agent layer that reads the *liberated* dataset, not the originals. The skill's job is to produce the clean structured input that QA layers consume.

## Modern unified extractors — when one tool is enough

Two libraries have emerged as the post-2024 defaults for "I want this document parsed end-to-end without writing per-format code":

- **[docling](https://github.com/docling-project/docling)** (LF AI & Data, IBM origin) — best-in-class for *PDF understanding*. Parses page layout, reading order, table structure, code blocks, formulas, image classification. Outputs the unified `DoclingDocument` representation with exports to Markdown, HTML, lossless JSON, and `DocTags` (an LLM-friendly intermediate). Native VLM support via [GraniteDocling](https://huggingface.co/ibm-granite/granite-docling-258M) and other vision-language models. Supports PDF, DOCX, PPTX, XLSX, HTML, images, LaTeX, and several application-specific XML schemas (USPTO patents, JATS articles, XBRL financial reports). Ships an MCP server and integrations with LangChain / LlamaIndex / Haystack / Crew AI. Reach for `docling` when the source has complex layout, embedded code or formulas, multi-column reading order that matters, or when you want a markdown-or-JSON dump suitable for downstream RAG without writing per-format code.

- **[kreuzberg](https://github.com/kreuzberg-dev/kreuzberg)** — polyglot (Python / Rust / Node / WASM / Java / Go / C# / PHP / Ruby / Elixir / R / Dart / Kotlin / Swift) high-throughput extractor across 90+ formats. Rust core with PDFium + Tesseract / PaddleOCR. Includes a *code intelligence* mode with semantic chunking across 300+ programming languages. Faster than docling for bulk extraction at scale, less PDF-understanding depth. Reach for `kreuzberg` when the project is *bulk-extracting* a large heterogeneous corpus, when extraction needs to run from a non-Python service (the polyglot bindings are real), or when the source mix includes a lot of formats that don't fit one specialist tool.

**When to skip both and use per-format tools:** when you need fine control over what comes out — e.g., a specific table on page 7 with the exact column boundaries pinned by reproducible `explicit_vertical_lines`, or a precise XPath against a namespaced XML schema. Per-format tools (pdfplumber, lxml, selectolax) give you that control; docling and kreuzberg trade some of it for breadth. The decision tree:

```
Need one specific table or selector, reproducibly       → per-format tool
Need a markdown dump of a complex layout-rich PDF       → docling
Need bulk extraction across many heterogeneous formats  → kreuzberg
Need a layout-aware embedding for downstream RAG        → docling (export DocTags)
Need scanned-PDF text with no per-source tuning         → docling (VLM pipeline) or kreuzberg
Need structured key/value extraction from forms         → docling + a KIE prompt, or a dedicated KIE model
Need fine control over OCR config per source/vintage    → tesseract directly — see the PDF part
```

The rest of this part covers the per-format tools that the right side of that tree calls into.

## HTML

The web's lingua franca, and a surprisingly common civic-data format: agency reports rendered as HTML pages, FOIA logs in `<table>` form, dashboards backed by data tables, legislative records with one bill per `<div>`. Two paths into HTML, in increasing order of complexity:

### `pandas.read_html` for clean `<table>` elements

The friendliest path. `pd.read_html` walks the document, finds every `<table>` element, and returns a list of DataFrames. It works astonishingly well for well-formed HTML tables and is the right first try whenever the source contains an actual `<table>` tag:

```python
import pandas as pd

tables = pd.read_html("https://example.gov/quarterly-report.html")
# tables is a list of DataFrames — one per <table> on the page
df = tables[0]
```

For local files, pass a path; for HTML strings, pass the string. `pd.read_html` requires `lxml` and `html5lib` for robust parsing; install both.

Common refinements:

- **Multi-row headers:** `pd.read_html(..., header=[0, 1])` for stacked headers; flatten the `MultiIndex` afterward as in the tabular part.
- **Skip rows:** `pd.read_html(..., skiprows=2)` for tables preceded by title rows.
- **Encoding:** `pd.read_html(..., encoding="utf-8")` if the page lies about its encoding via the HTTP header.
- **Specific table:** Use `match=` with a regex to pick the table by a string in its caption or contents: `pd.read_html(url, match="Statement of Vote")`.

What `pd.read_html` does *not* do:

- Recover meaning from CSS-styled layouts (`<div>`-as-tables; tables drawn with `<span>` and `display: grid`). For those, drop to a parser.
- Resolve nested tables sensibly. If a table contains another table in a cell, the result is ugly; reach for `selectolax` or `lxml`.
- Handle JavaScript-rendered content. The HTML must already be in the document; if it's injected by JS, use `playwright` per the scraping part.

### `selectolax` for layout-as-tables and structured non-table content

When the data lives in `<div>` or `<li>` blocks — most modern agency dashboards, most "card grid" layouts — drop to a real HTML parser. [`selectolax`](https://github.com/rushter/selectolax) is the right default: it's an order of magnitude faster than BeautifulSoup, has a CSS-selector API that matches `querySelectorAll`, and handles malformed HTML gracefully.

```python
from selectolax.parser import HTMLParser

tree = HTMLParser(html_string)

rows = []
for card in tree.css("div.report-card"):
    rows.append({
        "title": card.css_first("h3.title").text(strip=True),
        "agency": card.css_first("span.agency").text(strip=True),
        "published": card.css_first("time").attributes.get("datetime"),
        "url": card.css_first("a.download").attributes.get("href"),
    })

df = pd.DataFrame(rows)
```

CSS selectors are usually the right vocabulary for civic-data scraping (developers writing public sites tend to use class names that mirror the data they're displaying — `.report-row`, `.agency-name`, `.fiscal-year`). XPath via `lxml` is the fallback when CSS isn't expressive enough; reach for it for ancestor/sibling queries or attribute predicates beyond CSS's reach.

`BeautifulSoup` is the older, more widely-known alternative. It's fine, just slower; if a project already uses it, no urgency to migrate.

### When the HTML page is really a table-with-CSS-styling

A common government-site pattern: a `<table>` element exists, but each row is split across multiple `<tr>` (one for the visible row, one for an expanded-detail row that JS toggles open), or the visible "rows" are actually `<div>` blocks styled to look like a table. Don't fight the HTML; treat the visible structure as the source of truth and assemble rows from the divs:

```python
rows = []
for row_div in tree.css("div.results-row"):
    cells = [c.text(strip=True) for c in row_div.css("div.cell")]
    if len(cells) == EXPECTED_NCOLS:
        rows.append(cells)
```

The fragility budget here is the page redesign. Commit a saved copy of the page HTML as a `tests/fixtures/` artifact, write a small parser test against it, and the redesign becomes a clear test failure rather than a silent regression.

## XML

XML is calmer than HTML — it's actually structured by design — but the documents tend to be either trivially small (RSS feeds, sitemaps) or alarmingly large (full agency document corpora, GIS metadata catalogs, regulatory filing repositories like SEC EDGAR). The tool choice tracks the size.

### Small documents: `pd.read_xml`

For shallow, well-formed XML with a clear repeated-record structure:

```python
import pandas as pd

df = pd.read_xml("data/original/feed.xml", xpath="//entry")
```

`pd.read_xml` (which uses `lxml` under the hood) returns one row per matched element and one column per child element or attribute. It works well for RSS, Atom, and most agency-flat-XML formats. Pass a custom `xpath` to pick out a specific record-level element.

### Large documents: streaming with `lxml.etree.iterparse`

Loading a multi-gigabyte XML into memory is not an option for many civic sources (SEC filings, full agency dumps). Stream:

```python
from lxml import etree

rows = []
context = etree.iterparse(
    "data/original/big.xml",
    events=("end",),
    tag="record",       # only fire events for <record> elements
)
for _, elem in context:
    rows.append({
        "id": elem.findtext("id"),
        "value": elem.findtext("value"),
        "agency": elem.get("agency"),  # an attribute
    })
    elem.clear()         # free the parsed subtree — critical for memory
    # Also clear preceding siblings to release their memory
    while elem.getprevious() is not None:
        del elem.getparent()[0]
```

The two memory-management calls (`elem.clear()` and the sibling-deletion) are not optional for large files. Without them, `iterparse` is still building the full tree as it goes; you just get a callback per element. With them, memory stays flat.

For very large documents, write rows to disk (CSV, Parquet) in chunks rather than accumulating them in memory:

```python
import pyarrow as pa
import pyarrow.parquet as pq

writer = None
buffer = []
BATCH = 100_000

for _, elem in context:
    buffer.append({"id": elem.findtext("id"), ...})
    elem.clear()
    if len(buffer) >= BATCH:
        table = pa.Table.from_pylist(buffer)
        if writer is None:
            writer = pq.ParquetWriter("data/processed/big.parquet", table.schema)
        writer.write_table(table)
        buffer.clear()

if buffer:
    table = pa.Table.from_pylist(buffer)
    writer.write_table(table)
if writer:
    writer.close()
```

### XPath patterns worth knowing

`lxml` and `pd.read_xml` accept XPath 1.0. A few patterns recur in civic data:

- **All elements anywhere:** `//element-name`
- **Direct children:** `/root/level1/level2`
- **By attribute:** `//report[@status='final']`
- **Text contains:** `//*[contains(text(), 'Total')]`
- **Namespaces:** `//ns:element` with a `namespaces={"ns": "http://example.org"}` argument. Namespace-heavy XML (SEC, NIEM-derived schemas) requires registering namespaces explicitly — there is no shortcut.

If the XML defines namespaces (declared via `xmlns` attributes on the root), every XPath query must address them. The most common failure mode in agency XML is forgetting this and getting empty results from a query that "should work."

## JSON

JSON is the friendliest input format and the most common output from APIs. Three patterns, in increasing order of structural awkwardness.

### Flat JSON arrays

When the source is a list of records with no nesting:

```python
import json
import pandas as pd

with open("data/original/records.json") as f:
    data = json.load(f)

df = pd.DataFrame(data)
```

This is the happy path. Encoding gotchas don't really apply (JSON is UTF-8 by spec; if a file claims otherwise, the publisher made a mistake worth flagging).

### Nested JSON: `pd.json_normalize`

When each record contains nested objects or lists, [`pd.json_normalize`](https://pandas.pydata.org/docs/reference/api/pandas.json_normalize.html) is the workhorse:

```python
data = [
    {
        "id": "001",
        "agency": {"name": "DOE", "code": "DE"},
        "filings": [{"year": 2023, "amount": 1000}, {"year": 2024, "amount": 1200}],
    },
    # ...
]

# Flatten top-level objects with dot notation:
df = pd.json_normalize(data, sep=".")
# Columns: id, agency.name, agency.code, filings (still a list)

# Or, normalize an inner list to its own DataFrame, propagating parent fields:
filings = pd.json_normalize(
    data,
    record_path="filings",
    meta=["id", ["agency", "name"], ["agency", "code"]],
    sep=".",
)
# Columns: year, amount, id, agency.name, agency.code
```

`record_path` is the path into the nested list that becomes one row per inner record; `meta` is the parent fields to propagate. Both accept dot-style strings for shallow nesting and lists-of-strings for deeper nesting (`["agency", "name"]` means the parent's `agency.name`).

Two `json_normalize` gotchas:

- **`max_level`** caps the depth of dotted expansion. Default is None (expand everything); set to `1` if a deeply nested object would explode the column count.
- **Missing inner keys** in some records become NaN columns, which is correct but can surprise you when one row in 10,000 happens to have a key the others don't.

### JSON Lines: stream from disk

For large JSON exports — common in document-store dumps and log archives — the publisher usually emits JSON Lines (one record per line, no top-level array). Pandas reads this directly:

```python
df = pd.read_json("data/original/records.jsonl", lines=True)
```

For very large JSONL, stream:

```python
import json

with open("data/original/records.jsonl") as f:
    for line in f:
        record = json.loads(line)
        # process record incrementally
```

Combined with the Parquet writer pattern from the XML streaming section, JSONL → Parquet conversion is the standard way to handle big civic-data document dumps without ever loading them into memory.

### Pagination from APIs

Most public APIs paginate. Two patterns:

```python
import httpx

# Offset-based pagination
def paginate_offset(base_url, page_size=100):
    offset = 0
    with httpx.Client() as client:
        while True:
            r = client.get(base_url, params={"limit": page_size, "offset": offset})
            r.raise_for_status()
            batch = r.json()["results"]
            if not batch:
                break
            yield from batch
            offset += page_size

# Cursor-based pagination
def paginate_cursor(base_url):
    cursor = None
    with httpx.Client() as client:
        while True:
            params = {"cursor": cursor} if cursor else {}
            r = client.get(base_url, params=params)
            r.raise_for_status()
            data = r.json()
            yield from data["results"]
            cursor = data.get("next_cursor")
            if not cursor:
                break
```

Both should be paired with `requests-cache` (idempotent reruns) and a `tenacity` retry decorator (transient API failures). See the scraping part for the polite-request budget — the same etiquette applies to API consumption.

## Narrative documents in proprietary formats — DOCX, RTF, and the markdown-as-intermediate pattern

Agency reports, FOIA-released drafts, and legislative responses sometimes arrive as `.docx` or `.rtf` rather than PDF or HTML. The pattern that scales across all of them is to **pass through markdown as an intermediate representation** before the parser does anything domain-specific: the markdown form is plain text with predictable structural conventions (headings, lists, tables), the OOXML / RTF byte format is not. Pandoc is the canonical converter; the *principle* (proprietary narrative → markdown → tidy long via the same parser conventions used for HTML extraction) is format-agnostic and survives format-of-the-month churn.

```python
# Conceptual sketch. The point is the two-stage flow, not the specific tool.
import subprocess
from pathlib import Path

src = Path("data/original/agency/2024-report.docx")
md  = src.with_suffix(".md")
subprocess.run(["pandoc", "-f", "docx", "-t", "gfm", "-o", str(md), str(src)], check=True)
# md is now parseable by the same selectolax/regex/headings-and-tables pipeline
# you use for born-digital HTML.
```

Two recurring failure modes worth naming: (1) DOCX-embedded tables that lose row-column structure on conversion — fall back to direct OOXML inspection (the document is a ZIP of XML files; tables are `<w:tbl>` elements with predictable structure) when the markdown shape isn't faithful. (2) RTF documents from older agencies sometimes have legacy encodings (CP1252, Mac Roman) — pandoc's `--from rtf` flag handles the parse but document the encoding in `provenance.csv`.

### Forensic revision history as a first-class signal

DOCX, RTF, and PDF revision streams all carry metadata most consumers ignore — *tracked changes*, *comments*, *revision marks*, *editor identities*, *timestamps of each edit*. For most civic liberation work, the final visible text is the data and the audit trail is noise. But sometimes **the audit trail is the story**: an FOIA release where the redactions tell you what was sensitive; a leaked draft where the tracked changes reveal which clause an agency lawyer fought; an annotated policy document where the comments name the dissenting reviewer.

The generalizable principle: **when a source carries an audit trail in its native format, preserving that trail is part of provenance, not optional metadata.** Two concrete moves:

- **Extract the audit trail alongside the surface text.** For DOCX, that's `<w:ins>`, `<w:del>`, `<w:comment>` elements in the OOXML. For PDF, it's the revision objects in the trailer dictionary. For source repositories (some publishers FOIA-release git history), it's the commit log. The audit trail becomes a sibling artifact under `data/audit/revision_history/<source>/<vintage>.json` — never silently flattened into the processed CSV.
- **Document the existence even when not extracted.** A column in `docs/data-dictionary.md` *Known caveats* noting *"the source DOCX contains 47 tracked-change insertions by 'A. Smith (DOJ)' between 2019-03-14 and 2019-03-21; raw OOXML preserved in `data/audit/revision_history/`"* is enough to let a future researcher follow the lead. The forensic value of revision history compounds over time; the cost of preserving it is small.

The principle generalizes past DOCX: any format that distinguishes *displayed text* from *edit history* (PDF incremental updates, RTF revision marks, OOXML tracked changes, git commit logs, Wikipedia article histories) gets the same treatment.

## Choosing the output format

These document formats lower into the same canonical CSV/Parquet via `scripts/parsers/<source>_<vintage>.py`. The parser's job is to call the right library, recover the rows, return a DataFrame validated against `CanonicalLong` (see `references/data-modeling.md`).

For very large source documents (multi-GB XML, JSON dumps), keep the original on disk in its native format and write only the *processed* output to `data/processed/`. Don't try to commit the original to Git LFS unless the project genuinely needs versioned access to it — for most civic projects, the original is reproducible by re-fetching, and the sha256 in `data/original/manifest.json` plus the URL in `provenance.csv` is sufficient.

## Common failure modes — documents

| Symptom | Likely cause | Fix |
|---|---|---|
| `pd.read_html` returns `[]` | Page has no `<table>` element (often `<div>`-as-table) | Drop to `selectolax` and target the actual structural classes |
| `pd.read_html` returns the table but cells are merged or missing | Multi-row headers or merged cells | Pass `header=[0, 1]` and flatten the MultiIndex; if that fails, drop to `selectolax` |
| XML query returns empty results that should match | Document uses XML namespaces; XPath doesn't address them | Register namespaces explicitly via `namespaces=` argument |
| `iterparse` is using gigabytes of memory | Forgot `elem.clear()` and the sibling-deletion | Add both; verify memory stays flat during the stream |
| `pd.json_normalize` returns one row when you expected many | `record_path` is wrong — pointing at a key rather than the nested list | Inspect with `pd.json_normalize(data)` (no path) first; identify the column that's a list, then re-normalize with that as `record_path` |
| JSON file claims `utf-8` but `json.load` raises `UnicodeDecodeError` | File has a BOM or is actually `utf-8-sig` | `json.loads(Path(p).read_text(encoding="utf-8-sig"))` |
| Selectolax's `css_first` returns `None` and the parser crashes | Selector matches nothing on some pages; assumed every page had the element | Check for `None` before `.text()`; commit a page where the element is missing as a fixture |
| API pagination loops forever | `next_cursor` returned but it's the same as the previous one | Detect repeat cursor and break; also bound by a max-pages safety limit |

---

# Part 4 — Web scraping

This part is for when the data is on a website rather than in a downloadable file. Government dashboards, court records, agency results pages, real-time logs, FOIA case trackers — common civic data sources, many publishing only as HTML.

The structure follows the CU Information Science [INFO4871 *Web Data Science* course](https://github.com/cuinfoscience/INFO4871-Fall2024): ethics first, then archives (often the fastest path involves no live request at all), then protocols (HTTP discipline), then dynamic pages, then government data specifically.

## Scraping in the post-API age

For about a decade the canonical research-data move was *use the platform API*. That era is over. Twitter / X shut down free academic access in 2023; Reddit's API repricing in 2023 ended large-scale academic use; Facebook deprecated CrowdTangle and Pages-Public-Content APIs; YouTube and TikTok tightened to single-digit-percent-of-corpus sampling. The aggregate effect — described in the [INFO4871 *Post-API Age* materials](https://github.com/cuinfoscience/INFO4871-Fall2024/tree/master/Week%2002%20-%20Post-API%20Age) — is that scraping has returned to the methodological mainstream for any research or accountability project that needs corpus-scale public data. The civic-data version of this is even sharper: government APIs were always thin, and the bulk-download alternative was always sparse, so civic projects never left the scraping era.

This shapes the skill's posture:

- **Scraping is the default**, not the fallback. The toolchain decision tree starts with "what's the most polite way to scrape this?" not "is there an API?"
- **The legal frame matters more than it used to.** Without the consent-by-API-key fiction, the project has to defend each scrape on its own merits — robots.txt, ToS, jurisdiction, public-record statutes. The *Ethics and consent* section below is not optional reading.
- **Archives are the first-class fallback.** When a publisher locks down (or just changes their HTML), the Wayback snapshot is often the only retrievable form. Treat Internet Archive as part of the toolchain, not an emergency.
- **Documentation of method is part of the artifact.** Post-API scraping is contestable in ways API access wasn't; documenting the legal basis, the request budget, and the fixture-pinned selectors *in `AGENTS.md`* is what makes a scrape defensible six months later.

## Ethics and consent

Scraping is a request for access made unilaterally. The legitimacy of any individual scraper turns on a handful of judgments — about who the publisher is, what the data is, how the request load compares to ordinary use, and whether there's a non-scraping path the publisher would prefer.

The defaults worth holding to:

- **Read `robots.txt`** and respect `Disallow` entries on the paths you intend to crawl. The file lives at `<host>/robots.txt`. `Disallow` is not legally binding in the US, but ignoring it is the loudest signal possible that the project isn't operating in good faith. The `urllib.robotparser` standard-library module reads it correctly; the [`robotexclusionrulesparser`](https://pypi.org/project/robotexclusionrulesparser/) package handles edge cases better.
- **Identify the project in the `User-Agent`.** A header like `User-Agent: {project_slug}/0.1 (+https://github.com/{user}/{project}; contact@example.org)` lets a publisher figure out who's hitting them. Anonymous scrapers are read as bad-faith by default; identified ones get a polite email instead of a block.
- **Use a request budget** matched to the publisher's evident expectations. Government sites built for human browsing tolerate one request per 1–2 seconds without strain; a sustained 10/sec is hostile. The polite-request pattern below sets this explicitly.
- **Don't scrape what you can download.** Many agency sites publish bulk CSVs or annual ZIP archives in addition to the per-record web interface. Scraping the search results when the same data is available as a bulk download is wasted effort and unnecessary load.
- **Don't republish content you don't have rights to.** Scraping is a method, not a license. Original journalism, court filings, copyrighted reports — the scrape recovers a corpus, but redistribution is governed by the underlying rights regime. For civic data, the relevant test is usually "is this a public record?" — which a public records lawyer can answer for borderline cases.
- **Watch for terms-of-service language** that addresses automated access. Many sites' ToS prohibit scraping in some form. Whether that prohibition is enforceable against a public-interest research project varies by jurisdiction; the safe move is to consult, document the legal basis in `AGENTS.md`, and proceed if the basis is solid.

The [`hiQ Labs v. LinkedIn`](https://en.wikipedia.org/wiki/HiQ_Labs_v._LinkedIn) line of cases established (in US federal court) that scraping publicly-accessible data is generally not a violation of the Computer Fraud and Abuse Act, but specific facts matter. The point is that defensible scraping operates within a documented frame, not on the assumption that public-facing means consequence-free.

## Archives — try them first

Before writing a single line of fetch code, check whether someone else already fetched what you need.

### Wayback Machine

The [Internet Archive's Wayback Machine](https://web.archive.org/) snapshots a large fraction of the public web. For static pages — agency annual reports, archived statements of vote, historical legislative records — there is usually a Wayback snapshot from a usefully recent date. Fetching from Wayback has three advantages: no load on the publisher, stable URLs (the Wayback URL bakes in the snapshot date), and a built-in provenance proof (the snapshot itself is the evidence of what the page contained at that time).

```python
import httpx

# Fetch a specific snapshot of a page
wayback_url = "https://web.archive.org/web/2024/https://example.gov/report.html"
r = httpx.get(wayback_url)
```

The [`waybackpy`](https://pypi.org/project/waybackpy/) package wraps the Wayback CDX API for programmatic snapshot lookup: "give me all snapshots of this URL," "find the snapshot closest to a date," "save this URL now (Save Page Now)."

### Common Crawl, CommonSearch, etc.

For very-large-scale projects (millions of pages), [Common Crawl](https://commoncrawl.org/) publishes monthly snapshots of the public web in WARC format. The processing model is "filter the bulk dump for the URLs that matter," not "crawl yourself." Out of scope for most civic projects but worth knowing about for survey-scale work.

### Project archives and Datasette mirrors

Many civic data projects publish their own archives (BoulderPublicData/Election-Results commits all raw SoV PDFs to the repo; PUDL publishes versioned releases on Zenodo). Before scraping, check whether someone has done the work and made it citable. Crediting an upstream archive is cheaper and more durable than redoing it.

## Protocols — when you do need to fetch

When you do need to make requests, the discipline is the same for every project: identifiable client, polite pacing, idempotent cache, durable retries.

### `httpx` over `requests` (or with `requests-cache`)

[`httpx`](https://www.python-httpx.org/) is the modern Python HTTP client. It's API-compatible with `requests` but supports HTTP/2, async, and timeouts-by-default (a critical safety property — `requests` silently waits forever without `timeout=`). For sync workflows, `httpx.Client()` is a drop-in `requests.Session()` replacement.

A minimal polite scraper:

```python
import time
import httpx
from urllib.robotparser import RobotFileParser

USER_AGENT = "{project_slug}/0.1 (+https://github.com/{user}/{project})"
HEADERS = {"User-Agent": USER_AGENT}
TIMEOUT = httpx.Timeout(30.0, connect=10.0)
DELAY_BETWEEN_REQUESTS_S = 1.5  # adjust per publisher tolerance

# Check robots.txt once
rp = RobotFileParser()
rp.set_url("https://example.gov/robots.txt")
rp.read()


def polite_get(url: str) -> httpx.Response:
    if not rp.can_fetch(USER_AGENT, url):
        raise RuntimeError(f"robots.txt disallows: {url}")
    with httpx.Client(headers=HEADERS, timeout=TIMEOUT) as client:
        r = client.get(url)
        time.sleep(DELAY_BETWEEN_REQUESTS_S)
        return r
```

### `requests-cache` for idempotence

Every civic-data scrape gets developed iteratively, which means re-fetching the same pages dozens of times. [`requests-cache`](https://requests-cache.readthedocs.io/) makes this cheap: the first request hits the network, every subsequent request for the same URL reads from a local SQLite cache. The cache expires after a configurable interval (24 hours is the usual default for development; longer for stable archives, shorter for live data).

```python
import requests_cache
import requests

session = requests_cache.CachedSession(
    cache_name=".requests-cache",
    backend="sqlite",
    expire_after=86400,  # 24 hours
    cache_control=True,   # honor Cache-Control headers from the server
)
session.headers["User-Agent"] = USER_AGENT
```

The same pattern works with `httpx` via [`hishel`](https://hishel.com/), a transport-level cache.

### `tenacity` for retries

Transient failures (502, 503, connection reset, DNS hiccup) are the norm in any long-running scrape. [`tenacity`](https://tenacity.readthedocs.io/) handles them with exponential backoff:

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    reraise=True,
)
def fetch_with_retry(url: str) -> httpx.Response:
    r = session.get(url)
    r.raise_for_status()
    return r
```

Five attempts with exponential backoff (2, 4, 8, 16, 30 seconds) covers nearly all transient failures without becoming a pest. After five failures, the page is genuinely broken or being rate-limited; raise and let the audit catch it.

### Idempotent fetch pattern

The full `scripts/fetch.py` pattern that combines all four — robots.txt, polite delay, cache, retry — produces an `idempotent fetcher`: running it twice in a row produces identical state. This is the property `scripts/pipeline.py` depends on when running `discover → fetch → clean` after a no-change interval.

## Dynamic pages

When the data isn't in the HTML response — it's loaded by JavaScript after the page renders — a browser-driving tool is required. The default is [Playwright](https://playwright.dev/python/).

### When to reach for Playwright

Signs the page is dynamic:

- View-source on the page doesn't contain the data you see in the rendered view.
- The page does an XHR/fetch to a JSON endpoint after load and renders the response.
- A login or session cookie is required and the cookie is set via JavaScript.
- The data is in a JavaScript framework's state (React, Vue) and only realized in the DOM after render.

For all of these, the cheapest fix is often **not Playwright** — it's finding the JSON endpoint the page itself is calling. Open the browser's DevTools, watch the Network tab while the page loads, identify the XHR request that returns the data, and call that endpoint directly with `httpx`. This is faster, cheaper, and more stable than rendering the full page.

Reach for Playwright only when:

- The endpoint requires a session token that can only be obtained by clicking through the UI.
- The data is rendered from a complex JS state machine that doesn't surface a clean endpoint.
- The page uses canvas or another non-DOM rendering target.

### Minimal Playwright pattern

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent=USER_AGENT)
    page = context.new_page()
    page.goto("https://example.gov/dashboard")
    page.wait_for_selector("table.results", state="visible")
    page.wait_for_load_state("networkidle")  # ensure XHRs have settled
    html = page.content()
    browser.close()

# Now parse `html` with selectolax or pandas.read_html
```

The two `wait_for_*` calls are not optional: `wait_for_selector` waits for the data-bearing element to exist; `wait_for_load_state("networkidle")` waits for in-flight XHRs to complete. Skipping either gives you the empty pre-render HTML.

For sites that paginate via JS interaction (Next button, infinite scroll), Playwright lets you script the interaction:

```python
for _ in range(MAX_PAGES):
    rows = page.query_selector_all("tr.data-row")
    # extract rows here
    next_btn = page.query_selector("button.next:not([disabled])")
    if next_btn is None:
        break
    next_btn.click()
    page.wait_for_load_state("networkidle")
```

The fragility budget for browser-driven scraping is high — small UI changes break the script. The mitigation is the same as for HTML parsing: commit a saved trace (Playwright's [trace viewer](https://playwright.dev/python/docs/trace-viewer) is excellent for this) as a fixture, and add a test that exercises the interaction sequence.

### Selenium

[Selenium](https://www.selenium.dev/) predates Playwright and is still widely used. For new projects, Playwright is the better default: faster, more reliable auto-wait, better debugging tools. If a project already uses Selenium, no urgency to migrate.

## Government data specifically

A handful of patterns recur often enough in civic-data scraping to be worth naming.

### Bulk downloads first

Many agencies publish per-record search interfaces alongside annual bulk dumps. The bulk dumps are almost always preferable: faster, more complete, less load on the publisher, and usually the same format every year (so parsers are stable). The Secretary of State's annual election archive ZIP, the agency's annual report bulk PDF set, the bureau's quarterly CSV release — find these first; scrape the search interface only for data that genuinely isn't in the bulk releases.

### CORA / FOIA as a scraping alternative

For records not posted online, the records request is often faster than building a scraper for a hostile interface. [MuckRock](https://www.muckrock.com/) tracks request status across agencies; Colorado has [CORA](https://www.coloradoattorneygeneral.gov/the-colorado-open-records-act/) for state and local records. A well-targeted records request returns a structured dataset directly; the alternative is scraping an interface that's likely undocumented and may change without notice.

When a project does both (FOIA for the historical period, scraping for ongoing refreshes), document both paths in `AGENTS.md`.

### API discovery

Many government sites publish data through APIs without advertising them prominently:

- **`/api/v1/...`** or `/data/api/` paths.
- A `data.json` at the root of a site (the [Project Open Data](https://project-open-data.cio.gov/) standard, mandated for US federal agencies).
- A CKAN portal (`<host>/api/3/action/...` patterns) — used by many state and city open-data sites.
- A Socrata portal (`<host>/resource/<id>.json`) — used by many municipal data sites.

A quick scan for these before writing any HTML scraper is worth a few minutes; using the API is more polite, more stable, and often returns better-typed data than the HTML version.

### Session cookies and CSRF tokens

Search interfaces backed by ASP.NET (still common in court and county records systems) often require a session cookie and a hidden form token (`__VIEWSTATE`, `__EVENTVALIDATION`) on every request. The flow:

1. GET the initial page; extract `__VIEWSTATE` and `__EVENTVALIDATION` from the HTML.
2. POST to the same URL with the form data plus the extracted tokens.
3. The response is the next page (which has new `__VIEWSTATE` for the next request).

```python
import httpx
from selectolax.parser import HTMLParser

client = httpx.Client(headers={"User-Agent": USER_AGENT})
r = client.get("https://court.example.gov/search")
tree = HTMLParser(r.text)
viewstate = tree.css_first("input[name='__VIEWSTATE']").attributes["value"]
event_val = tree.css_first("input[name='__EVENTVALIDATION']").attributes["value"]

r = client.post(
    "https://court.example.gov/search",
    data={
        "__VIEWSTATE": viewstate,
        "__EVENTVALIDATION": event_val,
        "search_field": "smith",
    },
)
```

These interfaces are fragile and tedious; if a records request would yield the same data, prefer that.

## Discovery as scraping's calmer cousin

`scripts/discover.py` (see `references/pipeline.md`) is fundamentally a scraping operation, but a very small one — just enough HTTP to ask "what's available?" without downloading anything. Treat it with the same discipline: identifiable User-Agent, polite delay, cached fetch, retries. The two operations share most of their infrastructure, which is why `fetch.py` and `discover.py` both end up importing from the same `_http.py` helper module in mature projects.

## Common failure modes — scraping

| Symptom | Likely cause | Fix |
|---|---|---|
| `httpx.ConnectError` after some delay | DNS or TLS handshake failing intermittently | Wrap in `tenacity` retry; raise the retry count |
| 403 on every request | Default User-Agent matches a known bot pattern | Set an identifiable `User-Agent` with project URL |
| Pagination loops forever | "Next" link always present but returns the same page | Detect repeat by URL or by content hash; break |
| Playwright timeout on `wait_for_selector` | Page renders the element but uses a different selector across vintages | Inspect with `page.pause()` in dev; commit fixtures of each layout variant |
| Cached responses return stale data | `requests-cache` expiration too long; site updated | Lower `expire_after`; clear cache for development of a specific source |
| Scraped table looks right but every numeric cell is the same value | The selector matches a sibling element instead of the row's value | Inspect with DevTools; tighten the selector |
| Long scrape blocked midway by Cloudflare | The publisher uses Cloudflare bot protection | Slow the request rate further; consider whether a records request is preferable |
| Site changed and parser fails silently | UI redesign | Commit the saved HTML as a fixture; the parser test catches the next breakage |

---

## What to write in the AGENTS.md

**PDF:**

- Which tool (pdfplumber / camelot / tesseract) for which source × vintage, and the classifier fact that drove the choice.
- Any non-default configuration — table_settings, OCR PSM, character whitelist.
- Per-vintage quirks (merged cells, footnoted rows, multi-page table headers, OCR-degraded years).

**Tabular:**

- File format(s), including any cases where the extension lies about the actual format.
- Encoding — often a hidden property of the source.
- Sentinel values used for missing data.
- Panel format / multi-row headers / merged cells, with the per-vintage strategy.
- Dtype expectations for ID-like columns (FIPS, ZIP, precinct ID, agency code).

**Documents:**

- **Format and the load-bearing selector** (HTML) or root element / repeated record (XML, JSON).
- **Encoding** (HTML/JSON) and **namespace declarations** (XML) — the kind of detail that's invisible until it breaks.
- **API pagination style** — offset vs cursor, page size, rate limit, link to publisher's API docs if any.
- **Structural fragility** — which selectors / paths are load-bearing, where the pinning fixture lives.
- **Streaming requirements** — note when a parser uses `iterparse` or chunked JSONL because the document is too large to load.

**Scraping:**

- **Scraped vs downloaded** — which parts of the data come from a live scrape vs a bulk-download or records request.
- **Ethical frame** — rate limit, User-Agent, robots.txt status, legal basis for the underlying records (CORA / FOIA / public-record statute).
- **Auth / session** — cookie or token flow, expiry.
- **Dynamic vs static** — `httpx` + parser, or Playwright (with reason).
- **Fragility points** — the load-bearing selector(s) and the saved-page fixture that pins them.
- **Backup paths** — Wayback snapshot URL pattern, records-request fallback.
