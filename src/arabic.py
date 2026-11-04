#!/usr/bin/env python3
"""
Arabic-Specific NLP Module.

Handles Arabic-specific challenges:
- Root-and-pattern morphology
- MSA vs dialect detection
- Gender agreement
- Broken plural agreement
- Diacritics (tashkīl) policy
- Orthography normalization (alef/ya/ta-marbuta)
- Named entity handling (transliterate vs translate)
- RTL preservation
- 6 Arabic plural forms (zero/one/two/few/many/other)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


class ArabicProcessor:
    """Processor for Arabic-specific linguistic features."""

    # Alef variants
    ALEF_VARIANTS = ["أ", "إ", "آ", "ا"]

    # Ya variants
    YA_VARIANTS = ["ي", "ى"]

    # Ta-marbuta variants
    TA_MARBUTA_VARIANTS = ["ة", "ه"]

    # Arabic diacritics (tashkīl)
    DIACRITICS = re.compile(
        r"[\u064B-\u065F\u0670\u0640]"  # harakat + tatweel
    )

    # Arabic Unicode range
    ARABIC_RANGE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")

    # 6 Arabic plural forms (CLDR)
    PLURAL_FORMS = ["zero", "one", "two", "few", "many", "other"]

    def __init__(self) -> None:
        self.diacritics_policy: str = "remove"  # retain | remove | optional
        self.orthography_normalization: bool = True

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------
    def is_arabic(self, text: str) -> bool:
        """Check if text contains Arabic characters."""
        return bool(self.ARABIC_RANGE.search(text))

    def contains_arabic(self, text: str) -> bool:
        """Alias for is_arabic."""
        return self.is_arabic(text)

    def detect_register(self, text: str) -> str:
        """Detect Arabic register: MSA or dialect (heuristic)."""
        # Heuristic: MSA tends to use more formal vocabulary and case endings
        # Dialect tends to use clitics, circumfix negation, etc.
        # This is a placeholder — real implementation uses trained models.
        dialect_markers = ["شو", "كيفك", "ächbar", "يا", "wallah", "يا ريت"]
        msa_markers = ["و", "في", "من", "إلى", "على", "عن", "مع", "بال", "لقد", "قد"]

        dialect_count = sum(1 for m in dialect_markers if m in text)
        msa_count = sum(1 for m in msa_markers if m in text)

        if dialect_count > msa_count:
            return "dialect"
        return "MSA"

    # ------------------------------------------------------------------
    # Orthography Normalization
    # ------------------------------------------------------------------
    def normalize_orthography(self, text: str) -> str:
        """Normalize Arabic orthography variants."""
        if not self.orthography_normalization:
            return text

        # Normalize alef variants to plain alef (ا)
        for variant in self.ALEF_VARIANTS:
            text = text.replace(variant, "ا")

        # Normalize ya variants to ي
        for variant in self.YA_VARIANTS:
            text = text.replace(variant, "ي")

        # Normalize ta-marbuta: ه at end -> ة (context-dependent)
        # Simplified: keep as-is to avoid over-correction

        return text

    # ------------------------------------------------------------------
    # Diacritics
    # ------------------------------------------------------------------
    def remove_diacritics(self, text: str) -> str:
        """Remove Arabic diacritics (tashkīl)."""
        return self.DIACRITICS.sub("", text)

    def add_diacritics(self, text: str) -> str:
        """Add diacritics (placeholder — requires trained model)."""
        # Real implementation would use a diacritization model (e.g., AraNizer)
        return text

    def apply_diacritics_policy(self, text: str) -> str:
        """Apply configured diacritics policy."""
        if self.diacritics_policy == "remove":
            return self.remove_diacritics(text)
        elif self.diacritics_policy == "retain":
            return text
        elif self.diacritics_policy == "optional":
            return self.remove_diacritics(text)
        return text

    # ------------------------------------------------------------------
    # Plural Forms
    # ------------------------------------------------------------------
    def get_plural_form(self, count: int) -> str:
        """Get Arabic plural form category for a count (CLDR)."""
        if count == 0:
            return "zero"
        elif count == 1:
            return "one"
        elif count == 2:
            return "two"
        elif 3 <= count <= 10:
            return "few"
        elif 11 <= count <= 99:
            return "many"
        else:
            return "other"

    def format_plural(self, singular: str, count: int, dual: Optional[str] = None) -> str:
        """Format Arabic word with correct plural form."""
        form = self.get_plural_form(count)
        if form == "one":
            return singular
        elif form == "two" and dual:
            return dual
        else:
            # For few/many/other, would need broken plural forms
            # Placeholder: return singular with count indicator
            return f"{singular} ({form})"

    # ------------------------------------------------------------------
    # Gender Agreement
    # ------------------------------------------------------------------
    def check_gender_agreement(
        self,
        subject_gender: str,
        object_gender: str,
        verb_form: str,
    ) -> Dict[str, Any]:
        """Check Arabic gender agreement between subject, object, and verb."""
        issues = []

        # In Arabic, verb agrees with subject in gender and number
        valid_combinations = {
            ("male", "male"),
            ("female", "female"),
            ("neutral", "neutral"),
            ("male", "female"),
            ("female", "male"),
        }

        if (subject_gender, object_gender) not in valid_combinations:
            issues.append({
                "type": "gender_agreement",
                "subject": subject_gender,
                "object": object_gender,
                "verb": verb_form,
            })

        return {
            "agreed": len(issues) == 0,
            "issues": issues,
        }

    # ------------------------------------------------------------------
    # Named Entities
    # ------------------------------------------------------------------
    def transliterate_to_arabic(self, text: str) -> str:
        """Transliterate foreign names to Arabic (placeholder)."""
        # Real implementation would use a transliteration model
        # or lookup table (e.g., UNGEGN, ALA-LC)
        return f"[{text}]"  # Placeholder: mark for manual review

    def is_named_entity(self, text: str) -> bool:
        """Heuristic check for named entities."""
        return bool(re.match(r"^[A-Z][a-z]+(?:\s[A-Z][a-z]+)*$", text))

    # ------------------------------------------------------------------
    # RTL
    # ------------------------------------------------------------------
    def add_rtl_markers(self, text: str) -> str:
        """Add RTL embedding markers for Arabic text."""
        if self.contains_arabic(text):
            return f"\u202B{text}\u202C"  # RLE ... PDF
        return text

    def remove_rtl_markers(self, text: str) -> str:
        """Remove RTL embedding markers."""
        return text.replace("\u202B", "").replace("\u202C", "")

    # ------------------------------------------------------------------
    # Code Block Protection
    # ------------------------------------------------------------------
    def protect_code_blocks(self, text: str) -> tuple[str, List[str]]:
        """Extract code blocks for protection during translation."""
        pattern = r"`[^`]+`|<[^>]+>|\{\{[^}]+\}\}|\$\{[^}]+\}"
        blocks = re.findall(pattern, text)
        protected = re.sub(pattern, "___CODE_BLOCK___", text)
        return protected, blocks

    def restore_code_blocks(
        self, text: str, blocks: List[str]
    ) -> str:
        """Restore code blocks after translation."""
        for block in blocks:
            text = text.replace("___CODE_BLOCK___", block, 1)
        return text


# Convenience functions
def normalize_arabic(text: str) -> str:
    """Normalize Arabic text orthography."""
    processor = ArabicProcessor()
    return processor.normalize_orthography(text)


def remove_arabic_diacritics(text: str) -> str:
    """Remove Arabic diacritics."""
    processor = ArabicProcessor()
    return processor.remove_diacritics(text)


def is_arabic_text(text: str) -> bool:
    """Check if text contains Arabic characters."""
    processor = ArabicProcessor()
    return processor.is_arabic(text)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Arabic NLP utilities")
    parser.add_argument("--text", required=True, help="Arabic text to process")
    parser.add_argument("--normalize", action="store_true", help="Normalize orthography")
    parser.add_argument("--strip-diacritics", action="store_true", help="Remove diacritics")
    parser.add_argument("--detect-register", action="store_true", help="Detect MSA/dialect")

    args = parser.parse_args()
    proc = ArabicProcessor()

    if args.normalize:
        print(proc.normalize_orthography(args.text))
    if args.strip_diacritics:
        print(proc.remove_diacritics(args.text))
    if args.detect_register:
        print(proc.detect_register(args.text))
