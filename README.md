# Launchpad

A student project marketplace where the AI runs on your own machine. Sellers turn a README into a
listing in minutes; buyers ask questions that are answered only from the listing itself, then buy and
download. Every model call goes to an open-weight model served by local [Ollama](https://ollama.com)
— no external AI API, no API key, no per-question cost.

**Status:** Days 1 and 2 of a 3-day build are done and verified end to end (see [Verification](#verification)).
Razorpay test mode, polish and the demo video remain.

---

## The problem

Every semester, working student projects die the week after they are graded, while the juniors behind
them rebuild the same things. The market that should exist between them does not, because a listing
is only a promise: a title, a paragraph and a price. A buyer cannot tell a finished, runnable project
from an abandoned repository with a good README, and a seller cannot answer questions without giving
away the thing they are selling.

Launchpad is that marketplace with a trust layer sized for it.

## What it does

**Seller** — paste the project's README. The local model drafts the listing (title, tagline,
description, tech stack, category, difficulty, what the buyer gets, demo talking points). The seller
edits every field, saves the draft, attaches the ZIP, runs a quality check, and publishes.

**Buyer** — browse and filter the board; open a listing; ask it a direct question before spending
anything; buy through test-mode checkout; download the ZIP. The download is gated: without a paid
order it returns 403.

## Where the AI sits

Three narrow jobs, all schema-constrained and all advisory:

| Task | Endpoint | Input | Output |
| --- | --- | --- | --- |
| **A1 · Autofill** | `POST /ai/autofill` | the seller's README | a structured listing draft |
| **A2 · Quality check** | `POST /ai/review` | listing + README | score 0–100, summary, missing items, risk flags, fixes |
| **A3 · Ask** | `POST /projects/{id}/ask` | one question, one listing, its README | an answer plus a flag saying whether the answer came from the listing |

Design rules that hold across all three:

- **Schema-constrained output.** The Pydantic model doubles as the JSON schema handed to Ollama, so
  free-form prose is never parsed.
- **Validated before storage**, with one retry on malformed output.
- **Advisory only.** The seller's text is treated as data, never as instructions, and no rule the
  product depends on is delegated to the model.

## Why the model runs locally

This is the load-bearing decision in the project, not a deployment preference.

1. **The README is the product.** A seller's README and code are the asset being sold. Sending them
   to a hosted API would upload the thing they are about to charge for before a single sale. Running
   `gemma4:e2b` locally means that material never leaves the machine — and the README is never
   rendered to a buyer, who gets the AI's answer *about* it instead.
2. **The unit economics only close locally.** Listings sell for ₹149–₹749. An inference bill on every
   draft, check and buyer question would put a variable cost on browsing itself. Local inference makes
   the marginal cost of an AI call zero, with no keys, quotas or billing account to leak.
3. **It creates the trust it sells.** The stamp on every card says *"ran on this machine"*, and that
   is verifiable, because the score and the answers come from a model on the same laptop rather than a
   vendor's endpoint. Privacy here is shown, not asserted in a policy.
4. **It works where students are.** College Wi-Fi, a hostel room, a demo hall without reliable
   internet: the AI keeps working, because it is not a network dependency.
5. **The constraints made the architecture safer.** A model this small cannot be given trust it has
   not earned, so it is fenced: structured output, validation, human editing, and deterministic code
   behind everything that matters. The model drafts and grades; it never decides.

## Honest about a small local model

`gemma4:e2b` is small enough to run on a laptop CPU, and it behaves like it:

- Scores drift between identical runs (a listing scored 75 and 85 on two runs).
- It once flagged a correctly quoted README answer as "not in the listing". The prompt was tightened
  and the flag is now right in testing, but it can still leak a JSON fragment into prose.

That is exactly why its output is advisory, visible and editable, and why publish requirements,
ownership checks and download gating are plain deterministic code. Nothing the product depends on is
decided by the model.

## Stack

- **Backend:** Python 3.10+, FastAPI, SQLModel + SQLite, Pydantic v2, `bcrypt` + PyJWT, `httpx`.
- **Frontend:** Next.js (App Router, JSX — no TypeScript), plain CSS, no UI framework.
- **AI:** Ollama serving `gemma4:e2b`, reached only through `backend/services/llm.py`.
- **Payments:** a `PaymentProvider` interface with a mock provider. Razorpay test mode is next.

The UI design plan (palette, type, layout, principles) lives in `plan.md` §4 and the whole design
system is one stylesheet, `frontend/app/globals.css`.

## Setup

### 0. Prerequisites

Python 3.10+, Node 18+, and [Ollama](https://ollama.com) running locally with the model pulled:

```bash
ollama pull gemma4:e2b
ollama serve
```

### 1. Backend (port 8000)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\python.exe seed.py          # 2 demo sellers, 5 projects (4 published, 1 draft)
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

`GET http://127.0.0.1:8000/health` reports the database, whether Ollama answers, and whether the model
is actually pulled — check this first if anything looks wrong.

### 2. Frontend (port 3000)

```powershell
cd frontend
npm install
npm run dev
```

Then open <http://localhost:3000>.

### 3. Demo accounts

| Email | Password | Role |
| --- | --- | --- |
| `ananya@example.com` | `launchpad123` | seller |
| `rahul@example.com` | `launchpad123` | seller |

Buyers: register any email with an 8+ character password.

### Configuration

Everything has a local default; set these only if you need to change them.

| Variable | Default | Notes |
| --- | --- | --- |
| `LAUNCHPAD_MODEL` | `gemma4:e2b` | the only model the app calls |
| `OLLAMA_URL` | `http://localhost:11434` | |
| `OLLAMA_CONTEXT_LENGTH` | `8192` | |
| `OLLAMA_KEEP_ALIVE` | `10m` | keeps the model warm between calls |
| `LLM_TIMEOUT_SECONDS` | `180` | |
| `README_MAX_CHARS` | `6000` | READMEs are truncated to fit the context window |
| `JWT_SECRET` | `change-me` | **set a real 32+ byte secret before anything real**; the default is a dev value |
| `JWT_EXPIRE_MINUTES` | `10080` | 7 days |
| `DATABASE_URL` | `sqlite:///backend/launchpad.db` | |
| `STORAGE_DIR` | `backend/storage` | uploaded ZIPs |
| `MAX_UPLOAD_MB` | `25` | |
| `PAYMENT_PROVIDER` | `mock` | `razorpay` is a stub until Day 3 |
| `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` | empty | test mode only |
| `CORS_ORIGINS` | `http://localhost:3000` | comma separated |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | frontend build-time |

## Demo walkthrough

1. **Board** (`/`) — four seeded listings, each a pinned card with a price tag and its quality stamp.
   Try the filters: tech `React`, or a max price of `300`.
2. **A listing** — "What you get", numbered demo points, and **Ask about this project**. Ask *"How do
   I run it?"* (answered from the README) and then something the listing cannot answer, such as *"How
   many staff does the company employ?"* — it will say the listing does not cover it. Expect 5–15s per
   call on a CPU; the first call is slowest while the model loads.
3. **Buy** — sign in as a buyer and hit **Buy for ₹259** (or whatever the listing costs). Checkout is
   the mock provider and says so: no real money moves.
4. **Sell** — sign in as `ananya@example.com`, open **Sell a project**, paste a README, press **Fill
   from my README**, fix the fields, **Save draft**, attach a ZIP, **Check quality**, **Publish**.
   The four-step strip turns green as you go.
5. **Dashboard** — your listings with their scores, and everything you bought.

One expected snag: the seeded listings have **no ZIP attached**, so downloading one replies *"the
seller has not uploaded a ZIP yet"*. Do step 4 with a zip first if you want to see a real download.

## Verification

There is no unit-test suite; the checks are scripts that drive the real API and a real browser. Start
Ollama, the backend and the frontend first, then from the repository root:

```powershell
.\scripts\day1_check.ps1     # 19 checks: auth, projects, publish gates, A1, A2
.\scripts\day2_check.ps1     # 28 checks: upload, gated download, A3, orders, filters
.\scripts\ask_check.ps1      #  3 checks: A3 grounding flag, answerable and not
node .\scripts\contrast.mjs  #  7 WCAG AA contrast pairs from the design tokens
node .\scripts\ui_flow.mjs   # 33 checks: the whole flow driven through headless Chrome
```

Latest results, all re-run from this repository:

| Script | Result |
| --- | --- |
| `day1_check.ps1` | **19 / 19** |
| `day2_check.ps1` | **28 / 28** |
| `ask_check.ps1` | **3 / 3** |
| `contrast.mjs` | **7 / 7** WCAG AA (ink/paper 13.25:1, ink-soft 5.47:1, stamp 5.17:1, verified 5.46:1) |
| `ui_flow.mjs` | **33 / 33** — seller goes README → published listing, buyer asks → buys → downloads, non-buyer gets 403 |

`ui_flow.mjs` drives Chrome (or Edge) over the DevTools protocol: it signs in, fills the form, uploads
a real ZIP through the file input, publishes, registers a buyer, asks a question, buys, and checks the
board and both dashboards. It writes screenshots next to its output; override `CHROME_PATH`,
`LAUNCHPAD_SHOTS`, `LAUNCHPAD_TMP` or `CDP_PORT` if the defaults do not suit.

`npm run build` also completes cleanly.

## Money

There is no real payment anywhere in this project. `PAYMENT_PROVIDER=mock` creates an order, returns a
`mock_*` reference and marks it paid on confirmation. `RazorpayProvider` exists behind the same
interface and raises until Day 3 wires up test mode.

## Model and licence notes

- **Model:** `gemma4:e2b` is an open-weight model pulled and served by Ollama. No model weights are
  stored in this repository — only the model name in configuration. The weights carry Google's Gemma
  terms of use; read them before redistributing or using this commercially.
- **Bundled third-party code:** `.opencode/skills/frontend-design/` is a design skill used while
  building the UI. It keeps its own `LICENSE.txt` and is not part of the running app.
- **This repository's own code** has no licence file yet. Add one before publishing.

## What is next

- Razorpay test mode behind `PaymentProvider` (the mock stays the default).
- AI natural-language search (`POST /ai/search`) — the one stretch item from the plan.
- Polish pass against the Day 2 design plan, `README` and demo video.

---

## Project description

> Launchpad is a marketplace where students sell the projects they've finished and buy the ones they
> need, with a local open-weight model doing the work that makes that market trustworthy. A seller
> pastes their README and `gemma4:e2b` drafts the whole listing, grades it for missing setup steps,
> tests and licence, and then answers buyers' questions using only that listing and README. Running
> gemma4 locally is the core of the product rather than a deployment choice: a seller's README and code
> *are* the asset being sold, so sending them to a hosted API would leak the product before its first
> sale, and with listings at ₹149–₹749 an inference bill on every draft, check and question would put a
> cost on browsing itself. Because the model is small, it stays advisory — output is schema-constrained,
> validated and seller-editable, and everything load-bearing (publish gates, ownership, download
> gating) is plain deterministic code.

Built during a 3-day hackathon sprint. The day-by-day plan and the running log of decisions,
deviations and verification results are in `plan.md` and `progress_tracker.md`.
