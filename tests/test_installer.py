"""End-to-end test: the installer ships everything the installed prompts use."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_installer_ships_runtime_dependencies(tmp_path: Path) -> None:
    dest = tmp_path / "host"
    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / "install.sh"), "--host", "generic", "--dest", str(dest)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr

    base = dest / ".agents"
    expected = [
        "skills/translator-skill/SKILL.md",
        "skills/reference-skills/SKILL.md",
        "agents/analysis_agent.md",
        "agents/translator_agent.md",
        "agents/posteditor_agent.md",
        "agents/reviewer_agent.md",
        "agents/editor_agent.md",
        "agents/judge_agent.md",
        "agents/consistency_agent.md",
        "docs/style-guide.md",
        "config/translator.yaml",
        "data/glossary.tbx",
        "data/characters.json",
        "data/places.json",
        "src/pipeline.py",
        "src/glossary.py",
        "src/arabic.py",
        "src/dictionary.py",
        "src/evaluation.py",
        "src/book.py",
        "src/book_formats.py",
        "scripts/translate_book.py",
        "scripts/install.sh",
        "scripts/install_skill.sh",
        "commands/translate.md",
        ".claude-plugin/plugin.json",
        "data/manifest.json",
        "requirements.txt",
        "requirements-optional.txt",
    ]
    missing = [name for name in expected if not (base / name).is_file()]
    assert not missing, f"installer omitted: {missing}"
