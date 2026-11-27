"""Consistency checks for the project-facing documentation.

Scope: the documents a new contributor or host-agent user reads. They must
describe the portable, key-free architecture, use repository-relative paths,
and keep their domain vocabulary separate from implementation detail.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ADR_PATH = "docs/adr/0001-portable-skill-pack-no-api-key.md"

# The project-facing docs owned by this workstream. The retired absolute
# workspace path is assembled so the forbidden literal lives only here as data.
DOC_PATHS = (
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "plan.md",
    "GLOSSARY.md",
    ADR_PATH,
)
STALE_PATH = "/data/workspace/" + "projects/translator"

HOSTS = ("claude-code", "codex", "opencode", "hermes", "generic")
AGENTS = (
    "Analysis",
    "Translator",
    "Post-editor",
    "Reviewer",
    "Editor",
    "Judge",
    "Consistency",
)


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_glossary_and_adr_exist() -> None:
    for relative_path in ("GLOSSARY.md", ADR_PATH):
        assert (REPO_ROOT / relative_path).is_file(), f"missing {relative_path}"


@pytest.mark.parametrize("relative_path", DOC_PATHS)
def test_no_stale_absolute_path_in_docs(relative_path: str) -> None:
    assert STALE_PATH not in _read(relative_path), relative_path


def test_readme_has_no_api_key_setup() -> None:
    readme = _read("README.md")
    forbidden = (
        r"export\s+[A-Z0-9_]*API[\s_]?KEY",
        r"--llm[\s_-]?api[\s_-]?key",
        r"\b(OPENAI|ANTHROPIC|GOOGLE)_API_KEY\b",
        r"api[\s_]?key\s*[:=]\s*[\"']?[A-Za-z0-9]",
        r"\bset\s+(an?\s+)?api[\s_-]?key\b",
    )
    for pattern in forbidden:
        assert not re.search(pattern, readme, re.IGNORECASE), pattern
    assert re.search(
        r"no\s+api[\s_-]?key", readme, re.IGNORECASE
    ), "README should state that no API key is required"


def test_readme_documents_installer_and_seven_agents() -> None:
    readme = _read("README.md")
    assert "scripts/install.sh" in readme
    for flag in ("--host", "--dry-run", "--help", "--dest"):
        assert flag in readme, flag
    for host in HOSTS:
        assert host in readme, host
    for agent in AGENTS:
        assert f"| {agent} |" in readme, agent


def test_glossary_stays_domain_only() -> None:
    glossary = _read("GLOSSARY.md")
    assert glossary.count("_Avoid_:") >= 10
    for implementation_detail in ("Python", "pytest", "src/", ".py", "api_key"):
        assert implementation_detail not in glossary, implementation_detail


def test_adr_records_the_key_free_decision() -> None:
    adr = _read(ADR_PATH)
    for section in ("## Context", "## Decision", "## Consequences", "## Alternatives"):
        assert section in adr, section
    assert "host agent" in adr.lower()
    assert "no api key" in adr.lower()
