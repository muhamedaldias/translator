#!/usr/bin/env python3
"""Unit tests for translation evaluation metrics (offline, deterministic)."""

import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.evaluation import TranslationEvaluator


class TestTranslationEvaluator:
    """Tests for TranslationEvaluator class."""

    def setup_method(self):
        self.eval = TranslationEvaluator()

    def test_bleu(self):
        score = self.eval.bleu("hello world", "hello world")
        assert isinstance(score, float) and score >= 0
        assert score >= self.eval.bleu("hello world", "goodbye universe")

    # --- Review Focus / audit: identical strings == 100 ---------------
    def test_bleu_identical_strings_is_exactly_100(self):
        assert self.eval.bleu("hello world", "hello world") == 100.0
        assert self.eval.bleu("مرحبا بالعالم", "مرحبا بالعالم") == 100.0

    def test_bleu_fallback_without_nltk_identical_is_100(self, monkeypatch):
        import src.evaluation as evaluation_module
        monkeypatch.setattr(evaluation_module, "nltk", None)
        ev = TranslationEvaluator()
        assert ev.smoothing is None
        assert ev.bleu("hello world", "hello world") == 100.0
        assert ev.bleu("hello world", "other words") < 100.0

    def test_chrf(self):
        score = self.eval.chrf("مرحبا بالعالم", "مرحبا بالعالم")
        assert isinstance(score, float) and 0 <= score <= 100

    def test_chrf_word_order_honoured(self):
        ref = "alpha beta gamma delta"
        hyp = "delta gamma beta alpha"
        char_only = self.eval.chrf(ref, hyp, word_order=0)
        with_words = self.eval.chrf(ref, hyp, word_order=2)
        assert char_only != with_words
        assert with_words < char_only
        # Identical strings score 100 regardless of the word component.
        assert self.eval.chrf(ref, ref, word_order=2) == 100.0

    def test_al_bleu_is_documented_deterministic_blend(self):
        ref, hyp = "a b c", "a b c"
        expected = 0.4 * self.eval.bleu(ref, hyp) + 0.6 * self.eval.chrf(ref, hyp, word_order=0)
        assert abs(self.eval.al_bleu(ref, hyp) - expected) < 1e-9
        assert self.eval.al_bleu(ref, hyp) == 100.0
        assert (self.eval.AL_BLEU_BLEU_WEIGHT, self.eval.AL_BLEU_CHRF_WEIGHT) == (0.4, 0.6)

    def test_tsr(self):
        translation = "الكمبيوتر والبرمجيات مهمة"
        glossary = [
            {"en": "computer", "ar": "الكمبيوتر"},
            {"en": "software", "ar": "البرمجيات"},
            {"en": "network", "ar": "الشبكة"},
        ]
        assert self.eval.tsr(translation, glossary) == (2 / 3) * 100

    def test_evaluate_comprehensive(self):
        result = self.eval.evaluate("Hello world", "مرحبا بالعالم", "مرحبا بالعالم")
        for key in ("bleu", "chrf", "al_bleu", "tsr", "comet_mqm", "overall_score", "passed"):
            assert key in result
        assert "comet_mqm_status" in result

    # --- Review Focus: COMET optional and honest, no network ----------
    def test_comet_mqm_returns_none_without_local_model(self, monkeypatch):
        import importlib.util

        monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
        monkeypatch.delenv("COMET_MODEL_PATH", raising=False)
        ev = TranslationEvaluator()
        assert ev.comet_mqm("source", "reference", "hypothesis") is None
        assert ev.comet_status in ("not_installed", "no_local_model")

    def test_import_succeeds_when_optional_deps_missing(self):
        # Importing the module must never require COMET or a model download.
        module = importlib.import_module("src.evaluation")
        assert hasattr(module, "TranslationEvaluator")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
