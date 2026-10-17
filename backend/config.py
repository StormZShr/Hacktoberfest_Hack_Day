"""Environment configuration for Launchpad.

Every setting comes from an env var with a safe local default (see plan.md section 11).
Nothing here talks to the network; import it freely.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _env_int(name: str, default: int) -> int:
    """Read an int env var, failing loudly on a bad value."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from None


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"{name} must be a number, got {raw!r}") from None


# --- Local AI (Ollama). All model calls go through services/llm.py. ---
MODEL = os.getenv("LAUNCHPAD_MODEL", "gemma4:e2b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_CONTEXT_LENGTH = _env_int("OLLAMA_CONTEXT_LENGTH", 8192)
LLM_TIMEOUT_SECONDS = _env_float("LLM_TIMEOUT_SECONDS", 180.0)
KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "10m")
# READMEs are truncated to this many chars so they fit the context window.
README_MAX_CHARS = _env_int("README_MAX_CHARS", 6000)

# --- Auth ---
JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = _env_int("JWT_EXPIRE_MINUTES", 60 * 24 * 7)

# --- Storage ---
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", str(BASE_DIR / "storage")))
MAX_UPLOAD_MB = _env_int("MAX_UPLOAD_MB", 25)
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# --- Payments (mock by default; Razorpay test mode only) ---
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "mock").strip().lower()
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

# --- Database / HTTP ---
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'launchpad.db'}")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
