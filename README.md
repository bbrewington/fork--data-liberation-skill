# data-liberation

An [Agent Skill](https://agentskills.io) for orchestrating data liberation projects — turning government PDFs, FOIA releases, scanned reports, scraped HTML, and panel-format spreadsheets into tidy, documented, reproducible civic datasets.

## What the skill does

Loaded into a compatible agent (Claude Code, Claude.ai, VS Code Copilot, Cursor, OpenAI Codex, Gemini CLI, Goose, OpenCode, and the [other clients in the AgentSkills ecosystem](https://agentskills.io/home)), it gives the agent:

- **Six escalating levels of complexity.** The skill's organizing idea: start at the lowest level that satisfies the request and offer to climb, so getting a CSV out of a PDF never requires buying the whole apparatus.
  - **L0 Extract** — source to CSV, no scaffold. "Just the data."
  - **L1 + Documentation** — data dictionary, provenance, README note. Now citable.
  - **L2 + Pipeline & Audit** — scaffolded, reproducible, validated. "Someone can re-run this."
  - **L3 + Harmonization** — crosswalks across sources, with caveats. Multi-source.
  - **L4 + Standards & Governance** — DCAT/PROV/FAIR naming + governance/ethics. Publishable responsibly.
  - **L5 + Publishing** — Datasette, Quarto site, Git LFS, DocumentCloud.

  The agent infers the level from the request, states its assumption, executes, and offers the next rung — see SKILL.md's *The six levels* section.
- **A six-phase workflow** — Survey → Scaffold → Extract → Tidy → Audit → Publish — mapping to CRISP-DM's data understanding → preparation → deployment phases and deliberately stopping where modeling begins. The phases describe *how* the work gets done within a project; the levels above describe *how far* a given engagement goes. Searchable against industry vocabulary (Goal Planning, Data Extraction, Data Cleaning and Transformation, Data Loading, Data Validation, Data Lineage, Data Observability, Data Governance, Data Maintenance) — see SKILL.md's vocabulary-alignment table.
- **A project template.** Immutable originals → processed tidy data → audit reports → lookups (crosswalks). Bootstraps single-source but is structured for multi-source work from day one. Fetched on demand from [`brianckeegan/data-liberation-template`](https://github.com/brianckeegan/data-liberation-template) by `scripts/scaffold.py`.
- **Toolchain decision trees.** When to reach for pdfplumber vs. camelot vs. tesseract; requests + BeautifulSoup vs. headless browser vs. archived snapshots; how to normalize XLSX / CSV / Parquet / HTML / XML / JSON into tabular form.
- **A 9-step cleaning pipeline.** Profile → structural fixes → exact + fuzzy deduplication (Jaro-Winkler / Levenshtein) → missing-value treatment (Rubin's MCAR/MAR/MNAR) → outlier detection (IQR + impossible-value ranges) → standardization → validation + reject port → PII redaction (presidio/scrubadub) → documentation. Each step with concrete tooling, mapped to a semantic role (source-extraction / transformation / sink-publication).
- **Documentation conventions and the contract framing.** Data dictionaries and pandera schemas as a *contract* the processed CSV obeys; concept catalogs as contracts at the cross-source-equivalence level; per-extract provenance; the five-dimension data-quality framework (availability / usability / reliability / relevance / presentation).
- **Auditing and bulletproofing patterns.** Discovery of new upstream sources; reconciliation of processed data against authoritative top-line totals; a pre-extraction bulletproofing checklist mapping each practitioner check to a quality dimension; the cron-driven recurring-refresh PR pattern.
- **A governance section.** License inheritance, data-subject considerations (CARE principles, out-of-scope use declarations), project-internal governance (schema-revision discipline, conflict-resolution paths), and downstream accountability (error-reporting paths, citation guidance, retraction-equivalent paths).
- **The movement context.** The civic-data liberation tradition (Sunlight Foundation, PDF Liberation Working Group, MuckRock, PUDL, BoulderPublicData) and the scholarly critiques worth keeping in view — Baack's "empowering intermediary" framing, Schrock's five activities of civic hacking, Johnson's information-justice frame, Casemajor's contested-data-culture diagnosis.
- **Open data standards, as background (not a constraint).** A synthesis of the official open-data frameworks the skill's artifacts already informally implement — the Sunlight Open Data Policy Guidelines, DCAT-US / W3C DCAT (cataloging), W3C PROV-O (provenance) and the Data Quality Vocabulary, the Data on the Web Best Practices, the FAIR principles, and the FAIRsharing / re3data / NIEM registries and exchange models — each profiled by history, precedents, standards organization, institutions, and infrastructure, with a crosswalk from each standard to the existing artifact (`provenance.csv` ≈ PROV, `metadata.yaml` ≈ DCAT, the quality dimensions ≈ DQV) and an optional deepening step. The skill treats these as background for *naming and optionally extending* what it does — never as added requirements or a gate in front of shipping.
- **The open government landscape, as background (not a constraint).** The civic and institutional context around the data: transparency law and records requests (FOIA, state sunshine laws), the US federal open-data mandates (OMB M-13-13, the OPEN Government Data Act / Evidence Act, the DATA Act), the civic-tech consumer ecosystem, institutional data portals (data.gov, CKAN, Socrata), and the international frame (Open Government Partnership, the International Open Data Charter, the Open Knowledge Foundation). Includes a catalogue of referenced resources (data.gov, FOIA.gov, USAspending, OGP, OKFN/CKAN, the World Bank toolkit, and more) and an honest gap-analysis of where the skill's small-team, US, self-hosted defaults meet the institutional and global picture — with privacy law and the CARE principles flagged as the few places that are *real gates*, not advisory.

The skill triggers on phrases like "data liberation," "PDF extraction," "get the data out," "give me a CSV," "make this citable," "reproducible pipeline," "tidy data," "data dictionary," "crosswalk," "provenance," "reconcile," and "scrape this site" — and on any request that involves turning a document into a dataset someone else could reuse. See [SKILL.md](SKILL.md) for the full instructions.

## Repository contents

```
data-liberation-skill/
├── SKILL.md           # Skill entry point (loaded on activation) — the six levels + workflow
├── references/        # Toolchain + methodology docs (loaded on demand), grouped by level
│   ├── extract.md            # L0: PDF (pdfplumber/camelot/tesseract), tabular (XLSX/CSV/Parquet/db), HTML/XML/JSON, scraping
│   ├── data-modeling.md      # L1–L3: tidy, schema-as-contract, dictionary, concepts/crosswalks, provenance, validation, quality dimensions
│   ├── pipeline.md           # L2: 9-step cleaning pipeline + discovery/audit/reconcile + bulletproofing + recurring refresh
│   ├── project-template.md   # L2/L4: project skeleton spec + governance section
│   ├── publishing.md         # L5: Datasette, Quarto site, Git LFS, DocumentCloud
│   └── context.md            # L4 background (not a gate): movement history + critical perspectives, open-data standards, open-government landscape
├── scripts/scaffold.py  # Fetches the template repo and renders it (L2+ only)
└── RELEASING.md         # Lockstep version-bump procedure across skill + template repos
```

The working project template lives in a separate repo, [`brianckeegan/data-liberation-template`](https://github.com/brianckeegan/data-liberation-template), pinned to a commit SHA so scaffolded output is reproducible. `scripts/scaffold.py` fetches it at scaffold time so the skill repo stays small and an agent doesn't burn context on files it shouldn't be reading directly.

## Installation

The skill follows the [AgentSkills.io specification](https://agentskills.io/specification): a folder containing a `SKILL.md` with `name` and `description` frontmatter, plus optional `scripts/`, `references/`, and `assets/`. Every AgentSkills-compatible client discovers skills the same way — by scanning one or more known directories — so installation is just cloning this repo (or symlinking it) into the directory your client watches, **as a folder named `data-liberation`** (the folder name must match the `name:` field in the frontmatter).

### Claude Code, Claude.ai, Claude Agent SDK

User-level (available across all projects):

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/brianckeegan/data-liberation-skill.git ~/.claude/skills/data-liberation
```

Project-level (scoped to one repo):

```bash
mkdir -p .claude/skills
git clone https://github.com/brianckeegan/data-liberation-skill.git .claude/skills/data-liberation
```

### VS Code (Copilot agent mode), Cursor, and most other AgentSkills clients

Project-level — the default location is `.agents/skills/`:

```bash
mkdir -p .agents/skills
git clone https://github.com/brianckeegan/data-liberation-skill.git .agents/skills/data-liberation
```

### Other clients

For OpenAI Codex, Gemini CLI, Goose, OpenCode, OpenHands, Amp, Letta, Factory, and the rest of the [client showcase](https://agentskills.io/home), check that client's skills documentation for its install path, then clone this repo into it under the folder name `data-liberation`. The skill itself is unchanged across clients.

### Verify it loaded

In Claude Code, run `/skills` and confirm `data-liberation` appears. In VS Code Copilot agent mode, do the same in the chat panel. The skill should activate on prompts like *"get the data out of this PDF into a CSV"* (L0), *"liberate this PDF into a documented, citable dataset"* (L1), or *"scaffold a new civic data project"* (L2).

## License

MIT — see [LICENSE](LICENSE).
