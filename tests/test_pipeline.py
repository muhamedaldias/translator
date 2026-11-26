#!/usr/bin/env python3
"""Unit tests for the deterministic, key-free translation pipeline."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.pipeline import AnalysisResult, ReviewResult, TranslationPipeline, TranslationResult

SOURCE = (
    'Chapter 1. Alice met Bob in Paris. Use {{api_key}} and `code --flag <x>` '
    'with <tag attr="v"> plus {"id": 7} and ${VAR}. She said: "مرحبا بالعالم".'
)
SPANS = [
    "{{api_key}}",
    "`code --flag <x>`",
    '<tag attr="v">',
    '{"id": 7}',
    "${VAR}",
]
ROLES = [
    "analysis", "translator", "postedit", "reviewer", "editor", "judge", "consistency"
]


def _pipeline(tmp_path=None, config_text=None):
    kwargs = {}
    if tmp_path is not None:
        cfg = tmp_path / "config.yaml"
        cfg.write_text(config_text or "", encoding="utf-8")
        kwargs["config_path"] = str(cfg)
    return TranslationPipeline(source_lang="en", target_lang="ar", **kwargs)


class TestTranslationPipeline:
    def setup_method(self):
        self.pipeline = _pipeline()

    def teardown_method(self):
        self.pipeline.close()

    # --- Basic analysis -------------------------------------------------
    def test_analyze(self):
        result = self.pipeline.analyze("Hello world", domain_hint="general")
        assert isinstance(result, AnalysisResult)
        assert result.register == "MSA"
        assert result.domain == "general"
        assert result.word_count == 2
        assert result.has_rtl is False

    def test_analyze_arabic(self):
        assert self.pipeline.analyze("مرحبا بالعالم").has_rtl is True

    # --- Review Focus: empty / whitespace source ------------------------
    def test_empty_source_analysis_has_zero_counts(self):
        for text in ("", "   \n\t "):
            result = self.pipeline.analyze(text)
            assert result.word_count == 0
            assert result.sentence_count == 0
            assert result.entities == []
            assert result.code_blocks == []
            assert result.difficult_terms == []
            assert result.gender_context["subject_gender"] == "neutral"

    def test_empty_source_still_builds_brief(self):
        brief = self.pipeline.build_brief("   ")
        assert set(["analysis", "glossary_terms", "placeholder_map", "agent_prompts", "style_profile"]) <= set(brief)
        assert len(brief["agent_prompts"]) == 7

    # --- Review Focus: real entities / gender / code blocks -------------
    def test_analyze_populates_entities_gender_and_code_blocks(self):
        result = self.pipeline.analyze(SOURCE, domain_hint="technical")
        texts = [e["text"] for e in result.entities]
        assert "Alice" in texts and "Bob" in texts and "Paris" in texts
        assert result.gender_context["subject_gender"] == "female"
        assert result.gender_context["object_gender"] == "neutral"
        assert result.code_blocks == SPANS
        assert result.register == "MSA"

    def test_analyze_arabic_dialect_overrides_default_register(self):
        result = self.pipeline.analyze("شو أخبارك؟ كيفك؟")
        assert result.register == "dialect"

    def test_code_blocks_detected_in_indented_paragraph(self):
        text = "    <para id=\"7\">hello</para>\n\t{{token}}"
        assert self.pipeline.analyze(text).code_blocks == [
            "<para id=\"7\">", "</para>", "{{token}}"
        ]

    # --- Review Focus: build_brief preserves all protected spans --------
    def test_build_brief_returns_seven_ordered_prompts(self):
        brief = self.pipeline.build_brief(SOURCE, domain_hint="technical")
        assert list(brief["agent_prompts"].keys()) == ROLES
        assert len(brief["agent_prompts"]) == 7
        # Both dict-style and list-style access work for host agents.
        assert [p["role"] for p in brief["agent_prompts"]] == ROLES
        assert brief["agent_prompts"][0]["role"] == "analysis"
        assert all(brief["agent_prompts"][role].strip() for role in ROLES)
        assert brief["style_profile"]["target_register"] == "MSA"
        assert brief["style_profile"]["diacritics_policy"] == "remove"

    def test_build_brief_placeholder_map_is_verbatim(self):
        brief = self.pipeline.build_brief(SOURCE, domain_hint="technical")
        assert list(brief["placeholder_map"].values()) == SPANS
        for span in SPANS:
            assert span in brief["agent_prompts"]["translator"]
        assert all("preserve" in brief["agent_prompts"][role].lower() for role in ROLES)

    def test_previous_context_does_not_raise(self):
        brief = self.pipeline.build_brief(
            SOURCE, domain_hint="literary", previous_context="Chapter 0 introduced Alice."
        )
        assert "Chapter 0 introduced Alice." in brief["agent_prompts"]["translator"]
        result = self.pipeline.translate(SOURCE, self.pipeline.analyze(SOURCE), previous_context="Chapter 0")
        assert isinstance(result, TranslationResult)

    # --- Review Focus: validation catches missing placeholders ----------
    def test_validate_accepts_full_host_translation(self):
        brief = self.pipeline.build_brief(SOURCE, domain_hint="technical")
        translation = "الفصل 1. " + " ".join(SPANS) + " الحاسوب جاهز"
        validation = self.pipeline.validate(translation, brief)
        assert validation["passed"] is True
        assert validation["issues"] == []
        assert validation["score"] == 100.0

    def test_validate_missing_placeholder_is_named_issue(self):
        brief = self.pipeline.build_brief(SOURCE, domain_hint="technical")
        translation = "الفصل 1. " + " ".join(SPANS[:-1])
        validation = self.pipeline.validate(translation, brief)
        assert validation["passed"] is False
        assert any(i["name"] == "missing_placeholder" for i in validation["issues"])
        assert any("${VAR}" in str(i) for i in validation["issues"])
        assert validation["score"] < 100

    def test_validate_checks_glossary_msa_and_diacritics(self):
        source = "The computer is ready. Alice said مرحبا."
        brief = self.pipeline.build_brief(source, domain_hint="technology")
        bad = "شو أخبارك؟ الحاسوب مُسْلِمٌ جاهز"
        validation = self.pipeline.validate(bad, brief)
        names = {i["name"] for i in validation["issues"]}
        assert "diacritics_present" in names
        assert "register_not_msa" in names
        assert "empty_translation" not in names
        good = "الحاسوب جاهز. قالت أليس مرحبا"
        assert self.pipeline.validate(good, brief)["passed"] is True

    # --- Review Focus: config errors reported, never silent -------------
    def test_duplicate_yaml_key_reported_with_safe_defaults(self, tmp_path):
        text = "pipeline:\n  quality_threshold: 95\npipeline:\n  max_iterations: 9\n"
        pipeline = _pipeline(tmp_path, text)
        try:
            assert pipeline.config_errors
            assert "duplicate" in " ".join(pipeline.config_errors).lower()
            assert pipeline.quality_threshold == 85
            assert pipeline.max_iterations == 3
        finally:
            pipeline.close()

    def test_malformed_yaml_reported_with_safe_defaults(self, tmp_path):
        pipeline = _pipeline(tmp_path, "pipeline: [unclosed\n")
        try:
            assert pipeline.config_errors
            assert pipeline.quality_threshold == 85
        finally:
            pipeline.close()

    def test_valid_config_thresholds_used_by_review_and_judge(self, tmp_path):
        text = "pipeline:\n  quality_threshold: 95\n  revise_threshold: 60\n  max_iterations: 4\n"
        pipeline = _pipeline(tmp_path, text)
        try:
            assert pipeline.config_errors == []
            assert (pipeline.quality_threshold, pipeline.revise_threshold) == (95, 60)
            review = ReviewResult(overall_score=90, dimension_scores={k: 90 for k in
                ("accuracy", "fluency", "style_register", "terminology", "coherence")})
            assert pipeline.judge("x", review).decision == "revise"
            review.overall_score = 96
            assert pipeline.judge("x", review).decision == "approve"
        finally:
            pipeline.close()

    # --- Judge / revision behaviour ------------------------------------
    def test_judge_honours_host_decision(self):
        review = ReviewResult(overall_score=95)
        judge = self.pipeline.judge("x", review, host_decision="retranslate")
        assert judge.decision == "retranslate" and judge.passed is False
        judge2 = self.pipeline.judge("x", review, host_decision="approve")
        assert judge2.decision == "approve" and judge2.passed is True

    def test_judge_score_and_low_score(self):
        review = ReviewResult(overall_score=90)
        judge = self.pipeline.judge("x", review)
        assert judge.decision == "approve" and judge.passed and judge.score == 90
        assert self.pipeline.judge("x", ReviewResult(overall_score=50)).decision == "retranslate"

    def test_post_edit_keeps_orthography_after_diacritics(self):
        analysis = self.pipeline.analyze("مرحبا")
        draft = "الإسلامُ مُسْلِمٌ"
        result = self.pipeline.post_edit(draft, analysis)
        assert "إ" not in result.revised_translation
        assert result.revised_translation == "الاسلام مسلم"
        assert result.diacritics_applied is True
        assert any(c["reason"] == "orthography" for c in result.corrections)
        assert any(c["reason"] == "diacritics" for c in result.corrections)

    def test_review_uses_configured_thresholds(self):
        analysis = self.pipeline.analyze("Hello world")
        review = self.pipeline.review("مرحبا بالعالم", "Hello world", analysis)
        assert isinstance(review.overall_score, int) and 0 <= review.overall_score <= 100
        assert review.recommendation in ("approve", "revise", "retranslate")
        assert (review.overall_score >= self.pipeline.approve_threshold) == (review.recommendation == "approve")

    # --- Review Focus: no fake translation, no LLM ----------------------
    def test_run_without_host_translation_is_explicit(self):
        result = self.pipeline.run(SOURCE, domain_hint="technical", previous_context="Ch 0")
        assert result["translation"] == ""
        assert result["host_agent_required"] is True
        assert result["needs_host_revision"] is True
        assert result["approved"] is False
        assert result["judge"]["score"] == 0
        assert result["brief"]["placeholder_map"]

    def test_run_with_host_translation_uses_it_verbatim(self):
        translation = "الفصل 1. " + " ".join(SPANS)
        result = self.pipeline.run(SOURCE, domain_hint="technical", host_translation=translation)
        assert result["translation"] == translation
        assert result["host_agent_required"] is False
        assert result["validation"]["passed"] is True
        assert result["iterations"] == 1
        assert "pipeline_id" in result

    def test_no_llm_symbols_in_pipeline(self):
        import inspect
        import src.pipeline as pipeline_module
        src = inspect.getsource(pipeline_module)
        for symbol in ("_llm_complete", "llm_client", "LLMManager", "LLMResponse", "download_model"):
            assert symbol not in src

    def test_legacy_cli_flags_warn_as_noop(self, capsys, monkeypatch):
        import src.pipeline as pipeline_module
        monkeypatch.setattr(sys, "argv", [
            "pipeline.py", "--source", "Hello world", "--use-llm", "--llm-api-key", "dummy"
        ])
        pipeline_module.main()
        err = capsys.readouterr().err
        assert "no-op" in err.lower()
        assert "dummy" not in err


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
