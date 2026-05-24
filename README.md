# data-liberation

An [Agent Skill](https://agentskills.io) for orchestrating data liberation projects — turning government PDFs, FOIA releases, scanned reports, scraped HTML, and panel-format spreadsheets into tidy, documented, reproducible civic datasets.

## What the skill does

Loaded into a compatible agent (Claude Code, Claude.ai, VS Code Copilot, Cursor, OpenAI Codex, Gemini CLI, Goose, OpenCode, and the [other clients in the AgentSkills ecosystem](https://agentskills.io/home)), it gives the agent:

- **A project template.** Immutable originals → processed tidy data → audit reports → lookups (crosswalks). Bootstraps single-source but is structured for multi-source work from day one.
- **Toolchain decision trees.** When to reach for pdfplumber vs. camelot vs. tesseract; requests + BeautifulSoup vs. headless browser vs. archived snapshots; how to normalize XLSX / CSV / Parquet / HTML / XML / JSON into tabular form.
- **Documentation conventions.** Data dictionaries, harmonization crosswalks, per-extract provenance, filter-and-pivot recipes for tidy ↔ wide reshapes.
- **Auditing patterns.** Discovery of new upstream sources; reconciliation of processed data against original totals.
- **A six-phase workflow** — Survey → Scaffold → Extract → Tidy → Audit → Publish — that maps to CRISP-DM's data understanding → preparation → deployment phases and deliberately stops where modeling begins.
- **The movement context.** The civic data liberation tradition (Sunlight Foundation, PDF Liberation Working Group, MuckRock, PUDL, BoulderPublicData) and its academic counterpart (Shigarov's table understanding survey, Holstein et al.'s data understanding dimensions).

The skill triggers on phrases like "data liberation," "PDF extraction," "tidy data," "data dictionary," "crosswalk," "provenance," "reconcile," and "scrape this site" — and on any request that involves turning a document into a dataset someone else could reuse. See [SKILL.md](SKILL.md) for the full instructions.

## Repository contents

```
data-liberation-skill/
├── SKILL.md           # Skill entry point (loaded on activation)
├── references/        # Toolchain + methodology docs (loaded on demand)
└── scripts/           # scaffold.py — fetches the template repo and renders it
```

The working project template lives in a separate repo, [`brianckeegan/data-liberation-template`](https://github.com/brianckeegan/data-liberation-template), pinned to a tagged release. `scripts/scaffold.py` fetches it at scaffold time so the skill repo stays small and an agent doesn't burn context on files it shouldn't be reading directly.

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

In Claude Code, run `/skills` and confirm `data-liberation` appears. In VS Code Copilot agent mode, do the same in the chat panel. The skill should activate on prompts like *"liberate this PDF into a tidy CSV"* or *"scaffold a new civic data project."*

## License

MIT — see [LICENSE](LICENSE).
