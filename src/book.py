#!/usr/bin/env python3
"""
Book Translation Workflow Module.

Handles chapter-by-chapter translation with cross-chapter consistency:
- Character registry (names, aliases, pronouns, titles)
- Places/world-building registry
- Dynamic glossary (updated per chapter)
- Manifest with integrity checks (resumable)
- Two-phase workflow: ``prepare_chapter`` writes a context-rich brief,
  ``assemble_chapter`` validates the host-produced translation and writes it.

The Python layer is deterministic: it never calls an LLM itself. Briefs and
validation come from :class:`~src.pipeline.TranslationPipeline` (Task A
contract: ``build_brief(text, domain_hint=None, previous_context=None)`` and
``validate(host_translation, brief)``). A local fallback is used only when
those methods are not yet available, so this module remains importable and
runnable in a partially-migrated checkout.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, cast

from src.book_formats import BookStructure, get_handler, list_supported_formats
from src.pipeline import TranslationPipeline

# Portable repository root — derived from this file, never a stale absolute path.
REPO_ROOT = Path(__file__).resolve().parent.parent

_ARABIC_TOKEN_RE = re.compile(r"[\u0600-\u06FF]+")
_PLACEHOLDER_PATTERNS = (
    r"\{\{[^}]+\}\}",  # {{token}}
    r"`[^`]+`",  # `code`
    r"<[^>]+>",  # <xml/>
    r"\{\s*\"[^\"]+\"\s*:\s*[^}]+\}",  # {"id": 7}
)


def _to_dict(value: Any) -> dict[str, Any] | None:
    """Best-effort conversion of a dataclass/object to a plain dict."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if hasattr(value, "__dict__"):
        return {k: v for k, v in vars(value).items() if not k.startswith("_")}
    return None


def _arabic_tokens(text: str) -> list[str]:
    return _ARABIC_TOKEN_RE.findall(text or "")


def _json_safe(value: Any) -> Any:
    """Recursively convert a brief payload into JSON-serialisable primitives.

    Task A's brief uses dict/str subclasses and dataclasses; this normalises
    all of them so a brief can be persisted and reloaded in a new process.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value if not isinstance(value, str) else str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if is_dataclass(value) and not isinstance(value, type):
        return _json_safe(asdict(value))
    if hasattr(value, "__dict__"):
        return _json_safe(vars(value))
    return str(value)


def _near_renderings(text: str, canonical: str) -> list[str]:
    """Arabic sequences that start like ``canonical`` but differ from it."""
    canon = _arabic_tokens(canonical)
    if not canon:
        return []
    words = _arabic_tokens(text)
    found: list[str] = []
    for i, word in enumerate(words):
        if word != canon[0]:
            continue
        seq = " ".join(words[i : i + len(canon)])
        if seq != canonical and seq not in found:
            found.append(seq)
    return found


def _extract_placeholders(source_text: str) -> dict[str, str]:
    """Map every verbatim placeholder found in ``source_text`` to itself."""
    found: dict[str, str] = {}
    for pattern in _PLACEHOLDER_PATTERNS:
        for token in re.findall(pattern, source_text or ""):
            found[token] = token
    return found


def _chapter_slug(chapter_id: Any) -> str:
    """Normalise a chapter id (1, '2', 'chapter_003') into a file slug."""
    match = re.search(r"(\d+)", str(chapter_id))
    if match:
        return f"{int(match.group(1)):03d}"
    return re.sub(r"\W+", "_", str(chapter_id)).strip("_") or "000"


def _judge_score(result: Any) -> int | None:
    """Read a judge score from either a JudgeResult dataclass or a dict."""
    if not isinstance(result, dict):
        return None
    judge = result.get("judge")
    if judge is None:
        return None
    if isinstance(judge, dict):
        return judge.get("score")
    return getattr(judge, "score", None)


def _approved(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    value = result.get("approved")
    if isinstance(value, bool):
        return value
    judge = result.get("judge")
    if isinstance(judge, dict):
        return bool(judge.get("passed"))
    return bool(getattr(judge, "passed", False)) if judge is not None else False


@dataclass
class CharacterEntry:
    name: str
    aliases: list[str] = field(default_factory=list)
    arabic_name: str = ""
    arabic_aliases: list[str] = field(default_factory=list)
    pronouns: str = "neutral"
    title: str = ""
    first_chapter: int = 0
    description: str = ""


@dataclass
class PlaceEntry:
    name: str
    arabic_name: str = ""
    place_type: str = "other"  # city | country | building | region | other
    description: str = ""


@dataclass
class ChapterManifest:
    chapter: int
    title: str
    source_path: str
    output_path: str
    checksum: str
    status: str = "pending"  # pending | translated | reviewed | completed
    pipeline_id: str | None = None
    judge_score: int | None = None


class BookTranslator:
    """Book translation workflow with cross-chapter consistency."""

    def __init__(
        self,
        project_root: str | None = None,
        target_lang: str = "ar",
        output_dir: str | None = None,
        pipeline: Any | None = None,
    ) -> None:
        if project_root is None:
            self.project_root = REPO_ROOT
        else:
            root = Path(project_root)
            self.project_root = root if root.is_absolute() else REPO_ROOT / root
        self.target_lang = target_lang

        self.characters_path = self.project_root / "data" / "characters.json"
        self.places_path = self.project_root / "data" / "places.json"
        self.manifest_path = self.project_root / "data" / "manifest.json"
        self.dynamic_glossary_path = self.project_root / "data" / "dynamic_glossary.json"

        if output_dir is None:
            self.output_dir = self.project_root / "outputs"
        else:
            out = Path(output_dir)
            self.output_dir = out if out.is_absolute() else REPO_ROOT / out
        self.briefs_dir = self.output_dir / "briefs"
        self.chapters_dir = self.output_dir / "chapters"

        self.characters: list[dict[str, Any]] = []
        self.places: list[dict[str, Any]] = []
        self.manifest: list[ChapterManifest] = []
        self.dynamic_glossary: list[dict[str, Any]] = []

        self._load_registries()
        self._load_manifest()

        # Dependency injection keeps tests deterministic and decouples them
        # from Task A landing during a concurrent session.
        self.pipeline = (
            pipeline
            if pipeline is not None
            else TranslationPipeline(source_lang="en", target_lang=target_lang)
        )

    # ------------------------------------------------------------------
    # Registries
    # ------------------------------------------------------------------
    def _load_registries(self) -> None:
        """Load character, place and dynamic-glossary registries."""
        if self.characters_path.exists():
            with open(self.characters_path, encoding="utf-8") as f:
                self.characters = json.load(f).get("characters", [])

        if self.places_path.exists():
            with open(self.places_path, encoding="utf-8") as f:
                self.places = json.load(f).get("places", [])

        if self.dynamic_glossary_path.exists():
            with open(self.dynamic_glossary_path, encoding="utf-8") as f:
                self.dynamic_glossary = json.load(f).get("terms", [])

    def _load_manifest(self) -> None:
        """Load translation manifest."""
        if self.manifest_path.exists():
            with open(self.manifest_path, encoding="utf-8") as f:
                data = json.load(f)
                self.manifest = [ChapterManifest(**m) for m in data]

    def _save_registries(self) -> None:
        """Persist all registries, including the dynamic glossary."""
        self.characters_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.characters_path, "w", encoding="utf-8") as f:
            json.dump({"characters": self.characters}, f, ensure_ascii=False, indent=2)
        with open(self.places_path, "w", encoding="utf-8") as f:
            json.dump({"places": self.places}, f, ensure_ascii=False, indent=2)
        with open(self.dynamic_glossary_path, "w", encoding="utf-8") as f:
            json.dump({"terms": self.dynamic_glossary}, f, ensure_ascii=False, indent=2)

    def _save_manifest(self) -> None:
        """Save translation manifest."""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(
                [
                    {
                        "chapter": m.chapter,
                        "title": m.title,
                        "source_path": m.source_path,
                        "output_path": m.output_path,
                        "checksum": m.checksum,
                        "status": m.status,
                        "pipeline_id": m.pipeline_id,
                        "judge_score": m.judge_score,
                    }
                    for m in self.manifest
                ],
                f,
                ensure_ascii=False,
                indent=2,
            )

    def _upsert_manifest(self, entry: ChapterManifest) -> None:
        existing = next(
            (i for i, m in enumerate(self.manifest) if m.chapter == entry.chapter), None
        )
        if existing is None:
            self.manifest.append(entry)
        else:
            self.manifest[existing] = entry
        self._save_manifest()

    # ------------------------------------------------------------------
    # Brief / validation bridge to the deterministic pipeline
    # ------------------------------------------------------------------
    def _build_brief(
        self,
        source_text: str,
        domain_hint: str | None = None,
        previous_context: str | None = None,
    ) -> dict[str, Any]:
        """Build a brief via ``TranslationPipeline.build_brief``.

        Falls back to a deterministic local brief only when that method is
        unavailable, so the book workflow never crashes mid-migration.
        """
        builder = getattr(self.pipeline, "build_brief", None)
        if callable(builder):
            result = builder(
                source_text,
                domain_hint=domain_hint,
                previous_context=previous_context,
            )
            return result if isinstance(result, dict) else (_to_dict(result) or {})

        # --- fallback (Task A not yet present) ---
        analysis: dict[str, Any] | None = None
        analyzer = getattr(self.pipeline, "analyze", None)
        if callable(analyzer):
            try:
                analysis = _to_dict(analyzer(source_text, domain_hint))
            except TypeError:
                analysis = _to_dict(analyzer(source_text))

        if analysis is None:
            analysis = {
                "register": "MSA",
                "domain": domain_hint or "literary",
                "word_count": len((source_text or "").split()),
                "sentence_count": (source_text or "").count(".")
                + (source_text or "").count("!")
                + (source_text or "").count("?"),
                "entities": [],
                "gender_context": {},
                "code_blocks": list(_extract_placeholders(source_text).keys()),
            }

        glossary_terms: list[dict[str, Any]] = []
        glossary = getattr(self.pipeline, "glossary", None)
        get_terms = getattr(glossary, "get_relevant_terms", None)
        if callable(get_terms):
            try:
                terms = cast(list[Any], get_terms(source_text, domain_hint or "literary")) or []
                for term in terms:
                    as_dict = _to_dict(term) or {}
                    if as_dict:
                        glossary_terms.append(as_dict)
            except Exception:
                pass

        return {
            "analysis": analysis,
            "glossary_terms": glossary_terms,
            "placeholder_map": _extract_placeholders(source_text),
            "agent_prompts": [
                "Analysis Agent prompt",
                "Translator Agent prompt",
                "Post-editor Agent prompt",
                "Reviewer Agent prompt",
                "Editor Agent prompt",
                "Judge Agent prompt",
                "Consistency Agent prompt",
            ],
            "style_profile": {
                "register": "MSA",
                "target_language": self.target_lang,
                "domain": domain_hint or "literary",
            },
            "source_text": source_text,
            "domain_hint": domain_hint,
            "previous_context": previous_context,
        }

    def _validate(self, host_translation: str, brief: dict[str, Any]) -> dict[str, Any]:
        """Validate via ``TranslationPipeline.validate`` with a safe fallback."""
        validator = getattr(self.pipeline, "validate", None)
        if callable(validator):
            result = validator(host_translation, brief)
            if isinstance(result, dict):
                return result
            return _to_dict(result) or {"passed": False, "issues": [], "score": 0}

        # --- fallback: placeholder integrity check ---
        issues: list[dict[str, str]] = []
        placeholder_map = brief.get("placeholder_map", {}) or {}
        for token in placeholder_map:
            if token not in (host_translation or ""):
                issues.append(
                    {
                        "code": "missing_placeholder",
                        "severity": "critical",
                        "detail": f"Missing verbatim placeholder: {token}",
                    }
                )
        score = max(0, 100 - 25 * len(issues))
        return {"passed": not issues, "issues": issues, "score": score}

    # ------------------------------------------------------------------
    # Book format parsing
    # ------------------------------------------------------------------
    def parse_book(self, file_path: str) -> BookStructure:
        """Parse a book file using the appropriate format handler."""
        return get_handler(file_path).parse(file_path)

    def reconstruct_book(
        self,
        structure: BookStructure,
        translations: dict[str, str],
        output_path: str,
    ) -> None:
        """Reconstruct a book with translated segments."""
        handler = get_handler(output_path)
        handler.reconstruct(structure, translations, output_path, language=self.target_lang)

    # ------------------------------------------------------------------
    # Two-phase chapter workflow
    # ------------------------------------------------------------------
    def _brief_path(self, chapter_id: Any) -> Path:
        return self.briefs_dir / f"chapter_{_chapter_slug(chapter_id)}.brief.json"

    def _output_path(self, chapter_id: Any) -> Path:
        return self.chapters_dir / f"chapter_{_chapter_slug(chapter_id)}.ar.txt"

    def prepare_chapter(
        self,
        source_path: str | None = None,
        chapter_id: Any | None = None,
        source_text: str | None = None,
        domain_hint: str | None = "literary",
        previous_context: str | None = None,
        output_dir: str | None = None,
    ) -> dict[str, Any]:
        """Build and persist a translation brief for one chapter.

        ``previous_context`` (chapter 2+) is forwarded verbatim to
        ``build_brief`` so the host agent sees the prior chapter's context.
        """
        if source_text is None:
            if not source_path:
                raise ValueError("prepare_chapter requires source_path or source_text")
            source_text = Path(source_path).read_text(encoding="utf-8")

        if chapter_id is None:
            chapter_id = (
                _chapter_slug(Path(source_path).stem) if source_path else len(self.manifest) + 1
            )

        brief = self._build_brief(source_text, domain_hint, previous_context)

        base = Path(output_dir) if output_dir else self.output_dir
        briefs_dir = base / "briefs"
        briefs_dir.mkdir(parents=True, exist_ok=True)
        brief_path = briefs_dir / f"chapter_{_chapter_slug(chapter_id)}.brief.json"

        record = {
            "chapter_id": chapter_id,
            "source_path": str(source_path) if source_path else None,
            "source_text": source_text,
            "checksum": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
            "domain_hint": domain_hint,
            "previous_context": previous_context,
            "brief": _json_safe(brief),
        }
        brief_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

        numeric_chapter: Any = chapter_id
        match = re.search(r"(\d+)", str(chapter_id))
        if match:
            numeric_chapter = int(match.group(1))

        pipeline_id = None
        if isinstance(brief, dict):
            pipeline_id = brief.get("pipeline_id")

        self._upsert_manifest(
            ChapterManifest(
                chapter=numeric_chapter,
                title=str(chapter_id),
                source_path=str(source_path) if source_path else "",
                output_path=str(base / "chapters" / f"chapter_{_chapter_slug(chapter_id)}.ar.txt"),
                checksum=record["checksum"],
                status="pending",
                pipeline_id=pipeline_id,
            )
        )

        return {
            "chapter": chapter_id,
            "chapter_id": chapter_id,
            "brief_path": str(brief_path),
            "checksum": record["checksum"],
            "previous_context": previous_context,
            "brief": brief,
        }

    def assemble_chapter(
        self,
        chapter_id: Any,
        host_translation: str,
        output_dir: str | None = None,
        output_path: str | None = None,
    ) -> dict[str, Any]:
        """Validate ``host_translation`` against a prepared brief and write it."""
        base = Path(output_dir) if output_dir else self.output_dir
        brief_path = base / "briefs" / f"chapter_{_chapter_slug(chapter_id)}.brief.json"
        if not brief_path.exists():
            raise FileNotFoundError(
                f"No prepared brief for chapter {chapter_id}: {brief_path}. " "Run --prepare first."
            )

        record = json.loads(brief_path.read_text(encoding="utf-8"))
        brief = record.get("brief", {})
        source_text = record.get("source_text", "") or ""

        validation = self._validate(host_translation or "", brief)
        passed = bool(validation.get("passed", False)) if isinstance(validation, dict) else False

        target = (
            Path(output_path)
            if output_path
            else base / "chapters" / f"chapter_{_chapter_slug(chapter_id)}.ar.txt"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(host_translation or "", encoding="utf-8")

        consistency = self.check_consistency(chapter_id, host_translation or "", source_text)
        glossary_terms = brief.get("glossary_terms", []) if isinstance(brief, dict) else []
        registry_updates = self.update_registries_from_chapter(
            chapter_id, host_translation or "", source_text, glossary_terms=glossary_terms
        )

        numeric_chapter: Any = chapter_id
        match = re.search(r"(\d+)", str(chapter_id))
        if match:
            numeric_chapter = int(match.group(1))

        judge_score = validation.get("score") if isinstance(validation, dict) else None
        self._upsert_manifest(
            ChapterManifest(
                chapter=numeric_chapter,
                title=str(chapter_id),
                source_path=record.get("source_path", "") or "",
                output_path=str(target),
                checksum=record.get("checksum", ""),
                status="completed" if passed else "reviewed",
                pipeline_id=(
                    record.get("brief", {}).get("pipeline_id")
                    if isinstance(record.get("brief"), dict)
                    else None
                ),
                judge_score=judge_score,
            )
        )

        return {
            "chapter": chapter_id,
            "chapter_id": chapter_id,
            "output_path": str(target),
            "validation": validation,
            "passed": passed,
            "judge_score": judge_score,
            "consistency": consistency,
            "registry_updates": registry_updates,
        }

    # ------------------------------------------------------------------
    # Consistency
    # ------------------------------------------------------------------
    def check_consistency(
        self,
        chapter_num: Any,
        translation: str,
        source_text: str | None = None,
    ) -> dict[str, Any]:
        """Compare a translation with the registries and return REAL findings."""
        findings: list[dict[str, Any]] = []

        # --- renamed characters ---
        for char in self.characters:
            canonical = char.get("arabic_name", "")
            if not canonical:
                continue
            approved = {canonical} | set(char.get("arabic_aliases") or [])
            near = [n for n in _near_renderings(translation, canonical) if n not in approved]
            if near:
                findings.append(
                    {
                        "type": "renamed_character",
                        "severity": "major",
                        "entity": char.get("name", ""),
                        "expected": canonical,
                        "found": near[0],
                        "chapter": chapter_num,
                        "detail": (
                            f"Character '{char.get('name', '')}' rendered as "
                            f"'{near[0]}' instead of registered '{canonical}'."
                        ),
                    }
                )
                continue
            source_names = [char.get("name", "")] + list(char.get("aliases") or [])
            mentioned = bool(
                source_text and any(n and n.lower() in source_text.lower() for n in source_names)
            )
            if mentioned and not any(a and a in translation for a in approved):
                findings.append(
                    {
                        "type": "untranslated_character",
                        "severity": "major",
                        "entity": char.get("name", ""),
                        "expected": canonical,
                        "found": char.get("name", ""),
                        "chapter": chapter_num,
                        "detail": (
                            f"Registered character '{char.get('name', '')}' is "
                            f"missing its Arabic rendering '{canonical}'."
                        ),
                    }
                )

        # --- changed places ---
        for place in self.places:
            canonical = place.get("arabic_name", "")
            if not canonical:
                continue
            near = [n for n in _near_renderings(translation, canonical) if n != canonical]
            name = place.get("name", "")
            mentioned = bool(source_text and name and name.lower() in source_text.lower())
            if near:
                findings.append(
                    {
                        "type": "changed_place",
                        "severity": "major",
                        "entity": name,
                        "expected": canonical,
                        "found": near[0],
                        "chapter": chapter_num,
                        "detail": (
                            f"Place '{name}' rendered as '{near[0]}' instead of "
                            f"registered '{canonical}'."
                        ),
                    }
                )
            elif mentioned and canonical not in translation:
                findings.append(
                    {
                        "type": "changed_place",
                        "severity": "major",
                        "entity": name,
                        "expected": canonical,
                        "found": name,
                        "chapter": chapter_num,
                        "detail": (
                            f"Approved place rendering '{canonical}' for '{name}' "
                            "is missing from the translation."
                        ),
                    }
                )

        # --- changed glossary renderings ---
        for term in self.dynamic_glossary:
            source = term.get("source", "")
            target = term.get("target", "")
            alternatives = term.get("alternatives") or []
            used_alt = next((a for a in alternatives if a and a in translation), None)
            if used_alt and target and target not in translation:
                findings.append(
                    {
                        "type": "changed_glossary_rendering",
                        "severity": "major",
                        "entity": source,
                        "expected": target,
                        "found": used_alt,
                        "chapter": chapter_num,
                        "detail": (
                            f"Glossary term '{source}' should render as '{target}', "
                            f"but '{used_alt}' was used."
                        ),
                    }
                )
            elif (
                target
                and source
                and target not in translation
                and source_text
                and source.lower() in source_text.lower()
            ):
                findings.append(
                    {
                        "type": "changed_glossary_rendering",
                        "severity": "minor",
                        "entity": source,
                        "expected": target,
                        "found": source,
                        "chapter": chapter_num,
                        "detail": (
                            f"Glossary term '{source}' is left untranslated; "
                            f"expected '{target}'."
                        ),
                    }
                )

        return {
            "consistent": not findings,
            "findings": findings,
            # Backwards-compatible aliases.
            "inconsistencies": list(findings),
            "new_terms": [],
        }

    def update_registries_from_chapter(
        self,
        chapter_num: Any,
        translation: str,
        source_text: str,
        glossary_terms: list[Any] | None = None,
    ) -> dict[str, int]:
        """Extract new entities and glossary terms; persist all registries."""
        chars_added = 0
        places_added = 0
        terms_added = 0

        stop_words = {
            "The",
            "This",
            "That",
            "Chapter",
            "He",
            "She",
            "They",
            "It",
            "In",
            "At",
            "To",
            "And",
            "But",
            "For",
            "His",
            "Her",
            "Its",
            "A",
            "An",
            "There",
            "Then",
            "When",
            "While",
            "Once",
        }
        known_chars = {c.get("name") for c in self.characters}
        for name in re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", source_text or ""):
            if name.split()[0] in stop_words or name in known_chars:
                continue
            self.characters.append(
                {
                    "name": name,
                    "aliases": [],
                    "arabic_name": "",
                    "arabic_aliases": [],
                    "pronouns": "neutral",
                    "title": "",
                    "first_chapter": chapter_num,
                    "description": "",
                }
            )
            known_chars.add(name)
            chars_added += 1

        known_places = {p.get("name") for p in self.places}
        for match in re.finditer(
            r"\b(?:in|at|to|from|near)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            source_text or "",
        ):
            place = match.group(1)
            if place in known_places or place in known_chars:
                continue
            self.places.append(
                {
                    "name": place,
                    "arabic_name": "",
                    "place_type": "other",
                    "description": "",
                }
            )
            known_places.add(place)
            places_added += 1

        for raw_term in glossary_terms or []:
            term = raw_term if isinstance(raw_term, dict) else (_to_dict(raw_term) or {})
            source = (
                term.get("source") or term.get("en") or term.get("term") or term.get("source_term")
            )
            target = (
                term.get("target")
                or term.get("ar")
                or term.get("translation")
                or term.get("target_term")
            )
            if not source or not target:
                continue
            if any(g.get("source") == source for g in self.dynamic_glossary):
                continue
            self.dynamic_glossary.append(
                {
                    "source": source,
                    "target": target,
                    "chapter": chapter_num,
                    "alternatives": list(term.get("alternatives") or []),
                }
            )
            terms_added += 1

        self._save_registries()
        return {
            "characters_added": chars_added,
            "places_added": places_added,
            "terms_added": terms_added,
        }

    # ------------------------------------------------------------------
    # Checksum
    # ------------------------------------------------------------------
    @staticmethod
    def _checksum(file_path: str) -> str:
        """Compute SHA-256 checksum of a file."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    # ------------------------------------------------------------------
    # Legacy chapter translation (single-phase, host-agent aware)
    # ------------------------------------------------------------------
    def translate_chapter(
        self,
        chapter_num: int,
        source_path: str,
        output_path: str | None = None,
        previous_context: str | None = None,
    ) -> dict[str, Any]:
        """Translate a single chapter through the full pipeline.

        Never subscripts ``JudgeResult`` directly; no output is fabricated
        when the deterministic pipeline reports that a host agent is needed.
        """
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source chapter not found: {source}")
        source_text = source.read_text(encoding="utf-8")
        if output_path is None:
            output_path = str(self.output_dir / f"chapter_{chapter_num:03d}.ar.txt")

        checksum = self._checksum(str(source))
        for m in self.manifest:
            if m.chapter == chapter_num and m.checksum == checksum and m.status == "completed":
                # Resume path: return the SAME shape as a fresh run so callers
                # never hit a KeyError on 'judge_score' / 'approved'.
                resumed_text = (
                    Path(m.output_path).read_text(encoding="utf-8")
                    if m.output_path and Path(m.output_path).exists()
                    else ""
                )
                return {
                    "chapter": chapter_num,
                    "status": "already_completed",
                    "source_path": m.source_path,
                    "output_path": m.output_path,
                    "translation": resumed_text,
                    "judge_score": m.judge_score,
                    "approved": m.status == "completed",
                    "iterations": 0,
                    "consistency": {"consistent": True, "findings": []},
                    "registry_updates": {
                        "characters_added": 0,
                        "places_added": 0,
                        "terms_added": 0,
                    },
                    "pipeline_id": m.pipeline_id,
                }

        result = self.pipeline.run(
            source_text,
            domain_hint="literary",
            previous_context=previous_context,
        )

        translation = result.get("translation", "") if isinstance(result, dict) else ""
        if not translation or not translation.strip():
            return {
                "chapter": chapter_num,
                "status": "awaiting_host",
                "source_path": str(source),
                "output_path": output_path,
                "translation": "",
                "host_agent_required": bool(
                    isinstance(result, dict) and result.get("host_agent_required")
                ),
                "judge_score": _judge_score(result),
                "approved": False,
                "iterations": result.get("iterations", 0) if isinstance(result, dict) else 0,
                "consistency": {"consistent": True, "findings": []},
                "registry_updates": {
                    "characters_added": 0,
                    "places_added": 0,
                    "terms_added": 0,
                },
                "pipeline_id": result.get("pipeline_id") if isinstance(result, dict) else None,
            }

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(translation, encoding="utf-8")

        consistency = self.check_consistency(chapter_num, translation)
        registry_updates = self.update_registries_from_chapter(
            chapter_num, translation, source_text
        )

        entry = ChapterManifest(
            chapter=chapter_num,
            title=source.stem,
            source_path=str(source),
            output_path=output_path,
            checksum=checksum,
            status="completed" if _approved(result) else "reviewed",
            pipeline_id=result.get("pipeline_id") if isinstance(result, dict) else None,
            judge_score=_judge_score(result),
        )
        self._upsert_manifest(entry)

        return {
            "chapter": chapter_num,
            "status": "translated",
            "source_path": str(source),
            "output_path": output_path,
            "translation": translation,
            "judge_score": _judge_score(result),
            "approved": _approved(result),
            "iterations": result.get("iterations", 1) if isinstance(result, dict) else 1,
            "consistency": consistency,
            "registry_updates": registry_updates,
            "pipeline_id": entry.pipeline_id,
        }

    # ------------------------------------------------------------------
    # Full book
    # ------------------------------------------------------------------
    def translate_book(
        self,
        chapters: list[str],
        output_dir: str | None = None,
    ) -> list[dict[str, Any]]:
        """Translate all chapters of a book sequentially."""
        base = Path(output_dir) if output_dir else self.output_dir
        base.mkdir(parents=True, exist_ok=True)

        results: list[dict[str, Any]] = []
        previous_context: str | None = None

        for i, chapter_path in enumerate(chapters, 1):
            chapter_output = str(base / f"chapter_{i:03d}.ar.txt")
            result = self.translate_chapter(
                chapter_num=i,
                source_path=chapter_path,
                output_path=chapter_output,
                previous_context=previous_context,
            )
            results.append(result)

            # Build real context for the next chapter (chapter 2+).
            previous_context = (
                f"Chapter {i} ({Path(chapter_path).stem}) established. "
                f"Score: {result.get('judge_score')}. "
                f"Approved: {result.get('approved')}. "
                f"Glossary terms: "
                f"{json.dumps([g.get('source') for g in self.dynamic_glossary], ensure_ascii=False)}."  # noqa: E501
            )

        return results

    def get_status(self) -> dict[str, Any]:
        """Get overall book translation status."""
        total = len(self.manifest)
        completed = sum(1 for m in self.manifest if m.status == "completed")
        pending = sum(1 for m in self.manifest if m.status == "pending")

        return {
            "total_chapters": total,
            "completed": completed,
            "pending": pending,
            "completion_percent": (completed / total * 100) if total > 0 else 0.0,
            "characters_count": len(self.characters),
            "places_count": len(self.places),
            "dynamic_glossary_count": len(self.dynamic_glossary),
        }


def main() -> int:
    """CLI entry point for book translation (kept graceful)."""
    import argparse

    parser = argparse.ArgumentParser(description="Book Translation Workflow")
    parser.add_argument("--input", help="Input book file or directory")
    parser.add_argument("--target", default="ar", help="Target language")
    parser.add_argument("--output", help="Output directory")
    parser.add_argument("--format", default="txt", help="Book format")
    parser.add_argument("--list-formats", action="store_true", help="List formats")
    args = parser.parse_args()

    if args.list_formats:
        print("Supported formats: " + ", ".join(list_supported_formats()))
        return 0
    if not args.input:
        parser.error("--input is required unless --list-formats is given")

    input_path = Path(args.input)
    if input_path.is_dir():
        chapters = sorted(
            str(p) for p in input_path.glob("*") if p.suffix.lower() in (".txt", ".md", ".epub")
        )
    else:
        chapters = [str(input_path)]

    try:
        translator = BookTranslator(target_lang=args.target, output_dir=args.output)
        results = translator.translate_book(chapters, output_dir=args.output)
    except (FileNotFoundError, ValueError, ImportError) as exc:
        print(f"Error: {exc}")
        return 1

    print("\n=== Book Translation Complete ===")
    print(f"Chapters translated: {len(results)}")
    for r in results:
        print(
            f"  Chapter {r['chapter']}: score={r.get('judge_score')}, "
            f"approved={r.get('approved')}"
        )
    status = translator.get_status()
    print(
        f"\nOverall status: {status['completed']}/{status['total_chapters']} chapters "
        f"({status['completion_percent']:.1f}%)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
