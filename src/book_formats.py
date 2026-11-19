#!/usr/bin/env python3
"""
Book Format Handlers.

Supports reading/writing multiple book formats:
- Plain text (.txt)
- Markdown (.md)
- EPUB (.epub)
- DOCX (.docx)
- PDF (.pdf)

Each handler extracts translatable text while preserving structure,
and reconstructs the file with translated content.
"""

from __future__ import annotations

import html
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BookSegment:
    """A translatable segment of a book."""
    id: str
    text: str
    segment_type: str = "paragraph"  # paragraph, heading, code_block, title, etc.
    chapter: int = 0
    position: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BookStructure:
    """Parsed book structure with segments and metadata."""
    title: str = ""
    author: str = ""
    language: str = "en"
    chapters: list[dict[str, Any]] = field(default_factory=list)
    segments: list[BookSegment] = field(default_factory=list)
    total_words: int = 0
    format: str = "txt"


class BookFormatHandler(ABC):
    """Abstract base class for book format handlers."""

    @abstractmethod
    def can_handle(self, file_path: str) -> bool:
        """Check if this handler can process the file."""
        ...

    @abstractmethod
    def parse(self, file_path: str) -> BookStructure:
        """Parse a book file into segments."""
        ...

    @abstractmethod
    def reconstruct(
        self,
        structure: BookStructure,
        translations: dict[str, str],
        output_path: str,
    ) -> None:
        """Reconstruct the book with translated segments."""
        ...


class TextHandler(BookFormatHandler):
    """Handler for plain text (.txt) and Markdown (.md) files."""

    def can_handle(self, file_path: str) -> bool:
        return file_path.lower().endswith((".txt", ".md"))

    def parse(self, file_path: str) -> BookStructure:
        path = Path(file_path)
        text = path.read_text(encoding="utf-8")

        structure = BookStructure(
            title=path.stem,
            format=path.suffix.lower().lstrip("."),
            language="en",
        )

        # Split into paragraphs
        paragraphs = re.split(r"\n\s*\n", text.strip())

        segment_id = 0
        chapter = 1
        seen_content = False

        for para in paragraphs:
            stripped = para.strip()
            if not stripped:
                continue

            # Detect fenced/indented code BEFORE stripping indentation
            if (
                stripped.startswith(("```", "~~~"))
                or para.startswith(("    ", "\t"))
            ):
                segment_type = "code_block"
            elif re.match(r"^(#{1,6}\s|CHAPTER|Chapter|الفصل|الفصل\s+\d+)", stripped, re.IGNORECASE):
                segment_type = "heading"
                if seen_content:
                    chapter += 1
            else:
                segment_type = "paragraph"
            seen_content = True
            para = stripped

            segment = BookSegment(
                id=f"seg_{segment_id}",
                text=para,
                segment_type=segment_type,
                chapter=chapter,
                position=segment_id,
            )
            structure.segments.append(segment)
            structure.total_words += len(para.split())
            segment_id += 1

        return structure

    def reconstruct(
        self,
        structure: BookStructure,
        translations: dict[str, str],
        output_path: str,
    ) -> None:
        """Reconstruct text file with translated segments."""
        output_segments = []

        for seg in structure.segments:
            translated = translations.get(seg.id, seg.text)
            output_segments.append(translated)

        output_text = "\n\n".join(output_segments)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(output_text, encoding="utf-8")


class EPUBHandler(BookFormatHandler):
    """Handler for EPUB files."""

    def can_handle(self, file_path: str) -> bool:
        return file_path.lower().endswith(".epub")

    def parse(self, file_path: str) -> BookStructure:
        """Parse EPUB file into segments."""
        try:
            import ebooklib  # type: ignore
            from bs4 import BeautifulSoup  # type: ignore
            from ebooklib import epub  # type: ignore
        except ImportError:
            raise ImportError(
                "EPUB support requires: pip install ebooklib beautifulsoup4"
            )

        book = epub.read_epub(file_path)
        structure = BookStructure(
            title=Path(file_path).stem,
            format="epub",
            language="en",
        )

        segment_id = 0
        chapter = 1

        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            content = item.get_content()
            soup = BeautifulSoup(content, "html.parser")

            # Extract title metadata
            if not structure.title and soup.title:
                structure.title = soup.title.get_text()

            # Extract BLOCK-level elements so inline tags (<em>, <code>)
            # do not fragment sentences into separate segments
            blocks = soup.find_all(
                ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote"]
            )
            if blocks:
                paragraphs = [b.get_text(" ", strip=True) for b in blocks]
            else:
                text = soup.get_text("\n", strip=True)
                paragraphs = [p.strip() for p in text.split("\n")]
            paragraphs = [p for p in paragraphs if p]

            for para in paragraphs:
                segment = BookSegment(
                    id=f"seg_{segment_id}",
                    text=para,
                    segment_type="paragraph",
                    chapter=chapter,
                    position=segment_id,
                )
                structure.segments.append(segment)
                structure.total_words += len(para.split())
                segment_id += 1

            chapter += 1

        return structure

    def reconstruct(
        self,
        structure: BookStructure,
        translations: dict[str, str],
        output_path: str,
    ) -> None:
        """Reconstruct EPUB with translated segments."""
        try:
            from ebooklib import epub  # type: ignore
        except ImportError:
            raise ImportError(
                "EPUB support requires: pip install ebooklib beautifulsoup4"
            )

        # For simplicity, create a new EPUB with translated text
        book = epub.EpubBook()
        book.set_title(structure.title)
        book.set_language(structure.language or "ar")

        # Group segments by chapter
        chapters: dict[int, list[BookSegment]] = {}
        for seg in structure.segments:
            chapters.setdefault(seg.chapter, []).append(seg)

        for chap_num, segs in sorted(chapters.items()):
            chapter = epub.EpubHtml(
                title=f"Chapter {chap_num}",
                file_name=f"chap_{chap_num}.xhtml",
                lang=structure.language or "ar",
            )

            translated_paras = []
            for seg in segs:
                translated = translations.get(seg.id, seg.text)
                # Escape: translation text must never inject markup into the EPUB
                translated_paras.append(f"<p>{html.escape(translated)}</p>")

            chapter.content = (
                "<html><head><meta charset='utf-8'/></head>"
                "<body>"
                + "\n".join(translated_paras)
                + "</body></html>"
            )

            book.add_item(chapter)

        book.toc = [
            epub.Link(f"chap_{c}.xhtml", f"Chapter {c}", f"chap_{c}")
            for c in sorted(chapters.keys())
        ]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        epub.write_epub(output_path, book, {})


class DOCXHandler(BookFormatHandler):
    """Handler for DOCX files."""

    def can_handle(self, file_path: str) -> bool:
        return file_path.lower().endswith(".docx")

    def parse(self, file_path: str) -> BookStructure:
        """Parse DOCX file into segments."""
        try:
            from docx import Document  # type: ignore
        except ImportError:
            raise ImportError(
                "DOCX support requires: pip install python-docx"
            )

        doc = Document(file_path)
        structure = BookStructure(
            title=Path(file_path).stem,
            format="docx",
            language="en",
        )

        segment_id = 0
        chapter = 1

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            # Detect headings
            style_name = para.style.name if para.style is not None else "Normal"
            if style_name.startswith("Heading"):
                segment_type = "heading"
                chapter += 1
            else:
                segment_type = "paragraph"

            segment = BookSegment(
                id=f"seg_{segment_id}",
                text=text,
                segment_type=segment_type,
                chapter=chapter,
                position=segment_id,
                metadata={"style": style_name},
            )
            structure.segments.append(segment)
            structure.total_words += len(text.split())
            segment_id += 1

        return structure

    def reconstruct(
        self,
        structure: BookStructure,
        translations: dict[str, str],
        output_path: str,
    ) -> None:
        """Reconstruct DOCX with translated segments."""
        try:
            from docx import Document  # type: ignore
        except ImportError:
            raise ImportError(
                "DOCX support requires: pip install python-docx"
            )

        doc = Document()

        # Set title
        doc.add_heading(structure.title, level=0)

        for seg in structure.segments:
            translated = translations.get(seg.id, seg.text)

            if seg.segment_type == "heading":
                doc.add_heading(translated, level=1)
            else:
                p = doc.add_paragraph(translated)
                # Preserve style if available
                style_name = seg.metadata.get("style", "Normal")
                try:
                    p.style = doc.styles[style_name]
                except KeyError:
                    pass

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path)


class PDFHandler(BookFormatHandler):
    """Handler for PDF files (text extraction only)."""

    def can_handle(self, file_path: str) -> bool:
        return file_path.lower().endswith(".pdf")

    def parse(self, file_path: str) -> BookStructure:
        """Parse PDF file into segments."""
        try:
            import pypdf as PyPDF2  # type: ignore
        except ImportError:
            try:
                import PyPDF2  # type: ignore
            except ImportError:
                raise ImportError(
                    "PDF support requires: pip install pypdf"
                )

        structure = BookStructure(
            title=Path(file_path).stem,
            format="pdf",
            language="en",
        )

        segment_id = 0
        chapter = 1

        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)

            for page_num, page in enumerate(reader.pages):
                text = page.extract_text() or ""

                # Split into paragraphs
                paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

                for para in paragraphs:
                    segment = BookSegment(
                        id=f"seg_{segment_id}",
                        text=para,
                        segment_type="paragraph",
                        chapter=chapter,
                        position=segment_id,
                        metadata={"page": page_num + 1},
                    )
                    structure.segments.append(segment)
                    structure.total_words += len(para.split())
                    segment_id += 1

                chapter += 1

        return structure

    def reconstruct(
        self,
        structure: BookStructure,
        translations: dict[str, str],
        output_path: str,
    ) -> None:
        """Reconstruct PDF with translated segments (text-only output).

        Real PDF typesetting is not implemented; writing plain text to a
        .pdf path would produce a corrupt 'PDF', so text goes to a .txt
        sibling instead.
        """
        out = Path(output_path)
        if out.suffix.lower() == ".pdf":
            out = out.with_suffix(".txt")
            logger.warning(
                "PDF reconstruction is text-only; writing %s instead of a fake .pdf", out
            )
        output_lines = []
        current_chapter = 0

        for seg in structure.segments:
            translated = translations.get(seg.id, seg.text)
            if seg.chapter != current_chapter:
                current_chapter = seg.chapter
                output_lines.append(f"\n=== Chapter {current_chapter} ===\n")
            output_lines.append(translated)
            output_lines.append("")

        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(output_lines), encoding="utf-8")


# ------------------------------------------------------------------
# Handler registry
# ------------------------------------------------------------------
HANDLERS: list[BookFormatHandler] = [
    TextHandler(),
    EPUBHandler(),
    DOCXHandler(),
    PDFHandler(),
]


def get_handler(file_path: str) -> BookFormatHandler:
    """Get the appropriate format handler for a file."""
    for handler in HANDLERS:
        if handler.can_handle(file_path):
            return handler
    raise ValueError(
        f"No handler available for file format: {file_path}"
    )


def list_supported_formats() -> list[str]:
    """List all supported file formats."""
    return [".txt", ".md", ".epub", ".docx", ".pdf"]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Book Format Handler Test")
    parser.add_argument("--file", required=True, help="Book file to parse")
    parser.add_argument("--list-formats", action="store_true", help="List supported formats")

    args = parser.parse_args()

    if args.list_formats:
        print("Supported formats: .txt, .md, .epub, .docx, .pdf")
    elif args.file:
        handler = get_handler(args.file)
        structure = handler.parse(args.file)
        print(f"Book: {structure.title}")
        print(f"Format: {structure.format}")
        print(f"Segments: {len(structure.segments)}")
        print(f"Total words: {structure.total_words}")
        print("\nFirst 3 segments:")
        for seg in structure.segments[:3]:
            print(f"  [{seg.id}] {seg.segment_type} (ch{seg.chapter}): {seg.text[:80]}")
