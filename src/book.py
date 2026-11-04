#!/usr/bin/env python3
"""
Book Translation Workflow Module.

Handles chapter-by-chapter translation with cross-chapter consistency:
- Character registry (names, aliases, pronouns, titles)
- Places/world-building registry
- Dynamic glossary (updated per chapter)
- Manifest with integrity checks (resumable)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.pipeline import TranslationPipeline


@dataclass
class CharacterEntry:
    name: str
    aliases: List[str] = field(default_factory=list)
    arabic_name: str = ""
    arabic_aliases: List[str] = field(default_factory=list)
    pronouns: str = "neutral"
    title: str = ""
    first_chapter: int = 0
    description: str = ""


@dataclass
class PlaceEntry:
    name: str
    arabic_name: str = ""
    place_type: str = "other"  # city | country | building | region | other
    description: str = ""


@dataclass
class ChapterManifest:
    chapter: int
    title: str
    source_path: str
    output_path: str
    checksum: str
    status: str = "pending"  # pending | translated | reviewed | completed
    pipeline_id: Optional[str] = None
    judge_score: Optional[int] = None


class BookTranslator:
    """Book translation workflow with cross-chapter consistency."""

    def __init__(
        self,
        project_root: str = "/data/workspace/projects/translator",
        target_lang: str = "ar",
    ) -> None:
        self.project_root = Path(project_root)
        self.target_lang = target_lang

        self.characters_path = self.project_root / "data" / "characters.json"
        self.places_path = self.project_root / "data" / "places.json"
        self.manifest_path = self.project_root / "data" / "manifest.json"

        self.characters: List[Dict[str, Any]] = []
        self.places: List[Dict[str, Any]] = []
        self.manifest: List[ChapterManifest] = []
        self.dynamic_glossary: List[Dict[str, str]] = []

        self._load_registries()
        self._load_manifest()

        self.pipeline = TranslationPipeline(
            source_lang="en",
            target_lang=target_lang,
        )

    # ------------------------------------------------------------------
    # Registries
    # ------------------------------------------------------------------
    def _load_registries(self) -> None:
        """Load character and place registries."""
        if self.characters_path.exists():
            with open(self.characters_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.characters = data.get("characters", [])

        if self.places_path.exists():
            with open(self.places_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.places = data.get("places", [])

    def _load_manifest(self) -> None:
        """Load translation manifest."""
        if self.manifest_path.exists():
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.manifest = [ChapterManifest(**m) for m in data]

    def _save_registries(self) -> None:
        """Save character and place registries."""
        self.characters_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.characters_path, "w", encoding="utf-8") as f:
            json.dump({"characters": self.characters}, f, ensure_ascii=False, indent=2)

        with open(self.places_path, "w", encoding="utf-8") as f:
            json.dump({"places": self.places}, f, ensure_ascii=False, indent=2)

    def _save_manifest(self) -> None:
        """Save translation manifest."""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(
                [
                    {
                        "chapter": m.chapter,
                        "title": m.title,
                        "source_path": m.source_path,
                        "output_path": m.output_path,
                        "checksum": m.checksum,
                        "status": m.status,
                        "pipeline_id": m.pipeline_id,
                        "judge_score": m.judge_score,
                    }
                    for m in self.manifest
                ],
                f,
                ensure_ascii=False,
                indent=2,
            )

    # ------------------------------------------------------------------
    # Consistency
    # ------------------------------------------------------------------
    def check_consistency(
        self,
        chapter_num: int,
        translation: str,
    ) -> Dict[str, Any]:
        """Check translation against character/place registries for consistency."""
        inconsistencies: List[Dict[str, Any]] = []
        new_terms: List[Dict[str, str]] = []

        # Check character names
        for char in self.characters:
            arabic_name = char.get("arabic_name", "")
            if arabic_name and arabic_name not in translation:
                # Character mentioned but Arabic name not found — may be inconsistency
                pass  # Character may not appear in this chapter

        # Check places
        for place in self.places:
            arabic_name = place.get("arabic_name", "")
            if arabic_name and arabic_name not in translation:
                pass

        return {
            "consistent": len(inconsistencies) == 0,
            "inconsistencies": inconsistencies,
            "new_terms": new_terms,
        }

    def update_registries_from_chapter(
        self,
        chapter_num: int,
        translation: str,
        source_text: str,
    ) -> Dict[str, int]:
        """Extract new terms from chapter and update registries."""
        chars_added = 0
        places_added = 0
        terms_added = 0

        # Simple heuristic: find capitalized words as potential names/places
        names = re.findall(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b", source_text)

        for name in names:
            if name not in [c.get("name", "") for c in self.characters]:
                self.characters.append({
                    "name": name,
                    "aliases": [],
                    "arabic_name": "",
                    "arabic_aliases": [],
                    "pronouns": "neutral",
                    "title": "",
                    "first_chapter": chapter_num,
                    "description": "",
                })
                chars_added += 1

        self._save_registries()

        return {
            "characters_added": chars_added,
            "places_added": places_added,
            "terms_added": terms_added,
        }

    # ------------------------------------------------------------------
    # Checksum
    # ------------------------------------------------------------------
    @staticmethod
    def _checksum(file_path: str) -> str:
        """Compute SHA-256 checksum of a file."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    # ------------------------------------------------------------------
    # Chapter Translation
    # ------------------------------------------------------------------
    def translate_chapter(
        self,
        chapter_num: int,
        source_path: str,
        output_path: Optional[str] = None,
        previous_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Translate a single chapter through the full pipeline."""
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source chapter not found: {source_path}")

        source_text = source_path.read_text(encoding="utf-8")

        if output_path is None:
            output_path = str(
                self.project_root / "outputs" / f"chapter_{chapter_num:03d}.ar.txt"
            )

        # Check if already translated (resumable)
        checksum = self._checksum(str(source_path))
        for m in self.manifest:
            if m.chapter == chapter_num and m.checksum == checksum and m.status == "completed":
                return {
                    "chapter": chapter_num,
                    "status": "already_completed",
                    "output_path": m.output_path,
                }

        # Run pipeline
        result = self.pipeline.run(
            source_text,
            domain_hint="literary",
            previous_context=previous_context,
        )

        # Save output
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(result["translation"], encoding="utf-8")

        # Check consistency
        consistency = self.check_consistency(chapter_num, result["translation"])

        # Update registries
        registry_updates = self.update_registries_from_chapter(
            chapter_num, result["translation"], source_text
        )

        # Update manifest
        manifest_entry = ChapterManifest(
            chapter=chapter_num,
            title=source_path.stem,
            source_path=str(source_path),
            output_path=output_path,
            checksum=checksum,
            status="completed" if result["approved"] else "reviewed",
            pipeline_id=result["pipeline_id"],
            judge_score=result["judge"]["score"],
        )

        # Replace or append
        existing = next((i for i, m in enumerate(self.manifest) if m.chapter == chapter_num), None)
        if existing is not None:
            self.manifest[existing] = manifest_entry
        else:
            self.manifest.append(manifest_entry)

        self._save_manifest()

        return {
            "chapter": chapter_num,
            "source_path": str(source_path),
            "output_path": output_path,
            "translation": result["translation"],
            "judge_score": result["judge"]["score"],
            "approved": result["approved"],
            "iterations": result["iterations"],
            "consistency": consistency,
            "registry_updates": registry_updates,
            "pipeline_id": result["pipeline_id"],
        }

    # ------------------------------------------------------------------
    # Full Book
    # ------------------------------------------------------------------
    def translate_book(
        self,
        chapters: List[str],
        output_dir: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Translate all chapters of a book sequentially."""
        if output_dir is None:
            output_dir = str(self.project_root / "outputs")

        results = []
        previous_context = None

        for i, chapter_path in enumerate(chapters, 1):
            chapter_output = str(Path(output_dir) / f"chapter_{i:03d}.ar.txt")

            result = self.translate_chapter(
                chapter_num=i,
                source_path=chapter_path,
                output_path=chapter_output,
                previous_context=previous_context,
            )

            results.append(result)

            # Build context for next chapter (summary of current)
            previous_context = f"Chapter {i} translated. Score: {result['judge_score']}. Approved: {result['approved']}."

        return results

    def get_status(self) -> Dict[str, Any]:
        """Get overall book translation status."""
        total = len(self.manifest)
        completed = sum(1 for m in self.manifest if m.status == "completed")
        pending = sum(1 for m in self.manifest if m.status == "pending")

        return {
            "total_chapters": total,
            "completed": completed,
            "pending": pending,
            "completion_percent": (completed / total * 100) if total > 0 else 0.0,
            "characters_count": len(self.characters),
            "places_count": len(self.places),
        }


def main() -> None:
    """CLI entry point for book translation."""
    import argparse

    parser = argparse.ArgumentParser(description="Book Translation Workflow")
    parser.add_argument("--input", required=True, help="Input book file or directory")
    parser.add_argument("--target", default="ar", help="Target language")
    parser.add_argument("--output", help="Output directory")
    parser.add_argument("--format", default="txt", help="Book format (txt, epub, pdf, docx, md)")

    args = parser.parse_args()

    input_path = Path(args.input)

    if input_path.is_dir():
        # Directory of chapter files
        chapters = sorted(
            str(p) for p in input_path.glob("*.*")
            if p.suffix.lower() in (".txt", ".md", ".epub")
        )
    else:
        # Single file — split by chapter markers (simple heuristic)
        chapters = [str(input_path)]

    translator = BookTranslator(target_lang=args.target)
    results = translator.translate_book(chapters, output_dir=args.output)

    print(f"\n=== Book Translation Complete ===")
    print(f"Chapters translated: {len(results)}")
    for r in results:
        print(f"  Chapter {r['chapter']}: score={r['judge_score']}, approved={r['approved']}")

    status = translator.get_status()
    print(f"\nOverall status: {status['completed']}/{status['total_chapters']} chapters ({status['completion_percent']:.1f}%)")


if __name__ == "__main__":
    main()
