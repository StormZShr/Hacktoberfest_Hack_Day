"""Pydantic models for RepoPilot AI.

Every model in this file is hand-written and validated at the API boundary, so a
bad model reply becomes a skipped file instead of a 500.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["high", "medium", "low"]

# Used to sort findings: high first, then medium, then low.
SEVERITY_ORDER: dict[str, int] = {"high": 0, "medium": 1, "low": 2}


class Finding(BaseModel):
    """A single review finding, as returned to the client."""

    file: str
    line: int = Field(ge=1)
    severity: Severity
    title: str
    explanation: str
    suggestion: str


class FileFindings(BaseModel):
    """Validates one file's model reply (the top-level object we ask for)."""

    findings: list[Finding] = Field(default_factory=list)


class SkippedFile(BaseModel):
    """A file we could not review, plus the human-readable reason why."""

    file: str
    reason: str


class ReviewRequest(BaseModel):
    diff: str = Field(min_length=1)


class ReviewResponse(BaseModel):
    findings: list[Finding]
    skipped: list[SkippedFile]
    files_reviewed: int


class HealthResponse(BaseModel):
    ollama_up: bool
    model: str
    model_pulled: bool


# Flat JSON schema handed to Ollama's structured-output `format` field.
# Written by hand instead of using FileFindings.model_json_schema() because the
# generated version relies on $defs/$ref, which is harder for the grammar
# converter to handle. Keep this in sync with FileFindings above.
FINDINGS_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file": {"type": "string"},
                    "line": {"type": "integer"},
                    "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                    "title": {"type": "string"},
                    "explanation": {"type": "string"},
                    "suggestion": {"type": "string"},
                },
                "required": [
                    "file",
                    "line",
                    "severity",
                    "title",
                    "explanation",
                    "suggestion",
                ],
            },
        }
    },
    "required": ["findings"],
}
