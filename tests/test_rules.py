"""Každé pravidlo: pozitivní a negativní případ."""
from app.ingest.rc import validate
from app.models import Confidence, ConfidenceComponents, Evidence, Fact, FieldValue
from app.rules import checks
from app.rules.checks import RuleContext


def fact(fid, field, code, raw="x", assertion="affirmed", temporal="unknown"):
    return Fact(
        fact_id=fid, field=field, value_raw=raw, value_code=code, assertion=assertion, temporal=temporal,
        evidence=[Evidence(doc_id="d", page=1, quote=raw)], method="regex",
        confidence=Confidence(score=0.9, components=ConfidenceComponents(quote_verified=True)),
    )


def fv(value, **kw):
    return FieldValue(value=value, status="filled" if value is not None else "missing", source="auto", **kw)


VALID_RC = validate("800101/0006")
INVALID_RC = validate("123456/1111")


def ctx(fields=None, facts=None, rc=VALID_RC, test_mode=True):
    return RuleContext(fields or {}, facts or [], rc, test_mode)


def test_missing_required():
    issues = checks.missing_required(ctx({"dg_nov": fv("C163")}))
    names = {i.fields[0] for i in issues}
    assert "dat_dg" in names and "dg_nov" not in names
    assert all(i.severity == "error" for i in issues)


def test_date_imprecise():
    f = fact("f1", "dat_dg", "2026-03", "3/26")
    assert checks.date_imprecise(ctx({"dat_dg": fv(None, chosen_fact_id="f1")}, [f]))[0].code == "DATE_IMPRECISE"
    g = fact("f2", "dat_dg", "2026-03-12", "12.3.26")
    assert checks.date_imprecise(ctx({"dat_dg": fv("2026-03-12", chosen_fact_id="f2")}, [g])) == []


def test_rc_invalid_info_in_test_mode_error_otherwise():
    assert checks.rc_invalid(ctx(rc=INVALID_RC))[0].severity == "info"
    assert checks.rc_invalid(ctx(rc=INVALID_RC, test_mode=False))[0].severity == "error"
    assert checks.rc_invalid(ctx(rc=VALID_RC)) == []


def test_sex_conflict():
    facts = [fact("a", "pohlavi", "M", "poučen"), fact("b", "pohlavi", "F", "pacientka")]
    assert checks.sex_conflict(ctx(facts=facts, rc=INVALID_RC))[0].code == "SEX_CONFLICT"
    assert checks.sex_conflict(ctx(facts=facts[1:], rc=INVALID_RC)) == []
    # RČ muže + text „pacientka“ → rozpor
    assert checks.sex_conflict(ctx(facts=facts[1:], rc=VALID_RC))


def test_codelist_missing():
    issues = checks.codelist_missing(ctx({"t": fv("4a"), "dg_nov": fv("C163")}))
    assert issues and issues[0].fields == ["t"]
    assert checks.codelist_missing(ctx({"dg_nov": fv("C163")})) == []


def test_diagnosis_suspected_only():
    sus = [fact("a", "dg_nov", "C504", assertion="suspected")]
    assert checks.diagnosis_suspected_only(ctx(facts=sus))[0].severity == "error"
    assert checks.diagnosis_suspected_only(ctx(facts=sus + [fact("b", "dg_nov", "C504")])) == []


def test_dgstan_inconsistent():
    assert checks.dgstan_inconsistent(ctx({"morfo_metoda": fv("H"), "dg_stan": fv(1)}))
    assert checks.dgstan_inconsistent(ctx({"morfo_metoda": fv("H"), "dg_stan": fv(17)})) == []
    assert checks.dgstan_inconsistent(ctx({"morfo_metoda": fv("H")})) == []
