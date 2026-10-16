"""Repozitář: převod mezi řádky DB a Pydantic modely."""
import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import AuditEvent, Document, Fact, NorCase, Patient
from .tables import AuditRow, CaseRow, DocumentRow, FactRow, LlmCallRow, PatientRow


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _dump(model) -> str:
    return json.dumps(model.model_dump(mode="json"), ensure_ascii=False)


# --- pacienti ---------------------------------------------------------------

def get_patient(s: Session, key: str) -> Patient | None:
    row = s.get(PatientRow, key)
    return Patient(patient_key=row.patient_key, rc_raw=row.rc_raw, rc_valid=row.rc_valid,
                   pseudonym=row.pseudonym) if row else None


def ensure_patient(s: Session, key: str, rc_raw: str, rc_valid: bool) -> Patient:
    row = s.get(PatientRow, key)
    if row is None:
        n = (s.scalar(select(func.count()).select_from(PatientRow)) or 0) + 1
        row = PatientRow(patient_key=key, rc_raw=rc_raw, rc_valid=rc_valid, pseudonym=f"Pacient {n}")
        s.add(row)
        s.flush()
    return get_patient(s, key)


def list_patients(s: Session) -> list[Patient]:
    rows = s.scalars(select(PatientRow).order_by(PatientRow.created_at)).all()
    return [Patient(patient_key=r.patient_key, rc_raw=r.rc_raw, rc_valid=r.rc_valid, pseudonym=r.pseudonym)
            for r in rows]


# --- dokumenty --------------------------------------------------------------

def get_document_row(s: Session, doc_id: str) -> DocumentRow | None:
    return s.get(DocumentRow, doc_id)


def find_document_by_sha(s: Session, sha: str) -> DocumentRow | None:
    return s.scalar(select(DocumentRow).where(DocumentRow.sha256 == sha))


def document_model(row: DocumentRow) -> Document | None:
    return Document.model_validate(json.loads(row.data)) if row.data else None


def save_document(s: Session, row: DocumentRow, doc: Document | None) -> None:
    row.data = _dump(doc) if doc else None
    s.add(row)


def patient_documents(s: Session, key: str, only_done: bool = True) -> list[DocumentRow]:
    q = select(DocumentRow).where(DocumentRow.patient_key == key).order_by(DocumentRow.created_at)
    if only_done:
        q = q.where(DocumentRow.status == "done")
    return list(s.scalars(q).all())


# --- fakty ------------------------------------------------------------------

def replace_document_facts(s: Session, patient_key: str, doc_id: str, facts: list[Fact]) -> None:
    for row in s.scalars(select(FactRow).where(FactRow.doc_id == doc_id)).all():
        s.delete(row)
    s.flush()
    for f in facts:
        s.add(FactRow(fact_id=f.fact_id, patient_key=patient_key, doc_id=doc_id, field=f.field, data=_dump(f)))


def patient_facts(s: Session, key: str) -> list[Fact]:
    rows = s.scalars(select(FactRow).where(FactRow.patient_key == key)).all()
    return [Fact.model_validate(json.loads(r.data)) for r in rows]


def update_facts(s: Session, facts: list[Fact]) -> None:
    for f in facts:
        row = s.get(FactRow, f.fact_id)
        if row:
            row.data = _dump(f)


# --- případy ----------------------------------------------------------------

def get_case(s: Session, case_id: str) -> NorCase | None:
    row = s.get(CaseRow, case_id)
    return NorCase.model_validate(json.loads(row.data)) if row else None


def case_for_patient(s: Session, key: str) -> NorCase | None:
    row = s.scalar(select(CaseRow).where(CaseRow.patient_key == key))
    return NorCase.model_validate(json.loads(row.data)) if row else None


def save_case(s: Session, case: NorCase) -> None:
    row = s.get(CaseRow, case.case_id)
    if row is None:
        row = CaseRow(case_id=case.case_id, patient_key=case.patient_key, data=_dump(case))
        s.add(row)
    else:
        row.data = _dump(case)


# --- audit a LLM ------------------------------------------------------------

def add_audit(s: Session, patient_key: str | None, event: AuditEvent) -> None:
    s.add(AuditRow(patient_key=patient_key, data=_dump(event)))


def patient_audit(s: Session, key: str) -> list[AuditEvent]:
    rows = s.scalars(select(AuditRow).where(AuditRow.patient_key == key).order_by(AuditRow.id)).all()
    return [AuditEvent.model_validate(json.loads(r.data)) for r in rows]


def add_llm_call(s: Session, doc_id: str, prompt_version: str, model: str, cache_key: str,
                 from_cache: bool, raw: str) -> None:
    s.add(LlmCallRow(doc_id=doc_id, prompt_version=prompt_version, model=model, cache_key=cache_key,
                     from_cache=from_cache, response_raw=raw))
