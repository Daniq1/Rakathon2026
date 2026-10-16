"""Řez 2 end-to-end: upload 3 PDF Pacienta 1 → GET /api/cases/{id} je validní vůči schématu.

LLM se nevolá: odpovědi jsou v data/demo_cache (klíč = text + prompt_version + model).
"""
import jsonschema
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def case(patient1_pdfs):
    with TestClient(app) as client:
        files = [("files", (p.name, p.read_bytes(), "application/pdf")) for p in patient1_pdfs]
        r = client.post("/api/documents?sync=true", files=files)
        assert r.status_code == 202, r.text
        docs = r.json()["documents"]
        assert [d["status"] for d in docs] == ["done"] * 3, docs
        assert all(d["message"] is None for d in docs), "LLM odpověď chybí v demo cache"

        patients = client.get("/api/patients").json()
        assert len(patients) == 1 and patients[0]["pseudonym"] == "Pacient 1"
        assert "1111" not in patients[0]["rc_masked"]

        bundle = client.get(f"/api/cases/{patients[0]['case_id']}").json()
        doc = client.get(f"/api/documents/{docs[0]['doc_id']}").json()
        assert doc["pages"][0]["text"]
        # Opakovaný upload stejného souboru se nezpracovává znovu
        again = client.post("/api/documents?sync=true", files=files[:1]).json()["documents"][0]
        assert again["duplicate"] is True
        return bundle


def test_case_valid_against_schema(case, schema):
    jsonschema.Draft202012Validator(schema).validate(case)


def test_fields(case):
    f = case["case"]["fields"]
    assert f["dg_nov"]["value"] == "C163" and f["dg_nov"]["label"] == "ZN – antrum pyloricum"
    assert f["topo"]["value"] == "C16.3" and f["topo"]["automation_level"] == "C"
    assert f["morfo"]["value"] == "81403"
    assert (f["t"]["value"], f["n"]["value"], f["m"]["value"]) == ("4a", "0", "0")
    assert (f["pt"]["value"], f["pn"]["value"], f["ptnmy"]["value"]) == ("3", "3b", True)
    assert (f["pvu"]["value"], f["ppu"]["value"]) == (24, 19)
    assert f["grade"]["value"] == "3" and f["grade"]["status"] == "conflict"
    assert f["dat_dg"]["value"] is None and f["dat_dg"]["chosen_fact_id"]


def test_issues(case):
    codes = {i["code"] for i in case["case"]["issues"]}
    assert {"CONFLICT_VALUE", "DATE_IMPRECISE", "SEX_CONFLICT", "RC_INVALID", "MISSING_REQUIRED"} <= codes
    rc = next(i for i in case["case"]["issues"] if i["code"] == "RC_INVALID")
    assert rc["severity"] == "info"


def test_every_fact_has_verified_quote(case):
    pages = {(d["doc_id"], p["page"]): p["text"] for d in case["documents"] for p in d["pages"]}
    for fact in case["facts"]:
        for ev in fact["evidence"]:
            assert fact["confidence"]["components"]["quote_verified"], fact
            assert pages[(ev["doc_id"], ev["page"])][ev["char_start"]:ev["char_end"]].split() == ev["quote"].split()


def test_llm_facts_have_prompt_version(case):
    llm = [f for f in case["facts"] if f["method"] == "llm"]
    assert {f["field"] for f in llm} == {"grade", "dat_dg"}
    assert all(f["prompt_version"] for f in llm)


def test_audit(case):
    actions = [a["action"] for a in case["audit"]]
    assert actions.count("upload") == 3 and "extract" in actions and "llm_call" in actions
