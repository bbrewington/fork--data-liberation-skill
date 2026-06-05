# Open Government Landscape: Transparency, Civic Tech, Policy, and Global Initiatives

Background context, **not a constraint** on the workflow — the same register as [`open-data-standards.md`](open-data-standards.md). Where that file covers the *technical* standards the skill's artifacts implement (DCAT, PROV, DQV, FAIR), this one zooms out to the *civic and institutional* landscape around them: how governments are *obliged* to publish (transparency law and open-data policy), who *consumes* liberated data (the civic-tech ecosystem), and how the work connects to *international* open-government efforts. It complements [`movement-history.md`](movement-history.md) — that file tells the activist lineage; this one maps the surrounding institutions, laws, and resources.

Read it once for orientation, then reach for the resource catalog at the end when a project needs a portal, a law, a request channel, or a downstream outlet. Nothing here gates shipping a tidy CSV; it's a map of the territory the dataset lands in.

> **Source-quality note.** This reference was prompted by a synthesis of the *Open Government Platform* knowledge base (`opengovtplatform.org`), whose pages could not be fetched directly (HTTP 403) and were reconstructed via web search — so its site-specific particulars are approximate and some article URLs may not be stable. Everything below is therefore anchored on **independently verifiable primary resources** (data.gov, FOIA.gov, OGP, OKFN/CKAN, the World Bank toolkit, the Open Data Charter, etc.), not on that site's specific claims. Treat the figures as indicative and verify against the linked primaries before citing them.

## The five themes, synthesized

The knowledge base organizes open government into five themes. Each maps onto something the skill already does — or marks a boundary the skill deliberately doesn't cross.

### 1. Open data — the publishing layer

Open data is public-sector information released in standardized, machine-readable, openly-licensed form. The durable touchstones: the **8 Principles of Open Government Data** (Sebastopol, 2007 — the ancestor of Sunlight's 10), the **3-star minimum** (CSV/JSON/XML before you've earned a star for openness), and the federal lineage from `data.gov` (launched 2009) through the metadata standard now known as **DCAT-US**. Government **APIs** (`api.data.gov`, the Census and USAspending APIs) are the machine-to-machine face of the same idea.

*How the skill relates:* this is the skill's home turf — see [`open-data-standards.md`](open-data-standards.md) for the standards and the artifact crosswalk. The gap the knowledge base surfaces is **institutional publishing**: the skill builds a Datasette + Quarto + LFS bundle, but says little about federating *back* into a `data.gov`/CKAN/Socrata portal. See [the portal-federation note](#institutional-publishing-the-portal-layer) below and the DCAT-export pointer added to [`toolchain-datasette.md`](toolchain-datasette.md).

### 2. Government transparency — the obligation layer

Transparency is the *why* beneath much liberation work: FOIA (the federal **Freedom of Information Act**, 1966, 5 U.S.C. § 552), state **sunshine / open-records laws**, spending disclosure (**USAspending.gov**, Treasury Fiscal Data, mandated by the **DATA Act** of 2014), and **whistleblower** protections. The knowledge base treats FOIA as a *process* — drafting a request, the ~20-business-day clock, fee categories (commercial vs. news-media/educational vs. other), appeals, and redaction disputes — not just as a source of PDFs.

*How the skill relates:* the skill names FOIA/MuckRock/CORA as *source paths* but is thin on FOIA *procedure* and on transparency *politics* (when a redaction is excessive; what the project will *refuse* to liberate). A short FOIA-as-process + scope note now lives in [`discovery-and-audit.md`](discovery-and-audit.md) under the Survey-phase checks.

### 3. Civic technology — the consumer/intermediary layer

Civic tech is the ecosystem of tools that put government data in front of people: reporting tools (**SeeClickFix**, 311), legislative trackers (**GovTrack**, **Councilmatic**, **OpenStates** / Open Civic Data), accountability databases (**OpenSecrets**, **Follow the Money**), and the investigative-journalism layer (**ProPublica**). Civic **hackathons** (the lineage from "Apps for Democracy," DC 2008) are how open data gets turned into demonstrations of use.

*How the skill relates:* the skill already frames its output as feedstock for "empowering intermediaries" (Baack) and names Schrock's five activities (Request / Digest / Contribute / Model / Contest) — see [`movement-history.md`](movement-history.md#critical-perspectives-worth-absorbing). What it underplays is the *operational hookup*: which export shapes (bulk CSV vs. API vs. DCAT-cataloged) suit which downstream tool, and how to *find and recruit* the journalists/NGOs a dataset is for rather than hoping they discover it. This stays largely a documentation concern (the README's *movement context* section), not a pipeline change.

### 4. Policy & legislation — the mandate layer

The legal scaffolding that makes open data *owed*, not merely nice:

- **FOIA** (1966) and state **sunshine laws** — the request-driven floor.
- **OMB M-13-13** ("Open Data Policy — Managing Information as an Asset," 2013) and **Project Open Data** — the origin of the federal metadata schema that became **DCAT-US**.
- The **OPEN Government Data Act** (Title II of the **Foundations for Evidence-Based Policymaking Act**, 2019) — makes "open by default" and machine-readable inventories a *statutory* duty for federal agencies, and stands up agency **Chief Data Officers**.
- The **DATA Act** (2014) — standardized federal spending data.
- Privacy counterweights: **GDPR** (Art. 17 erasure), **CCPA**, and the **CARE Principles** for Indigenous Data Governance, which sit *alongside* FAIR and can pull the other way (collective authority and restricted access vs. maximal openness).

*How the skill relates:* the skill is strong on Sunlight + licensing but didn't name the federal *mandates*. A focused policy note (M-13-13 → DCAT-US, the Evidence Act / OPEN Government Data Act, the DATA Act) now lives in [`open-data-standards.md`](open-data-standards.md), and the CARE-vs-FAIR tension is sharpened in [`project-template.md`](project-template.md#governance). Naming a mandate lets an agent prioritize — *federally-required-but-PDF-locked* beats *nice-to-have* — and gives the README a citation for *why* the data should have been public.

### 5. Global initiatives — the international layer

Open government is not a US-only story. The anchors: the **Open Government Partnership** (OGP, est. 2011; ~75+ member countries plus local jurisdictions, working through National Action Plans and an Independent Reporting Mechanism co-created with civil society), the **International Open Data Charter** (principles adopted by a large number of national and subnational governments), the **Open Knowledge Foundation** (OKFN — steward of **CKAN**, the portal software behind data.gov, `open.canada.ca`, `data.europa.eu`-adjacent and many national portals, and the **Open Data Handbook**), fiscal-transparency bodies (**GIFT** — sunsetted July 2025, materials hosted by the **International Budget Partnership**; the **Open Budget Index**), and **Transparency International** / the **World Bank Open Government Data Toolkit**.

*How the skill relates:* this is the skill's biggest blind spot — its lineage and tooling (GitHub, CC-BY, Datasette) are US/Anglophone. That's a *deliberate scope boundary*, not a defect the skill can fully close, but it should be *named*. A short international-context note now lives in [`movement-history.md`](movement-history.md) so an agent working outside the US knows which universal principles transfer (immutable originals, tidy long-form, provenance, reconciliation) and which implementation assumptions to localize (license regime, portal software, hosting, language).

## Gaps and tensions, and how the skill responds

The audit against the knowledge base surfaced six gaps. Honest disposition: two are addressed by *fixes*, two by *this reference plus light cross-links*, and two are *deliberate scope boundaries* now made explicit rather than silently left open.

| # | Gap / tension | Disposition |
|---|---|---|
| 1 | **Institutional data portals** — skill publishes its own surfaces, ignores federating into data.gov / CKAN / Socrata | Fix: DCAT-export / CKAN note in [`toolchain-datasette.md`](toolchain-datasette.md); framing [below](#institutional-publishing-the-portal-layer) |
| 2 | **Federal policy not encoded** — no M-13-13, Evidence Act, DATA Act | Fix: policy note added to [`open-data-standards.md`](open-data-standards.md) |
| 3 | **Civic-tech intermediaries named but not connected** | This reference (theme 3) + the existing README *movement context* convention; stays a documentation concern |
| 4 | **CARE / GDPR / CCPA named but not operationalized** | Fix: CARE-vs-FAIR + privacy decision note sharpened in [`project-template.md`](project-template.md#governance) |
| 5 | **International landscape absent** — OGP, OKFN, Open Data Charter, SDMX, CKAN | This reference (theme 5) + international-context note in [`movement-history.md`](movement-history.md); a deliberate scope boundary, now named |
| 6 | **Transparency politics underexplored** — redaction disputes, what to refuse | This reference (theme 2) + FOIA-process/scope note in [`discovery-and-audit.md`](discovery-and-audit.md) |

### Institutional publishing: the portal layer

The skill's default deployment is *activist*: extract locked data, build a Datasette + Quarto + LFS bundle, host it yourself. That is the right MVP for a 1–3-person liberation project. But when the audience is a city or agency open-data program, the expected endpoint is *their* portal — a **CKAN** or **Socrata** instance that ingests a **DCAT** catalog record. These are two different workflows, and the skill should not pretend the second away:

- For **self-hosted** publishing, nothing changes — Datasette/Quarto/LFS as today.
- For **portal federation**, emit a DCAT-US catalog record alongside `metadata.yaml` (see the note in [`toolchain-datasette.md`](toolchain-datasette.md) and the crosswalk in [`open-data-standards.md`](open-data-standards.md#crosswalk-standards--what-the-skill-already-builds)) so the dataset can be harvested into data.gov-style discovery. Optional, only when a portal consumer exists.

This is the load-bearing tension between the knowledge base (institutional, federated, global) and the skill (small-team, self-hosted, US). Naming it is the fix; collapsing the skill into a portal CMS is not.

## Referenced-resources catalog

The knowledge base's *Resources* directory, incorporated here as a load-on-demand catalog. Grouped by purpose; each entry is a primary, verifiable source an agent can fetch when a project needs it. (Status notes flag resources that have sunsetted — verify before relying on them.)

### Federal data & API portals
- **data.gov** — <https://data.gov/> — the US federal open-data catalog (hundreds of thousands of datasets).
- **api.data.gov** — <https://api.data.gov/> — unified API-key gateway across federal APIs.
- **Census Bureau APIs** — <https://developer.census.gov/> — demographic, economic, housing data.
- **USAspending.gov** + **API** — <https://www.usaspending.gov/> / <https://api.usaspending.gov/> — federal contracts, grants, loans (DATA Act).
- **Treasury Fiscal Data** — <https://fiscaldata.treasury.gov/> — official budget/financial datasets and APIs.

### Portal software, standards & toolkits
- **CKAN** — <https://ckan.org/> — open-source data-portal platform behind data.gov and many national portals; speaks DCAT.
- **DCAT** (W3C) — the data-catalog vocabulary; see [`open-data-standards.md`](open-data-standards.md).
- **FAIR principles** — Findable / Accessible / Interoperable / Reusable; see [`open-data-standards.md`](open-data-standards.md).
- **Open Civic Data** — <https://open-civic-data.readthedocs.io/> — schemas for governments, officials, legislation, events (OpenStates lineage).
- **8 Principles of Open Government Data** — <https://opengovdata.org/> — the 2007 foundational principles.
- **World Bank Open Government Data Toolkit** — <https://opendatatoolkit.worldbank.org/> — implementation guidance for OGD programs.
- **Open Data Handbook** (OKFN) — <https://opendatahandbook.org/> — practical how-to for opening data.

### Transparency & access to information
- **FOIA.gov** — <https://www.foia.gov/> — official federal FOIA guidance + request routing.
- **Reporters Committee for Freedom of the Press** — <https://www.rcfp.org/> — legal resources for journalists seeking records.
- **State sunshine / open-records laws** — vary by state; the publisher's records officer is the entry point (see [`discovery-and-audit.md`](discovery-and-audit.md)).

### Money in politics & accountability
- **OpenSecrets** — <https://www.opensecrets.org/> — federal campaign finance and lobbying.
- **Follow the Money** — <https://www.followthemoney.org/> — state-level campaign finance.
- **GAO** — <https://www.gao.gov/> — congressional audit/watchdog.
- **Office of Special Counsel** — <https://osc.gov/> — federal whistleblower protection.
- **POGO** — <https://www.pogo.org/> — nonpartisan government-oversight investigations.

### Civic-tech & civil-society organizations
- **Code for America** — <https://codeforamerica.org/> — civic-tech tools and the Brigade network.
- **Open Knowledge Foundation** — <https://okfn.org/> — global open-data nonprofit; stewards CKAN and the Open Data Handbook.
- **OpenTheGovernment** — <https://www.openthegovernment.org/> — open-government advocacy coalition.

### International initiatives & frameworks
- **Open Government Partnership** — <https://www.opengovpartnership.org/> — multilateral open-gov initiative (National Action Plans, IRM).
- **International Open Data Charter** — <https://opendatacharter.org/> — shared open-data principles across governments.
- **Transparency International** — <https://www.transparency.org/> — global anti-corruption; Corruption Perceptions Index.
- **International Budget Partnership** — <https://internationalbudget.org/> — fiscal transparency; Open Budget Survey/Index; hosts legacy **GIFT** materials (GIFT sunsetted July 2025).
- **World Bank — Open Government** — <https://www.worldbank.org/en/topic/governance> — global open-government solutions.

### Privacy & compliance
- **GDPR** — the EU data-protection regime (Art. 17 right to erasure); the global reference standard.
- **Data Privacy Framework** — <https://www.dataprivacyframework.gov/> — transatlantic data-transfer compliance.
- **CARE Principles for Indigenous Data Governance** — <https://www.gida-global.org/care> — collective benefit, authority to control, responsibility, ethics.

## How to use this responsibly

- **Cite the mandate, don't just extract.** When a source is legally *owed* (Evidence Act, M-13-13, a state sunshine law), name that in the README — it's the strongest justification for the work and orients downstream users.
- **Match the publishing surface to the audience.** Self-hosted Datasette for an activist release; a DCAT record for portal federation. Don't build portal machinery a project doesn't need.
- **Localize before you globalize.** Outside the US, the principles transfer but the implementation (license regime, CKAN vs. GitHub Pages, language, hosting) needs local judgment. Name the assumptions you're carrying.
- **Let privacy law and CARE actually constrain.** Unlike most of this skill's "optional" guidance, GDPR/CCPA and CARE can mean *do not publish, or publish differently*. Treat those as real gates, not caveats — see [`project-template.md`](project-template.md#governance).
- **Don't over-trust any single aggregator.** This very reference was prompted by a site that couldn't be fetched; follow the primary links above and verify figures before citing.

## Further reading within this skill

- [`open-data-standards.md`](open-data-standards.md) — the technical standards (DCAT, PROV, DQV, FAIR) and the federal-policy note.
- [`movement-history.md`](movement-history.md) — the activist lineage + the international-context note.
- [`discovery-and-audit.md`](discovery-and-audit.md) — FOIA-as-process and the bulletproofing checklist.
- [`project-template.md`](project-template.md#governance) — licensing, CARE-vs-FAIR, privacy, out-of-scope uses.
- [`toolchain-datasette.md`](toolchain-datasette.md) — `metadata.yaml` and the optional DCAT/CKAN federation path.
