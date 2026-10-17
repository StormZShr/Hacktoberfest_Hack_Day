"""The only place that talks to Ollama.

`structured()` sends a JSON schema to the local model, validates the reply with
Pydantic, retries once, then fails loudly. No external AI API is ever called.
"""

import json
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

import config

T = TypeVar("T", bound=BaseModel)

# Temperature per plan.md section 3: cold for extraction and review, warmer for Q&A.
TEMPERATURE_EXTRACT = 0.1
TEMPERATURE_QA = 0.3


class LLMError(RuntimeError):
    """The local model could not produce usable output."""


def truncate(text: str, limit: int = config.README_MAX_CHARS) -> str:
    """Keep input inside the context window."""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"


def _extract_json(raw: str) -> str:
    """Be forgiving about fences or stray prose around the JSON object."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
        text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text


async def _chat(system: str, user: str, schema: dict[str, Any], temperature: float) -> str:
    """One raw call to Ollama's /api/chat with a JSON-schema `format`."""
    payload = {
        "model": config.MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "format": schema,
        "stream": False,
        "keep_alive": config.KEEP_ALIVE,
        "options": {
            "temperature": temperature,
            "num_ctx": config.OLLAMA_CONTEXT_LENGTH,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=config.LLM_TIMEOUT_SECONDS) as client:
            response = await client.post(f"{config.OLLAMA_URL}/api/chat", json=payload)
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        raise LLMError(
            f"could not reach the local model at {config.OLLAMA_URL} ({exc.__class__.__name__})"
        ) from exc
    except ValueError as exc:
        raise LLMError("the local model returned a non-JSON response") from exc

    content = body.get("message", {}).get("content", "")
    if not content.strip():
        raise LLMError("the local model returned an empty reply")
    return content


async def structured(
    schema_model: type[T],
    *,
    system: str,
    user: str,
    temperature: float = TEMPERATURE_EXTRACT,
    attempts: int = 2,
) -> T:
    """Ask the model for `schema_model`, validated by Pydantic. One retry, then error."""
    schema = schema_model.model_json_schema()
    prompt = user
    last_error: str = "no attempt made"

    for _ in range(max(1, attempts)):
        raw = await _chat(system, prompt, schema, temperature)
        try:
            return schema_model.model_validate_json(_extract_json(raw))
        except (ValidationError, ValueError) as exc:
            last_error = str(exc).splitlines()[0]
            prompt = (
                f"{user}\n\n"
                f"Your previous reply was rejected: {last_error}\n"
                f"Reply again with JSON that matches the schema exactly."
            )

    raise LLMError(f"{config.MODEL} did not return valid {schema_model.__name__} JSON: {last_error}")


async def health() -> dict[str, Any]:
    """Small probe for GET /health. Never raises."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{config.OLLAMA_URL}/api/tags")
            response.raise_for_status()
            names = [m.get("name", "") for m in response.json().get("models", [])]
    except Exception as exc:  # noqa: BLE001 - health must not raise
        return {"reachable": False, "model_pulled": False, "error": exc.__class__.__name__}

    return {
        "reachable": True,
        "model_pulled": any(name == config.MODEL or name.startswith(f"{config.MODEL}:") for name in names),
        "models": len(names),
    }


def schema_preview(schema_model: type[BaseModel]) -> str:
    """Handy for logs and debugging what the model was asked for."""
    return json.dumps(schema_model.model_json_schema(), indent=2)
