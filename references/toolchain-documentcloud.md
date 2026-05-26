# Toolchain: DocumentCloud

The **source-document** layer of a liberation project's publishing surfaces. The other three: [`toolchain-datasette.md`](toolchain-datasette.md) for the queryable data interface; [`toolchain-quarto.md`](toolchain-quarto.md) for the documentation site; [`toolchain-lfs.md`](toolchain-lfs.md) for bulk file distribution.

[DocumentCloud](https://www.documentcloud.org/) (a MuckRock project, descended from the *New York Times* and *ProPublica* journalism platform) is the publishing endpoint for the *source documents themselves* — the PDFs, scanned originals, FOIA responses, and agency reports that the processed CSV was extracted from. Hosting them on DocumentCloud rather than dumping them in LFS gives readers a real reading UI, automatic OCR, page-level permalinks, text-selection permalinks, annotations, embed iframes, and full-text search across the corpus. It's the difference between *the data is reproducible* and *the data is accountable*.

## When to reach for DocumentCloud

| If the source artifacts are… | And readers will… | Then |
|---|---|---|
| Born-digital PDFs in `data/original/` (statements of vote, budget books, annual reports) | Want to verify a number by looking at the original page it came from | **Yes** — DocumentCloud's page-permalink + text-selection-permalink is the affordance |
| Scanned PDFs that need OCR before they're searchable | Want to search the corpus by phrase, not just by filename | **Yes** — DocumentCloud OCRs every upload and exposes the text via search |
| FOIA responses (often hundreds of documents per request) | Want a single browsable, citable corpus | **Yes** — `Project` model groups documents; the project has its own URL |
| Multi-gigabyte raw archives, ZIPs, parquet files | Want a tarball download, not a reader | **No** — use [`toolchain-lfs.md`](toolchain-lfs.md) or GitHub Releases |
| Already-tidy CSV / Parquet (no originals worth showing) | Want to query the data | **No** — use [`toolchain-datasette.md`](toolchain-datasette.md) |
| Source documents in a *sensitive* corpus (whistleblower drops, draft FOIAs, redaction-in-progress) | Need controlled access | DocumentCloud's `private` and `organization` access levels handle this; LFS doesn't have access control beyond the repo |

The rule: **if a reader of the published Datasette / Quarto pages might want to click through to the source PDF, the source PDF should be on DocumentCloud.** If not, LFS or Releases.

## Install and authenticate

```bash
uv add python-documentcloud
```

`python-documentcloud` (the [official MuckRock wrapper](https://github.com/MuckRock/python-documentcloud)) is the canonical client. The library reads anonymously without credentials (public documents only) and authenticated with a DocumentCloud account:

```python
from documentcloud import DocumentCloud

client_anon = DocumentCloud()                          # public read only
client = DocumentCloud(USERNAME, PASSWORD)             # upload + read private
```

For projects, register a *Squarelet* account (the MuckRock auth service) and store the credentials in `.env` alongside the project's other secrets. **Never commit credentials**; the `.env` template in the project template already excludes them.

## Upload patterns

The four upload modes cover every civic-data ingestion shape:

```python
# 1. Single document from local path
doc = client.documents.upload(
    "data/original/boulder_county_sov/2024/sov-2024-general.pdf",
    title="Boulder County Statement of Vote, 2024 General",
    source="Boulder County Clerk and Recorder",
    project=PROJECT_ID,
    access="public",
)

# 2. Multiple URLs (DocumentCloud fetches them — useful when the source
#    publisher hosts the artifact and you don't want to mirror)
docs = client.documents.upload_urls([
    "https://bouldercounty.gov/elections/results/2024-general.pdf",
    "https://bouldercounty.gov/elections/results/2024-primary.pdf",
], project=PROJECT_ID, access="public")

# 3. Directory of PDFs at once (recommended for bulk vintages)
docs = client.documents.upload_directory(
    "data/original/boulder_county_sov/2024/",
    project=PROJECT_ID,
)

# 4. Non-PDF source files (DOCX, TXT, XLSX) — pass extension explicitly
doc = client.documents.upload(
    "data/original/agency_response/foia_log.xlsx",
    original_extension="xlsx",
)
```

Uploads enter a server-side processing queue. Documents are not viewable, searchable, or embeddable until processing completes — poll the document's status field if your pipeline needs to wait synchronously:

```python
import time
while doc.status != "success":
    time.sleep(5)
    doc = client.documents.get(doc.id)
```

For bulk corpora (more than a few hundred documents), use the [`pneumatic`](https://github.com/anthonydb/pneumatic) or [`dcupload`](https://github.com/onyxfish/dcupload) bulk-upload CLIs rather than scripting around `upload()` directly — they handle retry, deduplication, and rate-limit backoff that the basic library leaves to the caller.

## Projects — organizing the corpus

Every uploaded document should belong to a **project**. A project has its own canonical URL (`documentcloud.org/projects/<id>`), and the project page is where readers land when following an "all source documents" link from the Quarto site or Datasette metadata.

```python
project = client.projects.create(
    title="Boulder County Election Results — Source Documents",
    description="Statements of vote and underlying ballots, 2004–present. "
                "Liberated by github.com/owner/boulder-elections.",
)
project.document_list = docs   # attach uploaded documents
project.put()
```

The project structure should mirror the source registry in `scripts/config.py::SOURCES` — one DocumentCloud project per source registry slug, or one project per (source × vintage) for long-running series. Document this convention in `AGENTS.md` under *Deployment surface*.

## Embedding in the Quarto site

DocumentCloud's main reader-facing payoff is the **embed iframe** — every document gets HTML that drops cleanly into a Quarto page:

```html
<iframe src="https://embed.documentcloud.org/documents/{ID}/?embed=1"
        width="100%" height="600" frameborder="0">
</iframe>
```

The library exposes this directly:

```python
doc.embed_code()       # full <iframe> HTML
doc.canonical_url      # plain link to the reader UI
```

The plain full-document embed is the right default, but the embed URL accepts query parameters that change what the reader lands on — and a methodology page is *much* more legible when the embed opens on the exact page being discussed rather than the document's title page. Three useful variants:

```html
<!-- Open on a specific page -->
<iframe src="https://embed.documentcloud.org/documents/{ID}/?embed=1&page=17"
        width="100%" height="600"></iframe>

<!-- Open on a specific note (annotation) by note ID -->
<iframe src="https://embed.documentcloud.org/documents/{ID}/annotations/{NOTE_ID}/?embed=1"
        width="100%" height="600"></iframe>

<!-- Page-image only (no reader UI) — useful for a static thumbnail next to body text -->
<img src="https://embed.documentcloud.org/documents/{ID}/pages/17-large.gif"
     alt="SoV 2024 page 17 — Boulder County precinct totals">
```

The page-anchored iframe is the workhorse. Combine with a permalinked text-selection URL — the DocumentCloud reader supports `?selection={start}-{end}` URL fragments that highlight a text range — and a methodology paragraph can deep-link into the exact paragraph of the original that the processed CSV's column was derived from.

Inside a `.qmd` file, the canonical pattern is to keep iframe HTML in per-document partial files under `docs/_includes/` and `{{< include >}}` them from the prose pages, so the same embed can appear in multiple places (methodology page, vintage changelog entry, data-dictionary caveat) without copy-pasting the iframe markup. The partial files are tiny — typically 3-line HTML stubs — but factoring them out keeps the `.qmd` source readable:

```markdown
## How the 2024 results were extracted

The published Statement of Vote ([source]({{< var sov_2024_url >}})) is
a 412-page PDF. Pages 17–143 carry the precinct-by-contest tables that
became `data/processed/elections.csv`.

{{< include _includes/sov_2024_pages_17_to_143_embed.html >}}

The vote-totals row at the bottom of every precinct block is the
authoritative figure `reconcile.py` verifies against.
```

For a *comparison* layout — two source vintages side by side on the same Quarto page — Quarto's column layout works directly with iframes:

```markdown
:::: {.columns}
::: {.column width="50%"}
**2020 General**
{{< include _includes/sov_2020_embed.html >}}
:::
::: {.column width="50%"}
**2024 General**
{{< include _includes/sov_2024_embed.html >}}
:::
::::
```

Two practical notes on rendering: (1) Iframes are *not* captured by Quarto's `freeze: auto` cache — every render fetches DocumentCloud live. That's the right default (the embed reflects the current state of the source document) but it means the rendered site will have broken embeds if the network is down at render time or if the document has been deleted from DocumentCloud. Pin the document IDs in `_quarto.yml`'s `var` block or in a per-source YAML so a typo doesn't silently break the build. (2) For PDF output of the Quarto site, iframes don't render — replace them at PDF-build time with the page-image variants (the `pages/N-large.gif` URLs) plus a permalink to the live reader.

The LFS-cannot-serve-from-Pages constraint (see [`toolchain-lfs.md`](toolchain-lfs.md)) is what makes DocumentCloud structurally important here: the Quarto site can embed DocumentCloud iframes without serving the PDFs from `gh-pages`. The methodology page describes the data; the iframe shows the data; the underlying file lives on a third host that handles the OCR and the reader UI for free.

## Splitting large documents before upload

DocumentCloud accepts large PDFs but its sweet spot is documents in the ~50-page range. Multi-hundred-page PDFs (the typical scale of a county Comprehensive Plan, a multi-year fiscal report, or a complete EIS) hit three real problems: (1) server-side OCR takes minutes-to-hours and occasionally fails silently; (2) the reader UI gets sluggish over ~500 pages, especially on mobile; (3) the embed's page-anchored URL is less useful when the relevant page is one of two thousand. Splitting upstream — before upload — solves all three.

Splitting is a *parser-side* concern, not a DocumentCloud concern. The immutable-originals discipline (`data/original/` is write-once) means splits live as derived files. Two conventions work:

- **Split-at-upload**, no on-disk derivative: the parser reads the whole original, slices into per-section page ranges in memory, and uploads each slice as a separate DocumentCloud document. The original PDF stays whole on disk; no `data/original/` mutation. Simplest; right default for most projects.
- **Split-and-persist**, derivative on disk: derived splits live under `data/original/<source>/<vintage>/_splits/` (or `data/processed/_splits/` if you prefer the derivative-bucket framing). Each split file gets its own entry in `manifest.json` with a `parent_sha256` field pointing back at the unsplit original. Heavier; useful when splits get cited or re-used independently of the parent.

For Python-native splitting, [`pypdf`](https://github.com/py-pdf/pypdf) is the canonical library (formerly PyPDF2):

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("data/original/boulder/sov-2024-general.pdf")
splits = [
    ("sov-2024-general_summary",          0, 16),    # cover + summary
    ("sov-2024-general_precincts",       16, 143),   # the precinct tables
    ("sov-2024-general_recount_appendix", 143, 412), # appendices
]
for name, start, end in splits:
    writer = PdfWriter()
    for i in range(start, end):
        writer.add_page(reader.pages[i])
    with open(f"/tmp/{name}.pdf", "wb") as f:
        writer.write(f)
```

For command-line splitting in shell pipelines, [`qpdf`](https://github.com/qpdf/qpdf) (`qpdf input.pdf --pages . 17-143 -- output.pdf`) and [`pdftk`](https://www.pdflabs.com/tools/pdftk-the-pdf-toolkit/) (`pdftk input.pdf cat 17-143 output output.pdf`) are the durable choices — pick whichever is already in the project's container or system image. Both handle multi-gigabyte PDFs without loading them into memory.

The harder question is *where* to split. Three strategies, in order of robustness:

- **By structural marker** (most robust). Use `pdfplumber` to scan the PDF for a known section boundary — "PRECINCT REPORT" header, a fiscal-year-divider page, a contest-name change — and split at those page indices. The split logic lives in `scripts/parsers/_split.py` (or inline in the parser); the markers belong in the parser's docstring or `AGENTS.md` so a future contributor knows why the page boundaries are what they are. Vintage-specific: different years may have moved the marker.
- **By section in a table of contents** (when the source has a parseable ToC). `pypdf` exposes `reader.outline` — if the publisher included PDF bookmarks, those are the right split points and they survive across vintages if the publisher's template stayed put.
- **By fixed page count** (last resort). 100-page chunks with a 5-page overlap so context isn't lost at the boundary. Easy to script, terrible for citation — the chunks have no semantic meaning and a reader following a permalink lands on an arbitrary mid-document page.

Whichever strategy, the split chunks need to carry their lineage in provenance so the chain of custody back to the original survives. Conventions:

- **Naming.** `<original-stem>_<descriptor>.pdf` (`sov-2024-general_precincts.pdf`) when splitting by marker; `<original-stem>_pages-N-to-M.pdf` when splitting by page range. Names are stable across re-runs so the upload step's dedup-by-sha256 stays reliable.
- **`provenance.csv` extensions.** Add `parent_sha256` (the unsplit original's hash), `parent_documentcloud_url` (a link to the unsplit version if it's also on DocumentCloud), and `page_range` (`17-143`) columns. The processed-CSV-row-to-source-page chain becomes: row → `(source, vintage)` → provenance entry → split DocumentCloud URL → page within the split.
- **`AGENTS.md` *Deployment surface* note.** Document the split convention per source — "Boulder SoV PDFs split into summary / precincts / appendices; the precincts split is the citable one; the appendices split is uploaded as `organization` because the recount narratives reference jurors by name" — so the access-level and citation choices stay legible.

A split is not a transformation in the parser sense — it doesn't change pixels or text. It's a packaging decision at the *publish* boundary. The split's content is the original's content; the value is purely that readers can find what they need without scrolling through 412 pages. Treat splitting as part of the upload step, not the cleaning step.

## Access levels and provenance chain-of-custody

DocumentCloud has three access levels:

| Level | Who sees it | When to use |
|---|---|---|
| `public` | Anyone (search-indexed) | Default for liberated public-record corpora |
| `organization` | Members of your DocumentCloud organization | In-progress liberation; documents from a pending FOIA that aren't yet ready to publish |
| `private` | Only the uploader | Sensitive material in early review; one-off testing |

The access decision is a **governance decision** (see [`project-template.md#governance`](project-template.md#governance)) and should be documented per source in `provenance.csv`. Add a `documentcloud_url` and `documentcloud_access` column to the provenance schema once DocumentCloud is in use; this keeps the chain of custody traceable: `processed CSV row → (source, vintage) → provenance.csv entry → DocumentCloud project URL → individual document URL → original page`.

The `source_url` column in `provenance.csv` should remain the *publisher's* original URL (the agency website where the document came from); the DocumentCloud URL is a *mirror* with reader affordances, not a replacement for the canonical source.

## Search and discovery

DocumentCloud's search is exposed both via web UI and the API:

```python
# All documents tagged with this project
hits = client.documents.search(f"projectid:{PROJECT_ID}")

# Full-text search across the corpus
hits = client.documents.search("non-resident alien tuition")

# Combine
hits = client.documents.search(f'projectid:{PROJECT_ID} "right to know"')
```

Search results respect the document's access level — anonymous queries see only `public` documents. For civic projects, this means the published corpus is discoverable by anyone searching DocumentCloud directly, not just by people who land on the project's Quarto site. That's part of the value: liberated documents become *findable* in the broader DocumentCloud corpus, not just behind one project's URL.

## Add-ons — DocumentCloud as an ETL hook

[DocumentCloud Add-ons](https://www.documentcloud.org/help/add-ons/) (GitHub-hosted Python scripts that run server-side against documents in a user's account) extend the platform with custom processing: redaction, entity extraction, language detection, classification, OCR-cleanup. Civic-data projects rarely need to author add-ons, but two existing add-ons are useful as upload-time hooks:

- [`documentcloud-scraper-addon`](https://github.com/MuckRock/documentcloud-scraper-addon) — periodically scrapes a publisher's site and uploads new artifacts to a project. Pair with `discover.py` to keep the DocumentCloud project in sync with the source registry.
- [`documentcloud-scraper-cron-addon`](https://github.com/MuckRock/documentcloud-scraper-cron-addon) — cron-driven version of the above for daily/weekly auto-refresh.

For projects with a custom ETL hook (entity extraction, redaction-on-upload), authoring a project-specific add-on can move processing off the project's CI infrastructure and onto DocumentCloud's, which scales better for large corpora.

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `upload()` returns immediately but the document never appears in search | Server-side processing failed (OCR error, corrupted PDF, oversized file) | Poll `doc.status`; if `error`, check `doc.error_message`; for huge PDFs, split first |
| `upload_directory()` is slow and re-uploads on each run | No built-in deduplication | Use `pneumatic` or `dcupload` for bulk; or compute sha256 against an existing `documentcloud_url` column in provenance.csv and skip already-uploaded files |
| Embedded iframe shows a permissions-denied page | Document is `private` or `organization`-only; reader isn't logged in | Set `access="public"` for liberated documents; or accept the permission boundary for sensitive ones |
| Search returns nothing despite a known phrase | OCR hasn't run or failed | Check `doc.status == "success"`; re-trigger OCR via `doc.process()`; for image-only PDFs from older scans, OCR may need preprocessing first |
| `Unauthorized` on every upload despite correct credentials | Squarelet credentials expired or 2FA enabled | Refresh credentials via DocumentCloud web UI; use an API token instead of password |
| Documents uploaded but not visible in the project | Forgot `project=PROJECT_ID` on upload | `project.document_list = [...]; project.put()` to attach retroactively |
| `upload_urls()` queues fail silently for some URLs | DocumentCloud's fetcher hit a 403 / paywall / Cloudflare | Mirror the file locally first via `fetch.py`, then `upload()` from disk |

## What to write in the AGENTS.md

- **The DocumentCloud project URL(s)** — one per source registry slug, with the convention named.
- **Access level per source** — what's `public`, what's `organization`, what's `private`, and why. The justification is a governance decision per [`project-template.md#governance`](project-template.md#governance); document it where the access-level choice lives.
- **Upload-trigger policy** — does new content reach DocumentCloud automatically (via an add-on, or a step in `refresh.yml`) or manually? If automatic, where the credentials live (`.env`, GitHub secret) and which workflow uses them.
- **Quarto embed convention** — how the methodology pages reference DocumentCloud documents (direct iframe; partial-include of an iframe HTML file; jump-to-page links). Pick one and stick to it so the site reads consistently.
- **Provenance schema extensions** — `documentcloud_url` + `documentcloud_access` columns in `provenance.csv`; how the chain-of-custody is documented when a downstream reader follows a CSV row back to the source page.

## Where this lives in the project

| Operation | Lives in |
|---|---|
| Initial bulk upload of an existing corpus | A one-off script under `scripts/` (e.g., `scripts/upload_to_documentcloud.py`); not part of the recurring pipeline |
| Per-refresh upload of newly-fetched documents | A new step in `refresh.yml` running after `fetch`, OR a DocumentCloud scraper add-on configured against the source URL |
| Project URL + access level | `provenance.csv` (extended schema) + `AGENTS.md` *Deployment surface* table |
| Embed iframes for the Quarto site | `docs/_includes/<source>_<vintage>_embed.html` partials referenced from the relevant `.qmd` pages |
| Credentials | `.env` (gitignored) + GitHub Actions secrets (`DOCUMENTCLOUD_USERNAME`, `DOCUMENTCLOUD_PASSWORD`) |

DocumentCloud is the fourth publishing surface; it sits next to Datasette, Quarto, and LFS, not on top of them. The recurring-refresh PR pattern (see [`discovery-and-audit.md`](discovery-and-audit.md)) extends naturally: a cron-driven `discover → fetch → clean → audit → upload-to-documentcloud → audit-the-upload` chain, with each new vintage producing both a processed-CSV row *and* a citable source-document URL.
