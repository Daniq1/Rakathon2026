from app.ingest.rc import validate
from app.models import Patient
from app.resolve.resolver import Resolved, resolve_case, resolve_date, resolve_grade, resolve_tnm
from test_rules import fact


def test_grade_prefers_pretreatment_biopsy_over_gx():
    facts = [fact("bio", "grade", "3", "G3", temporal="pre_treatment"),
             fact("res", "grade", "9", "Gx", temporal="post_neoadjuvant")]
    r = Resolved()
    resolve_grade(r, facts)
    g = r.fields["grade"]
    assert g.value == "3" and g.status == "conflict" and g.alternative_fact_ids == ["res"]
    assert r.issues[0].code == "CONFLICT_VALUE"


def test_grade_gx_not_chosen_when_concrete_exists():
    facts = [fact("a", "grade", "9", "x", temporal="unknown"), fact("b", "grade", "2", "G2", temporal="unknown")]
    r = Resolved()
    resolve_grade(r, facts)
    assert r.fields["grade"].value == "2"


def test_clinical_tnm_ignores_post_neoadjuvant():
    facts = [fact("c", "t", "4a", "cT4a", temporal="pre_treatment"),
             fact("y", "t", "2", "ycT2", temporal="post_neoadjuvant"),
             fact("p", "pt", "3", "ypT3", temporal="post_neoadjuvant")]
    r = Resolved()
    resolve_tnm(r, facts)
    assert r.fields["t"].value == "4a" and r.fields["t"].status == "filled"
    assert r.fields["pt"].value == "3"


def test_dat_dg_partial_date_is_not_filled():
    r = Resolved()
    resolve_date(r, [fact("d", "dat_dg", "2026-03", "3/26 gastro+histo")])
    assert r.fields["dat_dg"].value is None and r.fields["dat_dg"].status == "missing"
    assert r.fields["dat_dg"].chosen_fact_id == "d"


def test_dat_dg_prefers_histology_then_earliest():
    r = Resolved()
    resolve_date(r, [fact("ct", "dat_dg", "2026-01-05", "5.1.26 CT"),
                     fact("h2", "dat_dg", "2026-02-20", "20.2.26 histologie"),
                     fact("h1", "dat_dg", "2026-02-10", "10.2.26 biopsie")])
    assert r.fields["dat_dg"].value == "2026-02-10"


def test_admin_fields_are_admin_source():
    p = Patient(patient_key="1234561111", rc_raw="123456/1111", rc_valid=False)
    r = resolve_case(p, validate(p.rc_raw), [], [])
    assert r.fields["hzz"].source == "admin" and r.fields["hdatum"].value
