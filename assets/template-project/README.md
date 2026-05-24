# {{ project_name }}

{{ description }}

A reproducible data-liberation pipeline producing a tidy long-form
dataset from public sources, with provenance, audit reports, an
interactive [Datasette](https://datasette.io/) instance, and a
methodology site rendered with [Quarto](https://quarto.org/) on
GitHub Pages.

## A peek at the data

| source | vintage | observation_id | concept | ... |
|---|---|---|---|---|
| example | 2023 | a | temperature | ... |
| example | 2023 | b | temperature | ... |
| example | 2024 | c | _(null)_ | ... |

Full schema in [`docs/data-dictionary.md`](docs/data-dictionary.md);
sample recipes for pandas / R / Excel in
[`docs/filter-pivot-recipes.md`](docs/filter-pivot-recipes.md).

## How to use it

### Browse it

The published Datasette instance is at:

> **`https://{{ project_slug }}.vercel.app/`** *(replace with your actual URL after first deploy)*

Click into the `{{ project_slug }}` table to browse. The faceting on
the left filters by `source`, `vintage`, and other categorical
columns; the SQL editor at the top runs arbitrary queries; every
view has a `.csv` and `.json` sibling for downstream tooling.

### Read about it

The methodology site at
**`https://{{ owner }}.github.io/{{ project_slug }}/`** has:

- A long-form data dictionary with vintage breakpoints and caveats
- How the pipeline extracts and reconciles each source
- Per-vintage changelog
- Citation guidance

### Load it into pandas

```python
import pandas as pd
df = pd.read_parquet("data/processed/{{ project_slug }}.parquet")
# or, from the published instance directly:
df = pd.read_csv("https://{{ project_slug }}.vercel.app/{{ project_slug }}/{{ project_slug }}.csv?_size=max")
```

### Load it into R

```r
library(arrow)
df <- read_parquet("data/processed/{{ project_slug }}.parquet")
# or from the published instance:
df <- readr::read_csv("https://{{ project_slug }}.vercel.app/{{ project_slug }}/{{ project_slug }}.csv?_size=max")
```

## Movement context

This project participates in a longer tradition of public-interest
data liberation: the Sunlight Foundation's mid-2010s push to make
government data machine-readable; the [PUDL](https://catalystcoop-pudl.readthedocs.io/)
energy-data project; the Boulder Public Data
[Election-Results](https://github.com/BoulderPublicData/Election-Results)
and adjacent repos. See the `data-liberation` Claude skill's
`references/movement-history.md` for the broader landscape.

## Reproducibility

Everything is reproducible from clone:

```bash
git clone https://github.com/{{ owner }}/{{ project_slug }}.git
cd {{ project_slug }}
git lfs install                                     # if not already
git lfs pull                                        # pull large files
uv sync                                             # install Python deps
uv run python -m scripts.pipeline run               # rebuild data/processed/
```

The same input produces an identical SQLite file; that's the
[Baked Data](https://simonwillison.net/2021/Jul/28/baked-data/)
pattern.

## Refresh schedule

Configured via `.github/workflows/refresh.yml` (rename from
`.disabled` to enable). Default cadence: weekly on Mondays at
13:00 UTC. Each successful refresh opens a PR with the new audit;
merging triggers re-deploy of both the Datasette instance and the
methodology site.

## Citation

```bibtex
@misc{{{ project_slug }},
  author = {{{ author }}},
  title  = {{{{ project_name }}}},
  year   = {{2026}},
  note   = {{Liberated dataset}},
  url    = {{https://github.com/{{ owner }}/{{ project_slug }}}}
}
```

## License

- **Data:** [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/)
- **Code:** [MIT](LICENSE)

If you cite or republish, please link back to this repository and to
the upstream sources documented in `data/processed/provenance.csv`.

## Contributing

See [`AGENTS.md`](AGENTS.md) for architecture, conventions, and how
to add a new source or vintage. Issues and PRs welcome.
