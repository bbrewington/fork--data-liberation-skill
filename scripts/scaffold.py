#!/usr/bin/env python3
"""Scaffold a new data-liberation project from the bundled template.

Copies `assets/template-project/` to a destination path and substitutes
Jinja-style placeholders. Zero dependencies — uses only the standard
library so this runs in any Python ≥3.10 environment.

Usage
-----
    python scripts/scaffold.py \\
        --dest ~/code/boulder-election-results \\
        --name boulder-election-results \\
        --description "Boulder County election results, 1980–present" \\
        --author "Brian Keegan <bkeegan@example.org>" \\
        --owner BoulderPublicData \\
        --consumers pandas,R

Run with `--dry-run` to see what would be written without touching disk.

The placeholder set is documented in `references/project-template.md`
("Slot-fills used by `scaffold.py`").
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE_DIR = HERE.parent / "assets" / "template-project"

# File suffixes we treat as text (substitute placeholders). Anything else is
# copied byte-for-byte.
TEXT_SUFFIXES = {
    ".py", ".md", ".toml", ".yml", ".yaml", ".cfg", ".ini",
    ".txt", ".csv", ".json", ".disabled", ".gitkeep", ".gitignore",
    ".qmd",            # Quarto source files
    ".gitattributes",  # LFS configuration
}
# Files we always treat as text by exact name (no suffix or unusual case).
TEXT_NAMES = {".gitignore", ".gitkeep", ".gitattributes", "AGENTS.md", "README.md"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--dest", required=True, type=Path,
                   help="Destination directory (created if absent; must be empty if it exists).")
    p.add_argument("--name", required=True,
                   help="Project name, kebab-case (e.g. 'boulder-election-results').")
    p.add_argument("--description", required=True,
                   help="One-line description of what the project liberates.")
    p.add_argument("--author", default=None,
                   help="Author string. Falls back to `git config user.name <user.email>` if absent.")
    p.add_argument("--owner", default=None,
                   help="GitHub owner (user or org) the project will live under. "
                        "Used in README badges, Quarto site URL, and BibTeX. "
                        "Falls back to `git config user.name` if absent.")
    p.add_argument("--consumers", default="pandas",
                   help="Comma-separated consumer stacks (e.g. 'pandas,R,polars').")
    p.add_argument("--dry-run", action="store_true",
                   help="Print planned writes without touching disk.")
    return p.parse_args(argv)


def derive_slug(name: str) -> str:
    """`boulder-election-results` → `boulder_election_results`. Strict
    snake_case; lowercase ASCII letters, digits, underscores only.
    """
    cleaned = []
    for ch in name.strip().lower():
        if ch.isalnum():
            cleaned.append(ch)
        elif ch in "-_ ":
            cleaned.append("_")
        # silently drop other characters
    slug = "".join(cleaned).strip("_")
    if not slug:
        raise SystemExit(f"Cannot derive a valid Python identifier from name {name!r}")
    if slug[0].isdigit():
        slug = "_" + slug
    return slug


def _git_config(key: str) -> str:
    try:
        result = subprocess.run(
            ["git", "config", key], capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        return ""
    return result.stdout.strip()


def detect_git_author() -> str | None:
    name = _git_config("user.name")
    email = _git_config("user.email")
    if name and email:
        return f"{name} <{email}>"
    return name or None


def build_placeholders(args: argparse.Namespace) -> dict[str, str]:
    author = args.author or detect_git_author() or "Anonymous"
    owner = args.owner or _git_config("user.name") or "OWNER"
    return {
        "project_name":   args.name,
        "project_slug":   derive_slug(args.name),
        "description":    args.description,
        "author":         author,
        "owner":          owner,
        "consumer_stack": args.consumers,
    }


def is_text_file(path: Path) -> bool:
    if path.name in TEXT_NAMES:
        return True
    if path.suffix in TEXT_SUFFIXES:
        return True
    return False


def substitute(text: str, placeholders: dict[str, str]) -> str:
    """Replace every `{{ key }}` (with surrounding whitespace flexibility)
    using a simple `str.replace`. No dependencies, no escaping rules to
    learn, no surprises.
    """
    out = text
    for key, value in placeholders.items():
        # Accept either `{{ key }}` (one space) or `{{key}}` for hand-typed
        # variants. Run the wider form first so the substitution is
        # idempotent.
        out = out.replace("{{ " + key + " }}", value)
        out = out.replace("{{" + key + "}}", value)
    return out


def walk_and_write(
    src: Path,
    dst: Path,
    placeholders: dict[str, str],
    dry_run: bool,
) -> list[Path]:
    """Copy `src` tree to `dst`, substituting placeholders in text files.

    Returns a list of destination paths written (or that would be).
    """
    written: list[Path] = []
    for entry in src.rglob("*"):
        rel = entry.relative_to(src)
        # Substitute placeholders in path components too — lets the
        # template support filenames like `{{ project_slug }}.csv`.
        rel_str = substitute(str(rel), placeholders)
        target = dst / rel_str

        if entry.is_dir():
            if not dry_run:
                target.mkdir(parents=True, exist_ok=True)
            continue

        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)

        if is_text_file(entry):
            text = entry.read_text(encoding="utf-8")
            rendered = substitute(text, placeholders)
            if dry_run:
                print(f"  [text]   {target}")
            else:
                target.write_text(rendered, encoding="utf-8")
        else:
            if dry_run:
                print(f"  [binary] {target}")
            else:
                shutil.copy2(entry, target)
        written.append(target)
    return written


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    placeholders = build_placeholders(args)
    dest = args.dest.expanduser().resolve()

    if not TEMPLATE_DIR.exists():
        sys.stderr.write(
            f"Template directory not found: {TEMPLATE_DIR}\n"
            f"This script must run from a checked-out copy of the "
            f"data-liberation skill, where assets/template-project/ exists.\n"
        )
        return 1

    if dest.exists():
        if any(dest.iterdir()):
            sys.stderr.write(
                f"Destination {dest} exists and is not empty. "
                f"Refusing to overwrite. Pick a fresh directory.\n"
            )
            return 1
    else:
        if not args.dry_run:
            dest.mkdir(parents=True)

    print(f"Scaffolding {args.name}")
    print(f"  → {dest}")
    print(f"  slug:      {placeholders['project_slug']}")
    print(f"  author:    {placeholders['author']}")
    print(f"  owner:     {placeholders['owner']}")
    print(f"  consumers: {placeholders['consumer_stack']}")
    if args.dry_run:
        print("  (dry-run; no files written)")
    print()

    written = walk_and_write(TEMPLATE_DIR, dest, placeholders, args.dry_run)

    if args.dry_run:
        print(f"\nWould write {len(written)} files.")
        return 0

    print(f"Wrote {len(written)} files.")
    print()
    print("Next steps:")
    print(f"  cd {dest}")
    print("  uv sync")
    print("  uv run pytest")
    print("  # Edit scripts/config.py to register your first source,")
    print("  # then `uv run python -m scripts.pipeline run`.")
    print("  # For Datasette publishing: `uv sync --extra publish` then")
    print("  # `uv run python -m scripts.publish build` and `serve` or `deploy`.")
    print("  # For the Quarto site: run `quarto publish gh-pages` once locally,")
    print("  # then rename .github/workflows/gh-pages.yml.disabled to enable CI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
