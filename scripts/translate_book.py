#!/usr/bin/env python3
"""
translate_book.py — CLI for the two-phase book translation workflow.

Phases
------
* ``--prepare``   : build a context-rich translation brief per chapter.
* ``--assemble``  : validate the host-produced translation against the brief
                    and write the final chapter output.
* (no phase flag) : legacy single-phase ``translate_book`` flow.

The CLI is defensive: it prints actionable errors instead of crashing, and
``--list-formats`` works without ``--input``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.book import BookTranslator
from src.book_formats import list_supported_formats


SOURCE_SUFFIXES = (".txt", ".md")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Translate a book chapter by chapter with consistency tracking"
    )
    parser.add_argument("--input", help="Input book file or directory of chapters")
    parser.add_argument("--target", default="ar", help="Target language (default: ar)")
    parser.add_argument("--output", help="Output directory (default: <repo>/outputs)")
    parser.add_argument("--format", default="txt", help="Book format: txt, md, epub, docx, pdf")
    parser.add_argument("--prepare", action="store_true", help="Build briefs for all chapters")
    parser.add_argument(
        "--assemble", action="store_true",
        help="Validate host translations against briefs and write output",
    )
    parser.add_argument(
        "--list-formats", action="store_true", help="List supported book formats and exit"
    )
    parser.add_argument(
        "--project-root",
        help="Project root holding data/ registries (default: repository root)",
    )
    parser.add_argument(
        "--translations",
        help="Directory (or single file) of host-produced translations for --assemble",
    )
    parser.add_argument("--chapter", help="Chapter id for a single-chapter --assemble")
    parser.add_argument(
        "--host-translation", help="Inline host translation text (used with --chapter)"
    )
    return parser


def _collect_sources(input_path: Path) -> List[Path]:
    if input_path.is_dir():
        return sorted(
            p for p in input_path.glob("*") if p.suffix.lower() in SOURCE_SUFFIXES
        )
    if input_path.exists():
        return [input_path]
    return []


def _slug(path: Path) -> str:
    import re
    match = re.search(r"(\d+)", path.stem)
    return f"{int(match.group(1)):03d}" if match else path.stem


def _run_prepare(translator: BookTranslator, args: argparse.Namespace, parser) -> int:
    if not args.input:
        parser.error("--input is required with --prepare")
    sources = _collect_sources(Path(args.input))
    if not sources:
        print(f"No source chapters found in: {args.input}")
        return 1

    previous_context: Optional[str] = None
    records = []
    for source in sources:
        chapter_id = _slug(source)
        info = translator.prepare_chapter(
            source_path=str(source),
            chapter_id=chapter_id,
            previous_context=previous_context,
            output_dir=args.output,
        )
        records.append(info)
        previous_context = (
            f"Chapter {chapter_id} source context: "
            f"{Path(source).read_text(encoding='utf-8')[:300]}... "
            f"Target language: {args.target}."
        )
        print(f"Prepared chapter {chapter_id}: {info['brief_path']}")

    print(f"\n{len(records)} chapter brief(s) prepared.")
    return 0


def _host_translation_inputs(args: argparse.Namespace, parser) -> List[tuple]:
    """Return a list of (chapter_id, translation_text) pairs."""
    if args.host_translation is not None:
        if not args.chapter:
            parser.error("--chapter is required with --host-translation")
        return [(args.chapter, args.host_translation)]

    if args.translations:
        path = Path(args.translations)
        files = (
            sorted(p for p in path.glob("*") if p.suffix.lower() in SOURCE_SUFFIXES)
            if path.is_dir()
            else ([path] if path.exists() else [])
        )
        if not files:
            print(f"No host translations found in: {args.translations}")
            return []
        return [( _slug(p), p.read_text(encoding="utf-8")) for p in files]

    if args.input and not Path(args.input).is_dir() and Path(args.input).exists():
        path = Path(args.input)
        return [(_slug(path), path.read_text(encoding="utf-8"))]

    parser.error(
        "--assemble needs --translations (file/dir), --host-translation with "
        "--chapter, or --input pointing to a translation file"
    )
    return []


def _run_assemble(translator: BookTranslator, args: argparse.Namespace, parser) -> int:
    pairs = _host_translation_inputs(args, parser)
    if not pairs:
        return 1

    for chapter_id, translation in pairs:
        result = translator.assemble_chapter(
            chapter_id, translation, output_dir=args.output
        )
        validation = result["validation"]
        status = "PASSED" if result["passed"] else "NEEDS REVIEW"
        issues = validation.get("issues", []) if isinstance(validation, dict) else []
        findings = result["consistency"].get("findings", [])
        print(
            f"Assembled chapter {chapter_id}: {status} "
            f"(score={result['judge_score']}) -> {result['output_path']}"
        )
        for issue in issues:
            print(f"  validation: {issue.get('code', 'issue')}: {issue.get('detail', issue)}")
        for finding in findings:
            print(f"  consistency: {finding['type']}: {finding['detail']}")

    print(f"\n{len(pairs)} chapter(s) assembled.")
    return 0


def _run_legacy(translator: BookTranslator, args: argparse.Namespace, parser) -> int:
    """No-flag flow: be explicit that it produces no translation."""
    if not args.input:
        parser.error("--input is required unless --list-formats is given")
    sources = _collect_sources(Path(args.input))
    if not sources:
        print(f"No source chapters found in: {args.input}")
        return 1

    print("=== No Translation Produced ===")
    print(
        "This CLI does not translate by itself: the host coding agent performs "
        "translation. Without --host-translation/--assemble (or --prepare) it "
        "produces no translated output."
    )
    print(
        f"Found {len(sources)} source chapter(s). Run the seven-stage agent "
        "workflow, then use --assemble with --translations <dir> or "
        "--host-translation with --chapter to validate and write the "
        "host-produced translation."
    )
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list_formats:
        print("Supported formats: " + ", ".join(list_supported_formats()))
        return 0

    if args.prepare and args.assemble:
        parser.error("use --prepare or --assemble, not both")

    try:
        translator = BookTranslator(
            target_lang=args.target, output_dir=args.output, project_root=args.project_root
        )
        if args.prepare:
            return _run_prepare(translator, args, parser)
        if args.assemble:
            return _run_assemble(translator, args, parser)
        return _run_legacy(translator, args, parser)
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return 1
    except ImportError as exc:
        print(f"Error: {exc}")
        return 1
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
