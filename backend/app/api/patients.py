from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import repo
from ..db.session import get_session

router = APIRouter(prefix="/api/patients", tags=["patients"])


def mask_rc(rc: str) -> str:
    digits = "".join(ch for ch in rc if ch.isdigit())
    return f"{digits[:2]}****/****" if len(digits) >= 6 else "******"


class IssueCounts(BaseModel):
    error: int = 0
    warning: int = 0
    info: int = 0


class PatientSummary(BaseModel):
    patient_key: str
    pseudonym: str | None
    rc_masked: str
    rc_valid: bool
    documents: int
    documents_processing: int
    case_id: str | None
    case_status: str | None
    issues: IssueCounts
    avg_confidence: float | None


class DocumentInfo(BaseModel):
    doc_id: str
    source_file: str
    doc_type: str | None
    pages: int | None
    status: str
    error: str | None


@router.get("", response_model=list[PatientSummary])
def list_patients(s: Session = Depends(get_session)):
    out = []
    for p in repo.list_patients(s):
        docs = repo.patient_documents(s, p.patient_key, only_done=False)
        case = repo.case_for_patient(s, p.patient_key)
        counts = IssueCounts()
        scores: list[float] = []
        if case:
            for i in case.issues:
                setattr(counts, i.severity, getattr(counts, i.severity) + 1)
            scores = [f.confidence for f in case.fields.values() if f.confidence is not None and f.source != "admin"]
        out.append(PatientSummary(
            patient_key=p.patient_key, pseudonym=p.pseudonym, rc_masked=mask_rc(p.rc_raw), rc_valid=p.rc_valid,
            documents=sum(1 for d in docs if d.status == "done"),
            documents_processing=sum(1 for d in docs if d.status == "processing"),
            case_id=case.case_id if case else None, case_status=case.status if case else None, issues=counts,
            avg_confidence=round(sum(scores) / len(scores), 3) if scores else None,
        ))
    return out


@router.get("/{key}/documents", response_model=list[DocumentInfo])
def patient_documents(key: str, s: Session = Depends(get_session)):
    if not repo.get_patient(s, key):
        raise HTTPException(404, "Pacient nenalezen")
    out = []
    for row in repo.patient_documents(s, key, only_done=False):
        doc = repo.document_model(row)
        out.append(DocumentInfo(doc_id=row.doc_id, source_file=row.source_file,
                                doc_type=doc.doc_type if doc else None, pages=len(doc.pages) if doc else None,
                                status=row.status, error=row.error))
    return out
