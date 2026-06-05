# Discovery and Audit: Finding Upstream Changes and Verifying Against the Truth

The three "watchful" steps of a liberation pipeline. `discover.py` finds what's available upstream; `audit.py` reports on what came in; `reconcile.py` (opt-in) verifies that the processed output matches authoritative top-line totals from the original. Together, they are what makes a pipeline *trustworthy* rather than just *runnable*.

The patterns here are distilled from BoulderPublicData/Election-Results (where `reconcile.py` originated), the IPEDS pipeline (which formalized the `discover.py` self-refresh), and ProPublica's [data-bulletproofing guide](https://github.com/propublica/guides/blob/master/data-bulletproofing.md) (the journalistic practice that long predates either).

## Pre-extraction bulletproofing

Before writing a single parser, vet the source itself. ProPublica's data-bulletproofing guide distills this practice; the checklist below adapts it for the liberation workflow. Most of these are five-minute checks; skipping them buys hours of debugging later.

Each check below corresponds to a specific [data-quality dimension](data-modeling.md#data-quality) — naming the dimension makes the check defensible to engineers, and using the engineer's framework keeps the journalist honest about what's being measured:

| Check | Dimension it serves |
|---|---|
| Record count verification (watch for the 65,536-row Excel ceiling, powers of two) | Completeness |
| Top-line totals match the publisher's claim | Accuracy |
| Date and geography range checks | Timeliness; Relevance |
| `GROUP BY` every categorical field to surface spelling drift | Consistency |
| Find the publisher's codebook / methodology / statute | Usability (Documentation, Metadata) |
| Identify the records officer / contact | Usability (Credibility) |
| Discriminate blanks from sentinel values (`-9`, `9999`, `1900-01-01`) | Completeness (with the three-way *exists-but-unknown* / *does-not-exist* / *unknown-whether-exists* distinction in the data dictionary) |
| Demand questionnaires for survey-derived data | Usability (Credibility) |
| Cross-source corroboration | Consistency |
| Random-sample physical spot-check | Auditability |

The documentation-and-contact checks are *state reconstruction* — the under-rotated, highest-leverage phase that happens before any measurement code is written. See [`data-modeling.md#pipeline-shape`](data-modeling.md#pipeline-shape).

This checklist parallels the quality, provenance, and metadata best practices in the W3C **Data on the Web Best Practices** — DWBP is a useful published yardstick to skim once if you want an external "did we miss anything?" list, but the journalistic checklist here is the operational form. See [`open-data-standards.md`](open-data-standards.md#a-meta-synthesis-four-lenses-on-open-data) for the framing; it's background, not an added gate.

### Source-level checks

- **Record count.** Confirm the total matches what the publisher claims (or what an independent count says it should be). Watch for *suspicious round limits* — 65,536 rows in an Excel export, 1,048,576 rows, exactly 10,000 rows, powers of two — they often mean the export was truncated upstream.
- **Top-line totals.** If the source publishes a "Total" line, sum the rows and compare. A mismatch here is either an arithmetic error in the source (document it explicitly in `docs/data-dictionary.md` under "Known mismatches" — see [reconciliation](#reconciliation)) or evidence the export is incomplete.
- **Date and geography ranges.** Does the data actually cover the years and jurisdictions the publisher claims? A "1980–present" dataset that has zero records before 1995 needs explaining.
- **Categorical field consistency.** `GROUP BY` every important categorical column and read the result. Spelling variations (`"Main St"` vs `"Main Street"` vs `"MAIN ST."`), trailing whitespace, and case differences are how dirty data hides.
- **Blank values.** Determine whether blanks are *real values* (the publisher genuinely didn't measure this) or *import errors* (the column dropped during export). The two cases require different treatment in the parser.
- **Suspicious sentinel values.** `-9`, `9999`, `99999999`, `-1`, `1900-01-01`, the empty string — government datasets use ALL of these for "missing." Document the ones this source uses and convert them to NA in the parser, not silently in the pipeline. See [`cleaning-and-standardization.md`](cleaning-and-standardization.md#4-missing-value-treatment) for the Rubin MCAR/MAR/MNAR framework and treatment choices.
- **Format-native error markers are quality signals, not noise.** When the source format encodes its own failure states — `#REF!`, `#DIV/0!`, `#VALUE!`, `#N/A`, `#NAME?` in spreadsheets; `null` in JSON columns the schema says are required; `<missing>` placeholders in HTML tables — those errors *originated with the publisher*, not the parser, and they're worth surfacing as audit findings rather than silently coerced to NA. The principle generalizes past spreadsheets: any format-native "this value is broken" marker is a publisher-side data-quality issue worth a row in `data/audit/source_errors.csv` so the count can be trended over time. Silently converting them to NA loses the signal that the *source* has a problem.

### Methodology and provenance checks

- **Find the original documentation.** The publisher's codebook, methodology PDF, statute or regulation mandating the publication. Read it before parsing. If you can't find one, that's a finding worth recording in `AGENTS.md` "Known limitations."
- **Identify the contact.** Records officer, FOIA liaison, the journalist who last covered this beat, the academic who maintains a derivative dataset. Make the introduction early; you'll need them when something is weird.
- **Demand questionnaires/methodologies for survey-derived data.** Refusal to share methodology is a red flag worth naming. Identify non-scientific methods (web-based panels, self-selection) and bake that caveat into the dictionary.
- **Cross-source corroboration.** Find an independent source for the same underlying phenomenon — a federal mirror of state data, an aggregator (Census, BLS), a watchdog dataset that audits the original. Two sources that match build confidence; two that diverge surface a story.

### When the source path is a records request (FOIA / sunshine laws)

If the data has to be *requested* rather than downloaded, the request itself is part of the Survey. A few process notes that change what you get back:

- **Ask for data, not narrative.** Request the underlying records in their native machine-readable format ("the database export / the spreadsheet behind this report," not "a report about X"). Agencies often default to printing-to-PDF; naming the format you want up front avoids a re-request.
- **Know the clock and the fee tiers.** Federal FOIA runs ~20 business days (often longer); fee categories differ for commercial vs. news-media/educational vs. other requesters, and waivers exist for public-interest requests. State **sunshine / open-records laws** vary — the records officer is the contact, and `FOIA.gov` routes federal requests.
- **Treat redactions as findings, not just obstacles.** A heavily-redacted or truncated release can still carry usable tables; record what was withheld and the claimed exemption in `AGENTS.md` "Known limitations." An *excessive* redaction is itself a transparency story worth naming, not silently absorbing.
- **Decide what the project will not liberate.** "Available to extract" is not the same as "responsible to publish." Where a release contains personal data that privacy law protects, or where the downstream use is one the project considers out of scope, that judgment belongs in the Survey, not after publication — see the governance section of [`project-template.md`](project-template.md#governance). The wider transparency-law and records-request landscape is catalogued in [`open-government-landscape.md`](open-government-landscape.md).

### Cognitive checks worth naming

- *"If something doesn't seem right, it probably isn't."* The 50% year-over-year jump that doesn't appear in the press? Almost always an extraction bug, not a real spike.
- *"Avoid false precision."* Reporting "52.18%" when the underlying counts have ±30 of margin invents accuracy. The data dictionary should declare which columns have meaningful precision and which round to integers.
- *"Set a cutoff date."* Organic datasets that grow during your reporting will rewrite history under you. Pick a freeze date, document it, and don't reach past it except for explicit corrections.
- *"Spot-check physically."* For a small sample (say, 10 records), open the original source artifact and verify each cell of the processed CSV by eye. This catches column-shift bugs that no automated check finds.

### A practitioner's prep list

The colleagues quoted in ProPublica's guide each contributed one durable practice; the union is the working baseline:

- **Maintain a work log.** A `docs/notebook.md` recording each cleaning decision, why, and when. The IPEDS pipeline's `AGENTS.md` is the maximalist version; a chronological log is the minimum.
- **Document SQL.** Every non-trivial query in the audit or reconcile modules gets a comment explaining why this aggregation/filter, not just what it does.
- **Write the alternate query.** For top-line numbers that will be published, derive the same value via a different code path. Two queries that agree raise confidence by more than two queries that look similar.
- **Random-sample validation.** Pull 50 rows at random from the processed CSV; verify each against the original. Repeat after every significant parser change.
- **Pre-publication review.** Show findings to the subject before publishing them. Errors caught at this stage are corrections; errors caught after are retractions.

### How this fits the workflow

| Workflow phase | Bulletproofing checks that belong here |
|---|---|
| **Survey** | Source-level checks against publisher's own summary; methodology/provenance fact-finding; identifying the contact |
| **Extract** | Sentinel-value handling in parsers; categorical consistency; physical spot-checks of the first parser's output |
| **Tidy** | Date and geography range verification post-normalization; cross-source corroboration setup |
| **Audit** | `audit.py` automates the easy checks (null rates, distinct values, suspicious counts); see [Audit](#audit-what-came-in) below |
| **Reconcile** | Top-line totals against the source's own published total; see [Reconciliation](#reconciliation) below |

The Survey-phase checks are the cheapest and the most under-done. Lean into them.

## Discovery

**Discovery's job:** answer the question "is there a vintage we don't have yet?" without downloading anything. A correctly-implemented `discover()` is cheap, idempotent, and a precondition for any recurring-refresh workflow.

Two patterns, depending on how the upstream publishes.

### Static-list discovery

For sources where new vintages appear at predictable URLs — say, an agency that publishes `https://example.gov/annual-report/2024.pdf`, `…/2025.pdf` annually — the `discover()` implementation is a static URL pattern plus a year range:

```python
# scripts/sources.py (excerpt)
from datetime import datetime
from scripts.sources import Source, Artifact


class AgencyAnnualReport(Source):
    name = "agency_annual"
    label = "Example Agency Annual Report"
    URL_PATTERN = "https://example.gov/annual-report/{year}.pdf"

    def discover(self):
        current = datetime.now().year
        for year in range(2010, current + 1):
            yield Artifact(
                source=self.name,
                vintage=str(year),
                url=self.URL_PATTERN.format(year=year),
                local_path=Path(f"data/original/{self.name}/{year}/report.pdf"),
                metadata={"year": year},
            )
```

The corresponding `fetch.py` is responsible for HEAD-checking each artifact (so a year that hasn't been published yet doesn't get downloaded). Discovery is the catalog; fetch is the gate.

### Index-page discovery

For publishers with an index page that lists what's available — most agencies' "Reports" landing pages, most secretary of state election archives — `discover()` scrapes the index and yields one artifact per linked PDF/XLSX/CSV:

```python
import httpx
from selectolax.parser import HTMLParser


class BoulderCountySoV(Source):
    name = "boulder_county_sov"
    label = "Boulder County Statement of Vote"
    INDEX_URL = "https://bouldercounty.gov/elections/historical-results/"

    def discover(self):
        with httpx.Client() as client:
            html = client.get(self.INDEX_URL).text
        tree = HTMLParser(html)
        for link in tree.css("a[href$='.pdf']"):
            href = link.attributes.get("href", "")
            text = link.text(strip=True)
            vintage = self._parse_vintage(text)
            if vintage is None:
                continue
            yield Artifact(
                source=self.name,
                vintage=vintage,
                url=href,
                local_path=Path(f"data/original/{self.name}/{vintage}/sov.pdf"),
                metadata={"link_text": text},
            )

    @staticmethod
    def _parse_vintage(link_text: str) -> str | None:
        """Extract `2009` from `'2009 General Election - Statement of Vote (PDF)'`."""
        import re
        m = re.search(r"\b(20\d{2})\b", link_text)
        return m.group(1) if m else None
```

This is what makes the pipeline self-updating: a cron run of `discover → fetch → clean → audit` automatically picks up a new vintage when the publisher posts it. The recurring-refresh pattern below depends on this.

### Standalone discovery script

`scripts/discover.py` runs every source's `discover()` and prints what's available, optionally filtering to "what's not yet in `data/original/`":

```bash
$ uv run python -m scripts.pipeline discover
boulder_county_sov: 12 artifacts available, 11 already fetched, 1 NEW
  NEW  2024: https://bouldercounty.gov/.../2024-sov.pdf
co_secretary_of_state: 8 artifacts available, 8 already fetched
```

Output also written to `data/audit/discovery-<ts>.txt`. The diff between consecutive runs is a useful change signal: a new vintage appearing is the trigger to fetch.

## Audit: what came in

**Audit's job:** answer "does what we just produced look right?" Run after every `clean.py` pass. The artifact is `data/audit/summary-<ts>.md`, scannable in 30 seconds by a maintainer reviewing a refresh PR.

What goes in the audit (this is what `audit.py` writes to `data/audit/summary-<ts>.md`):

| Section | What it tells you |
|---|---|
| **Row count** | Total rows in the processed CSV. Headline number for refresh diffs. |
| **Source coverage** | Rows per `(source, vintage)`. Should match expectations: every registered source × vintage should be non-zero. |
| **Null rates per column** | Catches schema drift (a column suddenly all-null usually means a layout change broke a parser). |
| **Distinct values for low-cardinality columns** | Sanity check for categorical columns: did the controlled vocabulary just gain or lose a value? |
| **Empty sources / vintages** | Explicit flagged section. A registered source returning zero rows is almost always a regression. |
| **Extraction errors** | Summary of `data/audit/extraction_errors.json` — which artifacts failed to parse, with the exception type and the first line of the error. |

The Markdown format is deliberate. Auto-generated reports that nobody reads are wasted effort; Markdown renders inline in a GitHub PR diff and is what a human reviewer actually sees.

### A minimal audit implementation

```python
# scripts/audit.py
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import structlog

from scripts.config import DATA_AUDIT, PROCESSED_CSV

log = structlog.get_logger()


def audit_all() -> int:
    if not PROCESSED_CSV.exists():
        log.error("audit_no_processed_csv", path=str(PROCESSED_CSV))
        return 1

    df = pd.read_csv(PROCESSED_CSV, dtype=str)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = DATA_AUDIT / f"summary-{ts}.md"

    lines = [f"# Audit Summary — {ts}", "", f"Rows: **{len(df):,}**", ""]
    lines.extend(_section_source_coverage(df))
    lines.extend(_section_null_rates(df))
    lines.extend(_section_low_cardinality(df))
    lines.extend(_section_empty_sources(df))
    lines.extend(_section_extraction_errors())

    out.write_text("\n".join(lines))
    variables_report(PROCESSED_CSV)
    return 0


def _section_source_coverage(df):
    coverage = (
        df.groupby(["source", "vintage"], dropna=False)
        .size().rename("rows").reset_index()
        .sort_values(["source", "vintage"])
    )
    return ["## Source coverage", "", coverage.to_markdown(index=False), ""]
```

### `docs/variables.{md,csv}` — the long-form column report

The same `audit.py` (or a sibling function) emits the long-form per-column summary that complements the hand-maintained `docs/data-dictionary.md`:

```python
def variables_report(processed_csv: Path) -> None:
    df = pd.read_csv(processed_csv)
    rows = []
    for col in df.columns:
        s = df[col]
        rows.append({
            "column": col,
            "dtype": str(s.dtype),
            "distinct": int(s.nunique(dropna=True)),
            "null_rate": float(s.isna().mean()),
            "min": s.min() if pd.api.types.is_numeric_dtype(s) else "",
            "max": s.max() if pd.api.types.is_numeric_dtype(s) else "",
            "sample_values": ", ".join(str(v) for v in s.dropna().unique()[:5]),
        })
    rep = pd.DataFrame(rows)
    rep.to_csv("docs/variables.csv", index=False)
    Path("docs/variables.md").write_text(
        "# Variables (auto-generated)\n\n" + rep.to_markdown(index=False)
    )
```

If `variables.csv` says a column is `object` and `docs/data-dictionary.md` says it's `Int64`, the dictionary is wrong or the parser is. Treat their agreement as a precondition — see `references/data-modeling.md` for the rationale.

### Recording extraction errors

`audit.py` also defines `record_extraction_error()`, called from `clean.py` when an individual artifact's parse fails. The pipeline doesn't stop — the failure appends to `data/audit/extraction_errors.json` and the next vintage proceeds:

```python
def record_extraction_error(*, source: str, artifact, error: Exception) -> None:
    EXTRACTION_ERRORS_JSON.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(EXTRACTION_ERRORS_JSON.read_text()) if EXTRACTION_ERRORS_JSON.exists() else []
    existing.append({
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "artifact_url": artifact.url,
        "artifact_vintage": artifact.vintage,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": "".join(traceback.format_exception(type(error), error, error.__traceback__)),
    })
    EXTRACTION_ERRORS_JSON.write_text(json.dumps(existing, indent=2, default=str))
```

This is the "durable, not fatal" pattern: a parser failure on one vintage doesn't block the eleven other vintages from refreshing. The audit summary flags it next run; a human investigates on their own schedule.

## Reconciliation

For high-stakes pipelines (anything that will be cited publicly — election results, financial reports, agency budgets), re-open each original file independently and compute a small set of authoritative top-line totals, then compare to the processed output. Mismatches are regressions: the pipeline run completes (don't lose the data), but CI fails on the reconcile job and the audit flags it.

[BoulderPublicData/Election-Results' `reconcile.py`](https://github.com/BoulderPublicData/Election-Results) is the canonical example. It currently has 149 of 150 cross-checks matching exactly. The one mismatch is documented in `docs/data-dictionary.md` with the upstream-error explanation (a Statement of Vote PDF that itself contained an arithmetic error in one precinct subtotal). That kind of *known and documented* mismatch is what "safe scrutiny" looks like at a pipeline level — not zero mismatches, but every mismatch accounted for.

### The skeleton

```python
# scripts/reconcile.py
from dataclasses import dataclass, field
from typing import Callable

import pandas as pd


@dataclass
class Check:
    label: str
    expected: int | float
    actual: int | float
    match: bool
    delta: int | float = 0
    notes: str = ""


@dataclass
class ReconcileResult:
    source: str
    checks: list[Check] = field(default_factory=list)


def reconcile_boulder_sov() -> ReconcileResult:
    """Sum votes per contest from each original PDF; compare to processed CSV."""
    df = pd.read_csv("data/processed/boulder_election_results.csv")
    checks: list[Check] = []
    for original_pdf in sorted(Path("data/original/boulder_county_sov").rglob("*.pdf")):
        vintage = original_pdf.parent.name
        pdf_totals = _extract_totals_from_pdf(original_pdf)  # parser-specific
        csv_totals = (
            df.query("source == 'boulder_county_sov' and vintage == @vintage")
              .groupby("contest")["votes"].sum().to_dict()
        )
        for contest, expected in pdf_totals.items():
            actual = csv_totals.get(contest, 0)
            checks.append(Check(
                label=f"{vintage}:{contest}",
                expected=expected, actual=actual,
                match=(expected == actual),
                delta=actual - expected,
            ))
    return ReconcileResult(source="boulder_county_sov", checks=checks)


RECONCILE_REGISTRY: dict[str, Callable[[], ReconcileResult]] = {
    "boulder_county_sov": reconcile_boulder_sov,
}
```

### When to turn reconciliation on

Default: off. Reconciliation costs developer time to write per-source logic and CI time on every run.

Turn it on when:

- The data will be cited publicly.
- The data is contested (election results, salary databases, anything where someone has motivation to dispute the numbers).
- The publisher publishes top-line totals separately from the per-row data, *and* those totals are authoritative (the published total is the ground truth, not just a side-effect).

Don't turn it on for:

- Exploratory pipelines.
- Sources where you don't have an independent total to compare against.
- One-shot extractions that won't be re-run.

When you do turn it on, document the reconciliation logic in `AGENTS.md` so a future maintainer knows which totals are the authoritative ones to check against. Boulder Election-Results does this clearly: the AGENTS.md section "What reconcile.py checks" enumerates the four authoritative totals per Statement of Vote and explains why each is independent of the per-precinct rows.

### Reconcile output

`scripts/reconcile.py` writes `data/audit/reconcile.json` with the full per-check results and prints a summary:

```
$ uv run python -m scripts.pipeline reconcile
[boulder_county_sov] 149/150 checks matched
    ✗ 2009:BOULDER COUNTY COMMISSIONER DISTRICT 1: expected=23456 actual=23457 delta=1
       (known: precinct 042 subtotal in source PDF has +1 arithmetic error;
        see docs/data-dictionary.md "Known mismatches")
```

Non-matching checks return a non-zero exit code, which fails the CI reconcile job. The pipeline `run` workflow continues; the reconcile failure is a separate signal.

## The recurring-refresh pattern (cron + PR)

For recurring sources (annual statements of vote, monthly FOIA logs, weekly compensation pulls), wire a GitHub Actions cron that runs `discover → fetch → clean → audit` and opens a PR with the new data and audit report. The template ships a ready-to-rename `refresh.yml.disabled`; the canonical pattern is captured there. Three decisions matter:

**Cadence — slightly trail the publisher.** Faster than the publisher updates wastes compute and pollutes the audit history; lagging is fine because `workflow_dispatch` covers the impatient case.

| Publisher cadence | Cron |
|---|---|
| Annual (post-certification) | `"0 13 1 11 *"` — Nov 1, 13:00 UTC |
| Monthly | `"0 13 1 * *"` — 1st of each month |
| Weekly | `"0 13 * * 1"` — Mondays |
| On-demand | Omit `schedule:`; keep `workflow_dispatch:` |

**PR, not commit-to-main.** Auto-commits make a silent change to published data. A PR forces a human pass on four signals: does the row-count delta in `data/audit/summary-*.md` match expectations? Any new entries in `extraction_errors.json`? Any new "Empty sources" flags? Did `reconcile.py` (if enabled) newly mismatch? Mature pipelines with strong reconcile coverage sometimes relax this to commit-to-main with audit-driven rollback; PR is the safer default and what BoulderPublicData, PUDL, and IPEDS-pipeline actually use.

**Path-scoped commits.** Stage `data/original/**`, `data/processed/**`, `data/audit/**`, and the auto-generated `docs/variables.*` files. Anything outside that scope means the workflow misbehaved.

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `discover.py` reports zero artifacts | Index page redesigned; CSS selector no longer matches | Update the selector; commit a recorded HTTP cassette in `tests/fixtures/` so the test catches the next breakage |
| Audit shows null rates of 1.0 for a previously-working column | Parser broke silently on a layout change | Look at the most recent vintage in `data/original/`; compare to the prior vintage's layout |
| `extraction_errors.json` accumulates across runs without anyone noticing | Audit summary doesn't surface error count prominently enough | Add an early-section "⚠️ N extraction errors" line to the audit Markdown |
| Reconcile passed for years and now fails on one check | (a) Genuine regression in a new parser, OR (b) upstream arithmetic error in the source PDF | Re-open the source PDF; compute the totals by hand on one precinct. If the source PDF itself is wrong, document in `docs/data-dictionary.md` "Known mismatches" and adjust the expected total. |
| Cron runs daily and the publisher updates annually | Cadence mismatch; audit history is mostly noise | Move cron to annual; use `workflow_dispatch` for impatient refreshes |
| PR from cron sits unreviewed for months | No notification or human accountability | Add a `CODEOWNERS` entry; configure GitHub notifications; or move to commit-to-main with strong audit-driven rollback |

## What to write in the AGENTS.md

- **Refresh cadence** — the cron expression (if `refresh.yml` is enabled) and which day of the publication cycle it trails.
- **Discovery surface** — what `discover.py` checks per source (URL pattern, index page, year range). First place to look when a publisher redesigns.
- **Reconcile scope** (if enabled) — which authoritative totals are checked against which originals, plus a "Known mismatches" subsection with each entry's explanation.
- **Audit invariants** the summary alone can't express, e.g., "source X should always be non-empty for vintages ≥ 2010" or "null rate on `precinct` must stay ≤ 0.01."
