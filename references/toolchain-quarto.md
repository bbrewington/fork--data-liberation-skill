# Toolchain: Quarto + GitHub Pages

The **documentation site** layer of a liberation project's three publishing surfaces (the queryable data interface is [`toolchain-datasette.md`](toolchain-datasette.md); bulk distribution is [`toolchain-lfs.md`](toolchain-lfs.md)).

[Quarto](https://quarto.org/) authors `.qmd` files (Markdown with executable code blocks in Python, R, Julia, or Observable JS), renders to HTML / PDF / Word, and publishes to GitHub Pages with one command. The result is a static site sitting alongside the GitHub repo, free to host, with clean URLs the project can cite.

## Why Quarto alongside Datasette

Datasette publishes the *data interface* — per-column metadata, faceted browsing, canned queries, SQL editor. Quarto publishes the *prose about how to use it* — methodology, long-form data dictionary, tutorials, change log, replication code. The split matches what readers want at different moments:

| Content | Lives in | Reason |
|---|---|---|
| Per-column description, units, controlled vocabulary | Datasette `metadata.yaml` | Renders inline with the column; readers see it where they need it |
| Long-form column rationale, vintage breakpoints, caveats | `docs/data-dictionary.qmd` | Too long for inline metadata; benefits from prose, links, examples |
| Canned queries with named parameters | Datasette `metadata.yaml` | Datasette renders these as forms; readers run them in the browser |
| Methodology essays, reconciliation logs, change log | `docs/*.qmd` | Static prose; readers consume sequentially, not query-by-query |
| The data itself | Datasette + CSV/Parquet downloads | The site is *about* the data, not a copy of it |

A small script in `scripts/publish.py` can read `docs/data-dictionary.md` (or `.qmd` front-matter + content) and emit `metadata.yaml`'s per-column descriptions, so the long form and the inline form stay in sync.

## Minimum viable Quarto setup

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
- `docs/data-dictionary.qmd` — the long-form column-by-column reference.
- `docs/filter-pivot-recipes.qmd` — pandas + tidyverse + Excel recipes, with executable code blocks that run against a small sample of the data committed to the repo.
- `docs/methodology.qmd` — how the data was extracted, what's known to be incomplete, the reconciliation log, the cross-source caveats from the concept catalog.
- `docs/changelog.qmd` — what changed in each vintage, what schema migrations happened, what's deprecated.

This is the documentation a journalist or researcher reads *before* opening the CSV.

## Publishing with `quarto publish gh-pages` (one-time setup)

Quarto needs a one-time local setup to create the `gh-pages` branch — this isn't optional, because the GitHub Action below relies on the branch already existing:

```bash
quarto publish gh-pages
```

That command renders the site, creates a `gh-pages` orphan branch with just the rendered output, pushes it, and (for project sites) GitHub auto-configures Pages to serve from it. The URL is `https://<owner>.github.io/<repo>/`. Custom domains work via a `CNAME` file at the project root — see [Quarto's GitHub Pages docs](https://quarto.org/docs/publishing/github-pages.html) for the details.

## Automated publishing via GitHub Actions

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
          lfs: true            # pull LFS pointers (see toolchain-lfs.md)

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
- **`quarto-dev/quarto-actions/setup@v2`** then **`publish@v2 target: gh-pages`** — the two-step canonical pattern. `publish@v2` renders before pushing by default; set `render: false` if rendering happens elsewhere.
- **`paths:` filter** — rerender only when `docs/`, `_quarto.yml`, or the data itself changes. Avoids spurious rebuilds.
- **`with: lfs: true`** — pulls Git LFS-tracked files so the Quarto site can embed sample data.

The `_freeze/` directory (created by `quarto render` with `freeze: auto`) should be committed to version control. It stores executed-code outputs so the GH Action only re-runs the code that actually changed, not the entire site every time. The PyCon SQLite tutorial's published instance uses this pattern.

## The LFS-and-Pages constraint

**Git LFS files do not work in GitHub Pages sites.** Pages serves content from the `gh-pages` branch directly; LFS pointers in that branch resolve to text-pointer-file content, not the underlying data. This shapes what the Quarto site can serve:

- The Quarto site **cannot serve LFS-tracked data files directly.** A `docs/methodology.qmd` that tries to embed a 500 MB Parquet via a link will serve the LFS pointer text, not the data.
- The Quarto site **can embed small samples** of the data — the first 1000 rows committed as a regular file (not LFS-tracked) under `docs/` works fine.
- The Quarto site **can link out to the bulk data** hosted elsewhere — the Datasette deployment URL, a GitHub Release asset, a Zenodo DOI, an S3 bucket. The methodology page describes the data; the data itself lives where it can.

See [`toolchain-lfs.md`](toolchain-lfs.md) for the full LFS architecture and the per-plan size limits.

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| Quarto GH Action fails with 403 on push to gh-pages | Workflow lacks `contents: write` permission | Add `permissions: contents: write` at workflow or job level |
| Quarto re-runs all code on every CI build, taking 20+ minutes | `_freeze/` not committed; `freeze: auto` not configured | Set `execute: freeze: auto` in `_quarto.yml`; run `quarto render` locally; commit `_freeze/` |
| `quarto publish gh-pages` fails: "branch does not exist" | First-time setup never run; GH Action depends on the branch already existing | Run `quarto publish gh-pages` once locally before relying on the Action |
| Quarto site shows pointer text instead of an embedded data file | LFS-tracked file referenced from a `.qmd`; Pages can't serve LFS | Move a small sample (non-LFS) under `docs/`; link to the Datasette URL or a Release for the full file |
| `.md` files in `docs/` render with the site title instead of their own | Missing YAML frontmatter | Add `---\ntitle: "Page title"\n---` at the top |

## What to write in the AGENTS.md

- **Site URL and source of truth** — `https://<owner>.github.io/<project>/`, rendered from `docs/*.qmd` by `.github/workflows/gh-pages.yml`.
- **`docs/` ↔ `metadata.yaml` split** — which content lives where, and how they're kept in sync (typically `scripts/publish.py` generates `metadata.yaml` from `docs/data-dictionary.md`).
- **Freeze policy** — code in `.qmd` files executes locally with `_freeze/` committed, or re-runs in CI on every render (slower but always fresh).
