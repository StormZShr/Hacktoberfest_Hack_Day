# Progress

Current step: Day 1 exit criteria met — next is Day 2, Task 2.1
Status: Day 1 Done; re-verified under `gemma4:e2b` on 2026-10-17 (see log) — contract PASS, recall 7/9 vs 0/9 under `qwen2.5:3b`

| Day | Task | Status | Files | Manual check result |
| --- | ---- | ------ | ----- | ------------------- |
| 1 | 1.1 Local environment | Done | `backend/.venv`, `.gitignore` | PASS — deps import; `.venv` ignored by git |
| 1 | 1.2 Model pulled, health path proven | Done | none | PASS — default reports `model_pulled: False`; `qwen2.5:3b` reports `True` |
| 1 | 1.3 Structured output proven | Done | none | PASS — schema-constrained reply parsed and validated (3 findings, 38.2s incl. cold load) |
| 1 | 1.4 `/health` over HTTP | Done | none | PASS — HTTP 200, `HealthResponse` shape |
| 1 | 1.5 `/review` against `samples/buggy.diff` | Done | none | Contract PASS / quality FAIL — see caveat below |
| 1 | 1.6 Skip path proven | Done | none | PASS — all four degenerate inputs degrade gracefully, no 500 |
| 2 | 2.1 Next.js scaffold | Not started | | |
| 2 | 2.2 API client | Not started | | |
| 2 | 2.3 Review tab | Not started | | |
| 2 | 2.4 `repo.py` chunking and BM25 | Not started | | |
| 2 | 2.5 `/index` and `/ask` | Not started | | |
| 2 | 2.6 Ask tab | Not started | | |
| 3 | 3.1 One real open-source Python repo | Not started | | |
| 3 | 3.2 `README.md` | Not started | | |
| 3 | 3.3 Cold-start rehearsal | Not started | | |

## Log

### 2026-10-17 — Day 1, Tasks 1.1–1.6 — backend verified end to end

**Status:** Done. No source file needed changing; the pre-existing backend ran
correctly on first execution.

**Files changed:** `backend/.venv/` (created, git-ignored), `.gitignore` (new).
No `.py` file was modified.

**Deviations from plan.md:**
1. The model under test is `qwen2.5:3b`, not the `qwen2.5-coder:1.5b` named in
   Task 1.2. The user pulled `qwen2.5:3b`, which is Qwen2.5's **general instruct**
   model — not the Coder variant. Structured output still works; review quality
   suffers (see 1.5).
2. Task 1.5's expected `skipped == []` was met, but the seeded-defect recall table
   was **not** met. Recorded as a model-quality failure, not a code defect.

**Manual checks and observed results**

1.1 — `.venv\Scripts\python -c "import fastapi, uvicorn, httpx, pydantic"`
  -> fastapi 0.143.3, uvicorn 0.54.0, httpx 0.28.1, pydantic 2.14.1
  -> `git check-ignore -v backend/.venv` -> `.gitignore:1:.venv/`
  -> `git status -uall` does not list `.venv`

1.2 — `python -c "import llm; print(llm.health())"`
  -> default: `{'ollama_up': True, 'model': 'qwen2.5-coder:7b', 'model_pulled': False}`
  -> `REPOPILOT_MODEL=qwen2.5:3b`: `{'ollama_up': True, 'model': 'qwen2.5:3b', 'model_pulled': True}`
  -> `ollama list` -> `qwen2.5:3b`, 1.9 GB, Q4_K_M, capabilities `["completion","tools"]`

1.3 — direct `llm.chat_json(main.REVIEW_SYSTEM, prompt, schemas.FINDINGS_JSON_SCHEMA)`
  -> `error: None`, 38.2s including cold model load
  -> `FileFindings.model_validate` succeeded, 3 findings
  -> **The `format` JSON-schema constraint is honoured.** Highest-risk assumption cleared.

1.4 — `Invoke-WebRequest http://127.0.0.1:8000/health`
  -> 200 `{"ollama_up":true,"model":"qwen2.5:3b","model_pulled":true}`
  -> Note: uvicorn binds `127.0.0.1` only; `localhost` resolves to `::1` first on this box.

1.5 — `POST /review` with `samples/buggy.diff`
  -> status 200, elapsed 59.3s for 2 files (~30s/file)
  -> `files_reviewed == 2` PASS, `skipped == []` PASS
  -> severity sorted high->medium->low PASS
  -> every `line` within `1..max_line` PASS (`config.py` max 19, `inventory.py` max 31)
  -> **quality FAIL:** of the 9 seeded defects, 0 were correctly diagnosed. Severity was
     all-`high` (no discrimination, and non-deterministic: 5 findings on one call,
     4 on the next, despite `temperature: 0.1`). Findings landed on the right *regions*
     (config.py lines 2/5/10/18, inventory.py line 22) but with invented explanations,
     e.g. flagging the hardcoded secret as "missing salt"; calling `retry()` "unused"
     instead of off-by-one; and missing the `/idx` division by zero outright.

1.6 — degenerate inputs, all HTTP 200
  -> `"not a diff at all"` -> `{'findings': [], 'skipped': [], 'files_reviewed': 0}`
  -> deleted-file-only -> `skipped: [{'file': 'gone.py', 'reason': 'file deleted, nothing new to review'}]`
  -> `{"diff": ""}` -> 422 (Pydantic `min_length=1`, correct boundary validation)
  -> dead host `http://127.0.0.1:9` -> `health: ollama_up False`;
     `chat_json: (None, 'ollama unreachable at http://127.0.0.1:9')`

**Open decision for the user:** pull `qwen2.5-coder:3b` (the Coder variant of what was
pulled) or accept `qwen2.5:3b`. Switching is an env var only — no code change.

**Resolved:** the user will pull the Coder variant themselves. Until they do, all
quality numbers above are the *general* `qwen2.5:3b`, not a Coder model — treat the
0/9 recall figure as a floor, not a verdict on the architecture.

**Stray process:** the uvicorn instance started for 1.4/1.5 has been stopped;
port 8000 is free. Its access log confirms 4x `POST /review` 200 and 1x 422.

### 2026-10-17 — Model swap re-verification — `gemma4:e2b`

- Status: Done. The project still works; the model swap is env-var only.
- Files changed: `AGENT.md` -> `AGENTS.md` (rename only); `Progress.md`. No `.py`
  file was modified.
- Manual check (exact commands, from `backend/` with `$env:REPOPILOT_MODEL='gemma4:e2b'`):
  1. `.venv\Scripts\python -c "import llm; print(llm.health())"`
  2. `.venv\Scripts\python -c "import llm,schemas; d,e = llm.chat_json('You are a reviewer.','File: x.py\n\n1: return 1/0\n\nReturn the findings for this file.', schemas.FINDINGS_JSON_SCHEMA); print('error=',e); print('ok=', schemas.FileFindings.model_validate(d) if d else None)"`
  3. `.venv\Scripts\python -m uvicorn main:app --port 8000`, then `POST /review`
     with `samples/buggy.diff` and with `{"diff": "not a diff at all"}`
- Observed:
  - 1.2 — `{'ollama_up': True, 'model': 'gemma4:e2b', 'model_pulled': True}` PASS
  - 1.3 — `error= None`; `FileFindings` validated (1 finding, correct
    `ZeroDivisionError`) in 36.5s including cold model load. **The `format`
    JSON-schema constraint is still honoured.** PASS
  - 1.4 — 200 `{"ollama_up":true,"model":"gemma4:e2b","model_pulled":true}` PASS
  - 1.5 — 200, elapsed **179.7s for 2 files** (~90s/file), `files_reviewed == 2`,
    `skipped == []`, 7 findings sorted high -> medium -> low, every `line` within
    `1..max_line` PASS. **Quality: recall 7/9** of the seeded defects, all on the
    correct lines — versus 0/9 under `qwen2.5:3b`. Missed: `retry()` returning
    `limit` instead of `times` (`config.py`); `prices == None` instead of
    `is None` (`inventory.py`). Severity still imperfect: the hardcoded secret is
    reported `low` (plan says high) and `average_price` / `find` are `medium`
    (plan says high).
  - 1.6 — `{"diff":"not a diff at all"}` -> 200
    `{'findings': [], 'skipped': [], 'files_reviewed': 0}`, unchanged PASS
- Deviation from plan.md: the model under test is `gemma4:e2b`, not the
  `qwen2.5-coder:*` named in Tasks 1.2/1.3/1.5. Switched via `REPOPILOT_MODEL`
  only (the env-var knob plan.md already documents); no code change.
- Carry-forward notes for Day 2: ~90s/file is under the 180s `CHAT_TIMEOUT` but
  slower than `qwen2.5:3b`'s ~30s/file, so the Review tab should show progress;
  and `/health` proxied Ollama's `/api/tags` in 2-5s while the model was
  resident, so `frontend/lib/api.js` must not use a short client timeout.
- Stray process: the uvicorn instance started for this check was stopped; port
  8000 is free.

## Resuming

Day 1 is complete and needs no rework. To restart work:

```
cd backend
.venv\Scripts\python.exe -m uvicorn main:app --port 8000
```

`REPOPILOT_MODEL` is unset in a fresh shell, so set it explicitly — otherwise
`/health` reports `model_pulled: False` for the default `qwen2.5-coder:7b`.

Next up: **Day 2, Task 2.1** (Next.js scaffold). Carry forward two findings from
Day 1: point `frontend/lib/api.js` at `http://127.0.0.1:8000`, not `localhost`
(uvicorn binds IPv4 only, `localhost` resolves to `::1` first on this box); and
expect Day 2's `/ask` quality to track whatever model is pulled here.
