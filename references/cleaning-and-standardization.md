# Cleaning and Standardization

The active counterpart to the audit/reconcile/bulletproofing references. Those describe *what's wrong*; this describes *what to do during a parser* to make a row conform to the canonical schema without losing the trail of what changed. Cleaning work happens between fetching the immutable original and writing the validated CSV — i.e. inside `scripts/parsers/<source>_<vintage>.py` and `scripts/clean.py`.

The skill commits to seven principles:

- **Originals are immutable.** Never write back to `data/original/`. Every cleaning operation reads from there and writes to `data/processed/` (or `data/audit/`).
- **Profile before you parse.** Inspect dtypes, distinct counts, null patterns, distributions *before* writing any coercion code.
- **Errors are durable, not fatal.** Malformed rows go to a *reject port* (`data/audit/rejected.csv`) with a reason; the rest of the pipeline keeps running.
- **Coerce explicitly.** Pandas's silent dtype inference is the source of most leading-zero bugs. Declare types at the boundary.
- **Document every transform.** A cleaning log (`data/audit/cleaning-log-<ts>.json`) records before/after counts per operation. Reproducibility is the property that distinguishes liberation from cleaning-by-spreadsheet.
- **Imputation is opt-in.** The default civic-data stance is to preserve missingness (NA) and document it, not to fill it. Imputation lives behind an explicit decision logged in `AGENTS.md`.
- **Redact PII at the boundary of `data/processed/`.** The originals retain whatever the publisher published; the processed CSV obeys the project's redaction policy.

## The cleaning pipeline

Run operations in this order — earlier steps surface issues that change how later steps behave. Skipping forward means redoing later.

| Step | Goal | Output |
|---|---|---|
| 1. Initial assessment | Know what you have | Profile report; structural-issues note |
| 2. Structural fixes | Make the shape canonical | Standardized column names, dtypes, no fully-empty rows/cols |
| 3. Deduplication | Remove redundant rows | Deduplicated frame + dropped-rows log |
| 4. Missing-value treatment | Decide per-mechanism, document | Frame with NA preserved or imputed with rationale |
| 5. Outlier detection | Catch the impossible and the suspicious | Outlier flag column (`outlier_method`, `outlier_reason`) |
| 6. Standardization / normalization | Make values uniform | Casing, encoding, formats unified |
| 7. Validation + reject port | Gate the canonical output | Valid rows → `data/processed/`; invalid → `data/audit/rejected.csv` |
| 8. PII redaction | Apply policy at the publish boundary | Redacted columns in `data/processed/` only |
| 9. Documentation | Log what changed | `data/audit/cleaning-log-<ts>.json` |

The rest of this reference unpacks each step with concrete tools and the integration point in this skill's project layout.

## 1. Initial assessment — profile before you parse

Three things, every time, before writing any coercion code:

- **`Describe`** — `df.describe(include='all')` for numeric + categorical summaries; `df.info()` for dtypes and non-null counts; `df.shape` for dimensions.
- **`Column profile`** — per column: dtype, distinct count, null count and percentage, min/max for numeric, top-5 frequent values for categorical, length distribution for strings.
- **`Histogram`** — for any numeric column, plot a histogram or compute quartiles. For categorical columns, plot a value-counts bar. Outliers and modal sentinel values (`-9`, `9999`, `1900-01-01`) show up immediately.

Tools, in order of escalation:

| Tool | When |
|---|---|
| `pandas.DataFrame.describe()`, `.info()`, `.value_counts()` | Default; for a quick parser-side profile |
| [`ydata-profiling`](https://github.com/ydataai/ydata-profiling) | One-shot HTML report; useful for sharing with non-Python collaborators |
| `DuckDB`'s `SUMMARIZE table` | When the data is large enough that pandas is slow |
| `sqlite-utils analyze-tables` | When the data is already in the Datasette SQLite file |

The profile produced *at this step* gets persisted: `audit.py`'s auto-generated `docs/variables.{md,csv}` is the durable artifact, and the diff between vintages is what surfaces drift over time. See the *profiling* sub-step of profiling / measurement / monitoring in [`data-modeling.md#data-quality`](data-modeling.md#data-quality).

## 2. Structural fixes

- **Column names → `snake_case`** with no spaces, no special characters, no leading digits. A small helper:
  ```python
  import re
  def snake(s: str) -> str:
      s = re.sub(r'[^0-9a-zA-Z]+', '_', s).strip('_').lower()
      if s and s[0].isdigit():
          s = '_' + s
      return s
  df.columns = [snake(c) for c in df.columns]
  ```
- **Dtype casting** with `pandas.to_numeric(..., errors='coerce')`, `pandas.to_datetime(..., errors='coerce')`, and explicit `dtype="string"` for ID-like columns. The `errors='coerce'` flag turns un-parseable values into `NaT`/`NaN` instead of raising — combined with the reject port (step 7), this is how the pipeline routes parser failures without crashing.
- **Split or merge columns** as the schema requires — e.g. an "Address" column → `street`, `city`, `state`, `zip`; or a `first_name` + `last_name` → `full_name`. Document either direction in the data dictionary.
- **Drop fully empty rows and columns:** `df.dropna(how='all')` for rows; `df.dropna(axis=1, how='all')` for columns. Fully empty *and not previously documented* is a structural artifact (Excel padding, export bug), not data.

## 3. Deduplication

Two kinds of duplicates, two different operations:

### Exact duplicates

```python
exact_dupes = df[df.duplicated(subset=KEY_COLS, keep=False)]
df = df.drop_duplicates(subset=KEY_COLS, keep='first')
```

The `subset=` argument matters. Across the whole row often catches too few (one whitespace character means two rows aren't equal); restricted to the natural key catches the right ones. Decide the keep policy and log it:

- **`keep='first'`** — earliest record wins; safe default when there's no quality difference.
- **`keep='last'`** — latest record wins; appropriate when records get corrected over time.
- **Merge** — fold the duplicates into one row, preferring non-null values per column. Pandas's `groupby(key).agg(...)` with a per-column priority dict is the standard pattern.

### Near-duplicates (fuzzy matching)

Two records that refer to the same entity but differ in spelling, case, whitespace, or transcription. Two algorithms cover most cases:

| Algorithm | What it measures | When to use |
|---|---|---|
| **Levenshtein** | Edit distance (insertions + deletions + substitutions) | OCR'd text, typos, transcription errors |
| **Jaro-Winkler** | String similarity favoring prefix matches | Names, addresses (where prefix consistency matters more than the tail) |

Tools:

- [`rapidfuzz`](https://github.com/maxbachmann/RapidFuzz) — the fast modern fuzzy-matching library; `fuzz.ratio`, `fuzz.token_sort_ratio`, `process.extract`.
- [`jellyfish`](https://github.com/jamesturk/jellyfish) — `jaro_winkler_similarity`, `damerau_levenshtein_distance`, plus phonetic encoders (Soundex, Metaphone, NYSIIS) when phonetic matches matter.
- [`recordlinkage`](https://github.com/J535D165/recordlinkage) — full record-matching framework with blocking, comparison, and classification stages; appropriate when matching across two large sources.

Pattern for **record matching** between two sources:

```python
import recordlinkage
indexer = recordlinkage.Index()
indexer.block('zip')                     # block by an exact-match field to limit pairs
candidate_pairs = indexer.index(df_a, df_b)
compare = recordlinkage.Compare()
compare.string('name', 'name', method='jarowinkler', threshold=0.85, label='name_sim')
compare.exact('dob', 'dob', label='dob_match')
features = compare.compute(candidate_pairs, df_a, df_b)
# features is a DataFrame of similarity scores per pair; threshold + score to classify
matches = features[features.sum(axis=1) > 1.5]
```

Output a *similarity score* with every match, and persist the pair-with-score table to `data/audit/`. Never silently merge near-duplicates without a reviewable record of which records were merged and at what similarity.

## 4. Missing-value treatment

The default is **preserve NA** and document the mechanism. Imputation is opt-in and requires an explicit AGENTS.md decision.

Classify the missingness mechanism (Rubin's framework):

| Mechanism | Definition | How to test | Reasonable response |
|---|---|---|---|
| **MCAR** — Missing Completely At Random | Missingness is unrelated to any variable, observed or not. *Example: lab samples randomly lost in transit.* | [Little's MCAR test](https://en.wikipedia.org/wiki/Missing_data#Little's_MCAR_Test); compare the distributions of observed columns conditional on missingness in the target column. | Listwise delete if <5% of records affected; document the deletion count. Mean/median imputation acceptable if needed downstream. |
| **MAR** — Missing At Random | Missingness depends on *observed* variables, not the missing value itself. *Example: younger participants skip income questions more.* | Compare missingness patterns across groups defined by observed variables (`df.groupby('age_bracket')['income'].isna().mean()`). | Multiple imputation (`sklearn.experimental.IterativeImputer`, `miceforest`) or regression imputation — both should be opt-in flags, not pipeline defaults. |
| **MNAR** — Missing Not At Random | Missingness depends on the *unobserved* value itself. *Example: high-income respondents refuse to report income.* | Cannot be tested from the data alone; requires domain knowledge or external corroboration. | Sensitivity analysis, selection models. Often the right answer is **don't impute** and document the bias in the data dictionary's caveat section. |

The data dictionary should record, per column, the three-way distinction Batini surfaces — *missing-and-known-to-exist* vs *does-not-exist* vs *unknown-whether-exists* — because they require different downstream treatment.

Concrete sentinel-to-NA conversion belongs in the parser, not the consumer:

```python
df['income'] = df['income'].replace([-9, -99, 999999, '.', 'N/A', 'NULL'], pd.NA)
df['birth_date'] = df['birth_date'].replace({'1900-01-01': pd.NaT, '9999-12-31': pd.NaT})
```

Document the sentinel set per column in `docs/data-dictionary.md` under *Known caveats*.

## 5. Outlier detection

Two complementary approaches; use both.

### Statistical outliers

| Method | Definition | When |
|---|---|---|
| **IQR rule** | Below `Q1 − 1.5·IQR` or above `Q3 + 1.5·IQR` | Default for skewed distributions; robust to non-normality |
| **z-score** | `|x − μ| / σ > 3` | When the column is approximately normal |
| **Mahalanobis distance** | Multi-variate distance from the centroid in covariance-weighted space | When outliers are only visible in two+ dimensions jointly |
| **Isolation Forest** | Tree-based density anomaly score | Large mixed-type data where rules are hard to set |

```python
q1, q3 = df['amount'].quantile([0.25, 0.75])
iqr = q3 - q1
df['amount_outlier'] = (df['amount'] < q1 - 1.5*iqr) | (df['amount'] > q3 + 1.5*iqr)
```

### Domain validation — the impossible-value table

A row whose value violates physical or definitional limits isn't outlier-suspicious; it's *wrong*. Catch these with explicit range checks:

| Field | Plausible range | Notes |
|---|---|---|
| Age (years) | 0 – 120 | Flag >100 for review |
| Height (cm) | 50 – 250 | |
| Weight (kg) | 1 – 300 | |
| Systolic BP (mmHg) | 60 – 250 | |
| Diastolic BP (mmHg) | 30 – 150 | Must be < systolic |
| Body temperature (°C) | 30 – 45 | |
| Likert scale | integers 1 – 5 | reject non-integers |
| Percentage | 0 – 100 | unless explicitly proportion (0 – 1) |
| Latitude | −90 – 90 | |
| Longitude | −180 – 180 | |
| Year of birth | 1900 – current year | Or earlier for historical datasets, with floor documented |
| Email | regex `^[^@\s]+@[^@\s]+\.[^@\s]+$` | Stricter validators (RFC 5322) are usually overkill |
| US ZIP | regex `^\d{5}(-\d{4})?$` | preserve as string |
| US phone | digits-only length 10, or E.164 `+1\d{10}` | |

Decision policy per outlier: **correct** (if you can verify), **cap** (winsorize to the plausible bound), **remove** (route to reject port), or **keep with flag** (an `outlier_method` column). Pick one per column, document it.

## 6. Standardization and normalization

Different sources will have spelled the same value many ways. Unify at parser time so downstream joins work.

- **Casing.** `str.lower()` / `str.upper()` / `str.title()` consistently. The pattern that breaks: `"BOB"` vs `"Bob"` vs `"bob"` are three rows after a naive `groupby`.
- **Whitespace.** `str.strip()` removes leading/trailing whitespace; `str.replace(r'\s+', ' ', regex=True)` collapses runs.
- **Unicode normalization.** `unicodedata.normalize('NFKC', s)` — converts ligatures, full-width characters, decomposed accents to a canonical form. Critical for any source that mixes ASCII and accented characters.
- **Encoding.** Detect with `chardet` if uncertain; convert to UTF-8 at read time. Document the source's actual encoding in `provenance.csv`.
- **Date formats.** Convert everything to ISO-8601 (`YYYY-MM-DD`). `pd.to_datetime(..., format='...', errors='coerce')` with the source's format declared explicitly. Never let pandas auto-detect on mixed-locale data — it will guess wrong on `01/02/2024`.
- **Phone numbers.** Normalize to E.164 (`+1\d{10}` for US). The [`phonenumbers`](https://github.com/daviddrysdale/python-phonenumbers) library handles parsing across countries.
- **Addresses.** USPS-standardized form for US addresses ([`usaddress`](https://github.com/datamade/usaddress) for parsing; [`scourgify`](https://github.com/EdgewiseSolutions/scourgify) for normalization). For non-US, `libpostal` is the more general option.
- **Categorical canonicalization.** A `data/lookups/normalize_<column>.yaml` mapping raw values to canonical ones — `{"Mr.": "Mr", "Mister": "Mr", "MR": "Mr"}` — applied at parse time. This is a one-way crosswalk; see the *concept catalog* in [`data-modeling.md#concept-catalogs`](data-modeling.md#concept-catalogs) for the multi-way cross-source case.
- **Regex / string transforms.** Lift common patterns into named functions in `scripts/parsers/_normalize.py` and import them per-parser. Examples: strip trailing `.` from name initials; collapse `St.` and `Street`; extract a leading numeric ID from `"R21-007: Description..."`.

## 7. Validation and the reject port

The **reject port** pattern: any row that fails a parser's validation rules goes to `data/audit/rejected.csv` with a `reject_reason` column and the original row content preserved. The pipeline keeps running. The reject port is a first-class audit artifact, not a debug file.

```python
def parse(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype=str)
    raw['_row_num'] = raw.index

    # apply structural fixes, normalization...

    valid_mask = (
        raw['age'].astype(float).between(0, 120) &
        raw['email'].str.match(EMAIL_RE) &
        raw['zip'].str.match(ZIP_RE)
    )
    rejected = raw.loc[~valid_mask].assign(
        reject_reason=lambda d: _reason_for_each(d),
        source_file=path.name,
    )
    rejected.to_csv(REJECT_PORT, mode='a', header=not REJECT_PORT.exists(), index=False)

    return raw.loc[valid_mask].drop(columns=['_row_num'])
```

Beyond per-record validation:

- **Schema validation** via `pandera` at the boundary of `clean.py` (covered in [`data-modeling.md#validation`](data-modeling.md#validation)).
- **Cross-field validation** — `start_date < end_date`; `diastolic_bp < systolic_bp`; `child_age < parent_age`; `total = sum_of_parts`. These are pandera `Check` callables, or explicit assertions in `clean.py` that route violations to the reject port.
- **Referential integrity** — values in a column must appear in a lookup table. E.g. every `precinct` in the data must appear in `data/lookups/precincts.csv`. Mismatches are usually new precincts (or typos) and warrant a review.
- **Business rules** — domain-specific assertions a stakeholder names. Capture them in a `scripts/validators.py` registry so the rule set is inspectable in one place.

## 8. PII redaction

A liberation project is publishing data; whatever PII was in the original *and is not load-bearing for the public-interest analysis* should be redacted from `data/processed/` outputs. The original retains the source's content; the processed outputs obey the project's policy.

Common PII patterns and a regex starter set (use as a baseline; combine with a real library for production):

| PII type | Regex (Python) | Replacement strategy |
|---|---|---|
| Email | `r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'` | `<EMAIL>` or a faker-generated token |
| US phone | `r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'` | `<PHONE>` |
| SSN | `r'\b\d{3}-\d{2}-\d{4}\b'` | `<SSN>` — and confirm the source legally should have shared this in the first place |
| Credit card | `r'\b(?:\d[ -]*?){13,19}\b'` | `<CC>`, then verify with a Luhn check before redacting (avoid false positives on long ID numbers) |
| IPv4 | `r'\b(?:\d{1,3}\.){3}\d{1,3}\b'` | `<IP>` |
| Date of birth | varies; flag any column the dictionary marks as DOB | hash, generalize to year-only, or drop |

Tools that are sturdier than rolling regex from scratch:

- [`presidio`](https://github.com/microsoft/presidio) — Microsoft's PII detection and anonymization library; ships analyzers for ~50 entity types and supports redaction, hashing, replacement, encryption.
- [`scrubadub`](https://github.com/LeapBeyond/scrubadub) — focused on email/URL/phone/SSN with a clean API.
- [`faker`](https://github.com/joke2k/faker) — produces realistic replacement values when full nulling would break downstream use.

The decision matrix:

| Use case | Redaction |
|---|---|
| Identifier never needed downstream | Drop the column entirely |
| Identifier needed for joins but not display | Hash with a project-secret salt; document the hash function in the dictionary |
| Identifier needed for display but not full precision | Generalize (ZIP → ZIP3; DOB → birth year; address → census tract) |
| Identifier load-bearing for accountability (elected officials' salaries, public-record case parties) | Keep, with the legal basis documented in the dictionary |

**Never** redact PII in `data/original/`. The hash manifest assumes those files are byte-identical to what the publisher published. Redaction is a publish-time transform.

## 9. Documentation

Every cleaning run writes one structured log: `data/audit/cleaning-log-<ts>.json`. Minimum content:

```json
{
  "run_ts": "2026-05-25T18:00:00Z",
  "source": "boulder_county_sov",
  "vintage": "2024-general",
  "parser": "boulder_sov_2024.py@a1b2c3d",
  "rows_in": 14823,
  "rows_out": 14801,
  "rows_rejected": 22,
  "transforms": [
    {"step": "snake_case_columns", "columns_renamed": 17},
    {"step": "sentinel_to_na", "column": "votes", "values_replaced": 142},
    {"step": "drop_exact_duplicates", "keys": ["precinct", "contest", "candidate"], "dropped": 8},
    {"step": "outlier_flag", "column": "votes", "method": "IQR", "flagged": 3},
    {"step": "pii_redact", "column": "voter_email", "strategy": "drop_column"}
  ],
  "reject_port": "data/audit/rejected.csv"
}
```

This log is what reviewers read on the refresh PR. The per-vintage diff between two runs surfaces silent drift — e.g., a sudden jump from 22 rejected rows to 4,200 means the parser broke or the source changed.

## Where this lives in the project

| Operation | Lives in |
|---|---|
| Per-source parser logic (steps 1–7) | `scripts/parsers/<source>_<vintage>.py` |
| Shared normalization helpers | `scripts/parsers/_normalize.py` |
| Cross-source orchestration | `scripts/clean.py` |
| Validators (cross-field rules, business rules) | `scripts/validators.py` |
| PII redaction policy (per column) | `scripts/publish.py` (applied to the published artifact only) |
| Lookup tables (categorical canonicalizations, FK targets) | `data/lookups/` |
| Reject-port output | `data/audit/rejected.csv` |
| Per-run cleaning log | `data/audit/cleaning-log-<ts>.json` |
| Schema enforcement (pandera) at the boundary | `scripts/schema.py` (see [`data-modeling.md#validation`](data-modeling.md#validation)) |

The cleaning pipeline runs once per vintage at parser time. The reject port and cleaning log are first-class audit artifacts, reviewed on every refresh PR. Drift in any of the per-transform counts is usually the earliest signal that the upstream source changed.
