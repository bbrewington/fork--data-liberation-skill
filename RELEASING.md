# Releasing — keeping the skill and template repos in lockstep

The `data-liberation` skill lives in two repos that have to ship coordinated changes:

- **[brianckeegan/data-liberation-skill](https://github.com/brianckeegan/data-liberation-skill)** — `SKILL.md`, `references/`, and `scripts/scaffold.py`.
- **[brianckeegan/data-liberation-template](https://github.com/brianckeegan/data-liberation-template)** — the working Python project skeleton that `scaffold.py` copies.

This document is the procedure for releasing them together without drift.

## Versioning

Skill and template share a version number. Skill `v0.2.0` is **paired with** template `v0.2.0`. They don't have to share semver semantics across the pair — a skill-only change that just edits prose still bumps both, because `scripts/scaffold.py` pins to a specific template commit. This way "skill `v0.2.0`" unambiguously identifies what gets scaffolded.

## Pinning by SHA, not by tag

`scripts/scaffold.py`'s `DEFAULT_TEMPLATE_VERSION` is a **commit SHA**, not a tag. Tags on GitHub are mutable; a force-push to `v0.1.0` on the template repo would silently change scaffolded output for every user on the corresponding skill version. SHA pinning makes the bytes reproducible.

`DEFAULT_TEMPLATE_TAG` next to it is the human-readable equivalent — kept in sync at release time, used only in messaging.

## The release dance

To cut a new joint release `vX.Y.Z`:

### 1. In the template repo

```bash
cd data-liberation-template

# Make sure CI is green on main
gh run list --limit 3

git tag -a vX.Y.Z -m "vX.Y.Z — <one-liner>"
git push origin vX.Y.Z

# Capture the SHA the tag now points at
TEMPLATE_SHA=$(git rev-parse vX.Y.Z)
echo "Template SHA for vX.Y.Z: $TEMPLATE_SHA"

# Create the GitHub release
gh release create vX.Y.Z --title "vX.Y.Z — <one-liner>" --notes "Paired with [data-liberation-skill vX.Y.Z](https://github.com/brianckeegan/data-liberation-skill/releases/tag/vX.Y.Z)."
```

### 2. In the skill repo

```bash
cd data-liberation-skill

# Update scripts/scaffold.py — both lines:
#   DEFAULT_TEMPLATE_VERSION = "<the SHA from step 1>"
#   DEFAULT_TEMPLATE_TAG     = "vX.Y.Z"
$EDITOR scripts/scaffold.py

# Verify the scaffold still works end-to-end against the new template
python scripts/scaffold.py \
  --dest /tmp/release-test --name release-test \
  --description "Release rehearsal" --author "$(git config user.name) <$(git config user.email)>" \
  --owner ci-bot
grep -rE '\{\{ *[a-z_]+ *\}\}' /tmp/release-test  # should be empty
(cd /tmp/release-test && uv sync --extra publish && uv run ruff check scripts tests && uv run pytest -q)

# Commit and tag
git add scripts/scaffold.py
git commit -m "Bump default template pin to vX.Y.Z ($TEMPLATE_SHA)"
git push origin main

git tag -a vX.Y.Z -m "vX.Y.Z — <one-liner>"
git push origin vX.Y.Z
gh release create vX.Y.Z --title "vX.Y.Z — <one-liner>" --notes "..."
```

### 3. Verify

After both tags exist, the skill's `scaffold-e2e.yml` workflow should already have validated the pairing on the bump-commit. Spot-check:

```bash
gh run list --workflow=scaffold-e2e.yml --limit 1
```

## Adding a new `{{ placeholder }}`

When you add a new placeholder to the template, you have to update three things in one PR (or one PR per repo, but in close succession):

1. **In the template** — use the placeholder where you need it: `{{ deploy_target }}`.
2. **In `scaffold.py`** — add a CLI flag (or derive a default), and add the key to `build_placeholders` so `substitute` knows about it.
3. **In `references/project-template.md`** — add a row to the "Slot-fills used by `scaffold.py`" table.

The skill's `scaffold-e2e.yml` will catch any rendered output that still has unresolved `{{ deploy_target }}` literals. The template's `scaffold-e2e.yml` will catch the case where the template uses a placeholder `scaffold.py` doesn't know to render.

## Cross-repo dispatch — one-time setup

The two repos notify each other on changes via `repository_dispatch`. This requires a personal access token shared between them.

### Create the token

1. Go to <https://github.com/settings/tokens?type=beta>.
2. **Generate new token** (fine-grained).
3. Resource owner: `brianckeegan`. Repository access: select both `data-liberation-skill` and `data-liberation-template`.
4. Repository permissions:
   - **Contents:** Read-only
   - **Actions:** Read and write
5. Generate, copy the token (you'll only see it once).

### Install in both repos

```bash
gh secret set DISPATCH_TOKEN --repo brianckeegan/data-liberation-skill
# paste the token

gh secret set DISPATCH_TOKEN --repo brianckeegan/data-liberation-template
# paste the same token
```

### Verify

Push a trivial commit to either repo touching the dispatch trigger paths (e.g., `scripts/scaffold.py` for the skill). The corresponding workflow run on the other repo should appear within ~30 seconds:

```bash
# After pushing to the skill:
gh run list --repo brianckeegan/data-liberation-template --workflow=scaffold-e2e.yml --limit 1

# After pushing to the template:
gh run list --repo brianckeegan/data-liberation-skill --workflow=scaffold-e2e.yml --limit 1
```

The workflows degrade gracefully if the token is missing: they print a warning and exit 0 rather than failing CI.

## CI workflows at a glance

| Workflow | Repo | Trigger | What it does |
|---|---|---|---|
| `scaffold-e2e.yml` | skill | push, PR, `repository_dispatch: template-updated` | Render scaffold.py → lint + test rendered project |
| `scaffold-e2e.yml` | template | push, PR, `repository_dispatch: skill-updated` | Fetch skill's scaffold.py → render this template → lint + test |
| `dispatch-to-template.yml` | skill | push to main touching scaffold.py or template-relevant references | Fire `skill-updated` event to template repo |
| `dispatch-to-skill.yml` | template | push to main | Fire `template-updated` event to skill repo |
| `tests.yml` | template (shipped to scaffolded projects) | push, PR | Ruff + pytest on the **scaffolded** project. Skipped on the template repo itself (placeholders aren't rendered there). |

## Planned follow-ups (template repo)

The skill is organized into six complexity levels (L0–L5; see SKILL.md). L0 (Extract) and
L1 (Documentation) deliberately **do not** scaffold a project — they emit a CSV (and, at L1, a
data dictionary + `provenance.csv` + a Survey/README note) directly. Today `scripts/scaffold.py`
only knows how to render the **full** template, which is the right shape for L2+. To let the
scaffolder serve the lower rungs without overshooting, a follow-up PR (in this repo + the
template repo, in lockstep) should add:

1. **`scaffold.py --level <0-5>`.** A per-level path allowlist in the render walk:
   - `--level 0` → no-op / prints guidance (no files written).
   - `--level 1` → `README.md` + `docs/data-dictionary.md` + a `provenance.csv` header + a minimal
     governance/ethics stub; no `scripts/`, no CI, no `pyproject.toml`.
   - `--level 2` (default) → today's full scaffold.
   - `--level 5` → additionally un-disables `publish.yml` / `gh-pages.yml`.
2. **Template files tagged/grouped by level** so the scaffolder can subset them deterministically.

**Lockstep implication:** the `--level` flag is new behavior pinned to a template SHA, so it is a
**joint skill + template version bump** — update the "Slot-fills used by `scaffold.py`" table in
`references/project-template.md`, and confirm a green `scaffold-e2e.yml` on both repos via the
`repository_dispatch` pairing. (The level-restructure PR that introduced this section changes none
of `scaffold.py`, the template, or the slot-fills table, so it shipped as a **skill-only** change
with no template bump.)

## Yanking a release

If a release ships a broken pairing, the immediate fix is to revert the skill's `scaffold.py` to the previous SHA and tag a patch release. The old tags stay (don't force-push them); the patch release supersedes them.

```bash
# In the skill repo
git revert <bad-bump-commit>
git tag -a vX.Y.Z+1 -m "vX.Y.Z+1 — revert broken template pin"
git push origin main vX.Y.Z+1
gh release create vX.Y.Z+1 --title "vX.Y.Z+1 — hotfix" --notes "Reverts the template pin from vX.Y.Z; pins back to vX.Y.(Z-1)."
```
