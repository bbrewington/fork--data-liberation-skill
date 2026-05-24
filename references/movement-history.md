# Movement History: Data Liberation as Activism and Method

This reference grounds the skill in two intertwined traditions: the **civic data liberation movement** (an activist response to the inaccessibility of public data) and the **academic table-and-document understanding literature** (the methodological response to the same problem). They are the same struggle viewed from different sides, and a skilled data liberator draws on both.

Read this once at the start of a new project. It shapes how you frame the README, what citations belong in the AGENTS.md, and which design decisions are worth defending.

## Why "liberation"?

Tables and figures in PDF documents are arguably the dominant medium of public-record data communication: budget reports, statements of vote, FOIA responses, regulatory filings, scientific articles, statistical abstracts. The format is convenient for publishers and human readers, and deeply hostile to machine readability. A PDF table is, in computational terms, a set of rendering instructions: text strokes positioned on a page, sometimes accompanied by line strokes that suggest (but do not declare) a grid. Reconstructing the relational structure is a research problem (see [academic framing](#academic-framing) below); reconstructing it across many documents at scale is a civic infrastructure problem.

The term "liberation" enters from the activist side. Tom Lee at the Sunlight Foundation, [writing in early 2014](https://sunlightfoundation.com/2014/01/24/pdf-liberation-why-it-matters-and-how-you-can-help/), framed the problem this way: government PDFs lock up public data inside a format that is technically open but practically closed. The fix is not to scold publishers into using better formats (a slow battle that civil society has been losing for decades), but to build durable tooling and shared corpora that move data out of PDFs and into analyzable form. The Sunlight Foundation organized a PDF Liberation Hackathon in 2014; the [PDF Liberation Working Group](https://github.com/pdfliberation) on GitHub became a clearinghouse for tools and conventions. The phrase stuck because it names the underlying politics: the data was already public, but extraction labor was the gate.

## Lineage of civic liberation projects

A short, opinionated genealogy. Each project taught the community something that this skill encodes.

### Sunlight Foundation and the PDF Liberation Hackathon (2013–2014)

Sunlight's blog post coined the framing and the hackathon scaffolded the first wave of shared tooling. The lessons that survived: PDF extraction is per-document craft (no universal parser), open-source toolchains accumulate value across projects, and *most of the value is in documentation* (without provenance and a data dictionary, an extracted CSV is barely more useful than the original PDF).

### NPP / Tax Break — Recovery Act spending (2010s)

The [NPP tax-break project](https://github.com/npp/tax-break/tree/master) was an early demonstration that *patient, source-by-source extraction* could produce a longitudinal dataset from federal disclosure PDFs that researchers and journalists could query. It pioneered the convention — now ubiquitous — of treating each agency × year PDF as its own parser, with a thin schema-conformance layer above.

### MuckRock and the FOIA-driven liberation (2010s–ongoing)

[MuckRock](https://www.muckrock.com/) industrialized FOIA requests and accumulated a corpus of agency releases, mostly PDFs of wildly variable quality. The [BU Spark × MuckRock liberation project](https://github.com/BU-Spark/ds-muckrock-liberation/tree/main) is one of several student-team efforts to turn that corpus into reusable structured data. The lesson: the corpus is heterogeneous, the long tail is huge, and pragmatic per-document parsers + good provenance beats any universal extractor.

### PUDL — Public Utility Data Liberation (catalyst-cooperative, 2017–ongoing)

[PUDL](https://github.com/catalyst-cooperative/pudl) is the mature reference for infrastructural liberation: a multi-source ETL pipeline that harmonizes FERC, EIA, EPA energy data into a unified relational database with rigorous documentation, versioning, and CI. PUDL's conventions — `data/raw/` ↔ `data/processed/`, source-by-source ingest modules, comprehensive data dictionaries, vintage tracking, CI-built artifacts — directly inform the project template in this skill. PUDL also demonstrates that an academic-quality data infrastructure can be sustained as an open-source project with public funding.

### BoulderPublicData — Election-Results and Cast-Vote-Records (2020s)

[Boulder Public Data](https://github.com/BoulderPublicData) shows the small-scale modern shape of liberation work: 1–3 contributors, single-domain (elections), heavy automation. [Election-Results](https://github.com/BoulderPublicData/Election-Results) harmonizes 2004–2024 precinct-level statements of vote from Boulder County and the Colorado Secretary of State into a tidy long-form dataset, with a `reconcile.py` that re-opens originals to verify the processed totals match — an audit pattern worth stealing for any pipeline where the source carries an authoritative top-line. [Cast-Vote-Records](https://github.com/BoulderPublicData/Cast-Vote-Records) liberates anonymized ballot-level data using Colorado's Risk-Limiting Audit framework as the legal mechanism. Both repos use `uv` + AGENT.md + `data/original/` ↔ `data/processed/` ↔ `data/audit/` ↔ `data/lookups/` — the convention adopted here.

### What the lineage teaches

Across these projects a few hard-won patterns recur:

- **Per-source, per-vintage parsers.** No universal PDF extractor. Each new vintage is a parser file. Resist the urge to generalize prematurely.
- **Immutable originals.** The source files are part of the dataset. Hash them, commit them (or LFS them), and never edit them in place.
- **Tidy long-form as canonical storage; wide as analysis output.** Storage rewards uniformity; analysis rewards locality. Don't fight the trade.
- **Documentation is half the work.** A liberation without a data dictionary, a crosswalk, and a provenance trail is a private spreadsheet. The point is reuse.
- **Audit against originals.** A pipeline that doesn't reconcile against its source is faith-based. Reconciliation is what makes the dataset defensible.

## Academic framing

The activist tradition has a methodological counterpart in the document analysis and data engineering research literature. Three threads matter for this skill.

### CRISP-DM and its descendants

[CRISP-DM](https://www.ibm.com/docs/en/spss-modeler/saas?topic=guide-data-understanding) (Cross-Industry Standard Process for Data Mining), drafted in the late 1990s and now ubiquitous, divides a data project into six phases: business understanding, **data understanding**, **data preparation**, modeling, evaluation, **deployment**. This skill targets the bolded three — the rest belong to the analyst after liberation is done.

The data-understanding phase has long been the under-specified one. CRISP-DM names it but offers little methodological guidance; Holstein, Spitzer, Hoell, Vössing, and Kühl (2024, ECIS) propose [a five-dimension framework](https://aisel.aisnet.org/ecis2024/) that fills this gap:

| Dimension | What it covers |
|---|---|
| **Foundations** | Infrastructure, provenance, characterization (basic descriptive statistics, metadata) |
| **Collection & Selection** | What data to gather; what subsets to keep; identifying gaps |
| **Contextualization & Integration** | Linking data to domain knowledge; integrating multiple sources |
| **Exploration & Discovery** | Iteratively examining the data to surface clusters, patterns, anomalies |
| **Insights** | Documentation artifacts (collection report, description report, quality report); evaluating data quality and deciding whether to proceed |

The Holstein framework is descriptive — it names the dimensions that any data understanding effort traverses. The contribution of this skill is to make the traversal **operational**: each phase of the liberation workflow produces specific artifacts (Survey notes ≈ Holstein "Insights"; the data dictionary ≈ "Foundations"; the concept catalog ≈ "Contextualization & Integration"; `audit.py` output ≈ "Exploration & Discovery").

### Table Understanding (TU)

The document analysis research community has spent thirty-plus years on the table parsing problem. The canonical decomposition, surveyed by [Shigarov (2023, *WIREs Data Mining and Knowledge Discovery*)](https://doi.org/10.1002/widm.1482), distinguishes two top-level subproblems and seven tasks:

```
Table Understanding (TU)
├── Table Extraction (TE)
│   ├── Table Detection (TD)              <- find table regions in the document
│   ├── Table Structure Recognition (TSR) <- recover rows, columns, cells
│   ├── Table Functional Analysis (TFA)   <- header vs data; cell roles
│   └── Table Structural Analysis (TSA)   <- relationships between cells
└── Table Interpretation (TI)
    ├── Table Canonicalization (TC)       <- to a relational form
    ├── Table Normalization (TN)          <- to 3NF; entity resolution
    └── Semantic Table Interpretation (STI) <- match to a knowledge graph
```

Practical liberation work touches all of TE plus the canonicalization and normalization portions of TI. Semantic interpretation (matching to Wikidata/DBpedia) is a research frontier rarely needed for civic data work, though it can be useful for harmonizing entity names across sources (e.g., institution names, jurisdictions).

The state of the art for born-digital PDF table extraction, surveyed by [Kasem et al. (2024, *ACM Computing Surveys*)](https://doi.org/10.1145/3657281), is close to solved for cleanly ruled tables and unsolved for the long tail of complex layouts (multi-page tables, merged headers, panel formats). Practical implication: **start with rule-based / heuristic tools (pdfplumber, camelot) and resist the temptation to reach for deep-learning table extractors** unless the layout is genuinely beyond classical methods. The deep-learning frontier (TableFormer, CascadeTabNet, GTE) is impressive but rarely worth the operational cost for civic data, where per-document craft remains the most reliable approach.

The [ICDAR table competition evaluation methodology](https://doi.org/10.1145/2361354.2361365) (Göbel et al., 2012) gives the canonical performance metrics: precision/recall on table regions, on cell adjacency relations, and (for TI) tree-edit-distance similarity (TEDS). For civic liberation purposes the more useful audit is *top-line reconciliation* (see the Boulder Election-Results `reconcile.py` pattern) — does the sum of votes in the extracted CSV match the published total? — because it tests both extraction fidelity and downstream cleaning together.

#### Where the field has expanded since 2023

The Shigarov decomposition above frames the *extraction* side of table understanding. A parallel literature, surveyed in [tanfiona/LLM-on-Tabular-Data-Prediction-Table-Understanding-Data-Generation](https://github.com/tanfiona/LLM-on-Tabular-Data-Prediction-Table-Understanding-Data-Generation), organizes the *interpretation* side into eight task families that researchers benchmark separately:

| Task family | What the system does |
|---|---|
| **Question Answering** | Answer natural-language questions against a table (open or closed-domain). |
| **Numeric Question Answering** | Subset where the answer requires arithmetic over multiple cells — sums, ratios, year-over-year deltas. The hard case for LLMs. |
| **Text2SQL** | Translate a question into the SQL that would answer it against a known schema. |
| **Table2Text** | Generate a faithful natural-language summary of a table or table region. |
| **Fact Verification** | Decide whether a claim is supported, contradicted, or unanswerable from a table. |
| **Table Profiling** | Produce metadata about a table — dtypes, key columns, plausible joins, semantic types. |
| **Table Transformation** | Reshape a table — pivot, unpivot, fill, dedupe — by example or instruction. |
| **Entity Matching** | Decide whether two rows from different tables refer to the same real-world entity. |

For civic liberation work, **profiling, transformation, and entity matching** map directly onto the pipeline: profiling is what `scripts/audit.py` partially automates; transformation is what every parser does; entity matching is the concept-catalog problem under a different name. The QA and fact-verification work is mostly downstream of liberation — useful for the consumers of the published Datasette, less useful for building it.

The canonical benchmarks are useful as fixtures (or as inspiration for fixtures) when a parser handles a layout class that resembles one of them:

| Benchmark | Domain | Size | Use it when |
|---|---|---|---|
| [PubTabNet](https://github.com/ibm-aur-nlp/PubTabNet) | Scientific paper tables | ~568k | Borrowing test cases for ruled-table extraction at scale |
| [FinTabNet](https://developer.ibm.com/exchanges/data/all/fintabnet/) | Financial report tables (10-K, 10-Q) | ~112k | Government budget PDFs, agency annual reports |
| [SciTSR](https://github.com/Academic-Engineering-Materials/SciTSR) | Table Structure Recognition | ~15k | Multi-page tables with merged headers |
| [ICDAR competition corpora](https://tamirhassan.com/html/competition.html) | Mixed PDF tables | varies | Hard cases — the corpus is curated for adversarial layouts |
| [TabFact](https://tabfact.github.io/) | Wikipedia table fact-verification | ~16.6k | Less applicable; useful only if a project ships claim-checking |
| [WikiTableQuestions](https://ppasupat.github.io/WikiTableQuestions/) | QA over Wikipedia tables | ~2k | Downstream consumer benchmarking; not for extraction |
| [TAT-QA](https://github.com/NExTplusplus/TAT-QA) | Hybrid table+text financial QA | ~2.8k | When the source mixes tables with narrative numbers |
| [ToTTo](https://github.com/google-research-datasets/ToTTo) | Table-to-sentence | ~120k | Generating natural-language descriptions of rows (rarely needed in liberation) |
| [HiTAB](https://github.com/microsoft/HiTab) | Hierarchical statistical tables | ~3.6k | Census-style cross-tabulations |

The pragmatic implication for this skill stands unchanged: **rule-based first, deep-learning only when classical methods genuinely fail**, and even then prefer the open-source extractors with reproducible behavior (TableFormer, CascadeTabNet) over closed LLM table-parsers (which produce outputs you can't audit). The published reconciliation against the source's own top-line total is the test that matters; benchmark scores correlate weakly with that.

For a current snapshot of the literature, tanfiona's repo is the best-maintained index. Read it once when starting a parser that will hit non-trivial layouts; skip it for tabular sources that are already mostly clean.

### Tidy data and the Wickham tradition

Hadley Wickham's 2014 paper "Tidy Data" (*Journal of Statistical Software*) is the methodological anchor for the canonical storage shape used here: one row per observation, one column per variable, one cell per value. Almost every mature civic liberation project — PUDL, BoulderPublicData/Election-Results, the IPEDS pipeline — converges on this format because:

- Cross-source harmonization is easy: tidy long-form unions trivially.
- Auditing is easy: row counts, NA rates, dtype checks all operate uniformly.
- Documentation is easy: one row per column in the data dictionary, one entry per concept in the crosswalk.

The cost is that tidy long-form is hard to read by eye — analysts pivot to wide form for analysis. The skill resolves this by always shipping `docs/filter-pivot-recipes.md` with the dataset.

## The CUPIDS / public-interest framing

A contemporary thread worth naming: the public-interest data infrastructuring literature (CU Public Interest Data Science Clinic and adjacent work) reframes liberation projects as **infrastructure** in the science-and-technology-studies sense — installed bases of code, data, documentation, and labor that other actors come to depend on. The framework's "installed-base components" map onto this skill as follows:

| Installed-base component | What the liberation project provides |
|---|---|
| **Linkability** | A stable schema and unique identifiers that downstream uses can join against |
| **Interpretability** | The data dictionary and the concept catalog (with caveats) |
| **Continuity** | The CI workflow that refreshes annually; the source registry that survives the original developer leaving |
| **Safe scrutiny** | The reconciliation report and the audit log; immutable originals; visible provenance |
| **Authority** | Documentation of which body originally published the data and under what legal framework (CORA, FOIA, statutory disclosure) |
| **Remedy** | A documented path for downstream users to flag errors and for the project to correct them in a way that preserves the audit trail |

The framework is useful as a checklist: a liberation that supplies tidy data but no documented remedy for errors, or processed data but no provenance, has built infrastructure with missing struts.

## How to use this in a project

When you start a new liberation project:

- **In the README**, cite the relevant lineage. If you're liberating government PDFs, name Sunlight's framing. If it's energy or utility data, point to PUDL. If it's elections, point to Boulder Public Data. The citations are not throat-clearing — they orient downstream users (and AI assistants) to the conventions you've adopted.
- **In AGENTS.md**, name the academic conventions you've followed. "We store data tidy per Wickham 2014; harmonization concepts follow the IPEDS-pipeline / PUDL pattern; reconciliation follows the BoulderPublicData/Election-Results model." This earns interoperability cheaply.
- **In data-dictionary.md**, when documenting a concept that spans sources, *include the caveats*. The IPEDS pipeline's `concepts.py` is the model: every concept entry that crosses sources notes what is and isn't comparable. Renaming variables across sources without caveats is malpractice.
- **In the audit log**, note explicitly what the reconciliation report does and does not catch. If there are known unreconcilable years (legacy formats, mid-period schema changes), document them rather than papering over them.

The skill exists to make this kind of work cheaper to start and harder to do badly. The traditions above — activist and academic — are why the conventions look the way they do.

## Further reading

Activist / movement tradition:
- Tom Lee (Sunlight Foundation), [*PDF Liberation: Why It Matters And How You Can Help*](https://sunlightfoundation.com/2014/01/24/pdf-liberation-why-it-matters-and-how-you-can-help/), 2014
- [PDF Liberation Working Group](https://github.com/pdfliberation) on GitHub
- [catalyst-cooperative/pudl](https://github.com/catalyst-cooperative/pudl) — multi-source ETL reference
- [BoulderPublicData/Election-Results](https://github.com/BoulderPublicData/Election-Results) — modern small-team liberation pattern
- [ProPublica's data-bulletproofing guide](https://github.com/propublica/guides/blob/master/data-bulletproofing.md) — the journalistic standard for vetting a dataset before publishing it

Methodological / academic tradition:
- Wirth & Hipp, *CRISP-DM: Towards a standard process model for data mining*, 2000
- Holstein, Spitzer, Hoell, Vössing, Kühl, *Understanding Data Understanding: A Framework to Navigate the Intricacies of Data Analytics*, ECIS 2024
- Shigarov, *Table understanding: Problem overview*, *WIREs Data Mining and Knowledge Discovery*, 2023
- Kasem et al., *Deep Learning for Table Detection and Structure Recognition: A Survey*, *ACM Computing Surveys*, 2024
- Göbel, Hassan, Oro, Orsi, *A Methodology for Evaluating Algorithms for Table Understanding in PDF Documents*, DocEng 2012
- Long, Wang, Xue, Gao, Yang, Wang, Xia, *Parsing Table Structures in the Wild*, ICCV 2021
- Wickham, *Tidy Data*, *Journal of Statistical Software*, 2014
- Tamir Hassan's [Table Understanding Competition pages](https://tamirhassan.com/html/competition.html) — historical competition datasets and evaluation
- [tanfiona/LLM-on-Tabular-Data-Prediction-Table-Understanding-Data-Generation](https://github.com/tanfiona/LLM-on-Tabular-Data-Prediction-Table-Understanding-Data-Generation) — actively-maintained survey of LLM × table work, with curated benchmark and outlink catalog
