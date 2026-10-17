# AGENT.md — working rules for this repository

## Prime directive

`plan.md` is the only source of truth for what to build. `Progress.md` is the only
source of truth for what has already been built.

**Never start a new plan step without first reading `plan.md` and updating
`Progress.md`.** This applies to every session, including sessions that appear to
continue earlier work.

## Required loop

Repeat this for every single step in `plan.md`:

1. **Read `plan.md`.** Identify the next incomplete step — the earliest task whose
   row in `Progress.md` is not `Done`.
2. **Read `Progress.md`.** Confirm that step is genuinely next. Never reorder steps,
   skip ahead, or work in parallel on a later step.
3. **Mark it `In progress` in `Progress.md` *before* writing any code.** This is the
   gate: no edits happen until the step is recorded as started. Include the date and
   the files you expect to touch.
4. **Do the work.** Stay inside the "Files touched" list for that step. If the work
   needs a file outside that list, stop and ask the user first.
5. **Run that step's manual check.** Acceptance in this project is manual only.
   Record the exact command run and its observed output.
6. **Mark the step `Done` (or `Blocked`) in `Progress.md` *before* moving on.**
   Include: status, files changed, the manual check command, the observed result, and
   any deviation from `plan.md`.

If a step fails its manual check, leave it `In progress` or mark it `Blocked` with the
reason. Do not start the next step to "come back to it later".

## Progress.md format

Keep one table plus a dated log. Update in place; do not rewrite history.

```markdown
# Progress

Current step: <Day N, Task N.M — title>
Status: <Not started | In progress | Done | Blocked>

| Day | Task | Status | Files | Manual check result |
| --- | ---- | ------ | ----- | ------------------- |
| 1 | 1.1 Local environment | Not started | | |

## Log

### <YYYY-MM-DD> — Day N Task N.M — <title>
- Status:
- Files changed:
- Manual check: `<exact command>`
- Observed:
- Deviation from plan.md:
```

At the start of a session, print the current step and the top of the table so the
user can see where the project stands.

## Scope rules

- **Frozen scope.** Build only what `plan.md` lists. The "Out of scope" section of
  `plan.md` is a hard no: no patch generation, Tree-sitter, embeddings,
  multi-language support, persistence, pricing features, test suite, or CI.
- **Ask before adding anything** not already in `plan.md` — a feature, endpoint,
  file, dependency, or config knob. Log the answer in `Progress.md`.
- **Never crash** is a product requirement, not a nicety. A bad diff, a malformed
  model reply, an unindexed `/ask`, or a dead Ollama must degrade into a reported
  reason with an HTTP 200.
- **Do not write code files** unless the user has explicitly asked for implementation
  in this session. `plan.md`, `AGENT.md` and `Progress.md` are documentation and are
  always fair game.

## Editing rules

- Do not reformat, reorganize, or "clean up" files unrelated to the current step.
- Do not touch existing user work without asking.
- Commit at each day's exit criteria, not per file.

## Reporting

When reporting the outcome of a step, state plainly:
1. Which step it was.
2. What changed, by file.
3. The exact manual check command and its actual output.
4. Anything that deviates from `plan.md`, and what you did about it.
