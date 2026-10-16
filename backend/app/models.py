"""Pydantic v2 modely odpovídající schema/nor_case.schema.json (verze 0.1.0).

Psáno ručně (datamodel-code-generator zatím nejde nainstalovat na Python 3.15). Shodu se schématem
hlídá tests/test_schema.py: výstup API se validuje proti JSON Schema.
Pravidlo serializace: volitelná pole, která schéma nepovoluje jako null, se při None vynechají.
"""
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, model_serializer

SCHEMA_VERSION = "0.1.0"

NorFieldName = Literal[
    "dat_dg", "lateralita", "dg_stan", "dg_nov", "dg_nov_slovne", "topo", "morfo", "morfo_slovne",
    "morfo_metoda", "grade", "t", "n", "m", "ptnmy", "pt", "pn", "pvu", "ppu", "psu", "pm",
    "metastaze", "trofoblast", "serove_markery", "p16", "stadium", "rozsah", "pozn", "rodcis",
    "pohlavi", "dat_nar", "obec", "zeme", "cizinec", "bezdomovec", "hzz", "hodd", "htyp", "hdatum",
    "lekar", "idzz",
]
DocType = Literal[
    "ambulantni_zprava", "histologie", "propoustejici_zprava", "cytologie", "zobrazovaci", "jine", "nezname"
]
ExtractionMethod = Literal["text_layer", "ocr_tesseract", "ocr_azure_di", "llm_vision"]
Assertion = Literal["affirmed", "negated", "suspected", "historical", "unknown"]
Temporal = Literal["at_diagnosis", "pre_treatment", "post_neoadjuvant", "post_surgery", "current", "unknown"]
FactMethod = Literal["llm", "regex", "rule", "codelist_lookup", "manual"]
Band = Literal["high", "medium", "low"]
Level = Literal["A", "B", "C", "D", "E"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Volitelná pole, která ve schématu nesmí být null → při None vynechat
    _omit_if_none: ClassVar[frozenset[str]] = frozenset()

    @model_serializer(mode="wrap")
    def _drop_none(self, handler):
        data = handler(self)
        for key in self._omit_if_none:
            if data.get(key) is None:
                data.pop(key, None)
        return data


class Patient(Model):
    _omit_if_none = frozenset({"pseudonym"})
    patient_key: str
    rc_raw: str
    rc_valid: bool
    pseudonym: str | None = None


class PartialDate(Model):
    value: str | None = None
    precision: Literal["day", "month", "year", "unknown"]


class Page(Model):
    page: int = Field(ge=1)
    text: str


class Document(Model):
    _omit_if_none = frozenset({"doc_date", "mime", "ingested_at"})
    doc_id: str
    patient_key: str
    doc_type: DocType
    doc_date: PartialDate | None = None
    source_file: str
    mime: str | None = None
    sha256: str
    extraction_method: ExtractionMethod
    ocr_confidence: float | None = Field(default=None, ge=0, le=1)
    pages: list[Page]
    ingested_at: str | None = None


class Evidence(Model):
    doc_id: str
    page: int
    char_start: int | None = None
    char_end: int | None = None
    quote: str


class CodelistCandidate(Model):
    code: str
    label: str
    score: float


class ConfidenceComponents(Model):
    _omit_if_none = frozenset(
        {"llm_self", "quote_verified", "codelist_match", "cross_doc_agreement", "rules_passed"}
    )
    llm_self: float | None = None
    quote_verified: bool | None = None
    codelist_match: float | None = None
    cross_doc_agreement: float | None = None
    rules_passed: bool | None = None


class Confidence(Model):
    _omit_if_none = frozenset({"components"})
    score: float = Field(ge=0, le=1)
    components: ConfidenceComponents | None = None


class Fact(Model):
    _omit_if_none = frozenset({"codelist_candidates"})
    fact_id: str
    field: NorFieldName
    value_raw: str
    value_code: str | None = None
    codelist: str | None = None
    codelist_candidates: list[CodelistCandidate] | None = None
    assertion: Assertion
    temporal: Temporal
    evidence: list[Evidence] = Field(min_length=1)
    method: FactMethod
    model: str | None = None
    prompt_version: str | None = None
    confidence: Confidence


class FieldValue(Model):
    _omit_if_none = frozenset({"automation_level", "review"})
    value: str | int | bool | None
    label: str | None = None
    status: Literal["filled", "missing", "conflict", "not_applicable"]
    source: Literal["auto", "computed", "manual", "admin"]
    chosen_fact_id: str | None = None
    alternative_fact_ids: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    confidence_band: Band | None = None
    automation_level: Level | None = None
    review: Literal["pending", "confirmed", "edited", "rejected"] | None = "pending"
    reviewed_by: str | None = None
    reviewed_at: str | None = None


class Issue(Model):
    _omit_if_none = frozenset({"fact_ids"})
    code: str
    severity: Literal["error", "warning", "info"]
    fields: list[NorFieldName]
    message: str
    fact_ids: list[str] | None = None


class Metrics(Model):
    _omit_if_none = frozenset({"fields_total", "fields_auto", "fields_edited", "review_seconds"})
    fields_total: int | None = None
    fields_auto: int | None = None
    fields_edited: int | None = None
    review_seconds: float | None = None


class ExportInfo(Model):
    _omit_if_none = frozenset({"xml_file", "xsd_valid", "exported_at"})
    xml_file: str | None = None
    xsd_valid: bool | None = None
    exported_at: str | None = None


class NorCase(Model):
    _omit_if_none = frozenset({"metrics"})
    case_id: str
    patient_key: str
    status: Literal["draft", "in_review", "approved", "exported"]
    fields: dict[NorFieldName, FieldValue]
    issues: list[Issue]
    metrics: Metrics | None = None
    export: ExportInfo | None = None


class AuditEvent(Model):
    _omit_if_none = frozenset({"detail"})
    ts: str
    actor: str
    action: Literal["upload", "extract", "llm_call", "view", "edit", "confirm", "export"]
    field: str | None = None
    old: Any = None
    new: Any = None
    detail: str | None = None


class CaseBundle(Model):
    """Kořen schématu – to, co vrací GET /api/cases/{id}."""

    schema_version: Literal["0.1.0"] = SCHEMA_VERSION
    patient: Patient
    documents: list[Document]
    facts: list[Fact]
    case: NorCase
    audit: list[AuditEvent] = Field(default_factory=list)
