"""SQLAlchemy tabulky. Strukturovaná data (Document, Fact, NorCase) jsou v JSON textu –
jen standardní typy, aby šlo SQLite i IRIS bez kódu specifického pro DB."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class PatientRow(Base):
    __tablename__ = "patients"
    patient_key: Mapped[str] = mapped_column(String(32), primary_key=True)
    rc_raw: Mapped[str] = mapped_column(String(32))
    rc_valid: Mapped[bool] = mapped_column(Boolean)
    pseudonym: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DocumentRow(Base):
    __tablename__ = "documents"
    doc_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    patient_key: Mapped[str | None] = mapped_column(ForeignKey("patients.patient_key"), index=True, nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    source_file: Mapped[str] = mapped_column(String(512))
    raw_path: Mapped[str] = mapped_column(String(1024))
    # queued → processing → done | error
    status: Mapped[str] = mapped_column(String(16), default="queued")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON Document
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FactRow(Base):
    __tablename__ = "facts"
    fact_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    patient_key: Mapped[str] = mapped_column(ForeignKey("patients.patient_key"), index=True)
    doc_id: Mapped[str] = mapped_column(ForeignKey("documents.doc_id"), index=True)
    field: Mapped[str] = mapped_column(String(32))
    data: Mapped[str] = mapped_column(Text)  # JSON Fact


class CaseRow(Base):
    __tablename__ = "cases"
    case_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    patient_key: Mapped[str] = mapped_column(ForeignKey("patients.patient_key"), unique=True)
    data: Mapped[str] = mapped_column(Text)  # JSON NorCase
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AuditRow(Base):
    __tablename__ = "audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_key: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    data: Mapped[str] = mapped_column(Text)  # JSON AuditEvent


class LlmCallRow(Base):
    """Surová odpověď LLM ke každému volání (ladění, audit)."""

    __tablename__ = "llm_calls"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    cache_key: Mapped[str] = mapped_column(String(64))
    from_cache: Mapped[bool] = mapped_column(Boolean)
    response_raw: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
