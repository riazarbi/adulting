---
name: time-workflow
description: Records and reports time spent against a thread, billable or not — logging a session, correcting an entry, and totalling hours for a period. Activate when Riaz reports time spent ("spent 90 minutes on the SGB contract", "an hour reading this morning") or asks how much time went somewhere. For money received or statements of account, use billing-workflow.
---

# Skill: time workflow

For time spent — client work and personal alike. The `hours` tool
description carries the subcommands and flags; this is the judgement
around them.

Whether a thread is billable is a property of the thread, not of the
request. A thread with a currency is billed at its rate; one without
records the time as unbilled. Either way you log it the same way, so
never ask Riaz whether something is billable and never pass `--rate`
to force it — the thread already knows.

## Logging a session

**Always pass the thread.** `hours log` with no thread exits with an
argparse error and records nothing. Resolve the thread against
`threads list` first.

Compose three things:

**Description** — on a billable thread this becomes a line item on
an invoice, so write it for the client to read: "Reviewed and marked
up the vendor contract", not "contract stuff". Imperative past
tense, specific about what was produced. On a personal thread the
same standard is still worth keeping — it is what makes a month of
entries readable later.

**Duration** — `-m` in minutes, default 60. Convert "an hour and a
half" to `-m 90` yourself.

**Date and time** — default to now. Pass `-d` only when he is
logging something from an earlier day, `-t` only when the start time
matters.

Leave rate and currency alone. They come from the thread, and the
entry stores whatever was current when it was written — which is why
back-dating a rate change never re-prices logged work.

`-r 0` is for the exception: work on a *billable* thread that Riaz
is not charging for — goodwill, a write-off, internal time. The
hours still count, the money is zero. Don't reach for it on a thread
that has no currency; those are already unbilled.

Propose, then on confirm log it and relay the entry id.

## Correcting an entry

Find the id with `hours list <thread>`, then `hours edit`. The
common corrections are a mis-estimated duration and a description
that reads badly on an invoice.

`hours rm` is blocked for you. A wrong entry is corrected with
`edit`, not deleted — the record of the work stays, the numbers get
fixed. If Riaz genuinely wants an entry gone, say it needs doing by
hand and leave it.

## Reporting

Read-only — no confirm.

- "How much time on SGB this month" → `hours report --thread ...`
  with `--since` and `--until` bounding the month.
- "What did I do on SGB in June" → `hours list` over the same range,
  which gives the individual entries rather than the totals.

Compute the month boundaries yourself from today's date. Report
totals per currency — never add two currencies together, and keep
the unbilled total as its own line rather than folding it in.

## Example

> Spent an hour and a half reviewing the SGB vendor contract

→ `["log", "Projects/SGB", "Reviewed and marked up the vendor contract", "-m", "90"]`
