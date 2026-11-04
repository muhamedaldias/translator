#!/usr/bin/env python3
"""
Unit tests for translation evaluation metrics.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.evaluation import TranslationEvaluator


class TestTranslationEvaluator:
    """Tests for TranslationEvaluator class."""

    def setup_method(self):
        self.eval = TranslationEvaluator()

    def test_bleu(self):
        """Test BLEU score."""
        reference = "hello world"
        hypothesis = "hello world"
        score = self.eval.bleu(reference, hypothesis)
        assert isinstance(score, float)
        assert score >= 0

        # Different text should score lower
        score2 = self.eval.bleu(reference, "goodbye universe")
        assert score >= score2

    def test_chrf(self):
        """Test chrF score."""
        reference = "مرحبا بالعالم"
        hypothesis = "مرحبا بالعالم"
        score = self.eval.chrf(reference, hypothesis)
        assert isinstance(score, float)
        assert score >= 0
        assert score <= 100

    def test_al_bleu(self):
        """Test AL-BLEU score."""
        reference = "مرحبا بالعالم"
        hypothesis = "مرحبا بالعالم"
        score = self.eval.al_bleu(reference, hypothesis)
        assert isinstance(score, float)
        assert score >= 0

    def test_tsr(self):
        """Test Term Success Rate."""
        translation = "الكمبيوتر والبرمجيات مهمة"
        glossary = [
            {"en": "computer", "ar": "الكمبيوتر"},
            {"en": "software", "ar": "البرمجيات"},
            {"en": "network", "ar": "الشبكة"},
        ]

        tsr = self.eval.tsr(translation, glossary)
        assert tsr == (2 / 3) * 100  # 2 of 3 terms found

    def test_evaluate_comprehensive(self):
        """Test comprehensive evaluation."""
        source = "Hello world"
        reference = "مرحبا بالعالم"
        hypothesis = "مرحبا بالعالم"

        result = self.eval.evaluate(source, reference, hypothesis)
        assert "bleu" in result
        assert "chrf" in result
        assert "al_bleu" in result
        assert "tsr" in result
        assert "comet_mqm" in result
        assert "overall_score" in result
        assert "passed" in result

    def test_comet_mqm_not_available(self):
        """Test COMET-MQM returns None when not installed."""
        result = self.eval.comet_mqm("source", "reference", "hypothesis")
        assert result is None


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
