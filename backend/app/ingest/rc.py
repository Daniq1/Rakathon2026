"""Rodné číslo: nalezení v hlavičce, normalizace a validace."""
import re
from dataclasses import dataclass, field
from datetime import date

# 123456/1111, 123456 / 1111, 1234561111
RC_PATTERN = re.compile(r"(?<!\d)(\d{6})\s*/?\s*(\d{3,4})(?!\d)")
RC_WITH_SLASH = re.compile(r"(?<!\d)(\d{6})\s*/\s*(\d{3,4})(?!\d)")


@dataclass
class RcInfo:
    raw: str
    key: str
    valid: bool
    sex: str | None = None  # "M" / "F" (jen pokud je RČ platné)
    birth_date: date | None = None
    errors: list[str] = field(default_factory=list)


def normalize(rc: str) -> str:
    return re.sub(r"\D", "", rc)


def validate(rc_raw: str) -> RcInfo:
    key = normalize(rc_raw)
    info = RcInfo(raw=rc_raw, key=key, valid=False)
    if len(key) not in (9, 10):
        info.errors.append("RČ musí mít 9 nebo 10 číslic")
        return info

    yy, mm, dd = int(key[0:2]), int(key[2:4]), int(key[4:6])
    sex = "M"
    if mm > 50:
        sex, mm = "F", mm - 50
    if mm > 20:  # od roku 2004 lze přičíst 20 (při vyčerpání koncovek)
        mm -= 20
    if len(key) == 9:
        year = 1900 + yy  # devítimístná RČ jen do roku 1953
        if year >= 1954:
            info.errors.append("Devítimístné RČ musí být z doby před rokem 1954")
    else:
        year = 2000 + yy if yy < 54 else 1900 + yy
    try:
        birth = date(year, mm, dd)
    except ValueError:
        info.errors.append("RČ neobsahuje platné datum narození")
        birth = None

    if len(key) == 10:
        num = int(key)
        # Historická výjimka: zbytek 10 → kontrolní číslice 0
        if num % 11 != 0 and not (int(key[:9]) % 11 == 10 and key[9] == "0"):
            info.errors.append("Desetimístné RČ není dělitelné 11")

    if not info.errors:
        info.valid, info.sex, info.birth_date = True, sex, birth
    return info


def find_rc(text: str, header_lines: int = 12) -> str | None:
    """RČ z hlavičky dokumentu (prvních pár řádků), ve tvaru s lomítkem."""
    head = "\n".join(text.splitlines()[:header_lines])
    m = RC_WITH_SLASH.search(head)
    return f"{m.group(1)}/{m.group(2)}" if m else None
