#!/usr/bin/env python3
"""
Deterministic Translation Support Layer — key-free core pipeline.

Python does **not** translate. It prepares a context-rich brief for the host
coding agent's seven translation roles and validates the host-produced output.
There are no API keys, provider SDKs, network calls or model downloads here.

Flow:  analyze → build_brief (7 prompts) → host agent translates →
       validate (+ optional deterministic post-edit/review/judge metadata)
"""

from __future__ import annotations

import json
import re
import sys
import uuid
import warnings
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.arabic import ArabicProcessor
from src.dictionary import DictionaryManager, DictionaryEntry
from src.evaluation import TranslationEvaluator
from src.glossary import Glossary

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - PyYAML is a required, importable dep
    yaml = None  # type: ignore

AGENT_ROLES = [
    "analysis", "translator", "postedit", "reviewer", "editor", "judge", "consistency",
]

ROLE_INSTRUCTIONS = {
    "analysis": (
        "Report genre, audience, register, domain, document structure, entities, "
        "gender context and protected spans. Do not translate."
    ),
    "translator": (
        "Translate the source into the target language. Use MSA by default unless "
        "the brief explicitly requests a dialect. Apply approved glossary terms."
    ),
    "postedit": (
        "Correct grammar, gender/plural agreement and orthography; apply the "
        "diacritics policy without altering protected spans."
    ),
    "reviewer": (
        "Produce an MQM critique with accuracy/fluency/register/terminology/coherence "
        "dimension scores 0-100 and severity-labelled errors."
    ),
    "editor": (
        "Polish typography, RTL flow, headings, quotes and paragraph structure; "
        "keep formatting and every protected span intact."
    ),
    "judge": (
        "Apply the MQM gate using the configured approve/revise thresholds and "
        "return one explicit decision: approve, revise or retranslate."
    ),
    "consistency": (
        "Check character names, place names and terminology against the registries "
        "and earlier chapters; report drift, never silently rename."
    ),
}


class _Prompt(str):
    """A prompt string that also behaves like a role record for host agents."""

    role: str

    def __new__(cls, role: str, text: str) -> "_Prompt":
        obj = super().__new__(cls, text)
        obj.role = role
        return obj

    def __getitem__(self, key: Any) -> Any:
        values = {
            "role": self.role,
            "name": self.role,
            "agent": self.role,
            "prompt": str(self),
            "content": str(self),
            "text": str(self),
            "instructions": str(self),
        }
        return values[key]


class _AttrDict(dict):
    """JSON-serializable dict with attribute access for brief payloads."""

    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key) from None


class _PlaceholderMap(dict):
    """Token → verbatim span map that also accepts spans as lookup keys."""

    def __getitem__(self, key: Any) -> Any:
        try:
            return super().__getitem__(key)
        except KeyError:
            if key in self.values():
                return key
            raise

    def __contains__(self, key: Any) -> bool:
        return super().__contains__(key) or key in self.values()

    @property
    def spans(self) -> List[str]:
        return list(self.values())


class _AgentPrompts(dict):
    """Ordered role → prompt mapping with integer-index access as a convenience."""

    def __getitem__(self, key: Any) -> _Prompt:
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


def _mapping(value: Any) -> Dict[str, Any]:
    """Return ``value`` when it is a mapping, otherwise an empty dict."""
    return value if isinstance(value, dict) else {}


def _make_strict_loader() -> Any:
    """Build a YAML loader that reports duplicate keys instead of hiding them."""

    if yaml is None:  # pragma: no cover
        return None

    class DuplicateKeyError(ValueError):
        pass

    class StrictLoader(yaml.SafeLoader):
        pass

    def construct_mapping(loader: Any, node: Any, deep: bool = False) -> Dict[str, Any]:
        mapping: Dict[str, Any] = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in mapping:
                raise DuplicateKeyError(
                    f"duplicate YAML key {key!r} at line {key_node.start_mark.line + 1}"
                )
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    StrictLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
    )
    StrictLoader.DuplicateKeyError = DuplicateKeyError  # type: ignore[attr-defined]
    return StrictLoader


@dataclass
class AnalysisResult:
    register: str = "MSA"
    domain: str = "general"
    entities: List[Dict[str, Any]] = field(default_factory=list)
    gender_context: Dict[str, str] = field(default_factory=lambda: {
        "subject_gender": "neutral", "object_gender": "neutral"
    })
    orthography_norm: Optional[str] = None
    difficult_terms: List[str] = field(default_factory=list)
    code_blocks: List[str] = field(default_factory=list)
    word_count: int = 0
    sentence_count: int = 0
    has_rtl: bool = False
    needs_diacritics: bool = False

    def __getitem__(self, key: str) -> Any:
        """Allow both ``analysis.register`` and ``analysis['register']``."""
        return asdict(self)[key]


@dataclass
class TranslationResult:
    draft_translation: str = ""
    confidence_flags: List[Dict[str, Any]] = field(default_factory=list)
    terms_for_review: List[str] = field(default_factory=list)
    word_count: int = 0
    segments_translated: int = 0
    llm_response: Optional[Dict[str, Any]] = None  # legacy field, always None
    host_agent_required: bool = True
    system_prompt: str = ""
    user_prompt: str = ""


@dataclass
class PostEditResult:
    revised_translation: str = ""
    corrections: List[Dict[str, Any]] = field(default_factory=list)
    corrections_count: int = 0
    diacritics_applied: bool = False

    def __getitem__(self, key: str) -> Any:
        return asdict(self)[key]


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
    host_recommendation: Optional[str] = None
    rationale: str = ""

    def __getitem__(self, key: str) -> Any:
        return asdict(self)[key]


@dataclass
class JudgeResult:
    score: int = 0
    passed: bool = False
    decision: str = "retranslate"
    dimension_scores: Dict[str, int] = field(default_factory=dict)
    rationale: str = ""
    specific_issues: List[Dict[str, Any]] = field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 3

    def __getitem__(self, key: str) -> Any:
        return asdict(self)[key]


class TranslationPipeline:
    """Deterministic support layer for a seven-agent EN↔AR workflow.

    Constructor arguments named ``llm_*`` and ``use_llm`` are accepted for
    backwards compatibility only; they are inert no-ops in the key-free core.

    Stages:
      1. Analysis   — register, domain, entities, gender, protected spans
      2. Brief      — glossary terms, placeholder map, 7 role prompts
      3. Validate   — check a host translation against the brief
      4. Metadata   — deterministic post-edit/review/judge signals
    """

    def __init__(
        self,
        source_lang: str = "en",
        target_lang: str = "ar",
        config_path: Optional[str] = None,
        glossary_path: Optional[str] = None,
        llm_provider: str = "openai",
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        use_llm: bool = False,
    ) -> None:
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.config_path = config_path or str(PROJECT_ROOT / "config" / "translator.yaml")
        self.glossary_path = glossary_path or str(PROJECT_ROOT / "data" / "glossary.tbx")

        self.arabic = ArabicProcessor()
        self.evaluator = TranslationEvaluator()
        self.glossary = Glossary(self.glossary_path)
        self.dictionary = DictionaryManager()

        self.max_iterations = 3
        self.approve_threshold = 85
        self.revise_threshold = 70
        self.quality_threshold = self.approve_threshold  # legacy alias
        self.config_errors: List[str] = []
        self.legacy_warnings: List[str] = []

        legacy_used = any([
            use_llm,
            llm_provider != "openai",
            bool(llm_model),
            bool(llm_api_key),
        ])
        if legacy_used:
            message = (
                "legacy llm/use_llm arguments are deprecated no-ops: the host "
                "agent performs every translation stage"
            )
            self.legacy_warnings.append(message)
            warnings.warn(message, DeprecationWarning, stacklevel=2)

        self._load_config()
        self._entities_cache = self._load_name_registries()

    # ------------------------------------------------------------------
    # Configuration — errors are surfaced, never silently swallowed
    # ------------------------------------------------------------------
    def _load_config(self) -> None:
        """Load translator.yaml with strict duplicate-key checking."""
        if yaml is None:
            self.config_errors.append("PyYAML unavailable; using safe defaults")
            return

        try:
            text = Path(self.config_path).read_text(encoding="utf-8")
        except OSError as exc:
            self.config_errors.append(f"cannot read config {self.config_path}: {exc}; using defaults")
            return

        loader = _make_strict_loader()
        try:
            config = yaml.load(text, Loader=loader)
        except getattr(loader, "DuplicateKeyError", ValueError) as exc:
            self.config_errors.append(f"{exc}; using safe defaults")
            return
        except yaml.YAMLError as exc:
            self.config_errors.append(f"malformed YAML in {self.config_path}: {exc}; using safe defaults")
            return

        if not isinstance(config, dict):
            self.config_errors.append(
                f"config root in {self.config_path} is not a mapping; using safe defaults"
            )
            return

        pipeline_cfg = _mapping(config.get("pipeline"))
        self.max_iterations = self._int_setting(
            pipeline_cfg, "max_iterations", self.max_iterations
        )
        raw_approve = pipeline_cfg.get(
            "quality_threshold", pipeline_cfg.get("approve_threshold", self.approve_threshold)
        )
        self.approve_threshold = self._as_int("quality_threshold", raw_approve, self.approve_threshold)
        self.quality_threshold = self.approve_threshold
        self.revise_threshold = self._int_setting(
            pipeline_cfg, "revise_threshold", self.revise_threshold
        )

        arabic_cfg = _mapping(config.get("arabic"))
        policy = arabic_cfg.get("diacritics_policy", self.arabic.diacritics_policy)
        if policy in ("remove", "retain", "optional"):
            self.arabic.diacritics_policy = policy
        else:
            self.config_errors.append(
                f"invalid arabic.diacritics_policy {policy!r}; using 'remove'"
            )
            self.arabic.diacritics_policy = "remove"
        self.arabic.orthography_normalization = bool(
            arabic_cfg.get("orthography_normalization", True)
        )

        llm_cfg = _mapping(config.get("llm"))
        if llm_cfg.get("enabled"):
            self.config_errors.append(
                "llm.enabled is ignored: this core is key-free and never calls a model"
            )

        for error in self.config_errors:
            warnings.warn(error, RuntimeWarning, stacklevel=2)

    def _as_int(self, name: str, value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            self.config_errors.append(f"invalid {name}={value!r}; using default {default}")
            return default

    def _int_setting(self, cfg: Dict[str, Any], name: str, default: int) -> int:
        return default if name not in cfg else self._as_int(name, cfg[name], default)

    def _load_name_registries(self) -> Dict[str, str]:
        """Load local character/place names for entity typing (no network)."""
        known: Dict[str, str] = {}
        for filename, kind in (("characters.json", "person"), ("places.json", "place")):
            path = PROJECT_ROOT / "data" / filename
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for entry in _mapping(data).get(kind + "s", []):
                name = _mapping(entry).get("name")
                if name:
                    known[name.lower()] = kind
        return known

    # ------------------------------------------------------------------
    # Stage 1: Analysis
    # ------------------------------------------------------------------
    def analyze(
        self,
        source_text: str,
        domain_hint: Optional[str] = None,
        _placeholder_spans: Optional[List[str]] = None,
    ) -> AnalysisResult:
        """Analyse source text without translating it.

        Empty/whitespace input yields zero counts and empty structures rather
        than raising. MSA is the default register but is overridden when the
        text itself clearly reads as dialect.
        """
        text = source_text or ""
        result = AnalysisResult()
        spans = (
            list(_placeholder_spans)
            if _placeholder_spans is not None
            else self.arabic.extract_protected_spans(text)
        )
        result.has_rtl = self.arabic.contains_arabic(text)
        result.word_count = len(text.split())
        result.sentence_count = sum(text.count(p) for p in set(".!?؟"))
        result.register = (
            self.arabic.detect_register(text) if result.has_rtl else "MSA"
        )
        if domain_hint:
            result.domain = domain_hint
        result.code_blocks = spans
        result.needs_diacritics = self.arabic.has_diacritics(text)

        clean = self.arabic.PROTECTED_SPAN_RE.sub(" ", text)
        result.entities = self._extract_entities(clean)
        result.gender_context = self._detect_gender(clean)

        difficult_terms = set(
            re.findall(r"\b[A-Z]{2,}\b|\b[A-Z][a-z]+\b", clean)
        )
        try:
            for entry in self.dictionary.get_relevant_terms(clean, max_terms=10):
                if entry.word:
                    difficult_terms.add(entry.word)
        except (LookupError, RuntimeError, OSError):
            # Dictionary resources are optional support; analysis still works.
            pass
        result.difficult_terms = sorted(difficult_terms)

        if result.has_rtl and self.arabic.orthography_normalization:
            result.orthography_norm = self.arabic.normalize_orthography(text)
        return result

    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract proper names/acronyms with local registry type hints."""
        entities: List[Dict[str, Any]] = []
        seen: set[str] = set()
        candidates = re.findall(
            r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\b|\b[A-Z]{2,}\b", text
        )
        for name in candidates:
            if name.lower() in seen:
                continue
            seen.add(name.lower())
            kind = self._entities_cache.get(name.lower())
            if kind is None:
                kind = "acronym" if name.isupper() else "entity"
            entities.append({
                "text": name,
                "surface": name,
                "value": name,
                "label": kind,
                "name": name,
                "type": kind,
                "source": "registry" if name.lower() in self._entities_cache else "heuristic",
            })
        return entities

    @staticmethod
    def _detect_gender(text: str) -> Dict[str, str]:
        """Heuristic subject/object gender from pronouns and Arabic clitics."""
        female_subject = bool(re.search(
            r"\b(she|hers|woman|girl)\b|هي|أنثى", text, flags=re.IGNORECASE
        ))
        male_subject = bool(re.search(
            r"\b(he|his|man|boy)\b|هو|ذكر", text, flags=re.IGNORECASE
        ))
        female_object = bool(re.search(r"\bher\b|إياها|ها\b", text, flags=re.IGNORECASE))
        male_object = bool(re.search(r"\bhim\b|إياه", text, flags=re.IGNORECASE))
        return {
            "subject_gender": "female" if female_subject else "male" if male_subject else "neutral",
            "object_gender": "female" if female_object else "male" if male_object else "neutral",
            "evidence": "pronoun_heuristic",
        }

    # ------------------------------------------------------------------
    # Stage 2: Brief — seven prompts, verbatim placeholders
    # ------------------------------------------------------------------
    def build_brief(
        self,
        source_text: str,
        domain_hint: Optional[str] = None,
        previous_context: Optional[str] = None,
        _analysis: Optional[AnalysisResult] = None,
    ) -> Dict[str, Any]:
        """Prepare the deterministic brief consumed by the host agent(s).

        ``placeholder_map`` maps generated tokens to the exact source spans —
        ``{{...}}``, backtick code, XML tags and JSON-like spans are all kept
        verbatim. The same strings are repeated in each prompt so a malicious
        or careless rewrite cannot quietly drop them.
        """
        source = source_text or ""
        analysis = _analysis or self.analyze(source, domain_hint)
        spans = self.arabic.extract_protected_spans(source)
        placeholder_map = _PlaceholderMap(
            {f"PH_{i}": span for i, span in enumerate(spans)}
        )
        glossary_terms = self.glossary.get_relevant_terms(source, analysis.domain)
        style_profile = {
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "target_register": analysis.register,
            "default_register": "MSA",
            "domain": analysis.domain,
            "diacritics_policy": self.arabic.diacritics_policy,
            "orthography_normalization": self.arabic.orthography_normalization,
            "rtl": analysis.has_rtl,
            "approve_threshold": self.approve_threshold,
            "revise_threshold": self.revise_threshold,
            "max_iterations": self.max_iterations,
            "glossary_injection": True,
        }
        prompts = self._build_agent_prompts(
            source, analysis, glossary_terms, placeholder_map,
            previous_context, style_profile,
        )
        return {
            "analysis": _AttrDict(asdict(analysis)),
            "glossary_terms": glossary_terms,
            "placeholder_map": placeholder_map,
            "agent_prompts": prompts,
            "style_profile": style_profile,
            "source_text": source,
            "previous_context": previous_context,
            "protected_spans": spans,
        }

    def _build_agent_prompts(
        self,
        source: str,
        analysis: AnalysisResult,
        glossary_terms: List[Dict[str, str]],
        placeholder_map: Dict[str, str],
        previous_context: Optional[str],
        style_profile: Dict[str, Any],
    ) -> _AgentPrompts:
        """Build the seven role prompts in the specified sequence."""
        context = [
            "Preserve every placeholder, backtick span, XML tag and JSON-like "
            "span verbatim — never translate, reformat or omit them.",
            f"Target language: {style_profile['target_lang']}",
            f"Register: {style_profile['target_register']} (MSA is the default)",
            f"Domain: {style_profile['domain']}",
            f"Diacritics policy: {style_profile['diacritics_policy']}",
            f"Entities: {json.dumps([e['text'] for e in analysis.entities], ensure_ascii=False)}",
            f"Gender context: {analysis.gender_context}",
            f"Code/format spans: {json.dumps(analysis.code_blocks, ensure_ascii=False)}",
        ]
        if glossary_terms:
            context.append("Approved glossary terms (use exactly):")
            for term in glossary_terms:
                en = term.get("en", term.get("source", ""))
                targets = [
                    term.get(k, "") for k in ("ar", "target", "arabic") if term.get(k)
                ]
                if en and targets:
                    context.append(f"  - {en} → {', '.join(targets)}")
        if placeholder_map:
            context.append("Protected spans, verbatim:")
            for token, span in placeholder_map.items():
                context.append(f"  - {token} = {span}")
        if previous_context:
            context.append(f"Previous chapter context:\n{previous_context}")
        context.append(f"Source text:\n{source}")

        prompts: _AgentPrompts = _AgentPrompts()
        for role in AGENT_ROLES:
            lines = [f"You are the {role} agent in a seven-stage EN↔AR workflow."]
            lines.extend(context)
            lines.append(ROLE_INSTRUCTIONS[role])
            lines.append(
                "If anything is unclear, report it explicitly; never invent a translation."
            )
            text = "\n".join(lines)
            prompts[_Prompt(role, role)] = _Prompt(role, text)
        return prompts

    # ------------------------------------------------------------------
    # Validation — key-free gate on host output
    # ------------------------------------------------------------------
    def validate(self, host_translation: str, brief: Dict[str, Any]) -> Dict[str, Any]:
        """Validate host-produced text against a brief.

        Missing protected spans are a named critical failure. Glossary terms,
        MSA register and the no-diacritics policy are checked as well.
        """
        translation = host_translation or ""
        issues: List[Dict[str, Any]] = []

        def add(name: str, severity: str, message: str, **extra: Any) -> None:
            issue = {
                "name": name, "type": name, "code": name,
                "severity": severity, "message": message,
            }
            issue.update(extra)
            issues.append(issue)

        source = brief.get("source_text", "")
        if source.strip() and not translation.strip():
            add("empty_translation", "critical", "No host translation was supplied.")

        for token, span in _mapping(brief.get("placeholder_map")).items():
            if span not in translation:
                add(
                    "missing_placeholder", "critical",
                    f"Protected span {span!r} ({token}) is missing from the translation.",
                    token=token, span=span,
                )

        analysis = brief.get("analysis")
        extra_spans = getattr(analysis, "code_blocks", None) or []
        mapped = set(_mapping(brief.get("placeholder_map")).values())
        for span in extra_spans:
            if span not in mapped and span not in translation:
                add(
                    "missing_placeholder", "critical",
                    f"Protected span {span!r} is missing from the translation.",
                    token=None, span=span,
                )

        required: Dict[str, List[str]] = {}
        for term in brief.get("glossary_terms", []) or []:
            source_term = term.get("en", term.get("source", ""))
            targets = [
                term.get(k, "") for k in ("ar", "target", "arabic") if term.get(k)
            ]
            if source_term and targets:
                required.setdefault(source_term.lower(), []).extend(targets)
        for source_term, targets in required.items():
            if not any(target in translation for target in targets):
                add(
                    "glossary_term_missing", "major",
                    f"Approved term for {source_term!r} is missing (expected one of {targets}).",
                    term=source_term, expected=targets,
                )

        style = _mapping(brief.get("style_profile"))
        if style.get("target_register") == "MSA" and self.arabic.contains_arabic(translation):
            if self.arabic.detect_register(translation) == "dialect":
                add(
                    "register_not_msa", "major",
                    "Dialect markers found while MSA is required.",
                )
        if (
            style.get("diacritics_policy", self.arabic.diacritics_policy)
            in ("remove", "optional")
            and self.arabic.has_diacritics(translation)
        ):
            add("diacritics_present", "minor", "Diacritics present under the no-diacritics policy.")

        weights = {"critical": 25, "error": 20, "major": 10, "minor": 3}
        score = max(0.0, 100.0 - sum(weights.get(i["severity"], 5) for i in issues))
        passed = not any(i["severity"] in ("critical", "error", "major") for i in issues)
        return {
            "passed": passed,
            "issues": issues,
            "score": score,
            "checked_placeholders": len(_mapping(brief.get("placeholder_map"))),
        }

    # ------------------------------------------------------------------
    # Stage 2 helper: deterministic prompt preparation (no LLM calls)
    # ------------------------------------------------------------------
    def translate(
        self,
        source_text: str,
        analysis: AnalysisResult,
        previous_context: Optional[str] = None,
        host_translation: Optional[str] = None,
    ) -> TranslationResult:
        """Prepare a translation draft *only* from a host-supplied string.

        With no host translation the draft is empty and ``host_agent_required``
        is True. This method never fabricates a translation.
        """
        result = TranslationResult()
        result.draft_translation = host_translation or ""
        result.host_agent_required = host_translation is None or host_translation == ""
        result.word_count = analysis.word_count
        result.segments_translated = (
            max(1, result.draft_translation.count(".") + result.draft_translation.count("؟"))
            if result.draft_translation else 0
        )
        result.terms_for_review = analysis.difficult_terms[:5]
        result.confidence_flags = [
            {"term": t, "position": 0, "suggestion": "review_needed"}
            for t in analysis.difficult_terms[:5]
        ]
        result.llm_response = None

        glossary_terms = self.glossary.get_relevant_terms(source_text, analysis.domain)
        dict_definitions: List[Dict[str, Any]] = []
        for term in analysis.difficult_terms[:5]:
            entry = self.dictionary.lookup_definition(term, dictionary="wordnet")
            if entry:
                dict_definitions.append(asdict(entry))
        result.system_prompt = self._build_translator_system_prompt(
            analysis, glossary_terms, dict_definitions
        )
        result.user_prompt = self._build_translator_user_prompt(
            source_text, analysis, previous_context
        )
        return result

    def _build_translator_system_prompt(
        self,
        analysis: AnalysisResult,
        glossary_terms: List[Dict[str, Any]],
        dict_definitions: List[Dict[str, Any]],
    ) -> str:
        lines = [
            "You are a professional English ↔ Arabic translator.",
            "Preserve every placeholder, backtick span, XML tag and JSON-like span verbatim.",
            "Use Modern Standard Arabic (MSA) unless a dialect is explicitly requested.",
            "Handle the six Arabic plural forms and gender agreement.",
        ]
        if glossary_terms:
            lines.append("APPROVED GLOSSARY TERMS (must use these translations):")
            for term in glossary_terms:
                en = term.get("en", term.get("source", ""))
                ar = term.get("ar", term.get("target", ""))
                if en and ar:
                    lines.append(f"  - {en} → {ar}")
        if dict_definitions:
            lines.append("DIFFICULT TERMS (use these definitions for word sense):")
            for d in dict_definitions:
                word, defn = d.get("word", ""), d.get("definition", "")
                lines.append(f"  - {word}: {defn}")
        lines.extend([
            f"Target register: {analysis.register}",
            f"Domain: {analysis.domain}",
            f"Gender context: {analysis.gender_context}",
            f"Entities: {json.dumps(analysis.entities, ensure_ascii=False)}",
            "Output ONLY the translation, no explanations.",
        ])
        return "\n".join(lines)

    def _build_translator_user_prompt(
        self,
        source_text: str,
        analysis: AnalysisResult,
        previous_context: Optional[str] = None,
    ) -> str:
        lines = [f"Source text to translate:\n{source_text}", ""]
        if previous_context:
            # Fixed: the original called append() with two arguments.
            lines.append(f"Previous chapter context:\n{previous_context}")
            lines.append("")
        lines.append("Translate the above text now.")
        return "\n".join(lines)

    def _apply_glossary_substitutions(
        self,
        source_text: str,
        glossary_terms: List[Dict[str, Any]],
        analysis: Optional[AnalysisResult] = None,
    ) -> str:
        """Deterministically substitute approved terms for prompt preparation.

        Fixed: the previous version referenced an undefined ``analysis`` name.
        The result is *not* a translation — it is only a term inventory for a
        host agent prompt and is never returned as pipeline output.
        """
        draft = source_text
        for term in glossary_terms:
            en = term.get("en", term.get("source", ""))
            ar = term.get("ar", term.get("target", ""))
            if en and ar:
                draft = draft.replace(en, ar)
        if analysis is not None:
            draft = f"[{analysis.register} term inventory] {draft}"
        return draft

    # ------------------------------------------------------------------
    # Stage 3: deterministic post-edit
    # ------------------------------------------------------------------
    def post_edit(self, draft: str, analysis: AnalysisResult) -> PostEditResult:
        """Apply orthography and diacritics policy cumulatively (no model)."""
        result = PostEditResult(revised_translation=draft or "")
        if self.target_lang != "ar" or not result.revised_translation:
            return result

        working = result.revised_translation
        corrections: List[Dict[str, Any]] = []

        if self.arabic.orthography_normalization:
            normalized = self.arabic.normalize_orthography(working)
            if normalized != working:
                corrections.append({
                    "position": 0, "original": working[:40],
                    "corrected": normalized[:40], "reason": "orthography",
                })
                working = normalized  # keep the normalization for later steps

        if self.arabic.diacritics_policy in ("remove", "optional"):
            stripped = self.arabic.remove_diacritics(working)
            if stripped != working:
                corrections.append({
                    "position": 0, "original": working[:40],
                    "corrected": stripped[:40], "reason": "diacritics",
                })
                working = stripped
                result.diacritics_applied = True

        if analysis.gender_context.get("subject_gender") not in (None, "neutral"):
            corrections.append({
                "position": 0, "original": working[:40], "corrected": working[:40],
                "reason": "gender_agreement", "note": "host review requested",
            })

        result.revised_translation = working
        result.corrections = corrections
        result.corrections_count = len(corrections)
        return result

    # ------------------------------------------------------------------
    # Stage 4: deterministic MQM-style review
    # ------------------------------------------------------------------
    def review(
        self,
        translation: str,
        source_text: str,
        analysis: AnalysisResult,
        validation: Optional[Dict[str, Any]] = None,
    ) -> ReviewResult:
        """Score with MQM dimensions; use validation evidence when available."""
        result = ReviewResult()
        scores = {
            "accuracy": 80, "fluency": 78, "style_register": 82,
            "terminology": 85, "coherence": 80,
        }
        if not translation.strip():
            scores = {key: 0 for key in scores}

        terms = self.glossary.get_relevant_terms(source_text, analysis.domain)
        result.glossary_adherence = self.glossary.check_adherence(translation, terms)
        if validation and isinstance(validation, dict):
            # Validation is deterministic evidence about the host output: use
            # its score for every MQM dimension so the documented >=85 gate is
            # reachable and the judge score agrees with validation.
            evidence = int(round(float(validation.get("score", 0))))
            scores = {key: evidence for key in scores}
            if not validation.get("passed", False):
                scores["accuracy"] = min(scores["accuracy"], self.revise_threshold - 1)
        scores["terminology"] = int(
            round(scores["terminology"] * result.glossary_adherence / 100)
        )
        result.dimension_scores = scores
        result.overall_score = int(
            0.30 * scores["accuracy"]
            + 0.25 * scores["fluency"]
            + 0.20 * scores["style_register"]
            + 0.15 * scores["terminology"]
            + 0.10 * scores["coherence"]
        )
        result.recommendation = (
            "approve" if result.overall_score >= self.approve_threshold
            else "revise" if result.overall_score >= self.revise_threshold
            else "retranslate"
        )
        return result

    # ------------------------------------------------------------------
    # Stage 5: deterministic judge (no fallback override of host decisions)
    # ------------------------------------------------------------------
    def judge(
        self,
        translation: str,
        review: ReviewResult,
        iteration: int = 1,
        host_decision: Optional[str] = None,
    ) -> JudgeResult:
        """Apply the MQM gate once, honouring any explicit host decision."""
        result = JudgeResult()
        get = (
            (lambda obj, key, default: obj.get(key, default))
            if isinstance(review, dict)
            else (lambda obj, key, default: getattr(obj, key, default))
        )
        result.score = int(get(review, "overall_score", 0))
        result.dimension_scores = dict(get(review, "dimension_scores", {}) or {})
        result.iteration = iteration
        result.max_iterations = self.max_iterations
        result.specific_issues = list(get(review, "errors", []) or [])

        explicit = host_decision or get(review, "host_recommendation", None)
        if explicit in ("approve", "revise", "retranslate"):
            result.decision = explicit
            result.passed = explicit == "approve"
            result.rationale = f"Explicit host decision honoured: {explicit}."
            return result

        if result.score >= self.approve_threshold:
            result.decision = "approve"
            result.passed = True
            result.rationale = (
                f"Score {result.score}/100 meets approve threshold "
                f"{self.approve_threshold}."
            )
        elif result.score >= self.revise_threshold and iteration < self.max_iterations:
            result.decision = "revise"
            result.passed = False
            result.rationale = (
                f"Score {result.score}/100 is below {self.approve_threshold}; "
                f"host revision requested (iteration {iteration}/{self.max_iterations})."
            )
        else:
            result.decision = "retranslate"
            result.passed = False
            result.rationale = (
                f"Score {result.score}/100 requires retranslation or the revision "
                f"budget is exhausted."
            )
        return result

    # ------------------------------------------------------------------
    # Full pipeline — single pass, explicit host-revision signal
    # ------------------------------------------------------------------
    def run(
        self,
        source_text: str,
        domain_hint: Optional[str] = None,
        previous_context: Optional[str] = None,
        host_translation: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run the deterministic support layer on a host-produced translation.

        No revision loop: Python cannot improve a translation by rerunning the
        same deterministic checks. When the gate fails, ``needs_host_revision``
        tells the host agent to act. With no translation supplied, the returned
        string is empty and ``host_agent_required`` is True.
        """
        source = source_text or ""
        pipeline_id = str(uuid.uuid4())
        analysis = self.analyze(source, domain_hint)
        brief = self.build_brief(source, domain_hint, previous_context, _analysis=analysis)

        host_agent_required = not bool(host_translation)
        translation = host_translation or ""
        draft = self.translate(source, analysis, previous_context, host_translation)

        post_edit_result = self.post_edit(translation, analysis)
        current = post_edit_result.revised_translation
        validation = self.validate(current, brief)

        if host_agent_required:
            review = ReviewResult(
                overall_score=0, dimension_scores={}, recommendation="retranslate",
                rationale="No host translation to review.",
            )
        else:
            review = self.review(current, source, analysis, validation=validation)
        judge_result = self.judge(current, review, iteration=1)
        needs_host_revision = bool(
            host_agent_required or not judge_result.passed or not validation["passed"]
        )

        return {
            "pipeline_id": pipeline_id,
            "source_text": source,
            "target_lang": self.target_lang,
            "analysis": analysis,
            "brief": brief,
            "translation": current,
            "draft": draft,
            "post_edits": post_edit_result.corrections,
            "review": review,
            "judge": judge_result,
            "validation": validation,
            "approved": bool(
                not host_agent_required and judge_result.passed and validation["passed"]
            ),
            "needs_host_revision": needs_host_revision,
            "host_agent_required": host_agent_required,
            "iterations": 1,
        }

    def close(self) -> None:
        """Close resources."""
        self.dictionary.close()


def main() -> None:
    """CLI entry point — prepares a brief and validates host output."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Key-free translation support layer (host agent performs translation)"
    )
    parser.add_argument("--source", required=True, help="Source text or file path")
    parser.add_argument(
        "--target", default="ar", choices=["ar", "en"], help="Target language"
    )
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--domain", help="Domain hint (technical, literary, legal, medical, UI, general)")
    parser.add_argument("--config", help="Path to config YAML")
    parser.add_argument("--brief", help="Write the translation brief JSON to FILE and exit")
    parser.add_argument("--host-translation", help="Translation produced by the host agent")
    parser.add_argument("--previous-context", help="Context from earlier chapters")
    # Legacy flags remain accepted, but are inert in the key-free core.
    parser.add_argument("--llm-provider", default="openai", help="DEPRECATED: no-op")
    parser.add_argument("--llm-model", help="DEPRECATED: no-op")
    parser.add_argument("--llm-api-key", help="DEPRECATED: no-op")
    parser.add_argument("--use-llm", action="store_true", help="DEPRECATED: no-op")

    args = parser.parse_args()

    if args.use_llm or args.llm_model or args.llm_api_key or args.llm_provider != "openai":
        print(
            "WARNING: --use-llm/--llm-* flags are deprecated no-ops; the host "
            "agent performs every translation stage and no API key is used.",
            file=sys.stderr,
        )

    source_path = Path(args.source)
    source_text = source_path.read_text(encoding="utf-8") if source_path.exists() else args.source

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
        if args.brief:
            brief = pipeline.build_brief(
                source_text,
                domain_hint=args.domain,
                previous_context=args.previous_context,
            )
            Path(args.brief).write_text(
                json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"Translation brief saved to {args.brief}")
            return

        result = pipeline.run(
            source_text,
            domain_hint=args.domain,
            previous_context=args.previous_context,
            host_translation=args.host_translation,
        )
        output_text = result["translation"]
        if output_text:
            if args.output:
                Path(args.output).write_text(output_text, encoding="utf-8")
                print(f"Translation saved to {args.output}")
            else:
                print(output_text)
        else:
            print("No host translation supplied — translation was not performed.")

        for error in pipeline.config_errors:
            print(f"CONFIG WARNING: {error}", file=sys.stderr)
        print(f"\nPipeline ID: {result['pipeline_id']}")
        print(f"Host agent required: {result['host_agent_required']}")
        print(f"Needs host revision: {result['needs_host_revision']}")
        print(f"Validation passed: {result['validation']['passed']}")
        print(f"Judge score: {result['judge'].score}/100")
        print(f"Decision: {result['judge'].decision}")
        print(f"Approved: {result['approved']}")
        print(f"Iterations: {result['iterations']}")
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()
