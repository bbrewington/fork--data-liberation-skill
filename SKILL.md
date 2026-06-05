---
name: data-liberation
description: Build Python data pipelines that liberate structured data from unstructured and semi-structured sources — government PDFs, FOIA releases, scanned reports, scraped HTML, panel-format spreadsheets — into tidy, documented, reproducible civic datasets. Use whenever the user wants to extract tables or data from PDFs, scrape a government or institutional site for tabular data, scaffold a reproducible data project, harmonize records across multiple sources, add a new vintage or source to an existing pipeline, write a data dictionary or crosswalk, audit data against originals, or wrangle messy historical data. Trigger on phrases like "data liberation," "PDF extraction," "tidy data," "data dictionary," "crosswalk," "provenance," "reconcile," "scrape this site," even when the user does not name the skill explicitly; if the request involves turning a document into a dataset someone else could reuse, this skill applies. Do not trigger for pure ML model training or generic Python tutoring unrelated to data extraction.
---

# Data Liberation

A skill for generating Python data pipelines that liberate structured data from documents — PDFs, scraped pages, panel-format spreadsheets, scanned archives — into tidy, documented, reproducible datasets in the civic-data tradition.

"High-quality" means *fit for use* across five dimensions — availability, usability, reliability, relevance, and presentation. Each pipeline operation maps to a specific dimension; the [data-quality reference](references/data-modeling.md#data-quality) is the lookup. The skill stops short of modeling: it builds the artifact, but the politics of who benefits — open data ≠ information justice — is the maintainer's explicit responsibility in the README and AGENTS.md ([critical perspectives](references/movement-history.md#critical-perspectives-worth-absorbing)).

## What this skill encodes

- **A project template.** Immutable originals → processed tidy data → audit reports → lookups (crosswalks). Bootstrap from single-source, structured for multi-source from day one. See [`references/project-template.md`](references/project-template.md). The working example lives in a separate repo, [`brianckeegan/data-liberation-template`](https://github.com/brianckeegan/data-liberation-template), fetched on demand by `scripts/scaffold.py`.
- **Toolchain decision trees.** When to use pdfplumber vs. camelot vs. tesseract; requests + BeautifulSoup vs. headless browser vs. archived snapshots; how to read XLSX / CSV / Parquet / databases and normalize HTML / XML / JSON. See [`toolchain-pdf.md`](references/toolchain-pdf.md), [`toolchain-tabular.md`](references/toolchain-tabular.md), [`toolchain-documents.md`](references/toolchain-documents.md), [`toolchain-scraping.md`](references/toolchain-scraping.md).
- **Documentation conventions and quality dimensions.** Data dictionaries, harmonization crosswalks with caveats, per-extract provenance, the five-dimension quality framework, and the profiling / measurement / monitoring decomposition for what `audit.py` does. See [`data-modeling.md`](references/data-modeling.md).
- **Cleaning and standardization patterns.** The 9-step parser-time pipeline (profile → structural fixes → deduplication → missing-value treatment → outlier detection → normalization → validation + reject port → PII redaction → documentation), with concrete tooling per step (pandas, rapidfuzz / jellyfish / recordlinkage for fuzzy matching, presidio / scrubadub for PII, the impossible-value range table). See [`cleaning-and-standardization.md`](references/cleaning-and-standardization.md).
- **Auditing and bulletproofing.** Discovery of new upstream sources, reconciliation against published totals, and a pre-extraction bulletproofing checklist mapping each practitioner check to a quality dimension. See [`discovery-and-audit.md`](references/discovery-and-audit.md).
- **Movement context.** The civic-data tradition (Sunlight Foundation → PDF Liberation → PUDL → BoulderPublicData), four critical perspectives that shape what the skill commits to (empowering-intermediary self-description; the five activities request / digest / contribute / model / contest; information justice; contested data cultures), and the methodological lineage. Read [`movement-history.md`](references/movement-history.md) once at the start of a project so the framing is shared.
- **Open data standards (background, not a constraint).** The official standards the skill's artifacts already informally implement — Sunlight's policy principles, DCAT-US / W3C DCAT (cataloging), W3C PROV-O (provenance), the Data Quality Vocabulary and Data on the Web Best Practices, the FAIR principles, and the FAIRsharing / re3data / NIEM registries and exchange models. This is background for *naming and optionally deepening* what the pipeline already does — never a conformance gate in front of shipping. See [`open-data-standards.md`](references/open-data-standards.md).
- **Open government landscape (background, not a constraint).** The civic and institutional context around the data: transparency law and records requests (FOIA, state sunshine laws), the US federal open-data mandates (OMB M-13-13, the OPEN Government Data Act / Evidence Act, the DATA Act), the civic-tech consumer ecosystem, institutional portals (data.gov, CKAN, Socrata), and the international frame (Open Government Partnership, the International Open Data Charter, OKFN). Includes a catalogue of referenced resources and an honest gap-analysis of where the skill's small-team, US, self-hosted defaults meet the institutional/global picture. See [`open-government-landscape.md`](references/open-government-landscape.md).

## When to use this skill

Trigger when the user is:
- starting a new data liberation project from a PDF, FOIA release, scraped site, panel-format Excel, or other unstructured source
- adding a new source or vintage to an existing liberation pipeline
- asking how to extract tables from a specific document
- asking how to scaffold or structure a reproducible civic data project
- asking how to document, audit, or harmonize data from multiple sources
- wrangling messy historical data (mixed formats across years, mid-period schema changes, OCR-only old vintages)

Hand off to other tools when:
- the task is genuinely a one-line snippet ("read this PDF and tell me what it says") — answer directly, but mention this skill exists if the user is thinking about doing this more than once
- the user wants ML modeling on already-clean data — outside scope; this skill ends where modeling begins
- the user wants generic Python help unrelated to data extraction

## The six-phase workflow

This skill maps to the CRISP-DM phases of **data understanding → preparation → deployment**, deliberately stopping before modeling and evaluation (which are the analyst's domain after liberation is done). The framing comes from Shigarov's [table understanding survey](references/movement-history.md#academic-framing) and Holstein et al.'s [data understanding dimensions](references/movement-history.md#academic-framing); the workflow itself is distilled from PUDL, the Boulder Public Data repos, and the IPEDS pipeline.

```
┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────┐  ┌───────┐  ┌─────────┐
│ Survey  │->│ Scaffold │->│ Extract │->│ Tidy │->│ Audit │->│ Publish │
└─────────┘  └──────────┘  └─────────┘  └──────┘  └───────┘  └─────────┘
  understand   set up        pull text     reshape +  verify     serve via
  the source   the project   + tables out  document   vs. truth  Datasette
```

**Vocabulary alignment with industry frameworks.** This skill's six phases map onto the steps named by mainstream data-workflow frameworks (e.g., Monte Carlo's 8-step model and adjacent dbt/observability vocabularies). Use these as searchable synonyms — the names differ; the work is the same:

| Industry term | This skill's phase | What's named |
|---|---|---|
| **Goal Planning / Data Identification** | Survey | `discover.py` + Survey notes; unit-of-observation choice; codebook hunt |
| **Data Extraction** | Extract | `fetch.py` + per-vintage parsers' `read_*` calls |
| **Data Cleaning and Transformation** | Tidy (+ the cleaning pipeline) | 9-step parser-time pipeline in [`cleaning-and-standardization.md`](references/cleaning-and-standardization.md) |
| **Data Loading** | end of Tidy / start of Publish | `clean.py` writing the canonical CSV; `publish.py build` materializing the SQLite |
| **Data Validation** | Audit | `pandera` schema at the boundary; `audit.py`; `reconcile.py` against authoritative totals; the reject port |
| **Data Lineage** | (within Audit) | `provenance.csv` per-extract sidecar joined by `(source, vintage)` |
| **Data Observability** | (within Audit) | The diff-able `data/audit/summary-*.md` reviewed on every refresh PR |
| **Data Governance** | (cross-cutting) | License inheritance, PII redaction policy, data-subject considerations, downstream-accountability path — see the *Governance* section of [`project-template.md`](references/project-template.md#governance) |
| **Data Analysis and Modeling** | **Out of scope** | This skill deliberately stops at the deployment phase of CRISP-DM |
| **Data Maintenance** | recurring-refresh pattern | Cron-driven `discover → fetch → clean → audit` opening a reviewable PR; see [`discovery-and-audit.md`](references/discovery-and-audit.md) |

The reason for the alignment isn't to import the industry framings wholesale — it's so an agent that arrives via a Monte Carlo / dbt / Dagster context finds the right place in the skill, and so a search for "data validation" or "data lineage" lands somewhere useful.

### 1. Survey — understand the source before touching code

Before opening a Python file, answer:

- **What is this document?** Born-digital PDF (text extractable), scanned PDF (image-only, needs OCR), HTML page, panel-format XLSX, CSV, JSON API response, database export? Frame the extraction problem against the [Table Understanding taxonomy](references/movement-history.md#table-understanding-tu) — naming the subproblem (Table Detection? Structure Recognition? Functional Analysis? Canonicalization?) clarifies what's hard.
- **What is the unit of observation?** One row per ballot? Per precinct × contest × candidate? Per institution × year × variable? This is the most consequential design decision and is hard to change later.
- **What are the structural quirks?** Merged header cells; tables split across pages; footnotes that change column meaning; mid-period schema changes; multiple tables on one page; narrative-embedded numbers.
- **What is the public-interest stake?** Who collected this, who needs it, what gets lost if no one liberates it? This shapes documentation priorities later.
- **What history of access does the source have?** Has it been the subject of FOIA, MuckRock, or CORA requests? Is there a journalistic record of similar liberation work? Cite this in the README.

**Search and catalog — ask before assuming.** Before writing any code, ask the user explicitly:

- *What documentation exists for this source?* Codebooks, methodology PDFs, the publisher's own data dictionary, the survey questionnaire, the statute or regulation that mandates the publication. The original documentation is almost always more reliable than reverse-engineered guesses.
- *What prior work has touched this data?* Existing journalism, academic papers, FOIA logs, NICAR/IRE tipsheets, agency white papers, GitHub repos of past extraction attempts. A prior liberation effort (even a failed one) catches you up on the quirks for free.
- *What's the canonical contact?* The publisher's records officer, the journalist who last covered it, the academic who maintains a derivative dataset, the open-government group that's been pestering the agency. ProPublica's [data-bulletproofing checklist](references/discovery-and-audit.md#pre-extraction-bulletproofing) treats "ask the source" as a baseline practice, not an escalation.
- *What corroborating sources exist?* A separate publisher of the same underlying phenomenon — federal mirror of state data, aggregator like Census or BLS, watchdog dataset that audits the original — turns reconciliation from "compare to the source's own total" into "compare to an independent count."

If the user supplies a URL, FOIA tracking ID, prior repo, or paper, read it before drafting the Survey notes. If the user doesn't know, that's the time to web-search — but ask first; the user usually has better leads than the open web does.

*Optional:* if the source sits in a domain that may already have a standard or a canonical repository (research data, health, justice, statistics), a five-minute check of the registries — [FAIRsharing](https://www.fairsharing.org/), [re3data](https://www.re3data.org/) — can surface an existing metadata standard to reuse instead of inventing one. See [`references/open-data-standards.md`](references/open-data-standards.md). Most civic projects find nothing binding and proceed; the check is cheap insurance, not a required step.

*Also in Survey:* if the data has to be *requested* rather than downloaded (FOIA, a state sunshine law), or if a release may contain personal data that privacy law protects, the records-request process notes and the "what the project will not liberate" scope check live in [`references/discovery-and-audit.md`](references/discovery-and-audit.md#when-the-source-path-is-a-records-request-foia--sunshine-laws); the wider transparency-law, civic-tech, and international landscape (and a catalogue of referenced resources) is in [`references/open-government-landscape.md`](references/open-government-landscape.md). Background, not a gate.

Write a one-page Survey note (it becomes the seed of the project README). Decide whether this is **bespoke** (one-time extraction, single source, simple pipeline) or **infrastructural** (recurring data with vintages, multi-source, harmonized). The two cases share scaffolding but the second invests more upfront in `discover.py`, the concept catalog, and CI. Include the catalogued sources in `docs/methodology.qmd` from the start so the next contributor (or future Claude) doesn't re-discover them.

### 2. Scaffold — set up the project

**New project:** Run `scripts/scaffold.py` (it fetches the template from [`brianckeegan/data-liberation-template`](https://github.com/brianckeegan/data-liberation-template), renders the placeholders, and writes the project). Read [`references/project-template.md`](references/project-template.md) for the prose explanation of what each file in the skeleton does and why. Do not invent a parallel structure. The skeleton (with exact directory names) is:

```
project-name/
├── data/
│   ├── original/    <- immutable raw downloads (committed via LFS if large)
│   ├── processed/   <- tidy CSVs / parquet produced by the pipeline
│   ├── audit/       <- auto-generated audit + reconciliation reports
│   └── lookups/     <- JSON crosswalks, schema, code systems, etc.
├── scripts/
│   ├── schema.py    <- canonical column definitions, dtype coercion
│   ├── sources.py   <- Source ABC + Artifact dataclass
│   ├── config.py    <- paths, HTTP defaults, SOURCES registry
│   ├── fetch.py     <- idempotent downloader (hash + manifest)
│   ├── clean.py     <- orchestrator that routes per source/vintage
│   ├── audit.py     <- summary stats → Markdown report
│   ├── pipeline.py  <- end-to-end driver
│   └── parsers/     <- per-source, per-vintage parsers
├── tests/           <- pytest suite (schema contracts, parser fixtures)
├── docs/
│   ├── data-dictionary.md       <- one row per column, hand-maintained
│   └── filter-pivot-recipes.md  <- pandas + tidyverse + DuckDB recipes
├── AGENTS.md        <- architecture, gotchas, future-agent handbook
├── README.md        <- quickstart + data summary + movement context
├── pyproject.toml   <- uv-managed env (see template)
├── .gitignore
└── .github/workflows/  <- (opt-in) tests on push + scheduled refresh
```

**Existing project:** Identify where the new source fits in the existing Source registry. Read the project's `AGENTS.md` for conventions, then implement the `Source` contract (`discover` + `ingest`) in a new module under `scripts/parsers/`.

Bootstrap from single-source; keep the multi-source-ready layout (`scripts/parsers/<source>_<vintage>.py`, `data/original/<source>/<vintage>/`) from day one so adding a second source later is a parser file, not a refactor.

### 3. Extract — pull text and tables out

Match the input type to the toolchain:

| Input | Default tool | Fallback | Reference |
|---|---|---|---|
| Born-digital PDF, text-based table | `pdfplumber` | `camelot` (lattice) | [`toolchain-pdf.md`](references/toolchain-pdf.md) |
| Born-digital PDF, ruled grid | `camelot` (lattice mode) | `pdfplumber` | [`toolchain-pdf.md`](references/toolchain-pdf.md) |
| Scanned / image PDF | `tesseract` via `pytesseract` | manual transcription | [`toolchain-pdf.md`](references/toolchain-pdf.md) |
| HTML page with table | `pandas.read_html` then refine; `BeautifulSoup` for layout-as-tables | `lxml` directly | [`toolchain-documents.md`](references/toolchain-documents.md) |
| HTML page, no table tag | `BeautifulSoup` + CSS selectors | `playwright` if JS-rendered | [`toolchain-scraping.md`](references/toolchain-scraping.md) |
| Nested JSON | `pandas.json_normalize` | manual flatten | [`toolchain-documents.md`](references/toolchain-documents.md) |
| XML | `lxml.etree` + XPath | `pandas.read_xml` for simple cases | [`toolchain-documents.md`](references/toolchain-documents.md) |
| XLSX (clean) | `pandas.read_excel` | `openpyxl` directly | [`toolchain-tabular.md`](references/toolchain-tabular.md) |
| XLSX (panel format, merged cells) | `openpyxl` + manual unmerge | per-vintage parser | [`toolchain-tabular.md`](references/toolchain-tabular.md) |
| CSV / TSV | `pandas.read_csv` with explicit dtypes | `csv` module for malformed rows | [`toolchain-tabular.md`](references/toolchain-tabular.md) |
| Parquet | `pandas.read_parquet` (pyarrow engine) | — | [`toolchain-tabular.md`](references/toolchain-tabular.md) |
| Database | `sqlalchemy` + `pandas.read_sql` | `duckdb` for ad-hoc | [`toolchain-tabular.md`](references/toolchain-tabular.md) |
| Web scrape (recurring) | `requests` + `BeautifulSoup` + idempotent cache | Wayback Machine archive | [`toolchain-scraping.md`](references/toolchain-scraping.md) |

For *publishing* the liberated dataset — turning the processed CSV into a queryable web interface with a JSON API — see [`toolchain-datasette.md`](references/toolchain-datasette.md) (Datasette + sqlite-utils).

Always: capture a per-extract manifest entry (input file SHA256, page range or URL, tool + version, timestamp, row count) appended to `data/processed/provenance.csv`. This is the sidecar — joined onto the data by `(source, vintage)` rather than carried on every row. See [`data-modeling.md`](references/data-modeling.md#provenance).

Within each per-vintage parser, run the cleaning pipeline in order: **profile → structural fixes → deduplication → missing-value treatment → outlier detection → normalization → validation + reject port → PII redaction → log**. Each step has concrete tooling (pandas for profiling and structural; `rapidfuzz` / `jellyfish` / `recordlinkage` for fuzzy deduplication and record matching; Rubin's MCAR/MAR/MNAR for missingness; IQR + an impossible-value range table for outliers; `presidio` / `scrubadub` for PII). See [`cleaning-and-standardization.md`](references/cleaning-and-standardization.md). Malformed rows go to a reject port (`data/audit/rejected.csv`) — errors are durable, not fatal.

### 4. Tidy — reshape and document

Default to **Wickham-tidy long format**: one row per observation, one column per variable, one cell per value. This is the canonical storage shape across BoulderPublicData/Election-Results, the IPEDS pipeline, and PUDL.

Some domains have a more natural wide-by-key shape (e.g., one row per ballot in Cast-Vote-Records, where the ballot itself is the observation and each contest is a variable). In those cases, keep wide as the primary storage — but still emit a tidy long-form derivative for cross-source analysis if the project is multi-source.

Always include in `docs/filter-pivot-recipes.md`, side by side, for each recipe:
- **Python / pandas** — `df[df['variable'] == ...].pivot_table(index=..., columns=..., values=...)`
- **R / tidyverse** — `df |> filter(variable == ...) |> pivot_wider(names_from=..., values_from=...)`
- **SQL / DuckDB** — `PIVOT (FROM read_csv('...csv') WHERE variable = ...) ON ... USING ...`

DuckDB earns the third slot because it queries the CSV directly with no load step, runs SQL the consumer can paste straight into Datasette's SQL editor or BigQuery / Postgres / Snowflake, and handles tens-of-millions-of-rows tables without flinching. (For audiences where pivot tables in Excel or Google Sheets are the dominant consumption pattern, add that as a fourth.)

Generate `docs/data-dictionary.md` by hand (one row per column with type, units, source vocabulary, breakdown caveats). For multi-source projects, also maintain a **concept catalog** — a harmonization crosswalk that maps source-specific variable codes (e.g., IPEDS `EFTOTLT`, CDHE `TOTAL_HEADCOUNT`) to source-neutral concept names (e.g., `enrollment.headcount_fall_total`). The IPEDS pipeline's `concepts.py` (in its `pipeline/` package) is the canonical model; this skill's template puts the same module at `scripts/concepts.py`. Concepts carry not just labels but **caveats** explaining what is and isn't comparable across sources. See [`data-modeling.md`](references/data-modeling.md#concept-catalogs).

The data dictionary, the per-extract `provenance.csv`, and the quality dimensions are, respectively, informal **DCAT**, **PROV-O**, and **DQV** records — naming the standard they match (optionally) earns interoperability cheaply; see [`open-data-standards.md`](references/open-data-standards.md#crosswalk-standards--what-the-skill-already-builds). This is background, not a documentation requirement.

Validate the output with **pandera** schemas at the boundary of the pipeline plus **pytest** tests on parser behavior. Pandera schemas double as documentation. See [`data-modeling.md`](references/data-modeling.md#validation).

### 5. Audit — verify against the truth

Once the pipeline runs end-to-end:

- **Automatic audit (`scripts/audit.py`)** — per-source row counts, dtype conformance, NA rates, unique-key constraints, year coverage. Writes a Markdown report to `data/audit/summary.md`. Always include.
- **Reconciliation report (`scripts/reconcile.py`, optional)** — re-opens each original file independently, sums top-line totals (e.g., total votes per contest, total enrollment per institution), and compares to the processed CSV. Any new mismatch is a regression. Modeled on Election-Results' `reconcile.py`; see [`discovery-and-audit.md`](references/discovery-and-audit.md#reconciliation). Recommended for any project where the originals carry an authoritative top-line total (vote totals, enrollment, budget, etc.).
- **Discovery scan (`scripts/discover.py`, optional)** — scrapes the upstream source pages and flags any newly-published files not yet in the source registry. Pair with a scheduled GitHub Action for self-refreshing pipelines. See [`discovery-and-audit.md`](references/discovery-and-audit.md#discovery).

### 6. Publish — make the dataset queryable

The processed CSV is the deliverable. A complete liberation project ships *four* deployment surfaces — the **queryable data interface** ([`toolchain-datasette.md`](references/toolchain-datasette.md)), the **documentation site** ([`toolchain-quarto.md`](references/toolchain-quarto.md)), the **bulk distribution layer** for large files ([`toolchain-lfs.md`](references/toolchain-lfs.md)), and the **source-document layer** for the underlying PDFs / FOIA responses with reader-facing OCR + annotations + embed iframes + permalinks ([`toolchain-documentcloud.md`](references/toolchain-documentcloud.md)). Each plays to its strengths; together they cover the CRISP-DM deployment phase the workflow targets. The four are split so an agent working in just one layer only pays the context cost for that one.

- **Build SQLite (`scripts/publish.py build`)** — Converts the processed CSV + `provenance.csv` into a single SQLite file via [`sqlite-utils`](https://sqlite-utils.datasette.io/): composite primary key, indexed facetable columns, optional full-text search on narrative columns, foreign key from data → provenance. Generates `data/processed/metadata.yaml` from `docs/data-dictionary.md` to keep the two in sync. See [`toolchain-datasette.md`](references/toolchain-datasette.md).
- **Deploy Datasette (`scripts/publish.py deploy`)** — `datasette publish vercel|cloudrun|fly` ships the SQLite + metadata as a public read-only [Datasette](https://datasette.io/) instance with SQL editor, faceting, JSON API, and per-table/per-column documentation. For small datasets, [Datasette Lite](https://lite.datasette.io/) runs the same database in the browser with no server. The "Baked Data" architecture (database built fresh on every deploy, no application-layer writes) is the canonical shape for civic projects.
- **Document with [Quarto](https://quarto.org/) on [GitHub Pages](https://quarto.org/docs/publishing/github-pages.html)** — `.qmd` files in `docs/` (Markdown with executable code blocks) become the methodology, tutorials, and long-form data dictionary site. The `gh-pages.yml` workflow uses `quarto-dev/quarto-actions/publish@v2` with `target: gh-pages` to render and deploy on every push. Datasette serves the *data interface*; Quarto serves the *prose about how to use it*.
- **Track large files with [Git LFS](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage)** — Multi-gigabyte source PDFs, ZIP archives, and large Parquet outputs sit in LFS via `.gitattributes` patterns. Per-file limits are 2–5 GB depending on GitHub plan. **Architectural constraint: LFS does not work with GitHub Pages**, so the Quarto site links out to Datasette and to GitHub Releases for full-file downloads rather than embedding LFS-tracked data directly.
- **(Optional) Datasette Agent** — A conversational LLM interface over the published database, released as alpha in May 2026. Useful for reader discovery once the canned queries and metadata are solid; not a substitute for either.

*Optional standards pass:* the published `metadata.yaml` is already a **DCAT**-shaped catalog record; for a project that needs to federate into a `data.gov`-style catalog you can emit a `dcat-us.jsonld` alongside it, and a quick **FAIR** (Findable / Accessible / Interoperable / Reusable) or **DWBP** self-check is a useful "did we miss a license / stable identifier / provenance link?" review before announcing the dataset. Background and entirely optional — see [`open-data-standards.md`](references/open-data-standards.md). Never block shipping on it.

The recurring-refresh pattern extends naturally: the cron-driven `discover → fetch → clean → audit` PR, when merged, triggers `publish.yml` (rebuild SQLite + deploy Datasette) and `gh-pages.yml` (re-render Quarto site). Three deploys, one upstream change.

Commit. The pipeline is now reproducible *and* queryable *and* documented: anyone who clones can run `uv sync && uv run python -m scripts.pipeline` to regenerate `data/processed/` from `data/original/`; readers can browse, query, and cite the live Datasette instance; and the project's methodology, data dictionary, and tutorials live at a clean GitHub Pages URL.

## Bootstrap quickstart

For a new project the workflow is:

1. Read the user's source (the PDF, page, or spreadsheet) and produce the Survey notes inline.
2. Run `python scripts/scaffold.py --dest <path> --name <kebab-case> --description <…> --author <…> --owner <github-username>` — it fetches [`brianckeegan/data-liberation-template`](https://github.com/brianckeegan/data-liberation-template) at the pinned version, copies it into `<path>`, and substitutes placeholders. Read [`references/project-template.md`](references/project-template.md) for the per-file rationale.
3. Write the project files (README, pyproject.toml, schema.py, sources.py, an initial parser, AGENTS.md) to the user's working directory — not to this skill's `assets/`. Adapt placeholder names (`PROJECT_NAME`, `SOURCE_NAME`, etc.) to the actual project.
4. Suggest the user run `uv sync && uv run pytest` to verify the scaffold; then `uv run python -m scripts.pipeline` to attempt a first end-to-end run on a single sample file.
5. Iterate: each new vintage or quirk becomes a new parser file or a new test case.

## Adding a source to an existing project

1. Read the project's `AGENTS.md` first — every Boulder Public Data and similar project has one and it answers the architecture questions.
2. Add the `Source` subclass in `scripts/sources.py` (or a dedicated module) and register it in `scripts/config.py::SOURCES`.
3. Add a parser module under `scripts/parsers/`.
4. Add fixtures + a test under `tests/` — at minimum one fixture per source vintage that exercises the parser end-to-end.
5. If the project has a concept catalog (`data/lookups/concepts.yaml` or `scripts/concepts.py`), add the new source's variable codes to the existing concepts (or add new concepts with caveats explaining what's not comparable).
6. Run `audit.py` and `reconcile.py`. If reconciliation introduces a `mismatch`, investigate before merging.

## Adding a new vintage to an existing source

1. Add the new year's URL to the source registry.
2. Run `discover.py` — does it pick up the new file automatically?
3. Run `fetch.py` to pull it into `data/original/`.
4. Run `clean.py`. If it crashes, identify whether (a) the schema changed mid-period (add a vintage-specific branch in the parser) or (b) a structural quirk needs handling (merged cells, new columns).
5. Re-run audit and reconciliation. Update `docs/data-dictionary.md` with any new caveats.
6. Commit, preferably via PR with the audit + reconciliation diffs visible.

## Reference index

- [`references/movement-history.md`](references/movement-history.md) — the data liberation tradition (Sunlight, PDF Liberation, MuckRock, PUDL, BoulderPublicData) plus academic framing (CRISP-DM, table understanding, data understanding dimensions). Read once at the start.
- [`references/open-data-standards.md`](references/open-data-standards.md) — **background, not a constraint:** the official open-data standards the skill already informally implements (Sunlight policy guidelines, DCAT-US / W3C DCAT, PROV-O, DQV, DWBP, FAIR, FAIRsharing / re3data / NIEM), each profiled by history / precedents / standards organization / institutions / infrastructure, with a crosswalk from each standard to the existing skill artifact and an optional deepening step. For naming and optionally extending what the pipeline does — never a gate.
- [`references/open-government-landscape.md`](references/open-government-landscape.md) — **background, not a constraint:** the civic/institutional context around the data — transparency law and records requests (FOIA, sunshine laws), the US federal open-data mandates (M-13-13, OPEN Government Data Act, DATA Act), the civic-tech ecosystem, institutional portals (data.gov / CKAN / Socrata), and the international frame (OGP, Open Data Charter, OKFN). Synthesizes the five open-government themes, carries a catalogue of referenced resources, and maps the gaps between the skill's small-team/US/self-hosted defaults and the institutional/global picture to where each is addressed.
- [`references/toolchain-pdf.md`](references/toolchain-pdf.md) — pdfplumber, camelot, tesseract; decision tree, common gotchas, fallback chains.
- [`references/toolchain-tabular.md`](references/toolchain-tabular.md) — XLSX (including panel-format), CSV, Parquet, databases.
- [`references/toolchain-documents.md`](references/toolchain-documents.md) — HTML, XML, JSON → tidy; `pandas.json_normalize` patterns.
- [`references/toolchain-scraping.md`](references/toolchain-scraping.md) — post-API web scraping per the CU Info Science *Web Data Science Book*: ethics, archives, protocols, dynamic pages, government data.
- [`references/toolchain-datasette.md`](references/toolchain-datasette.md) — the queryable data interface: sqlite-utils, metadata, canned queries, plugins, the "Baked Data" pattern, deploy targets, Datasette Agent.
- [`references/toolchain-quarto.md`](references/toolchain-quarto.md) — the documentation site: `_quarto.yml`, `docs/*.qmd`, `quarto publish gh-pages`, the freeze cache, GitHub Actions.
- [`references/toolchain-lfs.md`](references/toolchain-lfs.md) — bulk distribution via Git LFS: per-plan size limits, the architectural caveat that LFS does not work with GitHub Pages, CI bandwidth posture.
- [`references/toolchain-documentcloud.md`](references/toolchain-documentcloud.md) — the source-document publishing surface: upload + project organization via `python-documentcloud`; reader-facing OCR + annotations + page-level permalinks; embed iframes for the Quarto site; access levels (public / organization / private) and the chain-of-custody from processed-CSV-row → provenance.csv → DocumentCloud document URL.
- [`references/project-template.md`](references/project-template.md) — full skeleton spec; what each file does and why.
- [`references/data-modeling.md`](references/data-modeling.md) — Wickham-tidy, data dictionaries, concept catalogs / crosswalks, provenance, pandera validation, filter-pivot recipes, the five-dimension quality framework.
- [`references/cleaning-and-standardization.md`](references/cleaning-and-standardization.md) — the 9-step parser-time cleaning pipeline: profile, structural fixes, exact + fuzzy deduplication (Jaro-Winkler / Levenshtein) and record matching, Rubin's MCAR/MAR/MNAR missing-data classification, statistical + domain-range outlier detection, normalization and standardization, validation + reject port, PII redaction (presidio/scrubadub).
- [`references/discovery-and-audit.md`](references/discovery-and-audit.md) — `discover.py` (find new sources upstream), `audit.py` (profile + measure), `reconcile.py` (verify against originals), and the pre-extraction bulletproofing checklist.

## The template repo

The working template lives at [`brianckeegan/data-liberation-template`](https://github.com/brianckeegan/data-liberation-template), pinned to a tagged release that pairs with this skill (`v0.1.0` of one matches `v0.1.0` of the other). `scripts/scaffold.py` fetches it on demand; you should not normally need to read it. What it contains, briefly:

- `pyproject.toml` — uv-managed; Python 3.11+; core deps pandas, pandera, pyarrow, requests, requests-cache, tenacity, structlog, tabulate; optional extras for `pdf`, `ocr`, `scrape`, `tabular`, `publish`.
- `scripts/{schema,sources,config,fetch,discover,clean,audit,reconcile,publish,pipeline}.py` — one-responsibility modules connected by `scripts/pipeline.py`'s argparse CLI (`discover | fetch | clean | audit | reconcile | publish | run`).
- `scripts/concepts.py` — optional cross-source harmonization (single-source projects leave it unused).
- `_quarto.yml` + `docs/*.qmd` — Quarto site seed.
- `.gitattributes` — Git LFS rules for source PDFs / large Parquet / SQLite.
- `AGENTS.md`, `README.md`, `docs/data-dictionary.md`, `docs/filter-pivot-recipes.md` — placeholder-filled documentation the scaffolder personalizes.
- `tests/test_schema.py` + `tests/conftest.py` — baseline schema-drift tests.
- `.github/workflows/tests.yml` — on by default. `refresh.yml.disabled`, `publish.yml.disabled`, `gh-pages.yml.disabled` — opt-in.

For why each piece is shaped this way, read [`references/project-template.md`](references/project-template.md). To inspect a rendered project, run `scripts/scaffold.py --dry-run` or scaffold into a temp dir.

## Conventions worth defending

A few that are easy to get wrong:

- **Immutable originals.** Files in `data/original/` are never edited in place after the first commit. Any cleaning lives in `scripts/parsers/` and produces `data/processed/`. The hash manifest in `data/original/manifest.json` enforces this. This is what makes the pipeline reproducible.
- **Per-extract provenance, not per-row.** Carrying source URL on every row is wasteful and noisy. Sidecar `provenance.csv` keyed on `(source, vintage)` and joined when needed. (Per-cell provenance is a different beast — opt-in for audit-grade work.)
- **Concepts carry caveats.** A concept catalog that just renames variables across sources is a foot-gun. Every concept entry should document what is and is not comparable — see the IPEDS pipeline's `concepts.py` for examples like "IPEDS Non-Resident Alien ≠ CDHE Non-Resident."
- **Tidy long is the storage shape, wide is the analysis shape.** Don't be shy about the long form being awkward to eyeball — the filter-pivot recipes in `docs/` are how readers recover human-readable wide views. The trade is worth it for cross-source analysis.
- **AGENTS.md before code.** A new contributor (or future Claude) should be able to read AGENTS.md and know enough to add a source without re-reading the codebase. If the file is missing or stale, the architecture is undocumented; fix it.
