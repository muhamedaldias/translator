#!/usr/bin/env python3
"""
Glossary / Term Base Module.

Handles TBX (ISO 30042) and UTX (AAMT) term bases for
consistent terminology enforcement across translation stages.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

# Escaping only, no parsing (B406 justification)
from xml.sax.saxutils import escape  # nosec B406

logger = logging.getLogger(__name__)

# Prefer defusedxml (entity-expansion DoS protection); fall back to stdlib
# ElementTree, which on Python >= 3.13 blocks classic billion-laughs but not
# all low-amplification memory attacks. Neither fetches external entities.
try:
    from defusedxml.ElementTree import parse as _xml_parse  # type: ignore
except ImportError:  # pragma: no cover
    # Fallback only; defusedxml is preferred when installed (B405 justification)
    from xml.etree.ElementTree import parse as _xml_parse  # type: ignore # nosec B405

_MAX_GLOSSARY_BYTES = 50 * 1024 * 1024  # 50 MB hard cap on term-base files


def _local_name(tag: str) -> str:
    """Strip any XML namespace from a tag name."""
    return tag.rsplit("}", 1)[-1]


class Glossary:
    """Term base for consistent translation terminology."""

    def __init__(self, path: str | None = None) -> None:
        self.path = path
        self.terms: list[dict[str, str]] = []
        self.terms_by_source: dict[str, dict[str, str]] = {}
        self.terms_by_target: dict[str, dict[str, str]] = {}

        if path and os.path.exists(path):
            self.load(path)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def load(self, path: str) -> None:
        """Load glossary from TBX, UTX or JSON file (replaces current terms)."""
        self.path = path
        self.terms = []  # reset: reloading must not duplicate terms
        size = os.path.getsize(path)
        if size > _MAX_GLOSSARY_BYTES:
            raise ValueError(
                f"Glossary file too large ({size} bytes > {_MAX_GLOSSARY_BYTES}): {path}"
            )
        ext = Path(path).suffix.lower()

        if ext == ".tbx":
            self._load_tbx(path)
        elif ext == ".utx":
            self._load_utx(path)
        elif ext == ".json":
            self._load_json(path)
        else:
            raise ValueError(f"Unsupported glossary format: {ext}")

        self._build_indexes()

    def _load_tbx(self, path: str) -> None:
        """Load TBX (TermBase eXchange, ISO 30042), namespace-agnostic."""
        # defusedxml when available + 50MB size cap above (B314 justification)
        root = _xml_parse(path).getroot()  # nosec B314
        if root is None:
            raise ValueError(f"Empty glossary XML file: {path}")

        for entry in root.iter():
            if _local_name(entry.tag) != "termEntry":
                continue
            term_data: dict[str, str] = {}
            for child in entry:
                if _local_name(child.tag) != "langSec":
                    continue
                lang = child.get("lang", "en")
                for term_el in child:
                    if _local_name(term_el.tag) == "term":
                        term_data[lang] = term_el.text or ""
            if "en" in term_data or "ar" in term_data:
                self.terms.append(term_data)

    def _load_utx(self, path: str) -> None:
        """Load UTX (AAMT tab-delimited) file."""
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 2:
                    self.terms.append({"en": parts[0], "ar": parts[1]})

    def _load_json(self, path: str) -> None:
        """Load glossary from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            self.terms = [t for t in data if isinstance(t, dict)]
        elif isinstance(data, dict) and "terms" in data:
            self.terms = [t for t in data["terms"] if isinstance(t, dict)]

    def _build_indexes(self) -> None:
        """Build lookup indexes for fast term retrieval."""
        self.terms_by_source = {}
        self.terms_by_target = {}
        for term in self.terms:
            source = term.get("en", term.get("source", ""))
            target = term.get("ar", term.get("target", ""))
            if source:
                self.terms_by_source[source.lower()] = term
            if target:
                self.terms_by_target[target.lower()] = term

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------
    def get(self, source_term: str, target_lang: str = "ar") -> str | None:
        """Get translation for a source term."""
        term = self.terms_by_source.get(source_term.lower())
        if term:
            return term.get(target_lang, term.get("ar", ""))
        return None

    def get_reverse(self, target_term: str, source_lang: str = "en") -> str | None:
        """Get source term for a target translation."""
        term = self.terms_by_target.get(target_term.lower())
        if term:
            return term.get(source_lang, term.get("en", ""))
        return None

    def get_relevant_terms(
        self,
        text: str,
        domain: str | None = None,
    ) -> list[dict[str, str]]:
        """Glossary terms appearing in text as whole words (case-insensitive).

        Word-boundary matching prevents false positives like 'API' inside
        'CAPITAL' or 'function' inside 'malfunction'.
        """
        relevant: list[dict[str, str]] = []
        for term in self.terms:
            source = term.get("en", term.get("source", ""))
            if not source:
                continue
            if domain and term.get("domain") and term["domain"] != domain:
                continue
            if re.search(r"\b" + re.escape(source) + r"\b", text, re.IGNORECASE):
                relevant.append(term)
        return relevant

    # ------------------------------------------------------------------
    # Adherence Check
    # ------------------------------------------------------------------
    def check_adherence(
        self, translation: str, source_text: str | None = None
    ) -> float:
        """Glossary adherence: % of expected terms correctly used.

        When source_text is given, only terms relevant to that source are
        scored (a perfect translation of a 1-term sentence scores 100, not
        1/N of the whole glossary). Without source_text, all terms are
        scored (legacy behavior).
        """
        terms = self.get_relevant_terms(source_text) if source_text is not None else self.terms
        if not terms:
            return 100.0

        found = 0
        for term in terms:
            target = term.get("ar", term.get("target", ""))
            if target and target in translation:
                found += 1
        return (found / len(terms)) * 100

    # ------------------------------------------------------------------
    # Add / Update
    # ------------------------------------------------------------------
    def add_term(self, source: str, target: str, domain: str | None = None) -> None:
        """Add a new term to the glossary."""
        term: dict[str, str] = {"en": source, "ar": target}
        if domain:
            term["domain"] = domain
        self.terms.append(term)
        self._build_indexes()

    def save(self, path: str | None = None) -> None:
        """Save glossary, preserving the format implied by the extension.

        .tbx -> TBX XML, .utx -> UTX, anything else -> JSON.
        Writing JSON over a .tbx path would corrupt the term base.
        """
        save_path = Path(path or self.path or str(
            Path(__file__).resolve().parent.parent / "data" / "glossary.json"
        ))
        ext = save_path.suffix.lower()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        if ext == ".tbx":
            content = self._to_tbx()
        elif ext == ".utx":
            content = self._to_utx()
        else:
            content = json.dumps(self.terms, ensure_ascii=False, indent=2)
        # Atomic write: never leave a half-written term base behind
        tmp = save_path.with_suffix(save_path.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(save_path)

    def _to_tbx(self) -> str:
        """Serialize terms as minimal TBX v2 XML."""
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<tbx version="2.0" lang="en">',
        ]
        for i, term in enumerate(self.terms, 1):
            lines.append(f'  <termEntry id="{i}">')
            for lang in ("en", "ar"):
                value = term.get(lang, "")
                if value:
                    lines.append(f'    <langSec lang="{lang}">')
                    lines.append(f"      <term>{escape(value)}</term>")
                    lines.append("    </langSec>")
            lines.append("  </termEntry>")
        lines.append("</tbx>")
        return "\n".join(lines) + "\n"

    def _to_utx(self) -> str:
        """Serialize terms as UTX tab-delimited."""
        lines = ["# UTX glossary (en\tar)"]
        for term in self.terms:
            en = term.get("en", term.get("source", ""))
            ar = term.get("ar", term.get("target", ""))
            if en and ar:
                lines.append(f"{en}\t{ar}")
        return "\n".join(lines) + "\n"

    def __len__(self) -> int:
        return len(self.terms)

    def __contains__(self, term: str) -> bool:
        return term.lower() in self.terms_by_source


def main() -> None:
    """CLI entry point for glossary operations."""
    import argparse

    parser = argparse.ArgumentParser(description="Glossary / Term Base tool")
    parser.add_argument("--load", help="Path to glossary file to load")
    parser.add_argument("--query", help="Query a term translation")
    parser.add_argument("--save", help="Save glossary to path")
    parser.add_argument("--add", nargs=2, metavar=("SOURCE", "TARGET"), help="Add a term")

    args = parser.parse_args()
    glossary = Glossary()

    if args.load:
        glossary.load(args.load)
        print(f"Loaded {len(glossary)} terms from {args.load}")

    if args.query:
        result = glossary.get(args.query)
        print(f"{args.query} -> {result or 'NOT FOUND'}")

    if args.add:
        source, target = args.add
        glossary.add_term(source, target)
        print(f"Added: {source} -> {target}")

    if args.save:
        glossary.save(args.save)
        print(f"Saved glossary to {args.save}")


if __name__ == "__main__":
    main()