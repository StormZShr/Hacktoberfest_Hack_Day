*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 2: Side Hustle](https://dev.to/challenges/hacktoberfest-week2-2026-10-12)*

## What I Built

**Launchpad** is a marketplace where students sell the projects they have already finished, and buy the ones they need next — with a local open-weight model doing the work that makes that market trustworthy.

**The problem.** Every semester, working student projects die the week after they are graded, while the juniors behind them rebuild the same thing. The market that should exist between them doesn't, because a listing is only a promise: a title, a paragraph and a price. A buyer can't tell a finished, runnable project from an abandoned repo with a good README, and a seller can't answer questions without giving away the thing they are selling. Writing the listing is also the chore that stops most students from listing anything at all.

**What it does.** Three narrow AI jobs, all schema-constrained and all advisory:

| Task | Endpoint | Input | Output |
| --- | --- | --- | --- |
| **A1 · Autofill** | `POST /ai/autofill` | the seller's README | a structured listing draft: title, tagline, description, tech stack, category, difficulty, "what you get", 3 demo talking points |
| **A2 · Quality check** | `POST /ai/review` | listing + README | score 0–100, summary, missing items (setup steps, licence, screenshots, tests), risk flags, fixes |
| **A3 · Ask** | `POST /projects/{id}/ask` | one question, one listing, its README | an answer, plus a flag saying whether the answer actually came from the listing |

The seller pastes a README, the model drafts the listing, the seller edits every field, attaches the ZIP, runs the quality check and publishes. The buyer browses a board of pinned index cards — each one carrying a red rubber **quality stamp** that says *"ran on this machine"* — opens a listing, asks it a direct question before spending anything, buys, and downloads. The download is gated: no paid order, no file.

**Who pays for it.** Individual listings sell for ₹149–₹749, a price a student pays. Free to list, the platform keeps a commission (10% in the pitch — a hypothesis to validate, not a market fact). The paying side is the buyer: a junior who gets a runnable, explained project for the price of a takeaway meal, instead of a weekend of rebuilding. The seller side is the supply, and it only exists because the AI removes the writing work and, with the local model, the risk of leaking the product before its first sale.

## Demo

<!-- TODO: paste the 2–3 minute demo video link here (still to be recorded) -->

No deployed link — this app is deliberately local-first, and the interesting part is that the AI is a process on your own laptop, so a hosted deploy would remove the point. To see it, start Ollama and the two servers (`ollama pull gemma4:e2b`, then `uvicorn main:app --port 8000` in `backend/` and `npm run dev` in `frontend/`), open <http://localhost:3000>, and sign in as `ananya@example.com` / `launchpad123`.

The two-minute path:

1. **Board** (`/`) — four seeded listings, each a pinned card with a price tag and its quality stamp. Filter by tech `React`, or a max price of `300`.
2. **A listing** — "What you get", numbered demo points, and **Ask about this project**. Ask *"How do I run it?"* (answered from the README), then something the listing can't answer, such as *"How many staff does the company employ?"* — it says the listing doesn't cover it instead of inventing an answer. Expect 5–15s per call on a CPU.
3. **Sell** — open **Sell a project**, paste a README, press **Fill from my README**, fix the fields, **Save draft**, attach a ZIP, **Check quality** (the stamp lands with the score), **Publish**. The four-step strip turns green as you go.
4. **Buy** — register any buyer email, hit **Buy for ₹259**, and the mock checkout says plainly that no real money moved.
5. **Dashboard** — your listings with their scores, and everything you bought.

## Code

Repository: **https://github.com/StormZShr/Hacktoberfest_Hack_Day**

```
backend/    main.py  config.py  models.py  schemas.py  auth.py  seed.py
            routers/   auth.py  projects.py  ai.py  orders.py
            services/  llm.py  prompts.py  payments.py  storage.py
frontend/   app/       page.jsx  sell/new  projects/[id]  dashboard  login
            components/ ProjectCard  SearchBar  ListingForm  ReviewPanel  AskBox  BuyButton
            app/globals.css   <- the entire design system, one plain-CSS stylesheet
scripts/    day1_check.ps1  day2_check.ps1  ask_check.ps1  contrast.mjs  ui_flow.mjs
```

The files that carry the story: `backend/services/llm.py` (the only place a model is ever called), `backend/services/prompts.py` (the three system prompts), `backend/services/ai.py` → `routers/ai.py` (A1–A3), and `backend/routers/projects.py` (the deterministic publish and download gates). The UI design plan — palette, type, layout, principles — is written out in `plan.md` §4 before any CSS, and the day-by-day build log with every command and its real output is in `progress_tracker.md`.

There is no unit-test suite by choice; verification is five scripts that drive the real API and a real headless Chrome, and they are committed so the claims below are re-runnable.

## How I Built It

**Compute: local Ollama, open weights, one call path.** Every model call in the whole app goes through `backend/services/llm.py`, which is a thin `httpx` client against Ollama's `POST /api/chat`. Four decisions pin its behaviour:

- `format` = a **JSON Schema**, and the Pydantic model *is* the schema (`schemas.py`). Free-form prose is never parsed; the runtime shapes the reply and Pydantic then decides whether the shape means anything. One retry on malformed output, then a clear error.
- `temperature` 0.1 for extraction and review, 0.3 for Q&A. `num_ctx` 8192, and READMEs are truncated at ~6,000 characters at a single choke point so no call can overflow the window.
- `keep_alive` keeps the model warm between calls, because CPU inference is slow and a cold model makes the demo crawl.
- Seller text is labelled as **data, never instructions**, in all three system prompts. The model has no tools and no write access, so the worst case of a prompt injection in a README is a bad answer, not a bad action.

**Nothing load-bearing is delegated to the model.** Publishing requires a title, a price ≥ 0, a demo URL or a ZIP, and that the quality check has run — all plain code. Download requires a `paid` order or being the seller (403 otherwise). Ownership checks and draft visibility (404, not 403, so drafts aren't leaked) are plain code. The model drafts and grades; it never decides.

**Stack:** Python 3.10+, FastAPI, SQLModel + SQLite, Pydantic v2, `bcrypt` + PyJWT, `httpx`; Next.js App Router in JSX with plain CSS and no UI framework; a `PaymentProvider` interface whose mock is the default and whose Razorpay test-mode provider sits behind the same interface.

**The honest numbers.** On a CPU-only box with integrated graphics, `gemma4:e2b` drafts a listing from a README in about 6s and grades a weak listing in about 15s. Two model choices were made by measurement, not vibes: A1 and A2 are cached on the project row so a page view never re-runs inference, and A3 is public while A1/A2 need a login, because asking is part of browsing and spends far less CPU.

**And the parts that are small-model noise, written down rather than papered over.** An identical listing scored 75 and 85 on two runs. The grounding flag once returned "not in the listing" on an answer that correctly quoted the README — the prompt was tightened, and the flag is now right in testing, but it can still leak a JSON fragment into the prose. That is exactly why every AI output is advisory, visible and seller-editable, and why the rules the product depends on are deterministic.

**Verification, all re-run from the repo against a live server and a real browser:**

| Script | Result |
| --- | --- |
| `day1_check.ps1` | **19 / 19** — auth, publish gates, ownership, A1, A2 |
| `day2_check.ps1` | **28 / 28** — upload, gated download, A3, orders, filters |
| `ask_check.ps1` | **3 / 3** — grounding flag, answerable and not |
| `contrast.mjs` | **7 / 7** WCAG AA pairs from the design tokens |
| `ui_flow.mjs` | **33 / 33** — seller README → published listing, buyer asks → buys → downloads, non-buyer gets 403, driven through headless Chrome over the DevTools protocol |

One of those checks was fixed *because* the log was honest: the filter assertions in `day2_check.ps1` used `.Count` on a pipeline result, which is `$null` under PowerShell 5.1 when a filter yields exactly one object, so a "28/28" had been recorded that could not fail. The assertions were rewritten and the run repeated. That correction is left visible in `progress_tracker.md` rather than quietly re-run.

## Why Does Open Innovation Matter?

Five things were only possible because the weights are open and the runtime is local:

1. **The README is the product — and it never leaves the machine.** A seller's README and code *are* the asset being sold. Sending them to a hosted API would upload the thing they are about to charge for before a single sale. Running `gemma4:e2b` locally means that material is analysed on the same laptop, and the README is never rendered to the buyer at all — the buyer gets the AI's answer *about* it instead. Privacy here is a property of the architecture, not a line in a policy.
2. **The unit economics only close locally.** At ₹149–₹749 a listing, an inference bill on every draft, every quality check and every buyer's question would put a variable cost on *browsing itself*. Local inference makes the marginal cost of an AI call zero, with no keys, no quotas and no billing account to leak. The product shape changes when inference stops being a metered line item.
3. **The model is a swappable, pinned file, not an endpoint that can move under you.** One env var (`LAUNCHPAD_MODEL`) changes it. That is what let me compare models against the same fixture and write down the real numbers instead of a vendor's benchmark; on a hosted API that experiment becomes a release note.
4. **It works where students are.** College Wi-Fi, a hostel room, a demo hall with no reliable internet: the AI keeps working, because it isn't a network dependency. For this audience that isn't a nicety, it's the difference between shipping and not.
5. **Open tooling on both ends made the safety cheap.** Ollama's schema-constrained `format` is what makes a model this small usable in a pipeline rather than a toy, and Pydantic on the other side decides whether the shape is meaningful. Because both halves are open and inspectable, "never trust the model, fence it in, and keep every rule that matters in plain code" cost almost nothing to build — and is the reason a 2B-class model can sit under a marketplace at all.

## My Agent Session

<!-- TODO: save the session with DevRelay and embed it with the agent_session tag, or link to it -->

## My First User

<!-- TODO: keep only if someone actually used it — who they were, what they said, and whether they paid -->

## Prize Categories

<!-- TODO: list every partner category you are entering, or delete this section -->

<!-- Thanks for participating! -->
