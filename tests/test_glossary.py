#!/usr/bin/env python3
"""Unit tests for glossary / TBX handling (offline)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.glossary import Glossary


NAMESPACED_TBX = """<?xml version="1.0" encoding="UTF-8"?>
<tbx xmlns="urn:iso:std:iso:30042:ed-2" version="2.0" lang="en">
  <termEntry id="1">
    <descrip type="subjectField">technology</descrip>
    <langSet xml:lang="en"><ntig><termGrp><term>computer</term></termGrp></ntig></langSet>
    <langSet xml:lang="ar"><ntig><termGrp><term>حاسوب</term></termGrp></ntig>
      <ntig><termGrp><term>كمبيوتر</term></termGrp></ntig></langSet>
  </termEntry>
  <termEntry id="2">
    <langSet xml:lang="en"><term>software</term></langSet>
    <langSet xml:lang="ar"><term>برمجيات</term></langSet>
  </termEntry>
</tbx>
"""

LEGACY_TBX = """<?xml version="1.0" encoding="UTF-8"?>
<tbx version="2.0" lang="en">
  <termEntry>
    <langSec lang="en"><term>server</term></langSec>
    <langSec lang="ar"><term>خادم</term></langSec>
  </termEntry>
</tbx>
"""


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


class TestGlossary:
    def test_namespaced_tbx_langset_loads_all_terms(self, tmp_path):
        g = Glossary(_write(tmp_path, "ns.tbx", NAMESPACED_TBX))
        pairs = {(t["en"], t["ar"]) for t in g.terms}
        assert ("computer", "حاسوب") in pairs
        assert ("computer", "كمبيوتر") in pairs
        assert ("software", "برمجيات") in pairs
        assert len(g) >= 3
        assert g.get("computer") in ("حاسوب", "كمبيوتر")
        assert g.get_reverse("كمبيوتر") == "computer"

    def test_langsec_and_namespace_both_supported(self, tmp_path):
        g = Glossary()
        g.load(_write(tmp_path, "legacy.tbx", LEGACY_TBX))
        assert g.get("server") == "خادم"
        g.load(_write(tmp_path, "ns.tbx", NAMESPACED_TBX))
        # Reload replaces, never duplicates.
        assert len(g) == 3
        assert g.get("software") == "برمجيات"

    def test_adherence_only_over_relevant_terms(self, tmp_path):
        g = Glossary(_write(tmp_path, "ns.tbx", NAMESPACED_TBX))
        source = "The computer is ready."
        relevant = g.get_relevant_terms(source, domain="technology")
        assert len(relevant) == 2  # both Arabic synonyms for one source term
        translation = "الحاسوب جاهز"
        assert g.check_adherence(translation, relevant) == 100.0
        assert g.check_adherence(translation) < 100.0
        # Irrelevant glossary terms do not drag the score down.
        assert g.check_adherence("برمجيات") == 50.0

    def test_json_and_utx_and_add(self, tmp_path):
        json_path = _write(tmp_path, "g.json", '[{"en": "api", "ar": "واجهة"}]')
        assert Glossary(json_path).get("api") == "واجهة"
        utx_path = _write(tmp_path, "g.utx", "api\tواجهة\n")
        assert Glossary(utx_path).get("api") == "واجهة"
        g = Glossary()
        g.add_term("network", "شبكة", domain="technology")
        assert "network" in g
        assert g.get("network") == "شبكة"

    def test_unsupported_format_raises(self, tmp_path):
        try:
            Glossary(_write(tmp_path, "g.txt", "nonsense"))
        except ValueError as exc:
            assert "Unsupported glossary format" in str(exc)
        else:
            raise AssertionError("expected ValueError for unsupported format")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
