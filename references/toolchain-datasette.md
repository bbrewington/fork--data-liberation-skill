# Toolchain: Datasette + sqlite-utils

The **queryable data interface** layer of a liberation project's four publishing surfaces (the other three: [`toolchain-quarto.md`](toolchain-quarto.md) for documentation, [`toolchain-lfs.md`](toolchain-lfs.md) for bulk distribution, [`toolchain-documentcloud.md`](toolchain-documentcloud.md) for the source documents with reader-facing OCR + embeds + permalinks).

[Datasette](https://datasette.io/) turns a SQLite database into a queryable web app with SQL editor, facet browsing, JSON API, and one-command deploy. [`sqlite-utils`](https://sqlite-utils.datasette.io/) is the workhorse for getting tidy CSV/Parquet into SQLite. The patterns here come from the [PyCon 2023 SQLite tutorial](https://sqlite-tutorial-pycon-2023.readthedocs.io/) and Simon Willison's "Baked Data" architecture that powers Niche Museums, TILs, and PUDL's published instance.

## Why Datasette for liberated data

The CSV-only baseline asks every downstream user to repeat the same setup work — load it, declare dtypes, build the joins to provenance, write the filter expressions. Datasette delivers all of that as a deployed read-only web app:

- **SQL in the browser.** Any reader can write SQL against the published database, including joins across tables, full-text search, and JSON output. Civic-data consumers (reporters, advocates, students) who would never install pandas can query a Datasette site fine.
- **Faceted browsing.** Categorical columns get per-value facets automatically — readers click "Boulder County" to filter, then "2024" to filter further, and the URL captures the state. The query is shareable; the result is citable.
- **JSON API for free.** Every table view and SQL query has a `.json` (and `.csv`) sibling. Downstream pipelines, Observable notebooks, and journalism teams pin against the URL rather than re-fetching the source.
- **Metadata as documentation.** Per-database, per-table, and per-column descriptions render alongside the data — the data dictionary travels with the database file.
- **One-command publishing.** `datasette publish` deploys to Google Cloud Run, Heroku, Vercel, or Fly with a single command.

## From processed data to SQLite

`sqlite-utils` is the workhorse. (The older [`csvs-to-sqlite`](https://datasette.io/tools/csvs-to-sqlite) is unmaintained; use `sqlite-utils` instead.)

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

Patterns worth memorizing:

- **`--pk` declares the composite primary key.** Datasette uses this for clean per-row URLs and pagination.
- **`--alter` lets a second insert append columns** — useful when a new vintage introduces new columns.
- **`--ignore` / `--replace` handle re-runs.** `--ignore` skips rows whose PK already exists; `--replace` overwrites.
- **Foreign keys connect tables.** `sqlite-utils add-foreign-key elections.db elections source provenance source` lets Datasette render the link as a clickable cross-table reference.

### Indexes

For tables of more than a few thousand rows, declare indexes on the columns readers will filter or facet by:

```bash
uvx sqlite-utils create-index data/processed/elections.db elections vintage
uvx sqlite-utils create-index data/processed/elections.db elections source
uvx sqlite-utils create-index data/processed/elections.db elections "contest, vintage"
```

Without indexes, Datasette's facet generation falls back to full-table scans, which gets slow above ~50k rows.

### Full-text search

For narrative columns (FOIA response text, candidate biographies, agency descriptions), enable SQLite FTS5:

```bash
uvx sqlite-utils enable-fts data/processed/elections.db elections candidate contest
```

The Datasette table view picks this up automatically and exposes a search box.

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

Wire this into the pipeline driver as `uv run python -m scripts.publish build`. The `elections.db` file is then a reproducible artifact: any commit + uv environment regenerates an identical database file.

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

The `uvx --with` pattern installs Datasette plus plugins into an ephemeral environment without polluting the project's `pyproject.toml`.

## Metadata: the documentation surface that travels with the data

Datasette reads a YAML or JSON file describing the dataset — title, license, source, per-table descriptions, per-column descriptions, canned queries. This is what readers see at the top of every page.

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
        sql: |
          SELECT vintage, contest, SUM(votes) AS total_votes
          FROM elections
          WHERE votes IS NOT NULL
          GROUP BY vintage, contest
          ORDER BY vintage DESC, total_votes DESC
```

Three patterns to lean into:

- **Mirror `docs/data-dictionary.md` column descriptions into `metadata.yaml`.** The dictionary is the source of truth (see [`data-modeling.md`](data-modeling.md#data-dictionary) for the per-column template); the metadata file is the published projection. A small `scripts/publish.py` step can read the dictionary and emit the metadata to keep them in sync.
- **Use `facets` to pre-declare browsable categoricals.** Datasette will auto-detect facetable columns, but declaring them sets the default view readers see first.
- **Write canned queries for the questions readers will ask.** Per-contest totals, year-over-year change, top-N. Each canned query gets a clean URL anyone can cite.

This `metadata.yaml` is already a **DCAT** / **DCAT-US**-shaped catalog record (the project is a Catalog, the database a Dataset, the CSV/SQLite/JSON-API its Distributions). For a project that needs to federate into a `data.gov`-style catalog, `scripts/publish.py` can emit a `dcat-us.jsonld` record from the same dictionary — optional, covered in [`open-data-standards.md`](open-data-standards.md#crosswalk-standards--what-the-skill-already-builds). Background, never a publishing prerequisite.

This matters most when the real audience is an **institutional portal** rather than a standalone site. Much of the world's government data is published through **CKAN** (the open-source platform behind data.gov and many national catalogs) or **Socrata**, both of which harvest DCAT records. A self-hosted Datasette is the right activist MVP; a DCAT record is the bridge when a city or agency open-data program wants the dataset in *their* catalog. The two are different endpoints — pick the one the audience actually uses. The portal/federation landscape is mapped in [`open-government-landscape.md`](open-government-landscape.md#institutional-publishing-the-portal-layer).

### `metadata.yaml` vs `datasette.yaml` (Datasette 1.0a8+)

In the 1.0 alpha series, Datasette splits configuration into two files. **`metadata.yaml`** keeps dataset-identity content (title, description, license, source, per-table/column descriptions, canned queries). **`datasette.yaml`** carries server configuration (plugin settings, permissions, settings that used to live in `metadata.yaml`). 0.x deployments keep both in `metadata.yaml`. See the [annotated release notes for 1.0a8](https://docs.datasette.io/en/latest/changelog.html#a8-2024-02-07) to decide which file each setting belongs in. The pragmatic rule: civic projects on a stable footing should stay on 0.x and a single `metadata.yaml` until 1.0 ships stably.

## Plugins worth knowing for civic data

| Plugin | What it adds | When to use |
|---|---|---|
| [`datasette-cluster-map`](https://datasette.io/plugins/datasette-cluster-map) | Renders any table with `latitude` and `longitude` columns as a clustered map. | Geospatial liberated data — incident logs, facility lists, polling places. |
| [`datasette-render-markdown`](https://datasette.io/plugins/datasette-render-markdown) | Renders Markdown in designated columns. | FOIA case logs, narrative descriptions, agency response text. |
| [`datasette-vega`](https://datasette.io/plugins/datasette-vega) | Lets readers chart query results with Vega-Lite. | Any time-series, any per-category comparison. |
| [`datasette-graphql`](https://datasette.io/plugins/datasette-graphql) | Exposes a GraphQL API alongside the REST/JSON one. | Downstream consumers that prefer GraphQL. |
| [`datasette-search-all`](https://datasette.io/plugins/datasette-search-all) | One search box across every FTS-enabled table. | Multi-table corpora (FOIA collections, legislative records). |
| [`datasette-copyable`](https://datasette.io/plugins/datasette-copyable) | Adds copy-to-clipboard for rows in CSV / TSV / Markdown. | Reporter workflows: read row, paste into draft. |

Install plugins into the deployment by adding `--install <plugin>` to `datasette publish` or by listing them in `pyproject.toml`'s `publish` extras group.

## The "Baked Data" pattern

The right architecture for liberated civic data: the database is built fresh during the deploy step from the source CSVs, and the deployed instance is read-only. No application-layer writes; no separate database server. See Simon Willison's [Baked Data architecture](https://sqlite-tutorial-pycon-2023.readthedocs.io/en/latest/baked-data.html); Niche Museums and TILs are the canonical examples.

This is the right architecture for liberated civic data specifically because:

- **The dataset is the deliverable.** Every cycle of `clean → audit → publish` produces a new version of the SQLite file. There's no user-generated content layered on top.
- **Cache headers can be aggressive.** A static-like artifact behind a CDN serves at near-zero cost per request, even under journalism-driven traffic spikes.
- **Versioning is automatic.** Each deploy is a new build; the git commit hash and the SQLite file's sha256 together cite a specific dataset version.
- **Reverting is trivial.** A bad refresh produced a broken database? Roll back the deploy.

Implementation: the publishing workflow runs `scripts/publish.py build` (which produces `data/processed/elections.db`) and then `datasette publish <provider>` with the freshly-built database. The pipeline runs in CI; the result is a deploy.

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

Builds a Docker image, deploys it, returns a URL. Cloud Run's free tier handles small-traffic civic sites for free.

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

For most civic projects, the choice is between Datasette Lite (one-off or small datasets) and Vercel or Fly (ongoing deployments under a custom domain). Cloud Run is right when the project is already in a GCP environment.

A pattern worth considering: ship to Datasette Lite for the "always available" demo URL, and to Vercel or Fly for the canonical production instance. The Lite URL works even when the production deploy is rebuilding.

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
- **Without rate limiting and identity.** A public Datasette Agent without sign-in costs real money under any traffic spike.

For a stable civic dataset, starting with a published Datasette without the agent and adding it later — once the metadata, canned queries, and faceting are solid — is the safer order.

## SQL patterns worth canning

Code these as canned queries in `metadata.yaml` and they become the stable read-paths for the dataset. (The PyCon SQLite tutorial's "Advanced SQL" chapter covers each in depth.)

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

## What to write in the AGENTS.md

- **Build command and target** — exact `scripts.publish build` invocation that produces the `.db`, and the deployment command (or workflow path) that ships it.
- **Metadata source of truth** — typically `docs/data-dictionary.md`, generated into `metadata.yaml` by `scripts/publish.py`; warn readers not to edit `metadata.yaml` by hand.
- **Deployment surface** — production URL, Datasette Lite URL if any, auth posture.
- **Plugin set** — which plugins are installed in production and why; explicitly note whether Datasette Agent is enabled.
- **Canned-query catalog** — short list of named queries in `metadata.yaml` with one sentence each on what they're for. New canned queries are the cheapest user-research signal.
- **Refresh workflow** — what triggers a redeploy (typically merging a refresh PR).
