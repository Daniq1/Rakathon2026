"""Orchestrace: upload → ingest → extrakce → resolve → pravidla → NorCase."""
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from . import confidence
from .config import get_settings
from .db import repo
from .db.tables import DocumentRow
from .extract.facts import build_facts, sex_candidates
from .extract.llm import extract_llm
from .extract.regex import extract_all
from .extract.types import Candidate
from .ingest.doctype import detect_doc_type
from .ingest.pdf import extract_pdf, extract_text_file
from .ingest.rc import RC_WITH_SLASH, find_rc, normalize, validate
from .llm.client import get_llm
from .models import AuditEvent, Document, FieldValue, Metrics, NorCase, Page
from .resolve.resolver import resolve_case
from .rules.checks import PENALIZING, RuleContext, run_rules

log = logging.getLogger(__name__)

NOR_FIELDS_TOTAL = 40


@dataclass
class Upload:
    filename: str
    content: bytes


@dataclass
class UploadResult:
    doc_id: str
    source_file: str
    status: str
    patient_key: str | None
    duplicate: bool
    message: str | None = None


def case_id_for(patient_key: str) -> str:
    # Neprůhledné ID – RČ nepatří do URL případu
    return "case-" + hashlib.sha256(patient_key.encode()).hexdigest()[:12]


# --- 1. ingest ------------------------------------------------------------

def ingest_files(s: Session, uploads: list[Upload], patient_key: str | None = None) -> list[UploadResult]:
    """Uloží originály, vytáhne text, určí typ a pacienta. Extrakci dělá process_documents."""
    settings = get_settings()
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    staged: list[tuple[DocumentRow, list[str], str, float | None, str | None]] = []
    results: list[UploadResult] = []

    for up in uploads:
        sha = hashlib.sha256(up.content).hexdigest()
        existing = repo.find_document_by_sha(s, sha)
        if existing:
            results.append(UploadResult(existing.doc_id, existing.source_file, existing.status,
                                        existing.patient_key, True, "Soubor už byl nahrán."))
            continue
        ext = Path(up.filename).suffix.lower() or ".bin"
        raw_path = settings.raw_dir / f"{sha}{ext}"
        raw_path.write_bytes(up.content)
        row = DocumentRow(doc_id=sha[:16], sha256=sha, source_file=up.filename, raw_path=str(raw_path),
                          status="processing")
        try:
            text = extract_text_file(up.content) if ext == ".txt" else extract_pdf(up.content)
        except Exception as exc:
            row.status, row.error = "error", f"Nelze přečíst soubor: {exc}"
            repo.save_document(s, row, None)
            results.append(UploadResult(row.doc_id, up.filename, row.status, None, False, row.error))
            continue
        rc_raw = find_rc(text.pages[0]) if text.pages else None
        staged.append((row, text.pages, text.method, text.ocr_confidence, rc_raw))

    # Přiřazení pacienta: zadaný klíč > RČ v hlavičce > jediné RČ v dávce
    batch_keys = {normalize(rc) for *_, rc in staged if rc}
    for row, pages, method, ocr_conf, rc_raw in staged:
        key = normalize(patient_key) if patient_key else (normalize(rc_raw) if rc_raw else None)
        if key is None and len(batch_keys) == 1:
            key = next(iter(batch_keys))
            rc_raw = next(rc for *_, rc in staged if rc and normalize(rc) == key)
        if key is None:
            row.status = "error"
            row.error = "Nelze přiřadit pacienta: RČ v hlavičce chybí a dávka neobsahuje jednoznačné RČ."
            repo.save_document(s, row, None)
            results.append(UploadResult(row.doc_id, row.source_file, row.status, None, False, row.error))
            continue
        if rc_raw is None:
            existing_patient = repo.get_patient(s, key)
            rc_raw = existing_patient.rc_raw if existing_patient else key
        info = validate(rc_raw)
        repo.ensure_patient(s, key, rc_raw, info.valid)
        doc = Document(
            doc_id=row.doc_id, patient_key=key, doc_type=detect_doc_type(pages[0] if pages else ""),
            source_file=row.source_file, mime="text/plain" if row.source_file.lower().endswith(".txt")
            else "application/pdf", sha256=row.sha256, extraction_method=method, ocr_confidence=ocr_conf,
            pages=[Page(page=i, text=t) for i, t in enumerate(pages, 1)], ingested_at=repo.now_iso(),
        )
        row.patient_key = key
        repo.save_document(s, row, doc)
        repo.add_audit(s, key, AuditEvent(ts=repo.now_iso(), actor="system", action="upload",
                                          detail=f"{row.source_file} ({doc.doc_type}, {len(pages)} str.)"))
        note = None if len(batch_keys) <= 1 else "Dávka obsahuje dokumenty více pacientů (různá RČ)."
        results.append(UploadResult(row.doc_id, row.source_file, row.status, key, False, note))
    s.commit()
    return results


# --- 2. extrakce ----------------------------------------------------------

def _rc_candidate(pages: list[str]) -> list[Candidate]:
    for line in (pages[0].splitlines()[:12] if pages else []):
        m = RC_WITH_SLASH.search(line)
        if m:
            return [Candidate("rodcis", m.group(0), normalize(m.group(0)), line.strip(), 1, temporal="current")]
    return []


def extract_document(s: Session, row: DocumentRow) -> None:
    doc = repo.document_model(row)
    patient = repo.get_patient(s, row.patient_key)
    pages = [p.text for p in doc.pages]
    cands = extract_all(pages, doc.doc_type) + sex_candidates(pages) + _rc_candidate(pages)

    def on_call(task, res):
        repo.add_llm_call(s, row.doc_id, task.prompt, res.model, res.cache_key, res.from_cache, res.raw)
        repo.add_audit(s, row.patient_key, AuditEvent(
            ts=repo.now_iso(), actor="system", action="llm_call", field=task.field,
            detail=f"{row.source_file}: {task.prompt}, {res.model}{' (cache)' if res.from_cache else ''}"))

    llm_cands, llm_errors = extract_llm(pages, patient.pseudonym or "Pacient", get_llm(), on_call)
    facts = build_facts(row.doc_id, pages, cands + llm_cands)
    repo.replace_document_facts(s, row.patient_key, row.doc_id, facts)
    row.status = "done"
    row.error = "; ".join(llm_errors) or None
    repo.add_audit(s, row.patient_key, AuditEvent(
        ts=repo.now_iso(), actor="system", action="extract",
        detail=f"{row.source_file}: {len(facts)} faktů" + (f"; LLM: {row.error}" if row.error else "")))


# --- 3. případ ------------------------------------------------------------

def _apply_penalties(fields: dict[str, FieldValue], issues) -> None:
    penalty = get_settings().confidence["rule_failed_penalty"]
    hit = {f for i in issues if i.code in PENALIZING for f in i.fields}
    for name in hit:
        fv = fields.get(name)
        if fv and fv.confidence is not None:
            fv.confidence = round(max(0.0, fv.confidence - penalty), 3)
            fv.confidence_band = confidence.band(fv.confidence)
            fv.automation_level = confidence.automation_level(fv.confidence_band, True)


def rebuild_case(s: Session, patient_key: str) -> NorCase:
    patient = repo.get_patient(s, patient_key)
    rows = repo.patient_documents(s, patient_key)
    documents = [repo.document_model(r) for r in rows]
    facts = repo.patient_facts(s, patient_key)
    rc = validate(patient.rc_raw)

    resolved = resolve_case(patient, rc, documents, facts)
    repo.update_facts(s, resolved.facts)  # cross_doc_agreement a skóre

    previous = repo.case_for_patient(s, patient_key)
    fields = resolved.fields
    if previous:
        # Ruční úpravy a potvrzení lékaře se při novém vytěžení nepřepisují (pravidlo 5)
        for name, fv in previous.fields.items():
            if fv.source == "manual" or (fv.review and fv.review != "pending"):
                fields[name] = fv

    issues = resolved.issues + run_rules(RuleContext(fields, facts, rc, get_settings().test_mode))
    _apply_penalties(fields, issues)
    case = NorCase(
        case_id=previous.case_id if previous else case_id_for(patient_key),
        patient_key=patient_key,
        status=previous.status if previous and previous.status != "exported" else "draft",
        fields=fields,
        issues=issues,
        metrics=Metrics(
            fields_total=NOR_FIELDS_TOTAL,
            fields_auto=sum(1 for f in fields.values() if f.source in ("auto", "computed") and f.value is not None),
            fields_edited=(previous.metrics.fields_edited if previous and previous.metrics else 0) or 0,
            review_seconds=(previous.metrics.review_seconds if previous and previous.metrics else 0) or 0,
        ),
        export=previous.export if previous else None,
    )
    repo.save_case(s, case)
    return case


def process_documents(s: Session, doc_ids: list[str]) -> None:
    """Extrakce nahraných dokumentů a přestavba případů dotčených pacientů."""
    patients: set[str] = set()
    for doc_id in doc_ids:
        row = repo.get_document_row(s, doc_id)
        if not row or row.status != "processing" or not row.patient_key:
            continue
        try:
            extract_document(s, row)
            patients.add(row.patient_key)
        except Exception as exc:
            log.exception("Extrakce selhala: %s", doc_id)
            row.status, row.error = "error", f"Extrakce selhala: {exc}"
        s.commit()
    for key in patients:
        rebuild_case(s, key)
        s.commit()
