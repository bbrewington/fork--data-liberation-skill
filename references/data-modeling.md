# Data Modeling: Schema, Dictionary, Concepts, Provenance, Validation

This reference covers what happens *after* extraction: how to reshape the rows, how to document them so someone else can use them, how to harmonize across sources, how to validate the result, and how to keep the audit trail intact. The decisions made here are what separate a liberated dataset from a private spreadsheet.

The conventions in this reference are distilled from PUDL, the [IPEDS pipeline](https://github.com/BrianMKeegan/ipeds-pipeline), and BoulderPublicData's Election-Results — three projects that converged on the same answers from different problem domains.

## Wickham-tidy as the storage shape

The canonical storage shape is **one row per observation, one column per variable, one cell per value**, per [Wickham 2014](https://www.jstatsoft.org/article/view/v059i10). Every column is a variable; every row is an observation; data of distinct kinds live in separate tables.

In a liberation project, this means:

- **One CSV** in `data/processed/` is the dataset. Each row is one observation, identified by a composite key (`source`, `vintage`, plus whatever domain key — `precinct`/`contest`/`candidate`, `unitid`/`year`/`variable`, etc.).
- A **second CSV** in `data/processed/provenance.csv` is the per-extract sidecar, keyed on `(source, vintage)`. See [Provenance](#provenance) below.
- A **third CSV** or YAML in `data/lookups/concepts.{csv,yaml}` (or a Python module `scripts/concepts.py`) carries the harmonization metadata when the project is multi-source. See [Concept catalogs](#concept-catalogs).

Why long form, given that nobody wants to *read* a long-form CSV?

- **Unions are trivial.** A new vintage is more rows, not more columns. A new source is more rows. The schema stays put.
- **Auditing is uniform.** Null rates, distinct counts, dtype conformance — the audit code runs the same against every column regardless of source or vintage.
- **Cross-source comparison is a `groupby`.** Once two sources have entries on the same concept, comparing them is one pandas call.
- **The wide views readers want are recipes, not schemas.** `docs/filter-pivot-recipes.md` (see [below](#filter-pivot-recipes)) is how analysts get the year × variable matrix.

### When wide is the natural primary

A few domains genuinely have a wide-as-primary unit of observation. Cast-Vote-Records are the canonical example: one row per ballot, one column per contest, the ballot is the observation. Forcing CVR into long form (one row per ballot × contest) bloats the dataset by 30–50× with no analytical benefit because nobody analyzes ballots one contest at a time.

The rule: if the row-as-observation cardinality is naturally small (≤ ~50 columns) and contests/variables are analytically inseparable, keep wide. Still emit a tidy long-form derivative for cross-source analysis if the project participates in a multi-source comparison. BoulderPublicData/Cast-Vote-Records does both.

## The canonical schema

`scripts/schema.py` declares the columns once and provides a normalization helper. Sketch:

```python
# scripts/schema.py
from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing.pandas import DataFrame, Series

# The canonical column list. Every parser emits these (plus domain columns).
LONG_COLUMNS = [
    "source",          # registry slug; joins to provenance
    "vintage",         # year or version
    # ── identifying columns (domain-specific) ──
    "precinct",
    "contest",
    "candidate",
    # ── measurement column(s) ──
    "votes",
    # ── optional harmonization ──
    "concept",         # cross-source concept key, nullable
]


class CanonicalLong(pa.DataFrameModel):
    source: Series[str]
    vintage: Series[str]                       # string — vintages aren't always years
    precinct: Series[str] = pa.Field(nullable=True)
    contest: Series[str]
    candidate: Series[str] = pa.Field(nullable=True)
    votes: Series[pd.Int64Dtype] = pa.Field(ge=0, nullable=True)
    concept: Series[str] = pa.Field(nullable=True)

    class Config:
        strict = True
        coerce = True


def normalize_long(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce a parser's raw output to the canonical schema.

    Parsers may produce extra columns during cleaning; this helper drops
    them, reorders to LONG_COLUMNS, coerces dtypes, and validates.
    """
    missing = [c for c in LONG_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"normalize_long: missing required columns: {missing}")
    df = df[LONG_COLUMNS].copy()
    return CanonicalLong.validate(df)
```

Two design choices worth defending:

- **`vintage` is a string.** Years aren't always integers (`"2024-Q1"`, `"2024-special-recall"`), and even when they are, treating them as strings prevents accidental arithmetic and preserves the natural ordering for sort.
- **`Int64` (nullable) over `int64` (numpy-backed).** Vote counts, enrollment counts, dollar amounts — all are non-negative integers, but they're frequently missing for legitimate reasons (suppressed cells, year-not-reported). Nullable integers keep zero and NA distinct.

The schema goes *inside* the parser pipeline, not at the consumer boundary. Validation at write time is the gate; consumers read a validated artifact.

## Data dictionary

Hand-maintained, one entry per column. Lives at `docs/data-dictionary.md`. The IPEDS pipeline's `DATA_DICTIONARY.md` is the model.

Template per column:

```markdown
## `<column_name>`

- **Type:** `<dtype>` (one of: `string`, `Int64`, `Float64`, `boolean`, `date`, `datetime`)
- **Description:** One or two sentences in plain English. Avoid jargon the data dictionary itself doesn't define.
- **Source(s):** Which `source` slugs contribute this column, and where in their original schema it comes from.
- **Vocabulary / units:** If categorical, the controlled vocabulary. If numeric, the units. If a code, the code system (FIPS, NCES, ISO 3166-2, agency-internal).
- **Known caveats:** Vintage breakpoints, definitional shifts, ID-format changes, sentinel values.
- **Crosswalks:** Joining lookup tables in `data/lookups/`, if any.
```

Caveats are what make the dictionary worth maintaining. *"2022's roster ID format changed from `R######` to `R21-######`, so roster IDs are not safely comparable across that boundary"* is the kind of note that prevents a downstream user from joining incorrectly across the breakpoint. Inventing the convention is cheap; maintaining it discipline.

The dictionary's mechanical complement is `docs/variables.{md,csv}`, **auto-generated** by `scripts/audit.py` from the data itself (dtype, distinct count, null rate, min/max for numeric, five sample values for categorical). Treat the auto-generated file as the dictionary's sanity check: if `variables.csv` says a column is `object` but the dictionary says `Int64`, one is wrong, and it's usually the parser.

## Concept catalogs

When two or more sources measure the same underlying thing under different names — IPEDS reports total fall enrollment as `EFTOTLT`, the Colorado Department of Higher Education reports it as `TOTAL_HEADCOUNT`, the institution's own factbook calls it `fall_census_total` — the harmonization happens through a **concept catalog**.

A concept catalog is *not* a rename map. A rename map is a foot-gun: it asserts equivalence without documenting the disagreements. A concept catalog is a structured record that for each concept declares:

1. The canonical concept name.
2. Which source variables map to it, per source × vintage.
3. **The caveats** — what is and is not comparable across those mappings.

The [IPEDS pipeline's `concepts.py`](https://github.com/BrianMKeegan/ipeds-pipeline) is the canonical model. Sketch in YAML form for projects that prefer a data-only catalog at `data/lookups/concepts.yaml`:

```yaml
- concept: enrollment.headcount_fall_total
  description: Total fall headcount enrollment, all students, all levels.
  sources:
    ipeds:
      vintages: [2010-, ]
      variable: EFTOTLT
      survey: EF
      notes: Census-date snapshot, fall term.
    cdhe:
      vintages: [2018-, ]
      variable: TOTAL_HEADCOUNT
      notes: Reported per-institution to the state Department of Higher Education.
  caveats:
    - "IPEDS' Non-Resident Alien category is wider than CDHE's Non-Resident
       category (CDHE excludes students on humanitarian visas); breakdowns
       by residency are NOT cross-source comparable, but the total is."
    - "CDHE data is not available before 2018; do not infer the IPEDS-only
       years as comparable in any sense to the later joint period."
```

Three patterns worth holding to:

- **Concepts carry caveats, always.** A concept with `caveats: []` is suspicious; either the comparison genuinely is clean (rare for multi-source civic data) or someone hasn't done the comparison carefully.
- **Vintage-bounded source mappings.** A source's variable name and definition can change mid-period. The concept entry records *which vintages of a source map to this concept*, not just the source as a whole.
- **The catalog is queried, not just read.** `scripts/concepts.py` should expose `concept_for(source, vintage, variable) -> str` and `caveats_for(concept) -> list[str]` so the pipeline can attach the harmonized `concept` column at clean time and the audit can flag missing caveats.

For single-source projects, no concept catalog is needed — the column names of the source *are* the concepts. The catalog earns its keep when the project crosses two sources or merges multiple agencies' data.

## Provenance

The audit trail. Three rules:

1. **Per-extract, not per-row.** Source URL, retrieval timestamp, sha256, extraction quality, extraction notes — these are properties of an *extract* (a source × vintage pull), not of every cell. Carrying them on every row inflates the deliverable for no analytical benefit. Sidecar instead.

2. **Sidecar at `data/processed/provenance.csv`.** One row per `(source, vintage)`. Joined on demand. Columns:

   | Column | Type | Description |
   |---|---|---|
   | `source` | string | Source slug; joins to processed CSV |
   | `vintage` | string | Vintage; joins to processed CSV |
   | `source_url` | string | Where the original was fetched |
   | `retrieved_at` | datetime UTC | When it was fetched |
   | `sha256` | string | Content hash of the original artifact |
   | `extraction_quality` | string | One of `clean`, `caveats`, `degraded`, `ocr_tesseract` |
   | `extraction_notes` | string | Free text — vintage drift, OCR fallback used, etc. |
   | `parser_module` | string | Which parser file was used (`scripts.parsers.boulder_sov_2009`) |

3. **Per-row hashes only when the parser legitimately needs them.** If a parser is OCR-fragile and you want each row to declare which source PDF it came from at the page level, add `source_file_sha256` and `page` as columns. The toolchain-pdf reference shows this pattern. Most pipelines don't need it.

Provenance is what makes the dataset *defensible*. When a downstream user finds an anomaly, the chain is: `(source, vintage)` in the processed CSV → matching row in `provenance.csv` → `source_url` and `sha256` → the original file in `data/original/`. Anyone with a clone can reproduce the extraction and verify.

## Data quality dimensions

"High-quality data" is the deliverable. But quality is not one thing — it's a structured set of dimensions, each with its own measurable elements, and each dimension matters more or less depending on what the data is for. The skill's pipeline operations correspond, one-to-one, to specific dimensions in this framework. Naming them lets you say *which* dimension you've improved (or broken) when a parser changes.

### The fitness-for-use lineage

Three definitions, in genealogical order:

| Source | Definition |
|---|---|
| Juran 1974 (*Quality Control Handbook*) | Quality is *fitness for use*. |
| Crosby 1988 (*Quality is Free*) | Quality is *conformance to requirements*. |
| Wang & Strong 1996 ([*JMIS* 12(4): 5-33](https://web.mit.edu/tdqm/www/tdqmpub/WangStrongJMIS96.pdf)) | Data quality is *the degree to which data are fit for use by data consumers*. A *data quality dimension* is "a set of data quality attributes that represent a single aspect or construct of data quality." |

Wang & Strong's two-stage consumer survey produced the foundational framework — four categories, fifteen dimensions, derived empirically from what data consumers said mattered:

| Category | Dimensions |
|---|---|
| **Intrinsic** — qualities the data has regardless of context | Accuracy, Believability, Objectivity, Reputation |
| **Contextual** — qualities that depend on the task at hand | Relevancy, Value-Added, Timeliness, Completeness, Appropriate Amount of Data |
| **Representational** — qualities of how the data is presented | Interpretability, Ease of Understanding, Representational Consistency, Concise Representation |
| **Accessibility** — qualities of the system that delivers it | Accessibility, Access Security |

This framework is the load-bearing reference for everything that follows. Most subsequent frameworks (Batini's methodology survey, the Cai/Zhu big-data extension below, Zaveri's Linked-Data dimensions, ISO 8000) are reorderings, refinements, or specializations of these fifteen.

### Cai & Zhu's user-perspective framework

For civic liberation projects, the most directly usable taxonomy is Cai & Zhu's hierarchical framework ([*Data Science Journal* 14: 2](https://datascience.codata.org/articles/10.5334/dsj-2015-002), 2015), which adapts Wang & Strong for the big-data era. Their move: explicitly organize the framework *from the user's perspective*, not the producer's, because in big-data settings "data users are not necessarily data producers." That's precisely the civic-data condition — the publisher and the journalist or researcher are different organizations. The hierarchy is `Dimensions → Elements → Indicators`:

| Dimension | Cai & Zhu's definition | Elements |
|---|---|---|
| **Availability** | "the degree of convenience for users to obtain data and related information" | Accessibility, Timeliness, Authorization |
| **Usability** | whether the data are "useful and meet users' needs" | Definition / Documentation, Credibility, MetaData |
| **Reliability** | whether the data can be trusted | Accuracy, Consistency, Completeness, Integrity, Auditability |
| **Relevance** | "the degree of correlation between data content and users' expectations or demands" | Fitness |
| **Presentation Quality** | a valid description method "which allows users to fully understand the data" | Readability, Structure |

The first four are *indispensable inherent features*; presentation quality is an *additional property that improves customer satisfaction* — a hierarchy worth preserving when prioritizing what to fix in a parser.

Each element resolves to concrete *indicators* — the things you can actually check. Selected from Cai & Zhu's Table 1, with the ones the pipeline directly touches in **bold**:

| Element | Indicators (selected, paper's wording) |
|---|---|
| Accessibility | Whether a data access interface is provided; **data can be easily made public or easy to purchase** |
| Timeliness | Within a given time, whether the data arrive on time; **whether data are regularly updated**; whether the time interval from collection to release meets requirements |
| Credibility | Data come from specialized organizations; experts or specialists audit the content; **data exist in the range of known or acceptable values** |
| Accuracy | **Data provided are accurate**; data representation reflects the true state of the source; **information representation will not cause ambiguity** |
| Consistency | **After data have been processed, their concepts, value domains, and formats still match as before processing**; **data and the data from other data sources are consistent or verifiable** |
| Integrity | **Data format is clear and meets the criteria**; data are consistent with structural integrity; data are consistent with content integrity |
| Completeness | **Whether the deficiency of a component will impact use of the data for data with multi-components**; **whether the deficiency of a component will impact data accuracy and integrity** |
| Fitness | The data collected do not completely match the theme but expound one aspect; **most datasets retrieved are within the retrieval theme users need** |
| Readability | **Data (content, format, etc.) are clear and understandable**; it is easy to judge that the data provided meet needs; **data description, classification, and coding content satisfy specification and are easy to understand** |

The bolded indicators map directly onto operations this skill's pipeline already performs:

| Operation in this skill | Indicators it satisfies |
|---|---|
| `fetch.py` writing manifests with sha256 + `fetched_at` | *Accessibility*, *Timeliness* indicators on whether updates arrive |
| Source registry + `provenance.csv` columns (`source_url`, `retrieved_at`, `extraction_quality`) | *Credibility* (specialized publisher), *Authorization* (legal basis) |
| `pandera` schema with `coerce=True, strict=True` and `Int64`/`string` dtypes | *Integrity* (format meets criteria), *Consistency* (after processing, concepts/value domains/formats still match) |
| `concept` column + `concepts.yaml` with caveats | *Consistency* (data verifiable against other sources), *Fitness* (concept catalog ensures cross-source rows are comparable) |
| `audit.py` null rates, distinct values, source coverage; `docs/variables.{md,csv}` | *Completeness* (deficiency-impact checks), *Accuracy* (within acceptable values) |
| `reconcile.py` against published top-line totals | *Accuracy* (data reflects true state), *Auditability* (auditors evaluate accuracy within rational time) |
| `docs/data-dictionary.md` (hand-authored, one H2 per column with type/units/caveats) | *Definition / Documentation*, *MetaData*, *Readability* |
| Datasette `metadata.yaml` + faceted browsing + canned queries | *Accessibility*, *Readability* (clear, understandable presentation) |

When a reviewer asks "is this data high quality?", the productive response is to walk through this mapping rather than reach for "yes/no." When a parser fails, identifying which indicator it's failing on tells you which dimension is in trouble — and that tells you whether the fix belongs in `parsers/`, `schema.py`, `audit.py`, or the data dictionary.

### Cai & Zhu's assessment process — and how this skill realizes it

Cai & Zhu pair the framework with a *dynamic assessment process with feedback* (their Figure 3). The flow:

```
goals of data collection
        ↓
determine quality dimensions and elements
        ↓
determine indicators ──────→ formulate evaluation baseline
                                        ↓
                              data collecting → data cleaning
                                                       ↓
                                          data quality assessment
                                                       ↓
                                          satisfy baseline?
                                                ↓ yes
                                     output data + generate DQ report
                                                ↓
                                     data analysis and data mining
                                                ↓
                                          satisfy goals?
                                                ↓ no
                                          adjustment & feedback ──┐
                                                                  │
                                                                  └─→ back to baseline
```

Mapping onto this skill's CLI:

| Cai & Zhu step | This skill |
|---|---|
| Goals of data collection | Survey phase; one-page Survey note |
| Determine dimensions, elements, indicators | `scripts/schema.py` (the canonical schema); `docs/data-dictionary.md` (per-column caveats); concept catalog |
| Formulate evaluation baseline | First pass of `audit.py` + reconciler registry; the diffable `data/audit/summary-*.md` of a known-good vintage |
| Data collecting | `discover.py` + `fetch.py` |
| Data cleaning | `clean.py` orchestrator + per-vintage parsers |
| Data quality assessment | `audit.py` summary + `reconcile.py` (opt-in) |
| Satisfy baseline? | CI: `clean --fail-on-empty`; `reconcile` non-zero exit on mismatch; PR-reviewable audit diff |
| Output + DQ report | `data/processed/<project>.csv` + `data/audit/summary-<ts>.md` + Datasette `metadata.yaml` |
| Adjustment and feedback | Refresh PR → audit diff visible to reviewer → parser/dictionary update → re-run |

Cai & Zhu note that for social-media data, "timeliness and accuracy are two important quality features," but accuracy is hard to judge directly, so *credibility becomes an important quality dimension* — checking the source's reputation in lieu of being able to verify each value. For biology data, "data storage software and data formats vary widely," so *consistency is hard to enforce as a dimension* and timeliness matters less. The point: dimension selection is context-dependent. A civic-data project should declare, in AGENTS.md, which Cai/Zhu dimensions are load-bearing for its sources and which are deprioritized.

### Profiling vs measurement vs monitoring — the Ehrlinger & Wöß tool survey

Ehrlinger & Wöß's systematic survey of 667 data-quality tools ([*Frontiers in Big Data* 5: 850611](https://doi.org/10.3389/fdata.2022.850611), 2022) is the most concrete inventory of what a data-quality tool actually does. They evaluated 13 tools (8 commercial, 5 open-source) against a 43-item requirements catalog grouped into three functionality areas. The catalog is worth reproducing because it doubles as a checklist for what `audit.py` should produce — and as a map of where commercial tools leave gaps that a small civic-data project can close cheaply.

**Data profiling (30 items)** — describing what's there:

| Group | Items |
|---|---|
| Single-column cardinalities | row count; null count; null %; distinct count; distinct % |
| Single-column value distributions | equi-width / equi-depth frequency histograms; min/max; *constancy* (most-frequent-value / total); quartiles; **Benford's-law first-digit distribution** |
| Single-column patterns / types / domains | basic type; DBMS dtype; value length min/max/avg/median; max digits; max decimals; value-pattern histogram (e.g. `Aa9...`); semantic generic type (code, date, quantity, identifier); semantic domain (credit card, first name, city...) |
| Dependencies | unique column combinations (UCCs / key discovery); relaxed UCCs; inclusion dependencies (IND / foreign-key discovery); relaxed INDs; functional dependencies (FDs); relaxed FDs |
| Multi-column profiling | correlation analysis; association rule mining; cluster analysis; outlier detection; exact duplicate detection; relaxed duplicate detection |

**DQ measurement (8 items)** — computing metrics for the four canonical dimensions:

- Metric for **accuracy** — defined by the paper as "the closeness between an information system and the part of the real-world it is supposed to model" (Batini & Scannapieco)
- Metric for **completeness** — "the breadth, depth, and scope of information contained in the data" (Wang & Strong)
- Metric for **consistency** — "the violation of semantic rules defined over data items" (Batini & Scannapieco)
- Metric for **timeliness** — "how current the data are for the task at hand" (Batini & Scannapieco)
- Metrics for *other* DQ dimensions (the vendor extensions: conformance, currency, duplicates, freshness, integrity, latency, plausibility, referential integrity, structure, uniformedness, uniqueness, validity)
- Business-rule creation; general-applicable integrity rules; rule-verification

**Automated DQ monitoring (5 items)** — catching drift over time:

- Scheduling a DQ metric / profiling task in user-defined periods
- Persistent storage of measurements / profiling results
- Retrieval of stored results
- Comparison between multiple measurements
- Visualisation of results over time

Ehrlinger & Wöß's key empirical findings — these are the gaps a per-project pipeline naturally closes:

| Finding | What it means for civic-data work |
|---|---|
| **About half (50.82%) of DQ tools are domain-specific** — e.g., built for one company's CRM | A general-purpose civic pipeline must roll its own; the tools market won't supply one. |
| **16.67% of tools "modify data without measurement"** — clean without reporting | Don't silently clean: emit per-row provenance of every coercion (`provenance.csv`'s `extraction_notes`). |
| **Association rule mining: zero tools** support it | Cross-column pattern detection is yours to write. DuckDB SQL handles most of it. |
| **Correlation analysis: one tool** (Aggregate Profiler) | A `df.corr()` in `audit.py` beats the field. |
| **No tool implements a timeliness metric** | Timeliness comes from `provenance.csv`'s `retrieved_at` minus the source's published date; trivial to compute, no commercial tool offers it. |
| **Dependency discovery (UCC, IND, FD)** strongly supported only by Informatica DQ and Experian Pandora | The pandera schema's primary-key declarations + per-vintage tests cover this. |
| **DQ monitoring is a paywalled premium feature** in general-purpose tools; only Apache Griffin and MobyDQ ship it open-source, and both lack profiling | The cron-driven refresh PR + diff-able `data/audit/summary-*.md` *is* DQ monitoring; the gap most expensive to close commercially is closed for free here. |

The five open-source tools worth knowing about — none of them replaces a per-project pipeline, but each one closes a different gap:

| Tool | What it gives you | When to consider it |
|---|---|---|
| [**MobyDQ**](https://github.com/ubisoft/mobydq) (Ubisoft, open-source) | Automates source-vs-target comparisons with freshness and latency indicators | When the refresh pattern needs measurable lag between upstream publication and your latest pull |
| [**Apache Griffin**](https://griffin.apache.org/) | Table-level accuracy metric on batch + streaming sources | When the project's scale exceeds a single-machine pandas/DuckDB workflow (rare in civic work; install cost is hostile) |
| [**OpenRefine + MetricDoc**](https://openrefine.org/) | Cleansing workbench with customisable reusable DQ metrics + immediate visual feedback | One-off liberations where you'd rather drag-and-drop than write Python |
| [**Talend Open Studio for DQ**](https://www.talend.com/) | Mature open-source profiling, business-rule management, UI; only tool with Benford's-law support | When a project's downstream consumers expect a familiar enterprise tool |
| [**Aggregate Profiler**](https://sourceforge.net/projects/dataquality/) (Arrah) | Statistical analysis + pattern matching + Pearson correlation | Sanity-check second opinion on a project's audit |

The deeper Ehrlinger & Wöß framing worth absorbing: DQ has become "no longer a question of 'hygiene' [...], but rather critical for operational excellence" (quoting Otto & Österle), and "without automation, the speed and volume of data will quickly overwhelm even the most dedicated efforts to measure" (Sebastian-Coleman). Cyclic DQ management has four core steps in the literature they survey: state reconstruction → measurement/assessment → cleansing/improvement → continuous monitoring. The skill's `discover → fetch → clean → audit → reconcile → refresh` chain is one realisation of that cycle, and the recurring-refresh PR is the *automation* the Sebastian-Coleman quote demands.

### Two edge cases — unstructured text (Woods et al.) and Linked Data (Luzzu)

#### Free-text columns: the maintenance-work-order pattern

Woods, Selway, Bikaun, Stumptner & Hodkiewicz's "An ontology for maintenance activities and its application to data quality" ([*Semantic Web* 15(2): 319–352](https://doi.org/10.3233/SW-233299), 2024) is the cleanest worked example for a civic-data problem most projects face: a row with a few structured fields (date, location, cost, status) wrapped around a short free-text "what happened" string written by many different staff over many years, with no controlled vocabulary, abundant misspellings, and the verb that determines the analytic category often *missing*, *vague*, or *contradicted* by the structured fields. Civic analogs: FOIA case logs, police incident narratives, code-enforcement complaints, 311 service requests, agency response letters.

Working from ~800,000 maintenance work orders, the authors built a seven-class reference ontology of maintenance activities (rooted in BFO, aligned with ISO 14224 and ISO 15926-4). The classes — distilled from an NLP frequency analysis of 10,860 unique activity tokens reduced to 108 after lexical normalization, then SME-grouped — are:

| Activity (BFO process) | Synonyms (from corpus) | Strategy |
|---|---|---|
| **Replace** | replace, change-out, fit, remove, install, connect | corrective or preventative |
| **Repair** | repair, seal, weld, overhaul, rectify, rebuild, mount, torque, refurbish, fix, build up, rewheel, rewire, renew, heat, return, regas, grind | corrective |
| **Inspect** | inspect, monitor, ndt, measure, crack test | preventative |
| **Adjust** | adjust, tighten, fit, position, tune, straighten, turn, set, shim, top up, tension, tilt, regulate | corrective |
| **Service** | service, clean, fill, sample, charge, rotate, drain, wash, lubricate, grease | preventative |
| **Diagnose** | check, investigate, test, diagnose, check out, analyse | corrective |
| **Calibrate** | calibrate | preventative |

The pipeline that uses this ontology has seven stages: (1) NER on the free text using a model fine-tuned on 6,000 gold-standard MWOs (off-the-shelf POS taggers failed on informal short text); (2) frequency analysis (top 99% of tokens = 109 terms); (3) lexical normalization (misspellings, tense, strip "re-" prefixes); (4) SME synonym grouping into the seven classes; (5) author the reference ontology with BFO-aligned elucidations; (6) write SWRL rules that classify each MWO against structured fields (functional location, work type, labour cost, material cost); (7) SPARQL-query the result for mismatches.

Result on a 36-MWO pump dataset: **20 records (55%) flagged with DQ issues**; for the **12 records (33%) where the unstructured text contained no verb at all**, the ontology *inferred* a likely activity class with 100% expert agreement. The DQ-issue patterns the paper catalogs are the exact ones a FOIA-log audit hits:

| Pattern | What it looks like |
|---|---|
| **Missing verb** | Free text describes a state ("pump not pumping well") with no action verb |
| **Wrong verb / verb–data mismatch** | "Calibrate pressure switch" recorded, but labour and material costs indicate corrective adjust or diagnose, not preventative calibrate |
| **Verb–cost inconsistency** | "Service pump" with $0 labour cost = the work was logged but not actually done |
| **Ambiguous corrective verb** | Repair vs replace cannot be distinguished from the available fields; flag as "Repair-or-Replace" with an Uncertain marker |
| **Verb conflating discovery and action** | "Investigate oil leak" with $0 labour: diagnose was logged but no action taken |

The pattern transfers to civic narrative columns: (1) treat the free-text field as the *primary site* of DQ failure and benchmark it against structured fields rather than trusting it; (2) build a small reference vocabulary of 5–10 core action/disposition terms with explicit synonym groups derived **empirically from a corpus frequency analysis**, not top-down; (3) write decision rules cross-checking the narrative verb against structured-field expectations (cost, type, location) and flag mismatches as DQ issues rather than silently re-coding them; (4) for records missing the action verb entirely, infer the likely category but mark it with an `Uncertain` or `Inferred` classifier so downstream users can choose whether to include. As Woods et al. put it: "we cannot afford to rely only on the words used by the data generator to describe the activity. There are too many different people involved over the years in generating these records and they come from a wide range of backgrounds."

This is the civic-data analog of the *concept catalog* (see [Concept catalogs](#concept-catalogs)) for cross-source variables — except now the controlled vocabulary lives in `data/lookups/narrative_actions.yaml`, the inference happens in a parser, and the audit reports which records were classified vs inferred vs flagged-ambiguous.

#### Linked Data: the Luzzu architecture

Civic-data projects mostly ship CSV, not RDF, but Debattista, Auer & Lange's "Luzzu" framework ([*ACM J. Data and Information Quality* 8(1): 4](https://doi.org/10.1145/2992786), 2016) is the canonical extensible quality-assessment harness, and four of its design ideas port directly. Luzzu has four components:

1. **Extensible per-metric interface.** A metric is either a Java class implementing `QualityMetric` (`compute(Quad)` plus precursor / successor hooks) or a declarative *LQML* definition with seven fields: `def`, `metric` (URI), `label`, `description`, `match` (condition), `action`, and `finally` (the global aggregation). Custom functions (`isDereferenceable`, `hasValidInverseFunctionalPropertyUsage`) can be registered. Formally a metric is a *Quality Metric Pattern* — a triple (α, λ, ω) of precursor, assessment rule, successor — interpreted as a state-aware inductive aggregation over the data stream.
2. **Ontology-driven back-end.** Three vocabularies sit on top of W3C Data Cube and PROV-O: **daQ** (Dataset Quality Ontology, three abstract levels: Category / Dimension / Metric — daQ contributed the core of the W3C Data Quality Vocabulary DQV); **QPRO** (Quality Problem Report Ontology, with `QualityReport`, `QualityProblem`, `computedOn`, `hasProblem`, `isDescribedBy`, `problematicThing`, `inGraph` — so each problem points at the exact offending triples); and **LMI** (Luzzu Metric Implementation, linking semantic metric definitions to their implementations via `lmi:referTo` and `lmi:javaPackageName`).
3. **Scalable dataset processors.** Four interchangeable processors — Stream, SPARQL, In-Memory, SPARK — feed triples to a metric thread pool; the metric implementation's complexity doesn't affect the processor's time complexity. Tested at 125M triples (Berlin SPARQL Benchmark); real-world assessment of nine statistical Linked Data datasets totaling >1 billion triples on 21 metrics across 9 dimensions ran in 3 minutes (smallest) to 6 hours (largest).
4. **User-customisable ranking.** Users assign weights at three granularities — by metric, by dimension, or by category. Weighted metric value = θ × raw; weighted dimension distributes θ evenly across constituent metrics; category averages over dimensions. Non-numeric outputs (Boolean, datetime) coerce to numeric (true → 1, datetime → `now − value`). The persisted weights form reusable **Quality Profiles** — saved sets of measures, weights, and slices.

Luzzu reports ~60% coverage of the Zaveri et al. (2015) catalog of Linked Data quality metrics — accessibility (availability 100%, licensing 67%, interlinking 100%, security 50%, performance 100%); intrinsic (semantic accuracy 20%, consistency 80%, conciseness 33%); contextual (understandability 83%, timeliness 100%); representational (concise representation 100%, interoperability 100%, interpretability 75%, versatility 100%).

What ports to a CSV-based civic project:

- **Round-tripping**: quality metadata in the same format as the data. Luzzu represents quality issues themselves as RDF; the CSV analog is a `data/audit/quality.csv` (or a [Frictionless Data quality report](https://specs.frictionlessdata.io/)) alongside `data/processed/<project>.csv`, joinable by `(source, vintage)`, queryable by the same DuckDB or pandas tooling consumers already use to query the data.
- **Per-user weighted ranking**: different consumers care about different dimensions — a journalist comparing TIGER vintages cares about geometry completeness, a researcher about longitudinal join keys. Luzzu's three-level weighting model (category / dimension / metric) is the right abstraction for projects that publish to multiple audiences. Datasette's facets + canned queries are an informal version of the same affordance.
- **Extensible metrics architecture**: adding a new DQ check should be writing one small module, not editing a pipeline-wide config. A `scripts/audit/metrics/` directory where each file declares one metric (label, what it computes, the dimension it serves) is the civic-data analog of Luzzu's QualityMetric interface.
- **The Zaveri dimensions catalog**: dataset-format-agnostic. *Accessibility*, *intrinsic*, *contextual*, *representational* is a coherent dictionary for talking about CSV quality — availability, license clarity, timeliness, conciseness, interpretability, consistency — that anchors data dictionaries and audit reports in something more rigorous than ad-hoc checklists.

Luzzu's larger argument also matters: data quality is a *co-evolution* of data and its assessment — "quality assessment on its own cannot improve the quality of a dataset." Their five-stage lifecycle (Metric Identification & Definition → Assessment → Repairing / Cleaning → Storage / Cataloguing / Archiving → Exploration / Ranking) is essentially what the skill's six-phase workflow performs, with the assessment-exploration loop closed by the recurring-refresh PR.

## DQ methodologies — the Batini survey

If Cai/Zhu, Ehrlinger/Wöß, and Luzzu describe *what to measure* and *what tools exist*, Batini, Cappiello, Francalanci & Maurino's "Methodologies for Data Quality Assessment and Improvement" ([*ACM Computing Surveys* 41(3): Article 16](https://doi.org/10.1145/1541880.1541883), 2009) describes *the procedural shape of any DQ effort*. They define a data quality methodology as:

> A set of guidelines and techniques that, starting from input information describing a given application context, defines a rational process to assess and improve the quality of data.

### Three generic phases

Every DQ effort, regardless of methodology, traverses (or skips) three phases:

| Phase | Purpose | The skill's analog |
|---|---|---|
| **State reconstruction** | "Collecting contextual information on organizational processes and services, data collections and related management procedures, quality issues and corresponding costs." Can be skipped if prior analyses already provide it. | The Survey phase — and reading the publisher's codebook, identifying the contact, finding prior journalism. See [SKILL.md Survey section](../SKILL.md). |
| **Assessment / measurement** | "Measures the quality of data collections along relevant quality dimensions." Batini distinguishes *measurement* (the act of measuring) from *assessment* (comparing measurements against reference values to diagnose causes). | `audit.py` is measurement; `reconcile.py` against authoritative totals is assessment. |
| **Improvement** | "Selection of the steps, strategies, and techniques for reaching new data quality targets." | The parser-by-parser, vintage-by-vintage iteration that follows an audit's revelations. |

Batini decomposes each phase into canonical sub-steps that double as documentation scaffolding for any liberation project:

| Phase | Sub-steps |
|---|---|
| Assessment | *data analysis* (examines schemas, conducts interviews) → *DQ requirements analysis* (surveys users to set targets) → *identification of critical areas* (selects the most relevant data flows) → *process modeling* (models the data-producing/-updating processes) → *measurement of quality* (selects dimensions, defines metrics) |
| Improvement | *evaluation of costs* (direct + indirect) → *assignment of process responsibilities* → *assignment of data responsibilities* → *identification of causes of errors* → *selection of strategies and techniques* → *design of data improvement solutions* → *process control* (in-flight check points) → *process redesign* → *improvement management* (new organizational rules) → *improvement monitoring* (periodic feedback + dynamic tuning) |

In civic-data work, the assessment sub-steps live in the Survey phase (data analysis, requirements analysis), in `scripts/schema.py` (measurement-of-quality framed as schema enforcement), and in `audit.py`/`reconcile.py`. The improvement sub-steps map onto how a project handles a *new* vintage that fails audit: identification-of-causes-of-errors is the parser triage; process redesign is the parser refactor; improvement monitoring is the diff-able `data/audit/summary-*.md` review.

### Five axes of comparison among methodologies

Batini surveys 13 named methodologies and compares them along **five perspectives**:

| Axis | What it discriminates |
|---|---|
| **Methodological phases and steps** | *Complete* (assessment + improvement, e.g. TIQM, CDQ) vs *audit* (assessment-only — AIMQ, CIHI, DQA, AMEQ, QAFD, IQM) vs *operational* (TDQM, DWQ, ISTAT, DaQuinCIS) vs *economic* (COLDQ). Most civic-data pipelines are *complete* in scope: they audit and they iterate. |
| **Strategies and techniques** | *Data-driven* (improve data directly, e.g. DWQ, DaQuinCIS) vs *process-driven* (TDQM — change the upstream process) vs *mixed* (TIQM, ISTAT, COLDQ, CDQ). Civic projects are almost always data-driven because the upstream agency is out of reach. |
| **DQ dimensions and metrics** | *Fixed* dimension sets vs *open / extensible*. Whether metrics are *subjective* (questionnaires) or *objective* (computed from data). |
| **Types of costs** | Direct (cost of DQ assessment + improvement) vs indirect (cost of poor data quality — process costs + opportunity costs). Only TIQM, COLDQ, and CDQ provide detailed cost models. |
| **Types of data + information systems** | Structured / semistructured / unstructured. Monolithic / data-warehouse / distributed / cooperative (CIS) / Web / P2P. The civic-data common case is *structured + semistructured* on a *distributed / cooperative* substrate (federated agency publishers). |

### The named methodologies — short reference

| Acronym | Author / year | What's distinctive |
|---|---|---|
| **TDQM** | Wang 1998 | First general DQ methodology; introduces IP-MAP (Information Production Map) and role assignment (info supplier / manufacturer / consumer / process manager). |
| **DWQ** | Jeusfeld et al. 1998 | EU data-warehouse project; classifies dimensions by design / administration / software-implementation / data-usage quality; uses Goal-Question-Metric. |
| **TIQM** | English 1999 | DW-consolidation focus; deepest cost classification (process failure, information scrap and rework, lost opportunity). |
| **AIMQ** | Lee et al. 2002 | Benchmarking-focused; introduces *PSP/IQ* (Product vs Service × Conforms-to-specs vs Meets-expectations) yielding "sound, dependable, useful, usable" information; purely subjective questionnaires. |
| **CIHI** | Long & Seko 2005 | Canadian Institute for Health Information; four-level hierarchy (86 criteria → 24 characteristics → 5 dimensions → 1 evaluation); continuous-improvement cycle. |
| **DQA** | Pipino et al. 2002 | Principles for defining metrics; distinguishes subjective/objective and task-dependent/task-independent; three metric classes (simple ratio, min/max, weighted average). |
| **IQM** | Eppler & Münzenmaier 2002 | Web-data focus; uses site analyzers, traffic analyzers, port scanners, Web mining for objective measurement. |
| **ISTAT** | Falorsi et al. 2003 | Italian Bureau of Census; localization/address data exchanged across Public Administration via common XML schema; *the closest analog in the paper to multi-jurisdiction civic-data work*. |
| **AMEQ** | Su & Jin 2004 | Manufacturing; OO modeling of enterprise object types; uses Information Quality Management Maturity Grid. |
| **COLDQ** | Loshin 2004 | Centered on the *data quality scorecard*; classifies costs by operational/tactical/strategic domain impact; supports ROI/break-even. |
| **DaQuinCIS** | Scannapieco et al. 2004 | Cooperative Information Systems; introduces the D²Q model, Data Quality Broker, Quality Notification Service, source-trustworthiness rating. |
| **QAFD** | De Amicis & Batini 2004 | Only methodology for financial data; combines objective + subjective assessments; defines DQ rules as "dynamic semantic properties." |
| **CDQ** | Batini & Scannapieco 2006 | Designed as flexible/complete/simple; works intra- and inter-organizationally; supports all data types; selects optimal improvement process by *minimum cost*. |

For a civic-data pipeline, **ISTAT** is the most directly relevant — its design (central XML schema, autonomous local administrations, three phases: assessment → global improvement → inter-administrative improvement) is essentially how multi-source liberation projects already work, with the concept catalog playing the role of the central schema.

### Strategies and techniques — the toolbox

Batini catalogs the techniques that improvement actually applies. Two top-level categories:

**Data-driven** — improve the data directly (the civic-data default):

- *Acquisition of new data* — replace problem values with higher-quality data.
- *Standardization (normalization)* — replace non-standard values with standard ones (Bob → Robert; Channel Str. → Channel Street). Lives in parsers and in `data/lookups/`.
- *Record linkage* — "identifies that data representations in two (or multiple) tables that might refer to the same real-world object." Three flavors: *probabilistic*, *empirical* (sorting, neighbor comparison, pruning), *knowledge-based*. The civic-data analog is the concept catalog plus per-source identifier resolution.
- *Data and schema integration* — unified view across heterogeneous sources; addresses technological, schema-level, and instance-level heterogeneities. This is `concepts.yaml` and the canonical long-form schema.
- *Source trustworthiness* — select sources by quality. The `provenance.csv` `extraction_quality` flag plus the publisher-vetting moves in the bulletproofing checklist.
- *Error localization and correction* — "detect records that do not satisfy a given set of quality rules"; the "act of restoring correct values is called *imputation* [Fellegi & Holt 1976]." This is pandera schema violations + `audit.py` extraction-error logging; imputation is generally **out of scope for this skill** (the pipeline emits what the source says, with NA preserved).
- *Cost optimization* — minimize total cost across improvement dimensions.

**Process-driven** — change the upstream process (rare in civic work because the publisher is usually out of reach):

- *Process control* — "inserts checks and control procedures in the data production process when (1) new data are created, (2) data sets are updated, or (3) new data sets are accessed." For civic projects, this means *advocating for better source agreements* (the FOIA-modernization angle), not refactoring agency IT.
- *Process redesign* — radical version = business process reengineering. Civic-data analog: persuading an agency to publish a CSV instead of a PDF. Rarely fast.

Citing Redman 1996 and English 1999, Batini gives the *durable strategic recommendation* that informs how this skill is scoped:

> In the long term, process-driven techniques are found to outperform data-driven techniques, since they eliminate the root causes of quality problems. However, from a short-term perspective, process redesign can be extremely expensive. On the contrary, data-driven strategies are reported to be cost efficient in the short term, but expensive in the long term. They are suitable for one-time application and, thus, they are recommended for static data.

A civic liberation pipeline is *almost always* the data-driven short-term answer to a problem whose process-driven long-term answer (the agency publishes better data) is decades away. That tradeoff is structural, not accidental. AGENTS.md should be honest about it.

### Dimensions catalog (Batini's framing)

Batini treats *accuracy, completeness, consistency, timeliness* as the foundational four, with operational formulas:

| Dimension | Paper's wording | Operational form |
|---|---|---|
| **Accuracy** | "The extent to which data are correct, reliable, and certified" (Wang & Strong 1996); split into *syntactic* (closeness to elements of the definition domain) vs *semantic* (correspondence to real-world value). | Compare to a known reference value; in civic data, the reconcile.py top-line totals provide the reference. |
| **Completeness** | "The degree to which a given data collection includes data describing the corresponding set of real-world objects." Distinguishes value missing because *exists-but-unknown*, *does-not-exist*, or *unknown-whether-exists*. | `Compl1 = non-null / total`. The three-way missingness distinction belongs in the data dictionary's caveat section. |
| **Consistency** | "The violation of semantic rules defined over a set of data items." In relational theory: intra- and inter-relation integrity constraints. The "act of restoring correct values is called *imputation*." | Pandera schema violations + cross-source `reconcile.py` checks. |
| **Currency / Volatility / Timeliness** | *Currency*: "time in which data are stored in the system minus time in which data are updated in the real world." *Volatility*: "time length for which data remain valid." *Timeliness*: "extent to which the age of data is appropriate for the task at hand." | `Time1 = max(0, 1 − Currency/Volatility)^s`. For civic data, *currency* is `fetched_at − published_at`; volatility comes from publisher cadence. |

Beyond the foundational four, the paper surveys 20+ additional dimensions across methodologies (accessibility, appropriateness, believability, interpretability, objectivity, relevance, reputation, security, traceability, uniqueness, credibility, conciseness, maintainability, etc.) — mostly subsumed under Wang & Strong's four categories and Cai/Zhu's five dimensions tabulated [above](#data-quality-dimensions).

## Validation

A liberation pipeline benefits from validation in three places, each catching a different class of problem.

| Layer | Tool | What it catches |
|---|---|---|
| Record-level | `pydantic` | Malformed individual records during parsing (e.g., a vote count that parsed as `"---"`). Per-row validation is slow; use sparingly, usually only inside a parser's coercion pass. |
| DataFrame-level | `pandera` | Schema drift at the boundary of the pipeline (new column appeared, dtype changed, required column missing, value out of declared range). This is the gate. |
| Behavior | `pytest` | The parser does what the project says it does — a known-fixture-in, expected-frame-out test per source × vintage. |

The pandera schema in `scripts/schema.py` is the most consequential of the three. It runs at clean time, before write, and rejects frames that don't match. `strict=True` rejects unknown columns; `coerce=True` lets parsers be loose with intermediate dtypes and the schema does the final cast.

Pandera schemas also double as documentation. The schema declaration is more enforceable than prose in `docs/data-dictionary.md`; treat the two as complementary — the schema declares the contract, the dictionary explains it.

Per-parser pytest tests live at `tests/test_<source>_<vintage>.py`. The minimum useful test:

```python
# tests/test_boulder_sov_2009.py
from pathlib import Path
import pandas as pd
from scripts.parsers.boulder_sov_2009 import parse

FIXTURE = Path(__file__).parent / "fixtures" / "boulder_sov_2009_small.pdf"

def test_parses_canonical_schema():
    df = parse(FIXTURE)
    # Validated by normalize_long inside parse()
    assert len(df) > 0
    assert df["source"].unique().tolist() == ["boulder_county_sov"]
    assert set(df["contest"].unique()) >= {"PRESIDENT", "GOVERNOR"}

def test_known_totals():
    """Top-line totals from a small subset of the SoV."""
    df = parse(FIXTURE)
    pres_total = df.query("contest == 'PRESIDENT'")["votes"].sum()
    assert pres_total == 12_345  # known from the source PDF's own total row
```

The second test is doing the reconciliation work that `scripts/reconcile.py` would do at full scale — a small enough version that it can run on a fixture in CI in milliseconds. Both tests are cheap; both fail loudly when a vintage's parser drifts.

## Filter-pivot recipes

`docs/filter-pivot-recipes.md` is the document that bridges tidy storage to wide-form analysis. Ship it in three stacks, all reading the canonical CSV at `data/processed/<project>.csv`:

- **Python / pandas** — for Python-using analysts and downstream pipelines. `pd.read_csv(path, dtype=str)` is the safe default; coerce specific columns explicitly.
- **R / tidyverse** — for academic and policy researchers. `readr::read_csv(path, col_types = cols(.default = col_character()))` mirrors the pandas default.
- **SQL / DuckDB** — for analysts who prefer SQL, and as a copy-paste-into-Datasette path. `duckdb` reads the CSV directly via `read_csv('data/processed/<project>.csv')`; no load step, no `pyarrow` dependency, and the same SQL runs against the published Datasette instance and most warehouse engines.

(If non-technical readers are a primary audience, an Excel / Google Sheets pivot-table recipe earns a fourth slot. The three above are the durable defaults.)

Four recipes carry most of the weight:

1. **Single-vintage wide pivot.** "Show me 2024 only, with one row per observation_id and the measurements as columns."
2. **Year × source matrix.** "How many rows from each source, in each vintage?" — the audit table, on demand for readers.
3. **Roll up to coarser geography.** "Aggregate from precinct to district." Requires a crosswalk; the recipe documents the join.
4. **Cross-source concept comparison.** "For every observation where source A and source B both report the same concept, show both values side by side." This is the payoff of the concept catalog.

Each recipe in each stack runs against a fixture so the documentation doesn't drift from the data. The IPEDS pipeline's filter-pivot recipes are the model.

## When schema decisions are hard to reverse

A few choices are expensive to change once the project has data and downstream users:

- **The unit of observation.** Changing from "row per precinct × contest × candidate" to "row per precinct × contest" later means every downstream join breaks. Get this right before the second source goes in.
- **The vintage convention.** Whether `vintage` is `"2024"`, `"2024-general"`, `"2024-Q1"`, or `"2024-11-05"` determines what kinds of within-year comparisons are sayable in the schema. Pick the finest granularity any source publishes and use that uniformly.
- **The composite primary key.** Whatever combination of columns must be unique — declare it in the pandera schema as a multi-column uniqueness check and enforce it. If you discover later that the key isn't actually unique, the cleanup is painful.

Spend the survey phase on these specifically. The cost of revisiting them after a project has a year of data and citations is high; the cost of getting them right upfront is one careful afternoon.

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| Schema validation fails on a previously-passing source | New vintage added new columns | Update `LONG_COLUMNS` and the schema; add the new columns to the data dictionary in the same commit |
| Pivot recipe in `filter-pivot-recipes.md` returns mostly NaN | New source introduced sparse coverage on the pivoted variable | Document in the concept catalog's `caveats`; consider whether the pivot is honest given the sparsity |
| Two sources have the "same" concept but different totals | Definitional difference not yet caveated | Add the caveat to the concept entry; do not silently average or pick a winner |
| Per-row hashes on every row | Provenance design drifted into per-row | Move to sidecar; carry only `source` and `vintage` on the row |
| `provenance.csv` has rows with no matching data | Source was registered but parser failed silently | `audit.py` should flag this; check for empty parser output upstream |
| Dictionary says `Int64`, `variables.csv` says `object` | Parser is returning a string column; schema is silently coercing to NaN | Fix the parser; the dictionary and the auto-generated variables report agreeing is a precondition |

## What to write in the AGENTS.md

- **Unit of observation** and why this one was chosen over the alternatives.
- **Vintage convention** — string format and granularity (year, year-quarter, election-date).
- **Concept catalog status** — none / single-source, or which concepts harmonize across which sources with which caveats.
- **Provenance scope** — per-extract sidecar by default; note any per-row provenance columns for OCR-fragile parsers.
- **Validation surface** — which parsers have pytest fixtures.
