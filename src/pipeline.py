#!/usr/bin/env python3
"""
Multi-Agent Translation System — Core Pipeline Orchestrator.

Implements the sequential, quality-gated pipeline:
  Analysis → Translate → Post-edit → Review → Judge

Designed for English ↔ Arabic translation with Arabic-specific handling.
Integrates real LLM calls and dictionary skills for production-quality output.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.arabic import ArabicProcessor
from src.dictionary import DictionaryManager
from src.evaluation import TranslationEvaluator
from src.glossary import Glossary
from src.llm_client import LLMManager, LLMResponse


@dataclass
class AnalysisResult:
    register: str = "MSA"
    domain: str = "general"
    entities: list[dict[str, Any]] = field(default_factory=list)
    gender_context: dict[str, str] = field(default_factory=dict)
    orthography_norm: str | None = None
    difficult_terms: list[str] = field(default_factory=list)
    code_blocks: list[str] = field(default_factory=list)
    protected_source: str | None = None
    word_count: int = 0
    sentence_count: int = 0
    has_rtl: bool = False
    needs_diacritics: bool = False


@dataclass
class TranslationResult:
    draft_translation: str = ""
    confidence_flags: list[dict[str, Any]] = field(default_factory=list)
    terms_for_review: list[str] = field(default_factory=list)
    word_count: int = 0
    segments_translated: int = 0
    llm_response: dict[str, Any] | None = None


@dataclass
class PostEditResult:
    revised_translation: str = ""
    corrections: list[dict[str, Any]] = field(default_factory=list)
    corrections_count: int = 0
    diacritics_applied: bool = False


@dataclass
class ReviewResult:
    overall_score: int = 0
    dimension_scores: dict[str, int] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)
    critical_errors: int = 0
    major_errors: int = 0
    minor_errors: int = 0
    glossary_adherence: float = 0.0
    recommendation: str = "revise"
    score_source: str = "fallback"  # "llm" when validated LLM scores were used


@dataclass
class JudgeResult:
    score: int = 0
    passed: bool = False
    decision: str = "revise"
    dimension_scores: dict[str, int] = field(default_factory=dict)
    rationale: str = ""
    specific_issues: list[dict[str, Any]] = field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 3


class TranslationPipeline:
    """
    Orchestrates the multi-agent translation pipeline.

    Stages:
      1. Analysis  — detect register, domain, entities, gender context
      2. Translate — draft translation with glossary injection (via LLM)
      3. Post-edit — Arabic grammar, morphology, gender/plural correction
      4. Review    — MQM-style structured critique (via LLM)
      5. Judge     — quality gate (approve / revise / retranslate) (via LLM)
    """

    def __init__(
        self,
        source_lang: str = "en",
        target_lang: str = "ar",
        config_path: str | None = None,
        glossary_path: str | None = None,
        llm_provider: str = "openai",
        llm_model: str | None = None,
        llm_api_key: str | None = None,
        use_llm: bool | None = None,
    ) -> None:
        self.source_lang = source_lang
        self.target_lang = target_lang
        self._config_explicit = config_path is not None
        self.config_path = config_path or str(
            PROJECT_ROOT / "config" / "translator.yaml"
        )
        self.glossary_path = glossary_path or str(
            PROJECT_ROOT / "data" / "glossary.tbx"
        )

        self.arabic = ArabicProcessor()
        self.evaluator = TranslationEvaluator()
        self.glossary = Glossary(self.glossary_path)
        self.dictionary = DictionaryManager()

        self.max_iterations = 3
        self.quality_threshold = 85
        # None = follow config; True/False = explicit caller intent that
        # config must never silently override
        self._explicit_use_llm = use_llm is not None
        self.use_llm = bool(use_llm)
        self._last_completion_truncated = False

        # Initialize LLM manager if requested
        self.llm: LLMManager | None = None
        if use_llm:
            self.llm = LLMManager(
                provider=llm_provider,
                model=llm_model,
                api_key=llm_api_key,
            )

        # Load config (clean up resources if configuration fails)
        try:
            self._load_config()
        except Exception:
            self.dictionary.close()
            raise

    def _load_config(self) -> None:
        """Load configuration from translator.yaml.

        Missing default config -> defaults + info log. Missing or malformed
        EXPLICIT config -> raise (never silently ignore user settings).
        """
        try:
            import yaml  # type: ignore
        except ImportError:
            if self._config_explicit:
                raise
            logger.warning("PyYAML not installed; using default configuration")
            return

        config_file = Path(self.config_path)
        if not config_file.exists():
            if self._config_explicit:
                raise FileNotFoundError(f"Config file not found: {config_file}")
            logger.info("No config at %s; using defaults", config_file)
            return

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"Malformed config {config_file}: {exc}") from exc
        if not isinstance(config, dict):
            raise TypeError(f"Config must be a YAML mapping: {config_file}")

        pipeline_cfg = config.get("pipeline", {})
        self.max_iterations = pipeline_cfg.get("max_iterations", 3)
        self.quality_threshold = pipeline_cfg.get("quality_threshold", 85)

        arabic_cfg = config.get("arabic", {})
        self.arabic.diacritics_policy = arabic_cfg.get("diacritics_policy", "remove")
        self.arabic.orthography_normalization = arabic_cfg.get(
            "orthography_normalization", True
        )
        self.arabic.normalize_output = arabic_cfg.get("normalize_output", False)

        llm_cfg = config.get("llm", {})
        if llm_cfg.get("api_key"):
            logger.warning(
                "API key in config file is insecure (committed/shared); "
                "prefer OPENAI_API_KEY / ANTHROPIC_API_KEY environment variables"
            )
        if llm_cfg.get("enabled") and self.llm is None and not self._explicit_use_llm:
            self.use_llm = True
            self.llm = LLMManager(
                provider=llm_cfg.get("provider", "openai"),
                model=llm_cfg.get("model"),
                api_key=llm_cfg.get("api_key"),
            )

    # ------------------------------------------------------------------
    # LLM helper
    # ------------------------------------------------------------------
    def _llm_complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        """Send a completion request to the LLM or return a placeholder.

        LLM failures RAISE (surfaced by run()); they are never converted
        into fake translation text.
        """
        if self.llm and self.use_llm:
            self._last_completion_truncated = False
            response: LLMResponse = self.llm.complete(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if response.finish_reason == "length":
                self._last_completion_truncated = True
                logger.warning(
                    "LLM completion truncated at max_tokens=%s", max_tokens
                )
            return response.content
        # No LLM configured — return structured placeholder
        return f"[LLM REQUIRED] {user_prompt[:200]}..."

    # ------------------------------------------------------------------
    # Stage 1: Analysis
    # ------------------------------------------------------------------
    def analyze(
        self, source_text: str, domain_hint: str | None = None
    ) -> AnalysisResult:
        """Run Analysis Agent: pre-process source text, extract context."""
        result = AnalysisResult()

        # Detect RTL
        result.has_rtl = self.arabic.contains_arabic(source_text)

        # Word / sentence count
        result.word_count = len(source_text.split())
        result.sentence_count = max(
            1,
            source_text.count(".")
            + source_text.count("!")
            + source_text.count("?"),
        )

        # Register detection (default MSA for written Arabic)
        result.register = "MSA"
        if domain_hint:
            result.domain = domain_hint

        # Extract code blocks (preserve unchanged)
        protected, code_blocks = self.arabic.protect_code_blocks(source_text)
        result.code_blocks = code_blocks
        result.protected_source = protected

        # Difficult terms (use dictionary + heuristics)
        difficult_terms = set()
        # Heuristic: capitalized words, acronyms
        difficult_terms.update(
            re.findall(r"\b[A-Z]{2,}\b|\b[A-Z][a-z]+\b", source_text)
        )
        # Dictionary lookup for difficult terms
        try:
            dict_entries = self.dictionary.get_relevant_terms(
                source_text, max_terms=10
            )
            for entry in dict_entries:
                difficult_terms.add(entry.word)
        except Exception as exc:
            logger.debug("Dictionary term extraction failed: %s", exc)

        result.difficult_terms = sorted(difficult_terms)

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
        previous_context: str | None = None,
    ) -> TranslationResult:
        """Run Translator Agent: produce draft translation with glossary injection (via LLM)."""
        result = TranslationResult()

        # Inject glossary terms
        glossary_terms = self.glossary.get_relevant_terms(
            source_text, analysis.domain
        )

        # Dictionary lookups for difficult terms
        dict_definitions: list[dict[str, Any]] = []
        for term in analysis.difficult_terms[:5]:
            entry = self.dictionary.lookup_definition(term, dictionary="wordnet")
            if entry:
                dict_definitions.append(asdict(entry))

        # Build translation prompt (agent system prompt)
        system_prompt = self._build_translator_system_prompt(
            analysis, glossary_terms, dict_definitions
        )

        user_prompt = self._build_translator_user_prompt(
            source_text, analysis, previous_context
        )

        # Generate draft via LLM or placeholder
        draft = self._llm_complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=2000,
        )

        # Clean up placeholder markers if present
        if draft.startswith("[LLM"):
            # Apply glossary substitutions manually for placeholder mode
            draft = self._apply_glossary_substitutions(source_text, glossary_terms, analysis)
        elif analysis.code_blocks:
            # LLM path: restore protected code blocks by index (order-safe)
            draft = self.arabic.restore_code_blocks(draft, analysis.code_blocks)

        result.draft_translation = draft
        result.word_count = analysis.word_count
        result.segments_translated = max(
            1, draft.count(".") + draft.count("!") + draft.count("?")
        )

        # Flag difficult terms for review
        result.terms_for_review = analysis.difficult_terms[:5]
        result.confidence_flags = [
            {"term": t, "position": 0, "suggestion": "review_needed"}
            for t in analysis.difficult_terms[:5]
        ]
        if self._last_completion_truncated:
            result.confidence_flags.append({
                "term": "__truncated__",
                "position": -1,
                "suggestion": "completion hit max_tokens; translation may be incomplete",
            })

        # Store LLM response metadata
        result.llm_response = {
            "model": self.llm.primary.model if self.llm else "placeholder",
            "provider": self.llm.provider if self.llm else "placeholder",
        }

        return result

    def _build_translator_system_prompt(
        self,
        analysis: AnalysisResult,
        glossary_terms: list[dict[str, Any]],
        dict_definitions: list[dict[str, Any]],
    ) -> str:
        """Build the Translator Agent system prompt."""
        lines = [
            "You are a professional English ↔ Arabic translator.",
            "Translate the source text accurately and fluently.",
            "",
            "CRITICAL CONSTRAINTS:",
            "1. NEVER translate code blocks, placeholders, XML/HTML tags, or IDs.",
            "2. Preserve formatting: RTL markers, paragraph structure, line breaks.",
            "3. Use Modern Standard Arabic (MSA) for written Arabic unless dialect is requested.",
            "4. Handle 6 Arabic plural forms: zero, one, two, few, many, other.",
            "5. Ensure gender agreement (verb-subject, noun-adjective, definiteness).",
            "6. Normalize Arabic orthography (alef/ya/ta-marbuta variants).",
            "",
        ]

        # Glossary injection
        if glossary_terms:
            lines.append("APPROVED GLOSSARY TERMS (must use these translations):")
            for term in glossary_terms:
                en = term.get("en", term.get("source", ""))
                ar = term.get("ar", term.get("target", ""))
                if en and ar:
                    lines.append(f"  - {en} → {ar}")
            lines.append("")

        # Dictionary definitions
        if dict_definitions:
            lines.append("DIFFICULT TERMS (use these definitions for word sense):")
            for d in dict_definitions:
                word = d.get("word", "")
                defn = d.get("definition", "")
                syns = d.get("synonyms", [])
                lines.append(f"  - {word}: {defn}")
                if syns:
                    lines.append(f"    Synonyms: {', '.join(syns[:5])}")
            lines.append("")

        # Context
        lines.append(f"Target register: {analysis.register}")
        lines.append(f"Domain: {analysis.domain}")
        lines.append(f"Gender context: {analysis.gender_context}")
        lines.append(f"Entities: {json.dumps(analysis.entities, ensure_ascii=False)}")
        lines.append("")
        lines.append(
            "Output ONLY the translation, no explanations, no markdown code blocks."
        )

        return "\n".join(lines)

    def _build_translator_user_prompt(
        self,
        source_text: str,
        analysis: AnalysisResult,
        previous_context: str | None = None,
    ) -> str:
        """Build the Translator Agent user prompt."""
        # Send code-protected text to the LLM when blocks were extracted
        text_for_llm = analysis.protected_source if analysis.code_blocks else source_text
        lines = [f"Source text to translate:\n{text_for_llm}", ""]
        if analysis.code_blocks:
            lines.extend([
                ("Markers like ___CODE_BLOCK_0___ are protected code blocks: "
                 "keep each marker EXACTLY as-is, in its original position."),
                "",
            ])
        if previous_context:
            lines.extend([f"Previous chapter context:\n{previous_context}", ""])
        lines.append("Translate the above text now.")
        return "\n".join(lines)

    def _apply_glossary_substitutions(
        self, source_text: str, glossary_terms: list[dict[str, Any]], analysis: AnalysisResult
    ) -> str:
        """Apply glossary term substitutions (placeholder mode fallback).

        Protects code blocks before substitution and restores them after,
        so glossary terms inside code blocks (e.g. XML tags, IDs) are not mangled.
        """
        # Extract and protect code blocks
        protected, blocks = self.arabic.protect_code_blocks(source_text)

        # Apply glossary substitutions to protected text only:
        # whole-word, case-insensitive (never corrupt 'malfunction' via 'function')
        draft = protected
        for term in glossary_terms:
            en = term.get("en", term.get("source", ""))
            ar = term.get("ar", term.get("target", ""))
            if en and ar:
                def _sub(m: re.Match[str], replacement: str = ar) -> str:
                    return replacement

                draft = re.sub(
                    r"\b" + re.escape(en) + r"\b",
                    _sub,
                    draft,
                    flags=re.IGNORECASE,
                )

        # Restore code blocks (order-independent, indexed markers)
        draft = self.arabic.restore_code_blocks(draft, blocks)

        return f"[ترجمة مسودة مسجل: {analysis.register}] {draft}"

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

        # Gender agreement check (placeholder — requires LLM analysis of the draft)
        if analysis.gender_context.get("subject_gender") != "neutral":
            corrections.append({
                "position": 0,
                "original": draft[:20],
                "corrected": draft[:20],
                "reason": "gender_agreement",
            })

        # Orthography normalization of OUTPUT is opt-in (lossy: أحمد -> احمد);
        # analysis-stage normalization is controlled separately.
        if self.arabic.orthography_normalization and self.arabic.normalize_output:
            normalized = self.arabic.normalize_orthography(draft)
            if normalized != draft:
                # Find first position where text differs
                pos = 0
                for c1, c2 in zip(draft, normalized):
                    if c1 != c2:
                        break
                    pos += 1
                corrections.append({
                    "position": pos,
                    "original": draft[pos:pos + 20],
                    "corrected": normalized[pos:pos + 20],
                    "reason": "orthography",
                })
                result.revised_translation = normalized

        # Diacritics policy
        if self.arabic.diacritics_policy == "remove":
            stripped = self.arabic.remove_diacritics(draft)
            if stripped != draft:
                # Find first position containing a diacritic IN THE DRAFT
                pos = 0
                for ch in draft:
                    if self.arabic.DIACRITICS.search(ch):
                        break
                    pos += 1
                corrections.append({
                    "position": pos,
                    "original": draft[pos:pos + 20],
                    "corrected": stripped[pos:pos + 20],
                    "reason": "diacritics",
                })
                result.revised_translation = stripped
                result.diacritics_applied = True

        # LLM-based Arabic post-editing (if available)
        if self.llm and self.use_llm and self.target_lang == "ar":
            system_prompt = (
                "You are an Arabic post-editor. Correct grammar, morphology, "
                "gender agreement, plural forms, and diacritics in the translation. "
                "Preserve code blocks, placeholders, and formatting. "
                "Output ONLY the corrected translation."
            )
            user_prompt = f"Source (for context):\n{draft}\n\nCorrect this Arabic translation:"

            corrected = self._llm_complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=2000,
            )

            if not corrected.startswith("[LLM"):
                result.revised_translation = corrected
                corrections.append({
                    "position": 0,
                    "original": draft[:30],
                    "corrected": corrected[:30],
                    "reason": "llm_postedit",
                })

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
        """Run Reviewer Agent: MQM-style structured critique (via LLM)."""
        result = ReviewResult()

        # LLM-based review (if available)
        if self.llm and self.use_llm:
            system_prompt = (
                "You are a translation quality reviewer using the MQM framework. "
                "Evaluate the translation on: Accuracy (30%), Fluency (25%), "
                "Style/Register (20%), Terminology (15%), Coherence (10%). "
                "Provide scores 0-100 for each dimension, identify errors with "
                "severity (critical/major/minor), and suggest fixes. "
                "Output valid JSON only."
            )
            user_prompt = (
                f"Source:\n{source_text}\n\n"
                f"Translation:\n{translation}\n\n"
                f"Target language: {self.target_lang}\n"
                f"Register: {analysis.register}\n"
                f"Domain: {analysis.domain}\n\n"
                "Review this translation and output JSON with dimension_scores, "
                "errors, and recommendation."
            )

            review_text = self._llm_complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=1500,
            )

            # Parse and TYPE-VALIDATE the LLM JSON: string scores or errors
            # must never crash the weighted arithmetic below
            try:
                json_match = re.search(r"\{.*\}", review_text, re.DOTALL)
                if json_match:
                    review_data = json.loads(json_match.group())
                    scores = review_data.get("dimension_scores", {})
                    if isinstance(scores, dict):
                        valid = {
                            k: min(100, max(0, int(v)))
                            for k, v in scores.items()
                            if isinstance(v, (int, float)) and not isinstance(v, bool)
                        }
                        if valid:
                            result.dimension_scores = valid
                            result.score_source = "llm"
                    errors = review_data.get("errors", [])
                    if isinstance(errors, list):
                        result.errors = [e for e in errors if isinstance(e, dict)]
            except (json.JSONDecodeError, ValueError, TypeError) as exc:
                logger.warning("Review JSON parse failed: %s", exc)

        # Fallback scores if LLM not available or parsing failed
        if not result.dimension_scores:
            result.dimension_scores = {
                "accuracy": 80,
                "fluency": 78,
                "style_register": 82,
                "terminology": 85,
                "coherence": 80,
            }

        result.overall_score = int(
            0.30 * result.dimension_scores.get("accuracy", 80)
            + 0.25 * result.dimension_scores.get("fluency", 78)
            + 0.20 * result.dimension_scores.get("style_register", 82)
            + 0.15 * result.dimension_scores.get("terminology", 85)
            + 0.10 * result.dimension_scores.get("coherence", 80)
        )

        # Glossary adherence scoped to terms relevant to this source
        result.glossary_adherence = self.glossary.check_adherence(
            translation, source_text=source_text
        )

        # Error counts
        result.critical_errors = sum(
            1 for e in result.errors if e.get("severity") == "critical"
        )
        result.major_errors = sum(
            1 for e in result.errors if e.get("severity") == "major"
        )
        result.minor_errors = sum(
            1 for e in result.errors if e.get("severity") == "minor"
        )

        # Deterministic recommendation (authoritative; LLM suggestion is advisory)
        if result.overall_score >= self.quality_threshold:
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

        # LLM-based judging (if available)
        if self.llm and self.use_llm:
            system_prompt = (
                "You are a translation quality judge. Decide whether to approve "
                "the translation or request revision. Use the MQM rubric. "
                "Threshold: score >= 85 approves, 70-84 allows one revision, "
                "< 70 requires retranslation. Max 3 iterations. "
                "Output valid JSON only with score, decision, rationale."
            )
            user_prompt = (
                f"Translation score: {review.overall_score}/100\n"
                f"Dimension scores: {json.dumps(review.dimension_scores, ensure_ascii=False)}\n"
                f"Errors: {json.dumps(review.errors, ensure_ascii=False)}\n"
                f"Iteration: {iteration}/{self.max_iterations}\n\n"
                "Make your decision and output JSON."
            )

            judge_text = self._llm_complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=1000,
            )

            try:
                json_match = re.search(r"\{.*\}", judge_text, re.DOTALL)
                if json_match:
                    judge_data = json.loads(json_match.group())
                    raw_score = judge_data.get("score")
                    if isinstance(raw_score, (int, float)) and not isinstance(raw_score, bool):
                        result.score = min(100, max(0, int(raw_score)))
                    rationale = judge_data.get("rationale")
                    if isinstance(rationale, str) and rationale.strip():
                        result.rationale = rationale.strip()
            except (json.JSONDecodeError, ValueError, TypeError) as exc:
                logger.warning("Judge JSON parse failed: %s", exc)

        # Deterministic quality gate — AUTHORITATIVE. The LLM judge's score
        # and rationale inform it, but an LLM "approve" can never bypass the
        # configured threshold (defense against prompt-injection/persuasion).
        if result.score >= self.quality_threshold:
            result.passed = True
            result.decision = "approve"
            if not result.rationale:
                result.rationale = (
                    f"Translation scored {result.score}/100, "
                    f"meeting threshold {self.quality_threshold}."
                )
        elif result.score >= 70 and iteration < self.max_iterations:
            result.passed = False
            result.decision = "revise"
            if not result.rationale:
                result.rationale = (
                    f"Translation scored {result.score}/100. One revision allowed "
                    f"(iteration {iteration}/{self.max_iterations})."
                )
        else:
            result.passed = False
            result.decision = "retranslate"
            if not result.rationale:
                result.rationale = (
                    f"Translation scored {result.score}/100. Full re-translation required."
                )

        result.specific_issues = review.errors

        return result

    # ------------------------------------------------------------------
    # Full Pipeline
    # ------------------------------------------------------------------
    def _revise(
        self,
        current: str,
        source_text: str,
        review: ReviewResult,
        analysis: AnalysisResult,
    ) -> str:
        """Editor pass: apply reviewer feedback to produce a revised draft."""
        system_prompt = (
            "You are a translation editor. Revise the translation to fix the "
            "reviewer's errors while preserving meaning, formatting, and any "
            "___CODE_BLOCK_n___ markers exactly. Output ONLY the revised translation."
        )
        user_prompt = (
            f"Source:\n{source_text}\n\n"
            f"Current translation:\n{current}\n\n"
            f"Reviewer errors:\n{json.dumps(review.errors, ensure_ascii=False)}\n\n"
            "Produce the revised translation now."
        )
        revised = self._llm_complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=2000,
        )
        if revised.startswith("[LLM"):
            return current
        if analysis.code_blocks:
            revised = self.arabic.restore_code_blocks(revised, analysis.code_blocks)
        return revised

    def run(
        self,
        source_text: str,
        domain_hint: str | None = None,
        previous_context: str | None = None,
    ) -> dict[str, Any]:
        """Run the complete pipeline and return the final result.

        Never fabricates success: LLM failures yield approved=False with an
        error and empty translation; placeholder mode is loudly flagged.
        """
        pipeline_id = str(uuid.uuid4())
        mode = "llm" if (self.llm and self.use_llm) else "placeholder"
        warnings: list[str] = []
        if mode == "placeholder":
            warnings.append(
                "LLM not configured: output is a glossary-substituted PLACEHOLDER, "
                "not a real translation. Set an API key (OPENAI_API_KEY / "
                "ANTHROPIC_API_KEY) and enable --use-llm."
            )
        base: dict[str, Any] = {
            "pipeline_id": pipeline_id,
            "source_text": source_text,
            "target_lang": self.target_lang,
            "mode": mode,
            "warnings": warnings,
        }
        try:
            # Stage 1: Analysis
            analysis = self.analyze(source_text, domain_hint)

            # Stage 2: Translate
            translation = self.translate(source_text, analysis, previous_context)

            # Stage 3: Post-edit
            post_edit_result = self.post_edit(
                translation.draft_translation, analysis
            )
            current_translation = post_edit_result.revised_translation

            # Stage 4: Review
            review = self.review(current_translation, source_text, analysis)

            # Stage 5: Judge with a REAL revision loop (LLM mode only)
            iteration = 1
            judge_result = self.judge(current_translation, review, iteration)

            while (
                judge_result.decision in ("revise", "retranslate")
                and iteration < self.max_iterations
                and mode == "llm"
            ):
                iteration += 1
                current_translation = self._revise(
                    current_translation, source_text, review, analysis
                )
                review = self.review(current_translation, source_text, analysis)
                judge_result = self.judge(current_translation, review, iteration)
        except Exception as exc:
            logger.error("Pipeline failed: %s", exc)
            return {
                **base,
                "analysis": AnalysisResult(),
                "translation": "",
                "post_edits": [],
                "review": ReviewResult(),
                "judge": JudgeResult(),
                "approved": False,
                "iterations": 0,
                "error": str(exc),
                "warnings": warnings + [f"Pipeline error: {exc}"],
            }

        return {
            **base,
            "analysis": analysis,
            "translation": current_translation,
            "post_edits": post_edit_result.corrections,
            "review": review,
            "judge": judge_result,
            "approved": judge_result.passed,
            "iterations": iteration,
        }

    def close(self) -> None:
        """Close resources."""
        self.dictionary.close()

    def __enter__(self) -> TranslationPipeline:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


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
    parser.add_argument(
        "--llm-provider", default="openai", help="LLM provider (openai, anthropic, local)"
    )
    parser.add_argument("--llm-model", help="LLM model name")
    parser.add_argument("--llm-api-key", help="LLM API key (prefer env vars: keys in argv are visible in process listings)")
    parser.add_argument(
        "--use-llm", action="store_true", default=None,
        help="Enable real LLM calls (default: follow config llm.enabled)",
    )

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
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        llm_api_key=args.llm_api_key,
        use_llm=args.use_llm,
    )

    try:
        result = pipeline.run(source_text, domain_hint=args.domain)

        for warning in result.get("warnings", []):
            print(f"WARNING: {warning}", file=sys.stderr)
        if result.get("error"):
            print(f"ERROR: pipeline failed: {result['error']}", file=sys.stderr)
            sys.exit(1)

        output_text = result["translation"]
        if args.output:
            Path(args.output).write_text(output_text, encoding="utf-8")
            print(f"Translation saved to {args.output}")
        else:
            print(output_text)

        print(f"\nPipeline ID: {result['pipeline_id']}")
        print(f"Judge score: {result['judge'].score}/100")
        print(f"Decision: {result['judge'].decision}")
        print(f"Approved: {result['approved']}")
        print(f"Iterations: {result['iterations']}")
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()
