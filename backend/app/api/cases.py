from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import repo
from ..db.session import get_session
from ..db.tables import CaseRow
from ..models import CaseBundle

router = APIRouter(prefix="/api/cases", tags=["cases"])


def load_bundle(s: Session, case_id: str) -> CaseBundle | None:
    row = s.get(CaseRow, case_id)
    if not row:
        return None
    case = repo.get_case(s, case_id)
    documents = [repo.document_model(r) for r in repo.patient_documents(s, row.patient_key)]
    return CaseBundle(
        patient=repo.get_patient(s, row.patient_key),
        documents=documents,
        facts=repo.patient_facts(s, row.patient_key),
        case=case,
        audit=repo.patient_audit(s, row.patient_key),
    )


@router.get("/{case_id}")
def get_case(case_id: str, s: Session = Depends(get_session)):
    """Celý případ ve formátu schema/nor_case.schema.json."""
    bundle = load_bundle(s, case_id)
    if not bundle:
        raise HTTPException(404, "Případ nenalezen")
    return bundle.model_dump(mode="json")
