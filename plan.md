# RepoPilot AI — 3-Day MVP Plan

Local-first code review assistant. Python-only, offline once the model is pulled.
No database, no auth, in-memory state only, manual acceptance checks only.

**Deadline: hard, 3 days.** Smallest working MVP. Nothing on this page is optional
except where it is marked `[optional]`.

## Ground rules

- **Scope is frozen.** Everything not listed here is out of scope. Ask the user
  before adding a feature, file, endpoint, dependency, or config knob.
- **No test suite, no extra tooling.** Acceptance is manual, by command and eyeball.
- **Never crash.** A bad model reply, a bad diff, or a dead Ollama degrades into a
  `skipped` entry with a reason. `/review` must return 200 even when every file fails.
- **Out of scope:** patch generation, Tree-sitter, embeddings, multi-language,
  persistence, pricing-tier features, tests, linting, CI.
- Update `Progress.md` at every task boundary (see `AGENT.md`).

## Target file structure

```
backend/   main.py  diffparse.py  llm.py  repo.py  schemas.py  requirements.txt  samples/buggy.diff
frontend/  package.json  app/page.jsx  app/layout.jsx
           components/DiffInput.jsx  components/FindingsList.jsx  components/AskPanel.jsx
           lib/api.js
root       README.md
```

Run commands: `uvicorn main:app --reload --port 8000` (from `backend/`),
`npx next dev` (from `frontend/`, port 3000). CORS allows `http://localhost:3000`.

## Current state (start of Day 1)

| Item | Status |
| --- | --- |
| `backend/main.py`, `diffparse.py`, `llm.py`, `schemas.py`, `samples/buggy.diff` | **Written, never executed** |
| `backend/repo.py` | Does not exist |
| `frontend/` | Does not exist |
| `README.md` | Does not exist |
| Python deps | Not installed (no venv) |
| Ollama model | Not pulled |
| Git history | No commits yet, everything untracked |

Day 1 is therefore **verify and fix**, not build-from-scratch.

---

# Day 1 — backend `/health` and `/review` working against `samples/buggy.diff`

## Task 1.1 — Local environment
**Files touched:** `backend/.venv/` (created), `.gitignore` (new)

1. `python -m venv .venv` in `backend/`
2. `.venv\Scripts\python -m pip install -r requirements.txt`
3. Create root `.gitignore` with `.venv/`, `__pycache__/`, `node_modules/`, `.next/`

**Acceptance criteria:** `fastapi`, `uvicorn`, `httpx`, `pydantic` all import inside
the venv; the venv itself is not stageable by git.

**Manual check:**
```
cd backend
.venv\Scripts\python -c "import fastapi, uvicorn, httpx, pydantic; print('deps ok')"
git status --short          # .venv/ must NOT appear
```

## Task 1.2 — Model pulled, health path proven
**Files touched:** none (environment only)

1. `ollama pull qwen2.5-coder:1.5b`
2. Set `REPOPILOT_MODEL=qwen2.5-coder:1.5b` for the active shell.
3. Call the Ollama layer directly, before FastAPI is involved.

**Acceptance criteria:** `llm.health()` reports `ollama_up: True` **and**
`model_pulled: True`. This deliberately separates "Ollama is broken" from
"FastAPI is broken".

**Manual check:**
```
cd backend
.venv\Scripts\python -c "import llm; print(llm.health())"
:: expect {'ollama_up': True, 'model': 'qwen2.5-coder:1.5b', 'model_pulled': True}
```
If this reports `ollama_up: False` while `ollama list` works, set
`REPOPILOT_OLLAMA_HOST=http://127.0.0.1:11434` (Windows `localhost` may resolve to `::1`).

## Task 1.3 — Structured output proven
**Files touched:** none

One direct `llm.chat_json()` call using the real `FINDINGS_JSON_SCHEMA`, with no
HTTP server and no frontend in the loop.

**Acceptance criteria:** the call returns a dict (not an error string), and the
dict validates against `FileFindings`. This is the single highest-risk assumption
in the project, so it is proven on its own.

**Manual check:**
```
.venv\Scripts\python -c "import llm,schemas; d,e = llm.chat_json('You are a reviewer.','File: x.py\n\n1: return 1/0\n\nReturn the findings for this file.', schemas.FINDINGS_JSON_SCHEMA); print('error=',e); print('ok=', schemas.FileFindings.model_validate(d) if d else None)"
```
Pass = a `FileFindings` object prints. Fail = an error string prints.

## Task 1.4 — `/health` over HTTP
**Files touched:** `backend/main.py` (fix only, if needed)

Start `uvicorn main:app --reload --port 8000` from `backend/` and hit the endpoint.

**Acceptance criteria:** HTTP 200, body matches `HealthResponse` exactly
(`ollama_up`, `model`, `model_pulled`).

**Manual check:**
```
curl http://localhost:8000/health
```
Then `ollama stop qwen2.5-coder:1.5b` is **not** run here — but do confirm that
stopping the Ollama server yields `{"ollama_up": false, ...}` and still HTTP 200.

## Task 1.5 — `/review` against `samples/buggy.diff`
**Files touched:** `backend/main.py`, `diffparse.py`, `schemas.py`, `llm.py` (fix only)

`buggy.diff` is a seeded fixture, so this is a real acceptance test, not a smoke test.

**Acceptance criteria:**
- `files_reviewed == 2`, `skipped == []`
- Findings sorted high -> medium -> low
- Every `line` is within `1..max_line` for its file
- Findings point at genuinely bad lines

**Manual check:**
```
curl -s -X POST http://localhost:8000/review -H "Content-Type: application/json" ^
  -d "{\"diff\": \"...\"}"
```
Easiest reliable form (avoids shell quoting):
```
cd backend
.venv\Scripts\python -c "import json,httpx,pathlib; d=pathlib.Path('samples/buggy.diff').read_text(); r=httpx.post('http://localhost:8000/review', json={'diff':d}, timeout=600); print(r.status_code); print(json.dumps(r.json(), indent=2))"
```
Seeded defects to look for, by file:

| File | Seeded defect |
| --- | --- |
| `config.py` | hardcoded `API_TOKEN` secret (high) |
| `config.py` | `open()` without `with` — leaked handle (medium) |
| `config.py` | `retry()` returns `limit` instead of `times` |
| `config.py` | `DEFAULT_TIMEOUT / idx` — ZeroDivisionError on `idx=0` (high) |
| `inventory.py` | mutable default `items=[]` (medium) |
| `inventory.py` | `prices == None` instead of `is None` (low) |
| `inventory.py` | `average_price` divides by `len(prices)` — zero-length crash (high) |
| `inventory.py` | `find()` deletes before reading — KeyError (high) |
| `inventory.py` | bare `except: pass` swallows errors (medium) |

Note: with the 1.5b smoke model, several of these will be **missed**. That is an
expected model-quality result, not a bug in the code. Judge the 2-file contract,
sorting, and line numbering here; judge recall separately in Task 3.1.

## Task 1.6 — Skip path proven, not just the happy path
**Files touched:** `samples/buggy.diff` (read-only), `diffparse.py` (fix only)

Post three degenerate bodies and confirm HTTP 200 each time.

**Acceptance criteria:** each returns a `skipped` list with a meaningful reason and
never a 500.
1. `{"diff": "not a diff at all"}` -> skipped or empty, HTTP 200
2. A diff containing only a deleted file -> `file deleted, nothing new to review`
3. Ollama stopped -> every reviewable file skipped with an `ollama unreachable` reason

**Manual check:** the three `curl`s above, checking `status_code` and the `skipped` text.

## Day 1 exit criteria
`/health` and `/review` both return 200; `buggy.diff` gives `files_reviewed == 2`
with correctly sorted findings on real line numbers; all three degenerate inputs
degrade gracefully. Commit.

---

# Day 2 — Next.js UI, `/index`, `/ask`

## Task 2.1 — Next.js scaffold
**Files touched:** `frontend/package.json`, `frontend/app/layout.jsx`

`next`, `react`, `react-dom`; scripts `dev`, `build`, `start`. JavaScript/JSX only —
**no TypeScript**. Plain CSS only.

**Acceptance criteria:** `next dev` serves a page on port 3000 with no build error;
`next build` clean.

**Manual check:** `cd frontend && npx next dev`, open `http://localhost:3000`,
confirm the layout renders. Tab titles "Review" and "Ask" are visible.

## Task 2.2 — API client
**Files touched:** `frontend/lib/api.js`

Single place holding `BASE = "http://localhost:8000"`, with `getHealth`, `postReview`,
`postIndex`, `postAsk`.

**Acceptance criteria:** no hardcoded backend URL anywhere outside this file;
non-200 responses surface a readable error instead of throwing into the void.

**Manual check:** in the browser console,
`await fetch("http://localhost:8000/health").then(r=>r.json())` succeeds while the
backend is up.

## Task 2.3 — Review tab
**Files touched:** `frontend/app/page.jsx`, `components/DiffInput.jsx`,
`components/FindingsList.jsx`

Textarea for the diff, a Review button, and a findings list. Render `skipped` visibly —
a silently dropped file is worse than a bad finding.

**Acceptance criteria:** pasting `samples/buggy.diff` and clicking Review renders
findings with file, line, severity, title, explanation, suggestion, and shows
`files_reviewed` plus any skipped entries.

**Manual check:** paste the sample, click Review. Then paste `garbage` and confirm a
clean "no findings / nothing parseable" state with no unhandled error.

## Task 2.4 — `repo.py`: chunking and BM25 retrieval
**Files touched:** `backend/repo.py` (new)

- Walk `.py` files under a given path (skip `.venv`, `node_modules`, `__pycache__`, `.git`)
- Chunk ~50 lines with small overlap, keeping file path and line range
- Build an in-memory index; score queries with keyword/BM25, no embeddings
- `TOP_K = 5` as a **fixed module constant in this file**, not configurable

**Acceptance criteria:** indexing this very repo returns chunks with correct
`path`, `start_line`, `end_line`; `TOP_K == 5`; a query for a distinctive identifier
returns the chunk that contains it, first.

**Manual check:**
```
cd backend
.venv\Scripts\python -c "import repo; r=repo.index_repo('.'); print(len(r['chunks'])); print(repo.TOP_K); [print(c['path'], c['start_line'], c['end_line']) for c in repo.search('parse_diff')]"
```
A query for `parse_diff` must return `diffparse.py` as the top hit.

## Task 2.5 — `/index` and `/ask`
**Files touched:** `backend/main.py`, `backend/schemas.py` (new models)

`/index` takes a local repo path and returns a summary (files walked, chunks built).
`/ask` retrieves the top `TOP_K` chunks and asks the model, which must answer with
`file:line` references. The index lives in memory — restarting the server clears it.

**Acceptance criteria:** `/index` then `/ask` works against a local Python repo;
the answer cites `file:line` from the retrieved chunks; asking before indexing
returns a clear "nothing indexed" message, not a 500.

**Manual check:**
```
curl -X POST http://localhost:8000/index -H "Content-Type: application/json" -d "{\"path\": \"C:/path/to/local/python/repo\"}"
curl -X POST http://localhost:8000/ask  -H "Content-Type: application/json" -d "{\"question\": \"How is the diff split per file?\"}"
```
Expected: an answer referencing real `file:line` locations that exist.

## Task 2.6 — Ask tab
**Files touched:** `frontend/components/AskPanel.jsx`, `frontend/app/page.jsx`

Path input + Index button, question input + Ask button, answer display. Existing
tab state in `page.jsx` must not re-mount the Review tab's textarea on switch.

**Acceptance criteria:** full flow works from the browser with no console errors;
Review findings survive a tab switch.

**Manual check:** review the sample, switch to Ask, index, ask, switch back —
the findings are still on screen.

## Day 2 exit criteria
Browser-only demo: paste a diff -> get sorted findings; index a local repo -> ask a
question -> get an answer with `file:line` citations. Commit.

---

# Day 3 — real repo, README, cold-start rehearsal

## Task 3.1 — One real open-source Python repo
**Files touched:** none (do not add sample files; use a temp path outside the repo)

Pick **one small** Python repo, ideally one already on disk. Generate a diff to a
temp file rather than committing anything.

**Acceptance criteria:** `/review` on a real diff returns either findings or clean
`skipped` reasons within the 180 s per-file timeout, and `/ask` over the same repo
cites real locations.

**Manual check:**
```
git -C C:/path/to/repo diff HEAD~1 -- "*.py" > $env:TEMP\real.diff
:: then POST $env:TEMP\real.diff to /review as in Task 1.5
```
Watch for: diffs larger than the 10-file review cap (expect explicit cap reasons in
`skipped`, which is correct behavior); and large files that exceed the context window.

Determine here whether `qwen2.5-coder:1.5b` recall is good enough for the demo or
whether `qwen2.5-coder:7b` is worth the latency. Switching is an env var only:
`REPOPILOT_MODEL=qwen2.5-coder:7b`, no code change.

## Task 3.2 — `README.md`
**Files touched:** `README.md` (root, new)

Required sections:
- Setup: Python venv + deps, `ollama pull`, backend and frontend run commands
- Model and license: `qwen2.5-coder:7b` (default) and `1.5b` (smoke), both
  **Apache-2.0**
- Why open beats closed: fully offline, no API keys, no per-token cost, code never
  leaves the machine, pinned reproducible weights
- Limitations: no embeddings (keyword retrieval misses semantic matches), Python
  only, 10-file review cap, no patch generation, in-memory index lost on restart,
  CPU-only latency, small models miss subtle bugs
- **Demo walkthrough:** numbered steps with exact commands and inputs, including the
  expected output at each step

**Acceptance criteria:** a reader who has never seen the project can go from clone to
a rendered finding by following the walkthrough verbatim, with no missing step.

**Manual check:** read the walkthrough and run each command exactly as written.

## Task 3.3 — Cold-start rehearsal
**Files touched:** none

From a clean shell: pull model, start backend, start frontend, walk the README
top to bottom, including the failure cases (bad diff, unindexed ask, Ollama stopped).

**Acceptance criteria:** no step produces an unhandled error; every documented
expected output matches what actually appears; both failure cases degrade gracefully.

**Manual check:** the walkthrough itself, timed end to end.

## Day 3 exit criteria
Demo runs cold from the README. Final commit.

---

# Top 3 risks

### 1. The model never returns schema-conforming JSON
Highest-leverage risk: it empties `/review` entirely while everything else looks fine.
**Cheapest mitigation:** Task 1.3 — one direct `llm.chat_json()` call against the real
schema *before* any HTTP or UI work. If it fails, the fix is the schema/prompt in
`schemas.py` and `main.py`, not a rebuild. Already mitigated once the smoke test passes.

### 2. CPU-only inference is slower than the 180 s `CHAT_TIMEOUT`
This box has 15.7 GB RAM, 12 threads and integrated graphics only. A 7b model over a
few hundred injected lines may blow the timeout and return everything as `skipped`.
**Cheapest mitigation:** time exactly one file first (Task 1.5), then set
`REPOPILOT_MODEL=qwen2.5-coder:1.5b` for the demo. Pure env var, zero code change.

### 3. Day 3 depends on a real repo that may not be available on the day
Network access, clone size, or a diff full of binary/non-Python files can eat the
last day. **Cheapest mitigation:** use a Python repo already on disk; restrict the diff
with `-- "*.py"`; if none exists, fall back to a second hand-written sample diff in
the existing `samples/` directory — the same fixture pattern already used by
`buggy.diff`, so nothing new is invented.

---

# Out of scope — do not build

Patch generation or auto-fix. Tree-sitter parsing. Embeddings or a vector store.
Languages other than Python. Any database or persistence. Auth, accounts, rate
limits, pricing tiers. Test suite, linter config, CI. A demo script.
