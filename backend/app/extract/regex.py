"""Deterministické extraktory (CLAUDE.md 5.2/1): MKN-10, morfologie, TNM, mízní uzliny.

Citace = celý řádek se shodou (doslovně z textu stránky), offsety ukazují na ten řádek.
"""
import re
from collections.abc import Iterator

from .types import Candidate

_SUSPECT = re.compile(r"susp|suspektn|k\s+vyloučení|\bsuspicio|\?\s*$|nelze\s+vyloučit", re.I)

# MKN-10: C00–C97 a D00–D09 (in situ); ne CD163, CK20 apod.
_ICD = re.compile(r"(?<![A-Za-z0-9])(?P<code>C\d{2}|D0\d)\.?(?P<sub>\d)?(?![\d])")
# Morfologie MKN-O-3: M81403, M8140/3, 8140/3
_MORPHO = re.compile(r"(?<![A-Za-z0-9])(?:M(?P<a>\d{4})/?(?P<b>\d)|(?P<c>\d{4})/(?P<d>\d))(?![\d])")
_MORPHO_WORDS = re.compile(r"\s+(?P<words>[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ ,\-]{2,}?)(?=\s+[A-Z]:|\s*$)")
# TNM: volitelný prefix (c, p, yp, yc, r), T/N/M kategorie včetně písmen (4a, 3b)
_PFX = r"(?:yp|yc|p|c|r|y)"
_TNM = re.compile(
    rf"(?<![A-Za-z0-9])(?P<prefix>{_PFX})?T(?P<t>is|[0-4][a-d]?|[xX])(?![0-9])"
    rf"(?:\s*(?P<npfx>{_PFX})?N(?P<n>[0-3][a-c]?|[xX])(?![0-9]))?"
    rf"(?:\s*(?P<mpfx>{_PFX})?M(?P<m>[01][a-c]?|[xX])(?![0-9]))?"
)
_NODES = re.compile(
    r"(?:počet\s+a\s+stav\s+mízních\s+uzlin\s*:?|\bLU)\s*(?P<a>\d{1,3})\s*/\s*(?P<b>\d{1,3})(?!\d)", re.I
)


def _lines(text: str) -> Iterator[tuple[int, str]]:
    pos = 0
    for line in text.splitlines(keepends=True):
        yield pos, line.rstrip("\r\n")
        pos += len(line)


def _quote(line_start: int, line: str) -> tuple[str, int, int]:
    stripped = line.strip()
    start = line_start + line.index(stripped) if stripped else line_start
    return stripped, start, start + len(stripped)


def _assertion(line: str) -> str:
    if _SUSPECT.search(line):
        return "suspected"
    return "affirmed"


def extract_icd10(text: str, page: int) -> list[Candidate]:
    out = []
    for ls, line in _lines(text):
        for m in _ICD.finditer(line):
            code = m.group("code") + (m.group("sub") or "")
            q, s, e = _quote(ls, line)
            out.append(Candidate("dg_nov", m.group(0), code, q, page, s, e, _assertion(line),
                                 "at_diagnosis", codelist="MKN10_5"))
    return out


def extract_morphology(text: str, page: int, temporal: str) -> list[Candidate]:
    out = []
    for ls, line in _lines(text):
        for m in _MORPHO.finditer(line):
            code = (m.group("a") + m.group("b")) if m.group("a") else (m.group("c") + m.group("d"))
            q, s, e = _quote(ls, line)
            out.append(Candidate("morfo", m.group(0), code, q, page, s, e, _assertion(line), temporal,
                                 codelist="MKNO3Morfologie"))
            words = _MORPHO_WORDS.match(line, m.end())
            if words:
                name = words.group("words").strip(" ,-")
                out.append(Candidate("morfo_slovne", name, None, q, page, s, e, _assertion(line), temporal))
    return out


def _tnm_fields(prefix: str | None) -> tuple[tuple[str, str, str], str, bool] | None:
    """Prefix → (pole T, N, M), temporal, y."""
    p = (prefix or "").lower()
    if p == "yp":
        return ("pt", "pn", "pm"), "post_neoadjuvant", True
    if p == "p":
        return ("pt", "pn", "pm"), "post_surgery", False
    if p == "yc":
        return ("t", "n", "m"), "post_neoadjuvant", True
    if p == "c":
        return ("t", "n", "m"), "pre_treatment", False
    if p in ("", "y"):
        return ("t", "n", "m"), "unknown", p == "y"
    return None  # r = recidiva, do hlášení incidence nepatří


def extract_tnm(text: str, page: int) -> list[Candidate]:
    out = []
    for ls, line in _lines(text):
        for m in _TNM.finditer(line):
            # Holé „T3“ bez N/M a bez prefixu je příliš nejednoznačné (T jako topografie, teplota…)
            if not m.group("prefix") and not (m.group("n") or m.group("m")):
                continue
            q, s, e = _quote(ls, line)
            raw = m.group(0).strip()
            asrt = _assertion(line)
            # Každá složka může mít vlastní prefix („pT2 cN0M0“: T patologické, N a M klinické)
            parts = (("t", m.group("t"), m.group("prefix")),
                     ("n", m.group("n"), m.group("npfx") or m.group("prefix")),
                     ("m", m.group("m"), m.group("mpfx") or m.group("npfx") or m.group("prefix")))
            for idx, val, prefix in parts:
                mapped = _tnm_fields(prefix)
                if not val or not mapped:
                    continue
                names, temporal, y = mapped
                fld = names["tnm".index(idx)]
                out.append(Candidate(fld, raw, val.lower() if val in "xX" else val, q, page, s, e,
                                     asrt, temporal, codelist=f"TNM_{idx.upper()}"))
                if idx == "t" and fld == "pt":
                    out.append(Candidate("ptnmy", raw, "true" if y else "false", q, page, s, e, asrt, temporal,
                                         codelist="logical"))
    return out


def extract_nodes(text: str, page: int) -> list[Candidate]:
    out = []
    for ls, line in _lines(text):
        for m in _NODES.finditer(line):
            a, b = int(m.group("a")), int(m.group("b"))
            examined, positive = max(a, b), min(a, b)  # menší číslo = pozitivní
            q, s, e = _quote(ls, line)
            out.append(Candidate("pvu", m.group(0).strip(), str(examined), q, page, s, e, "affirmed", "post_surgery"))
            out.append(Candidate("ppu", m.group(0).strip(), str(positive), q, page, s, e, "affirmed", "post_surgery"))
    return out


_RESECTION = re.compile(r"resekát|resekce|ektomi|exstirpac", re.I)
_BIOPSY = re.compile(r"biops|excize|\bbiopt", re.I)


def histology_temporal(text: str) -> str:
    if _RESECTION.search(text):
        return "post_surgery"
    if _BIOPSY.search(text):
        return "pre_treatment"
    return "unknown"


def extract_all(pages: list[str], doc_type: str) -> list[Candidate]:
    full = "\n".join(pages)
    morpho_temporal = histology_temporal(full) if doc_type == "histologie" else "unknown"
    out: list[Candidate] = []
    for i, text in enumerate(pages, 1):
        out += extract_icd10(text, i)
        out += extract_morphology(text, i, morpho_temporal)
        out += extract_tnm(text, i)
        out += extract_nodes(text, i)
    # Stejný fakt (pole, hodnota, citace) na stránce jen jednou
    seen, unique = set(), []
    for c in out:
        k = (c.field, c.value_code, c.value_raw, c.page, c.char_start)
        if k not in seen:
            seen.add(k)
            unique.append(c)
    return unique
