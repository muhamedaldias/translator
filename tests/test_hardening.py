#!/usr/bin/env python3
"""Hardening tests: LLM client layer (mocked SDKs), glossary round-trips,
evaluation edges, pipeline LLM-path behavior, book consistency/registries.
"""
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.arabic import ArabicProcessor
from src.dictionary import DictionaryManager
from src.evaluation import TranslationEvaluator
from src.glossary import Glossary
from src.llm_client import (
    AnthropicClient,
    LLMManager,
    LLMResponse,
    LocalClient,
    OpenAIClient,
    create_llm_manager,
)
from src.pipeline import ReviewResult, TranslationPipeline


def _openai_response(content="مرحبا", finish_reason="stop", tokens=42):
    return SimpleNamespace(
        choices=[SimpleNamespace(
            message=SimpleNamespace(content=content), finish_reason=finish_reason)],
        usage=SimpleNamespace(total_tokens=tokens),
    )


@pytest.fixture
def fake_openai(monkeypatch):
    mod = types.ModuleType("openai")
    state = {"response": _openai_response(), "init_kwargs": None}

    class FakeOpenAI:
        def __init__(self, **kw):
            state["init_kwargs"] = kw
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=lambda **kw: state["response"]))

    mod.OpenAI = FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", mod)
    return state


@pytest.fixture
def fake_anthropic(monkeypatch):
    mod = types.ModuleType("anthropic")

    class FakeAnthropic:
        def __init__(self, **kw):
            self.messages = SimpleNamespace(create=lambda **kw: SimpleNamespace(
                content=[SimpleNamespace(text="مرحبا")],
                usage=SimpleNamespace(input_tokens=10, output_tokens=5),
                stop_reason="end_turn"))

    mod.Anthropic = FakeAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", mod)
    return mod


class TestLLMClients:
    def test_openai_complete(self, fake_openai):
        c = OpenAIClient(api_key="test-key")
        assert c.is_available() is True
        r = c.complete([{"role": "user", "content": "hi"}])
        assert r.content == "مرحبا" and r.provider == "openai"
        assert r.tokens_used == 42 and r.latency_ms >= 0
        assert fake_openai["init_kwargs"]["timeout"] == 60.0

    def test_openai_truncation_flag(self, fake_openai):
        fake_openai["response"] = _openai_response(finish_reason="length")
        r = OpenAIClient(api_key="k").complete([{"role": "user", "content": "hi"}])
        assert r.finish_reason == "length"

    def test_openai_no_key_unavailable(self):
        c = OpenAIClient(api_key=None)
        c.api_key = None
        assert c.is_available() is False

    def test_anthropic_complete(self, fake_anthropic):
        c = AnthropicClient(api_key="test-key")
        r = c.complete([
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
        ])
        assert r.content == "مرحبا" and r.provider == "anthropic"
        assert r.tokens_used == 15 and r.finish_reason == "end_turn"

    def test_local_complete(self, fake_openai):
        c = LocalClient(api_key=None, base_url="http://localhost:11434/v1")
        r = c.complete([{"role": "user", "content": "hi"}])
        assert r.provider == "local"

    def test_local_parse_defaults(self):
        assert LocalClient(base_url="http://localhost:11434/v1")._parse_host_port() == ("localhost", 11434)
        assert LocalClient(base_url="https://example.com/v1")._parse_host_port() == ("example.com", 443)


class TestLLMManager:
    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError):
            LLMManager(provider="nonexistent")

    def test_no_provider_available_raises(self):
        m = LLMManager(provider="openai", api_key=None)
        m.primary.api_key = None
        with pytest.raises(RuntimeError):
            m.complete([{"role": "user", "content": "hi"}])

    def test_fallback_used_on_primary_error(self):
        m = create_llm_manager(provider="openai", api_key="k", fallback_provider="anthropic")
        m.primary = SimpleNamespace(
            is_available=lambda: True,
            complete=lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("primary down")))
        m.fallback = SimpleNamespace(
            is_available=lambda: True,
            complete=lambda *a, **kw: LLMResponse(content="fallback", model="m", provider="anthropic"))
        r = m.complete([{"role": "user", "content": "hi"}])
        assert r.content == "fallback"

    def test_primary_error_propagates_without_fallback(self):
        m = LLMManager(provider="openai", api_key="k")
        m.primary = SimpleNamespace(
            is_available=lambda: True,
            complete=lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))
        with pytest.raises(RuntimeError, match="boom"):
            m.complete([{"role": "user", "content": "hi"}])

    def test_get_status(self):
        m = LLMManager(provider="openai", api_key="k")
        s = m.get_status()
        assert s["primary"]["provider"] == "openai" and s["fallback"] is None


class TestPipelineLLMPath:
    def _pipeline(self, content, finish_reason="stop"):
        p = TranslationPipeline()
        p.use_llm = True
        p.llm = SimpleNamespace(
            primary=SimpleNamespace(model="stub-model"), provider="openai",
            complete=lambda **kw: LLMResponse(
                content=content, model="stub-model", provider="openai",
                finish_reason=finish_reason))
        return p

    def test_truncation_flagged(self):
        p = self._pipeline("نص", finish_reason="length")
        t = p.translate("Hello", p.analyze("Hello"))
        assert any(f["term"] == "__truncated__" for f in t.confidence_flags)

    def test_code_blocks_restored_llm_path(self):
        p = self._pipeline("ترجمة ___CODE_BLOCK_0___ نهاية")
        t = p.translate("Use `foo()` now", p.analyze("Use `foo()` now"))
        assert "`foo()`" in t.draft_translation
        assert "___CODE_BLOCK" not in t.draft_translation

    def test_revise_restores_blocks(self):
        p = self._pipeline("مراجع ___CODE_BLOCK_0___")
        a = p.analyze("Use `foo()` now")
        revised = p._revise("قديم", "Use `foo()` now", ReviewResult(), a)
        assert "`foo()`" in revised

    def test_judge_iteration_cap(self):
        p = TranslationPipeline()
        r = ReviewResult()
        r.overall_score = 75
        r.dimension_scores = {k: 75 for k in
                              ("accuracy", "fluency", "style_register", "terminology", "coherence")}
        j = p.judge("نص", r, iteration=3)
        assert j.decision == "retranslate" and j.passed is False

    def test_context_manager(self):
        with TranslationPipeline() as p:
            res = p.run("Hello")
            assert res["translation"]


class TestGlossaryRoundTrips:
    def test_utx_roundtrip(self, tmp_path):
        utx = tmp_path / "g.utx"
        utx.write_text("# header\ncomputer\tحاسوب\nsoftware\tبرمجيات\n", encoding="utf-8")
        g = Glossary(str(utx))
        assert len(g) == 2
        out = tmp_path / "out.utx"
        g.save(str(out))
        assert len(Glossary(str(out))) == 2

    def test_json_roundtrip_and_queries(self, tmp_path):
        p = tmp_path / "g.json"
        p.write_text(json.dumps([{"en": "computer", "ar": "حاسوب"}]), encoding="utf-8")
        g = Glossary(str(p))
        assert g.get("computer") == "حاسوب"
        assert g.get_reverse("حاسوب") == "computer"
        assert "computer" in g and "COMPUTER" in g
        g.add_term("server", "خادم", domain="tech")
        out = tmp_path / "out.json"
        g.save(str(out))
        g2 = Glossary(str(out))
        assert len(g2) == 2 and g2.get("server") == "خادم"

    def test_unsupported_extension_raises(self, tmp_path):
        f = tmp_path / "g.xyz"
        f.write_text("x", encoding="utf-8")
        with pytest.raises(ValueError):
            Glossary(str(f))

    def test_oversized_file_raises(self, tmp_path):
        f = tmp_path / "big.tbx"
        with open(f, "wb") as fh:
            fh.truncate(50 * 1024 * 1024 + 1)  # sparse file
        with pytest.raises(ValueError):
            Glossary(str(f))

    def test_adherence_no_relevant_terms_is_100(self):
        g = Glossary(str(REPO / "data" / "glossary.tbx"))
        assert g.check_adherence("نص عادي", source_text="plain text") == 100.0


class TestEvaluationEdges:
    def test_tsr_empty_glossary(self):
        assert TranslationEvaluator().tsr("نص", []) == 100.0

    def test_chrf_empty(self):
        assert TranslationEvaluator().chrf("", "") == 0.0

    def test_bleu_empty(self):
        e = TranslationEvaluator()
        assert e.bleu("", "x") == 0.0 and e._simple_bleu("x", "") == 0.0

    def test_al_bleu_identical(self):
        e = TranslationEvaluator()
        assert e.al_bleu("مرحبا بالعالم", "مرحبا بالعالم") == pytest.approx(100.0)

    def test_evaluate_with_glossary(self):
        e = TranslationEvaluator()
        r = e.evaluate("computer", "حاسوب", "حاسوب",
                       glossary_terms=[{"en": "computer", "ar": "حاسوب"}])
        assert r["tsr"] == 100.0 and r["passed"] is True


class TestBookConsistency:
    def _translator(self, tmp_path):
        from src.book import BookTranslator
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "characters.json").write_text(json.dumps({
            "characters": [{
                "name": "John Smith", "aliases": ["John"],
                "arabic_name": "جون سميث", "arabic_aliases": ["جون"],
                "pronouns": "he", "title": "Mr.", "first_chapter": 1,
                "description": "",
            }]}), encoding="utf-8")
        return BookTranslator(project_root=str(tmp_path))

    def test_alias_used_flagged(self, tmp_path):
        bt = self._translator(tmp_path)
        res = bt.check_consistency(1, "ذهب جون إلى السوق")
        assert res["consistent"] is False
        assert res["inconsistencies"][0]["expected"] == "جون سميث"

    def test_canonical_used_ok(self, tmp_path):
        bt = self._translator(tmp_path)
        assert bt.check_consistency(1, "ذهب جون سميث إلى السوق")["consistent"] is True

    def test_registry_skips_sentence_initial(self, tmp_path):
        bt = self._translator(tmp_path)
        bt.update_registries_from_chapter(1, "", "The dog saw John Smith. He ran.")
        names = [c["name"] for c in bt.characters]
        assert "John Smith" in names
        assert "The" not in names and "He" not in names


class TestArabicExtras:
    def test_restore_order_independent(self):
        proc = ArabicProcessor()
        text = "A `x` B `y` C"
        protected, blocks = proc.protect_code_blocks(text)
        swapped = protected.replace("___CODE_BLOCK_0___", "TMP0").replace(
            "___CODE_BLOCK_1___", "___CODE_BLOCK_0___").replace("TMP0", "___CODE_BLOCK_1___")
        restored = proc.restore_code_blocks(swapped, blocks)
        assert '`x`' in restored and '`y`' in restored

    def test_format_plural_dual(self):
        proc = ArabicProcessor()
        assert proc.format_plural("كتاب", 1) == "كتاب"
        assert proc.format_plural("كتاب", 2, dual="كتابان") == "كتابان"
        assert "(few)" in proc.format_plural("كتاب", 5)

    def test_transliterate_placeholder(self):
        assert ArabicProcessor().transliterate_to_arabic("Smith") == "[Smith]"

    def test_is_named_entity(self):
        proc = ArabicProcessor()
        assert proc.is_named_entity("John Smith") is True
        assert proc.is_named_entity("the dog") is False

    def test_marker_collision_safe(self):
        proc = ArabicProcessor()
        text = "literal ___CODE_BLOCK_0___ and `code`"
        protected, blocks = proc.protect_code_blocks(text)
        assert proc.restore_code_blocks(protected, blocks) == text


class TestDictionaryEdges:
    def test_lookup_unknown_source(self, tmp_path):
        dm = DictionaryManager(data_dir=str(tmp_path / "d"), cache_dir=str(tmp_path / "c"))
        try:
            assert dm.lookup_synonyms("x", source="unknown") == []
            assert dm.lookup_en_ar("x", direction="unknown") == []
            assert dm.lookup_definition("x", dictionary="unknown") is None
            entry = dm.lookup_definition("computer", dictionary="wordnet")
            assert entry is not None and entry.word == "computer"
            assert isinstance(dm.get_relevant_terms("computer software"), list)
        finally:
            dm.close()


class TestCoverageBoost:
    def test_text_reconstruct_roundtrip(self, tmp_path):
        from src.book_formats import TextHandler
        src = tmp_path / "b.txt"
        src.write_text("Hello world.\n\nSecond paragraph.\n", encoding="utf-8")
        h = TextHandler()
        st = h.parse(str(src))
        out = tmp_path / "out.txt"
        h.reconstruct(st, {s.id: "مرحبا" for s in st.segments}, str(out))
        assert out.read_text(encoding="utf-8") == "مرحبا\n\nمرحبا"

    def test_get_handler_unknown_raises(self):
        from src.book_formats import get_handler, list_supported_formats
        with pytest.raises(ValueError):
            get_handler("book.xyz")
        assert ".epub" in list_supported_formats()

    def test_epub_import_error_message(self, tmp_path, monkeypatch):
        from src.book_formats import EPUBHandler
        monkeypatch.setitem(sys.modules, "ebooklib", None)
        with pytest.raises(ImportError, match="ebooklib"):
            EPUBHandler().parse(str(tmp_path / "b.epub"))

    def test_docx_import_error_message(self, tmp_path, monkeypatch):
        from src.book_formats import DOCXHandler
        monkeypatch.setitem(sys.modules, "docx", None)
        with pytest.raises(ImportError, match="python-docx"):
            DOCXHandler().parse(str(tmp_path / "b.docx"))

    def test_pdf_import_error_message(self, tmp_path, monkeypatch):
        from src.book_formats import PDFHandler
        monkeypatch.setitem(sys.modules, "pypdf", None)
        monkeypatch.setitem(sys.modules, "PyPDF2", None)
        with pytest.raises(ImportError, match="pypdf"):
            PDFHandler().parse(str(tmp_path / "b.pdf"))

    def test_wordnet_json_resource(self, tmp_path):
        data = tmp_path / "d"
        (data / "wordnet").mkdir(parents=True)
        (data / "wordnet" / "english-wordnet.json").write_text(
            json.dumps({"computer": {"synonyms": ["machine"], "definition": "a device"}}),
            encoding="utf-8")
        dm = DictionaryManager(data_dir=str(data), cache_dir=str(tmp_path / "c"))
        try:
            assert dm.wordnet_synonyms("computer") == ["machine"]
            assert dm.wordnet_definition("computer") == "a device"
        finally:
            dm.close()

    def test_wiktionary_reverse_lookup(self, tmp_path):
        data = tmp_path / "d"
        (data / "wiktionary").mkdir(parents=True)
        (data / "wiktionary" / "en-ar.json").write_text(
            json.dumps({"computer": ["حاسوب"]}), encoding="utf-8")
        dm = DictionaryManager(data_dir=str(data), cache_dir=str(tmp_path / "c"))
        try:
            assert dm.wiktionary_ar_en("حاسوب") == ["computer"]
        finally:
            dm.close()

    def test_merriam_webster_mocked(self, tmp_path, monkeypatch):
        import src.dictionary as dmod
        dm = DictionaryManager(data_dir=str(tmp_path / "d"), cache_dir=str(tmp_path / "c"),
                               merriam_webster_key="test-key")
        try:
            class Resp:
                status_code = 200
                def json(self):
                    return [{"fl": "noun", "shortdef": ["a computing device"]}]
            monkeypatch.setattr(dmod.requests, "get", lambda *a, **kw: Resp())
            entry = dm.merriam_webster_definition("computer")
            assert entry is not None and entry.definition == "a computing device"
            # second call served from cache
            entry2 = dm.merriam_webster_definition("computer")
            assert entry2 is not None and entry2.source == "merriam_webster"
        finally:
            dm.close()

    def test_cache_expiry(self, tmp_path):
        dm = DictionaryManager(data_dir=str(tmp_path / "d"), cache_dir=str(tmp_path / "c"))
        try:
            dm._cache_set("k", ["v"], ttl_seconds=-1)
            assert dm._cache_get("k") is None
        finally:
            dm.close()

    def test_detect_register_dialect(self):
        proc = ArabicProcessor()
        assert proc.detect_register("شو كيفك يا wallah يا ريت") == "dialect"

    def test_diacritics_policy_optional_and_unknown(self):
        proc = ArabicProcessor()
        proc.diacritics_policy = "optional"
        assert proc.apply_diacritics_policy("مُسْلِمٌ") == "مسلم"
        proc.diacritics_policy = "weird"
        assert proc.apply_diacritics_policy("نص") == "نص"

    def test_chrf_word_order_only(self):
        e = TranslationEvaluator()
        s = e.chrf("the cat sat", "the cat sat", char_order=0, word_order=2)
        assert s == pytest.approx(100.0)

    def test_normalize_disabled(self):
        proc = ArabicProcessor()
        proc.orthography_normalization = False
        assert proc.normalize_orthography("أحمد") == "أحمد"

    def test_book_context_manager(self, tmp_path):
        from src.book import BookTranslator
        with BookTranslator(project_root=str(tmp_path)) as bt:
            assert bt.get_status()["total_chapters"] == 0