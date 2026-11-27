"""Offline unit tests for scripts/fetch_lexicon.py (pure functions only).

Every fixture is inline; no test in this module touches the network.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.fetch_lexicon import (  # noqa: E402
    default_output,
    is_open_license,
    oewn_pairs,
    wiktionary_ar_pairs,
)

OEWN_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<LexicalResource>
  <Lexicon id="oewn" language="en"
           license="https://creativecommons.org/licenses/by/4.0">
    <LexicalEntry id="w1">
      <Lemma writtenForm="apple" partOfSpeech="n"/>
      <Sense id="s1" synset="syn1"/>
    </LexicalEntry>
    <LexicalEntry id="w2">
      <Lemma writtenForm="book" partOfSpeech="n"/>
    </LexicalEntry>
  </Lexicon>
</LexicalResource>
"""

OEWN_XML_WITH_AR = """\
<LexicalResource>
  <LexicalEntry id="w3">
    <Lemma writtenForm="dog" partOfSpeech="n"/>
    <Translation lang="ar">كلب</Translation>
  </LexicalEntry>
</LexicalResource>
"""

KAIKKI_JSONL = """\
{"word": "كلب", "translations": [{"lang": "en", "word": "dog"}, {"lang": "fr", "word": "chien"}]}
{"word": "كتاب", "translations": [{"lang": "en", "translation": "book"}]}
{"word": "قطة", "translations": [{"lang": "ar", "word": "cat"}]}

not-json
"""


class TestOewnPairs:
    def test_extracts_english_lemmas_with_empty_arabic(self) -> None:
        assert oewn_pairs(OEWN_XML) == [("apple", ""), ("book", "")]

    def test_uses_arabic_label_when_one_is_present(self) -> None:
        assert oewn_pairs(OEWN_XML_WITH_AR) == [("dog", "كلب")]


class TestWiktionaryArPairs:
    def test_reads_english_translations_from_kaikki_jsonl(self) -> None:
        assert wiktionary_ar_pairs(KAIKKI_JSONL) == [("dog", "كلب"), ("book", "كتاب")]

    def test_falls_back_to_english_glosses_for_real_kaikki_records(self) -> None:
        jsonl = (
            '{"word": "سلام", "lang_code": "ar", "senses": [{"glosses": ["peace"]}]}\n'
            '{"word": "حرب", "lang_code": "ar", "senses": [{"glosses": ["حرب"]}]}\n'
        )
        assert wiktionary_ar_pairs(jsonl) == [("peace", "سلام")]

    def test_trims_parenthetical_gloss_to_a_compact_term(self) -> None:
        jsonl = (
            '{"word": "حماس", "lang_code": "ar", '
            '"senses": [{"glosses": ["Hamas (a Palestinian Islamist group)"]}]}\n'
        )
        assert wiktionary_ar_pairs(jsonl) == [("Hamas", "حماس")]

    def test_deduplicates_pairs_preserving_first_seen_order(self) -> None:
        jsonl = (
            '{"word": "سلام", "translations": [{"lang": "en", "word": "peace"}]}\n'
            '{"word": "سلام", "translations": [{"lang": "en", "word": "peace"}]}\n'
        )
        assert wiktionary_ar_pairs(jsonl) == [("peace", "سلام")]


class TestIsOpenLicense:
    @pytest.mark.parametrize(
        "text",
        [
            "CC BY 4.0",
            "cc by-sa 4.0",
            "Creative Commons Attribution 4.0 International",
            "GNU Free Documentation License",
            "GFDL",
        ],
    )
    def test_accepts_open_licenses(self, text: str) -> None:
        assert is_open_license(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            "Merriam-Webster terms of use",
            "Oxford University Press",
            "Collins Dictionary",
            "All rights reserved",
            "Proprietary",
        ],
    )
    def test_rejects_proprietary_licenses(self, text: str) -> None:
        assert is_open_license(text) is False


def test_default_output_stays_under_data_dictionaries() -> None:
    out = Path(default_output())
    assert out.name.endswith(".jsonl")
    assert out.resolve().is_relative_to(REPO_ROOT / "data" / "dictionaries")
