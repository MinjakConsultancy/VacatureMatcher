"""Tests for CV/motivatie document parsing."""

from __future__ import annotations

import io

import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, StreamObject

from app.services.cv_parser import parse_cv_bytes


def _make_text_pdf(text: str) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})
    })
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    lines = escaped.split("\n")
    parts = ["BT", "/F1 12 Tf", "72 720 Td"]
    for i, line in enumerate(lines):
        if i > 0:
            parts.append("0 -14 Td")
        parts.append(f"({line}) Tj")
    parts.append("ET")
    stream = StreamObject()
    stream.set_data("\n".join(parts).encode("latin-1"))
    page.replace_contents(stream)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_parse_txt():
    data = "Jan Jansen\nPython developer".encode("utf-8")
    result = parse_cv_bytes(data, "cv.txt")
    assert "Jan Jansen" in result
    assert "Python developer" in result


def test_parse_pdf_with_text():
    data = _make_text_pdf("Jan Jansen\nPython developer")
    result = parse_cv_bytes(data, "cv.pdf")
    assert "Jan Jansen" in result
    assert "Python developer" in result


def test_parse_unsupported_extension():
    with pytest.raises(ValueError, match="Alleen .pdf, .docx of .txt toegestaan"):
        parse_cv_bytes(b"data", "cv.doc")


def test_parse_pdf_without_text():
    data = _make_blank_pdf()
    with pytest.raises(ValueError, match="geen leesbare tekst"):
        parse_cv_bytes(data, "cv.pdf")
