#!/usr/bin/env python3
"""
Focused tests for book format handlers (Task B).

Covers: code-block detection before strip, EPUB spine + language,
PDF refusing to fake a .pdf, data-driven format listing, and lazy,
actionable optional-dependency errors.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import src.book_formats as bf
from src.book_formats import (
    BookSegment,
    BookStructure,
    DOCXHandler,
    EPUBHandler,
    PDFHandler,
    TextHandler,
    get_handler,
    list_supported_formats,
)

VENV_PY = sys.executable


# ------------------------------------------------------------------
# Text / Markdown
# ------------------------------------------------------------------
def test_indented_code_block_detected_before_strip(tmp_path):
    path = tmp_path / "book.txt"
    path.write_text(
        "Intro paragraph.\n\n    print('hello')\n\nOutro paragraph.",
        encoding="utf-8",
    )
    structure = TextHandler().parse(str(path))
    code = [s for s in structure.segments if s.segment_type == "code_block"]
    assert len(code) == 1
    assert code[0].text.startswith("    ")
    assert "print('hello')" in code[0].text


def test_tab_indented_code_block_detected(tmp_path):
    path = tmp_path / "book.md"
    path.write_text("# Title\n\n\tcode line", encoding="utf-8")
    structure = TextHandler().parse(str(path))
    assert any(s.segment_type == "code_block" for s in structure.segments)


def test_text_reconstruct_writes_translated_segments(tmp_path):
    structure = BookStructure(title="t", format="txt")
    structure.segments = [
        BookSegment(id="s0", text="Hello", chapter=1),
        BookSegment(id="s1", text="World", chapter=1),
    ]
    out = tmp_path / "out.txt"
    TextHandler().reconstruct(structure, {"s0": "مرحبا"}, str(out))
    assert "مرحبا" in out.read_text(encoding="utf-8")
    assert "World" in out.read_text(encoding="utf-8")


# ------------------------------------------------------------------
# Format registry
# ------------------------------------------------------------------
def test_list_supported_formats():
    formats = list_supported_formats()
    assert set(formats) == {".txt", ".md", ".epub", ".docx", ".pdf"}
    assert all(f.startswith(".") for f in formats)


def test_get_handler_selects_correct_class():
    assert isinstance(get_handler("book.txt"), TextHandler)
    assert isinstance(get_handler("book.md"), TextHandler)
    assert isinstance(get_handler("book.epub"), EPUBHandler)
    assert isinstance(get_handler("book.docx"), DOCXHandler)
    assert isinstance(get_handler("book.pdf"), PDFHandler)
    with pytest.raises(ValueError):
        get_handler("book.xyz")


# ------------------------------------------------------------------
# PDF: never fake a PDF
# ------------------------------------------------------------------
def test_pdf_reconstruct_refuses_pdf_path(tmp_path):
    structure = BookStructure(title="t", format="pdf")
    structure.segments = [BookSegment(id="s0", text="body", chapter=1)]
    with pytest.raises(NotImplementedError, match="PDF output is not supported"):
        PDFHandler().reconstruct(structure, {}, str(tmp_path / "out.pdf"))


def test_pdf_reconstruct_text_export_is_explicit(tmp_path):
    structure = BookStructure(title="t", format="pdf")
    structure.segments = [BookSegment(id="s0", text="body", chapter=1)]
    out = tmp_path / "out.txt"
    PDFHandler().reconstruct(structure, {"s0": "محتوى"}, str(out))
    text = out.read_text(encoding="utf-8")
    assert "Chapter 1" in text
    assert "محتوى" in text


# ------------------------------------------------------------------
# EPUB: valid spine, all chapters, declared language
# ------------------------------------------------------------------
def test_epub_reconstruct_keeps_spine_and_language(monkeypatch, tmp_path):
    captured = {}

    class FakeEpubHtml:
        def __init__(self, title, file_name, lang):
            self.title = title
            self.file_name = file_name
            self.lang = lang
            self.content = None

    class FakeLink:
        def __init__(self, href, title, uid):
            self.href, self.title, self.uid = href, title, uid

    class FakeNav:
        pass

    class FakeNcx:
        pass

    class FakeBook:
        def __init__(self):
            self.spine = None
            self.toc = None
            self.language = None
            self.title = None
            self.items = []
            self.metadata = []

        def set_title(self, title):
            self.title = title

        def set_language(self, language):
            self.language = language

        def add_item(self, item):
            self.items.append(item)

        def add_metadata(self, *args):
            self.metadata.append(args)

    class FakeEpubModule:
        EpubBook = FakeBook
        EpubHtml = FakeEpubHtml
        EpubNcx = FakeNcx
        EpubNav = FakeNav
        Link = FakeLink

        def write_epub(self, path, book, opts):
            captured["book"] = book
            Path(path).write_bytes(b"EPUB")

    fake_epub = FakeEpubModule()

    def fake_import(name):
        if name == "ebooklib.epub":
            return fake_epub
        raise ImportError(name)

    monkeypatch.setattr(bf.importlib, "import_module", fake_import)

    structure = BookStructure(title="Translated", language="en", format="epub")
    structure.segments = [
        BookSegment(id="s0", text="one", chapter=1),
        BookSegment(id="s1", text="two", chapter=1),
        BookSegment(id="s2", text="three", chapter=2),
    ]
    out = tmp_path / "book.epub"
    EPUBHandler().reconstruct(
        structure, {"s1": "اثنان"}, str(out), language="ar"
    )

    book = captured["book"]
    assert book.language == "ar"
    assert book.spine[0] == "nav"
    chapters = [item for item in book.spine if item != "nav"]
    assert len(chapters) == 2  # both chapters are in the spine
    assert len(book.toc) == 2
    assert all(ch.lang == "ar" for ch in chapters)
    assert "اثنان" in chapters[0].content
    assert out.exists()


# ------------------------------------------------------------------
# Lazy, actionable optional dependency errors
# ------------------------------------------------------------------
@pytest.mark.parametrize(
    "call, expected",
    [
        (lambda: EPUBHandler().parse("x.epub"), "pip install ebooklib"),
        (lambda: EPUBHandler().reconstruct(BookStructure(), {}, "x.epub"), "pip install ebooklib"),
        (lambda: DOCXHandler().parse("x.docx"), "pip install python-docx"),
        (lambda: DOCXHandler().reconstruct(BookStructure(), {}, "x.docx"), "pip install python-docx"),
        (lambda: PDFHandler().parse("x.pdf"), "pip install pypdf"),
    ],
)
def test_optional_dependency_errors_are_actionable(monkeypatch, call, expected):
    def fake_import(name):
        raise ImportError(f"No module named '{name}'")

    monkeypatch.setattr(bf.importlib, "import_module", fake_import)
    with pytest.raises(ImportError) as excinfo:
        call()
    assert expected in str(excinfo.value)
    assert "Optional dependency" in str(excinfo.value)


def test_module_import_does_not_import_optional_dependencies():
    code = (
        "import sys; import src.book_formats; "
        "print([m for m in ('ebooklib','bs4','docx','PyPDF2','pypdf') if m in sys.modules])"
    )
    result = subprocess.run(
        [str(VENV_PY), "-c", code], cwd=str(ROOT), capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
