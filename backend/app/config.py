"""Konfigurace z prostředí (.env v kořeni repa) a konfiguračních souborů v backend/config/."""
import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"

load_dotenv(REPO_ROOT / ".env")


def _path(env: str, default: Path) -> Path:
    value = os.environ.get(env)
    return Path(value) if value else default


@dataclass(frozen=True)
class Settings:
    app_mode: str
    database_url: str
    raw_dir: Path
    cache_dir: Path
    seed_cache_dir: Path
    codelist_dir: Path
    mkn10_dir: Path
    schema_path: Path
    llm_base_url: str | None
    llm_api_key: str | None
    llm_deployment_extract: str | None
    llm_max_concurrency: int
    confidence: dict = field(default_factory=dict)
    workplace: dict = field(default_factory=dict)

    @property
    def test_mode(self) -> bool:
        return self.app_mode == "test"

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_base_url and self.llm_api_key and self.llm_deployment_extract)


def _load_json(name: str) -> dict:
    return json.loads((CONFIG_DIR / name).read_text(encoding="utf-8"))


@lru_cache
def get_settings() -> Settings:
    data_dir = _path("DATA_DIR", REPO_ROOT / "data")
    return Settings(
        app_mode=os.environ.get("APP_MODE", "test"),
        database_url=os.environ.get("DATABASE_URL", f"sqlite:///{(data_dir / 'ainor.db').as_posix()}"),
        raw_dir=_path("RAW_DIR", data_dir / "raw"),
        cache_dir=_path("CACHE_DIR", data_dir / "cache"),
        # Cache pro demo pacienty v repu (jen čtení): demo běží bez jediného volání LLM
        seed_cache_dir=_path("SEED_CACHE_DIR", data_dir / "demo_cache"),
        codelist_dir=_path("CODELIST_DIR", data_dir / "codelists"),
        mkn10_dir=_path(
            "MKN10_DIR",
            data_dir / "mkn-10-strukturovane-podklady-20260101" / "mkn10_strukturovane_podklady_20260101" / "cp_utf8",
        ),
        schema_path=REPO_ROOT / "schema" / "nor_case.schema.json",
        llm_base_url=os.environ.get("LLM_BASE_URL") or None,
        llm_api_key=os.environ.get("LLM_API_KEY") or None,
        llm_deployment_extract=os.environ.get("LLM_DEPLOYMENT_EXTRACT") or None,
        llm_max_concurrency=int(os.environ.get("LLM_MAX_CONCURRENCY", "2")),
        confidence=_load_json("confidence.json"),
        workplace=_load_json("workplace.json"),
    )
