# Extract: images, OCR, and computer vision

When the input is image-based rather than a text layer — scanned PDFs, photographed documents, image files (PNG/TIFF/JPG), maps, exhibits, signatures — extraction can't read characters off the page; it has to recover them. The path is **rasterize → preprocess → OCR (or a vision model) → handle the output as text**. Quality varies dramatically by document and is dominated by input image quality, so preprocessing matters more than the engine choice. This is the **Level 0** reference for the image/OCR/CV branch; the born-digital PDF path is in [`extract-pdf.md`](extract-pdf.md), and multi-format unified extractors (docling/kreuzberg) are in [`extract-documents.md`](extract-documents.md#modern-unified-extractors--when-one-tool-is-enough).

## When the input is image-based

Run the same triage you'd run on any PDF: is there a usable text layer? Open the file in a viewer and try to **select and copy text** from it. If you get the content back, you have a born-digital document — use the path in [`extract-pdf.md`](extract-pdf.md). If you get nothing or garbled glyphs, or the input is a raster image file (PNG/TIFF/JPG) to begin with, the text doesn't exist as characters yet and you're here: rasterize each page (if it's a PDF), preprocess, and OCR.

## OCR engines — tesseract and its alternatives

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

OCR'd output should always be **flagged as such in provenance** (e.g., `extraction_quality = "ocr_tesseract"` in the provenance sidecar) so downstream users can apply extra skepticism.

### When tesseract isn't enough

Tesseract remains the default — bundled in every Linux distro, 100+ language packs, tunes well via PSM and character-whitelist flags. But several modern OCR engines outperform it on specific failure modes, in this order:

| If tesseract is failing on… | Try |
|---|---|
| **Degraded or low-resolution scans** where preprocessing isn't enough | [**PaddleOCR**](https://github.com/PaddlePaddle/PaddleOCR) — production-grade engine with 80+ languages; reliably better than tesseract on noisy or rotated scans. Heavier install (PaddlePaddle wheel) but the accuracy bump is usually worth it. Also the backend kreuzberg uses by default. |
| **Mixed printed + handwritten** or **complex layouts where reading order matters** | [**Surya**](https://github.com/VikParuchuri/surya) — newer (VikParuchuri); does OCR + line / paragraph / reading-order detection in one pass. Pure-Python install, fast on CPU. Strong on multi-column documents. |
| **High-throughput batch processing** where install simplicity beats peak accuracy | [**EasyOCR**](https://github.com/JaidedAI/EasyOCR) — `pip install easyocr` and you have a working multi-language OCR. Less tunable than tesseract, but the lowest-friction option when you just need text out of a thousand scans. |
| **Production deployment with a clean Python API** for documents (not just images) | [**docTR**](https://github.com/mindee/doctr) — explicit "alternative for Tesseract" from Mindee; ships text-detection + text-recognition models with a higher-level document API than tesseract exposes. Worth it for projects building a sustained OCR service. |

Two-tool combinations also help: **[`OCRmyPDF`](https://github.com/jbarlow83/OCRmyPDF) + pdfplumber** is the canonical pattern for a scanned-PDF corpus that needs to be searched *and* extracted. OCRmyPDF wraps tesseract (or any tool above) to add a text layer *to the PDF in place* — the scanned PDF becomes a born-digital PDF that [`pdfplumber`](extract-pdf.md) can then parse normally. This collapses the otherwise-awkward "OCR the page, save text separately, re-attribute text to coordinates" three-step into one. The original is preserved (OCRmyPDF writes a sidecar `.ocr.pdf`), so the immutable-originals discipline holds.

Update `extraction_quality` in `provenance.csv` to name the engine used (`ocr_paddleocr`, `ocr_surya`, `ocrmypdf`, etc.) — downstream users apply different skepticism levels depending on which engine produced the text.

## Image preprocessing for OCR

Image quality at the input is the single biggest factor in OCR output quality. Standard fixes:

- **Resolution.** 300 dpi minimum, 400 dpi for small fonts. Below 200 dpi you will fight Tesseract for every digit.
- **Deskew.** Even a 1° rotation degrades accuracy noticeably. Use `cv2.minAreaRect` on the document's bounding contour or [`deskew`](https://pypi.org/project/deskew/).
- **Binarize.** `cv2.threshold` with Otsu's method or `cv2.adaptiveThreshold` for uneven lighting.
- **Despeckle.** A median filter (`cv2.medianBlur`) before thresholding helps with scanner noise.
- **Crop to content.** Margins waste OCR effort and confuse the layout analyzer.

## OCR gotchas

- **Numbers vs letters confusion.** "0" vs "O", "1" vs "I" vs "l". For numeric tables, restrict the character set with `--psm 6 -c tessedit_char_whitelist=0123456789.,-`.
- **PSM (Page Segmentation Mode) matters.** The default (`--psm 3`, "auto") is often wrong for tables. Try `--psm 6` (assume a single uniform block of text) or `--psm 11` (sparse text) when default OCR is fragmenting rows.
- **Language packs.** English is bundled; other languages require `tesseract-ocr-<lang>` system packages. If the document is multilingual, pass `lang="eng+spa"`.
- **Training a custom model** is rarely worth it for civic data; the [tesseract training guide](https://github.com/neiths/tesseract_training_guide) documents the path if you do need it.

## Extracting embedded images as evidence

PDFs aren't always text-with-tables. Court filings, incident reports, environmental impact assessments, and FOIA-released archives often carry images that *are* the evidence — exhibits, photographs, scanned signatures, maps. The principle: **if the image is referenced by the surface text, the image is part of the dataset**, not optional ephemera. Extract it, hash it, store it alongside the text under `data/original/<source>/<vintage>/_images/<page>-<index>.<ext>`, and add a `has_image` column or a sidecar `images.csv` keyed on `(source, vintage, page)` so a downstream reader can join from a processed-CSV row back to the exhibit it cites.

```python
# pdfplumber exposes pdf.pages[N].images — bounding boxes + the raw bytes
# behind each embedded image. The same image objects are also reachable
# from the PDF's resource dictionary via pdfminer.six or pypdf for projects
# that need image-format-preserving extraction.
```

Update `provenance.csv` with an `images_extracted` count per (source, vintage) so the audit can flag the drift case where a refresh suddenly stops emitting images (usually a parser regression or a publisher format change).

## Layout analysis and computer vision

For documents where the structure is not just tables but mixed layout (figures, multi-column text, sidebars), reach for:

- [**`docling`**](https://github.com/docling-project/docling) — the modern default for PDF understanding with mixed layout. Parses reading order, table structure, code blocks, formulas, and image classification into a unified `DoclingDocument` representation with Markdown / HTML / lossless JSON / DocTags exports. Native VLM support via [GraniteDocling](https://huggingface.co/ibm-granite/granite-docling-258M) handles scanned PDFs without a separate OCR pass. See [the documents part](extract-documents.md#modern-unified-extractors--when-one-tool-is-enough) for the decision tree on docling vs per-format tools.
- [**`unstructured`**](https://github.com/Unstructured-IO/unstructured) for general document partitioning into typed blocks (Title, NarrativeText, Table, ListItem, …) — older incumbent, still fine but generally less capable than docling for PDFs.
- [**`layoutparser`**](https://github.com/Layout-Parser/layout-parser) for ML-based region detection if classical methods fail and you need lower-level control than docling exposes.

These are heavier dependencies. Reach for them only when the layout itself is the problem; for table-centric extraction, pdfplumber/camelot remain the default.

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| OCR text has "rn" where you expect "m" | Tesseract artifact on small fonts | Increase image resolution to 400 dpi; consider character whitelist if domain is numeric |
| OCR drops or mangles digits in numeric tables | Low resolution, or "0"/"O" and "1"/"I"/"l" confusion | Raise dpi to 400; restrict with `tessedit_char_whitelist`; try PaddleOCR/Surya |
| OCR rows are fragmented or out of order | Wrong PSM, or skew/multi-column layout | Try `--psm 6`/`--psm 11`; deskew first; use Surya for reading order |

---

## What to write in the AGENTS.md

- Which OCR engine (tesseract / PaddleOCR / Surya / EasyOCR / docTR) for which source × vintage, and the failure mode that drove the choice.
- Any preprocessing applied — resolution/dpi, deskew, binarize, despeckle, crop.
- Non-default OCR configuration — PSM mode and character whitelist.
- The `extraction_quality` values used (`ocr_tesseract`, `ocr_paddleocr`, `ocr_surya`, `ocrmypdf`, …) so downstream users know which engine produced each batch.
- Whether OCRmyPDF was used to add a text layer in place (and that the original scanned PDF is preserved as the immutable source).
