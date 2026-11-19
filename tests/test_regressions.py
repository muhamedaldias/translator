#!/usr/bin/env python3
"""Regression tests for audited defects (ECC audit 2026-11-19).

RED phase: these encode correct behavior and FAIL on the audited commit.
Each test references the finding ID it guards (see /data/workspace/translator-audit/findings.md).
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.arabic import ArabicProcessor
from src.dictionary import DictionaryManager
from src.evaluation import TranslationEvaluator
from src.glossary import Glossary
from src.pipeline import ReviewResult, TranslationPipeline


# ---------------------------------------------------------------- F2: dictionary
class TestDictionaryShadowing:
    def _manager(self, tmp_path):
        data = tmp_path / "data"
        (data / "wiktionary").mkdir(parents=True)
        (data / "wiktionary" / "en-ar.json").write_text(
            json.dumps({"computer": ["حاسوب"]}), encoding="utf-8")
        (data / "roget").mkdir(parents=True)
        (data / "roget" / "synonyms.json").write_text(
            json.dumps({"computer": ["machine"]}), encoding="utf-8")
        return DictionaryManager(data_dir=str(data), cache_dir=str(tmp_path / "cache"))

    def test_lookup_en_ar_callable(self, tmp_path):
        dm = self._manager(tmp_path)
        try:
            assert dm.lookup_en_ar("computer") == ["حاسوب"]
        finally:
            dm.close()

    def test_lookup_synonyms_roget(self, tmp_path):
        dm = self._manager(tmp_path)
        try:
            assert dm.lookup_synonyms("computer", source="roget") == ["machine"]
        finally:
            dm.close()

    def test_lookup_synonyms_all(self, tmp_path):
        dm = self._manager(tmp_path)
        try:
            syns = dm.lookup_synonyms("computer", source="all")
            assert isinstance(syns, list) and "machine" in syns
        finally:
            dm.close()


# ---------------------------------------------------------------- F3/F4: book
class TestBookWorkflow:
    def test_translate_chapter_returns_score(self, tmp_path):
        from src.book import BookTranslator
        (tmp_path / "ch1.txt").write_text("John Smith went to Cairo.", encoding="utf-8")
        bt = BookTranslator(project_root=str(tmp_path))
        res = bt.translate_chapter(1, str(tmp_path / "ch1.txt"))
        assert isinstance(res["judge_score"], int)
        assert (tmp_path / "data" / "manifest.json").exists()

    def test_default_project_root_is_repo(self):
        from src.book import BookTranslator
        bt = BookTranslator()
        assert bt.project_root == REPO
        assert str(bt.project_root) != "/data/workspace/projects/translator"

    def test_book_cli_end_to_end(self, tmp_path):
        chapters = tmp_path / "chapters"
        chapters.mkdir()
        (chapters / "ch1.txt").write_text("Hello world.", encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        proc = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "translate_book.py"),
             "--input", str(chapters), "--target", "ar",
             "--output", str(tmp_path / "out"),
             "--project-root", str(tmp_path)],
            cwd=str(REPO), env=env, capture_output=True, text=True, timeout=120,
            check=False)
        assert proc.returncode == 0, proc.stderr[-2000:]


# ---------------------------------------------------------------- F5: diacritics position
class TestPostEditPositions:
    def test_diacritic_correction_position(self):
        p = TranslationPipeline()
        draft = "مُسْلِمٌ"
        res = p.post_edit(draft, p.analyze("test"))
        diac = [c for c in res.corrections if c["reason"] == "diacritics"]
        assert diac, "expected a diacritics correction"
        expected_pos = next(i for i, ch in enumerate(draft)
                            if p.arabic.DIACRITICS.search(ch))
        stripped = p.arabic.remove_diacritics(draft)
        assert diac[0]["position"] == expected_pos
        assert diac[0]["original"] == draft[expected_pos:expected_pos + 20]
        assert diac[0]["corrected"] == stripped[expected_pos:expected_pos + 20]

    def test_output_orthography_preserved(self):
        # F20: lossy normalization belongs in analysis, not in final output
        p = TranslationPipeline()
        res = p.post_edit("أحمد ذهب إلى المدرسة", p.analyze("test"))
        assert "أحمد" in res.revised_translation


# ---------------------------------------------------------------- F6: judge gate
class TestJudgeIntegrity:
    def _pipeline_with_llm(self, payload):
        p = TranslationPipeline()
        p.use_llm = True
        p.llm = object()  # truthy sentinel; completion is stubbed below
        p._llm_complete = lambda **kw: payload
        return p

    def test_llm_rationale_preserved(self):
        p = self._pipeline_with_llm(
            '{"score": 90, "decision": "approve", "rationale": "UNIQUE_LLM_RATIONALE"}')
        r = ReviewResult()
        r.overall_score = 90
        r.dimension_scores = {k: 90 for k in
                              ("accuracy", "fluency", "style_register", "terminology", "coherence")}
        j = p.judge("نص", r, iteration=1)
        assert j.passed is True
        assert "UNIQUE_LLM_RATIONALE" in j.rationale

    def test_gate_not_bypassed_by_llm_approve(self):
        p = self._pipeline_with_llm(
            '{"score": 50, "decision": "approve", "rationale": "talked into it"}')
        r = ReviewResult()
        r.overall_score = 50
        r.dimension_scores = {k: 50 for k in
                              ("accuracy", "fluency", "style_register", "terminology", "coherence")}
        j = p.judge("نص", r, iteration=1)
        assert j.passed is False  # threshold is authoritative


# ---------------------------------------------------------------- F8/F9: placeholder mode
class TestPlaceholderHonesty:
    def test_run_reports_placeholder_warning(self):
        p = TranslationPipeline()
        res = p.run("Hello world")
        warnings = res.get("warnings") or []
        assert any("LLM" in w for w in warnings), "must warn that no real translation happened"

    def test_no_wasted_iterations_without_llm(self):
        p = TranslationPipeline()
        res = p.run("Hello world")
        assert res["iterations"] == 1


# ---------------------------------------------------------------- F10: CLDR plurals
class TestPluralCLDR:
    @pytest.mark.parametrize("n,expected", [
        (0, "zero"), (1, "one"), (2, "two"), (3, "few"), (10, "few"),
        (11, "many"), (99, "many"), (100, "other"), (102, "other"),
        (103, "few"), (111, "many"), (203, "few"), (300, "other"), (-3, "few"),
    ])
    def test_plural_form(self, n, expected):
        assert ArabicProcessor().get_plural_form(n) == expected


# ---------------------------------------------------------------- F11: code protection
class TestCodeProtection:
    def test_fenced_block_protected_and_restored(self):
        proc = ArabicProcessor()
        text = "Use this:\n```python\nprint('hi')\n```\nOK?"
        protected, blocks = proc.protect_code_blocks(text)
        assert any("```python" in b for b in blocks)
        assert "print" not in protected
        assert proc.restore_code_blocks(protected, blocks) == text

    def test_inline_code_roundtrip(self):
        proc = ArabicProcessor()
        text = "Call `foo(x)` and <b>bold</b> now."
        protected, blocks = proc.protect_code_blocks(text)
        assert proc.restore_code_blocks(protected, blocks) == text


# ---------------------------------------------------------------- F12: glossary
class TestGlossary:
    def test_save_preserves_tbx_format(self, tmp_path):
        import shutil
        tbx = tmp_path / "g.tbx"
        shutil.copy(REPO / "data" / "glossary.tbx", tbx)
        g = Glossary(str(tbx))
        n = len(g)
        g.save()
        head = tbx.read_text(encoding="utf-8").lstrip()
        assert head.startswith("<?xml") or head.startswith("<tbx")
        assert len(Glossary(str(tbx))) == n

    def test_namespaced_tbx_loads(self, tmp_path):
        tbx = tmp_path / "ns.tbx"
        tbx.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<tbx xmlns="urn:iso:std:iso:30042:ed-2" version="2.0" lang="en">\n'
            '  <termEntry id="1">\n'
            '    <langSec lang="en"><term>computer</term></langSec>\n'
            '    <langSec lang="ar"><term>حاسوب</term></langSec>\n'
            '  </termEntry>\n</tbx>', encoding="utf-8")
        assert len(Glossary(str(tbx))) == 1

    def test_adherence_scoped_to_source(self):
        g = Glossary(str(REPO / "data" / "glossary.tbx"))
        score = g.check_adherence("هذا حاسوب جديد", source_text="a new computer")
        assert score == 100.0

    def test_no_substring_false_positives(self):
        g = Glossary(str(REPO / "data" / "glossary.tbx"))
        assert g.get_relevant_terms("The CAPITAL city.", None) == []
        assert g.get_relevant_terms("malfunction", None) == []

    def test_case_insensitive_substitution(self):
        p = TranslationPipeline()
        a = p.analyze("The api works")
        t = p.translate("The api works", a)
        assert "واجهة برمجة التطبيقات" in t.draft_translation


# ---------------------------------------------------------------- F13: chrF
class TestChrf:
    def test_word_order_respected(self):
        e = TranslationEvaluator()
        ref, hyp = "the cat sat on the mat", "the cat sat on a rug"
        assert e.chrf(ref, hyp, word_order=0) != e.chrf(ref, hyp, word_order=2)

    def test_identical_text_scores_100(self):
        e = TranslationEvaluator()
        assert e.chrf("مرحبا بالعالم", "مرحبا بالعالم", word_order=2) == pytest.approx(100.0)


# ---------------------------------------------------------------- F14: local URL parsing
class TestLocalClientURL:
    @pytest.mark.parametrize("url,host,port", [
        ("https://api.example.com/v1", "api.example.com", 443),
        ("http://localhost:11434/v1", "localhost", 11434),
        ("http://127.0.0.1:8080", "127.0.0.1", 8080),
    ])
    def test_parse_host_port(self, url, host, port):
        from src.llm_client import LocalClient
        c = LocalClient(base_url=url)
        assert c._parse_host_port() == (host, port)


# ---------------------------------------------------------------- F15: format handlers
class TestBookFormats:
    def test_epub_escapes_translation_markup(self, tmp_path):
        epub = pytest.importorskip("ebooklib")
        from ebooklib import epub as epub_mod

        from src.book_formats import EPUBHandler
        src = tmp_path / "b.epub"
        b = epub_mod.EpubBook()
        b.set_title("T"); b.set_language("en")
        c = epub_mod.EpubHtml(title="C", file_name="c.xhtml", lang="en")
        c.content = "<html><body><p>Hello world.</p></body></html>"
        b.add_item(c); b.add_item(epub_mod.EpubNcx()); b.add_item(epub_mod.EpubNav())
        epub_mod.write_epub(str(src), b, {})
        h = EPUBHandler()
        st = h.parse(str(src))
        out = tmp_path / "b_ar.epub"
        h.reconstruct(st, {s.id: 'A & B <b>x</b>' for s in st.segments}, str(out))
        b2 = epub_mod.read_epub(str(out))
        joined = "\n".join(i.get_content().decode("utf-8", "replace")
                           for i in b2.get_items_of_type(epub.ITEM_DOCUMENT))
        assert "&lt;b&gt;" in joined
        assert "<b>x</b>" not in joined

    def test_epub_language_not_hardcoded(self, tmp_path):
        epub = pytest.importorskip("ebooklib")
        from ebooklib import epub as epub_mod

        from src.book_formats import EPUBHandler
        src = tmp_path / "b.epub"
        b = epub_mod.EpubBook()
        b.set_title("T"); b.set_language("en")
        c = epub_mod.EpubHtml(title="C", file_name="c.xhtml", lang="en")
        c.content = "<html><body><p>Hello.</p></body></html>"
        b.add_item(c); b.add_item(epub_mod.EpubNcx()); b.add_item(epub_mod.EpubNav())
        epub_mod.write_epub(str(src), b, {})
        h = EPUBHandler()
        st = h.parse(str(src))
        st.language = "en"  # caller sets target language
        out = tmp_path / "out.epub"
        h.reconstruct(st, {s.id: "Hello translated." for s in st.segments}, str(out))
        b2 = epub_mod.read_epub(str(out))
        langs = str(b2.get_metadata("DC", "language"))
        assert "en" in langs and "'ar'" not in langs

    def test_pdf_reconstruct_does_not_fake_pdf(self, tmp_path):
        from src.book_formats import BookSegment, BookStructure, PDFHandler
        st = BookStructure(title="T", format="pdf",
                           segments=[BookSegment(id="seg_0", text="Hello", chapter=1)])
        out = tmp_path / "out.pdf"
        PDFHandler().reconstruct(st, {"seg_0": "مرحبا"}, str(out))
        assert not out.exists(), "must not write plain text to a .pdf path"
        txt = out.with_suffix(".txt")
        assert txt.exists() and "مرحبا" in txt.read_text(encoding="utf-8")

    def test_docx_roundtrip_guard(self, tmp_path):
        docx = pytest.importorskip("docx")
        from src.book_formats import DOCXHandler
        d = docx.Document()
        d.add_heading("Chapter One", level=1)
        d.add_paragraph("Hello world.")
        src = tmp_path / "b.docx"; d.save(str(src))
        h = DOCXHandler()
        st = h.parse(str(src))
        out = tmp_path / "b_ar.docx"
        h.reconstruct(st, {s.id: "مرحبا" for s in st.segments}, str(out))
        d2 = docx.Document(str(out))
        assert any("مرحبا" in p.text for p in d2.paragraphs)


# ---------------------------------------------------------------- F1/F16/F18: packaging
class TestPackaging:
    def test_requirements_correct_comet_package(self):
        text = (REPO / "requirements.txt").read_text(encoding="utf-8")
        active = [line.split("#")[0].strip() for line in text.splitlines()]
        active = [line for line in active if line]
        assert not any(
            line.lower().replace("-", "_").startswith("comet_ml") for line in active
        ), "comet_ml is the wrong package (experiment tracking, not COMET-MQM)"
        assert "unbabel-comet" in text

    def test_config_no_duplicate_book_key(self):
        text = (REPO / "config" / "translator.yaml").read_text(encoding="utf-8")
        assert len(re.findall(r"^book:", text, re.MULTILINE)) == 1

    def test_license_file_exists(self):
        lic = REPO / "LICENSE"
        assert lic.exists(), "README declares MIT but no LICENSE file"
        assert "MIT" in lic.read_text(encoding="utf-8")


# ------------------------------------------------- Reviewer findings (N-series)
class TestReviewerFindings:
    def test_previous_context_does_not_crash(self):
        # N1: two-arg list.append crashed every multi-chapter book at ch2
        p = TranslationPipeline()
        res = p.run("Hello world.", previous_context="Chapter 1 translated. Score: 80.")
        assert res["translation"] != ""
        assert "error" not in res

    def test_llm_string_scores_do_not_crash(self):
        # N3: unvalidated LLM JSON types (string scores, string errors)
        p = TranslationPipeline()
        p.use_llm = True
        p.llm = object()
        p._llm_complete = lambda **kw: (
            '{"dimension_scores": {"accuracy": "90", "fluency": null}, '
            '"errors": "oops", "score": "95", "decision": "approve"}'
        )
        a = p.analyze("Hello")
        review = p.review("مرحبا", "Hello", a)  # must not raise
        assert isinstance(review.overall_score, int)
        judge = p.judge("مرحبا", review, iteration=1)
        assert isinstance(judge.score, int)

    def test_llm_failure_surfaces_not_fake(self):
        p = TranslationPipeline()
        p.use_llm = True
        p.llm = object()

        def boom(**kw):
            raise RuntimeError("401 Unauthorized")

        p._llm_complete = boom
        res = p.run("Hello world")
        assert res["approved"] is False
        assert res["translation"] == ""
        assert res.get("error")
        assert any("401" in w for w in res["warnings"])

    def test_explicit_use_llm_false_not_overridden(self, tmp_path):
        cfg = tmp_path / "c.yaml"
        cfg.write_text("llm:\n  enabled: true\n  provider: openai\n", encoding="utf-8")
        p = TranslationPipeline(config_path=str(cfg), use_llm=False)
        assert p.use_llm is False and p.llm is None

    def test_explicit_missing_config_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            TranslationPipeline(config_path=str(tmp_path / "nope.yaml"))

    def test_malformed_config_raises(self, tmp_path):
        cfg = tmp_path / "bad.yaml"
        cfg.write_text("pipeline: [unclosed", encoding="utf-8")
        with pytest.raises(ValueError):
            TranslationPipeline(config_path=str(cfg))

    def test_glossary_reload_no_duplicates(self, tmp_path):
        import shutil
        tbx = tmp_path / "g.tbx"
        shutil.copy(REPO / "data" / "glossary.tbx", tbx)
        g = Glossary(str(tbx))
        n = len(g)
        g.load(str(tbx))
        assert len(g) == n

    def test_datamuse_failure_not_negative_cached(self, tmp_path, monkeypatch):
        import src.dictionary as dmod
        dm = DictionaryManager(data_dir=str(tmp_path / "d"), cache_dir=str(tmp_path / "c"))
        try:
            calls = {"n": 0}

            class FakeResp:
                status_code = 500

            def fake_get(*a, **kw):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise OSError("network down")
                return FakeResp()

            monkeypatch.setattr(dmod.requests, "get", fake_get)
            assert dm.datamuse_synonyms("computer") == []
            # failure must NOT be cached: second call hits the network again
            assert dm.datamuse_synonyms("computer") == []
            assert calls["n"] == 2
        finally:
            dm.close()

    def test_book_resume_returns_score(self, tmp_path):
        from src.book import BookTranslator
        (tmp_path / "ch1.txt").write_text("Hello world.", encoding="utf-8")
        bt = BookTranslator(project_root=str(tmp_path))
        bt.translate_chapter(1, str(tmp_path / "ch1.txt"))
        bt.manifest[0].status = "completed"  # exercise the resume path
        bt._save_manifest()
        bt2 = BookTranslator(project_root=str(tmp_path))
        res = bt2.translate_chapter(1, str(tmp_path / "ch1.txt"))
        assert res["status"] == "already_completed"
        assert isinstance(res["judge_score"], int)  # N11: KeyError before fix
        assert "approved" in res

    def test_bleu_identical_text_both_paths(self):
        e = TranslationEvaluator()
        assert e.bleu("hello world", "hello world") >= 95.0
        assert e._simple_bleu("hello world", "hello world") >= 95.0

    def test_epub_parse_keeps_sentences_intact(self, tmp_path):
        epub = pytest.importorskip("ebooklib")
        from ebooklib import epub as epub_mod

        from src.book_formats import EPUBHandler
        src = tmp_path / "b.epub"
        b = epub_mod.EpubBook(); b.set_title("T"); b.set_language("en")
        c = epub_mod.EpubHtml(title="C", file_name="c.xhtml", lang="en")
        c.content = "<html><body><p>Hello &amp; welcome to <em>the</em> world.</p></body></html>"
        b.add_item(c); b.add_item(epub_mod.EpubNcx()); b.add_item(epub_mod.EpubNav())
        epub_mod.write_epub(str(src), b, {})
        st = EPUBHandler().parse(str(src))
        texts = [s.text for s in st.segments]
        assert any("Hello & welcome to the world." in t for t in texts)

    def test_text_handler_fenced_code_and_chapters(self, tmp_path):
        from src.book_formats import TextHandler
        md = tmp_path / "b.md"
        md.write_text(
            "# Chapter One\n\nFirst paragraph.\n\n```python\nprint('hi')\n```\n",
            encoding="utf-8",
        )
        st = TextHandler().parse(str(md))
        by_type = {s.segment_type: s for s in st.segments}
        assert "code_block" in by_type
        assert by_type["code_block"].text.startswith("```python")
        headings = [s for s in st.segments if s.segment_type == "heading"]
        assert headings[0].chapter == 1

    def test_book_epub_end_to_end(self, tmp_path):
        epub = pytest.importorskip("ebooklib")
        from ebooklib import epub as epub_mod

        from src.book import BookTranslator
        src = tmp_path / "book.epub"
        b = epub_mod.EpubBook(); b.set_title("T"); b.set_language("en")
        c = epub_mod.EpubHtml(title="C", file_name="c.xhtml", lang="en")
        c.content = "<html><body><p>Hello world.</p></body></html>"
        b.add_item(c); b.add_item(epub_mod.EpubNcx()); b.add_item(epub_mod.EpubNav())
        epub_mod.write_epub(str(src), b, {})
        bt = BookTranslator(project_root=str(tmp_path))
        res = bt.translate_chapter(1, str(src))
        assert isinstance(res["judge_score"], int)
        out = Path(res["output_path"])
        assert out.exists() or out.with_suffix(".txt").exists()