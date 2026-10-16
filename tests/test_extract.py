from app.codelists.loader import grading
from app.extract.llm import TASKS, build_snippets, extract_llm
from app.extract.regex import extract_icd10, extract_morphology, extract_nodes, extract_tnm
from app.extract.verify import verify_quote
from app.llm.client import CachedClient, LlmResult


def fields(cands):
    return {(c.field, c.value_code, c.temporal) for c in cands}


def test_icd10_ignores_cd_markers():
    cands = extract_icd10("CD3, CD20, CD163 a CK20\nDiagnózy:\nC163 ZN - antrum pyloricum", 1)
    assert [c.value_code for c in cands] == ["C163"]
    assert cands[0].quote == "C163 ZN - antrum pyloricum"


def test_icd10_suspected():
    (c,) = extract_icd10("susp. C50.4 k vyloučení", 1)
    assert c.value_code == "C504" and c.assertion == "suspected"


def test_morphology_with_and_without_m():
    cands = extract_morphology("M1: M81403 ADENOKARCINOM G: P:1\nkód 8500/3\nvýkon 51023(1x)", 2, "post_surgery")
    codes = {c.value_code for c in cands if c.field == "morfo"}
    assert codes == {"81403", "85003"}
    assert any(c.field == "morfo_slovne" and c.value_raw == "ADENOKARCINOM" for c in cands)


def test_tnm_clinical_vs_pathological():
    f = fields(extract_tnm("Adenoca žaludku, cT4aN0M0\n10. pTNM: ypT3 ypN3b", 1))
    assert ("t", "4a", "pre_treatment") in f
    assert ("n", "0", "pre_treatment") in f and ("m", "0", "pre_treatment") in f
    assert ("pt", "3", "post_neoadjuvant") in f and ("pn", "3b", "post_neoadjuvant") in f
    assert ("ptnmy", "true", "post_neoadjuvant") in f


def test_tnm_mixed_prefixes():
    f = fields(extract_tnm("pT2 cN0M0", 1))
    assert ("pt", "2", "post_surgery") in f
    assert ("n", "0", "pre_treatment") in f and ("m", "0", "pre_treatment") in f
    assert ("ptnmy", "false", "post_surgery") in f
    assert not any(field in ("pn", "pm") for field, _, _ in f)


def test_tnm_ignores_topography_and_bare_t():
    assert extract_tnm("TOP: T63 ZALUDEK\nTeplota T3 dny", 1) == []


def test_nodes_smaller_is_positive():
    cands = extract_nodes("8. počet a stav mízních uzlin: 24/19\nH: ... LU 19/24", 1)
    assert {(c.field, c.value_code) for c in cands} == {("pvu", "24"), ("ppu", "19")}


def test_verify_quote_tolerates_whitespace_and_wrong_page():
    pages = ["první stránka", "stupeň diferenciace\nnádoru (grading): x"]
    assert verify_quote(pages, 1, "stupeň diferenciace nádoru (grading): x")[0] == 2
    assert verify_quote(pages, 1, "vymyšlená citace") is None


class FakeLlm(CachedClient):
    def __init__(self, response: dict):
        self.model = "fake"
        self.response = response

    def complete_json(self, system, user, prompt_version):
        import json

        return LlmResult(self.response, json.dumps(self.response), "fake", "k", False)


def test_llm_codes_only_from_codelist():
    resp = {"facts": [
        {"page": 1, "quote": "adenoCa G3", "value_raw": "G3", "value_code": "3", "temporal": "pre_treatment"},
        {"page": 1, "quote": "adenoCa G3", "value_raw": "G3", "value_code": "G3-vymysleny", "temporal": "x"},
    ]}
    cands, errors = extract_llm(["3/26 gastro+histo: adenoCa G3"], "Pacient 1", FakeLlm(resp))
    grades = [c for c in cands if c.field == "grade"]
    assert errors == []
    assert all(grading().exact(c.value_code) for c in grades)
    assert len([c for c in grades if c.value_code == "3"]) >= 1
    assert not any(c.value_code == "G3-vymysleny" for c in grades)


def test_snippets_only_relevant_lines_and_pseudonymized_input():
    grade_task = next(t for t in TASKS if t.field == "grade")
    page = "Pacient 1 r.č. [RC]\nhemoglobin 111\nstupeň diferenciace (grading): x"
    snip = build_snippets([page], grade_task.keywords, context=0)
    assert "grading" in snip and "hemoglobin" not in snip
