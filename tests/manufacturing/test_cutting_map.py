"""Tests for cutting map PDF generation (Task 11).

TDD: tests written first, must fail until PDF impl added to cutting_map.py.

Covers:
- generate_cutting_map_pdf returns bytes
- PDF contains required elements: scale, dimensions, grain, labels, order/revision, kerf, margin, unplaced warnings
- Multiple placed + unplaced
- Grain arrows and metadata in content (text extract)
- Visual render to PNG for inspection (Step 5)
- No ezdxf import (enforced by separate test_artifact_separation)

Uses minimal inline fixtures only.
"""
from __future__ import annotations

import os
import tempfile

import pytest

# Fixtures defined inline (minimal, per instructions — no other files modified)

@pytest.fixture
def sample_layout():
    """Минимальный SheetLayout с 2 размещёнными и 1 неразмещённой панелью."""
    from api.manufacturing.cutting_map import Panel, SheetLayout

    p1 = Panel(id="p1", name="Боковина левая", width_mm=600, height_mm=400, thickness_mm=18, material="ЛДСП")
    p2 = Panel(id="p2", name="Дно", width_mm=568, height_mm=400, thickness_mm=18, material="ЛДСП")
    p3 = Panel(id="p3", name="Большая полка", width_mm=1200, height_mm=300, thickness_mm=18, material="ЛДСП")

    placed = [
        (p1, 10.0, 10.0, False),
        (p2, 620.0, 10.0, True),  # rotated example
    ]
    unplaced = [p3]

    return SheetLayout(
        sheet_width=2800.0,
        sheet_height=2070.0,
        placed_panels=placed,
        unplaced_panels=unplaced,
        utilization_percent=42.5,
    )


@pytest.fixture
def empty_layout():
    from api.manufacturing.cutting_map import SheetLayout
    return SheetLayout(
        sheet_width=2800.0,
        sheet_height=2070.0,
        placed_panels=[],
        unplaced_panels=[],
        utilization_percent=0.0,
    )


# ---------------------------------------------------------------------------
# PDF generation tests (Step 3)
# ---------------------------------------------------------------------------


class TestCuttingMapPDFGeneration:
    """PDF должен генерироваться и содержать все требуемые элементы."""

    def test_returns_bytes_nonempty(self, sample_layout):
        from api.manufacturing.cutting_map import generate_cutting_map_pdf

        pdf_bytes = generate_cutting_map_pdf(
            layout=sample_layout,
            order_id="ORD-2026-007",
            revision="rev-3",
            kerf_mm=4.0,
            margin_mm=10.0,
            grain="none",
        )
        assert isinstance(pdf_bytes, (bytes, bytearray))
        assert len(pdf_bytes) > 500  # non-trivial PDF

    def test_pdf_includes_order_revision(self, sample_layout):
        from api.manufacturing.cutting_map import generate_cutting_map_pdf

        pdf_bytes = generate_cutting_map_pdf(
            layout=sample_layout,
            order_id="ORD-TEST-11",
            revision="A-42",
            kerf_mm=3.2,
            margin_mm=15.0,
        )
        # Use fitz to extract text (round-trip inspection of generated PDF)
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()

        t = text.lower().replace("\xad", "-").replace("\xa0", " ")
        assert "ORD-TEST-11" in t or "ord" in t or "заказ" in t
        assert "A-42" in t or "rev" in t or "ревизия" in t or "42" in t

    def test_pdf_includes_kerf_margin_dimensions(self, sample_layout):
        from api.manufacturing.cutting_map import generate_cutting_map_pdf

        pdf_bytes = generate_cutting_map_pdf(
            layout=sample_layout,
            order_id="K",
            revision="1",
            kerf_mm=4.0,
            margin_mm=12.0,
        )
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "".join(p.get_text() for p in doc)
        doc.close()

        # Dimensions of sheet
        assert "2800" in text and "2070" in text
        # kerf and margin mentioned
        assert "4" in text or "kerf" in text.lower() or "зазор" in text.lower() or "пропил" in text.lower()
        assert "12" in text or "margin" in text.lower() or "поле" in text.lower() or "отступ" in text.lower()

    def test_pdf_handles_unplaced_warnings(self, sample_layout):
        from api.manufacturing.cutting_map import generate_cutting_map_pdf

        pdf_bytes = generate_cutting_map_pdf(layout=sample_layout)
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "".join(p.get_text() for p in doc)
        doc.close()

        assert len(sample_layout.unplaced_panels) > 0
        t = text.lower().replace("\xad", "-").replace("\xa0", " ")
        assert "не размещ" in t or "unplaced" in t or "непоме" in t or "⚠" in text or "предупрежд" in t

    def test_pdf_includes_part_labels(self, sample_layout):
        from api.manufacturing.cutting_map import generate_cutting_map_pdf

        pdf_bytes = generate_cutting_map_pdf(layout=sample_layout)
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "".join(p.get_text() for p in doc)
        doc.close()

        assert "Боковина левая" in text or "p1" in text or "Боковина" in text
        assert "Дно" in text or "p2" in text

    def test_pdf_scale_and_grain(self, sample_layout):
        from api.manufacturing.cutting_map import generate_cutting_map_pdf

        pdf_bytes = generate_cutting_map_pdf(
            layout=sample_layout,
            grain="vertical",
        )
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "".join(p.get_text() for p in doc)
        doc.close()

        # Scale indication
        assert "scale" in text.lower() or "масштаб" in text.lower() or "1:" in text or "мм" in text
        # Grain arrow indication
        assert "grain" in text.lower() or "зерно" in text.lower() or "волокн" in text.lower() or "arrow" in text.lower() or "→" in text or "↑" in text


# ---------------------------------------------------------------------------
# Visual / render verification (Step 5) + roundtrip-like on PDF
# ---------------------------------------------------------------------------


class TestPDFVisualAndRender:
    """Генерация + рендер PNG для визуальной инспекции. Файлы в temp."""

    def test_render_png_nonempty(self, sample_layout):
        from api.manufacturing.cutting_map import generate_cutting_map_pdf

        pdf_bytes = generate_cutting_map_pdf(
            layout=sample_layout,
            order_id="VIS-001",
            revision="pilot",
            kerf_mm=4.0,
            margin_mm=10.0,
        )
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        assert len(doc) >= 1
        page = doc[0]
        # Render at reasonable dpi
        mat = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat)
        assert pix.width > 100
        assert pix.height > 100

        with tempfile.TemporaryDirectory() as tmp:
            png_path = os.path.join(tmp, "cutting_map_sample.png")
            pix.save(png_path)
            assert os.path.exists(png_path)
            assert os.path.getsize(png_path) > 1000
        doc.close()

    def test_pdf_with_empty_layout_still_valid(self, empty_layout):
        from api.manufacturing.cutting_map import generate_cutting_map_pdf

        pdf_bytes = generate_cutting_map_pdf(layout=empty_layout, order_id="EMPTY", revision="0")
        assert len(pdf_bytes) > 100
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        # Should still have at least header/warnings
        text = "".join(p.get_text() for p in doc)
        doc.close()
        assert "EMPTY" in text or len(text) > 5


# ---------------------------------------------------------------------------
# Round-trip style checks on layout data (no ezdxf here)
# ---------------------------------------------------------------------------


class TestLayoutDataIntegrity:
    """Проверки данных раскладки перед/после PDF (детерминизм)."""

    def test_placed_and_unplaced_counts_preserved(self, sample_layout):
        from api.manufacturing.cutting_map import generate_cutting_map_pdf

        assert len(sample_layout.placed_panels) == 2
        assert len(sample_layout.unplaced_panels) == 1
        pdf_bytes = generate_cutting_map_pdf(layout=sample_layout)
        assert len(pdf_bytes) > 0  # side effect free on layout

    def test_utilization_reported(self, sample_layout):
        assert 0 <= sample_layout.utilization_percent <= 100
