from __future__ import annotations

from pathlib import Path

import pytest

from apply_track.extract import UnsupportedFile, extract_text


def test_plain_text_roundtrip(tmp_path: Path):
    path = tmp_path / "resume.txt"
    path.write_text("Ada Lovelace\n\n\n\nAnalyst   \n", encoding="utf-8")

    out = extract_text(path)

    # Runs of blank lines collapse and trailing spaces go.
    assert out == "Ada Lovelace\n\nAnalyst"


def test_unsupported_extension_rejected(tmp_path: Path):
    path = tmp_path / "resume.pages"
    path.write_bytes(b"nope")

    with pytest.raises(UnsupportedFile):
        extract_text(path)


def test_docx_paragraphs_and_tables(tmp_path: Path):
    docx = pytest.importorskip("docx")

    path = tmp_path / "resume.docx"
    doc = docx.Document()
    doc.add_paragraph("Ada Lovelace")
    doc.add_paragraph("ada@example.com")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Analyst"
    table.rows[0].cells[1].text = "1842 - 1843"
    doc.save(path)

    out = extract_text(path)

    assert "Ada Lovelace" in out
    # Table-based layouts are common in resumes, so cells must survive.
    assert "Analyst | 1842 - 1843" in out


def test_pdf_text(tmp_path: Path):
    pymupdf = pytest.importorskip("pymupdf")

    path = tmp_path / "resume.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Ada Lovelace")
    page.insert_text((72, 96), "Analytical Engine Co")
    doc.save(path)
    doc.close()

    out = extract_text(path)

    assert "Ada Lovelace" in out
    assert "Analytical Engine Co" in out
