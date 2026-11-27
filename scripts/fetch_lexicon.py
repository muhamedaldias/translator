#!/usr/bin/env python3
"""Opt-in downloader for open, redistributable EN/AR lexicon data.

No API keys and no committed dumps: raw downloads are streamed into the
gitignored ``data/cache`` directory and only compact, provenance-tagged JSONL
records are written to ``data/dictionaries``.

Sources:
  oewn           Open English WordNet 2025 XML (CC BY 4.0, English only)
  wiktionary-ar  kaikki.org extraction of Arabic Wiktionary (CC BY-SA 4.0 + GFDL)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zlib
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

SOURCES: dict[str, dict[str, str]] = {
    "oewn": {
        "url": "https://en-word.net/downloads/english-wordnet-2025.xml.gz",
        "filename": "english-wordnet-2025.xml.gz",
        "license": "CC BY 4.0",
    },
    "wiktionary-ar": {
        "url": "https://kaikki.org/dictionary/Arabic/kaikki.org-dictionary-Arabic.jsonl",
        "filename": "kaikki-arabic.jsonl",
        "license": "CC BY-SA 4.0 + GFDL",
    },
}

_ARABIC = re.compile(r"[\u0600-\u06FF]")
_ENGLISH_LANGS = {"en", "eng", "english"}
_OPEN_LICENSE_PATTERNS = (
    r"\bcc[\s-]*by[\s-]*sa[\s-]*4(?:\.0)?\b",
    r"\bcc[\s-]*by[\s-]*4(?:\.0)?\b",
    r"creative commons attribution",
    r"\bgfdl\b",
    r"gnu free documentation license",
)
_PROPRIETARY_MARKERS = (
    "merriam-webster",
    "merriam webster",
    "oxford",
    "collins",
    "all rights reserved",
    "proprietary",
)


def has_arabic(text: str) -> bool:
    """Return True when the text contains an Arabic block character."""
    return bool(_ARABIC.search(text))


def is_open_license(text: str) -> bool:
    """Recognise the open licences used by the supported sources only."""
    lowered = text.lower()
    if any(marker in lowered for marker in _PROPRIETARY_MARKERS):
        return False
    return any(re.search(pattern, lowered) for pattern in _OPEN_LICENSE_PATTERNS)


def default_output() -> Path:
    """Return the repo-local output path (inside the gitignored data dir)."""
    return REPO_ROOT / "data" / "dictionaries" / "lexicon.jsonl"


def _clean_en(text: str) -> str:
    """Reduce an English gloss to a compact term, dropping parentheticals."""
    term = re.split(r"[;(,]", text, maxsplit=1)[0]
    term = re.sub(r"\s+", " ", term).strip()
    if not term or len(term) > 80 or has_arabic(term) or not re.search(r"[A-Za-z]", term):
        return ""
    return term


def _oewn_entry_pair(entry: ET.Element) -> tuple[str, str] | None:
    """Convert one WN-LMF LexicalEntry into an (en, ar-or-empty) pair."""
    lemma = entry.find("Lemma")
    en = (lemma.get("writtenForm", "") if lemma is not None else "").strip()
    if not en:
        return None
    ar = ""
    for node in entry.iter():
        if node is entry:
            continue
        lang = node.get("lang", "") or node.get("{http://www.w3.org/XML/1998/namespace}lang", "")
        if lang.lower() in {"ar", "ara", "arabic"} and (node.text or "").strip():
            ar = (node.text or "").strip()
            break
    return en, ar


def oewn_pairs(xml_text: str) -> list[tuple[str, str]]:
    """Extract (en, ar-or-empty) pairs from a WN-LMF XML document.

    Open English WordNet is English-only, so ``ar`` is normally empty; an
    explicitly labelled Arabic translation is used when one is present.
    """
    root = ET.fromstring(xml_text)
    pairs = [pair for entry in root.iter("LexicalEntry") if (pair := _oewn_entry_pair(entry))]
    return list(dict.fromkeys(pairs))


def _pair_from_record(record: Any) -> tuple[str, str] | None:
    """Prefer explicit English translations, then English glosses."""
    if not isinstance(record, dict):
        return None
    ar = str(record.get("word", "")).strip()
    if not has_arabic(ar):
        return None

    translations = record.get("translations") or []
    if isinstance(translations, list):
        for item in translations:
            if not isinstance(item, dict):
                continue
            if str(item.get("lang", "")).lower() not in _ENGLISH_LANGS:
                continue
            value = item.get("word") or item.get("translation") or item.get("en") or ""
            en = _clean_en(str(value))
            if en:
                return en, ar

    senses = record.get("senses") or []
    if isinstance(senses, list):
        for sense in senses:
            if not isinstance(sense, dict):
                continue
            glosses = sense.get("glosses") or []
            if not isinstance(glosses, list):
                continue
            for gloss in glosses:
                en = _clean_en(str(gloss))
                if en:
                    return en, ar
    return None


def _pair_from_line(line: str) -> tuple[str, str] | None:
    if not line.strip():
        return None
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        return None
    return _pair_from_record(record)


def wiktionary_ar_pairs(jsonl_text: str) -> list[tuple[str, str]]:
    """Extract (en, ar) pairs from kaikki-style Arabic Wiktionary JSONL.

    Recognises explicit ``translations`` entries with ``lang == "en"`` and
    (for real kaikki dumps, which omit that field) English sense glosses.
    """
    pairs = [pair for line in jsonl_text.splitlines() if (pair := _pair_from_line(line))]
    return list(dict.fromkeys(pairs))


class _TeeReader:
    """Read bytes from a stream while mirroring them to a cache file."""

    def __init__(self, source: Any, sink: Any) -> None:
        self.source = source
        self.sink = sink

    def read(self, size: int = -1) -> bytes:
        chunk = self.source.read(size)
        if chunk:
            self.sink.write(chunk)
        return chunk


def _raw_chunks(reader: _TeeReader, size: int = 65536) -> Iterator[bytes]:
    while chunk := reader.read(size):
        yield chunk


def _gunzip_chunks(chunks: Iterable[bytes]) -> Iterator[bytes]:
    """Incrementally decompress a gzip stream without reading to its end."""
    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    for chunk in chunks:
        if block := decompressor.decompress(chunk):
            yield block
    if tail := decompressor.flush():
        yield tail


def _lines_from_chunks(chunks: Iterable[bytes]) -> Iterator[str]:
    buffer = b""
    for chunk in chunks:
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            yield line.decode("utf-8", "replace")
    if buffer.strip():
        yield buffer.decode("utf-8", "replace")


def _pairs_from_xml_chunks(chunks: Iterable[bytes], limit: int) -> Iterator[tuple[str, str]]:
    parser = ET.XMLPullParser(events=("end",))
    emitted = 0
    for chunk in chunks:
        parser.feed(chunk)
        for _event, element in parser.read_events():
            if element.tag != "LexicalEntry":
                continue
            pair = _oewn_entry_pair(element)
            element.clear()
            if pair:
                yield pair
                emitted += 1
                if emitted >= limit:
                    return


def _pairs_from_jsonl_chunks(chunks: Iterable[bytes], limit: int) -> Iterator[tuple[str, str]]:
    emitted = 0
    for line in _lines_from_chunks(chunks):
        pair = _pair_from_line(line)
        if pair:
            yield pair
            emitted += 1
            if emitted >= limit:
                return


def stream_pairs(source: str, limit: int, cache_dir: Path) -> Iterator[tuple[str, str]]:
    """Stream a limited number of pairs, caching the bytes actually fetched."""
    config = SOURCES[source]
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / config["filename"]
    request = urllib.request.Request(
        config["url"], headers={"User-Agent": "translator-lexicon-fetch/1.0"}
    )
    with (
        urllib.request.urlopen(request, timeout=60) as response,
        cache_path.open("wb") as sink,
    ):
        chunks = _raw_chunks(_TeeReader(response, sink))
        if source == "oewn":
            yield from _pairs_from_xml_chunks(_gunzip_chunks(chunks), limit)
        else:
            yield from _pairs_from_jsonl_chunks(chunks, limit)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", choices=sorted(SOURCES), required=True)
    parser.add_argument("--limit", type=int, default=100, help="maximum pairs to extract")
    parser.add_argument("--output", type=Path, default=None, help="output JSONL path")
    parser.add_argument(
        "--cache-dir", type=Path, default=REPO_ROOT / "data" / "cache", help="raw download cache"
    )
    args = parser.parse_args(argv)

    if args.limit < 1:
        parser.error("--limit must be at least 1")
    config = SOURCES[args.source]
    if not is_open_license(config["license"]):
        parser.error(f"source {args.source} has a non-open licence: {config['license']}")

    output = args.output or default_output()
    output.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    ar_pairs = 0
    with output.open("w", encoding="utf-8") as handle:
        for en, ar in stream_pairs(args.source, args.limit, args.cache_dir):
            record = {
                "en": en,
                "ar": ar,
                "source": args.source,
                "license": config["license"],
            }
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            written += 1
            ar_pairs += bool(ar)

    print(f"wrote {written} records to {output}")
    print(f"source={args.source} license={config['license']} en_ar_pairs={ar_pairs}")
    if ar_pairs == 0:
        print(f"note: {args.source} does not yield Arabic translations; 'ar' is empty throughout")
    return 0


if __name__ == "__main__":
    sys.exit(main())
