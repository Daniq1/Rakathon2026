"""Kandidáti → Fact: ověření citace, kandidáti z číselníku, základní skóre (shodu mezi dokumenty doplní resolve)."""
import hashlib
import re

from .. import confidence
from ..codelists.loader import get_codelist
from ..config import get_settings
from ..models import CodelistCandidate, Confidence, ConfidenceComponents, Evidence, Fact
from .types import Candidate
from .verify import verify_quote

# Pohlaví z textu (pravidlo, ne LLM). „Pacient“ samo o sobě nic neříká (používá se pro oba).
_FEMALE = re.compile(r"\b(pacientka|poučena|přijata|propuštěna|menopau[sz]\w*|gravid\w*)\b", re.I)
_MALE = re.compile(r"\b(poučen|přijat|propuštěn)\b", re.I)


def sex_candidates(pages: list[str]) -> list[Candidate]:
    out = []
    for no, text in enumerate(pages, 1):
        for line in text.splitlines():
            q = line.strip()
            for pattern, code in ((_FEMALE, "F"), (_MALE, "M")):
                for m in pattern.finditer(line):
                    out.append(Candidate("pohlavi", m.group(0), code, q, no, method="rule", temporal="current"))
    return out


def codelist_match(cand: Candidate) -> tuple[float, list[CodelistCandidate] | None]:
    cfg = get_settings().confidence
    if cand.codelist is None:
        return 1.0, None  # pole bez číselníku (počty, datum)
    cl = get_codelist(cand.codelist)
    if cl is None:
        return cfg["codelist_missing_match"], None
    matches = cl.candidates(cand.value_code, cand.value_raw)
    cands = [CodelistCandidate(code=m.code, label=m.label, score=m.score) for m in matches]
    exact = next((m.score for m in matches if m.code == cand.value_code), 0.0)
    return exact, cands


def fact_id(doc_id: str, cand: Candidate, n: int) -> str:
    h = hashlib.sha1(f"{doc_id}|{cand.field}|{cand.value_code}|{cand.quote}|{n}".encode()).hexdigest()[:10]
    return f"f-{h}"


def build_facts(doc_id: str, pages: list[str], cands: list[Candidate]) -> list[Fact]:
    facts = []
    for n, c in enumerate(cands):
        located = verify_quote(pages, c.page, c.quote)
        page, start, end = located if located else (c.page, None, None)
        match, cl_cands = codelist_match(c)
        comps = ConfidenceComponents(
            quote_verified=located is not None,
            codelist_match=round(match, 3),
            cross_doc_agreement=0.5,  # přepočítá resolve podle ostatních dokumentů
            llm_self=c.llm_self if c.method == "llm" else 1.0,
        )
        facts.append(
            Fact(
                fact_id=fact_id(doc_id, c, n),
                field=c.field,
                value_raw=c.value_raw,
                value_code=c.value_code,
                codelist=c.codelist,
                codelist_candidates=cl_cands,
                assertion=c.assertion,
                temporal=c.temporal,
                evidence=[Evidence(doc_id=doc_id, page=page, char_start=start, char_end=end, quote=c.quote)],
                method=c.method,
                model=c.model,
                prompt_version=c.prompt_version,
                confidence=Confidence(score=confidence.score(comps), components=comps),
            )
        )
    return facts
