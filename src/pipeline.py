#!/usr/bin/env python3
"""
Multi-Agent Translation System — Core Pipeline Orchestrator.

Implements the sequential, quality-gated pipeline:
  Analysis → Translate → Post-edit → Review → Judge

Designed for English ↔ Arabic translation with Arabic-specific handling.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.arabic import ArabicProcessor
from src.evaluation import TranslationEvaluator
from src.glossary import Glossary


@dataclass
class AnalysisResult:
    register: str = "MSA"
    domain: str = "general"
    entities: List[Dict[str, Any]] = field(default_factory=list)
    gender_context: Dict[str, str] = field(default_factory=dict)
    orthography_norm: Optional[str] = None
    difficult_terms: List[str] = field(default_factory=list)
    code_blocks: List[str] = field(default_factory=list)
    word_count: int = 0
    sentence_count: int = 0
    has_rtl: bool = False
    needs_diacritics: bool = False


@dataclass
class TranslationResult:
    draft_translation: str = ""
    confidence_flags: List[Dict[str, Any]] = field(default_factory=list)
    terms_for_review: List[str] = field(default_factory=list)
    word_count: int = 0
    segments_translated: int = 0


@dataclass
class PostEditResult:
    revised_translation: str = ""
    corrections: List[Dict[str, Any]] = field(default_factory=list)
    corrections_count: int = 0
    diacritics_applied: bool = False


@dataclass
class ReviewResult:
    overall_score: int = 0
    dimension_scores: Dict[str, int] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    critical_errors: int = 0
    major_errors: int = 0
    minor_errors: int = 0
    glossary_adherence: float = 0.0
    recommendation: str = "revise"


@dataclass
class JudgeResult:
    score: int = 0
    passed: bool = False
    decision: str = "revise"
    dimension_scores: Dict[str, int] = field(default_factory=dict)
    rationale: str = ""
    specific_issues: List[Dict[str, Any]] = field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 3


class TranslationPipeline:
    """
    Orchestrates the multi-agent translation pipeline.

    Stages:
      1. Analysis  — detect register, domain, entities, gender context
      2. Translate — draft translation with glossary injection
      3. Post-edit — Arabic grammar, morphology, gender/plural correction
      4. Review    — MQM-style structured critique
      5. Judge     — quality gate (approve / revise / retranslate)
    """

    def __init__(
        self,
        source_lang: str = "en",
        target_lang: str = "ar",
        config_path: Optional[str] = None,
        glossary_path: Optional[str] = None,
    ) -> None:
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.config_path = config_path or str(
            PROJECT_ROOT / "config" / "translator.yaml"
        )
        self.glossary_path = glossary_path or str(
            PROJECT_ROOT / "data" / "glossary.tbx"
        )

        self.arabic = ArabicProcessor()
        self.evaluator = TranslationEvaluator()
        self.glossary = Glossary(self.glossary_path)

        self.max_iterations = 3
        self.quality_threshold = 85

        # Load config
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from translator.yaml."""
        try:
            import yaml  # type: ignore

            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            pipeline_cfg = config.get("pipeline", {})
            self.max_iterations = pipeline_cfg.get("max_iterations", 3)
            self.quality_threshold = pipeline_cfg.get("quality_threshold", 85)

            arabic_cfg = config.get("arabic", {})
            self.arabic.diacritics_policy = arabic_cfg.get(
                "diacritics_policy", "remove"
            )
            self.arabic.orthography_normalization = arabic_cfg.get(
                "orthography_normalization", True
            )

        except Exception:
            # Config not available — use defaults
            pass

    # ------------------------------------------------------------------
    # Stage 1: Analysis
    # ------------------------------------------------------------------
    def analyze(
        self, source_text: str, domain_hint: Optional[str] = None
    ) -> AnalysisResult:
        """Run Analysis Agent: pre-process source text, extract context."""
        result = AnalysisResult()

        # Detect RTL
        result.has_rtl = self.arabic.contains_arabic(source_text)

        # Word / sentence count
        result.word_count = len(source_text.split())
        result.sentence_count = max(1, source_text.count(".") + source_text.count("!") + source_text.count("?"))

        # Register detection (default MSA for written Arabic)
        result.register = "MSA"
        if domain_hint:
            result.domain = domain_hint

        # Extract code blocks (preserve unchanged)
        import re

        code_pattern = r"`[^`]+`|<[^>]+>|\{\{[^}]+\}\}|\$\{[^}]+\}"
        result.code_blocks = re.findall(code_pattern, source_text)

        # Difficult terms (simple heuristic: capitalized words, acronyms)
        result.difficult_terms = re.findall(r"\b[A-Z]{2,}\b|\b[A-Z][a-z]+\b", source_text)

        # Gender context (default neutral)
        result.gender_context = {
            "subject_gender": "neutral",
            "object_gender": "neutral",
        }

        # Orthography normalization if Arabic
        if result.has_rtl and self.arabic.orthography_normalization:
            result.orthography_norm = self.arabic.normalize_orthography(source_text)

        return result

    # ------------------------------------------------------------------
    # Stage 2: Translate
    # ------------------------------------------------------------------
    def translate(
        self,
        source_text: str,
        analysis: AnalysisResult,
        previous_context: Optional[str] = None,
    ) -> TranslationResult:
        """Run Translator Agent: produce draft translation with glossary injection."""
        result = TranslationResult()

        # Inject glossary terms
        glossary_terms = self.glossary.get_relevant_terms(
            source_text, analysis.domain
        )

        # Build translation prompt context
        context = {
            "source": source_text,
            "target_lang": self.target_lang,
            "register": analysis.register,
            "domain": analysis.domain,
            "entities": analysis.entities,
            "gender_context": analysis.gender_context,
            "glossary": glossary_terms,
            "code_blocks": analysis.code_blocks,
            "previous_context": previous_context or "",
        }

        # In a real implementation, this would call an LLM.
        # Here we produce a structured draft placeholder.
        draft = self._generate_draft(context)

        result.draft_translation = draft
        result.word_count = analysis.word_count
        result.segments_translated = max(1, draft.count(".") + draft.count("!") + draft.count("?"))

        # Flag difficult terms for review
        result.terms_for_review = analysis.difficult_terms[:5]
        result.confidence_flags = [
            {"term": t, "position": 0, "suggestion": "review_needed"}
            for t in analysis.difficult_terms[:5]
        ]

        return result

    def _generate_draft(self, context: Dict[str, Any]) -> str:
        """Generate draft translation (placeholder for LLM integration)."""
        source = context["source"]
        target_lang = context["target_lang"]
        register = context["register"]
        glossary = context["glossary"]

        if target_lang == "ar":
            # Arabic draft (placeholder — real implementation uses LLM)
            draft = f"[ترجمة مسودة مسجل: {register}] {source}"
            # Apply glossary substitutions
            for term in glossary:
                draft = draft.replace(term.get("en", ""), term.get("ar", term.get("en", "")))
            return draft
        else:
            return f"[Draft translation to {target_lang}] {source}"

    # ------------------------------------------------------------------
    # Stage 3: Post-Edit
    # ------------------------------------------------------------------
    def post_edit(
        self,
        draft: str,
        analysis: AnalysisResult,
    ) -> PostEditResult:
        """Run Post-Editor Agent: Arabic grammar, morphology, agreement correction."""
        result = PostEditResult()
        result.revised_translation = draft

        if self.target_lang != "ar":
            return result

        corrections = []

        # Gender agreement check (placeholder logic)
        if analysis.gender_context.get("subject_gender") != "neutral":
            corrections.append({
                "position": 0,
                "original": draft[:20],
                "corrected": draft[:20],
                "reason": "gender_agreement",
            })

        # Orthography normalization
        if self.arabic.orthography_normalization:
            normalized = self.arabic.normalize_orthography(draft)
            if normalized != draft:
                corrections.append({
                    "position": 0,
                    "original": draft[:20],
                    "corrected": normalized[:20],
                    "reason": "orthography",
                })
                result.revised_translation = normalized

        # Diacritics policy
        if self.arabic.diacritics_policy == "remove":
            stripped = self.arabic.remove_diacritics(draft)
            if stripped != draft:
                corrections.append({
                    "position": 0,
                    "original": draft[:20],
                    "corrected": stripped[:20],
                    "reason": "diacritics",
                })
                result.revised_translation = stripped
                result.diacritics_applied = True

        result.corrections = corrections
        result.corrections_count = len(corrections)

        return result

    # ------------------------------------------------------------------
    # Stage 4: Review
    # ------------------------------------------------------------------
    def review(
        self,
        translation: str,
        source_text: str,
        analysis: AnalysisResult,
    ) -> ReviewResult:
        """Run Reviewer Agent: MQM-style structured critique."""
        result = ReviewResult()

        # Dimension scores (placeholder — real implementation uses LLM judge)
        result.dimension_scores = {
            "accuracy": 80,
            "fluency": 78,
            "style_register": 82,
            "terminology": 85,
            "coherence": 80,
        }

        result.overall_score = int(
            0.30 * result.dimension_scores["accuracy"]
            + 0.25 * result.dimension_scores["fluency"]
            + 0.20 * result.dimension_scores["style_register"]
            + 0.15 * result.dimension_scores["terminology"]
            + 0.10 * result.dimension_scores["coherence"]
        )

        # Glossary adherence
        result.glossary_adherence = self.glossary.check_adherence(translation)

        # Errors (placeholder)
        result.errors = []
        result.critical_errors = 0
        result.major_errors = 0
        result.minor_errors = 0

        if result.overall_score >= 85:
            result.recommendation = "approve"
        elif result.overall_score >= 70:
            result.recommendation = "revise"
        else:
            result.recommendation = "retranslate"

        return result

    # ------------------------------------------------------------------
    # Stage 5: Judge
    # ------------------------------------------------------------------
    def judge(
        self,
        translation: str,
        review: ReviewResult,
        iteration: int = 1,
    ) -> JudgeResult:
        """Run LLM Judge Agent: quality gate (approve / revise / retranslate)."""
        result = JudgeResult()
        result.score = review.overall_score
        result.dimension_scores = review.dimension_scores
        result.iteration = iteration
        result.max_iterations = self.max_iterations

        if result.score >= self.quality_threshold:
            result.passed = True
            result.decision = "approve"
            result.rationale = f"Translation scored {result.score}/100, meeting threshold {self.quality_threshold}."
        elif result.score >= 70 and iteration < self.max_iterations:
            result.passed = False
            result.decision = "revise"
            result.rationale = (
                f"Translation scored {result.score}/100. One revision allowed "
                f"(iteration {iteration}/{self.max_iterations})."
            )
        else:
            result.passed = False
            result.decision = "retranslate"
            result.rationale = (
                f"Translation scored {result.score}/100. Full re-translation required."
            )

        result.specific_issues = review.errors

        return result

    # ------------------------------------------------------------------
    # Full Pipeline
    # ------------------------------------------------------------------
    def run(
        self,
        source_text: str,
        domain_hint: Optional[str] = None,
        previous_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run the complete pipeline and return the final result."""
        pipeline_id = str(uuid.uuid4())

        # Stage 1: Analysis
        analysis = self.analyze(source_text, domain_hint)

        # Stage 2: Translate
        translation = self.translate(source_text, analysis, previous_context)

        # Stage 3: Post-edit
        post_edit_result = self.post_edit(translation.draft_translation, analysis)
        current_translation = post_edit_result.revised_translation

        # Stage 4: Review
        review = self.review(current_translation, source_text, analysis)

        # Stage 5: Judge with iteration loop
        iteration = 1
        judge_result = self.judge(current_translation, review, iteration)

        while (
            judge_result.decision in ("revise", "retranslate")
            and iteration < self.max_iterations
        ):
            iteration += 1
            # Re-run review and judge (simplified iteration)
            review = self.review(current_translation, source_text, analysis)
            judge_result = self.judge(current_translation, review, iteration)

        return {
            "pipeline_id": pipeline_id,
            "source_text": source_text,
            "target_lang": self.target_lang,
            "analysis": analysis,
            "translation": current_translation,
            "post_edits": post_edit_result.corrections,
            "review": review,
            "judge": judge_result,
            "approved": judge_result.passed,
            "iterations": iteration,
        }


def main() -> None:
    """CLI entry point for the translation pipeline."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Multi-Agent Translation System (EN ↔ Arabic)"
    )
    parser.add_argument("--source", required=True, help="Source text or file path")
    parser.add_argument(
        "--target", default="ar", choices=["ar", "en"], help="Target language"
    )
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--domain", help="Domain hint (technical, literary, legal, medical, UI, general)")
    parser.add_argument("--config", help="Path to config YAML")

    args = parser.parse_args()

    # Read source
    source_path = Path(args.source)
    if source_path.exists():
        source_text = source_path.read_text(encoding="utf-8")
    else:
        source_text = args.source

    pipeline = TranslationPipeline(
        source_lang="en" if args.target == "ar" else "ar",
        target_lang=args.target,
        config_path=args.config,
    )

    result = pipeline.run(source_text, domain_hint=args.domain)

    output_text = result["translation"]
    if args.output:
        Path(args.output).write_text(output_text, encoding="utf-8")
        print(f"Translation saved to {args.output}")
    else:
        print(output_text)

    print(f"\nPipeline ID: {result['pipeline_id']}")
    print(f"Judge score: {result['judge']['score']}/100")
    print(f"Decision: {result['judge']['decision']}")
    print(f"Approved: {result['approved']}")
    print(f"Iterations: {result['iterations']}")


if __name__ == "__main__":
    main()
