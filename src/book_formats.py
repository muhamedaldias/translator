#!/usr/bin/env python3
"""
Book Format Handlers.

Supports reading/writing multiple book formats:
- Plain text (.txt)
- Markdown (.md)
- EPUB (.epub)
- DOCX (.docx)
- PDF (.pdf, read-only; rationalised text export)

Each handler extracts translatable text while preserving structure,
and reconstructs the file with translated content.

Design notes
------------
* Optional third-party packages (ebooklib, beautifulsoup4, python-docx,
  pypdf) are imported lazily, only inside the handlers that need them.
  Importing this module never requires them. A missing package raises an
  actionable ImportError that names the exact pip command to run.
* Format discovery is data-driven: every handler declares its ``extensions``
  and :func:`list_supported_formats` / :func:`get_handler` use that data.
"""

from __future__ import annotations

import html
import importlib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ------------------------------------------------------------------
# Optional dependency helpers (lazy + actionable errors)
# ------------------------------------------------------------------
_OPTIONAL_DEPS: dict[str, str] = {
    "ebooklib": "ebooklib beautifulsoup4",
    "bs4": "beautifulsoup4",
    "docx": "python-docx",
    "pypdf": "pypdf",
}


def _require(module_name: str) -> Any:
    """Import an optional dependency or raise an actionable ImportError."""
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        packages = _OPTIONAL_DEPS.get(module_name, module_name)
        raise ImportError(
            f"Optional dependency '{module_name}' is required for this book "
            f"format. Install it with: pip install {packages}"
        ) from exc


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

    extensions: tuple[str, ...] = ()

    @classmethod
    def can_handle(cls, file_path: str) -> bool:
        return str(file_path).lower().endswith(cls.extensions)

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
        language: str | None = None,
    ) -> None:
        """Reconstruct the book with translated segments."""
        ...


class TextHandler(BookFormatHandler):
    """Handler for plain text (.txt) and Markdown (.md) files."""

    extensions = (".txt", ".md")

    def parse(self, file_path: str) -> BookStructure:
        path = Path(file_path)
        # Only strip surrounding newlines so that leading indentation on the
        # first paragraph (an indented code block) survives detection.
        text = path.read_text(encoding="utf-8").strip("\n")

        structure = BookStructure(
            title=path.stem,
            format=path.suffix.lower().lstrip("."),
            language="en",
        )

        paragraphs = re.split(r"\n\s*\n", text)

        segment_id = 0
        chapter = 1

        for raw in paragraphs:
            # Detect indentation BEFORE stripping — a stripped string can
            # never start with spaces or a tab.
            is_code = raw.startswith(("    ", "\t"))
            para = raw.strip()
            if not para:
                continue

            if re.match(r"^(#{1,6}\s|CHAPTER|Chapter|الفصل)", para, re.IGNORECASE):
                segment_type = "heading"
                chapter += 1
            elif is_code:
                segment_type = "code_block"
            else:
                segment_type = "paragraph"

            # Keep the original indentation for code blocks so they can be
            # reproduced verbatim during reconstruction.
            segment_text = raw.rstrip() if is_code else para

            segment = BookSegment(
                id=f"seg_{segment_id}",
                text=segment_text,
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
        language: str | None = None,
    ) -> None:
        """Reconstruct a text file with translated segments."""
        output_segments = [translations.get(seg.id, seg.text) for seg in structure.segments]
        output_text = "\n\n".join(output_segments)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(output_text, encoding="utf-8")


class EPUBHandler(BookFormatHandler):
    """Handler for EPUB files."""

    extensions = (".epub",)

    def parse(self, file_path: str) -> BookStructure:
        """Parse EPUB file into segments."""
        ebooklib = _require("ebooklib")
        epub = _require("ebooklib.epub")
        BeautifulSoup = _require("bs4").BeautifulSoup

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

            if not structure.title and soup.title:
                structure.title = soup.title.get_text()

            text = soup.get_text("\n", strip=True)
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

            structure.chapters.append(
                {"number": chapter, "title": soup.title.get_text() if soup.title else ""}
            )

            for para in paragraphs:
                structure.segments.append(
                    BookSegment(
                        id=f"seg_{segment_id}",
                        text=para,
                        segment_type="paragraph",
                        chapter=chapter,
                        position=segment_id,
                    )
                )
                structure.total_words += len(para.split())
                segment_id += 1

            chapter += 1

        return structure

    def reconstruct(
        self,
        structure: BookStructure,
        translations: dict[str, str],
        output_path: str,
        language: str | None = None,
    ) -> None:
        """Reconstruct a valid EPUB: metadata language + complete spine."""
        epub = _require("ebooklib.epub")

        output_language = language or structure.language or "ar"
        book = epub.EpubBook()
        book.set_title(structure.title or "Translated Book")
        book.set_language(output_language)
        # Arabic is RTL — declare primary reading direction when relevant.
        if output_language.lower().startswith("ar"):
            try:
                book.add_metadata("DC", "direction", "rtl")
            except Exception:  # pragma: no cover - older ebooklib versions
                pass

        chapters_by_number: dict[int, list[BookSegment]] = {}
        for seg in structure.segments:
            chapters_by_number.setdefault(seg.chapter, []).append(seg)

        chapter_titles = {
            int(c.get("number", i + 1)): c.get("title", "")
            for i, c in enumerate(structure.chapters)
        }

        chapter_items: list[Any] = []
        toc: list[Any] = []
        for chap_num, segs in sorted(chapters_by_number.items()):
            title = chapter_titles.get(chap_num) or f"Chapter {chap_num}"
            file_name = f"chap_{chap_num}.xhtml"
            chapter = epub.EpubHtml(
                title=title,
                file_name=file_name,
                lang=output_language,
            )

            # Escape translated text before interpolating into XHTML so
            # '&', '<' and '>' cannot break the chapter markup.
            paras = [html.escape(translations.get(seg.id, seg.text), quote=False) for seg in segs]
            chapter.content = (
                "<html><head><meta charset='utf-8'/></head><body>"
                + "\n".join(f"<p>{p}</p>" for p in paras)
                + "</body></html>"
            )

            book.add_item(chapter)
            chapter_items.append(chapter)
            toc.append(epub.Link(file_name, title, f"chap_{chap_num}"))

        # A valid EPUB needs a spine that references every chapter plus the
        # navigation document. Without it readers show an empty book.
        nav = epub.EpubNav()
        ncx = epub.EpubNcx()
        book.add_item(ncx)
        book.add_item(nav)
        book.toc = toc or [nav]
        book.spine = ["nav"] + chapter_items

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        epub.write_epub(output_path, book, {})


class DOCXHandler(BookFormatHandler):
    """Handler for DOCX files."""

    extensions = (".docx",)

    def parse(self, file_path: str) -> BookStructure:
        """Parse DOCX file into segments."""
        Document = _require("docx").Document

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

            style_name = para.style.name
            if style_name.startswith("Heading"):
                segment_type = "heading"
                chapter += 1
            else:
                segment_type = "paragraph"

            structure.segments.append(
                BookSegment(
                    id=f"seg_{segment_id}",
                    text=text,
                    segment_type=segment_type,
                    chapter=chapter,
                    position=segment_id,
                    metadata={"style": style_name},
                )
            )
            structure.total_words += len(text.split())
            segment_id += 1

        return structure

    def reconstruct(
        self,
        structure: BookStructure,
        translations: dict[str, str],
        output_path: str,
        language: str | None = None,
    ) -> None:
        """Reconstruct DOCX with translated segments."""
        Document = _require("docx").Document

        doc = Document()
        doc.add_heading(structure.title or "Translated Book", level=0)

        for seg in structure.segments:
            translated = translations.get(seg.id, seg.text)
            if seg.segment_type == "heading":
                doc.add_heading(translated, level=1)
            else:
                p = doc.add_paragraph(translated)
                style_name = seg.metadata.get("style", "Normal")
                try:
                    p.style = doc.styles[style_name]
                except KeyError:
                    pass

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path)


class PDFHandler(BookFormatHandler):
    """Handler for PDF files (text extraction only)."""

    extensions = (".pdf",)

    def parse(self, file_path: str) -> BookStructure:
        """Parse PDF file into segments."""
        pdf_module = _require("pypdf")

        structure = BookStructure(
            title=Path(file_path).stem,
            format="pdf",
            language="en",
        )

        segment_id = 0
        chapter = 1

        with open(file_path, "rb") as f:
            reader = pdf_module.PdfReader(f)
            for page in reader.pages:
                text = page.extract_text() or ""
                paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
                for para in paragraphs:
                    structure.segments.append(
                        BookSegment(
                            id=f"seg_{segment_id}",
                            text=para,
                            segment_type="paragraph",
                            chapter=chapter,
                            position=segment_id,
                            metadata={"page": chapter},
                        )
                    )
                    structure.total_words += len(para.split())
                    segment_id += 1
                chapter += 1

        return structure

    def reconstruct(
        self,
        structure: BookStructure,
        translations: dict[str, str],
        output_path: str,
        language: str | None = None,
    ) -> None:
        """Export translated text.

        PDF *generation* is not supported: writing plain text to a ``.pdf``
        path would produce a corrupt, misleading file. Refuse explicitly and
        direct the caller to a real PDF converter. A ``.txt``/``.md`` export
        is allowed as an honest fallback.
        """
        suffix = Path(output_path).suffix.lower()
        if suffix == ".pdf":
            raise NotImplementedError(
                "PDF output is not supported: this handler can only extract "
                "text from PDFs. Use a .txt/.md output path, or convert the "
                "exported text to PDF with a dedicated tool (e.g. pandoc)."
            )
        if suffix not in (".txt", ".md"):
            raise ValueError(
                f"Unsupported PDF-export target '{suffix or '(no extension)'}'. "
                "Use .txt or .md, or a real PDF converter."
            )

        output_lines: list[str] = []
        current_chapter = 0
        for seg in structure.segments:
            translated = translations.get(seg.id, seg.text)
            if seg.chapter != current_chapter:
                current_chapter = seg.chapter
                output_lines.append(f"\n=== Chapter {current_chapter} ===\n")
            output_lines.append(translated)
            output_lines.append("")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text("\n".join(output_lines), encoding="utf-8")


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
    raise ValueError(f"No handler available for file format: {file_path}")


def list_supported_formats() -> list[str]:
    """List all supported file extensions (data-driven from handlers)."""
    seen: list[str] = []
    for handler in HANDLERS:
        for ext in handler.extensions:
            if ext not in seen:
                seen.append(ext)
    return seen


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Book Format Handler Test")
    parser.add_argument("--file", help="Book file to parse")
    parser.add_argument("--list-formats", action="store_true", help="List supported formats")

    args = parser.parse_args()

    if args.list_formats:
        print("Supported formats: " + ", ".join(list_supported_formats()))
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
    else:
        parser.error("provide --file or --list-formats")
