#!/usr/bin/env python3
"""Unit tests for Arabic morphology module (deterministic, offline)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.arabic import (
    ArabicProcessor,
    is_arabic_text,
    normalize_arabic,
    remove_arabic_diacritics,
)


class TestArabicProcessor:
    """Tests for ArabicProcessor class."""

    def setup_method(self):
        self.proc = ArabicProcessor()

    def test_is_arabic(self):
        assert self.proc.is_arabic("مرحبا") is True
        assert self.proc.is_arabic("Hello") is False
        assert self.proc.is_arabic("Hello مرحبا") is True

    def test_normalize_orthography(self):
        text = "أ Machado إ input ى"
        result = self.proc.normalize_orthography(text)
        assert "أ" in result  # proper nouns must keep their hamza
        assert "إ" in result
        assert "ى" not in result
        assert "ي" in result

    def test_remove_diacritics(self):
        assert self.proc.remove_diacritics("مُسْلِمٌ") == "مسلم"

    def test_diacritics_policy_remove(self):
        self.proc.diacritics_policy = "remove"
        assert self.proc.apply_diacritics_policy("مُسْلِمٌ") == "مسلم"

    def test_diacritics_policy_retain(self):
        self.proc.diacritics_policy = "retain"
        assert self.proc.apply_diacritics_policy("مُسْلِمٌ") == "مُسْلِمٌ"

    def test_plural_form(self):
        assert [self.proc.get_plural_form(n) for n in (0, 1, 2, 5, 50, 100)] == [
            "zero",
            "one",
            "two",
            "few",
            "many",
            "other",
        ]

    def test_detect_register_msa(self):
        assert self.proc.detect_register("في هذا اليوم، يمكن القول إن") == "MSA"

    def test_detect_register_dialect(self):
        assert self.proc.detect_register("شو أخبارك؟ كيفك؟") == "dialect"

    def test_rtl_markers(self):
        marked = self.proc.add_rtl_markers("مرحبا بالعالم")
        assert "\u202b" in marked and "\u202c" in marked
        assert self.proc.remove_rtl_markers(marked) == "مرحبا بالعالم"

    def test_convenience_functions(self):
        assert is_arabic_text("مرحبا") is True
        assert is_arabic_text("Hello") is False
        assert remove_arabic_diacritics("مُسْلِمٌ") == "مسلم"
        assert "أ" in normalize_arabic("أهلاً")  # hamza in names is preserved

    # --- Review Focus: protected spans ---------------------------------
    def test_extract_protected_spans_verbatim(self):
        text = 'See {{api_key}} and `code <x>` then <tag attr="v"> and {"id": 7}.'
        spans = self.proc.extract_protected_spans(text)
        assert spans == [
            "{{api_key}}",
            "`code <x>`",
            '<tag attr="v">',
            '{"id": 7}',
        ]

    def test_extract_protected_spans_empty_text(self):
        assert self.proc.extract_protected_spans("   ") == []
        assert self.proc.extract_protected_spans("") == []

    def test_protect_code_blocks_uses_same_spans(self):
        text = 'A {{token}} B `fn()` C <b> D {"id": 7}'
        protected, blocks = self.proc.protect_code_blocks(text)
        assert blocks == self.proc.extract_protected_spans(text)
        assert self.proc.restore_code_blocks(protected, blocks) == text

    def test_has_diacritics(self):
        assert self.proc.has_diacritics("مُسْلِمٌ") is True
        assert self.proc.has_diacritics("مسلم") is False
        assert self.proc.has_diacritics("hello") is False


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
