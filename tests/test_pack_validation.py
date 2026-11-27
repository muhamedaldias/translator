"""Tests for scripts/validate_pack.py.

Every test builds a throw-away pack under tmp_path; the real repository is
never mutated.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_pack import main, validate_pack  # noqa: E402

STALE_PATH = "/data/workspace/" + "projects/translator"

FRONTMATTER = "---\nname: demo\ndescription: A demo skill for validation tests\n---\n\n# Demo\n"


@pytest.fixture
def pack(tmp_path: Path) -> Path:
    """A minimal pack that satisfies every validator invariant."""
    (tmp_path / ".claude-plugin").mkdir()
    (tmp_path / ".claude-plugin" / "plugin.json").write_text(
        '{"name": "demo-pack", "version": "0.1.0"}\n', encoding="utf-8"
    )
    skill_dir = tmp_path / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(FRONTMATTER, encoding="utf-8")
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "demo_agent.md").write_text(FRONTMATTER, encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "# Demo pack\n\nNo API key is needed: the host coding agent translates.\n",
        encoding="utf-8",
    )
    (tmp_path / ".gitignore").write_text("outputs/\n__pycache__/\n", encoding="utf-8")
    return tmp_path


def test_valid_pack_passes(pack: Path) -> None:
    assert validate_pack(pack) == []


def test_missing_frontmatter_is_reported(pack: Path) -> None:
    (pack / "skills" / "demo" / "SKILL.md").write_text(
        "# Demo\n\nNo frontmatter here.\n", encoding="utf-8"
    )
    violations = validate_pack(pack)
    assert any("frontmatter" in v and "SKILL.md" in v for v in violations)


@pytest.mark.parametrize("field", ["name", "description"])
def test_empty_frontmatter_field_is_reported(pack: Path, field: str) -> None:
    lines = [
        "---",
        f"name: {'' if field == 'name' else 'demo'}",
        f"description: {'' if field == 'description' else 'A demo skill for validation tests'}",
        "---",
        "",
        "# Demo",
    ]
    (pack / "agents" / "demo_agent.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    violations = validate_pack(pack)
    assert any("frontmatter" in v and field in v for v in violations)


def test_malformed_plugin_manifest_is_reported(pack: Path) -> None:
    (pack / ".claude-plugin" / "plugin.json").write_text("{not valid json", encoding="utf-8")
    violations = validate_pack(pack)
    assert any("plugin" in v and "does not parse" in v for v in violations)


def test_missing_plugin_manifest_is_reported(pack: Path) -> None:
    (pack / ".claude-plugin" / "plugin.json").unlink()
    violations = validate_pack(pack)
    assert any("missing .claude-plugin/plugin.json" in v for v in violations)


def test_stale_path_in_tracked_text_file_is_reported(pack: Path) -> None:
    (pack / "README.md").write_text(f"Root: {STALE_PATH}\n", encoding="utf-8")
    violations = validate_pack(pack)
    assert any("stale path" in v and "README.md" in v for v in violations)


def test_stale_path_in_python_file_is_reported(pack: Path) -> None:
    (pack / "src").mkdir()
    (pack / "src" / "book.py").write_text(f'ROOT = "{STALE_PATH}"\n', encoding="utf-8")
    violations = validate_pack(pack)
    assert any("stale path" in v and "book.py" in v for v in violations)


@pytest.mark.parametrize(
    "relative_path",
    [
        "skills/demo/SKILL.md",
        "agents/demo_agent.md",
        "README.md",
    ],
)
def test_api_key_instruction_is_reported(pack: Path, relative_path: str) -> None:
    target = pack / relative_path
    target.write_text(
        target.read_text(encoding="utf-8")
        + "\nSet your OPENAI_API_KEY environment variable before running.\n",
        encoding="utf-8",
    )
    violations = validate_pack(pack)
    assert any("api-key instruction" in v and relative_path in v for v in violations)


def test_negated_api_key_mention_is_allowed(pack: Path) -> None:
    (pack / "skills" / "demo" / "SKILL.md").write_text(
        FRONTMATTER + "\nDo not set an API key; the host agent translates.\n",
        encoding="utf-8",
    )
    assert validate_pack(pack) == []


def test_outputs_must_be_ignored(pack: Path) -> None:
    (pack / ".gitignore").write_text("*.log\n", encoding="utf-8")
    violations = validate_pack(pack)
    assert any("outputs/ is not ignored" in v for v in violations)


def test_validator_prints_clear_violation_list_and_fails(
    pack: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (pack / "skills" / "demo" / "SKILL.md").write_text("# Broken\n", encoding="utf-8")
    (pack / "README.md").write_text(f"Root: {STALE_PATH}\n", encoding="utf-8")
    assert main(["--root", str(pack)]) == 1
    output = capsys.readouterr().out
    assert "Pack validation FAILED with" in output
    assert "1. frontmatter:" in output
    assert "2. stale path:" in output


def test_main_returns_zero_on_valid_pack(pack: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--root", str(pack)]) == 0
    assert "Pack validation PASSED" in capsys.readouterr().out


def test_validation_does_not_mutate_files(pack: Path) -> None:
    before = {p.relative_to(pack): p.read_bytes() for p in pack.rglob("*") if p.is_file()}
    validate_pack(pack)
    after = {p.relative_to(pack): p.read_bytes() for p in pack.rglob("*") if p.is_file()}
    assert before == after
