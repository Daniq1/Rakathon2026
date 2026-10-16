"""Rozhraní k LLM (CLAUDE.md 6). Poskytovatel je vyměnitelný: stačí implementovat LlmClient.

Cache: sha256(text + prompt_version + model) v data/cache/llm/ – demo pacienti jdou z cache bez volání.
Souběžnost max LLM_MAX_CONCURRENCY (výchozí 2), max_retries=2, bez smyček.
"""
import hashlib
import json
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ..config import get_settings

log = logging.getLogger(__name__)

# Model, kterým je vytvořená demo cache v data/demo_cache (klíč cache obsahuje název modelu)
DEMO_MODEL = "gpt-6-1-sol-dz-eu"


@dataclass
class LlmResult:
    data: dict
    raw: str
    model: str
    cache_key: str
    from_cache: bool


class LlmClient(Protocol):
    model: str

    def complete_json(self, system: str, user: str, prompt_version: str) -> LlmResult: ...


def cache_key(user: str, prompt_version: str, model: str) -> str:
    return hashlib.sha256(f"{prompt_version}\n{model}\n{user}".encode()).hexdigest()


class CachedClient:
    """Obálka nad libovolným klientem: čte/zapisuje JSON cache na disk."""

    def __init__(self, inner: "LlmClient | None", cache_dir: Path, model: str, seed_dirs: tuple[Path, ...] = ()):
        self.inner = inner
        self.cache_dir = cache_dir / "llm"
        self.seed_dirs = tuple(d / "llm" for d in seed_dirs)
        self.model = model

    def complete_json(self, system: str, user: str, prompt_version: str) -> LlmResult:
        key = cache_key(user, prompt_version, self.model)
        path = self.cache_dir / f"{key}.json"
        for candidate in (path, *(d / f"{key}.json" for d in self.seed_dirs)):
            if candidate.exists():
                raw = json.loads(candidate.read_text(encoding="utf-8"))["raw"]
                return LlmResult(json.loads(raw), raw, self.model, key, True)
        if self.inner is None:
            raise LlmUnavailable("LLM není nakonfigurované a odpověď není v cache")
        res = self.inner.complete_json(system, user, prompt_version)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"prompt_version": prompt_version, "model": self.model, "raw": res.raw}, ensure_ascii=False),
            encoding="utf-8",
        )
        return LlmResult(res.data, res.raw, self.model, key, False)


class LlmUnavailable(RuntimeError):
    pass


class OpenAICompatibleClient:
    """APIM endpoint kompatibilní s OpenAI (viz scripts/test_llm.py)."""

    def __init__(self, base_url: str, api_key: str, model: str, max_concurrency: int = 2):
        from openai import OpenAI

        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            default_headers={"api-key": api_key},  # APIM čeká klíč v hlavičce api-key
            max_retries=2,
            timeout=90,
        )
        self.model = model
        self._sem = threading.Semaphore(max_concurrency)
        self._temperature_supported = True

    def complete_json(self, system: str, user: str, prompt_version: str) -> LlmResult:
        from openai import BadRequestError

        kwargs = dict(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        with self._sem:
            try:
                r = self.client.chat.completions.create(
                    **kwargs, **({"temperature": 0} if self._temperature_supported else {})
                )
            except BadRequestError as exc:
                # Reasoning modely temperature nepodporují – jednou zkusit bez ní
                if "temperature" not in str(exc):
                    raise
                self._temperature_supported = False
                r = self.client.chat.completions.create(**kwargs)
        raw = r.choices[0].message.content or "{}"
        return LlmResult(json.loads(raw), raw, self.model, cache_key(user, prompt_version, self.model), False)


_default: CachedClient | None = None
_lock = threading.Lock()


def get_llm() -> CachedClient:
    global _default
    with _lock:
        if _default is None:
            s = get_settings()
            inner = (
                OpenAICompatibleClient(s.llm_base_url, s.llm_api_key, s.llm_deployment_extract, s.llm_max_concurrency)
                if s.llm_configured
                else None
            )
            # Bez konfigurace se použije název modelu, kterým byla vytvořena demo cache
            model = s.llm_deployment_extract or os.environ.get("LLM_DEMO_MODEL", DEMO_MODEL)
            _default = CachedClient(inner, s.cache_dir, model, (s.seed_cache_dir,))
        return _default


def set_llm(client: CachedClient | None) -> None:
    """Pro testy: podstrčit vlastního klienta."""
    global _default
    with _lock:
        _default = client
