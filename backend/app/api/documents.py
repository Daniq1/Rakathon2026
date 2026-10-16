from dataclasses import asdict

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..db import repo
from ..db.session import get_session, session_factory
from ..models import Document
from ..pipeline import Upload, ingest_files, process_documents

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_FILE_BYTES = 25 * 1024 * 1024
ALLOWED = (".pdf", ".txt")


def _process_in_background(doc_ids: list[str]) -> None:
    with session_factory()() as s:
        process_documents(s, doc_ids)


@router.post("", status_code=202)
async def upload_documents(
    background: BackgroundTasks,
    files: list[UploadFile] = File(...),
    patient_key: str | None = Form(None),
    sync: bool = False,
    s: Session = Depends(get_session),
):
    """Nahraje soubory (multipart, více najednou). Ingest proběhne hned, extrakce asynchronně
    (sync=true pro skripty a testy)."""
    uploads = []
    for f in files:
        name = f.filename or "soubor"
        if not name.lower().endswith(ALLOWED):
            raise HTTPException(415, f"Nepodporovaný typ souboru: {name} (povoleno: PDF, TXT)")
        content = await f.read()
        if len(content) > MAX_FILE_BYTES:
            raise HTTPException(413, f"Soubor {name} je větší než 25 MB")
        uploads.append(Upload(name, content))
    results = ingest_files(s, uploads, patient_key)
    todo = [r.doc_id for r in results if r.status == "processing"]
    if sync:
        process_documents(s, todo)
        for r in results:
            if r.doc_id in todo:
                row = repo.get_document_row(s, r.doc_id)
                r.status, r.message = row.status, row.error or r.message
    elif todo:
        background.add_task(_process_in_background, todo)
    return {"documents": [asdict(r) for r in results]}


@router.get("/{doc_id}", response_model=Document)
def get_document(doc_id: str, s: Session = Depends(get_session)):
    row = repo.get_document_row(s, doc_id)
    doc = repo.document_model(row) if row else None
    if not doc:
        raise HTTPException(404, "Dokument nenalezen")
    return doc
