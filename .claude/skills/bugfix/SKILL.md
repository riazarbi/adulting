---
name: bugfix
description: Disciplined bug-fixing workflow for this repo. Use when the user reports broken behavior, wrong output, or an unexpected error in one of the tools (tasks, buffer, notes, threads, people, lint, agent-build) and wants it diagnosed and fixed. Enforces reproduce-before-edit, observation-validated theory, smallest-scoped fix, regression coverage when a test suite exists, CI gating when CI exists, and probe cleanup. Skip for feature requests, refactors, or questions that aren't defect reports.
---

# Bugfix

A defect report is a claim about reality. Your job is to turn it
into a justified, durable fix without making the codebase worse on
the way through.

The default footing is **diagnose before mutating**. Don't reach for
Edit/Write until you can name the root cause and predict, in one
sentence, what changing it will do.

## Phases

Each phase has an exit condition. Don't advance until it's met.

### 1. Reproduce

Confirm the bug is real and your understanding of it matches the
report. Run the exact command/path the user named; capture actual
output beside expected.

**Exit:** you can point at the wrong behavior in a tool result, not
just describe it in prose. If the bug doesn't reproduce, say so and
ask for the missing context — don't fabricate a likely repro.

### 2. Form a theory

Trace the path from input to wrong output. Read the code on that
path; don't skim. Note where data is transformed, dropped,
defaulted, or split between sources.

Write the theory as one sentence with a falsifiable shape:

> *"Thread is missing from `tasks next` because <X> reads from
> <field A>, but ACTION-captured tasks store the thread in
> <field B>."*

Multiple plausible theories? Pick the most likely one, keep the
rest as a short list. Validation will eliminate.

**Exit:** you can name the specific function/file/line where the
divergence happens, and the theory is concrete enough to be wrong.

### 3. Validate the theory

Before editing, prove the theory by **observing** the divergence —
not by guessing what a fix would look like.

Cheapest first:

- Inspect the live data: read the actual on-disk records the bug
  involves (e.g., `tasks show <uuid>`, the source note frontmatter,
  the buffer line). Confirm field B holds what you think and field A
  is empty (or vice versa).
- If on-disk inspection is ambiguous, add a temporary `print` or
  small probe script and run it. **Mark probes clearly** so you
  can delete them in cleanup.
- Run a focused command (`tasks list`, `tasks show <uuid>`,
  `buffer list`) that surfaces the relevant fields.

If observation contradicts the theory: discard it, return to
step 2. Don't bend the theory to fit.

**Exit:** you have concrete evidence (a value, an empty field, a
log line) that confirms the named cause.

### 4. Act

Now write the fix. Keep it scoped to the root cause:

- **Smallest change that addresses the cause.** Don't bundle
  refactors, renames, or adjacent cleanup.
- **No defensive scaffolding for hypothetical adjacent bugs.** If
  the fix exposes a related issue, surface it separately — don't
  silently patch.
- **Match existing style.** Same parsing helper, same field-access
  pattern, same naming.
- **Confirm before mutating** when the fix touches behavior the
  user might want to weigh in on (changing a precedence rule,
  picking which field becomes canonical). For a clear
  field-plumbing bug with one obvious fix, just apply it.

**Exit:** the originally failing command now produces the expected
output, and you've eyeballed no obvious adjacent regressions.

### 5. Regression coverage *(when a test suite exists)*

This repo has no automated tests yet (see `TODO.md` — "smoke test
suite"). When tests exist:

- Add a test that **fails on the unpatched code** and **passes
  with the fix**. Run it both ways to prove this.
- Prefer an edge-case test at the boundary that broke (the
  specific capture path, the specific field combination) over a
  broad end-to-end test.
- Place it next to similar tests; don't invent a new harness.

Until smoke tests exist here, the substitute is a documented
manual repro: state in the response the exact command sequence
that demonstrates the fix. The user can replay it if regression
risk arises later.

### 6. CI gate *(when one exists)*

This repo has no CI yet. When CI exists:

- The suite **must pass on the unfixed branch before the fix**
  (baseline) and **after the fix**. If it was already failing,
  understand why before adding more changes on top.
- Don't bypass hooks (`--no-verify`, `--no-gpg-sign`) to land a
  fix. A failing hook is signal, not friction.

### 7. Cleanup

Before reporting done:

- Delete temporary probes, debug prints, scratch files.
- Revert any unrelated edits you made while exploring.
- Re-run the original repro one more time on the cleaned tree.
- If the bug was caused by drift between two representations
  (source note <-> tw task, buffer line <-> log file), check
  whether existing records on disk are stuck in the broken state
  and need a one-shot repair — flag it, don't silently rewrite
  history.

**Exit:** `git diff` shows only changes that directly support the
fix, plus (when relevant) the new regression test.

## Reporting

When relaying back:

- One line on the root cause.
- One line on what changed.
- The manual repro command (or test name) that demonstrates the
  fix.
- Any follow-ups you deliberately did **not** bundle.

## Anti-patterns

- **Patching the symptom.** Suppressing a missing-field warning
  rather than figuring out why the field is missing. The symptom
  comes back wearing different clothes.
- **Speculative fixes.** "This might also be involved, let me
  change it too." Either it's on the proven causal path or it's
  out of scope.
- **Skipping repro because the cause looks obvious.** Code reading
  is theory; running the command is fact.
- **Editing backend state directly to "fix" bad data.** The source
  of truth is the note (`ACTION:`/`TASK:` lines) and the buffer;
  mutating the backend out-of-band bypasses ingest and creates fresh
  drift. Use `tasks <subcommand>` (or `tasks rebuild`) to drive
  changes from source.
- **Leaving probes behind.** A stray `print(...)` in committed
  code is a sign the bugfix loop didn't finish.
