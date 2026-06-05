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

Sunlight also produced the *policy* counterpart to this activist history: the [Open Data Policy Guidelines](https://opendatapolicyhub.sunlightfoundation.com/guidelines/) (10 principles, 32 model provisions) that describe what publishers *should* do — the obligations whose absence makes liberation necessary. That standards-and-policy view, alongside DCAT-US, the W3C vocabularies, FAIR, and the research-data registries, lives in [`open-data-standards.md`](open-data-standards.md) as background context for naming and optionally deepening what a project already does.

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

### Critical perspectives worth absorbing

The lineage above is told from inside the movement. Four claims from outside change how the artifacts get built:

**The skill's working self-description: *empowering intermediary*** (Baack 2015, *Big Data & Society*). Open-data activists modulate three open-source practices into the data domain:

1. *Raw data as source code* — sharing the underlying records, not just summaries, breaks the publisher's interpretive monopoly. Implication: the **data dictionary and per-extract provenance** are the load-bearing artifacts; every documented sentinel value, every `extraction_quality` flag is a small act of that breaking. "Raw" means *as collected*, not mythically neutral — the dictionary's job is transparency about the choices, not their denial.
2. *Bazaar model applied to political participation* — self-selective contribution to *governance* of data, not just *consumption* of it. Implication: the **PR-reviewable refresh diffs** and opt-in workflows are how the project performs this — contributors who notice an issue can fix it without going through official channels.
3. *Empowering intermediaries* — raw data alone doesn't empower citizens; the project must build the intermediary layer. Baack's three criteria for an empowering intermediary are *data-driven* (handles real datasets), *open* (publishes sources alongside conclusions), and *engaging* (cooperative, not broadcast). **Empowering intermediary** is the right working self-description for a civic-data project; the README's *movement context* section should name the downstream intermediaries (journalists, researchers, NGOs, advocates) the project is for, not the end-readers.

**A vocabulary for what any specific project is doing** (Schrock 2016, *New Media & Society*). Civic-data work has five distinct modes; a healthy project does several:

| Mode | What it is | Project example |
|---|---|---|
| **Request** | Extract data from where it's locked | Scrape a portal; file FOIA/CORA |
| **Digest** | Interpret and make legible | Concept catalog, dictionary, crosswalks |
| **Contribute** | Add to the shared corpus | Publish a tidy CSV with provenance |
| **Model** | Build a prototype that demonstrates use | A Quarto explainer, a Datasette canned query |
| **Contest** | Name what's missing or wrong | An audit that calls out the publisher's gaps; reconcile failures published |

The skill's six-phase workflow naturally covers *Request* (discover/fetch) and *Contribute* (clean/publish). It's harder to make sure a project also *Digests*, *Models*, and *Contests* — those need explicit space in the README and the Quarto site, or the project ships a dataset without the politics that justify the work. Schrock's argument: machine-readable release without interpretation reproduces "naked transparency" (Lessig), which is not accountability.

**Three problems open data alone doesn't solve** (Johnson 2014, *Ethics and Information Technology*; building on Saitta's "data sovereignty must trump open data"). The skill encodes these as caveat-writing requirements, not as warnings to skip:

1. **Embedded privilege.** Datasets carry social privilege from the moment they're constructed (Census undercount; *Bhoomi* land records excluding Dalit claims documented only orally; net-price calculators that mislead first-generation students). The data dictionary's caveat section should answer per variable: *who is over- or under-represented in this source, and why?*
2. **Differential capabilities.** Open data is "dominated by state and business users… 'citizen-open' pales in comparison to 'enterprise-open'." The Quarto tutorials and filter-pivot recipes exist to flatten this asymmetry; without them, the project just supplies new feedstock for police and ad-tech. AGENTS.md should name uses that are *out of scope* (e.g., enrichment for enforcement, predictive policing, eviction targeting).
3. **Disciplinary normalization.** Data systems impose norms via their function — IPEDS reifies the four-year residential full-time student; *Gainful Employment* metrics discipline institutions toward a particular outcome shape. When the project's schema mirrors the publisher's, it inherits the publisher's disciplinary structure. Naming that explicitly in `AGENTS.md` design-decisions is the floor.

**Data culture inside any institution is plural and contested, not coherent** (Casemajor 2025, *Big Data & Society*). The "build a data culture" framing is mistaken not because there is *too little* data work but because there's *too much* — archivists, librarians, marketers, legal, executives, and open-data advocates all use the word "data" with different action logics and incompatible standards (MARC vs ISAD(G), heritage vs AI-training, KPI dashboards vs professional craft). A liberation project deployed inside such an institution shouldn't try to resolve those tensions; **`AGENTS.md` should name the surplus problem explicitly**, the **data dictionary should let contested terms have multiple definitions** (one row per stakeholder reading), and the project should expect contributors from different functional areas to disagree — not as a failure of governance but as the substrate.

## Academic framing

The skill's scoping decisions trace to three durable ideas from the methodology literature. Each one is operational, not theoretical — they're named here so the skill's commitments are auditable.

**CRISP-DM and what this skill targets.** The Cross-Industry Standard Process for Data Mining (Wirth & Hipp 2000) divides a data project into six phases: business understanding, data understanding, data preparation, modeling, evaluation, deployment. This skill targets **data understanding, preparation, and deployment** and deliberately stops short of modeling — the rest belongs to the analyst after liberation is done. The CRISP-DM framing also names the under-specified phase: *data understanding*. Holstein et al.'s (2024) five-dimension expansion of it (Foundations / Collection & Selection / Contextualization & Integration / Exploration & Discovery / Insights) maps roughly onto the skill's artifacts — Survey notes ≈ Insights; data dictionary ≈ Foundations; concept catalog ≈ Contextualization; `audit.py` output ≈ Exploration. The point isn't the taxonomy; it's that the artifacts answer the questions the phase poses.

### Table Understanding (TU)

A useful vocabulary when surveying a new source. The document-analysis community decomposes the table problem into two subproblems and seven tasks (Shigarov 2023):

```
Table Understanding (TU)
├── Table Extraction (TE)
│   ├── Table Detection (TD)              <- find table regions
│   ├── Table Structure Recognition (TSR) <- recover rows, columns, cells
│   ├── Table Functional Analysis (TFA)   <- header vs data; cell roles
│   └── Table Structural Analysis (TSA)   <- relationships between cells
└── Table Interpretation (TI)
    ├── Table Canonicalization (TC)       <- to relational form
    ├── Table Normalization (TN)          <- to 3NF; entity resolution
    └── Semantic Table Interpretation (STI) <- match to a knowledge graph
```

A liberation project touches all of TE plus the canonicalization and normalization halves of TI. Semantic interpretation (matching to Wikidata/DBpedia) is a research frontier rarely worth the cost in civic work — the concept catalog with caveats handles cross-source entity resolution at a sufficient level.

**Use rule-based / heuristic tools first** (pdfplumber, camelot). Deep-learning table extractors (TableFormer, CascadeTabNet, GTE) are impressive on average but rarely worth the operational cost for civic data — per-document craft remains more reliable, and the output is auditable. Reach for ML extractors only when classical methods genuinely fail, and prefer open-source extractors with reproducible behavior over closed LLM-based parsers. The audit that matters is *top-line reconciliation against the source's own published total*, not benchmark scores. Benchmark corpora (PubTabNet, FinTabNet, SciTSR, ICDAR) are useful as *fixtures* for parser tests but not as targets to optimize against.

**Tidy data.** Wickham's "Tidy Data" (2014) anchors the canonical storage shape: one row per observation, one column per variable, one cell per value. Every mature civic project converges on this because unions, audits, and dictionaries all become uniform operations. The trade — tidy long-form is awkward to read by eye — is bridged by shipping `docs/filter-pivot-recipes.md` with the dataset. See [`data-modeling.md#wickham-tidy-as-the-storage-shape`](data-modeling.md#wickham-tidy-as-the-storage-shape) for the operational form.

## Liberation as infrastructure

A useful checklist framing: a liberation project is *installed infrastructure* that other actors will depend on. Six components a complete project covers:

| Component | What the project provides |
|---|---|
| **Linkability** | Stable schema + unique identifiers downstream uses can join against |
| **Interpretability** | Data dictionary + concept catalog (with caveats) |
| **Continuity** | CI refresh workflow that survives the original developer leaving |
| **Safe scrutiny** | Reconciliation report; audit log; immutable originals; visible provenance |
| **Authority** | Documented legal framework — CORA / FOIA / statutory disclosure |
| **Remedy** | A path for downstream users to flag errors and for the project to correct them with the audit trail preserved |

A project that supplies tidy data but no documented remedy, or processed data but no provenance, has built infrastructure with missing struts.

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

Consumer-side practice (what happens *after* a liberation ships — adjacent to this skill, not within it):
- [NYT data-training](https://github.com/nytimes/data-training) — the *New York Times*' newsroom training materials for data journalists. Covers brainstorming story angles from a dataset, the verification practices reporters apply to avoid misreading data, and editorial review of data stories. Spreadsheet-first by audience (Google Sheets, not pandas), but the *methodological* content is what a complete liberation hands off to: a project that ships a tidy CSV and a data dictionary has done half the work; these materials describe the other half. Point downstream consumers here from the project's README rather than reinventing the consumer-side methodology in the pipeline's docs.

Critical / scholarly tradition (the movement read from outside):
- Schrock, *Civic hacking as data activism and advocacy: A history from publicity to open government data*, *New Media & Society*, 2016 — civic hacking's pre-2010 history
- Baack, *Datafication and empowerment: How the open data movement re-articulates notions of democracy, participation, and journalism*, *Big Data & Society*, 2015 — open-source modulation framework
- Johnson, *From open data to information justice*, *Ethics and Information Technology*, 2014 — the case that open data alone reproduces injustice
- Casemajor, *Data cultures: Contested meanings in a public cultural institution*, *Big Data & Society*, 2025 — data culture as plural and contested inside an institution

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
