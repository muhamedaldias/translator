#!/usr/bin/env python3
"""
Dictionary Skills Integration Module.

Integrates Phase 1 offline resources:
- Open English Wordnet 2025 (synonyms, hypernyms, glosses, WSD)
- Wiktionary EN-AR dumps (bilingual headword pairs)
- Roget's Thesaurus 1911 (concept-based synonym expansion)
- Datamuse API (lightweight synonyms, no key)

Plus Phase 2 metered APIs (with caching):
- Merriam-Webster Collegiate API (authoritative EN definitions)
- Collins Dictionary API (bilingual coverage)
- Oxford Dictionaries API (current-usage definitions)
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore


@dataclass
class DictionaryEntry:
    """Standardized dictionary entry."""
    word: str
    pos: Optional[str] = None  # part of speech
    definition: Optional[str] = None
    synonyms: List[str] = field(default_factory=list)
    antonyms: List[str] = field(default_factory=list)
    translations: Dict[str, List[str]] = field(default_factory=dict)  # lang -> [translations]
    examples: List[str] = field(default_factory=list)
    source: str = ""  # wordnet, wiktionary, merriam_webster, etc.


class DictionaryManager:
    """Manages all dictionary skills with offline-first preference."""

    def __init__(
        self,
        data_dir: Optional[str] = None,
        cache_dir: Optional[str] = None,
        merriam_webster_key: Optional[str] = None,
        collins_key: Optional[str] = None,
        oxford_app_id: Optional[str] = None,
        oxford_app_key: Optional[str] = None,
    ) -> None:
        self.data_dir = Path(data_dir) if data_dir else Path(
            __file__).resolve().parent.parent / "data" / "dictionaries"
        self.cache_dir = Path(cache_dir) if cache_dir else Path(
            __file__).resolve().parent.parent / "data" / "cache"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # API keys
        self.merriam_webster_key = merriam_webster_key or os.getenv("MERRIAM_WEBSTER_KEY")
        self.collins_key = collins_key or os.getenv("COLLINS_KEY")
        self.oxford_app_id = oxford_app_id or os.getenv("OXFORD_APP_ID")
        self.oxford_app_key = oxford_app_key or os.getenv("OXFORD_APP_KEY")

        # Cache (in-memory + SQLite)
        self._memory_cache: Dict[str, Any] = {}
        self._init_sqlite_cache()

        # Loaded resources
        self.wordnet: Optional[Any] = None
        self.wiktionary_en_ar: Dict[str, List[str]] = {}
        self.roget_synonyms: Dict[str, List[str]] = {}

        self._load_resources()

    # ------------------------------------------------------------------
    # SQLite cache
    # ------------------------------------------------------------------
    def _init_sqlite_cache(self) -> None:
        """Initialize SQLite cache for API responses."""
        self._db_path = self.cache_dir / "dictionary_cache.db"
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT,
                expiry REAL
            )
            """
        )
        self._conn.commit()

    def _cache_get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self._memory_cache:
            return self._memory_cache[key]

        row = self._conn.execute(
            "SELECT value, expiry FROM cache WHERE key = ?", (key,)
        ).fetchone()

        if row and row[1] > time.time():
            self._memory_cache[key] = json.loads(row[0])
            return self._memory_cache[key]

        if row:
            self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            self._conn.commit()

        return None

    def _cache_set(self, key: str, value: Any, ttl_seconds: int = 86400) -> None:
        """Set value in cache."""
        self._memory_cache[key] = value
        self._conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, expiry) VALUES (?, ?, ?)",
            (key, json.dumps(value, ensure_ascii=False), time.time() + ttl_seconds),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Resource loading
    # ------------------------------------------------------------------
    def _load_resources(self) -> None:
        """Load all available dictionary resources."""
        self._load_wordnet()
        self._load_wiktionary()
        self._load_roget()

    def _load_wordnet(self) -> None:
        """Load Open English Wordnet 2025 (local JSON/LMF)."""
        wn_path = self.data_dir / "wordnet"
        candidates = [
            wn_path / "english-wordnet.json",
            wn_path / "oewn.json",
            wn_path / "wordnet.json",
        ]

        for path in candidates:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self.wordnet = json.load(f)
                return

        # Try NLTK WordNet as fallback
        try:
            from nltk.corpus import wordnet as wn  # type: ignore

            self.wordnet = wn
        except Exception:
            pass

    def _load_wiktionary(self) -> None:
        """Load Wiktionary EN-AR dump (local)."""
        wk_path = self.data_dir / "wiktionary"
        candidates = [
            wk_path / "en-ar.json",
            wk_path / "wiktionary_en_ar.json",
        ]

        for path in candidates:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self.wiktionary_en_ar = json.load(f)
                return

    def _load_roget(self) -> None:
        """Load Roget's Thesaurus 1911 (local)."""
        roget_path = self.data_dir / "roget"
        candidates = [
            roget_path / "synonyms.json",
            roget_path / "roget.json",
        ]

        for path in candidates:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self.roget_synonyms = json.load(f)
                return

    # ------------------------------------------------------------------
    # WordNet operations
    # ------------------------------------------------------------------
    def wordnet_synonyms(self, word: str, pos: Optional[str] = None) -> List[str]:
        """Get synonyms from WordNet."""
        cache_key = f"wn:syn:{word}:{pos or 'any'}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        synonyms: List[str] = []

        # NLTK WordNet
        if hasattr(self.wordnet, "synsets"):
            try:
                from nltk.corpus import wordnet as wn  # type: ignore

                pos_map = {"n": wn.NOUN, "v": wn.VERB, "a": wn.ADJ, "r": wn.ADV}
                wn_pos = pos_map.get(pos) if pos else None
                synsets = wn.synsets(word, pos=wn_pos) if wn_pos else wn.synsets(word)
                for syn in synsets:
                    for lemma in syn.lemmas():
                        synonyms.append(lemma.name().replace("_", " "))
            except Exception:
                pass

        # OEWN JSON
        elif isinstance(self.wordnet, dict):
            entry = self.wordnet.get(word.lower())
            if entry:
                synonyms = entry.get("synonyms", [])

        # Deduplicate
        synonyms = list(dict.fromkeys(synonyms))

        self._cache_set(cache_key, synonyms)
        return synonyms

    def wordnet_definition(self, word: str, pos: Optional[str] = None) -> Optional[str]:
        """Get definition from WordNet."""
        cache_key = f"wn:def:{word}:{pos or 'any'}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        definition: Optional[str] = None

        if hasattr(self.wordnet, "synsets"):
            try:
                from nltk.corpus import wordnet as wn  # type: ignore

                pos_map = {"n": wn.NOUN, "v": wn.VERB, "a": wn.ADJ, "r": wn.ADV}
                wn_pos = pos_map.get(pos) if pos else None
                synsets = wn.synsets(word, pos=wn_pos) if wn_pos else wn.synsets(word)
                if synsets:
                    definition = synsets[0].definition()
            except Exception:
                pass

        elif isinstance(self.wordnet, dict):
            entry = self.wordnet.get(word.lower())
            if entry:
                definition = entry.get("definition")

        self._cache_set(cache_key, definition)
        return definition

    # ------------------------------------------------------------------
    # Wiktionary EN-AR
    # ------------------------------------------------------------------
    def wiktionary_en_ar(self, word: str) -> List[str]:
        """Get EN-AR translations from Wiktionary."""
        cache_key = f"wk:en-ar:{word.lower()}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        translations = self.wiktionary_en_ar.get(word.lower(), [])

        self._cache_set(cache_key, translations)
        return translations

    def wiktionary_ar_en(self, word: str) -> List[str]:
        """Get AR-EN translations from Wiktionary."""
        cache_key = f"wk:ar-en:{word.lower()}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        # Reverse lookup
        translations: List[str] = []
        for en_word, ar_translations in self.wiktionary_en_ar.items():
            if word.lower() in [t.lower() for t in ar_translations]:
                translations.append(en_word)

        self._cache_set(cache_key, translations)
        return translations

    # ------------------------------------------------------------------
    # Roget's Thesaurus
    # ------------------------------------------------------------------
    def roget_synonyms(self, word: str) -> List[str]:
        """Get concept-based synonyms from Roget's Thesaurus."""
        cache_key = f"roget:syn:{word.lower()}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        synonyms = self.roget_synonyms.get(word.lower(), [])

        self._cache_set(cache_key, synonyms)
        return synonyms

    # ------------------------------------------------------------------
    # Datamuse API
    # ------------------------------------------------------------------
    def datamuse_synonyms(self, word: str) -> List[str]:
        """Get synonyms from Datamuse API (free, no key)."""
        if requests is None:
            return []

        cache_key = f"dm:syn:{word.lower()}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        synonyms: List[str] = []

        try:
            resp = requests.get(
                "https://api.datamuse.com/words",
                params={"rel_syn": word, "max": 10},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                synonyms = [item.get("word", "") for item in data if item.get("word")]
        except Exception:
            pass

        self._cache_set(cache_key, synonyms, ttl_seconds=604800)  # 1 week
        return synonyms

    # ------------------------------------------------------------------
    # Merriam-Webster API (Phase 2, metered)
    # ------------------------------------------------------------------
    def merriam_webster_definition(self, word: str) -> Optional[DictionaryEntry]:
        """Get definition from Merriam-Webster Collegiate API."""
        if not self.merriam_webster_key or requests is None:
            return None

        cache_key = f"mw:def:{word.lower()}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return DictionaryEntry(**cached)

        entry: Optional[DictionaryEntry] = None

        try:
            resp = requests.get(
                f"https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word}",
                params={"key": self.merriam_webster_key},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, list) and len(data) > 0:
                    item = data[0]
                    entry = DictionaryEntry(
                        word=word,
                        pos=item.get("fl"),
                        definition=(
                            item.get("shortdef", [""])[0]
                            if item.get("shortdef")
                            else None
                        ),
                        source="merriam_webster",
                    )
        except Exception:
            pass

        if entry:
            self._cache_set(cache_key, entry.__dict__, ttl_seconds=604800)

        return entry

    # ------------------------------------------------------------------
    # Unified lookup
    # ------------------------------------------------------------------
    def lookup_definition(
        self,
        word: str,
        dictionary: str = "wordnet",
    ) -> Optional[DictionaryEntry]:
        """Unified definition lookup across dictionaries."""
        if dictionary == "wordnet":
            defn = self.wordnet_definition(word)
            syns = self.wordnet_synonyms(word)
            return DictionaryEntry(
                word=word,
                definition=defn,
                synonyms=syns,
                source="wordnet",
            )
        elif dictionary == "merriam_webster":
            return self.merriam_webster_definition(word)
        return None

    def lookup_synonyms(
        self,
        word: str,
        source: str = "wordnet",
    ) -> List[str]:
        """Unified synonym lookup."""
        if source == "wordnet":
            return self.wordnet_synonyms(word)
        elif source == "datamuse":
            return self.datamuse_synonyms(word)
        elif source == "roget":
            return self.roget_synonyms(word)
        elif source == "all":
            syns = set()
            syns.update(self.wordnet_synonyms(word))
            syns.update(self.datamuse_synonyms(word))
            syns.update(self.roget_synonyms(word))
            return list(syns)
        return []

    def lookup_en_ar(
        self,
        term: str,
        direction: str = "en-ar",
    ) -> List[str]:
        """Unified EN-AR / AR-EN lookup."""
        if direction == "en-ar":
            return self.wiktionary_en_ar(term)
        elif direction == "ar-en":
            return self.wiktionary_ar_en(term)
        return []

    def get_relevant_terms(
        self,
        text: str,
        max_terms: int = 10,
    ) -> List[DictionaryEntry]:
        """Extract difficult terms from text and look up their definitions."""
        words = re.findall(r"\b[A-Za-z]{4,}\b", text)
        entries: List[DictionaryEntry] = []

        for word in words[:max_terms]:
            entry = self.lookup_definition(word, dictionary="wordnet")
            if entry and entry.definition:
                entries.append(entry)

        return entries

    def close(self) -> None:
        """Close database connection."""
        self._conn.close()


def main() -> None:
    """CLI entry point for dictionary manager."""
    import argparse

    parser = argparse.ArgumentParser(description="Dictionary Manager")
    parser.add_argument("--word", help="Word to look up")
    parser.add_argument("--synonyms", action="store_true", help="Get synonyms")
    parser.add_argument("--definition", action="store_true", help="Get definition")
    parser.add_argument("--en-ar", metavar="TERM", help="EN-AR translation")
    parser.add_argument("--source", default="wordnet", help="Dictionary source")

    args = parser.parse_args()

    dm = DictionaryManager()

    if args.word and args.synonyms:
        syns = dm.lookup_synonyms(args.word, source=args.source)
        print(f"Synonyms of '{args.word}': {syns}")
    if args.word and args.definition:
        entry = dm.lookup_definition(args.word, dictionary=args.source)
        print(f"Definition of '{args.word}': {entry.definition if entry else 'NOT FOUND'}")
    if args.en_ar:
        trans = dm.lookup_en_ar(args.en_ar, direction="en-ar")
        print(f"EN-AR '{args.en_ar}': {trans}")

    dm.close()


if __name__ == "__main__":
    main()
