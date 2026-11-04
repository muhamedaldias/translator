#!/usr/bin/env python3
"""
translate_book.py — CLI for book translation.

Translates books chapter by chapter with cross-chapter consistency.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.book import BookTranslator


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Translate a book chapter by chapter with consistency tracking"
    )
    parser.add_argument("--input", required=True, help="Input book file or directory of chapters")
    parser.add_argument("--target", default="ar", help="Target language (default: ar)")
    parser.add_argument("--output", help="Output directory for translated chapters")
    parser.add_argument("--format", default="txt", help="Book format: txt, epub, pdf, docx, md")

    args = parser.parse_args()

    translator = BookTranslator(target_lang=args.target)

    input_path = Path(args.input)
    if input_path.is_dir():
        chapters = sorted(
            str(p) for p in input_path.glob("*")
            if p.suffix.lower() in (".txt", ".md")
        )
    else:
        chapters = [str(input_path)]

    results = translator.translate_book(chapters, output_dir=args.output)

    print(f"\n=== Book Translation Complete ===")
    print(f"Chapters: {len(results)}")
    for r in results:
        status = "APPROVED" if r["approved"] else "NEEDS REVIEW"
        print(f"  Chapter {r['chapter']}: score={r['judge_score']}, {status}")

    status = translator.get_status()
    print(f"\nProgress: {status['completed']}/{status['total_chapters']} ({status['completion_percent']:.1f}%)")


if __name__ == "__main__":
    main()
