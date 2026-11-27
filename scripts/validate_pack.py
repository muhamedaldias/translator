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
  * outputs/ is ignored by .gitignore;
  * no tracked file under data/ or skills/ exceeds 1 MiB;
  * no proprietary dictionary name (Merriam-Webster/Oxford/Collins) appears
    in a file under data/;
  * a root NOTICE exists and mentions CC BY 4.0 and CC BY-SA 4.0.

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

# Data-source gates (lexicon expansion design, approved 2026-11-27).
MAX_TRACKED_FILE_BYTES = 1024 * 1024  # 1 MiB - large lexicons belong outside Git
PROPRIETARY_DICTIONARY_RE = re.compile(
    r"\b(?:merriam[\s-]*webster|oxford|collins)\b",
    re.IGNORECASE,
)
NOTICE_FILENAMES = ("NOTICE", "NOTICE.md", "NOTICE.txt", "NOTICE.rst")
REQUIRED_LICENSE_MARKERS = ("CC BY 4.0", "CC BY-SA 4.0")
DATA_SOURCE_DIRS = ("data", "skills")


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


def _candidate_files(root: Path) -> list[Path]:
    """Files that would be committed: git-tracked in a checkout, else walked."""
    git_dir = root / ".git"
    candidates: list[Path] | None = None
    if git_dir.exists():
        try:
            proc = subprocess.run(
                ["git", "-C", str(root), "ls-files", "-z"],
                capture_output=True,
                check=True,
                timeout=30,
            )
            candidates = [
                root / raw.decode("utf-8", "replace") for raw in proc.stdout.split(b"\0") if raw
            ]
        except (OSError, subprocess.SubprocessError):
            candidates = None
    if candidates is None:
        candidates = sorted(p for p in root.rglob("*") if p.is_file())
    files: list[Path] = []
    for path in candidates:
        try:
            parts = path.relative_to(root).parts
        except ValueError:
            continue
        if any(part in SKIP_DIRS for part in parts):
            continue
        if path.is_file():
            files.append(path)
    return files


def _is_text_file(path: Path) -> bool:
    """True for a UTF-8 readable file with a non-binary suffix."""
    if path.suffix.lower() in BINARY_SUFFIXES:
        return False
    try:
        path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False
    return True


def _under_data_source_dir(rel: str) -> bool:
    """True when a root-relative POSIX path lives under data/ or skills/."""
    return any(rel == d or rel.startswith(d + "/") for d in DATA_SOURCE_DIRS)


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

    # 6. Tracked data/skill files must stay under 1 MiB.
    for path in _candidate_files(root):
        rel = _rel(root, path)
        if not _under_data_source_dir(rel):
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > MAX_TRACKED_FILE_BYTES:
            violations.append(
                f"oversized file: {rel} is {size} bytes (> 1 MiB); "
                "cache large lexicons outside Git"
            )

    # 7. No proprietary dictionary data under data/.
    for path in _candidate_files(root):
        rel = _rel(root, path)
        if not rel.startswith("data/") or not _is_text_file(path):
            continue
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            match = PROPRIETARY_DICTIONARY_RE.search(line)
            if match:
                violations.append(
                    f"proprietary dictionary: {rel}:{lineno} mentions "
                    f"'{match.group(0)}'; proprietary data may not be redistributed"
                )

    # 8. Root NOTICE must carry open-data attribution and license terms.
    notice = next(
        (root / name for name in NOTICE_FILENAMES if (root / name).is_file()),
        None,
    )
    if notice is None:
        violations.append(
            "notice: missing root NOTICE (data-source attribution and licenses required)"
        )
    else:
        lowered = notice.read_text(encoding="utf-8", errors="replace").lower()
        missing = [m for m in REQUIRED_LICENSE_MARKERS if m.lower() not in lowered]
        if missing:
            violations.append(
                f"notice: {_rel(root, notice)} is missing required license marker(s): "
                + ", ".join(missing)
            )

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
