"""LLM extraktor pro to, co regex nezvládne (řez 2: grade, dat_dg).

Do LLM jde jen pseudonymizovaný relevantní úsek (řádky s klíčovými slovy ± kontext), ne celý dokument.
Odpověď se validuje: kód jen z číselníku (pravidlo 2), datum jen v ISO tvaru; ostatní se zahodí.
"""
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from ..codelists.loader import grading
from ..ingest.pseudonymize import pseudonymize
from ..llm.client import CachedClient, LlmResult, LlmUnavailable
from .types import Candidate

log = logging.getLogger(__name__)

PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"

_ASSERTIONS = {"affirmed", "negated", "suspected", "historical", "unknown"}
_TEMPORALS = {"at_diagnosis", "pre_treatment", "post_neoadjuvant", "post_surgery", "current", "unknown"}
_ISO = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


@dataclass(frozen=True)
class Task:
    field: str
    prompt: str  # název souboru bez .md, např. grade_v1
    keywords: re.Pattern
    codelist: str | None


TASKS = [
    Task(
        "grade",
        "grade_v1",
        re.compile(r"grad|diferenc|(?<![A-Za-z])G\s?[1-4xX](?![0-9a-z])|low.grade|high.grade", re.I),
        "Grading",
    ),
    Task(
        "dat_dg",
        "dat_dg_v1",
        re.compile(
            r"(\b\d{1,2}\.\s?\d{1,2}\.\s?\d{2,4}\b|\b\d{1,2}/\d{2,4}\b|\b20\d{2}\b)"
            r".*(histo|biop|cytolog|gastro|kolono|bronchoskop|dg|diagnó|CT|MR|PET|USG|mamograf|odběr)"
            r"|(histo|biop|cytolog|gastro|diagnó).*(\b\d{1,2}\.\s?\d{1,2}\.\s?\d{2,4}\b|\b\d{1,2}/\d{2,4}\b)",
            re.I,
        ),
        None,
    ),
]


def load_prompt(name: str) -> str:
    return (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")


def build_snippets(pages: list[str], keywords: re.Pattern, context: int = 1, max_chars: int = 3000) -> str:
    """Řádky se shodou ± kontext, po stránkách. Prázdný řetězec = není co posílat."""
    parts: list[str] = []
    for no, text in enumerate(pages, 1):
        lines = text.splitlines()
        keep: set[int] = set()
        for i, line in enumerate(lines):
            if keywords.search(line):
                keep.update(range(max(0, i - context), min(len(lines), i + context + 1)))
        if keep:
            parts.append(f"[strana {no}]\n" + "\n".join(lines[i] for i in sorted(keep)))
    return "\n\n".join(parts)[:max_chars]


def _system_prompt(task: Task) -> str:
    text = load_prompt(task.prompt)
    if task.codelist == "Grading":
        codes = "\n".join(f"{e.code} = {e.label}" for e in grading().entries)
        text = text.replace("{codes}", codes)
    return text


def _validate(task: Task, item: dict) -> Candidate | None:
    quote = str(item.get("quote") or "").strip()
    value_raw = str(item.get("value_raw") or "").strip()
    code = item.get("value_code")
    code = str(code).strip() if code is not None else None
    if not quote or not value_raw:
        return None
    if task.codelist == "Grading":
        if not grading().exact(code):
            log.warning("LLM vrátilo kód gradingu mimo číselník: %r", code)
            return None
    if task.field == "dat_dg" and not (code and _ISO.match(code)):
        return None
    try:
        page = int(item.get("page") or 1)
    except (TypeError, ValueError):
        page = 1
    conf = item.get("confidence")
    return Candidate(
        field=task.field,
        value_raw=value_raw,
        value_code=code,
        quote=quote,
        page=page,
        assertion=item.get("assertion") if item.get("assertion") in _ASSERTIONS else "unknown",
        temporal=item.get("temporal") if item.get("temporal") in _TEMPORALS else "unknown",
        method="llm",
        codelist=task.codelist,
        prompt_version=task.prompt,
        llm_self=float(conf) if isinstance(conf, (int, float)) else None,
    )


def extract_llm(
    pages: list[str], pseudonym: str, llm: CachedClient, on_call=None
) -> tuple[list[Candidate], list[str]]:
    """Vrací kandidáty a seznam chyb (LLM nedostupné apod. – zpracování nezastaví)."""
    out: list[Candidate] = []
    errors: list[str] = []
    safe_pages = [pseudonymize(p, pseudonym) for p in pages]
    for task in TASKS:
        snippet = build_snippets(safe_pages, task.keywords)
        if not snippet:
            continue
        try:
            res: LlmResult = llm.complete_json(_system_prompt(task), snippet, task.prompt)
        except LlmUnavailable as exc:
            errors.append(f"{task.field}: {exc}")
            continue
        except Exception as exc:  # síť, 429, nevalidní JSON – nezastavovat zbytek
            log.exception("LLM volání selhalo")
            errors.append(f"{task.field}: {type(exc).__name__}: {exc}")
            continue
        if on_call:
            on_call(task, res)
        for item in res.data.get("facts") or []:
            if isinstance(item, dict):
                cand = _validate(task, item)
                if cand:
                    cand.model = res.model
                    out.append(cand)
    return out, errors
