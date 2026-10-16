"""Testy běží bez sítě a bez .env: dočasná DB a cache, LLM jen z demo cache (data/demo_cache)."""
import os
import tempfile
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="ainor-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["CACHE_DIR"] = str(_TMP / "cache")
os.environ["RAW_DIR"] = str(_TMP / "raw")
os.environ["APP_MODE"] = "test"
# Prázdné hodnoty přebijí .env (load_dotenv nepřepisuje existující proměnné) → žádné živé volání LLM
for var in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_DEPLOYMENT_EXTRACT"):
    os.environ[var] = ""

REPO = Path(__file__).resolve().parents[1]
PATIENTS = REPO / "data" / "Nor-pacienti_Anonymizace" / "Nor-pacienti"


@pytest.fixture(scope="session")
def schema() -> dict:
    import json

    return json.loads((REPO / "schema" / "nor_case.schema.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def patient1_pdfs() -> list[Path]:
    return sorted((PATIENTS / "pac.1_U").glob("*.pdf"))
