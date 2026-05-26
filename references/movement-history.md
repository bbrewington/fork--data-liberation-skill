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

### Critical perspectives worth absorbing

The lineage above is told from inside the movement. A parallel scholarly literature reads it from outside, and the skill is better when these critiques are kept in view:

- **Civic hacking has a longer history — and a more contested politics — than the open-data era.** Schrock ([2016, *New Media & Society* 18(4): 581–599](https://doi.org/10.1177/1461444816629469)) argues civic hackers are not apolitical "white hats" or Silicon Valley solutionists but **utopian realists** (a term he borrows from Giddens 1990) — "sensitive to social change, capable of creating positive models of society," but realist in their incremental, institutionally-collaborative tactics. Two parts of his argument are load-bearing for this skill:

  *(a)* **A five-part repertoire of data activism**, distilled from interviews and participant observation, that gives a working vocabulary for what any liberation project is *actually doing*:

  | Activity | What it is | Civic-data example |
  |---|---|---|
  | **Requesting** | "Sucking [data] out of its database and exposing it" (p. 591) — extension of FOIA-era informational transparency. Carl Malamud's 1990s mass SEC-EDGAR FOIA campaigns are the prototype. | A scrape of a city portal; a FOIA campaign for jail rosters. |
  | **Digesting** | "A process of interpretation and use that was previously served in an informational fashion by journalists" (p. 592) — Schudson's "monitorial citizens" watching data streams "for injustices." | A crosswalk that names what across-source variables share; a `concept` column that resolves nominal disagreements between sources. |
  | **Contributing** | Adding to shared data resources; "often paired with local grassroots use of mobile devices and amplification of local knowledge" (p. 592). | A tidy dataset republished with a dictionary; a public Datasette deployment with documented refresh cadence. |
  | **Modeling** | "Using code and open data to create working or partly working prototypes" (p. 593) — prototypes as "working evidence to lobby for changing government process." | A budget-explorer app built on a liberated CSV; a Quarto site that demonstrates uses the publisher didn't anticipate. |
  | **Contesting** | "Crowdsourced data or prototypes for not yet existent uses for data… with an oppositional rather than persuasive tone" (p. 593). Post-Ferguson Five-O (rating police interactions) is the canonical case. | An audit that names what's *missing* from the source; a reconcile script that surfaces the publisher's own arithmetic errors. |

  Any specific project mostly does one or two of these, but a healthy liberation practice eventually covers all five — and the README's "movement context" section should explicitly say which ones the project is *for*, not just which one was the immediate motivation.

  *(b)* **A historical arc — publicity → FOIA → open data — in which "openness" steadily lost its accountability mechanism.** Schrock reads four prior regimes:

  | Era | What "openness" meant | What it produced |
  |---|---|---|
  | Early-20th-c. *publicity* (Adams, Brandeis, the muckrakers) | Public-facing disclosure to enable rational choice and curb corruption — "an essential agency for the control of trusts" (Adams 1902) | Antitrust, the Pure Food and Drug Act, the muckrakers' investigative tradition |
  | 1920s *flashlight turn* (Lippmann, Bernays) | Professionalized propaganda — "a narrower and less powerful beam that only illuminated what corporations wanted" (Stoker & Rawlins 2005) | Public relations as discipline; loss of progressives' faith in pure information |
  | *FOIA era* (1946–70s) | A legal right of *individuals* to *request specific records*, with journalists as the interpretive layer | Watergate-era accountability journalism; the Cross 1953 / ASNE "right to know" campaign |
  | *Open-government data* (2007+, Sebastopol + CfA + Obama EOs) | Machine-readable bulk release *by default*, for "speculative reuse" | Open-data portals, civic apps — and, per Aaron Swartz's verdict, the rupture of "the pipeline of leak to investigation to revelation to report to reform" |

  The weakening mechanism: under the FOIA/publicity regime, data flowed through journalists into stories that "changed public opinion." Under open data, release became automatic, ecological, and unattached to a specific public concern — what Yu & Robinson (2012) called "politically neutral public sector disclosures that are easy to reuse, even if they have nothing to do with public accountability." Lessig's complaint about "naked transparency" overestimating citizens' time, and Swartz's about the broken leak-to-reform pipeline, are *internal* dissent from the Sebastopol coalition itself, not external critique. **For this skill, the implication is direct: a project that *only* contributes — ships polished CSVs without naming what's missing, who's affected, what to do about it — reproduces exactly the depoliticization Swartz and Lessig warned about.** The README's movement-context section should commit explicitly to *digesting* and *contesting* (interpretation, narrative, naming gaps), not only *requesting* and *contributing*. The dataset is a shard of a possible future (Wark 2014 / Coleman 2009), not a finished civic outcome.
- **Open-data activism is a *modulation* of open-source culture.** Baack ([2015, *Big Data & Society*](https://doi.org/10.1177/2053951715594634)) uses Kelty's framework from *Two Bits* (2008): open source is "an experimental system made up of five key practices" — sharing source code, defining openness, writing copyright licenses, coordinating collaborations, forming a movement — and movements like Wikipedia or Creative Commons are *modulations* that experiment with one or more of those practices in new domains. Drawing on 10 interviews and 9 documents from the Open Knowledge Foundation Germany, Baack identifies three specific modulations open-data activists perform:

  1. **Raw data as source code.** The open-source practice of sharing source code is modulated into sharing raw data. Summaries and press conferences are like compiled binaries — already interpreted. Activists' working definition: "raw" means *as collected*, not the mythic neutrality Gitelman rightly criticized. The point is *transparency about bias*, not its absence. As Baack quotes one activist, "open data therefore represents a democratization of interpretation or — as they put it — a 'democratization of information'." For this skill, this maps onto the **data dictionary and provenance sidecar**: every dictionary entry, every documented sentinel value, every per-extract `extraction_quality` flag is a small act of breaking interpretive monopoly. Pretending the processed CSV is neutral is the failure mode; documenting the choices that made it is the practice.

  2. **The bazaar model applied to political participation.** Raymond's self-selective, voluntary, decentralized open-source governance is modulated into a model of participatory democracy. Not a demand for direct democracy via referendum, but for "a more open and flexible form of representative democracy" with a "beta culture" inside public institutions willing to experiment and risk failure. Activists explicitly compare this to Barber's *strong democracy* rather than direct democracy. For this skill, this is the framing that justifies the **opt-in CI workflows** (`refresh.yml`, `publish.yml`, `gh-pages.yml`) and the **PR-reviewable refresh diffs**: governance of the data, not just consumption of it, is meant to be open to contributors who self-select rather than gated by official credentials.

  3. **Empowering intermediaries.** Kelty's "forming a movement" component is modulated into a recognition that *raw data alone does not empower citizens* — citizens lack time and expertise — so activists try to *build the intermediary layer* themselves. Baack identifies three criteria for an *empowering intermediary*: **data-driven** (can handle large/complex datasets), **open** (publishes source data alongside stories or apps — Baack's developer interviewee calls withholding sources "a fundamental bug of newspapers"), and **engaging** (cooperative, not one-way broadcast). This is where this skill *itself* mostly lives. The pipeline's audience is not end-readers but other intermediaries — journalists, civic technologists, researchers, NGOs — who will refine the data into civic knowledge. The README's "movement context" section should name those intermediaries explicitly; the Quarto tutorials and filter-pivot recipes are how the project performs the role itself; and the Datasette deployment is *the* engaging-but-data-driven public interface. *Empowering intermediary* should be the project's working self-description.

  Beneath these three modulations, Baack's larger argument is about agency in **datafied publics** — a term he draws from Couldry & Powell's "social analytics" call. The worry: in a world of pervasive datafication, data traces are unconscious and insights stay inside companies and governments, so publics lose agentic purchase on the world being made about them. A liberation pipeline is a small intervention on the *conditions* under which datafication might support rather than undermine public agency — what Kelty calls a *recursive public*, "vitally concerned with the material and practical maintenance and modification of the technical, legal, practical, and conceptual means of [its] own existence as a public."
- **Open data alone reproduces injustice — the case for *information justice*.** Johnson ([2014, *Ethics and Information Technology* 16(4): 263–274](https://doi.org/10.1007/s10676-014-9351-8)) argues that "open data has the quite real potential to exacerbate as much as alleviate injustices" because data is *constructed*, not mirror-of-reality — "a form of communication between actors that embeds the assumptions and worldview of those actors in what is communicated" (following Winner 1980's "inherently political technology" and Young 1990's "each social reality presents its own unrealized possibilities… it does not have to be this way, it could be otherwise"). The orienting maxim he adopts (from Saitta 2012): *"Not only must data sovereignty trump open data, but we need active pro-social countermeasures — a data justice movement."* Three concrete problems of justice the open-data movement has failed to address:

  1. **Social privilege embedded in datasets as constructed.** *"Datized moments"* occur in interactions with bureaucracies, and people differ in their propensity to interact, so privilege enters as over- and under-representation of the already privileged or marginalized. Concrete examples Johnson cites: the *U.S. Census undercount* of Black and Hispanic households (Prewitt 2010); *homelessness measurement* (Williams 2010); *food-desert geography* in Detroit (Zenk et al. 2005) where segregation produces data that ratifies the privileged customer base; *credit redlining* (Cohen-Cole 2011); the *Title-IV "net price calculators"* that hide first-generation students' actual aid figures (Goldrick-Rab 2013); the *Karnataka Bhoomi land-records project* (Raman 2012) whose relational-DB schema excluded Dalit land claims documented only in oral/narrative form. *"Whatever steps are taken to promote fairness in using data that is at its root unjust, the result will almost inevitably be unjust as well. Data is very much a case of 'Injustice in, injustice out.'"*

  2. **Differential capabilities — citizens vs "enterprise" users.** Raw open data must be transformed into "intelligence" through seven complementary layers (Gurstein 2011): internet access, software, skills, interpretation, advocacy, governance. Without them, opening data leads "not to data equality but to *empowering the empowered*." Examples: the Manchester pooled-authority data store that yielded little citizen use beyond a bus timetable; *police as the dominant consumer of open government data* (Archer 2012); the Obama 2012 campaign's data operation; *Bhoomi* developers using RTC records to *drive slum evictions* (Raman 2012). Open data, in practice, is *"dominated by state and business users… 'citizen-open' pales in comparison to what might be called 'enterprise-open' data."*

  3. **Disciplinary normalization — data systems as Foucauldian apparatuses.** Following Foucault, data systems exercise "normalizing judgment" — hierarchical observation that induces self-discipline toward an imposed norm; openness extends the surveillance reach and reifies the norm. Examples: the U.S. Department of Education's *Gainful Employment* regulations; *IPEDS* reporting that normalizes the four-year, residential, full-time, no-prior-college student; *Austin Peay / Arizona State / Rio Salado* "wise choice" advising systems built on behavioral-economics nudges. *"Open data enhances the capacity of disciplinary systems to observe and evaluate institutions' and individuals' conformity to norms that become the core values and assumptions of the institutional system whether or not they reflect the circumstances of those institutions and individuals."*

  Johnson distinguishes *distributive* from *structural* justice (after Kolm 1995 and Young 1990): reducing data harms to "who gets the dataset" misses the structural question of *who got to define the schema, the categories, the units, the norm.* That's where most information injustice lives. The two directions he sketches for an information-justice theory are *(a)* moral-inquiry frameworks (IRB-analog principles, participatory-design mandates, the EU "right to be forgotten") and *(b)* an *active pro-social social movement* building countervailing data structures and capabilities — exemplars are Map Kibera, HarassMap, Online Censorship, and "Truth campaigns" data-literacy efforts.

  **For this skill, the implication is structural, not optional.** Every schema choice in a liberation pipeline — what to datize, what to drop, which entity is the primary key, which records to reconcile against which authoritative total — is a values-laden decision with winners and losers. AGENTS.md's design-decisions section should record those choices as such, and require an explicit *"who is over- or under-represented in this source?"* entry per vintage. The data dictionary's caveat sections should carry a *provenance-and-power note* per variable: how the upstream agency constructed the category, which populations are systematically missing or miscounted, what disciplinary norm the field implicitly enforces (the IPEDS / *Bhoomi* lesson). The README's movement-context section should locate the dataset within the data-sovereignty / data-justice tradition — naming the affected community, pointing to countervailing community-led efforts where they exist, and *stating uses the maintainers consider out-of-scope* (e.g., enrichment for enforcement, predictive policing, eviction targeting) so the artifact ships paired with the pro-social countermeasures Johnson argues openness alone cannot provide.
- **Critiques from outside the movement are also worth naming.** Morozov ([2013](https://en.wikipedia.org/wiki/Evgeny_Morozov)) calls civic hacking "an apolitical category imposed by ideologies of 'scientism'"; Slee ([2012](https://www.aaronsw.com/weblog/openpolitics)) describes the open-data movement as "co-opted and neoliberalist." These are not internal-to-the-movement debates; they argue the *category* is wrong. Acknowledging them honestly in AGENTS.md design-decisions is the cost of intellectual seriousness.
- **"Data culture" inside an institution is a *contested field of meanings*, not a deficit to be filled.** Casemajor ([2025, *Big Data & Society* 12(3): 1–14](https://doi.org/10.1177/20539517251381671)), studying the National Library and Archives of Quebec (BAnQ) over 2020–2023 with 15 BAnQ staff interviews and a corpus of strategy and governance documents, reframes the standard industry diagnosis. The article opens with a BAnQ data-governance committee member's complaint that there was "no data culture" within the institution — even though it manages hundreds of millions of records of metadata, transactional, usage, and heritage data. Casemajor's pivot: this isn't a deficit (insufficient data literacy, no strategy, poor interoperability) but a **surplus** — "the multitude of practices that fall under the broad umbrella of 'data culture.' This surplus complicates efforts to establish a coherent and unifying meaning for data culture within the institution." Her definition of *data culture*, adopted as the article's framework:

  > Data culture is shaped by an interrelated set of collective repertoires of practices and frames of meaning, grounded in specific contexts and characterized by a particular sensibility and rationality constructed around data sets. These practices and interpretive frameworks influence the shaping of data, their status, and their effects on the world. They are informed by values, norms (both explicit and implicit), literacies, affects, and technical infrastructures.

  Following Foucault, she treats data apparatuses as "heterogeneous ensembles of discourses, practices, institutions, and technologies that establish particular regimes of visibility, legibility, and value" — meanings "coexist, compete and are mobilized in contextually specific ways—always open to contestation and re-interpretation." Following Ruppert and Scheel (2021), *data practices* are "intertwined human and material agency, situated in specific knowledge regimes and 'performed by actors […] in competitive struggles over authority, influence, and resources within specific fields of practice.'" Not neutral routines: stakes in an internal political economy.

  Casemajor identifies the **action logics** that collide inside BAnQ (the same patterns recur in any merged or multi-function institution):

  | Action logic | What it prioritizes | Standards / tools |
  |---|---|---|
  | **Heritage preservation / archival stewardship** (national archives) | Long-term documentary integrity; conservative on exploitation of usage data | ISAD(G) |
  | **Library cataloging / public reference** (national library) | Bibliographic normalization, high-quality reference data, public access | MARC |
  | **Public library service** (Grand Library) | Document loans, subscriber services, patron interaction | Independent loan system |
  | **Digital experience / communications / marketing** | Personalization, audience profiling, discoverability | Power BI dashboards, recommendation engines |
  | **Legal service** | Compliance; protection of personal information | Quebec privacy regime |
  | **Management / executive** | Data-led innovation; "knock down the walls between the organization's units and services" | Datamart, KPIs, ERP/BI |
  | **Open-data / public-service democratization** | Free release under open license | Données Québec |
  | **Generative-AI / monetization** | Heritage data as LLM training corpus | "Default openness… overridden in favor of a commercial agreement with a third party, provided there is 'serious and documented justification'" |

  Three pressures push the institution toward a thinner, more centralized data culture: **datafication** ("the process by which ever-wider aspects of personal and social life… are transformed into digital data that automated systems can exploit"); **discoverability** (a Quebec cultural-policy mandate to rank, recommend, and surface Francophone content); and **platformization** — though Casemajor is sharply skeptical of the last: "this approach may be better described as a *platformization fantasy* superimposed on a system of governmental data centralization." The CEO's quote captures the tool-ideology fusion: *"From now on, project production is based on the use of dashboards, and targets are set for each of them."*

  Concrete tensions worth borrowing as anticipations: **heritage vs AI-training data** (digitized manuscripts in demand as LLM corpora, with the "default openness… overridden" clause as the live edge case); **personalization vs democratization** ("we don't want the recommendations to be too personalized" — staff explicitly named Amazon as the anti-model, viewing recommendation as limiting cultural diversity); **platformization-centralization vs professional stewardship** (the CEO's "knock down the walls" goal balanced against the warning that "eroding the social boundaries and practices that foster a sense of belonging within organizational units can profoundly alter shared work experiences"); and the standing concern about *state surveillance* in mandatory data transfers to governing bodies. Casemajor's bottom line: *"Instead of being resolved, the tensions at the BAnQ appear to be constitutive of data culture itself, reflecting a dynamic and continuous state of negotiation rather than a stable consensus."*

  **For this skill, the implications are concrete.** A liberation project deployed *inside* an institution will hit exactly these dynamics — the data never arrives pre-pacified. Three places the framework should land:

  - **AGENTS.md should name the surplus problem explicitly.** State up front that "data culture" inside the partner institution is a contested field, not a deficit, and that the project's job is to make the competing logics *legible* (provenance, lineage, intended use) rather than to flatten them into one "true" schema.
  - **The data dictionary cannot assume single canonical definitions** of fields that mean different things to archivists, librarians, marketing/digital-experience staff, legal, and management. Contested terms ("user," "usage," "record," "item," "collection," "performance") deserve a *who-uses-this-and-how* note and, where definitions diverge, each variant as a first-class crosswalk row rather than silently picking a winner.
  - **Anticipate review-comment patterns from different functional teams** — not because anyone is wrong but because action logics genuinely diverge. Build governance norms (a documented escalation path, a "minority report" field in the dictionary) so disagreements are *logged and traced* rather than suppressed. The institution Casemajor studied couldn't resolve these tensions; expecting any liberation project to is a category error.

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
