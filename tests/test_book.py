#!/usr/bin/env python3
"""
Focused tests for the book workflow (Task B).

Each test maps to a Review Focus / hard requirement:
- previous_context for chapter 2+ and no JudgeResult subscripting
- resume path carries judge_score (no KeyError)
- real consistency findings (renamed character, changed place/glossary)
- brief via build_brief, validation via validate, real registry updates
- dynamic glossary and relative project_root
- CLI --list-formats / --help without --input
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.book import REPO_ROOT, BookTranslator, _extract_placeholders
from src.pipeline import JudgeResult

VENV_PY = sys.executable
CLI = ROOT / "scripts" / "translate_book.py"


class StubPipeline:
    """Deterministic stand-in for Task A's TranslationPipeline contract."""

    def __init__(self, translation: str = "ترجمة حقيقية من المضيف"):
        self.translation = translation
        self.brief_calls = []
        self.validate_calls = []
        self.run_calls = []

    def build_brief(self, source_text, domain_hint=None, previous_context=None):
        self.brief_calls.append((source_text, domain_hint, previous_context))
        return {
            "analysis": {"word_count": len(source_text.split()), "entities": []},
            "glossary_terms": [
                {"source": "engine", "target": "محرك", "en": "engine", "ar": "محرك"}
            ],
            "placeholder_map": _extract_placeholders(source_text),
            "agent_prompts": [f"prompt-{i}" for i in range(7)],
            "style_profile": {"register": "MSA", "target_language": "ar"},
            "previous_context": previous_context,
        }

    def validate(self, host_translation, brief):
        self.validate_calls.append((host_translation, brief))
        issues = []
        for token in (brief.get("placeholder_map") or {}):
            if token not in (host_translation or ""):
                issues.append(
                    {
                        "code": "missing_placeholder",
                        "severity": "critical",
                        "detail": f"Missing verbatim placeholder: {token}",
                    }
                )
        return {
            "passed": not issues,
            "issues": issues,
            "score": 100 if not issues else 40,
        }

    def run(self, source_text, domain_hint=None, previous_context=None):
        self.run_calls.append((source_text, domain_hint, previous_context))
        return {
            "pipeline_id": "stub-pipeline",
            "translation": self.translation,
            "judge": JudgeResult(score=91, passed=True, decision="approve"),
            "approved": True,
            "iterations": 1,
        }


class NoBriefPipeline:
    """Pipeline without build_brief/validate — exercises the local fallback."""

    def analyze(self, source_text, domain_hint=None):
        return {"word_count": len(source_text.split()), "register": "MSA"}


DEFAULT_CHARACTERS = [
    {
        "name": "John Smith",
        "aliases": ["John"],
        "arabic_name": "جون سميث",
        "arabic_aliases": ["جون"],
        "pronouns": "he",
        "title": "Mr.",
        "first_chapter": 1,
        "description": "protagonist",
    }
]

DEFAULT_PLACES = [
    {
        "name": "Cairo",
        "arabic_name": "القاهرة",
        "place_type": "city",
        "description": "capital of Egypt",
    }
]


@pytest.fixture
def project(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "characters.json").write_text(
        json.dumps({"characters": DEFAULT_CHARACTERS}, ensure_ascii=False), encoding="utf-8"
    )
    (data / "places.json").write_text(
        json.dumps({"places": DEFAULT_PLACES}, ensure_ascii=False), encoding="utf-8"
    )
    return tmp_path


def make_translator(project, pipeline=None):
    return BookTranslator(
        project_root=str(project),
        output_dir=str(project / "outputs"),
        pipeline=pipeline or StubPipeline(),
    )


# ------------------------------------------------------------------
# project_root / import safety
# ------------------------------------------------------------------
def test_project_root_is_repo_relative():
    translator = BookTranslator(project_root=None)
    assert translator.project_root == REPO_ROOT
    assert "projects/translator" not in str(translator.project_root)
    # Assembled so the forbidden literal does not appear in this file.
    stale = "/data/workspace/" + "projects/translator"
    assert stale not in str(translator.project_root)


# ------------------------------------------------------------------
# prepare / build_brief
# ------------------------------------------------------------------
def test_prepare_chapter_writes_brief_using_build_brief(project, tmp_path):
    stub = StubPipeline()
    tr = make_translator(project, stub)
    src = tmp_path / "chapter_001.txt"
    src.write_text("Hello {{name}} world.", encoding="utf-8")

    info = tr.prepare_chapter(source_path=str(src), chapter_id="1")

    brief_path = Path(info["brief_path"])
    assert brief_path.exists()
    record = json.loads(brief_path.read_text(encoding="utf-8"))
    brief = record["brief"]
    assert set(["analysis", "glossary_terms", "placeholder_map", "agent_prompts", "style_profile"]).issubset(brief)
    assert "{{name}}" in brief["placeholder_map"]
    assert len(stub.brief_calls) == 1
    assert stub.brief_calls[0][0] == "Hello {{name}} world."


def test_prepare_chapter_previous_context_for_chapter_two(project, tmp_path):
    stub = StubPipeline()
    tr = make_translator(project, stub)
    src1 = tmp_path / "chapter_001.txt"
    src2 = tmp_path / "chapter_002.txt"
    src1.write_text("First chapter.", encoding="utf-8")
    src2.write_text("Second chapter.", encoding="utf-8")

    tr.prepare_chapter(source_path=str(src1), chapter_id="1")
    context = "Chapter 1 context: John Smith left Cairo."
    tr.prepare_chapter(source_path=str(src2), chapter_id="2", previous_context=context)

    assert len(stub.brief_calls) == 2
    assert stub.brief_calls[0][2] is None
    assert stub.brief_calls[1][2] == context


# ------------------------------------------------------------------
# assemble / validate
# ------------------------------------------------------------------
def test_assemble_validates_and_writes_output(project, tmp_path):
    stub = StubPipeline()
    tr = make_translator(project, stub)
    src = tmp_path / "chapter_001.txt"
    src.write_text("Hello {{name}} world.", encoding="utf-8")
    tr.prepare_chapter(source_path=str(src), chapter_id="1")

    result = tr.assemble_chapter("1", "مرحبا {{name}} بالعالم")

    assert result["passed"] is True
    assert result["judge_score"] == 100
    assert len(stub.validate_calls) == 1
    assert Path(result["output_path"]).read_text(encoding="utf-8") == "مرحبا {{name}} بالعالم"


def test_assemble_missing_placeholder_fails_with_named_error(project, tmp_path):
    tr = make_translator(project, StubPipeline())
    src = tmp_path / "chapter_001.txt"
    src.write_text("Value {{id}} must stay.", encoding="utf-8")
    tr.prepare_chapter(source_path=str(src), chapter_id="1")

    result = tr.assemble_chapter("1", "القيمة يجب أن تبقى")

    assert result["passed"] is False
    codes = [i["code"] for i in result["validation"]["issues"]]
    assert "missing_placeholder" in codes


def test_assemble_without_brief_raises_clear_error(project):
    tr = make_translator(project, StubPipeline())
    with pytest.raises(FileNotFoundError, match="--prepare"):
        tr.assemble_chapter("99", "anything")


# ------------------------------------------------------------------
# consistency — real findings
# ------------------------------------------------------------------
def test_consistency_detects_renamed_character(project):
    tr = make_translator(project, StubPipeline())
    result = tr.check_consistency(
        2,
        "جون باركر ذهب إلى المنزل.",
        source_text="John Smith went home.",
    )
    findings = result["findings"]
    assert result["consistent"] is False
    renamed = [f for f in findings if f["type"] == "renamed_character"]
    assert renamed
    assert renamed[0]["expected"] == "جون سميث"
    assert renamed[0]["found"] == "جون باركر"


def test_consistency_detects_changed_place(project):
    tr = make_translator(project, StubPipeline())
    result = tr.check_consistency(
        1,
        "زرنا مدينة أخرى.",
        source_text="We visited Cairo last year.",
    )
    changed = [f for f in result["findings"] if f["type"] == "changed_place"]
    assert changed
    assert changed[0]["expected"] == "القاهرة"


def test_consistency_detects_changed_glossary_rendering(project):
    tr = make_translator(project, StubPipeline())
    tr.dynamic_glossary = [
        {"source": "engine", "target": "محرك", "alternatives": ["موتور"]}
    ]
    result = tr.check_consistency(
        1,
        "استخدم المهندس محركا جديدا.",
        source_text="The engineer installed a new engine.",
    )
    # canonical target present -> no changed rendering finding here
    assert not [f for f in result["findings"] if f["type"] == "changed_glossary_rendering"]

    result2 = tr.check_consistency(
        1,
        "استخدم المهندس موتورا جديدا.",
        source_text="The engineer installed a new engine.",
    )
    changed = [f for f in result2["findings"] if f["type"] == "changed_glossary_rendering"]
    assert changed
    assert changed[0]["expected"] == "محرك"
    assert changed[0]["found"] == "موتور"


def test_consistency_clean_translation_has_no_findings(project):
    tr = make_translator(project, StubPipeline())
    result = tr.check_consistency(
        1,
        "ذهب جون سميث إلى القاهرة.",
        source_text="John Smith went to Cairo.",
    )
    assert result["consistent"] is True
    assert result["findings"] == []


# ------------------------------------------------------------------
# registries (real updates, dynamic glossary)
# ------------------------------------------------------------------
def test_update_registries_truly_updates_including_dynamic_glossary(project):
    tr = make_translator(project, StubPipeline())
    before = len(tr.characters)
    updates = tr.update_registries_from_chapter(
        1,
        "ترجمة",
        "Alice Wonder visited Paris. The engine is new.",
        glossary_terms=[{"source": "engine", "target": "محرك"}],
    )
    assert updates["characters_added"] >= 1
    assert len(tr.characters) > before
    assert updates["terms_added"] == 1
    assert any(t["source"] == "engine" and t["target"] == "محرك" for t in tr.dynamic_glossary)

    saved = json.loads(
        (project / "data" / "dynamic_glossary.json").read_text(encoding="utf-8")
    )
    assert saved["terms"][0]["source"] == "engine"

    # dedupe on a second call
    updates2 = tr.update_registries_from_chapter(
        2, "ترجمة", "Another sentence.",
        glossary_terms=[{"source": "engine", "target": "محرك"}],
    )
    assert updates2["terms_added"] == 0


# ------------------------------------------------------------------
# legacy run: JudgeResult dataclass must not be subscripted
# ------------------------------------------------------------------
def test_translate_chapter_uses_judge_dataclass_attribute(project, tmp_path):
    stub = StubPipeline()
    tr = make_translator(project, stub)
    src = tmp_path / "chapter_001.txt"
    src.write_text("Some source text.", encoding="utf-8")

    result = tr.translate_chapter(1, str(src))

    assert result["judge_score"] == 91
    assert result["approved"] is True
    assert result["status"] == "translated"
    assert Path(result["output_path"]).exists()


def test_resume_path_has_judge_score_without_keyerror(project, tmp_path):
    tr = make_translator(project, StubPipeline())
    src = tmp_path / "chapter_001.txt"
    src.write_text("Resumable source text.", encoding="utf-8")

    first = tr.translate_chapter(1, str(src))
    assert first["judge_score"] == 91

    # Recreate translator so the saved manifest is loaded from disk.
    tr2 = make_translator(project, StubPipeline())
    resumed = tr2.translate_chapter(1, str(src))

    assert resumed["status"] == "already_completed"
    assert resumed["judge_score"] == 91
    assert "approved" in resumed
    assert "pipeline_id" in resumed


def test_two_chapter_book_with_previous_context(project, tmp_path):
    stub = StubPipeline()
    tr = make_translator(project, stub)
    c1 = tmp_path / "chapter_001.txt"
    c2 = tmp_path / "chapter_002.txt"
    c1.write_text("Chapter one source.", encoding="utf-8")
    c2.write_text("Chapter two source.", encoding="utf-8")

    results = tr.translate_book([str(c1), str(c2)], output_dir=str(project / "outputs"))

    assert len(results) == 2
    assert all("judge_score" in r for r in results)
    assert all(r["judge_score"] == 91 for r in results)
    assert len(stub.run_calls) == 2
    assert stub.run_calls[0][2] is None
    assert stub.run_calls[1][2] is not None  # chapter 2 got previous_context


def test_translate_chapter_awaiting_host_does_not_fabricate(project, tmp_path):
    class HostRequiredPipeline(StubPipeline):
        def run(self, source_text, domain_hint=None, previous_context=None):
            return {
                "pipeline_id": "x",
                "translation": "",
                "host_agent_required": True,
                "judge": JudgeResult(score=0),
                "approved": False,
                "iterations": 1,
            }

    tr = make_translator(project, HostRequiredPipeline())
    src = tmp_path / "chapter_001.txt"
    src.write_text("Needs a host translation.", encoding="utf-8")
    result = tr.translate_chapter(1, str(src))
    assert result["status"] == "awaiting_host"
    assert result["translation"] == ""
    assert result["host_agent_required"] is True


def test_fallback_brief_and_validate_without_task_a(project, tmp_path):
    tr = make_translator(project, NoBriefPipeline())
    src = tmp_path / "chapter_001.txt"
    src.write_text("Keep {{token}} verbatim.", encoding="utf-8")
    info = tr.prepare_chapter(source_path=str(src), chapter_id="1")
    record = json.loads(Path(info["brief_path"]).read_text(encoding="utf-8"))
    assert set(["analysis", "glossary_terms", "placeholder_map", "agent_prompts", "style_profile"]).issubset(record["brief"])

    ok = tr.assemble_chapter("1", "احفظ {{token}} حرفيا")
    assert ok["passed"] is True
    bad = tr.assemble_chapter("1", "بدون العنصر")
    assert bad["passed"] is False
    assert "missing_placeholder" in [i["code"] for i in bad["validation"]["issues"]]


# ------------------------------------------------------------------
# CLI surface
# ------------------------------------------------------------------
def _run_cli(*flags):
    return subprocess.run(
        [str(VENV_PY), str(CLI), *flags],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_cli_list_formats_without_input():
    result = _run_cli("--list-formats")
    assert result.returncode == 0, result.stderr
    assert ".txt" in result.stdout
    assert ".epub" in result.stdout


def test_cli_help_without_input():
    result = _run_cli("--help")
    assert result.returncode == 0, result.stderr
    for flag in ("--prepare", "--assemble", "--list-formats", "--input", "--target", "--output", "--format"):
        assert flag in result.stdout


def test_cli_prepare_and_assemble_two_chapters(tmp_path):
    # Use an isolated project root so repo data registries are never mutated.
    project_root = tmp_path / "project"
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "characters.json").write_text(
        json.dumps({"characters": DEFAULT_CHARACTERS}, ensure_ascii=False), encoding="utf-8"
    )
    (data_dir / "places.json").write_text(
        json.dumps({"places": DEFAULT_PLACES}, ensure_ascii=False), encoding="utf-8"
    )
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "chapter_001.txt").write_text("First {{token}} chapter.", encoding="utf-8")
    (src_dir / "chapter_002.txt").write_text("Second chapter.", encoding="utf-8")
    out_dir = tmp_path / "out"
    root_flags = ("--project-root", str(project_root))

    prepared = _run_cli("--prepare", *root_flags, "--input", str(src_dir), "--output", str(out_dir))
    assert prepared.returncode == 0, prepared.stderr
    assert (out_dir / "briefs" / "chapter_001.brief.json").exists()
    assert (out_dir / "briefs" / "chapter_002.brief.json").exists()

    trans_dir = tmp_path / "translations"
    trans_dir.mkdir()
    (trans_dir / "chapter_001.txt").write_text("أول {{token}} فصل", encoding="utf-8")
    (trans_dir / "chapter_002.txt").write_text("الفصل الثاني", encoding="utf-8")

    assembled = _run_cli(
        "--assemble", *root_flags, "--translations", str(trans_dir), "--output", str(out_dir)
    )
    assert assembled.returncode == 0, assembled.stderr
    assert (out_dir / "chapters" / "chapter_001.ar.txt").exists()
    assert (out_dir / "chapters" / "chapter_002.ar.txt").exists()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
