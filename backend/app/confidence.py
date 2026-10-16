"""Složené skóre jistoty (CLAUDE.md 5.6). Váhy a prahy jsou v backend/config/confidence.json."""
from .config import get_settings
from .models import ConfidenceComponents


def score(c: ConfidenceComponents, rules_passed: bool = True) -> float:
    cfg = get_settings().confidence
    w = cfg["weights"]
    s = (
        w["quote_verified"] * (1.0 if c.quote_verified else 0.0)
        + w["codelist_match"] * (c.codelist_match if c.codelist_match is not None else 0.0)
        + w["cross_doc_agreement"] * (c.cross_doc_agreement if c.cross_doc_agreement is not None else 0.0)
        + w["llm_self"] * (c.llm_self if c.llm_self is not None else cfg["default_llm_self"])
    )
    if not rules_passed:
        s -= cfg["rule_failed_penalty"]
    # Neověřená citace = nikdy auto-vyplnění (pravidlo 1): strop pod pásmem medium
    if not c.quote_verified:
        s = min(s, cfg["bands"]["medium"] - 0.01)
    return round(max(0.0, min(1.0, s)), 3)


def band(value: float | None) -> str | None:
    if value is None:
        return None
    b = get_settings().confidence["bands"]
    if value >= b["high"]:
        return "high"
    if value >= b["medium"]:
        return "medium"
    return "low"


def automation_level(band_: str | None, from_free_text: bool) -> str:
    level = get_settings().confidence["automation"][band_ or "missing"]
    # Kódy z volného textu nikdy úroveň A
    if from_free_text and level == "A":
        level = "B"
    return level
