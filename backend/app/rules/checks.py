"""Kontroly případu → Issue (CLAUDE.md 5.5). Každé pravidlo je samostatná funkce s unit testem.

Zatím chybí (potřebují číselníky/tabulky, které nemáme): TNM_STAGE_MISMATCH, TOPO_MORPHO_INCOMPATIBLE,
DATE_ORDER (léčba se zatím nevytěžuje).
"""
import json
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache

from ..codelists.loader import get_codelist
from ..config import get_settings
from ..ingest.rc import RcInfo
from ..models import Fact, FieldValue, Issue


@dataclass
class RuleContext:
    fields: dict[str, FieldValue]
    facts: list[Fact]
    rc: RcInfo
    test_mode: bool


@lru_cache
def nor_field_meta() -> dict[str, dict]:
    schema = json.loads(get_settings().schema_path.read_text(encoding="utf-8"))
    return schema["$defs"]["NorFieldName"]["x-nor-fields"]


def _is_missing(fv: FieldValue | None) -> bool:
    return fv is None or fv.value is None or fv.value == ""


def missing_required(ctx: RuleContext) -> list[Issue]:
    out = []
    for name, meta in nor_field_meta().items():
        if meta["required_in_xsd"] and _is_missing(ctx.fields.get(name)):
            out.append(Issue(code="MISSING_REQUIRED", severity="error", fields=[name],
                             message=f"Povinné pole {name} nemá hodnotu – doplnit ručně nebo z dokumentace."))
    return out


def date_imprecise(ctx: RuleContext) -> list[Issue]:
    fv = ctx.fields.get("dat_dg")
    if not fv or not fv.chosen_fact_id:
        return []
    fact = next((f for f in ctx.facts if f.fact_id == fv.chosen_fact_id), None)
    if not fact or not fact.value_code or len(fact.value_code) == 10:
        return []
    precision = "měsíc" if len(fact.value_code) == 7 else "rok"
    return [Issue(code="DATE_IMPRECISE", severity="error", fields=["dat_dg"], fact_ids=[fact.fact_id],
                  message=f"Datum diagnózy známo jen na {precision} ({fact.value_raw!r} → {fact.value_code}); "
                          "XSD vyžaduje celé datum, doplnit den.")]


def rc_invalid(ctx: RuleContext) -> list[Issue]:
    if ctx.rc.valid:
        return []
    severity = "info" if ctx.test_mode else "error"
    reason = "; ".join(ctx.rc.errors)
    suffix = " (APP_MODE=test, anonymizovaná data)" if ctx.test_mode else ""
    return [Issue(code="RC_INVALID", severity=severity, fields=["rodcis"],
                  message=f"RČ {ctx.rc.raw} neprošlo kontrolou: {reason}{suffix}.")]


def sex_conflict(ctx: RuleContext) -> list[Issue]:
    sex = [f for f in ctx.facts if f.field == "pohlavi"]
    values = {f.value_code for f in sex}
    if ctx.rc.valid and ctx.rc.sex:
        values.add(ctx.rc.sex)
    if len(values) < 2:
        return []
    def words(code: str) -> str:
        return ", ".join(sorted({repr(f.value_raw) for f in sex if f.value_code == code})) or "RČ"
    return [Issue(code="SEX_CONFLICT", severity="warning", fields=["pohlavi"], fact_ids=[f.fact_id for f in sex],
                  message=f"Rozpor v pohlaví: muž ({words('M')}) vs. žena ({words('F')}).")]


def codelist_missing(ctx: RuleContext) -> list[Issue]:
    """Pole má (nebo by mělo mít) kód, ale číselník NOR pro ně zatím nemáme."""
    meta = nor_field_meta()
    fields = []
    for name, fv in ctx.fields.items():
        cl = meta.get(name, {}).get("codelist")
        if not cl or cl == "logical" or fv.source == "admin":
            continue
        if get_codelist(cl) is None and (not _is_missing(fv) or fv.label):
            fields.append(name)
    if not fields:
        return []
    return [Issue(code="CODELIST_MISSING", severity="info", fields=sorted(fields),
                  message="Číselník NOR pro tato pole zatím není k dispozici; hodnoty nejsou ověřené proti "
                          "číselníku: " + ", ".join(sorted(fields)) + ".")]


def diagnosis_suspected_only(ctx: RuleContext) -> list[Issue]:
    dg = [f for f in ctx.facts if f.field == "dg_nov"]
    if dg and not any(f.assertion == "affirmed" for f in dg):
        return [Issue(code="DIAGNOSIS_SUSPECTED_ONLY", severity="error", fields=["dg_nov"],
                      fact_ids=[f.fact_id for f in dg],
                      message="Diagnóza je v dokumentaci jen jako suspektní / k vyloučení – není to potvrzená dg.")]
    return []


def dgstan_inconsistent(ctx: RuleContext) -> list[Issue]:
    metoda, dgstan = ctx.fields.get("morfo_metoda"), ctx.fields.get("dg_stan")
    if not metoda or metoda.value != "H" or _is_missing(dgstan):
        return []
    try:
        has_histology = int(dgstan.value) & 16
    except (TypeError, ValueError):
        return []
    if has_histology:
        return []
    return [Issue(code="DGSTAN_INCONSISTENT", severity="warning", fields=["dg_stan", "morfo_metoda"],
                  message="Morfologie je z histologie (H), ale „K dg. vedla vyšetření“ neobsahuje 16 "
                          "(histologie primárního nádoru).")]


RULES: list[Callable[[RuleContext], list[Issue]]] = [
    missing_required,
    date_imprecise,
    rc_invalid,
    sex_conflict,
    codelist_missing,
    diagnosis_suspected_only,
    dgstan_inconsistent,
]

# Pravidla, jejichž porušení snižuje jistotu dotčených polí (−rule_failed_penalty)
PENALIZING = {"SEX_CONFLICT", "DIAGNOSIS_SUSPECTED_ONLY", "DGSTAN_INCONSISTENT"}


def run_rules(ctx: RuleContext) -> list[Issue]:
    issues: list[Issue] = []
    for rule in RULES:
        issues += rule(ctx)
    return issues
