"""Text po stránkách: textová vrstva PDF (pdfplumber), prázdná stránka → OCR (Tesseract ces), je-li k dispozici."""
import io
import logging
from dataclasses import dataclass

import pdfplumber

log = logging.getLogger(__name__)


@dataclass
class ExtractedText:
    pages: list[str]
    method: str  # text_layer | ocr_tesseract
    ocr_confidence: float | None


def _ocr_page(page) -> tuple[str, float] | None:
    try:
        import pytesseract  # volitelná závislost
    except ImportError:
        return None
    try:
        image = page.to_image(resolution=300).original
        data = pytesseract.image_to_data(image, lang="ces", output_type=pytesseract.Output.DICT)
    except Exception as exc:  # Tesseract není v systému, chybí jazyk ces…
        log.warning("OCR selhalo: %s", exc)
        return None
    confs = [float(c) for c, w in zip(data["conf"], data["text"]) if w.strip() and float(c) >= 0]
    text = pytesseract.image_to_string(image, lang="ces")
    return text, (sum(confs) / len(confs) / 100) if confs else 0.0


def extract_pdf(content: bytes) -> ExtractedText:
    pages: list[str] = []
    ocr_confs: list[float] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if not text.strip():
                ocr = _ocr_page(page)
                if ocr:
                    text, conf = ocr
                    ocr_confs.append(conf)
            pages.append(text)
    if ocr_confs:
        return ExtractedText(pages, "ocr_tesseract", round(sum(ocr_confs) / len(ocr_confs), 3))
    return ExtractedText(pages, "text_layer", None)


def extract_text_file(content: bytes) -> ExtractedText:
    text = content.decode("utf-8", errors="replace")
    # Stránky oddělené form feed, jinak jedna stránka
    return ExtractedText(text.split("\f"), "text_layer", None)
