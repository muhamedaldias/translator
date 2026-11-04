#!/usr/bin/env python3
"""
Glossary / Term Base Module.

Handles TBX (ISO 30042) and UTX (AAMT) term bases for
consistent terminology enforcement across translation stages.
"""

from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional


class Glossary:
    """Term base for consistent translation terminology."""

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path
        self.terms: List[Dict[str, str]] = []
        self.terms_by_source: Dict[str, Dict[str, str]] = {}
        self.terms_by_target: Dict[str, Dict[str, str]] = {}

        if path and os.path.exists(path):
            self.load(path)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def load(self, path: str) -> None:
        """Load glossary from TBX or UTX file."""
        self.path = path
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
        """Load TBX (TermBase eXchange, ISO 30042) file."""
        tree = ET.parse(path)
        root = tree.getroot()

        # TBX namespace handling
        ns = {"tbx": "http://www.tbx.net"}

        for term_entry in root.findall(".//termEntry"):
            term_data: Dict[str, str] = {}

            # Get language sections
            for lang_sec in term_entry.findall("langSec"):
                lang = lang_sec.get("lang", "en")
                for term_el in lang_sec.findall("term"):
                    term_text = term_el.text or ""
                    term_data[lang] = term_text

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
                    self.terms.append({
                        "en": parts[0],
                        "ar": parts[1],
                    })

    def _load_json(self, path: str) -> None:
        """Load glossary from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            self.terms = data
        elif isinstance(data, dict) and "terms" in data:
            self.terms = data["terms"]

    def _build_indexes(self) -> None:
        """Build lookup indexes for fast term retrieval."""
        self.terms_by_source = {}
        self.terms_by_target = {}

        for term in self.terms:
            source = term.get("en", term.get("source", ""))
            target = term.get("ar", term.get("target", term.get("ar", "")))

            if source:
                self.terms_by_source[source.lower()] = term
            if target:
                self.terms_by_target[target.lower()] = term

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------
    def get(self, source_term: str, target_lang: str = "ar") -> Optional[str]:
        """Get translation for a source term."""
        term = self.terms_by_source.get(source_term.lower())
        if term:
            return term.get(target_lang, term.get("ar", ""))
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
        """Get glossary terms relevant to the given text."""
        relevant: List[Dict[str, str]] = []

        for term in self.terms:
            source = term.get("en", term.get("source", ""))
            if source and source.lower() in text.lower():
                relevant.append(term)

        return relevant

    # ------------------------------------------------------------------
    # Adherence Check
    # ------------------------------------------------------------------
    def check_adherence(self, translation: str) -> float:
        """Check glossary adherence: % of terms correctly used in translation."""
        if not self.terms:
            return 100.0

        found = 0
        for term in self.terms:
            target = term.get("ar", term.get("target", ""))
            if target and target in translation:
                found += 1

        return (found / len(self.terms)) * 100

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
