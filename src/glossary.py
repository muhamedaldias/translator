#!/usr/bin/env python3
"""
Glossary / Term Base Module.

Handles TBX (ISO 30042) and UTX (AAMT) term bases for
consistent terminology enforcement across translation stages.

The parser is namespace-aware and accepts both TBX v2 ``langSec`` and TBX v3
``langSet`` language sections, including nested ``termGrp`` wrappers and
multiple ``<term>`` elements per language (synonyms). All source/target
combinations are kept so no term is silently dropped.
"""

from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def _local_name(tag: str) -> str:
    """Strip an XML namespace from an ElementTree tag."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _language(element: ET.Element) -> str:
    """Read a language code from ``lang`` or ``xml:lang``."""
    value = element.get("lang") or element.get(XML_LANG) or "en"
    return value.split("-")[0].lower()


class Glossary:
    """Term base for consistent translation terminology."""

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path
        self.terms: List[Dict[str, str]] = []
        self.terms_by_source: Dict[str, Dict[str, str]] = {}
        self.terms_by_target: Dict[str, Dict[str, str]] = {}
        self.terms_by_source_all: Dict[str, List[Dict[str, str]]] = {}

        if path and os.path.exists(path):
            self.load(path)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def load(self, path: str) -> None:
        """Load a glossary from TBX, UTX or JSON (replacing current terms)."""
        self.path = path
        ext = Path(path).suffix.lower()

        self.terms = []
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
        """Load TBX entries with or without XML namespaces."""
        tree = ET.parse(path)
        root = tree.getroot()

        for term_entry in root.iter():
            if _local_name(term_entry.tag) != "termEntry":
                continue

            languages: Dict[str, List[str]] = {}
            for lang_section in term_entry:
                if _local_name(lang_section.tag) not in ("langSec", "langSet"):
                    continue
                lang = _language(lang_section)
                terms = [
                    (el.text or "").strip()
                    for el in lang_section.iter()
                    if _local_name(el.tag) == "term" and (el.text or "").strip()
                ]
                languages.setdefault(lang, []).extend(terms)

            domain = ""
            for el in term_entry.iter():
                if _local_name(el.tag) == "descrip" and el.get("type") == "subjectField":
                    domain = (el.text or "").strip()
                    break

            sources = languages.get("en") or languages.get("source") or []
            targets = languages.get("ar") or languages.get("target") or []
            for source in sources:
                for target in targets:
                    pair: Dict[str, str] = {"en": source, "ar": target}
                    if domain:
                        pair["domain"] = domain
                    self.terms.append(pair)

    def _load_utx(self, path: str) -> None:
        """Load UTX (AAMT tab-delimited) file."""
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 2:
                    self.terms.append({"en": parts[0].strip(), "ar": parts[1].strip()})

    def _load_json(self, path: str) -> None:
        """Load glossary from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            self.terms = list(data)
        elif isinstance(data, dict) and "terms" in data:
            self.terms = list(data["terms"])
        else:
            raise ValueError(f"Unrecognised glossary JSON structure in {path}")

    def _build_indexes(self) -> None:
        """Build lookup indexes for fast term retrieval."""
        self.terms_by_source = {}
        self.terms_by_target = {}
        self.terms_by_source_all = {}

        for term in self.terms:
            source = term.get("en", term.get("source", ""))
            target = term.get("ar", term.get("target", ""))

            if source:
                self.terms_by_source_all.setdefault(source.lower(), []).append(term)
                self.terms_by_source[source.lower()] = term
            if target:
                self.terms_by_target[target.lower()] = term

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------
    @staticmethod
    def _targets(term: Dict[str, str]) -> List[str]:
        return [
            value
            for key in ("ar", "target", "arabic")
            if (value := term.get(key, ""))
        ]

    def get(self, source_term: str, target_lang: str = "ar") -> Optional[str]:
        """Get one translation for a source term."""
        term = self.terms_by_source.get(source_term.lower())
        if term:
            return term.get(target_lang) or self._targets(term)[0] if self._targets(term) else None
        return None

    def get_reverse(self, target_term: str, source_lang: str = "en") -> Optional[str]:
        """Get source term for a target translation."""
        term = self.terms_by_target.get(target_term.lower())
        if term:
            return term.get(source_lang, term.get("en", ""))
        return None

    def get_relevant_terms(
        self,
        text: str,
        domain: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Return glossary terms whose source occurs in ``text``.

        Matches are case-insensitive and de-duplicated by source/target pair,
        so adding two synonyms does not inflate downstream term checks.
        """
        relevant: List[Dict[str, str]] = []
        lowered = (text or "").lower()
        seen: set[tuple[str, str]] = set()

        for term in self.terms:
            source = term.get("en", term.get("source", ""))
            if not source or source.lower() not in lowered:
                continue
            term_domain = term.get("domain")
            if domain and term_domain and term_domain.lower() != domain.lower():
                continue
            key = (source, self._targets(term)[0] if self._targets(term) else "")
            if key in seen:
                continue
            seen.add(key)
            relevant.append(term)

        return relevant

    # ------------------------------------------------------------------
    # Adherence Check
    # ------------------------------------------------------------------
    def check_adherence(
        self,
        translation: str,
        terms: Optional[Iterable[Dict[str, str]]] = None,
    ) -> float:
        """Percentage of required source terms rendered with an approved target.

        By default all glossary terms are checked. Pass the terms returned by
        :meth:`get_relevant_terms` to score only terminology relevant to the
        current source segment; synonyms count as alternatives, not extra work.
        """
        checked = list(self.terms if terms is None else terms)
        if not checked:
            return 100.0

        required: Dict[str, List[str]] = {}
        for term in checked:
            source = term.get("en", term.get("source", ""))
            targets = self._targets(term)
            if source and targets:
                required.setdefault(source.lower(), []).extend(targets)

        if not required:
            return 100.0

        found = sum(
            1 for targets in required.values()
            if any(target in translation for target in targets)
        )
        return (found / len(required)) * 100

    # ------------------------------------------------------------------
    # Add / Update
    # ------------------------------------------------------------------
    def add_term(self, source: str, target: str, domain: Optional[str] = None) -> None:
        """Add a new term to the glossary."""
        term: Dict[str, str] = {"en": source, "ar": target}
        if domain:
            term["domain"] = domain

        self.terms.append(term)
        self._build_indexes()

    def save(self, path: Optional[str] = None) -> None:
        """Save glossary to JSON file."""
        save_path = path or self.path or str(
            Path(__file__).resolve().parent.parent / "data" / "glossary.json"
        )
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(self.terms, f, ensure_ascii=False, indent=2)

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
