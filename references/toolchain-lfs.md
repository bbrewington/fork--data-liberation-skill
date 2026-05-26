# Toolchain: Git LFS for large datasets

The **bulk distribution** layer of a liberation project's four publishing surfaces (queryable data interface: [`toolchain-datasette.md`](toolchain-datasette.md); documentation site: [`toolchain-quarto.md`](toolchain-quarto.md); reader-facing source-document hosting with OCR + embeds + permalinks: [`toolchain-documentcloud.md`](toolchain-documentcloud.md)). LFS dumps raw artifacts as opaque downloadable files; DocumentCloud renders them with a reader UI — pick the right one for the source by the *reader want* (tarball vs page-anchored permalink).

A liberation project accumulates two kinds of files that strain ordinary Git: large source artifacts (full-resolution scanned PDFs, multi-gigabyte XML dumps, archive ZIPs) and large processed outputs (multi-million-row Parquet files). GitHub politely rejects files over 100 MB and *recommends* keeping repos under 1 GB total. [Git Large File Storage (LFS)](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage) is the escape hatch: Git tracks a small pointer file (sha256 + size, ~130 bytes), and the actual content lives on a separate LFS server that GitHub provides.

## When LFS earns its keep

- **`data/original/` artifacts over ~25 MB.** Election Statement of Vote PDFs from large counties; full-resolution scanned annual reports; agency document-dump ZIPs.
- **Processed Parquet files over ~100 MB.** Multi-million-row tidy long-form outputs; multi-decade longitudinal datasets.
- **Reproducible build artifacts.** A SQLite database that's expensive to rebuild (hours of OCR or scraping) and that downstream users want to clone-and-go.

When LFS doesn't earn its keep:

- **The processed CSV is under 10 MB.** Standard Git handles it fine, with the diff history downstream users actually want.
- **The source artifact can be re-fetched.** A small fetch script + a URL in `provenance.csv` is more durable than an LFS pointer that depends on GitHub's LFS billing remaining favorable.

The single most-cited disadvantage of LFS for civic projects: it imposes a billing dependency on GitHub. The free plan ships with 1 GB storage and 1 GB/month bandwidth bundled; data packs cost real money beyond that. For a project that may outlive a particular developer's GitHub account, this is a coupling worth understanding.

## Setting up LFS

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

## Per-file size limits by plan

| Plan | Per-file limit |
|---|---|
| GitHub Free | 2 GB |
| GitHub Pro | 2 GB |
| GitHub Team | 4 GB |
| GitHub Enterprise Cloud | 5 GB |

Files exceeding the per-file limit are rejected with a clear error. For artifacts larger than 5 GB — full Common Crawl snapshots, multi-region warehouse dumps — LFS is not the right tool; use [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github) for one-off attached binaries (per-file limit 2 GB but no LFS billing), [Zenodo](https://zenodo.org/) for citable archival (the PUDL pattern), or a separate object-storage bucket linked from `provenance.csv`.

## The critical caveat: LFS cannot be used with GitHub Pages

**Git LFS files do not work in GitHub Pages sites.** Pages serves content from the `gh-pages` branch directly; LFS pointers in that branch resolve to text-pointer-file content, not the underlying data. This is a hard architectural constraint, [documented in GitHub's docs](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage).

The implication for the layered publishing setup:

- The Quarto site (published to `gh-pages`) **cannot serve LFS-tracked data files directly.** A `docs/methodology.qmd` that tries to embed a 500 MB Parquet via a link will serve the LFS pointer text, not the data.
- The Quarto site **can embed small samples** of the data — the first 1000 rows committed as a regular file (not LFS-tracked) under `docs/` works fine.
- The Quarto site **can link out to the bulk data** hosted elsewhere — the Datasette deployment URL, a GitHub Release asset, a Zenodo DOI, an S3 bucket.

The natural division of labor:

- **`data/original/` LFS-tracked, in the main branch.** The pipeline reads from here. CI checks out with `lfs: true`. Not exposed to Pages.
- **`data/processed/<project>.db` built fresh during the Datasette publish step.** Deployed to Vercel/Fly/Cloud Run, *not* served from Pages. LFS plays no role here.
- **`data/processed/<project>.csv` and `.parquet`** — if small (<10 MB), regular Git; if large, LFS in main + small sample committed under `docs/` for the Quarto site to embed + a GitHub Release with the full file attached for direct download.
- **`docs/_freeze/` and rendered `_site/`** — never LFS; checked into Git normally so Pages serves them.

This works out to a clean three-deployment architecture: Pages serves the documentation, the Datasette platform serves the queryable data, and Releases (or Zenodo) serve the citable archival snapshots. Each surface plays to its strengths; nothing tries to serve LFS through Pages.

## LFS in CI

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

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| Quarto / Pages site shows pointer text instead of an embedded data file | LFS-tracked file referenced from a `.qmd`; Pages can't serve LFS | Move a small sample (non-LFS) under `docs/`; link to the Datasette URL or a Release for the full file |
| `git clone` of a fresh repo lacks data files | LFS not installed; only pointers were pulled | Contributor runs `git lfs install` once, then `git lfs pull` |
| LFS bandwidth quota exhausted mid-month | Heavy CI with `lfs: true` on every job | Cache LFS objects in CI; skip `lfs: true` on jobs that don't need raw data |
| File rejected at `git push`: "exceeds size limit" | File over 100 MB but not LFS-tracked | Add the pattern to `.gitattributes` *before* the first commit of the file; use `git lfs migrate` for retroactive conversion |

## What to write in the AGENTS.md

- **What's tracked** — globs in `.gitattributes`; the one-line contributor note that `git lfs install` is required.
- **Bandwidth posture** — Free / Pro / Team plan and any purchased data packs; which CI jobs skip `lfs: true` to conserve quota.
- **Pages constraint** — note explicitly that the Quarto site doesn't serve LFS; what it links to instead (Datasette URL, Releases).
- **Fallback if LFS budget is exceeded** — typically a mirror to GitHub Releases per tagged version, or Zenodo for citable archival.
