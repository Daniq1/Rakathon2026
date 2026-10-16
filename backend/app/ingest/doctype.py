"""Typ dokumentu z hlavičky."""
import re

# Pořadí je důležité: první shoda v hlavičce vyhrává
_RULES: list[tuple[str, re.Pattern]] = [
    ("propoustejici_zprava", re.compile(r"propouštěcí\s+zpráva", re.I)),
    ("ambulantni_zprava", re.compile(r"ambulantní\s+zpráva|amb\.\s*vyšetření|vstupní\s+onkologický\s+protokol", re.I)),
    ("histologie", re.compile(r"^\s*histologie\b|bioptického\s+materiálu|bioptick", re.I | re.M)),
    ("cytologie", re.compile(r"cytologi", re.I)),
    ("zobrazovaci", re.compile(r"^\s*(CT|MR|MRI|RTG|PET|USG|mamografie)\b", re.I | re.M)),
    ("jine", re.compile(r"\bMDT\b|konzili|protokol\s+MDT", re.I)),
]


def detect_doc_type(first_page: str, header_lines: int = 15) -> str:
    head = "\n".join(first_page.splitlines()[:header_lines])
    for doc_type, pattern in _RULES:
        if pattern.search(head):
            return doc_type
    return "nezname"
