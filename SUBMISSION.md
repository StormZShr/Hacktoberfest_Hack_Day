# RepoPilot AI — code review that runs on your laptop, not someone else's GPU

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 2: Side Hustle](https://dev.to/challenges/hacktoberfest-week2-2026-10-12)*

## What I Built

[RepoPilot AI](https://github.com/StormZShr/Hacktoberfest_Hack_Day) is a local-first code review assistant. You paste a unified `git` diff, and a small open-weight model running in Ollama on your own machine reviews every changed file: real defects only, each cited to its line number in the **new** version of the file, ranked high → medium → low.

**Who pays for it.** Freelancers and small teams working under NDA. Every hosted review tool means uploading a client's source to someone else's servers, holding an API key, and paying per token. RepoPilot has no API key, no per-token bill and no upload — the code never leaves the laptop, and it keeps working offline. A one-time local setup replaces a monthly SaaS line item, and "review every commit, not just the ones you can afford" becomes affordable.

The design constraint I built the whole thing around is boring but decisive: **it never crashes.** A malformed model reply, a truncated diff, or a dead Ollama must not produce a 500. It produces an entry in a `skipped` list with a human-readable reason, and the request still returns HTTP 200. Silently dropping a file is worse than reporting a bad finding.

```
$ POST /review  {"diff": "<samples/buggy.diff>"}
200 OK   (trimmed)
{
  "findings": [
    {
      "file": "config.py",
      "line": 10,
      "severity": "high",
      "title": "Division by zero when idx is 0",
      "explanation": "DEFAULT_TIMEOUT / idx will raise ZeroDivisionError on the first iteration.",
      "suggestion": "Guard with `if idx == 0: continue` or divide by `idx + 1`."
    }
  ],
  "skipped": [],
  "files_reviewed": 2
}
```

And the same endpoint on input it can't use:

```
$ POST /review  {"diff": "not a diff at all"}
200 OK   {"findings": [], "skipped": [], "files_reviewed": 0}

$ POST /review  {"diff": "<diff deleting gone.py>"}
200 OK   skipped: [{"file": "gone.py", "reason": "file deleted, nothing new to review"}]
```

## Demo

<!-- TODO: paste your demo video / GIF link here, or write up the two-tab walkthrough -->

Terminal demo today, because the fastest way to prove the riskiest part was to keep HTTP and the UI out of the loop entirely:

```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn main:app --port 8000
# then, in another shell:
.venv\Scripts\python -c "import json,httpx,pathlib; d=pathlib.Path('samples/buggy.diff').read_text(); r=httpx.post('http://127.0.0.1:8000/review', json={'diff':d}, timeout=600); print(r.status_code); print(json.dumps(r.json(), indent=2))"
```

`samples/buggy.diff` is a fixture seeded with nine known defects (hardcoded secret, `open()` without `with`, a zero-length division, a mutable default argument, `== None`, a bare `except: pass`, a delete-before-read `KeyError`, and two more) — so this is an acceptance test, not a smoke test.

## Code

Repository: **https://github.com/StormZShr/Hacktoberfest_Hack_Day**

Backend files that matter: `backend/main.py` (the two endpoints), `backend/diffparse.py` (diff → per-file new-file line numbers), `backend/llm.py` (Ollama client), `backend/schemas.py` (Pydantic models + the JSON schema).

```
backend/   main.py  diffparse.py  llm.py  schemas.py  samples/buggy.diff
frontend/  Next.js UI (Review tab + Ask tab)   <- in progress
```

## How I Built It

**Compute: local Ollama, open weights, no SDK.** `llm.py` is ~100 lines of `httpx` against `POST /api/chat`. Three calls pin the behaviour:

- `format` = a **hand-written flat JSON Schema**. I deliberately did not use `FileFindings.model_json_schema()`, because the generated version leans on `$defs`/`$ref` and is harder for the grammar converter to handle.
- `options = {"temperature": 0.1, "num_ctx": 8192}` — repeatable findings, and a chunked file fits without silent truncation.
- `CHAT_TIMEOUT = 180s`, and all four failure modes (connect error, timeout, HTTP error, non-JSON body) are **returned as values**, not raised.

**Diff parsing without a parser library.** `diffparse.py` walks the unified diff and rebuilds new-file line numbers from the `@@ -old +new @@` headers. Only added and context lines exist on the new side; a removed line has no new-file number, so it's dropped rather than guessed. Two safety caps: 400 injected lines per file and 10 files per review, because a huge diff should not queue half an hour of CPU inference. Anything unparseable becomes a `skip_reason`, never an exception.

**Never-crash, enforced at the seam.** Every model reply is validated against Pydantic at the boundary. On failure the file is appended to `skipped` with the reason `model output failed schema validation` and the loop continues. Deterministic post-processing then repairs what it can: the parsed path is trusted over whatever path the model echoed, and each `line` is clamped into `1..max_line` so a hallucinated line number can't escape the file the model was actually shown.

**The honest numbers, because this is the part most demos skip.** On a CPU-only box with integrated graphics, `qwen2.5:3b` (the *general* instruct model) diagnosed **0 of 9** seeded defects in 59s for two files — right regions, invented explanations, everything labelled `high`. Swapping only the `REPOPILOT_MODEL` environment variable to `gemma4:e2b` moved that to **7 of 9** correctly diagnosed, all on the correct lines, in 180s for two files (~90s/file, still inside the timeout). Missed: an off-by-one `return limit` instead of `times`, and `== None` instead of `is None`. No code changed between those two runs — that is the argument for keeping the model behind an env var.

**Acceptance is manual by design.** There is no test suite, by choice: each step in `plan.md` has an exact command and its observed output recorded in `Progress.md`, including the failure cases. That log is the most useful artifact here — it is where the 0/9 versus 7/9 result is written down next to the command that produced it.

## Why Does Open Innovation Matter?

Four things were only possible because the weights are open and the runtime is local:

1. **The model is a swappable, pinned artifact.** `qwen2.5-coder` is Apache-2.0 (the Gemma family ships under its own Gemma licence — worth checking before you redistribute). Because they're files on disk, I can pin an exact revision, diff two models against the same fixture, and report 0/9 versus 7/9 with no risk that the endpoint silently changes under me. A closed API turns that experiment into a vendor announcement.
2. **No API key means no per-token decision.** "Review every changed file in every commit" is an economically absurd feature on a metered API and a free one locally. The whole product shape changes when inference cost stops being a variable.
3. **Privacy is a property, not a promise.** There is no upload path in the code. For a freelancer who cannot paste a client's code into a web form, that isn't a nice-to-have — it's the difference between shipping and not.
4. **Small models + structured output = reliable components.** Ollama's schema constraint is what makes a 2B-class model usable in a pipeline instead of a toy: the reply is *shaped* correctly by the runtime, and Pydantic then decides whether the shape is meaningful. Open tooling on both ends of that contract is what made the never-crash guarantee cheap to implement.

## My Agent Session

<!-- TODO: save your session with DevRelay and embed it with the agent_session tag, or link to it -->

## My First User

<!-- TODO: only keep this section if someone actually used it. Who, what they said, did they pay. Delete otherwise. -->

## Prize Categories

<!-- TODO: list every partner category you're entering, or delete this section -->

<!-- Thanks for participating! -->
