#!/usr/bin/env python3
"""Unit tests for dictionary manager (offline)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.dictionary import DictionaryManager, DictionaryEntry


class TestDictionaryManager:
    def setup_method(self, tmp_path=None):
        # tmp_path is supplied per-test; use a neutral dir here and override below.
        self.tmp = None

    def _manager(self, tmp_path):
        data = tmp_path / "data"
        cache = tmp_path / "cache"
        dm = DictionaryManager(data_dir=str(data), cache_dir=str(cache))
        return dm

    # --- Review Focus / audit: method vs attribute name collisions ----
    def test_lookup_methods_are_callable_not_shadowed_by_data(self, tmp_path):
        dm = self._manager(tmp_path)
        try:
            assert callable(dm.wiktionary_en_ar)
            assert callable(dm.roget_synonyms)
            assert dm.wiktionary_en_ar("unknown-word") == []
            assert dm.roget_synonyms("unknown-word") == []
        finally:
            dm.close()

    def test_wiktionary_data_is_separate_from_method(self, tmp_path):
        dm = self._manager(tmp_path)
        try:
            dm._wiktionary_en_ar_data["hello"] = ["مرحبا"]
            assert dm.wiktionary_en_ar("Hello") == ["مرحبا"]
            assert dm.lookup_en_ar("hello", direction="en-ar") == ["مرحبا"]
            assert dm.lookup_en_ar("مرحبا", direction="ar-en") == ["hello"]
        finally:
            dm.close()

    def test_roget_data_is_separate_from_method(self, tmp_path):
        dm = self._manager(tmp_path)
        try:
            dm._roget_synonyms_data["big"] = ["large", "huge"]
            assert dm.roget_synonyms("big") == ["large", "huge"]
            assert dm.lookup_synonyms("big", source="roget") == ["large", "huge"]
        finally:
            dm.close()

    def test_lookup_definition_offline(self, tmp_path):
        dm = self._manager(tmp_path)
        try:
            entry = dm.lookup_definition("computer", dictionary="wordnet")
            assert isinstance(entry, DictionaryEntry)
            assert entry.word == "computer"
            assert entry.source == "wordnet"
        finally:
            dm.close()


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
