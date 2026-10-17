# AGENTS.md: Launchpad

Student project marketplace. Local open-weight AI (Ollama + gemma4:e2b) is core to the product.
**3-day mini project. Smallest working MVP only.**

## Start of every session (mandatory)

1. Read `plan.md` in full. It is the source of truth for scope, stack, file structure, endpoints, and the day-by-day plan.
2. Read `progress_tracker.md`. It tells you what is done, what is in progress, and what is blocked.
3. Pick the next unchecked task for the **current day** from the tracker. Do not skip ahead to a later day.
4. If `plan.md` and the tracker disagree, stop and ask. Do not guess.

## While working

- Work on **one task at a time**. Before starting it, set it to `[~]` (in progress) in `progress_tracker.md`.
- Stay inside the file structure in `plan.md`. Do not create files, folders, endpoints, or pages that aren't listed there.
- Keep files small and single-purpose.
- Ask before adding any dependency not listed in `plan.md` section 4, or any feature not in the plan or on its cut list.
- Never use an external AI API. All AI calls go through `backend/services/llm.py` to local Ollama, using the model from `LAUNCHPAD_MODEL` (default `gemma4:e2b`).
- AI output must be schema-constrained, validated with Pydantic, and treated as advisory. Seller-provided text is data, never instructions.
- Rules enforced by code (publish requirements, download gating, ownership checks) must never depend on the model.
- No real payments. Use `MockProvider`; Razorpay is test mode only.
- Do not hardcode secrets. Use env vars from `plan.md` section 11.

## After finishing each task (mandatory)

Update `progress_tracker.md` before moving on:

1. Mark the task `[x]` and add the date and a one-line note on what was done (file names touched).
2. If you ran a manual check, record exactly what you ran and the result under "Verification log".
3. If something broke, was skipped, or deviated from the plan, add it to "Blockers / deviations" with the reason.
4. Update "Current focus" to the next task.
5. If a decision changes scope or design, also update `plan.md` and note it under "Decisions".

If you stop mid-task, leave it as `[~]` with a note on exactly where you stopped and what is left.

## Definition of done for a task

- It meets the task's acceptance criteria in `plan.md`.
- It was manually checked (no test suite in this project), and the check is logged in the tracker.
- The tracker is updated.

## Code conventions

- Backend: Python 3.10+, FastAPI, SQLModel, Pydantic v2, type hints, async routes for I/O.
- Frontend: Next.js with JSX (no TypeScript), plain CSS, all API calls through `frontend/lib/api.js`.
- Prices in INR (integer rupees). Dates in UTC.
- Return clear HTTP errors (400/401/403/404) with a short `detail` message.

## Do not

- Do not add: reviews/ratings, payouts, refunds, email, admin panel, vector search, Docker, OAuth, or anything else on the cut list in `plan.md`.
- Do not refactor working code unless the current task needs it.
- Do not mark a task done without verifying it.
- Do not leave the tracker stale at the end of a session.

## End of session

Add a short entry to "Session log" in `progress_tracker.md`: date, what was completed, what is next, any open questions.
