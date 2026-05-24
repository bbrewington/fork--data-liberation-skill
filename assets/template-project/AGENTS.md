# AGENTS.md — {{ project_name }}

> Architecture brief and contribution guide. Read this first if you are
> coming to the project — human or AI assistant — and intend to add a
> source, fix a parser, change the schema, or update the deployment.

## What this project is

{{ description }}

This is a **data liberation pipeline** in the tradition of PUDL,
BoulderPublicData/Election-Results, and the IPEDS pipeline: immutable
originals on disk → per-source parsers → a single canonical tidy
deliverable, with provenance and audit reports versioned alongside.
The deliverable lives at `data/processed/{{ project_slug }}.csv` (and
`.parquet`, and `.db` for Datasette).

## Quickstart

```bash
uv sync                                          # install everything
uv sync --extra publish                          # also install Datasette + sqlite-utils
uv run pytest -q                                  # run the test suite
uv run python -m scripts.pipeline --help          # see all subcommands
uv run python -m scripts.pipeline run             # discover → fetch → clean → audit
uv run python -m scripts.publish build            # build SQLite for Datasette
uv run python -m scripts.publish serve            # serve Datasette locally on :8001
```

## Layout

| Path | What lives there |
|---|---|
| `scripts/` | Pipeline code. `pipeline.py` is the CLI entry; every other module is a phase. |
| `scripts/sources.py` | `Source` ABC with `discover` + `ingest` contract. |
| `scripts/parsers/` | Per-source-and-vintage parser modules. Each exposes `parse(path)`. |
| `scripts/schema.py` | Canonical column list + pandera schema. The contract parsers obey. |
| `scripts/concepts.py` | Cross-source harmonization (optional; multi-source projects only). |
| `scripts/publish.py` | SQLite + metadata.yaml builder; serves and deploys Datasette. |
| `data/original/` | Immutable raw downloads. Never edit in place. LFS-tracked for large files. |
| `data/processed/` | Tidy long-form deliverable + `.db` + `metadata.yaml` + `provenance.csv`. |
| `data/audit/` | Auto-generated; do not hand-edit. |
| `data/lookups/` | Hand-maintained crosswalks (FIPS, code systems, `concepts.yaml`). |
| `docs/` | Quarto site: `.qmd` files for methodology, tutorials, long-form dictionary. |
| `_quarto.yml` | Quarto site config. Renders to `_site/` (gitignored) and gh-pages branch. |
| `.gitattributes` | Git LFS rules — what gets stored via pointer files. |
| `.github/workflows/` | CI: tests on by default; refresh / publish / gh-pages opt-in. |

## Design decisions worth defending

**Tidy long, not wide.** One row per observation, one column per
variable, harmonization-by-concept-column. This makes cross-source
comparison and time-series analysis straightforward; the wide pivot is
a downstream consumer choice (see `docs/filter-pivot-recipes.md`).

**No imputation in the pipeline.** The pipeline emits what the sources
say; missingness is preserved. Imputation is the analyst's choice, not
ours to impose.

**`dtype=str` by default.** Leading zeros (precinct IDs, FIPS, ZIP)
survive a round trip through the pipeline. Numeric columns are
explicitly cast in the schema with nullable `Int64` so missingness is
preserved.

**Per-vintage parsers, not omnibus parsers.** When upstream layout
changes between years, branch by vintage. Don't pile cases into one
function — the readability cost compounds and the boundary cases get
missed.

**Errors are durable, not fatal.** A failing parser writes to
`data/audit/extraction_errors.json` and the pipeline continues. CI
fails when the audit shows new errors or `clean --fail-on-empty`
trips. This keeps a partial refresh useful while still surfacing
regressions loudly.

**Immutable originals.** `data/original/` is write-once. The pipeline
never edits in place; a new vintage is a new file under a new
directory.

**Three publish surfaces, not one.** Datasette is the *data
interface* (Vercel/Fly/Cloud Run); Quarto + GitHub Pages is the *prose
about the data*; LFS + Releases are the *bulk distribution* layer.
Each plays to its strengths. The architectural constraint that LFS
does not work with GitHub Pages is why these are three workflows
rather than one — see `references/toolchain-publishing.md` in the
data-liberation skill.

## Deployment surface

| Layer | Where | How |
|---|---|---|
| Documentation site | `https://{{ owner }}.github.io/{{ project_slug }}/` | `gh-pages.yml` workflow renders `docs/*.qmd` to gh-pages branch |
| Queryable data | `https://{{ project_slug }}.vercel.app/` (or Fly / Cloud Run) | `publish.yml` workflow runs `python -m scripts.publish deploy` |
| Bulk download | GitHub Releases attached to each tagged version | Manual via the GitHub UI, or `release.yml` if configured |

The `metadata.yaml` Datasette reads is generated from
`docs/data-dictionary.md` by `scripts/publish.py:generate_metadata`.
Edit the dictionary; rebuild; the published interface picks up the
new descriptions.

## Known limitations

(List the project's actual known limitations here as they accumulate.
Examples: a specific vintage uses scanned PDFs, certain columns are
imputed-but-not-marked, FIPS codes are missing for a subset of records.
This is the section reporters and downstream users read.)

## How to add a new source

1. Add a `Source` subclass to `scripts/sources.py` with `name`,
   `label`, and `discover` + `ingest` methods.
2. Register it in `scripts/config.py::SOURCES`.
3. Write per-vintage parser(s) under `scripts/parsers/<source>_<vintage>.py`,
   each exposing `parse(path: Path) -> pd.DataFrame`.
4. Add a small fixture under `tests/fixtures/<source>_<vintage>_small.<ext>`
   and a test under `tests/test_<source>_<vintage>.py`.
5. If this is a multi-source project introducing a new harmonization
   point, extend `data/lookups/concepts.yaml` with the new concept and
   document the caveats.
6. Run `uv run python -m scripts.pipeline run` and check the audit
   under `data/audit/summary-*.md`.

## How to add a new vintage

1. Add the new URL to `discover()` in the relevant `Source`.
2. Run `uv run python -m scripts.pipeline discover` and confirm it
   shows up.
3. Run `fetch` to pull it.
4. Run `clean` — if it errors, decide whether the change is a layout
   migration (new vintage-branch in the parser) or a quirk (handle in
   place).
5. Update `docs/changelog.qmd` with what changed and any new caveats.
6. Commit, preferably via PR with the audit diff visible.

## How to refresh the published Datasette + Quarto site

1. `uv run python -m scripts.pipeline run` (locally, to confirm
   nothing's broken).
2. `uv run python -m scripts.publish build` then
   `uv run python -m scripts.publish serve` to inspect locally.
3. Commit and push; `publish.yml` and `gh-pages.yml` (once enabled)
   deploy from main automatically.

## References

The Claude `data-liberation` skill at the root of this project
(or `/mnt/skills/user/data-liberation/` if used as a skill) contains
deeper references on:

- `references/data-modeling.md` — long vs. wide, dtypes, the concept catalog
- `references/discovery-and-audit.md` — recurring-refresh, reconcile, audit patterns
- `references/toolchain-publishing.md` — Datasette + Quarto + LFS in depth
- `references/project-template.md` — full skeleton spec
