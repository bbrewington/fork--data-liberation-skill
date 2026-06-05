# Open Data Standards: Background, Not a Constraint

This reference is **background context**, not a checklist that gates the workflow. The skill's
six-phase pipeline (Survey → Scaffold → Extract → Tidy → Audit → Publish) already *practices*
most of what the official open-data standards prescribe — it just doesn't usually *name* them.
The purpose of this file is twofold: to let an agent **recognize and name** the standard a given
artifact already informally implements (so it can cite it in the README or `AGENTS.md`), and to
sketch the **optional** path to deeper conformance when a downstream consumer actually needs it.

Read it the way you'd read [`movement-history.md`](movement-history.md): once, to share the
framing. Then forget it until a project gives you a concrete reason to reach for a specific
standard. **Conformance is never a precondition for shipping a liberated dataset.** A tidy CSV
with a data dictionary and a provenance trail is already doing the work these standards exist to
encourage; the standards are a vocabulary for *talking about* that work and a menu for extending
it, not a gate in front of it.

A note on framing: the skill's [movement history](movement-history.md) tells the open-data story
from the **activist** side (PDF Liberation, MuckRock, PUDL — getting public data *out*). This
reference tells the complementary **standards / policy** side (how institutions agree to publish
it *well*). They are the same struggle from two directions; a skilled liberator draws on both.

## Why this reference exists

Three things are true at once, and holding all three is the point:

1. **The skill already embodies these standards.** `provenance.csv` is a hand-rolled W3C **PROV**
   record; `metadata.yaml` is a **DCAT**-shaped catalog entry; the five-dimension quality
   framework parallels the W3C **Data Quality Vocabulary**; the immutable-originals /
   non-discrimination / permanence conventions track the **Sunlight** policy principles. Naming
   them earns interoperability cheaply and tells downstream users which conventions the project
   adopted.
2. **None of them is a requirement the skill imposes.** Civic liberation work is constrained by
   the source, the FOIA timeline, and a 1–3 person team. A standard that would block shipping is
   worse than no standard. Every item below is *optional deepening*, reached for only when a real
   consumer benefits.
3. **Knowing the landscape prevents reinvention.** When a domain already has a standard (a
   research repository's required metadata, an agency's NIEM exchange schema, a journal's deposit
   policy), reusing it beats inventing a parallel scheme. The registries below (FAIRsharing,
   re3data) exist precisely so you can *look first*.

## Standards profiled by theme

The nine sources organize cleanly along five recurring themes — **history** (when/why it
emerged), **precedents** (what it built on), **standards organization** (who governs it),
**institutions** (who adopts/runs it), and **infrastructure** (the concrete tooling/registries it
ships). The matrix is the at-a-glance comparison; the per-source notes below add nuance where a
cell needs it.

| Framework | History | Precedents | Standards org | Institutions | Infrastructure |
|---|---|---|---|---|---|
| **Sunlight Open Data Policy Guidelines** | Drafted 2007–2014, maintained as a static archive after Sunlight wound down its open-gov work (~2020) | The 8 Principles of Open Government Data (2007 Sebastopol meeting); FOIA tradition | Sunlight Foundation (archived); mirrored by **US Ignite** for continuity | Municipal & state open-data programs; civic-tech advocates | A policy framework: 10 principles + 32 model provisions in 3 categories |
| **DCAT-US** | Began as Project Open Data Metadata Schema under OMB **M-13-13** (2013); v3 modernizes it on the Evidence Act | W3C **DCAT** ← Dublin Core; Project Open Data | US Federal **CDO Council** + **FCSM**, profiling W3C DCAT | Federal agencies; many state/local govs | `data.gov` catalog + validator; JSON-LD / RDF serializations |
| **W3C DCAT & the Data Activity vocabularies** | DCAT a W3C Recommendation 2014 (v2 2020, v3 2024); PROV-O 2013; DQV 2016 | Semantic Web / Linked Data; RDF | **W3C** (Government Linked Data WG; Data Activity) | National data portals worldwide; CKAN/Socrata ecosystems | RDF vocabularies: DCAT, **PROV-O**, **DQV**, Org, RDF Data Cube |
| **W3C Data on the Web Best Practices (DWBP)** | WG chartered 2013; Recommendation 2017 | DCAT, PROV, the FAIR conversation | **W3C** Data on the Web Best Practices WG | Data publishers broadly (gov + research + commercial) | 35 best practices + a use-cases/requirements companion doc |
| **FAIR principles** | Articulated 2016 (Wilkinson et al., *Sci. Data*) | Earlier data-stewardship & e-science norms | **Force11** community; stewarded via RDA et al. | Funders, journals, repositories across the sciences | 15 guiding principles (Findable / Accessible / Interoperable / Reusable) |
| **FAIRsharing** | Grew from BioSharing (~2011) into cross-domain registry | The FAIR principles; community standards curation | **Research Data Alliance**–affiliated; community-curated | Journals, funders, repositories, researchers | A registry interlinking **standards ↔ databases ↔ policies**, with an API |
| **re3data** | Launched 2012 (DFG-funded) | Library/repository cataloging traditions | **KIT** + **Purdue University Libraries** (orig. w/ Helmholtz, HU Berlin) | Research libraries, funders, publishers | A registry of 3,000+ research-data repositories + metadata schema + API |
| **NIEM** | Began 2005 from DOJ/DHS **GJXDM** (justice-XML); now **NIEMOpen** | GJXDM; W3C XML Schema | **OASIS** Open Project (NIEMOpen); orig. DOJ/DHS/HHS | Justice, emergency-response, health, child-welfare agencies | Reference + extension XML schemas; Naming & Design Rules (NDR); IEPDs |

A few cells reward expansion:

- **Sunlight Open Data Policy Guidelines** — the *policy* counterpart to the skill's *activist*
  lineage. Its **ten principles** (completeness, primacy, timeliness, ease of physical and
  electronic access, machine readability, non-discrimination, use of commonly-owned standards,
  licensing, permanence, low/no usage costs) and **32 model provisions** ("what data should be
  public," "how to make data public," "how to implement policy") read as the publisher-side
  obligations whose absence is *why liberation work exists*. The skill already honors several
  (immutable originals → permanence; tidy machine-readable CSVs → machine readability; CC-BY
  defaults → licensing). US Ignite hosts a maintained mirror after Sunlight's wind-down.
- **DCAT-US** — the mandatory metadata standard behind `data.gov`. Its data model is a three-tier
  hierarchy — **Catalog → Dataset → Distribution** — with v3 adding **DataService** (APIs) and
  **DatasetSeries** (versioned/recurring releases). This is almost exactly the shape of the
  skill's published artifacts: a project is a *catalog*, the processed CSV is a *dataset*, and the
  CSV / SQLite / Datasette API are its *distributions*.
- **W3C Data Activity vocabularies** — beyond DCAT, the W3C stack includes **PROV-O** (provenance:
  Entity / Activity / Agent), **DQV** (data quality), the **Organization ontology**, and the
  **RDF Data Cube** (multidimensional statistics). The skill informally uses the first two; the
  Data Cube is occasionally relevant for statistical sources but rarely worth the RDF overhead in
  civic work.
- **DWBP** — 35 best practices spanning metadata, licenses, provenance, quality, versioning,
  identifiers, formats, vocabularies, access/APIs, and republication. It is the single best
  "did we miss anything?" checklist, and it aligns one-to-one with FAIR. Treat it as a *review
  lens*, not a gate.
- **NIEM** — the heaviest standard here and the one to reach for *least* often. It earns its keep
  only when the project exchanges data with an agency that mandates a NIEM **IEPD** (Information
  Exchange Package Documentation). Its reusable-component philosophy rhymes with the skill's
  concept catalog, but its XML-schema machinery is overkill for a tidy CSV.

## A meta-synthesis: four lenses on open data

Synthesized rather than listed, the nine sources resolve into four perspectives. A complete
liberation project touches all four — and, reassuringly, the skill's existing artifacts already
land in each.

**1. Policy / governance — *should* this be open, and on what terms?**
Sunlight's guidelines (and the US Ignite mirror) are the canonical statement. The questions they
pose — completeness, timeliness, non-discrimination, licensing, permanence, cost — are the same
ones the skill's [governance section](project-template.md#governance) makes a project answer in
its README and `AGENTS.md`. The lens is *normative*: it's about obligations, not file formats.

**2. Cataloging / metadata interoperability — can a machine *find and understand* it?**
DCAT-US, W3C DCAT, and the W3C *Publishing Open Government Data* note answer this with a shared
vocabulary (Catalog / Dataset / Distribution / DataService). The skill's `metadata.yaml` and
hand-maintained data dictionary are this lens in miniature; emitting a DCAT record is the optional
step that makes the dataset show up in a federated catalog.

**3. Discipline / domain standards & registries — has someone *already solved* this?**
FAIRsharing (standards ↔ databases ↔ policies), re3data (repositories), and NIEM (agency
exchange) are where you look *before* inventing. This lens maps onto the skill's **Survey** phase:
cataloguing prior work and existing standards is exactly the "ask before assuming" discipline the
workflow already prescribes. Most civic projects consult these, find nothing binding, and proceed
— but the five-minute check is worth it.

**4. Web best practice + FAIR — is it *good* open data, by a published yardstick?**
DWBP's 35 practices and the four FAIR principles are the connective tissue across the other three
lenses. They're the most useful as a *review* pass near Publish: a quick self-check against
Findable / Accessible / Interoperable / Reusable (or the DWBP practice list) catches the gap —
a missing license, an unstable identifier, undocumented provenance — without imposing a process.

## Crosswalk: standards ↔ what the skill already builds

The actionable core. Each row names a standard, the **existing** skill artifact that already
embodies it (no new work), and an **optional** deepening step to reach for only when a consumer
benefits. The "already in the skill" column is the load-bearing one — it's what lets you *cite*
the standard honestly today.

| Standard / vocabulary | Already in the skill | Optional deepening (only if a consumer needs it) |
|---|---|---|
| **DCAT-US v3 / W3C DCAT** (Catalog → Dataset → Distribution) | `data/processed/metadata.yaml`, `docs/data-dictionary.md`, Datasette's per-table/column metadata ([`toolchain-datasette.md`](toolchain-datasette.md#metadata-the-documentation-surface-that-travels-with-the-data)) | Emit a `dcat-us.jsonld` catalog record alongside `metadata.yaml` so the dataset federates into `data.gov`-style catalogs |
| **W3C PROV-O** (Entity / Activity / Agent) | `data/processed/provenance.csv`, the per-extract sidecar ([`data-modeling.md`](data-modeling.md#provenance)) | Map the sidecar columns to PROV terms (`source_url`→Entity, `parser_module`→Activity, the project→Agent); serialize to PROV-JSON only if a downstream graph consumes it |
| **W3C DQV + DWBP quality BPs** | The five-dimension quality framework + `audit.py` + `reconcile.py` ([`data-modeling.md`](data-modeling.md#data-quality)) | Tag audit metrics with DQV dimension URIs; expose them in `metadata.yaml` |
| **FAIR principles** | Tidy long-form, stable composite keys, the data dictionary, the provenance trail | Run a four-line FAIR self-check (Findable/Accessible/Interoperable/Reusable) before Publish and record gaps in `AGENTS.md` |
| **DWBP** (35 best practices) | The whole workflow — metadata, licensing, provenance, versioning, identifiers, access all have a home | Use the DWBP list as a one-time "did we miss anything?" review near Publish |
| **Sunlight 10 principles / 32 provisions** | Immutable originals (permanence), tidy CSVs (machine readability), CC-BY defaults (licensing), open repos (non-discrimination, low cost) ([`project-template.md`](project-template.md#governance)) | Self-assess the published dataset against the 10 principles; note any the source itself violates as a *finding* |
| **FAIRsharing / re3data** | The Survey-phase "search and catalog" discipline + README lineage citations | Consult the registries during Survey to find a domain standard to reuse or a repository to deposit a copy in |
| **NIEM** (reusable components, IEPDs) | Per-source parsers + the concept catalog (reusable cross-source equivalences) ([`data-modeling.md`](data-modeling.md#concept-catalogs)) | Only when an agency partner mandates a NIEM exchange — map the canonical schema to the required IEPD |

## How to use this responsibly

A short discipline, consistent with the skill's existing caveat-writing ethos:

- **Cite, don't conform for its own sake.** When an artifact already matches a standard, name the
  standard in the README or `AGENTS.md` ("provenance follows W3C PROV; metadata is DCAT-shaped").
  That's the cheap, high-value move. Don't restructure a working pipeline to chase a badge.
- **Look before you invent.** In Survey, spend five minutes in FAIRsharing / re3data and on the
  publisher's own metadata. If a domain standard exists, reuse it; if not, proceed without guilt.
- **Never let conformance block shipping.** A liberated dataset that exists beats a perfectly
  DCAT-conformant one that doesn't. If a standard would delay publication, defer it to an issue.
- **Record what you *didn't* adopt, and why.** Consistent with the skill's "concepts carry
  caveats" principle: a one-line note in `AGENTS.md` ("we did not emit DCAT-US JSON-LD — no
  federated-catalog consumer yet") is more honest and more useful than silent omission.
- **Let the standard catch the source's failures.** The Sunlight principles and DWBP are also a
  lens on the *publisher*: a source that fails "permanence" (dead links) or "machine readability"
  (scanned PDFs) is generating a *finding* worth recording, not just an inconvenience.

## Source map

The nine authoritative sources, one line each, so an agent can fetch the primary document on
demand rather than relying on this distillation:

- **Sunlight Open Data Policy Guidelines** — <https://opendatapolicyhub.sunlightfoundation.com/guidelines/> — the 10 principles + 32 model provisions for government open-data policy (archived).
- **US Ignite mirror of the Sunlight guidelines** — <https://www.us-ignite.org/tools/data-standards-and-policies/open-data-policy-guidelines-sunlight/> — maintained continuity copy of the same framework.
- **DCAT-US** — <https://resources.data.gov/standards/catalog/dcat-us/> — the US federal metadata profile (Catalog → Dataset → Distribution; DataService, DatasetSeries) behind `data.gov`.
- **FAIRsharing** — <https://www.fairsharing.org/> — curated registry interlinking standards, databases/repositories, and data policies across disciplines.
- **NIEM** — <https://www.niem.gov/> — the National Information Exchange Model: XML-schema framework + Naming & Design Rules for cross-agency data exchange.
- **re3data** — <https://www.re3data.org/> — the Registry of Research Data Repositories (3,000+ repositories, metadata schema, API).
- **W3C Data on the Web Best Practices — use cases** — <https://w3c.github.io/dwbp/usecasesv1.html> — the use cases and requirements grounding the 35 DWBP best practices.
- **W3C *Publishing Open Government Data*** — <https://www.w3.org/TR/gov-data/> — the W3C note on publishing government data as Linked Open Data (introduces DCAT in a gov context).
- **W3C Data Activity hub** — <https://www.w3.org/2013/data/> — the coordination point for DCAT, PROV-O, DQV, Org, and RDF Data Cube.

## Further reading within this skill

- [`movement-history.md`](movement-history.md) — the *activist* counterpart to this *standards* view; the Sunlight lineage as activism, plus the critical perspectives (information justice) that keep "open" from being mistaken for "just."
- [`data-modeling.md`](data-modeling.md) — where provenance (PROV), metadata (DCAT), concept catalogs (NIEM-adjacent), and the quality dimensions (DQV) actually live in code.
- [`project-template.md`](project-template.md#governance) — the governance checklist that operationalizes the Sunlight policy questions.
- [`discovery-and-audit.md`](discovery-and-audit.md) — the bulletproofing checklist and audit/reconcile loop that parallel DWBP's quality and provenance practices.
- [`toolchain-datasette.md`](toolchain-datasette.md#metadata-the-documentation-surface-that-travels-with-the-data) — `metadata.yaml`, the DCAT-shaped catalog surface that travels with the data.
