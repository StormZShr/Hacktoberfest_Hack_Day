"""RepoPilot AI backend (Day 1 scope: /health and /review).

Local-first code review over a unified git diff. One Ollama call per file, a
JSON-schema-constrained reply, Pydantic validation per file, and findings sorted
high -> medium -> low. A file that fails validation is skipped and reported; it
never takes the request down.
"""

from __future__ import annotations

import diffparse
import llm
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from schemas import (
    FINDINGS_JSON_SCHEMA,
    SEVERITY_ORDER,
    FileFindings,
    Finding,
    HealthResponse,
    ReviewRequest,
    ReviewResponse,
    SkippedFile,
)

# Safety cap: a huge diff should not queue dozens of minutes of local inference.
MAX_REVIEW_FILES = 10

REVIEW_SYSTEM = (
    "You are a meticulous senior Python code reviewer.\n"
    "You receive ONE changed file. Each line is prefixed with its line number "
    "in the new version of the file, in the form 'N: code'.\n"
    "Report only real defects in the code you can actually see: correctness "
    "bugs, crashes, security problems, resource leaks and clear style issues.\n"
    "Rules:\n"
    "- Cite the injected new-file line number for every finding.\n"
    "- Never invent line numbers or code that is not in the input.\n"
    "- Do not comment on the diff format itself, only on the code.\n"
    "- severity is 'high' for correctness or security bugs, 'medium' for likely "
    "bugs, crashes or leaks, 'low' for style and readability.\n"
    "- 'title' is a short summary; 'explanation' says why it is a problem; "
    "'suggestion' shows the concrete fix.\n"
    "- If the code contains no defects, return an empty findings list.\n"
    "Reply with JSON matching the required schema and nothing else."
)

app = FastAPI(title="RepoPilot AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report whether Ollama is up and whether the configured model is pulled."""
    return HealthResponse(**llm.health())


@app.post("/review", response_model=ReviewResponse)
def review(request: ReviewRequest) -> ReviewResponse:
    """Review a unified diff, one Ollama call per file."""
    files = diffparse.parse_diff(request.diff)

    skipped = [
        SkippedFile(file=file_diff.path, reason=file_diff.skip_reason)
        for file_diff in files
        if file_diff.skip_reason
    ]
    reviewable = [file_diff for file_diff in files if not file_diff.skip_reason]

    findings: list[Finding] = []
    files_reviewed = 0

    for position, file_diff in enumerate(reviewable):
        if position >= MAX_REVIEW_FILES:
            skipped.append(
                SkippedFile(
                    file=file_diff.path,
                    reason=f"review cap of {MAX_REVIEW_FILES} files reached",
                )
            )
            continue

        prompt = (
            f"File: {file_diff.path}\n\n"
            f"{file_diff.numbered_text()}\n\n"
            "Return the findings for this file."
        )
        try:
            data, error = llm.chat_json(REVIEW_SYSTEM, prompt, FINDINGS_JSON_SCHEMA)
        except Exception:
            # llm.py reports failures as values; this is belt and braces so one
            # bad file can never take down the whole request.
            skipped.append(
                SkippedFile(file=file_diff.path, reason="model call raised an unexpected error")
            )
            continue
        if error:
            skipped.append(SkippedFile(file=file_diff.path, reason=error))
            continue

        try:
            parsed = FileFindings.model_validate(data)
        except ValidationError:
            # Wrong types, missing keys, nulls: report and keep going.
            skipped.append(
                SkippedFile(file=file_diff.path, reason="model output failed schema validation")
            )
            continue
        except Exception:
            skipped.append(
                SkippedFile(file=file_diff.path, reason="could not read model output")
            )
            continue

        # Trust the path we parsed over whatever the model echoed back, and keep
        # the reported line inside the file the model was actually shown.
        line_limit = max(file_diff.max_line, 1)
        for finding in parsed.findings:
            findings.append(
                finding.model_copy(
                    update={
                        "file": file_diff.path,
                        "line": min(finding.line, line_limit),
                    }
                )
            )
        files_reviewed += 1

    findings.sort(key=lambda item: (SEVERITY_ORDER[item.severity], item.file, item.line))

    return ReviewResponse(
        findings=findings,
        skipped=skipped,
        files_reviewed=files_reviewed,
    )
