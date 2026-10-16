"""Pseudonymizace textu před odesláním do LLM (pravidlo 6).

Nahrazuje RČ, telefony, adresy, data narození a jméno v hlavičkových řádcích. Mapování
pseudonymů zůstává v backendu (tabulka patients); do LLM nejde RČ ani jméno.
"""
import re

from .rc import RC_PATTERN

_PHONE = re.compile(r"(?<!\d)(?:\+?420\s?)?\d{3}\s?\d{3}\s?\d{3}(?!\d)")
_ADDRESS = re.compile(r"(Adresa:)[^\n]*", re.I)
_BIRTH = re.compile(r"(Dat\.\s*nar\.:?)\s*\d{1,2}\.\s*\d{1,2}\.\s*\d{2,4}", re.I)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
# Jméno je v hlavičce před „r.č.“ nebo „Dat. nar.“ (např. „Jan Novák r.č. …“)
_NAME_BEFORE = re.compile(r"^(?P<name>[^\n]*?)(?P<marker>\s*-?\s*r\.\s?č\.|\s+Dat\.\s*nar\.)", re.I | re.M)


def pseudonymize(text: str, pseudonym: str) -> str:
    def name_sub(m: re.Match) -> str:
        name = m.group("name").strip()
        return (pseudonym if name else "") + m.group("marker")

    out = _NAME_BEFORE.sub(name_sub, text)
    out = _ADDRESS.sub(r"\1 [ADRESA]", out)
    out = _BIRTH.sub(r"\1 [DATUM_NAR]", out)
    out = _EMAIL.sub("[EMAIL]", out)
    out = RC_PATTERN.sub("[RC]", out)
    out = _PHONE.sub("[TEL]", out)
    return out
