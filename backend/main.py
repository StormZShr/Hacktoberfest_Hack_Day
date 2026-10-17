"""FastAPI app: CORS for the Next.js dev server, routers, and /health.

Run from the backend/ directory:
    uvicorn main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

import config
from db import create_db_and_tables, engine
from routers import ai, auth as auth_router, orders, projects
from services import llm


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    config.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Launchpad API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(projects.router)
app.include_router(ai.router)
app.include_router(ai.projects_router)
app.include_router(orders.router)


@app.get("/health")
async def health() -> dict:
    """Is the DB reachable, and is the local model pulled?"""
    db_ok = True
    db_error: str | None = None
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - health must not raise
        db_ok = False
        db_error = exc.__class__.__name__

    ollama = await llm.health()
    healthy = db_ok and bool(ollama.get("reachable")) and bool(ollama.get("model_pulled"))

    return {
        "status": "ok" if healthy else "degraded",
        "db": {"ok": db_ok, "error": db_error},
        "ollama": ollama,
        "model": config.MODEL,
        "ollama_url": config.OLLAMA_URL,
        "payment_provider": config.PAYMENT_PROVIDER,
    }
