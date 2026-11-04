#!/usr/bin/env python3
"""
Unit tests for the translation pipeline.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.pipeline import TranslationPipeline, AnalysisResult, TranslationResult


class TestTranslationPipeline:
    """Tests for TranslationPipeline class."""

    def setup_method(self):
        self.pipeline = TranslationPipeline(source_lang="en", target_lang="ar")

    def test_analyze(self):
        """Test analysis stage."""
        result = self.pipeline.analyze("Hello world", domain_hint="general")
        assert isinstance(result, AnalysisResult)
        assert result.register == "MSA"
        assert result.domain == "general"
        assert result.word_count == 2
        assert result.has_rtl is False

    def test_analyze_arabic(self):
        """Test analysis with Arabic text."""
        result = self.pipeline.analyze("مرحبا بالعالم")
        assert result.has_rtl is True

    def test_translate(self):
        """Test translation stage."""
        analysis = self.pipeline.analyze("Hello world", domain_hint="general")
        result = self.pipeline.translate("Hello world", analysis)
        assert isinstance(result, TranslationResult)
        assert result.draft_translation != ""

    def test_post_edit(self):
        """Test post-edit stage."""
        analysis = self.pipeline.analyze("Hello world", domain_hint="general")
        result = self.pipeline.post_edit("مرحبا بالعالم", analysis)
        assert result.revised_translation != ""
        assert isinstance(result.corrections, list)

    def test_review(self):
        """Test review stage."""
        analysis = self.pipeline.analyze("Hello world", domain_hint="general")
        review = self.pipeline.review("مرحبا بالعالم", "Hello world", analysis)
        assert isinstance(review.overall_score, int)
        assert 0 <= review.overall_score <= 100
        assert review.recommendation in ("approve", "revise", "retranslate")

    def test_judge(self):
        """Test judge stage."""
        from src.pipeline import ReviewResult

        review = ReviewResult()
        review.overall_score = 90
        review.dimension_scores = {
            "accuracy": 85,
            "fluency": 88,
            "style_register": 90,
            "terminology": 92,
            "coherence": 88,
        }

        judge = self.pipeline.judge("ترجمة جيدة", review, iteration=1)
        assert judge.decision == "approve"
        assert judge.passed is True
        assert judge.score == 90

    def test_judge_low_score(self):
        """Test judge with low score."""
        from src.pipeline import ReviewResult

        review = ReviewResult()
        review.overall_score = 50
        review.dimension_scores = {
            "accuracy": 50,
            "fluency": 50,
            "style_register": 50,
            "terminology": 50,
            "coherence": 50,
        }

        judge = self.pipeline.judge("ترجمة سيئة", review, iteration=1)
        assert judge.decision in ("revise", "retranslate")

    def test_full_pipeline(self):
        """Test full pipeline run."""
        result = self.pipeline.run("Hello world", domain_hint="general")
        assert "pipeline_id" in result
        assert "translation" in result
        assert "judge" in result
        assert "approved" in result
        assert "iterations" in result

    def test_pipeline_threshold(self):
        """Test that threshold is respected."""
        assert self.pipeline.quality_threshold == 85
        assert self.pipeline.max_iterations == 3


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
