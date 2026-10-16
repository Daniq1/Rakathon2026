"""Načítání číselníků a hledání kandidátů (CLAUDE.md 5.3).

Pořadí: přesná shoda kódu → fuzzy shoda názvu (rapidfuzz) → abecední seznam novotvarů MKN-10.
Výsledek je vždy jen ze seznamu – kódy se nevymýšlejí (pravidlo 2).
"""
import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from rapidfuzz import fuzz, process

from ..config import get_settings


@dataclass(frozen=True)
class Entry:
    code: str
    label: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Match:
    code: str
    label: str
    score: float


class Codelist:
    def __init__(self, name: str, entries: list[Entry]):
        self.name = name
        self.entries = entries
        self.by_code = {e.code: e for e in entries}
        self._labels = [e.label for e in entries]

    def exact(self, code: str | None) -> Entry | None:
        return self.by_code.get(code) if code else None

    def candidates(self, value_code: str | None, text: str | None = None, limit: int = 5) -> list[Match]:
        exact = self.exact(value_code)
        if exact:
            return [Match(exact.code, exact.label, 1.0)]
        out: list[Match] = []
        if text:
            # Shoda s aliasem (např. „Gx“, „x“ u gradingu)
            norm = text.strip().lower()
            for e in self.entries:
                if any(norm == a.lower() for a in e.aliases):
                    return [Match(e.code, e.label, 1.0)]
            for label, score, idx in process.extract(text, self._labels, scorer=fuzz.WRatio, limit=limit):
                e = self.entries[idx]
                out.append(Match(e.code, e.label, round(score / 100, 3)))
        return out


def _read_semicolon_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


@lru_cache
def mkn10() -> Codelist:
    """MKN-10-CZ, jen platné položky (prázdné PlatnostDo). Kód bez tečky (C163)."""
    path = get_settings().mkn10_dir / "01_MKN10_5E_2026_utf8.csv"
    entries = [
        Entry(r["Kod"], r["Nazev"], (r["KodSTeckou"], r["NazevPlny"]))
        for r in _read_semicolon_csv(path)
        if not r["PlatnostDo"]
    ]
    return Codelist("MKN10_5", entries)


def mkn10_full_name(code: str) -> str | None:
    e = mkn10().exact(code)
    return e.aliases[1] if e and len(e.aliases) > 1 else None


@lru_cache
def neoplasm_index() -> list[tuple[str, str]]:
    """Abecední seznam novotvarů: (termín, kód zhoubného primárního novotvaru)."""
    path = get_settings().mkn10_dir / "07_MKN10_2026_Abecední seznam - novotvary_utf8.csv"
    rows = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter=";")
        next(reader, None)
        for r in reader:
            if len(r) > 2 and r[2]:
                rows.append((r[1].strip("– ").strip(), r[2].replace(".", "")))
    return rows


def neoplasm_index_candidates(term: str, limit: int = 5) -> list[Match]:
    rows = neoplasm_index()
    terms = [t for t, _ in rows]
    out = []
    for label, score, idx in process.extract(term, terms, scorer=fuzz.WRatio, limit=limit):
        code = rows[idx][1]
        if mkn10().exact(code):
            out.append(Match(code, label, round(score / 100, 3)))
    return out


@lru_cache
def grading() -> Codelist:
    path = get_settings().codelist_dir / "grading.csv"
    entries = [
        Entry(r["code"], r["label"], tuple(a for a in r["aliases"].split("|") if a))
        for r in _read_semicolon_csv(path)
    ]
    return Codelist("Grading", entries)


def get_codelist(name: str | None) -> Codelist | None:
    """Číselník podle názvu z x-nor-fields; None = zatím nemáme (→ CODELIST_MISSING)."""
    if name == "MKN10_5":
        return mkn10()
    if name == "Grading":
        return grading()
    return None
