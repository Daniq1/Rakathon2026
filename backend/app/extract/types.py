from dataclasses import dataclass


@dataclass
class Candidate:
    """Kandidát faktu před sloučením do modelu Fact (citace je vždy z jedné stránky)."""

    field: str
    value_raw: str
    value_code: str | None
    quote: str
    page: int
    char_start: int | None = None
    char_end: int | None = None
    assertion: str = "affirmed"
    temporal: str = "unknown"
    method: str = "regex"
    codelist: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    llm_self: float | None = None
