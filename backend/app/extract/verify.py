"""Ověření citací (pravidlo 1): citace musí doslovně být v textu stránky.

Tolerance jen na bílé znaky (zalomení řádků z pdfplumber/OCR). Když LLM uvede špatnou stránku,
citace se hledá i na ostatních stránkách dokumentu a stránka se opraví.
"""
import re


def locate(text: str, quote: str) -> tuple[int, int] | None:
    if not quote:
        return None
    i = text.find(quote)
    if i >= 0:
        return i, i + len(quote)
    words = quote.split()
    if not words:
        return None
    m = re.search(r"\s+".join(re.escape(w) for w in words), text)
    return (m.start(), m.end()) if m else None


def verify_quote(pages: list[str], page: int, quote: str) -> tuple[int, int, int] | None:
    """(stránka, start, konec) v originálním textu, nebo None."""
    order = [page] + [p for p in range(1, len(pages) + 1) if p != page]
    for p in order:
        if 1 <= p <= len(pages):
            span = locate(pages[p - 1], quote)
            if span:
                return p, span[0], span[1]
    return None
