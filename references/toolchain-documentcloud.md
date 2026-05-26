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

Inside a `.qmd` file, embed the source PDF next to its prose explanation:

```markdown
## How the 2024 results were extracted

The published Statement of Vote ([source]({{< var sov_2024_url >}})) is
a 412-page PDF. Pages 17–143 carry the precinct-by-contest tables that
became `data/processed/elections.csv`.

{{< include _sov_2024_embed.html >}}
```

This is what turns a Quarto methodology page from *prose about the data* into *prose with the original document inline*. The LFS-cannot-serve-from-Pages constraint (see [`toolchain-lfs.md`](toolchain-lfs.md)) is what makes DocumentCloud structurally important here: the Quarto site can embed DocumentCloud iframes without serving the PDFs from `gh-pages`.

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
