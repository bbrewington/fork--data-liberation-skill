# Toolchain: Publishing Liberated Data with Datasette, Quarto, and Git LFS

A CSV in `data/processed/` is the deliverable. It's also inert: readers download it, open it in Excel or pandas, and that's where the conversation ends. A liberated dataset gains an order of magnitude in usefulness when the project ships three deployment surfaces together: a **queryable data interface** that lets readers browse, filter, and pull a JSON API; a **documentation site** that explains how the data was built and how to use it; and a **distribution layer** for the data itself, including large files that don't fit comfortably in plain Git.

Three tools cover this surface:

- **[Datasette](https://datasette.io/)** — turns a SQLite database into a queryable web app with SQL editor, facet browsing, JSON API, and one-command deploy. The *data interface*.
- **[Quarto](https://quarto.org/)** + **GitHub Pages** — renders `.qmd` files (Markdown with executable code blocks) to a static site, deployed for free. The *documentation, methodology, and tutorial* surface.
- **[Git LFS](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage)** — tracks large data artifacts (multi-gigabyte PDFs, large Parquet files) via pointer files in Git while storing the actual content on GitHub's LFS servers. The *bulk distribution* layer for files too big for ordinary Git.

This reference covers the round trip for each: tidy CSV/Parquet from the pipeline → SQLite via [`sqlite-utils`](https://sqlite-utils.datasette.io/) → Datasette running locally → metadata and plugins worth knowing → publishing to the web → optionally an LLM-driven interface via [Datasette Agent](https://datasette.io/blog/2026/datasette-agent/) (alpha, released May 2026); then Quarto setup, the `_quarto.yml`/`.qmd` model, and the `quarto-actions/publish@v2` GitHub Action; then Git LFS configuration via `.gitattributes`, the per-plan size limits, and the one architectural caveat that shapes everything else: **LFS does not work with GitHub Pages**. The patterns are drawn from the [PyCon 2023 SQLite tutorial](https://sqlite-tutorial-pycon-2023.readthedocs.io/) and from Simon Willison's "Baked Data" architecture that powers Niche Museums, TILs, and PUDL's published instance.

## Why Datasette for liberated data

The CSV-only baseline asks every downstream user to repeat the same setup work — load it, declare dtypes, build the joins to provenance, write the filter expressions. Datasette delivers all of that as a deployed read-only web app:

- **SQL in the browser.** Any registered user can write SQL against the published database directly, including joins across tables, full-text search, and JSON output. Civic-data consumers (reporters, advocates, students) who would never install pandas can query a Datasette site fine.
- **Faceted browsing.** For categorical columns, Datasette generates per-value facets automatically — readers click "Boulder County" to filter, then "2024" to filter further, and the URL captures the state. The query is shareable; the result is citable.
- **JSON API for free.** Every table view and SQL query has a `.json` (and `.csv`) sibling. Downstream pipelines, Observable notebooks, and journalism teams pin against the URL rather than re-fetching the source.
- **Metadata as documentation.** Per-database, per-table, and per-column descriptions render alongside the data. The `docs/data-dictionary.md` you maintain in the repo has a counterpart that *travels with the database file*.
- **One-command publishing.** `datasette publish` deploys to Google Cloud Run, Heroku, Vercel, or Fly with a single command. The deployed instance is the published artifact; the GitHub repo is the source of truth.

The pairing with this skill is clean: the pipeline emits a canonical CSV and Parquet at `data/processed/`. A small additional step converts that to SQLite, attaches the provenance sidecar as a related table, writes a `metadata.yaml` describing the dataset, and deploys. The Boulder Election-Results published instance is the model: same canonical schema, same provenance, plus a queryable web layer that readers actually use.

## From processed data to SQLite

`sqlite-utils` is the workhorse for getting tidy CSV/Parquet into SQLite in a form Datasette likes. (The older [`csvs-to-sqlite`](https://datasette.io/tools/csvs-to-sqlite) is no longer maintained; use `sqlite-utils` instead.)

### Basic ingest

```bash
uvx sqlite-utils insert data/processed/elections.db elections \
    data/processed/boulder_election_results.csv --csv

uvx sqlite-utils insert data/processed/elections.db provenance \
    data/processed/provenance.csv --csv
```

This creates two tables (`elections` and `provenance`) inside the single SQLite file. The `insert` command infers a schema from the CSV; for civic data with leading-zero IDs or other string-typed numeric columns, declare types explicitly:

```bash
uvx sqlite-utils insert data/processed/elections.db elections \
    data/processed/boulder_election_results.csv --csv \
    --pk source --pk vintage --pk precinct --pk contest --pk candidate
uvx sqlite-utils transform data/processed/elections.db elections \
    --type votes INTEGER \
    --type precinct TEXT \
    --type vintage TEXT
```

A few patterns worth memorizing:

- **`--pk` declares the composite primary key.** Datasette uses this for clean per-row URLs and pagination. Match it to the composite key declared in `scripts/schema.py`.
- **`--alter` lets a second insert append columns.** Useful when adding a vintage that introduces new columns.
- **`--ignore` and `--replace` handle re-runs.** `--ignore` skips rows whose PK already exists; `--replace` overwrites them.
- **Foreign keys connect tables.** `sqlite-utils add-foreign-key elections.db elections source provenance source` lets Datasette render the link as a clickable cross-table reference.

### Indexes

For tables of more than a few thousand rows, declare indexes on the columns readers will filter or facet by:

```bash
uvx sqlite-utils create-index data/processed/elections.db elections vintage
uvx sqlite-utils create-index data/processed/elections.db elections source
uvx sqlite-utils create-index data/processed/elections.db elections "contest, vintage"
```

Without indexes, Datasette's facet generation falls back to full-table scans, which gets slow above ~50k rows. With them, faceting is near-instant up to tens of millions.

### Full-text search

For narrative columns (FOIA response text, candidate biographies, agency descriptions), enable SQLite FTS5:

```bash
uvx sqlite-utils enable-fts data/processed/elections.db elections candidate contest
```

The Datasette table view picks this up automatically and exposes a search box; the underlying SQL uses the FTS5 MATCH operator.

### A `scripts/publish.py` wrapper

The canonical pattern is a small Python module that reproduces the SQLite build from the canonical CSV in a single command:

```python
# scripts/publish.py
import subprocess
from pathlib import Path

DB = Path("data/processed/elections.db")
CSV = Path("data/processed/boulder_election_results.csv")
PROV = Path("data/processed/provenance.csv")


def build():
    if DB.exists():
        DB.unlink()  # rebuild from scratch — single canonical source

    subprocess.run([
        "sqlite-utils", "insert", str(DB), "elections", str(CSV), "--csv",
        "--pk", "source", "--pk", "vintage", "--pk", "precinct",
        "--pk", "contest", "--pk", "candidate",
    ], check=True)

    subprocess.run([
        "sqlite-utils", "insert", str(DB), "provenance", str(PROV), "--csv",
        "--pk", "source", "--pk", "vintage",
    ], check=True)

    subprocess.run([
        "sqlite-utils", "add-foreign-key", str(DB),
        "elections", "source", "provenance", "source",
    ], check=False)  # idempotent: ignore "already exists"

    for col in ("vintage", "source", "contest"):
        subprocess.run([
            "sqlite-utils", "create-index", "--if-not-exists",
            str(DB), "elections", col,
        ], check=True)


if __name__ == "__main__":
    build()
```

Wire this into the pipeline driver as `uv run python -m scripts.publish build`. The `elections.db` file is then a reproducible artifact: any commit + uv environment regenerates an identical database file. (See [`references/project-template.md`](project-template.md) for where `scripts/publish.py` sits relative to the other pipeline modules.)

## Running Datasette locally

Once `data/processed/elections.db` exists, serve it:

```bash
uvx datasette serve data/processed/elections.db --metadata data/processed/metadata.yaml -o
```

`-o` opens the browser at `http://localhost:8001`. `--reload` auto-restarts on file changes during development. For dev with plugins:

```bash
uvx --with datasette-cluster-map --with datasette-render-markdown \
    datasette serve data/processed/elections.db --metadata metadata.yaml --reload
```

The `uvx --with` pattern installs Datasette plus plugins into an ephemeral environment without polluting the project's `pyproject.toml`. For project-level installation, add `datasette` and plugins to the `[project.optional-dependencies]` `publish` group.

## Metadata: the documentation surface that travels with the data

Datasette reads a YAML or JSON file describing the dataset — title, license, source, per-table descriptions, per-column descriptions, canned queries. This is what readers see at the top of every page, and it's the most-undervalued surface a liberation project has.

A starter `metadata.yaml`:

```yaml
title: Boulder Election Results
description_html: |
  Precinct-level statements of vote from Boulder County and the
  Colorado Secretary of State, 2004–present. Tidy long format,
  one row per (source, vintage, precinct, contest, candidate).
license: CC-BY-4.0
license_url: https://creativecommons.org/licenses/by/4.0/
source: Boulder County Clerk & Recorder + Colorado Secretary of State
source_url: https://bouldercounty.gov/elections/
about: Generated by the boulder-election-results pipeline
about_url: https://github.com/BoulderPublicData/Election-Results

databases:
  elections:
    description: |
      Tidy long-form precinct results, joined to per-extract provenance.
      See data-dictionary.md in the source repo for the full schema.
    tables:
      elections:
        title: Precinct results
        description: One row per (source, vintage, precinct, contest, candidate).
        sort: vintage
        facets: [vintage, source, contest]
        columns:
          source: Source registry slug; joins to `provenance` for fetch metadata.
          vintage: Election cycle; string ("2024-general").
          precinct: Boulder County precinct ID. Leading zeros preserved.
          votes: Vote count. Nullable when source suppressed the count.
        units:
          votes: count
      provenance:
        title: Per-extract provenance
        description: One row per (source, vintage); fetch URL, sha256, parser used.

    queries:
      total_votes_per_contest_per_vintage:
        title: Total votes per contest per vintage
        description: Top-line totals — useful for sanity-checking against published SoVs.
        sql: |
          SELECT vintage, contest, SUM(votes) AS total_votes
          FROM elections
          WHERE votes IS NOT NULL
          GROUP BY vintage, contest
          ORDER BY vintage DESC, total_votes DESC
```

Three patterns to lean into:

- **Mirror `docs/data-dictionary.md` column descriptions into `metadata.yaml`.** The dictionary is the source of truth (see [`references/data-modeling.md`](data-modeling.md#data-dictionary) for the per-column template); the metadata file is the published projection. A small `scripts/publish.py` step can read the dictionary and emit the metadata to keep them in sync.
- **Use `facets` to pre-declare browsable categoricals.** Datasette will auto-detect facetable columns, but declaring them in metadata sets the default view readers see first.
- **Write canned queries for the questions readers will ask.** Per-contest totals, year-over-year change, top-N by some measure. Each canned query gets a clean URL (`/elections/total_votes_per_contest_per_vintage`) that anyone can cite.

### `metadata.yaml` vs `datasette.yaml` (Datasette 1.0a8+)

A change worth knowing: in the 1.0 alpha series (the current stable is 0.65.2 but the alpha is at 1.0a26), Datasette split configuration into two files. **`metadata.yaml`** keeps dataset-identity content (title, description, license, source, per-table/column descriptions, canned queries). **`datasette.yaml`** carries server configuration (plugin settings, permissions, settings that used to live in `metadata.yaml`). For 0.x deployments, `metadata.yaml` still holds both. For 1.0a-track deployments, check the [annotated release notes for 1.0a8](https://docs.datasette.io/en/latest/changelog.html#a8-2024-02-07) to decide which file each setting belongs in.

The pragmatic rule: civic projects on a long-running stable footing should stay on 0.x and a single `metadata.yaml` until 1.0 ships stably. Projects starting fresh now can adopt the split; the tooling supports it.

## Plugins worth knowing for civic data

The Datasette plugin ecosystem is large; a handful are durable defaults for civic-data publishing.

| Plugin | What it adds | When to use |
|---|---|---|
| [`datasette-cluster-map`](https://datasette.io/plugins/datasette-cluster-map) | Renders any table with `latitude` and `longitude` columns as a clustered map. | Geospatial liberated data — incident logs, facility lists, polling places. |
| [`datasette-render-markdown`](https://datasette.io/plugins/datasette-render-markdown) | Renders Markdown in designated columns. | FOIA case logs, narrative descriptions, agency response text. |
| [`datasette-vega`](https://datasette.io/plugins/datasette-vega) | Lets readers chart query results with Vega-Lite. | Any time-series, any per-category comparison. |
| [`datasette-graphql`](https://datasette.io/plugins/datasette-graphql) | Exposes a GraphQL API alongside the REST/JSON one. | Downstream consumers that prefer GraphQL (some JS frontends). |
| [`datasette-search-all`](https://datasette.io/plugins/datasette-search-all) | One search box across every FTS-enabled table. | Multi-table corpora (FOIA collections, legislative records). |
| [`datasette-copyable`](https://datasette.io/plugins/datasette-copyable) | Adds copy-to-clipboard for rows in CSV / TSV / Markdown. | Reporter workflows: read row, paste into draft. |
| [`datasette-block-robots`](https://datasette.io/plugins/datasette-block-robots) | Adds `robots.txt` to deter scraping. | Almost never — the point is to *enable* republishing. Useful only if you've explicitly committed to not being a crawler target. |
| [Datasette Agent](https://agent.datasette.io/) | Conversational LLM over the published database. | See the [Datasette Agent](#datasette-agent-alpha-may-2026) section below. |

Install plugins into the deployment by adding `--install <plugin>` to `datasette publish` or by listing them in `pyproject.toml`'s `publish` extras group.

## The "Baked Data" pattern

Most civic liberation projects benefit from what Simon Willison calls the [Baked Data architecture](https://sqlite-tutorial-pycon-2023.readthedocs.io/en/latest/baked-data.html): the database is built fresh during the deploy step from the source CSVs, and the deployed instance is read-only. No application-layer writes; no separate database server; no application state. The Niche Museums and TILs sites are the canonical examples.

This is the right architecture for liberated civic data specifically because:

- **The dataset is the deliverable.** Every cycle of `clean → audit → publish` produces a new version of the SQLite file. There's no user-generated content layered on top of it.
- **Cache headers can be aggressive.** A static-like artifact behind a CDN serves at near-zero cost per request, even under journalism-driven traffic spikes.
- **Versioning is automatic.** Each deploy is a new build; the git commit hash and the SQLite file's sha256 together cite a specific dataset version.
- **Reverting is trivial.** A bad refresh produced a broken database? Roll back the deploy; the previous build is still there.

Implementation: the publishing workflow runs `scripts/publish.py build` (which produces `data/processed/elections.db`) and then `datasette publish <provider>` with the freshly-built database. The pipeline runs in CI; the result is a deploy. See the recurring-refresh pattern in [`references/discovery-and-audit.md`](discovery-and-audit.md) — extending that pattern with a final `datasette publish` step is the canonical shape.

## Publishing options

A spectrum from zero infrastructure to fully self-hosted:

### Datasette Lite (zero infrastructure)

[Datasette Lite](https://lite.datasette.io/) is Datasette compiled to WebAssembly. A static-hosted HTML page loads the SQLite file from a URL, runs Datasette entirely in the user's browser, and serves the interface. No server. No deploy.

```
https://lite.datasette.io/?url=https://github.com/{user}/{project}/raw/main/data/processed/elections.db
```

For datasets up to ~50 MB this works well and costs nothing. Above that, the browser's memory becomes the constraint. Best for small projects, demonstrations, and personal datasets.

### `datasette publish cloudrun` (built-in)

Google Cloud Run. The Datasette package ships this command natively:

```bash
uvx datasette publish cloudrun data/processed/elections.db \
    --metadata data/processed/metadata.yaml \
    --service boulder-election-results \
    --install datasette-cluster-map --install datasette-render-markdown
```

Builds a Docker image, deploys it, returns a URL. Cloud Run's free tier handles small-traffic civic sites for free; pricing scales with use.

### `datasette publish vercel` (plugin)

[Vercel](https://vercel.com/) via the [`datasette-publish-vercel`](https://github.com/simonw/datasette-publish-vercel) plugin. Serverless functions; free tier suitable for most civic-data sites:

```bash
uvx --with datasette-publish-vercel \
    datasette publish vercel data/processed/elections.db \
    --metadata data/processed/metadata.yaml \
    --project boulder-election-results \
    --install datasette-cluster-map
```

### `datasette publish fly` (plugin)

[Fly.io](https://fly.io/) via [`datasette-publish-fly`](https://github.com/simonw/datasette-publish-fly). Edge containers, supports SpatiaLite extension for geospatial data:

```bash
uvx --with datasette-publish-fly \
    datasette publish fly data/processed/elections.db \
    --metadata data/processed/metadata.yaml \
    --app boulder-election-results \
    --spatialite
```

### Choosing among them

For most civic projects, the choice is between Datasette Lite (for one-off or small datasets) and Vercel or Fly (for ongoing deployments under a custom domain). Cloud Run is the right choice when the project is already in a GCP environment. Heroku is supported but no longer the friendly default it once was.

A pattern worth considering: ship to Datasette Lite for the "always available" demo URL, and to Vercel or Fly for the canonical production instance. The Lite URL works even when the production deploy is rebuilding.

## Documentation and tutorials with Quarto + GitHub Pages

Datasette publishes the **data interface**. A complete liberation project also needs to publish the **documentation around the data** — the methodology, the data dictionary in long form, tutorials for downstream users, methodological essays, replication code, the change log between vintages. Datasette's per-table metadata is excellent for "what does this column mean," but it isn't the right surface for "how was this dataset built and what should you know before citing it." For that, the project's `docs/` directory wants its own published home.

[Quarto](https://quarto.org/) is the right tool for this layer. Quarto authors `.qmd` files (Markdown with executable code blocks in Python, R, Julia, or Observable JS), renders to HTML / PDF / Word / Hugo / Docusaurus, and publishes to GitHub Pages with one command. The result is a static site sitting alongside the GitHub repo, free to host, with clean URLs the project can cite.

The pairing is clean: Datasette serves the *live, queryable data interface*; the Quarto site serves the *durable documentation about how the data came to be*. Both are linked from the project README; they cite each other; together they cover the deployment surface of the project.

### Minimum viable Quarto setup

The `_quarto.yml` at the project root declares it a Quarto project and tells Quarto how to render:

```yaml
project:
  type: website
  output-dir: _site

website:
  title: "{{ project_name }}"
  description: "{{ description }}"
  navbar:
    left:
      - href: index.qmd
        text: Home
      - href: data-dictionary.qmd
        text: Data dictionary
      - href: filter-pivot-recipes.qmd
        text: Recipes
      - href: methodology.qmd
        text: Methodology
    right:
      - icon: github
        href: https://github.com/{{ owner }}/{{ project_name }}
      - text: "Datasette"
        href: https://{{ project_name }}.vercel.app/

format:
  html:
    theme: cosmo
    toc: true
    code-copy: true
    code-overflow: wrap

execute:
  freeze: auto      # store computation results; re-run only when source changes
```

A small set of `.qmd` files in `docs/` becomes the site:

- `docs/index.qmd` — landing page: what the dataset is, where to get it, who to cite, the Datasette URL, the bulk-download URL.
- `docs/data-dictionary.qmd` — the long-form column-by-column reference (the same content as `docs/data-dictionary.md` from `references/data-modeling.md`, rendered with examples).
- `docs/filter-pivot-recipes.qmd` — the pandas + tidyverse + Excel recipes, with executable code blocks that run against a small sample of the data committed to the repo.
- `docs/methodology.qmd` — how the data was extracted, what's known to be incomplete, the reconciliation log, the cross-source caveats from the concept catalog.
- `docs/changelog.qmd` — what changed in each vintage, what schema migrations happened, what's deprecated.

This is the documentation a journalist or researcher reads *before* opening the CSV. The IPEDS pipeline's Quarto site is the model.

### Publishing with `quarto publish gh-pages` (one-time setup)

Quarto needs a one-time local setup to create the `gh-pages` branch — this isn't optional, because the GitHub Action below relies on the branch already existing:

```bash
quarto publish gh-pages
```

That command renders the site, creates a `gh-pages` orphan branch with just the rendered output, pushes it, and (for project sites) GitHub auto-configures Pages to serve from it. The URL is `https://<owner>.github.io/<repo>/`. Custom domains work via a `CNAME` file at the project root — see [Quarto's GitHub Pages docs](https://quarto.org/docs/publishing/github-pages.html) for the details.

### Automated publishing via GitHub Actions

After the one-time local setup, automation is a small workflow:

```yaml
# .github/workflows/gh-pages.yml
name: Quarto site

on:
  push:
    branches: [main]
    paths:
      - 'docs/**'
      - '_quarto.yml'
      - 'data/processed/**'   # rebuild when the data changes
  workflow_dispatch:

jobs:
  build-deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: write          # required to push to gh-pages
    steps:
      - uses: actions/checkout@v4
        with:
          lfs: true            # pull LFS pointers (see Git LFS section)

      - uses: quarto-dev/quarto-actions/setup@v2

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Install Python and project dependencies
        run: uv sync --extra publish

      - name: Render and publish to gh-pages
        uses: quarto-dev/quarto-actions/publish@v2
        with:
          target: gh-pages
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

The key elements:

- **`permissions: contents: write`** — required so the action can push to `gh-pages`. Without it the publish step fails with a 403.
- **`quarto-dev/quarto-actions/setup@v2`** then **`publish@v2 target: gh-pages`** — the two-step canonical pattern. `publish@v2` renders before pushing by default; set `render: false` if rendering happens elsewhere (e.g., via `freeze: auto` with pre-committed `_freeze/`).
- **`paths:` filter** — rerender only when `docs/`, `_quarto.yml`, or the data itself changes. Avoids spurious rebuilds on every commit.
- **`with: lfs: true`** on checkout — pulls Git LFS-tracked files so the Quarto site can embed sample data. See the next section for what this implies architecturally.

The `_freeze/` directory (created by `quarto render` with `freeze: auto`) should be committed to version control. It stores executed-code outputs so the GH Action only re-runs the code that actually changed, not the entire site every time. The PyCon SQLite tutorial's published instance uses this pattern.

### What goes in `docs/` vs. what goes in Datasette metadata

A useful split:

| Content | Lives in | Reason |
|---|---|---|
| Per-column description, units, controlled vocabulary | Datasette `metadata.yaml` | Renders inline with the column; readers see it where they need it |
| Long-form column rationale, vintage breakpoints, caveats | `docs/data-dictionary.qmd` | Too long for inline metadata; benefits from prose, links, examples |
| Canned queries with named parameters | Datasette `metadata.yaml` | Datasette renders these as forms; readers run them in the browser |
| Methodology essays, reconciliation logs, change log | `docs/*.qmd` | Static prose; readers consume sequentially, not query-by-query |
| The data itself | Datasette + CSV/Parquet downloads | The site is *about* the data, not a copy of it |

A small script in `scripts/publish.py` can read `docs/data-dictionary.md` (or `.qmd`'s front-matter + content) and emit `metadata.yaml`'s per-column descriptions, so the long form and the inline form stay in sync.

## Git LFS for large datasets

A liberation project accumulates two kinds of files that strain ordinary Git: large source artifacts (full-resolution scanned PDFs, multi-gigabyte XML dumps, archive ZIPs) and large processed outputs (multi-million-row Parquet files). GitHub politely rejects files over 100 MB and *recommends* keeping repos under 1 GB total. [Git Large File Storage (LFS)](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage) is the escape hatch: Git tracks a small pointer file (sha256 + size, ~130 bytes), and the actual content lives on a separate LFS server that GitHub provides.

### When LFS earns its keep

- **`data/original/` artifacts over ~25 MB.** Election Statement of Vote PDFs from large counties; full-resolution scanned annual reports; agency document-dump ZIPs.
- **Processed Parquet files over ~100 MB.** Multi-million-row tidy long-form outputs; multi-decade longitudinal datasets.
- **Reproducible build artifacts.** A SQLite database that's expensive to rebuild (hours of OCR or scraping) and that downstream users want to clone-and-go.

When LFS doesn't earn its keep:

- **The processed CSV is under 10 MB.** Standard Git handles it fine, with the diff history downstream users actually want.
- **The source artifact can be re-fetched.** A small fetch script + a URL in `provenance.csv` is more durable than an LFS pointer that depends on GitHub's LFS billing remaining favorable.

The single most-cited disadvantage of LFS for civic projects: it imposes a billing dependency on GitHub. The free plan ships with 1 GB storage and 1 GB/month bandwidth bundled; data packs cost real money beyond that. For a project that may outlive a particular developer's GitHub account, this is a coupling worth understanding.

### Setting up LFS

```bash
# One-time per machine
git lfs install

# Per-repo: declare which file globs are LFS-tracked
git lfs track "data/original/*.pdf"
git lfs track "data/original/**/*.pdf"
git lfs track "data/processed/*.parquet"
git lfs track "data/processed/*.db"

# This created/modified .gitattributes — commit it
git add .gitattributes
```

The `.gitattributes` entries look like:

```
data/original/*.pdf filter=lfs diff=lfs merge=lfs -text
data/original/**/*.pdf filter=lfs diff=lfs merge=lfs -text
data/processed/*.parquet filter=lfs diff=lfs merge=lfs -text
data/processed/*.db filter=lfs diff=lfs merge=lfs -text
```

Now `git add` on a matching file pushes the content to LFS and commits the pointer. `git clone` of the repo downloads pointers only; `git lfs pull` (or `git clone --recurse-submodules` with LFS configured) downloads the actual files.

### Per-file size limits by plan

| Plan | Per-file limit |
|---|---|
| GitHub Free | 2 GB |
| GitHub Pro | 2 GB |
| GitHub Team | 4 GB |
| GitHub Enterprise Cloud | 5 GB |

Files exceeding the per-file limit are rejected with a clear error. For artifacts larger than 5 GB — full Common Crawl snapshots, multi-region warehouse dumps — LFS is not the right tool; use [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github) for one-off attached binaries (per-file limit 2 GB but no LFS billing), [Zenodo](https://zenodo.org/) for citable archival (the PUDL pattern), or a separate object-storage bucket linked from `provenance.csv`.

### The critical caveat: LFS cannot be used with GitHub Pages

**Git LFS files do not work in GitHub Pages sites.** Pages serves content from the `gh-pages` branch directly; LFS pointers in that branch resolve to text-pointer-file content, not the underlying data. This is a hard architectural constraint, [documented in GitHub's docs](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage).

The implication for the layered publishing setup:

- The Quarto site (published to `gh-pages`) **cannot serve LFS-tracked data files directly.** A `docs/methodology.qmd` that tries to embed a 500 MB Parquet via a link will serve the LFS pointer text, not the data.
- The Quarto site **can embed small samples** of the data — the first 1000 rows committed as a regular file (not LFS-tracked) under `docs/` works fine.
- The Quarto site **can link out to the bulk data** hosted elsewhere — the Datasette deployment URL, a GitHub Release asset, a Zenodo DOI, an S3 bucket. The methodology page describes the data; the data itself lives where it can.

The natural division of labor:

- **`data/original/` LFS-tracked, in the main branch.** The pipeline reads from here. CI checks out with `lfs: true`. Not exposed to Pages.
- **`data/processed/<project>.db` built fresh during the Datasette publish step.** Deployed to Vercel/Fly/Cloud Run, *not* served from Pages. LFS plays no role here.
- **`data/processed/<project>.csv` and `.parquet`** — if small (<10 MB), regular Git; if large, LFS in main + small sample committed under `docs/` for the Quarto site to embed + a GitHub Release with the full file attached for direct download.
- **`docs/_freeze/` and rendered `_site/`** — never LFS; checked into Git normally so Pages serves them.

This works out to a clean three-deployment architecture: Pages serves the documentation, the Datasette platform serves the queryable data, and Releases (or Zenodo) serve the citable archival snapshots. Each surface plays to its strengths; nothing tries to serve LFS through Pages.

### LFS in CI

Workflows that need the actual data files must pull LFS in checkout:

```yaml
- uses: actions/checkout@v4
  with:
    lfs: true            # pull LFS-tracked files, not just pointers
```

This counts against the repo's LFS bandwidth quota. For projects with heavy CI activity (every PR triggers a full pipeline run with LFS data), this can exhaust the free 1 GB/month quickly. Mitigations:

- **Cache LFS objects** in CI: GitHub Actions caches `~/.cache/lfs` between runs.
- **Skip LFS in jobs that don't need it**: the test job that runs schema unit tests against `tests/fixtures/` doesn't need the full 5 GB of `data/original/`; the full pipeline job does.
- **Don't re-fetch on every commit**: the `refresh.yml` workflow that runs the pipeline against the upstream sources usually doesn't need LFS at all — it's *writing* new data to LFS, not reading existing data.

## Datasette Agent (alpha, May 2026)

[Datasette Agent](https://datasette.io/blog/2026/datasette-agent/) is a plugin (released May 21, 2026, alpha) that adds a conversational LLM interface to a Datasette instance. The agent uses the [LLM library](https://llm.datasette.io/) to support hundreds of tool-calling models — OpenAI, Anthropic, Gemini, and open-weight models via local providers like LM Studio or Ollama. Readers ask natural-language questions; the agent writes SQL and returns the result.

Local run for development:

```bash
uvx --prerelease=allow --with datasette-agent \
    datasette -s plugins.datasette-llm.default_model gpt-5.5 \
    --internal internal.db --root data/processed/elections.db
```

When the agent helps:

- **Reporter or researcher discovery.** Someone unfamiliar with the schema asks "which contests had the closest margins in 2020?" and gets a useful SQL query and answer.
- **Reducing the SQL barrier.** Datasette's SQL UI is excellent for people who write SQL; the agent extends usefulness to those who don't.
- **Schema exploration.** "What columns describe the candidate?" reads from `metadata.yaml` and the database schema together.

When the agent doesn't help, or hurts:

- **As a substitute for canned queries.** A frequently-asked question is better served by a canned query with a stable URL than by a per-request LLM call.
- **For high-stakes citation.** LLM-generated SQL may be subtly wrong (off-by-one filters, wrong join condition). For data that will be cited publicly, the human-written canned query is the durable artifact.
- **Without rate limiting and identity.** A public Datasette Agent without sign-in costs real money under any traffic spike. The Datasette Agent demo at `agent.datasette.io` requires GitHub auth precisely to manage abuse and cost.

Plugins for the agent worth knowing: [`datasette-agent-charts`](https://github.com/datasette/datasette-agent-charts) renders Observable Plot visualizations from the agent's responses; [`datasette-agent-openai-imagegen`](https://github.com/datasette/datasette-agent-openai-imagegen) generates images on request; [`datasette-agent-sprites`](https://github.com/datasette/datasette-agent-sprites) executes generated code in a sandbox.

For a stable civic dataset (election results, agency budgets), starting with a published Datasette without the agent and adding it later — once the metadata, canned queries, and faceting are solid — is the safer order.

## SQL patterns worth canning

A handful of SQL patterns recur across civic-data Datasette deployments. Code each one as a canned query in `metadata.yaml` and they become the stable read-paths for the dataset. (The PyCon SQLite tutorial's "Advanced SQL" chapter covers each in depth.)

### Aggregations by category and vintage

```sql
SELECT vintage, contest, SUM(votes) AS total_votes
FROM elections
WHERE votes IS NOT NULL
GROUP BY vintage, contest
ORDER BY vintage DESC, total_votes DESC
```

### CTEs for cross-vintage comparison

```sql
WITH by_year AS (
    SELECT vintage, contest, candidate, SUM(votes) AS votes
    FROM elections
    WHERE votes IS NOT NULL
    GROUP BY vintage, contest, candidate
)
SELECT a.contest, a.candidate,
       a.votes AS votes_2020, b.votes AS votes_2024,
       (b.votes - a.votes) AS delta
FROM by_year a
JOIN by_year b USING (contest, candidate)
WHERE a.vintage = '2020-general' AND b.vintage = '2024-general'
ORDER BY ABS(delta) DESC
```

### Window functions for year-over-year change

```sql
SELECT vintage, contest, candidate, SUM(votes) AS votes,
       SUM(votes) - LAG(SUM(votes)) OVER (
           PARTITION BY contest, candidate ORDER BY vintage
       ) AS change_from_prior
FROM elections
GROUP BY vintage, contest, candidate
ORDER BY contest, candidate, vintage
```

### Joining to provenance

```sql
SELECT e.vintage, e.contest, SUM(e.votes) AS total,
       p.source_url, p.retrieved_at, p.sha256
FROM elections e
JOIN provenance p USING (source, vintage)
WHERE e.contest = :contest
GROUP BY e.vintage, e.contest, p.source_url, p.retrieved_at, p.sha256
```

The `:contest` is a Datasette named parameter — when the canned query is published, the URL gets a form input letting readers fill it in.

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `sqlite-utils insert` reads numeric columns with leading zeros as `INTEGER` | Schema inference; column looked numeric | Pass `--text` for those columns, or `transform` after insert with `--type col TEXT` |
| Facets don't appear for a column with reasonable cardinality | Column not indexed; Datasette falls back to no-facet | Add an index via `sqlite-utils create-index`; declare in `metadata.yaml` `facets` list |
| Published Datasette shows raw HTML in a column | Plain-text rendering of HTML-containing column | Add `datasette-render-html` plugin and declare the column in metadata; or strip HTML during clean |
| Canned query times out under load | Inefficient SQL or missing index | `EXPLAIN QUERY PLAN <sql>` in the SQL view; add indexes or rewrite to avoid full scans |
| `datasette publish vercel` deploy succeeds but the page 500s | Plugin installed at deploy didn't pin a compatible version | Pin the plugin version in `--install datasette-cluster-map==0.18.2`; check the deploy logs |
| Full-text search returns no rows for an obviously-matching term | FTS index not refreshed after data update | Re-run `sqlite-utils enable-fts ... --replace` or use `sqlite-utils populate-fts` |
| Database file in deploy is stale | CI deployed before `scripts/publish.py build` ran | Make `build` a hard prerequisite of `datasette publish` in the workflow |
| Datasette Agent generates a query that joins to the wrong key | Provenance table not foreign-keyed; agent guesses | Add the foreign key with `sqlite-utils add-foreign-key`; refresh the schema-prompt the agent uses |
| Quarto GH Action fails with 403 on push to gh-pages | Workflow lacks `contents: write` permission | Add `permissions: contents: write` at workflow or job level |
| Quarto re-runs all code on every CI build, taking 20+ minutes | `_freeze/` not committed; freeze: auto not configured | Set `execute: freeze: auto` in `_quarto.yml`; run `quarto render` locally; commit `_freeze/` |
| `quarto publish gh-pages` fails: "branch does not exist" | First-time setup never run; GH Action depends on the branch already existing | Run `quarto publish gh-pages` once locally before relying on the Action |
| Quarto site shows pointer text instead of an embedded data file | LFS-tracked file referenced from a `.qmd`; Pages can't serve LFS | Move a small sample (non-LFS) under `docs/`; link to the Datasette URL or a Release for the full file |
| `git clone` of a fresh repo lacks data files | LFS not installed; only pointers were pulled | Contributor runs `git lfs install` once, then `git lfs pull` |
| LFS bandwidth quota exhausted mid-month | Heavy CI with `lfs: true` on every job | Cache LFS objects in CI; skip `lfs: true` on jobs that don't need raw data |
| File rejected at `git push`: "exceeds size limit" | File over 100 MB but not LFS-tracked | Add the pattern to `.gitattributes` *before* the first commit of the file; use `git lfs migrate` for retroactive conversion |

## What to write in the AGENTS.md

For each published Datasette deployment:

- **The build command and target.** `uv run python -m scripts.publish build` produces `data/processed/elections.db`; the deployment uses `datasette publish vercel ...`. Document the exact command (or the workflow file path) here.
- **The metadata source of truth.** "Per-column descriptions in `metadata.yaml` are generated from `docs/data-dictionary.md` by `scripts/publish.py`; do not edit `metadata.yaml` directly — edit the dictionary and rebuild."
- **The deployment surface.** The production URL, the Datasette Lite URL (if any), the CDN configuration, the auth posture (public read-only vs. authenticated).
- **The plugin set.** "Installed plugins: `datasette-cluster-map`, `datasette-render-markdown`, `datasette-vega`. The agent plugin is *not* enabled in production; see the design-decisions section for the rationale."
- **The canned-query catalog.** A short list of the canned queries in `metadata.yaml` and a sentence each on what they're for. New canned queries are the cheapest user-research signal — when the same SQL keeps getting re-derived in the chat with reporters, that's the next canned query to add.
- **The refresh workflow.** "Triggered by `refresh.yml` (Mondays 13:00 UTC); each successful refresh opens a PR with the new audit; merging the PR triggers `publish.yml`, which rebuilds `elections.db` and deploys to Vercel."

For the Quarto documentation site:

- **The site URL and source of truth.** "https://{owner}.github.io/{project}/; rendered from `docs/*.qmd` by `.github/workflows/gh-pages.yml` on every push to `main` that touches `docs/`, `_quarto.yml`, or `data/processed/`."
- **The `docs/` ↔ `metadata.yaml` split.** Which content lives in which surface, and how they're kept in sync (typically `scripts/publish.py` generates `metadata.yaml` from `docs/data-dictionary.md`).
- **The freeze policy.** "Code in `.qmd` files executes locally; `_freeze/` is committed; the GH Action re-renders without re-running code unless a `.qmd` source changes." Or, if executing in CI: "Action installs `uv`, syncs the project, and re-runs all code on every render — slower but always fresh."

For Git LFS:

- **What's tracked.** "All `data/original/**/*.pdf` and `data/processed/*.parquet` are LFS-tracked; see `.gitattributes`. Contributors must `git lfs install` once per machine before cloning."
- **The bandwidth posture.** "On GitHub Free, 1 GB/month bandwidth bundled; data pack purchased for the project's GitHub org as of {date}. CI jobs that don't need raw data skip `lfs: true` to conserve quota."
- **The Pages constraint.** "The Quarto site at `/gh-pages` does not serve LFS-tracked data; the methodology page links to GitHub Releases for full-file downloads and to the Datasette URL for queryable access."
- **Fallback if LFS budget is exceeded.** "Bulk Parquet downloads are mirrored to a GitHub Release per tagged version; the latest release is linked from `docs/index.qmd`."

This is what makes the published interface durable. The published Datasette instance, Quarto site, and Releases (or Zenodo, or LFS) together are the deployment surface for what the pipeline produces. AGENTS.md is where the connections between them are made explicit.
