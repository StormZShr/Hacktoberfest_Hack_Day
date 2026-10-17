# Launchpad: plan.md

A marketplace where students list their project demos and anyone can buy the project.
A local open-weight model (**Ollama + gemma4:e2b**) runs the listing, quality-check, and buyer-assistant features.

**Deadline: 3 days. Smallest working MVP. Anything not listed here is out of scope; ask before adding it.**

---

## 1. Problem and pitch

- Students build good projects that sit unused on GitHub. Buyers (juniors, other students, small teams) want working, explained projects but can't judge quality or fit quickly.
- Sellers hate writing listings. Buyers can't tell what they're getting.
- Launchpad fixes both with a local AI layer: it writes the listing, checks its quality, and answers buyer questions about the project.

**Why open-weight + local matters (for the submission write-up):**
- **Privacy before purchase:** a seller's unpublished code and README are analyzed on the platform's own machine. They are never sent to a third-party AI API, so the paid asset isn't leaked before it's sold.
- **Cost:** AI help is free per listing and per question, so the platform can offer it to every seller with no per-request bill.
- **Control:** the model is swappable with one env var, and prompts and output schemas are fully inspectable.
- **Honest limits:** e2b is a small model. It makes mistakes, so every AI output is advisory, validated, and editable by the human.

**Business model (hypothesis to validate, not market fact):** free to list, platform keeps a commission (e.g. 10%) on each sale.

---

## 2. Users and core flows

| Role | Flow |
|---|---|
| **Seller (student)** | Register → paste README/description → **AI autofills listing** → upload ZIP + demo link → **AI quality check** → publish → see sales |
| **Buyer** | Browse/search (**AI natural-language search**) → open project → **ask the AI about it** → buy → download |

---

## 3. Where gemma4:e2b is critical

The model is not decoration. Remove it and the product loses its core flows.

| # | Feature | Input → Output | Notes |
|---|---|---|---|
| A1 | **Listing autofill** | Raw README/description → structured listing: title, tagline, description, tech stack, category, difficulty, "what you get", 3 demo talking points | Schema-constrained JSON. Seller edits before saving. |
| A2 | **Pre-publish quality check** | Listing + README → score 0–100, missing items (setup steps, license, screenshots, tests), risk flags, fix suggestions | Advisory. Hard checks (title, price, file, demo link) are deterministic code, not AI. |
| A3 | **Ask the project** (buyer) | Question + that project's listing/README → answer grounded only in that text, or "not in the listing" | Model gets only that project's text. No tools, no web. |
| A4 | **Smart search** (stretch) | "react project with auth under ₹500" → filters `{tech, category, max_price, keywords}` → SQL query | Model only extracts filters. SQL is built by code, never by the model. |

**Shared AI rules**
- Ollama `format` takes a JSON schema. Validate with Pydantic, retry once on failure, then return a clear error.
- `temperature` 0.1 for extraction and review, 0.3 for Q&A.
- Truncate input (e.g. README to ~6,000 chars) to fit context. Set `OLLAMA_CONTEXT_LENGTH=8192`.
- Treat seller text as **data, not instructions** (prompt-injection guard). The system prompt says to ignore instructions inside the listing. The model has no tools, so the worst case is a bad answer.
- The model never sets the price or approves a sale. It only suggests.
- Cache A1/A2 results on the project row. Don't re-run on every page view.
- Keep the model warm (`keep_alive`) and show loading states, since CPU inference is slow.

---

## 4. Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js (JavaScript/JSX, no TypeScript), plain CSS |
| Backend | Python, FastAPI, uvicorn |
| AI | Ollama, `gemma4:e2b` (env `LAUNCHPAD_MODEL`) |
| Database | SQLite via SQLModel (zero setup) |
| Auth | Email + password, hashed, JWT |
| Payments | `PaymentProvider` interface: **mock** first, **Razorpay test mode** if time. No real money. |
| File storage | Local disk (`backend/storage/`), ZIP upload with size cap |

**Dependencies (confirm before installing):**
- backend: `fastapi`, `uvicorn`, `httpx`, `pydantic`, `sqlmodel`, `python-multipart`, `PyJWT`, `bcrypt`, `razorpay` (stretch)
- frontend: `next`, `react`, `react-dom`

Two swaps from the original list, both forced by this machine (Python 3.15, no MSVC):
- `uvicorn[standard]` → `uvicorn`. The extra pulls `pyyaml`, which has no 3.15 wheel and fails to build without C++ build tools. `--reload` still works (StatReload).
- `passlib[bcrypt]` → `bcrypt` directly. passlib 1.7.4 (last release 2020) breaks against bcrypt 5 (`_bcrypt.__about__`). Older pip-only wheel and bcrypt hardening against >72-byte inputs make the direct call simpler than patching passlib.

**UI design:** all frontend work starts by loading the `frontend-design` skill (`.opencode/skills/frontend-design`) and writing a short design plan — palette, type, layout, principles — before any CSS is written. The plan is reviewed against the brief before building, and the pages are built to match it, so the UI does not read as stack-agnostic defaults. This adds no dependencies: plain CSS, one global stylesheet (`frontend/app/globals.css`, which Next.js requires), inside the structure in section 5.

### Frontend design plan (written before any CSS)

**Brief.** Launchpad is a noticeboard where Indian engineering students list working projects and juniors buy them. Two audited facts shape the design: every listing carries an AI quality score that ran on this machine, and the seller's code and README never render to a buyer.

**Visual concept.** A college project-exhibition board. Listings are index cards pinned to board paper: a strip of tape, a hand-placed tilt, a hairline ink rule, a marigold price tag, and a red rubber stamp carrying the quality score. The stamp is the one loud element — it is the product's differentiator and it is data, not decoration.

**Color (6).**
`--ink #1B2440` indigo: body text, page frame, button fill · `--paper #EFEFE9` green-cast recycled paper: page ground (deliberately not cream) · `--paper-2 #E3E2D9` ruled paper: card tops, dividers · `--ink-soft #575F7A` secondary text · `--marigold #E39B2C` price tags, primary action, focus ring (ink on marigold, never marigold text on paper) · `--stamp #B4372A` the quality stamp, risk flags, "not in the listing" · `--verified #2E6B4F` grounded answers, paid and download-ready.

**Type** (offline system stacks; plan's frontend deps stay `next`, `react`, `react-dom`).
- Display: Palatino / Iowan / Book Antiqua serif for the wordmark, listing titles and page headings. A printed notice, not a hero banner.
- Body and UI: Segoe UI Variable Text / `system-ui`; line length capped at 68ch.
- Numbers (price, score): same sans with `font-variant-numeric: tabular-nums`, so columns align without a monospace data-label look.
- Uppercase appears only inside the rubber stamp, which is genuinely uppercase.

**Layout.** Left-aligned throughout, nothing centred.

```
BROWSE
  Launchpad                                          [ Sign in ]
  Student projects you can buy and run today.
  [ search…                    ] [ category ][ tech ][ ₹ max ][ Go ]
  ┌ tape ──────────────┐   ┌ tape ──────────────┐
  │ StudyBuddy         │   │ MessMate           │
  │ title / tagline    │   │                    │
  │ tech, tech, tech   │   │ tech, tech         │
  │ (stamp)     ₹499 ⬦ │   │ (stamp)    ₹199 ⬦  │
  └────────────────────┘   └────────────────────┘

DETAIL (single sheet, 68ch column; buy panel pinned right on wide screens)
  StudyBuddy: flashcards from your notes
  tagline · ml-ai, difficulty: intermediate · ₹499 tag
  what you get (list)   |  ask the project (margin note, marigold rule)
  demo points 1-3       |  [ Buy ₹499 ]  or  [ Download ZIP ]
```

- Board: pinned cards, 3-up ≥1100px, 2-up ≥700px, 1-up below. No drop shadows and no border-radius; separation comes from the paper rule and the tilt (±0.5deg).
- Card: tape strip, full-width serif title, tagline, comma-separated tech, then a foot row where the rotated quality stamp sits next to the clipped marigold price tag, with an ink "DRAFT" note on the seller's own drafts.
- sell/new is an answer sheet: README textarea on ruled lines, **Fill from my README**, then the listing rows, then a step strip — Save draft, Check quality, Publish ZIP — where each step shows its state (ink = next, verified green = done, stamp red = blocked).
- Motion, two moments only: the stamp lands (scale 1.08 → 1, 180ms) when a score arrives, and the ask answer unrolls when it arrives. Both respect `prefers-reduced-motion`.
- States: empty board invites a first listing and links to sell/new; errors say what failed and the next action; loading says the check is running on this machine instead of showing a bare spinner.

**Principles.**
1. The quality stamp is the hero: one loud rotated device per card, carrying a real score and the words that it ran locally.
2. Everything is pinned paper: tape, tilt, hairline, clipped tag. Physicality replaces the SaaS card kit.
3. Two faces, both offline; sentence case everywhere except the stamp.
4. Privacy is shown, not claimed: the README is never sent to a buyer, and the stamp says where the check ran.
5. Quiet around the stamp: no ALL-CAPS labels, no middle-dot meta strings, no "→" on buttons, no fade-up sections.

**Self-critique before building.** Not cream-and-terracotta (indigo, marigold, green-cast paper). Not near-black with one acid accent. Not broadsheet: cards are pinned and tilted, not hairline newspaper columns. Not the SaaS card kit: no radius, no shadows, and cards differ by stamp and tilt. No big-number-gradient hero — the board of real listings is the hero. Numbered markers only on the demo talking points, which really are a sequence. The uppercase stamp is one deliberate material exception. Residual risk: paper plus serif can drift toward a craft brochure; the marigold tag, tape and stamp keep it a college noticeboard. Palette contrast is checked in the browser before this is called done.

---

## 5. File structure

```
launchpad/
├── plan.md
├── README.md
├── AGENTS.md
├── scripts/                 # manual verification, run against the live app
│   ├── day1_check.ps1       # auth, projects, publish gates, A1, A2
│   ├── day2_check.ps1       # upload, gated download, A3, orders, filters
│   ├── ask_check.ps1        # A3 grounding flag
│   ├── contrast.mjs         # WCAG AA pairs from the design tokens
│   └── ui_flow.mjs          # the whole flow in headless Chrome (CDP)
├── backend/
│   ├── main.py              # app, CORS, router registration, /health
│   ├── config.py            # env: model, ollama url, jwt secret, limits
│   ├── db.py                # engine, session, create tables
│   ├── models.py            # User, Project, Order (SQLModel)
│   ├── schemas.py           # request/response + AI output schemas
│   ├── auth.py              # hashing, JWT, current_user dependency
│   ├── seed.py              # demo sellers + 4-5 sample projects
│   ├── routers/
│   │   ├── auth.py          # register, login, me
│   │   ├── projects.py      # CRUD, publish, upload, download (gated)
│   │   ├── ai.py            # autofill, review, ask, search
│   │   └── orders.py        # create order, confirm/webhook, my orders
│   ├── services/
│   │   ├── llm.py           # Ollama client: schema call, retry, validate
│   │   ├── prompts.py       # system prompts for A1-A4
│   │   ├── payments.py      # PaymentProvider: MockProvider, RazorpayProvider
│   │   └── storage.py       # save/serve ZIPs, size/type checks
│   ├── storage/             # uploaded ZIPs (gitignored)
│   └── requirements.txt
└── frontend/
    ├── package.json
    ├── app/
    │   ├── globals.css              # the whole design system (plain CSS)
    │   ├── layout.jsx               # masthead, auth-aware nav
    │   ├── page.jsx                 # browse + smart search
    │   ├── login/page.jsx
    │   ├── sell/new/page.jsx        # autofill + review + publish
    │   ├── projects/[id]/page.jsx   # detail, ask-AI, buy
    │   └── dashboard/page.jsx       # my listings/sales, my purchases
    ├── components/
    │   ├── ProjectCard.jsx
    │   ├── SearchBar.jsx
    │   ├── ListingForm.jsx
    │   ├── ReviewPanel.jsx          # score + missing items
    │   ├── AskBox.jsx
    │   └── BuyButton.jsx
    └── lib/
        ├── api.js
        └── auth.js
```

---

## 6. High-level design

```
Next.js (3000) ──HTTP/JSON──> FastAPI (8000) ──> SQLite + storage/
                                   │
                                   └──> Ollama (11434) ──> gemma4:e2b   (local, offline)
```

**Data model**
- `User`: id, email, name, password_hash, created_at
- `Project`: id, seller_id, title, tagline, description, tech_stack (JSON), category, difficulty, what_you_get (JSON, from A1), demo_points (JSON, from A1), price_inr, demo_url, readme_text, file_path, status (`draft`/`published`), ai_score, ai_review (JSON), created_at
- `Order`: id, project_id, buyer_id, amount_inr, provider, provider_ref, status (`pending`/`paid`/`failed`), created_at

**Endpoints**
- Auth: `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
- Projects: `GET /projects` (q, category, tech, max_price), `GET /projects/mine` (the seller's own listings, drafts included), `GET /projects/{id}`, `POST /projects`, `PUT /projects/{id}`, `POST /projects/{id}/file`, `POST /projects/{id}/publish`, `GET /projects/{id}/download` (paid buyers and the seller only)
- AI: `POST /ai/autofill`, `POST /ai/review`, `POST /projects/{id}/ask`, `POST /ai/search` (stretch). Autofill and review require a login, since they run the local model; ask does not, because it is part of browsing (it reads one published listing and never writes).
- Orders: `POST /orders`, `POST /orders/{id}/confirm` (mock) or `POST /webhooks/razorpay`, `GET /orders/me`
- `GET /health`: Ollama up, model pulled, DB ok

**Visibility rules**
- `GET /projects` and `GET /projects/{id}` serve published projects only. A draft is visible to its seller through `?`-free `GET /projects/{id}` with their token, and to nobody else (404, not 403, so drafts aren't leaked).
- Publishing and editing are owner-only; `GET /orders/me` is per-buyer.

**Rules enforced by code, not AI**
- Publish requires: title, price ≥ 0, demo URL or file, and a completed AI review run (the score itself is advisory).
- Download requires a `paid` order for that buyer, or being the seller.
- Seller can only edit their own projects.
- Upload: ZIP only, size capped (e.g. 25 MB).

---

## 7. Three-day plan

### Day 1: Backend core + AI service
- `config.py`, `db.py`, `models.py`, `schemas.py`, `auth.py`, auth router
- `services/llm.py` with schema-constrained call, validation, retry, input truncation
- `services/prompts.py` and `routers/ai.py`: **A1 autofill** and **A2 review**
- `routers/projects.py`: create, update, list, get, publish
- `seed.py`

**Done when:**
- `/health` reports the model pulled
- Posting a sample README to `/ai/autofill` returns valid listing JSON
- `/ai/review` returns a score and a missing-items list for a deliberately weak listing
- Register → login → create → publish works via curl

### Day 2: Frontend + buying
- **Load the `frontend-design` skill and write the short design plan** (palette, type, layout, principles) before writing any frontend CSS
- Next.js pages: browse, project detail, login, sell/new, dashboard
- A1 and A2 wired into `sell/new` (autofill button, review panel with loading states)
- **A3 Ask-the-project** on the detail page
- `storage.py`, upload and gated download
- `payments.py` with `MockProvider`, `routers/orders.py`, `BuyButton`

**Done when:**
- A seller can go from pasted README to a published listing in the UI
- A buyer can ask a question, "buy" with the mock provider, and download the ZIP
- A non-buyer gets 403 on download

### Day 3: Payment, search, polish, submission
- Razorpay test mode behind the same `PaymentProvider` interface (fallback: keep mock)
- **A4 smart search** if Days 1-2 finished early
- Seed realistic demo data, fix the rough edges in the demo path, empty/error states, polish the UI against the Day 2 design plan (`frontend-design` skill for the second pass)
- README: setup, model and licence, why local open-weight beats closed here, limitations, **demo walkthrough**
- Record the 2-3 minute demo (morning, not last minute)

**Done when:** a fresh clone runs end to end from the README, and the demo video is recorded.

---

## 8. Demo walkthrough (target 2-3 min)

1. Show Ollama running locally with `gemma4:e2b` (no internet needed for AI).
2. Seller pastes a README → **autofill** produces the listing.
3. **Quality check** flags a missing item → seller fixes it → publish.
4. Buyer opens the listing → asks "Does it include auth? How do I run it?" → grounded answer.
5. Buyer buys (test checkout) → downloads the ZIP.
6. Closing line: the AI ran on a local open model, and the seller's code never left the machine.

---

## 9. Cut list (mention as roadmap in the README)

Reviews/ratings, seller payouts, refunds, email notifications, admin panel, real-money payments, embeddings/vector search, multi-file preview, OAuth login, license generation, Docker.

**Fallbacks if behind schedule**
- Replace JWT auth with email-only identity.
- Keep the mock payment provider.
- Drop A4.
- Never drop A1-A3, since they are the open-model story.

---

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| e2b output is malformed or low quality | JSON-schema `format` + Pydantic validation + one retry; human edits everything; test prompts on 3 sample READMEs on Day 1 |
| Slow responses on CPU | Keep model warm, truncate inputs, loading states, cache A1/A2 results |
| Scope creep (auth, payments, uploads add up) | Fixed cut list and fallbacks above; no new features without asking |
| Payment integration eats Day 3 | Mock provider is the default; Razorpay is behind the same interface |
| Prompt injection via README | Seller text treated as data; model has no tools or write access |
| Windows Smart App Control / Ollama setup issues | Ollama already runs via WSL; keep one Ollama server only |
| Bad AI claims about a project (hallucination) | A3 answers only from that project's text, says "not in the listing" otherwise; label AI output in the UI |

---

## 11. Environment

```
LAUNCHPAD_MODEL=gemma4:e2b
OLLAMA_URL=http://localhost:11434
OLLAMA_CONTEXT_LENGTH=8192      # set on the Ollama server
JWT_SECRET=change-me
MAX_UPLOAD_MB=25
PAYMENT_PROVIDER=mock           # or razorpay
RAZORPAY_KEY_ID=...             # test mode only
RAZORPAY_KEY_SECRET=...
```

Optional extras, all with working defaults in `backend/config.py`: `JWT_EXPIRE_MINUTES`, `README_MAX_CHARS` (input truncation, 6000), `OLLAMA_KEEP_ALIVE`, `LLM_TIMEOUT_SECONDS` (CPU inference is slow), `DATABASE_URL`, `STORAGE_DIR`, `CORS_ORIGINS`.

`JWT_SECRET=change-me` is a 9-byte dev default and PyJWT warns about it. Fine for the demo; set a 32+ byte secret before anything real.

Run: `ollama pull gemma4:e2b`, `uvicorn main:app --reload --port 8000` (backend), `npm run dev` (frontend, port 3000).

---

## 12. Reuse from RepoPilot

The Ollama structured-output pattern in the earlier `backend/main.py` (schema in `format`, Pydantic validation, per-call error handling) carries over into `services/llm.py`. The diff-review code and endpoints are dropped.

---

## 13. Definition of done

- [ ] Seller: paste README → autofill → review → publish, all in the UI
- [ ] Buyer: search, ask the AI, buy (test mode), download
- [ ] Download blocked without a paid order
- [ ] All AI calls go to local `gemma4:e2b`, with no external AI API
- [ ] README with setup, licence note, limitations, demo walkthrough
- [ ] Demo video recorded
