"""Thin Ollama HTTP client.

No SDK, just httpx. Every function reports failure as a value (or an error
string) instead of raising, so a dead Ollama degrades into a skipped file
rather than a 500 response.
"""

from __future__ import annotations

import json
import os

import httpx

OLLAMA_HOST = os.environ.get("REPOPILOT_OLLAMA_HOST", "http://localhost:11434").rstrip("/")
MODEL = os.environ.get("REPOPILOT_MODEL", "qwen2.5-coder:7b")

CHAT_TIMEOUT = 180.0
HEALTH_TIMEOUT = 5.0

# Low temperature keeps findings repeatable; the larger context window lets a
# whole chunked file fit without silent truncation.
CHAT_OPTIONS = {"temperature": 0.1, "num_ctx": 8192}


def _post_chat(
    system: str,
    user: str,
    schema: dict | None = None,
    timeout: float = CHAT_TIMEOUT,
) -> tuple[str | None, str | None]:
    """POST /api/chat. Returns (content, None) or (None, error message)."""
    payload: dict = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": CHAT_OPTIONS,
    }
    if schema is not None:
        payload["format"] = schema

    try:
        response = httpx.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=timeout)
        response.raise_for_status()
    except httpx.ConnectError:
        return None, f"ollama unreachable at {OLLAMA_HOST}"
    except httpx.TimeoutException:
        return None, f"ollama timed out after {timeout:.0f}s"
    except httpx.HTTPStatusError as exc:
        return None, f"ollama returned HTTP {exc.response.status_code}"
    except httpx.HTTPError as exc:
        return None, f"ollama request failed ({type(exc).__name__})"

    try:
        content = (response.json().get("message") or {}).get("content") or ""
    except ValueError:
        return None, "ollama returned a non-JSON response body"

    if not content.strip():
        return None, "model returned empty content"
    return content, None


def chat_json(system: str, user: str, schema: dict) -> tuple[dict | None, str | None]:
    """Chat with a JSON schema constraint. Returns (object, None) or (None, error)."""
    content, error = _post_chat(system, user, schema=schema)
    if error:
        return None, error
    try:
        data = json.loads(content or "")
    except json.JSONDecodeError:
        return None, "model output was not valid JSON"
    if not isinstance(data, dict):
        return None, "model output was not a JSON object"
    return data, None


def health() -> dict:
    """Report whether Ollama answers and whether the configured model is pulled."""
    down = {"ollama_up": False, "model": MODEL, "model_pulled": False}
    try:
        response = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=HEALTH_TIMEOUT)
        response.raise_for_status()
        tags = response.json().get("models") or []
    except (httpx.HTTPError, ValueError):
        return down

    names: set[str] = set()
    for tag in tags:
        if not isinstance(tag, dict):
            continue
        for key in ("name", "model"):
            value = tag.get(key)
            if isinstance(value, str):
                names.add(value)

    pulled = MODEL in names or f"{MODEL}:latest" in names
    return {"ollama_up": True, "model": MODEL, "model_pulled": pulled}
