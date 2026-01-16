"""Утилиты для работы с PDF через PyMuPDF."""

from __future__ import annotations

import io
import logging

import fitz  # PyMuPDF

log = logging.getLogger(__name__)

# Ограничения
MAX_PDF_PAGES = 2
MAX_PDF_SIZE_MB = 10
MAX_PDF_SIZE_BYTES = MAX_PDF_SIZE_MB * 1024 * 1024


class PDFValidationError(Exception):
    """Ошибка валидации PDF."""
    pass


def validate_pdf(pdf_bytes: bytes) -> None:
    """
    Проверяет PDF на соответствие ограничениям.

    Raises:
        PDFValidationError: если PDF не соответствует ограничениям
    """
    if len(pdf_bytes) > MAX_PDF_SIZE_BYTES:
        size_mb = len(pdf_bytes) / (1024 * 1024)
        raise PDFValidationError(
            f"PDF слишком большой: {size_mb:.1f} MB (максимум {MAX_PDF_SIZE_MB} MB)"
        )

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = len(doc)
        doc.close()

        if page_count > MAX_PDF_PAGES:
            raise PDFValidationError(
                f"PDF содержит {page_count} страниц (максимум {MAX_PDF_PAGES}). "
                "Вероятно, это не один модуль."
            )
    except fitz.fitz.FileDataError as e:
        raise PDFValidationError(f"Невалидный PDF файл: {e}")


def pdf_to_images(pdf_bytes: bytes, dpi: int = 150) -> list[bytes]:
    """
    Конвертирует PDF в список изображений (PNG).

    Args:
        pdf_bytes: PDF файл в байтах
        dpi: Разрешение рендеринга (по умолчанию 150)

    Returns:
        Список PNG изображений в байтах
    """
    validate_pdf(pdf_bytes)

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []

    try:
        for page_num in range(min(len(doc), MAX_PDF_PAGES)):
            page = doc[page_num]

            # Рендерим страницу в изображение
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)

            # Конвертируем в PNG
            png_bytes = pix.tobytes("png")
            images.append(png_bytes)

            log.info(f"[PDF] Page {page_num + 1}: {pix.width}x{pix.height} px")
    finally:
        doc.close()

    return images
