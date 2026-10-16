"""FastAPI aplikace: API na /api, sestavený frontend (frontend/dist) na /."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import cases, documents, patients
from .config import REPO_ROOT, get_settings
from .db.session import get_engine

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    get_engine()  # vytvoří tabulky
    yield


app = FastAPI(title="AI NOR", version="0.1.0", lifespan=lifespan)
app.include_router(patients.router)
app.include_router(documents.router)
app.include_router(cases.router)


@app.get("/api/health")
def health():
    s = get_settings()
    return {"ok": True, "app_mode": s.app_mode, "llm_configured": s.llm_configured}


_dist = REPO_ROOT / "frontend" / "dist"
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
