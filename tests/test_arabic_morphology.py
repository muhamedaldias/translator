#!/usr/bin/env python3
"""
Unit tests for Arabic morphology module.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.arabic import ArabicProcessor, normalize_arabic, remove_arabic_diacritics, is_arabic_text


class TestArabicProcessor:
    """Tests for ArabicProcessor class."""

    def setup_method(self):
        self.proc = ArabicProcessor()

    def test_is_arabic(self):
        """Test Arabic text detection."""
        assert self.proc.is_arabic("مرحبا") is True
        assert self.proc.is_arabic("Hello") is False
        assert self.proc.is_arabic("Hello مرحبا") is True

    def test_normalize_orthography(self):
        """Test Arabic orthography normalization."""
        # Alef variants should normalize to plain alef
        text = "أ Machado إ input"
        result = self.proc.normalize_orthography(text)
        assert "أ" not in result
        assert "إ" not in result

    def test_remove_diacritics(self):
        """Test diacritics removal."""
        text = "مُسْلِمٌ"  # with diacritics
        result = self.proc.remove_diacritics(text)
        assert result == "مسلم"

    def test_diacritics_policy_remove(self):
        """Test diacritics policy: remove."""
        self.proc.diacritics_policy = "remove"
        text = "مُسْلِمٌ"
        result = self.proc.apply_diacritics_policy(text)
        assert result == "مسلم"

    def test_diacritics_policy_retain(self):
        """Test diacritics policy: retain."""
        self.proc.diacritics_policy = "retain"
        text = "مُسْلِمٌ"
        result = self.proc.apply_diacritics_policy(text)
        assert result == text

    def test_plural_form(self):
        """Test Arabic plural form categories."""
        assert self.proc.get_plural_form(0) == "zero"
        assert self.proc.get_plural_form(1) == "one"
        assert self.proc.get_plural_form(2) == "two"
        assert self.proc.get_plural_form(5) == "few"
        assert self.proc.get_plural_form(50) == "many"
        assert self.proc.get_plural_form(100) == "other"

    def test_detect_register_msa(self):
        """Test MSA detection."""
        text = "في هذا اليوم، يمكن القول إن"
        result = self.proc.detect_register(text)
        assert result in ("MSA", "dialect")

    def test_rtl_markers(self):
        """Test RTL marker addition/removal."""
        text = "مرحبا بالعالم"
        marked = self.proc.add_rtl_markers(text)
        assert "\u202B" in marked
        assert "\u202C" in marked

        unmarked = self.proc.remove_rtl_markers(marked)
        assert "\u202B" not in unmarked
        assert "\u202C" not in unmarked

    def test_convenience_functions(self):
        """Test module-level convenience functions."""
        assert is_arabic_text("مرحبا") is True
        assert is_arabic_text("Hello") is False
        assert remove_arabic_diacritics("مُسْلِمٌ") == "مسلم"
        assert "أ" not in normalize_arabic("أهلاً")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
