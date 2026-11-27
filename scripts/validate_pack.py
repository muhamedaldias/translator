#!/usr/bin/env python3
"""Validate the portable translation skill pack.

Checks (all must hold for exit status 0):
  * every skills/**/SKILL.md and agents/*.md has YAML frontmatter with
    non-empty ``name`` and ``description``;
  * .claude-plugin/plugin.json exists and parses as a JSON object;
  * no tracked text file contains the retired absolute project path
    (assembled at runtime so this validator does not flag itself);
  * no SKILL.md, agent definition or README instructs the reader to set an
    API key (mentions that say no key is needed are fine);
  * outputs/ is ignored by .gitignore.

Usage: python scripts/validate_pack.py [--root REPO_ROOT]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - PyYAML is a declared requirement
    yaml = None  # type: ignore

STALE_PATH = "/data/workspace/" + "projects/translator"

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "outputs",
    "cache",
}

BINARY_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".db",
    ".sqlite",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".pdf",
    ".epub",
    ".docx",
    ".zip",
    ".gz",
    ".so",
    ".woff",
    ".woff2",
}

API_KEY_RE = re.compile(
    r"\b(?:api[\s_-]*key|api_key|openai_api_key|anthropic_api_key|"
    r"access[_\s-]?token|secret[_\s-]?key)\b",
    re.IGNORECASE,
)
SET_VERB_RE = re.compile(
    r"\b(?:set|export|configure|provide|enter|paste|add|obtain|get|create|"
    r"supply|define|require|need|must|generate|copy)\b",
    re.IGNORECASE,
)
NEGATION_RE = re.compile(
    r"\b(?:no|not|never|without|avoid|do\s+not|don't|does\s+not|doesn't|"
    r"must\s+not|none|unnecessary|optional|deprecated|ignore|forbidden|"
    r"prohibited|free|unneeded)\b",
    re.IGNORECASE,
)
ASSIGNMENT_RE = re.compile(
    r"(?:export\s+[A-Z0-9_]*(?:API_KEY|TOKEN|SECRET)\s*=)"
    r"|(?:os\.environ\[[^\]]*(?:API_KEY|TOKEN|SECRET)[^\]]*\]\s*=)"
    r"|(?:api[\s_-]?key\s*[:=]\s*[\"'][^\"']+[\"'])",
    re.IGNORECASE,
)
OUTPUTS_IGNORE_RE = re.compile(r"^outputs/?\s*(?:#.*)?$")


def _rel(root: Path, path: Path) -> str:
    """Return a stable, relative path for messages."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _walk_text_files(root: Path, skip_dirs: Sequence[str] = ()) -> list[Path]:
    """All readable text files below root, excluding heavyweight tool dirs."""
    excluded = set(SKIP_DIRS) | set(skip_dirs)
    found: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in excluded for part in path.relative_to(root).parts):
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        found.append(path)
    return found


def _tracked_text_files(root: Path) -> list[Path]:
    """Git-tracked text files, with a filesystem walk outside a git checkout."""
    git_dir = root / ".git"
    if git_dir.exists():
        try:
            proc = subprocess.run(
                ["git", "-C", str(root), "ls-files", "-z"],
                capture_output=True,
                check=True,
                timeout=30,
            )
            files: list[Path] = []
            for raw in proc.stdout.split(b"\0"):
                if not raw:
                    continue
                path = root / raw.decode("utf-8", "replace")
                if not path.is_file() or path.suffix.lower() in BINARY_SUFFIXES:
                    continue
                try:
                    path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                files.append(path)
            return files
        except (OSError, subprocess.SubprocessError):
            pass  # fall through to the untracked-tree fallback
    return _walk_text_files(root)


def _frontmatter(path: Path) -> tuple[dict | None, str | None]:
    """Parse YAML frontmatter, returning (data, error)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, "missing opening '---' frontmatter delimiter"
    closing = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing = index
            break
    if closing is None:
        return None, "missing closing '---' frontmatter delimiter"
    if yaml is None:
        return None, "PyYAML is required to parse frontmatter"
    try:
        data = yaml.safe_load("\n".join(lines[1:closing]))
    except Exception as exc:  # yaml.YAMLError and friends
        return None, f"invalid YAML frontmatter: {exc}"
    if not isinstance(data, dict):
        return None, "frontmatter must be a YAML mapping with name and description"
    return data, None


def _api_key_violations(paths: Sequence[Path], root: Path) -> list[str]:
    violations: list[str] = []
    for path in dict.fromkeys(paths):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            if NEGATION_RE.search(line):
                continue  # "no API key is required" is the desired message
            if ASSIGNMENT_RE.search(line) or (API_KEY_RE.search(line) and SET_VERB_RE.search(line)):
                violations.append(
                    f"api-key instruction: {_rel(root, path)}:{lineno} "
                    "instructs setting an API key"
                )
    return violations


def validate_pack(root: Path) -> list[str]:
    """Return a list of human-readable violations; empty means valid."""
    root = Path(root).resolve()
    violations: list[str] = []

    # 1. Loadable frontmatter on every skill and agent definition.
    skills = sorted(root.glob("skills/**/SKILL.md"))
    agents = sorted(root.glob("agents/*.md"))
    if not skills:
        violations.append("frontmatter: no skills/**/SKILL.md found")
    if not agents:
        violations.append("frontmatter: no agents/*.md found")
    for path in skills + agents:
        data, error = _frontmatter(path)
        if error or data is None:
            violations.append(f"frontmatter: {_rel(root, path)}: {error or 'empty frontmatter'}")
            continue
        for field in ("name", "description"):
            value = data.get(field)
            if not isinstance(value, str) or not value.strip():
                violations.append(f"frontmatter: {_rel(root, path)}: missing or empty '{field}'")

    # 2. Claude Code plugin manifest parses.
    plugin = root / ".claude-plugin" / "plugin.json"
    if not plugin.is_file():
        violations.append("plugin: missing .claude-plugin/plugin.json")
    else:
        try:
            manifest = json.loads(plugin.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            violations.append(f"plugin: .claude-plugin/plugin.json does not parse: {exc}")
        else:
            if not isinstance(manifest, dict):
                violations.append("plugin: .claude-plugin/plugin.json must be an object")

    # 3. No stale absolute project path in any tracked text file.
    for path in _tracked_text_files(root):
        # Design records quote the retired path deliberately as historical
        # context; they are documentation, not product files.
        if _rel(root, path).startswith("docs/superpowers/"):
            continue
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            if STALE_PATH in line:
                violations.append(f"stale path: {_rel(root, path)}:{lineno} contains {STALE_PATH}")

    # 4. No API-key setup instructions in skills, agents or READMEs.
    api_key_paths = list(skills) + list(agents)
    api_key_paths += [p for p in _walk_text_files(root) if p.name.startswith("README")]
    violations.extend(_api_key_violations(api_key_paths, root))

    # 5. Translation outputs must be ignored.
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        violations.append("gitignore: missing .gitignore (outputs/ must be ignored)")
    else:
        lines = [
            line.strip()
            for line in gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
        ]
        if not any(OUTPUTS_IGNORE_RE.match(line) for line in lines):
            violations.append("gitignore: outputs/ is not ignored by .gitignore")

    return violations


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the portable translation skill pack")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="repository root to validate (default: this repository)",
    )
    args = parser.parse_args(argv)
    violations = validate_pack(args.root)
    if violations:
        print(f"Pack validation FAILED with {len(violations)} violation(s):")
        for index, violation in enumerate(violations, 1):
            print(f"  {index}. {violation}")
        return 1
    print("Pack validation PASSED: all checks green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
