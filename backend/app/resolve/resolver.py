"""Výběr hodnoty pro každé pole NOR z více faktů a odvozené výpočty (CLAUDE.md 5.4).

Nic se tiše nezahazuje: neshodné hodnoty → status conflict, ostatní fakty do alternative_fact_ids,
Issue CONFLICT_VALUE.
"""
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from .. import confidence
from ..codelists.loader import get_codelist, mkn10, mkn10_full_name
from ..config import get_settings
from ..ingest.rc import RcInfo
from ..models import Document, Fact, FieldValue, Issue, Patient

CLINICAL_TEMPORALS = ("pre_treatment", "at_diagnosis", "unknown")
PATHOLOGICAL_TEMPORALS = ("post_surgery", "post_neoadjuvant", "unknown")
ADMIN_FIELDS = ("hzz", "hodd", "htyp", "lekar", "idzz", "zeme")
FREE_TEXT_METHODS = ("llm", "regex", "rule")


@dataclass
class Resolved:
    fields: dict[str, FieldValue] = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)
    facts: list[Fact] = field(default_factory=list)


def _key(f: Fact) -> str:
    return f.value_code if f.value_code is not None else f.value_raw


def _docs_of(facts: list[Fact]) -> set[str]:
    return {e.doc_id for f in facts for e in f.evidence}


def apply_cross_doc(facts: list[Fact]) -> None:
    """cross_doc_agreement = podíl dokumentů zmiňujících pole, které uvádějí stejnou hodnotu.
    Jediný dokument = 0.5 (nic nepotvrzuje ani nevyvrací)."""
    by_field: dict[str, list[Fact]] = defaultdict(list)
    for f in facts:
        if f.assertion == "affirmed":
            by_field[f.field].append(f)
    for group in by_field.values():
        docs = _docs_of(group)
        for f in group:
            same = _docs_of([g for g in group if _key(g) == _key(f)])
            agreement = 0.5 if len(docs) < 2 else len(same) / len(docs)
            comps = f.confidence.components
            comps.cross_doc_agreement = round(agreement, 3)
            f.confidence.score = confidence.score(comps)


def _field_from(
    chosen: Fact,
    alternatives: list[Fact],
    value,
    label: str | None,
    status: str = "filled",
    source: str = "auto",
    penalty: float = 0.0,
) -> FieldValue:
    score = round(max(0.0, chosen.confidence.score - penalty), 3)
    b = confidence.band(score)
    return FieldValue(
        value=value,
        label=label,
        status=status,
        source=source,
        chosen_fact_id=chosen.fact_id,
        alternative_fact_ids=[a.fact_id for a in alternatives],
        confidence=score,
        confidence_band=b,
        automation_level=confidence.automation_level(b, chosen.method in FREE_TEXT_METHODS),
        review="pending",
    )


def missing(source: str = "auto", automation: str = "E") -> FieldValue:
    return FieldValue(value=None, status="missing", source=source, automation_level=automation, review="pending")


def _label(f: Fact) -> str | None:
    cl = get_codelist(f.codelist)
    e = cl.exact(f.value_code) if cl else None
    return e.label if e else None


def _pick(
    facts: list[Fact],
    name: str,
    prefer_temporal: tuple[str, ...] = (),
    allowed_temporal: tuple[str, ...] | None = None,
) -> tuple[Fact | None, list[Fact], bool]:
    """Vybere fakt: preferovaný temporal → nejvíc dokumentů se stejnou hodnotou → nejvyšší skóre.
    Vrací (zvolený, alternativy s jinou hodnotou, je_konflikt)."""
    group = [f for f in facts if f.field == name and f.assertion == "affirmed"]
    if allowed_temporal is not None:
        group = [f for f in group if f.temporal in allowed_temporal]
    if not group:
        return None, [], False
    support = {k: len(_docs_of([g for g in group if _key(g) == k])) for k in {_key(g) for g in group}}

    def rank(f: Fact):
        t = prefer_temporal.index(f.temporal) if f.temporal in prefer_temporal else len(prefer_temporal)
        return (t, -support[_key(f)], -f.confidence.score)

    group.sort(key=rank)
    chosen = group[0]
    others = [f for f in group if _key(f) != _key(chosen)]
    return chosen, others, bool(others)


def _conflict_issue(name: str, chosen: Fact, others: list[Fact], reason: str) -> Issue:
    vals = ", ".join(sorted({f"{o.value_raw!r}" for o in others}))
    return Issue(
        code="CONFLICT_VALUE",
        severity="warning",
        fields=[name],
        fact_ids=[chosen.fact_id] + [o.fact_id for o in others],
        message=f"Pole {name}: zvoleno {chosen.value_raw!r} ({reason}), jiné hodnoty v dokumentaci: {vals}. Potvrdit.",
    )


def resolve_simple(r: Resolved, facts: list[Fact], name: str, **kw) -> Fact | None:
    chosen, others, conflict = _pick(facts, name, **kw)
    if not chosen:
        return None
    value = chosen.value_code if chosen.value_code is not None else chosen.value_raw
    r.fields[name] = _field_from(
        chosen, others, value, _label(chosen), status="conflict" if conflict else "filled",
        penalty=get_settings().confidence["rule_failed_penalty"] if conflict else 0.0,
    )
    if conflict:
        r.issues.append(_conflict_issue(name, chosen, others, "nejvíce dokumentů / nejvyšší jistota"))
    return chosen


def resolve_grade(r: Resolved, facts: list[Fact]) -> None:
    # Preferuj předléčebnou biopsii, resekát po neoadjuvanci často uvádí Gx
    chosen, others, conflict = _pick(facts, "grade", prefer_temporal=("pre_treatment", "at_diagnosis"))
    if not chosen:
        return
    if chosen.value_code == "9":  # GX: radši jakýkoli konkrétní grade
        concrete = [o for o in others if o.value_code != "9"]
        if concrete:
            chosen, others = concrete[0], [o for o in others if o is not concrete[0]] + [chosen]
    penalty = get_settings().confidence["rule_failed_penalty"] if conflict else 0.0
    r.fields["grade"] = _field_from(chosen, others, chosen.value_code, _label(chosen),
                                    status="conflict" if conflict else "filled", penalty=penalty)
    if conflict:
        r.issues.append(_conflict_issue("grade", chosen, others,
                                        "předléčebná biopsie má přednost před resekátem po neoadjuvanci"))


def resolve_diagnosis(r: Resolved, facts: list[Fact], docs: dict[str, Document]) -> None:
    chosen = resolve_simple(r, facts, "dg_nov")
    if not chosen:
        return
    fv = r.fields["dg_nov"]
    entry = mkn10().exact(chosen.value_code)
    if entry is None:
        # Kód mimo číselník je chyba (pravidlo 2) – nevyplnit, jen nabídnout
        r.fields["dg_nov"] = missing(automation="D")
        r.fields["dg_nov"].chosen_fact_id = chosen.fact_id
        return
    full = mkn10_full_name(chosen.value_code)
    if full:
        r.fields["dg_nov_slovne"] = fv.model_copy(update={"value": full, "label": None, "source": "computed"})
    # Topografie MKN-O-3 pro C00–C80 odpovídá kódu MKN-10 (C16.3 → C16.3). Číselník MKN-O-3 zatím nemáme,
    # proto jen předvyplnit k potvrzení (úroveň C). Texty typu „T63 ZALUDEK“ nejsou MKN-O-3 a ignorují se.
    if re.fullmatch(r"C\d{3}", chosen.value_code) and int(chosen.value_code[1:3]) <= 80:
        topo = f"{chosen.value_code[:3]}.{chosen.value_code[3]}"
        cfg = get_settings().confidence
        cap = 1 - (1 - cfg["codelist_missing_match"]) * cfg["weights"]["codelist_match"]
        score = round(min(fv.confidence or 0, cap), 3)
        r.fields["topo"] = fv.model_copy(update={
            "value": topo, "label": entry.label, "source": "computed", "confidence": score,
            "confidence_band": confidence.band(score), "automation_level": "C",
        })


def resolve_morphology(r: Resolved, facts: list[Fact], docs: dict[str, Document]) -> None:
    chosen = resolve_simple(r, facts, "morfo")
    if not chosen:
        return
    names = [f for f in facts if f.field == "morfo_slovne"
             and f.evidence[0].doc_id == chosen.evidence[0].doc_id and f.evidence[0].page == chosen.evidence[0].page]
    if names:
        r.fields["morfo"].label = names[0].value_raw
        r.fields["morfo_slovne"] = _field_from(names[0], [], names[0].value_raw, None)
    doc = docs.get(chosen.evidence[0].doc_id)
    method = {"histologie": "H", "cytologie": "C"}.get(doc.doc_type if doc else "")
    if method:
        fv = r.fields["morfo"]
        r.fields["morfo_metoda"] = fv.model_copy(update={
            "value": method, "label": "histologie" if method == "H" else "cytologie", "source": "computed",
        })


def resolve_tnm(r: Resolved, facts: list[Fact]) -> None:
    # Klinické TNM při diagnóze (před léčbou), ne stav po neoadjuvanci (pravidlo 4)
    for name in ("t", "n", "m"):
        resolve_simple(r, facts, name, prefer_temporal=("pre_treatment", "at_diagnosis"),
                       allowed_temporal=CLINICAL_TEMPORALS)
    for name in ("pt", "pn", "pm"):
        resolve_simple(r, facts, name, prefer_temporal=("post_neoadjuvant", "post_surgery"),
                       allowed_temporal=PATHOLOGICAL_TEMPORALS)
    chosen = resolve_simple(r, facts, "ptnmy")
    if chosen:
        fv = r.fields["ptnmy"]
        fv.value, fv.source = chosen.value_code == "true", "computed"
    for name in ("pvu", "ppu"):
        chosen = resolve_simple(r, facts, name)
        if chosen:
            r.fields[name].value = int(chosen.value_code)


def _date_basis(f: Fact) -> int:
    q = f.evidence[0].quote.lower()
    if re.search(r"histo|biop", q):
        return 0
    if "cytolog" in q:
        return 1
    return 2


def resolve_date(r: Resolved, facts: list[Fact]) -> None:
    """Nejčasnější datum histologického, jinak cytologického, jinak klinického potvrzení."""
    group = [f for f in facts if f.field == "dat_dg" and f.assertion == "affirmed" and f.value_code]
    if not group:
        return
    group.sort(key=lambda f: (_date_basis(f), f.value_code, -f.confidence.score))
    chosen, others = group[0], group[1:]
    precise = len(chosen.value_code) == 10
    precision = "měsíc" if len(chosen.value_code) == 7 else "rok"
    label = None if precise else f"{chosen.value_raw} (přesnost: {precision})"
    fv = _field_from(chosen, others, chosen.value_code if precise else None, label,
                     status="filled" if precise else "missing")
    if not precise:
        fv.automation_level = "D"
    r.fields["dat_dg"] = fv


def resolve_patient(r: Resolved, facts: list[Fact], patient: Patient, rc: RcInfo) -> None:
    rc_fact = next((f for f in facts if f.field == "rodcis"), None)
    if rc_fact:
        r.fields["rodcis"] = _field_from(rc_fact, [], patient.rc_raw, None)
    if rc.valid and rc.birth_date:
        r.fields["dat_nar"] = FieldValue(value=rc.birth_date.isoformat(), status="filled", source="computed",
                                         chosen_fact_id=rc_fact.fact_id if rc_fact else None, confidence=1.0,
                                         confidence_band="high", automation_level="B")
    sex = [f for f in facts if f.field == "pohlavi"]
    if rc.valid and rc.sex:
        # Číselník Pohlavi zatím nemáme → kód nevyplňovat, jen popisek (CODELIST_MISSING)
        r.fields["pohlavi"] = FieldValue(value=None, label="žena" if rc.sex == "F" else "muž", status="missing",
                                         source="computed", automation_level="C")
    elif sex:
        counts = defaultdict(int)
        for f in sex:
            counts[f.value_code] += 1
        best = max(counts, key=counts.get)
        chosen = next(f for f in sex if f.value_code == best)
        others = [f for f in sex if f.value_code != best]
        fv = _field_from(chosen, others, None, "žena" if best == "F" else "muž",
                         status="conflict" if others else "missing", source="auto")
        fv.automation_level = "C" if not others else "D"
        r.fields["pohlavi"] = fv


def resolve_admin(r: Resolved) -> None:
    wp = get_settings().workplace
    for name in ADMIN_FIELDS:
        v = wp.get(name)
        r.fields[name] = (
            FieldValue(value=v, status="filled", source="admin", confidence=1.0, confidence_band="high",
                       automation_level="B")
            if v not in (None, "") else missing(source="admin")
        )
    r.fields["hdatum"] = FieldValue(value=date.today().isoformat(), status="filled", source="admin",
                                    confidence=1.0, confidence_band="high", automation_level="B")


def resolve_case(patient: Patient, rc: RcInfo, documents: list[Document], facts: list[Fact]) -> Resolved:
    r = Resolved(facts=facts)
    apply_cross_doc(facts)
    docs = {d.doc_id: d for d in documents}
    resolve_diagnosis(r, facts, docs)
    resolve_morphology(r, facts, docs)
    resolve_grade(r, facts)
    resolve_tnm(r, facts)
    resolve_date(r, facts)
    resolve_patient(r, facts, patient, rc)
    resolve_admin(r)
    return r
