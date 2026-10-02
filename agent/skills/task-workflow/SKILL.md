---
name: task-workflow
description: Handles the lifecycle of an action item — adding one, modifying an existing one, querying the list, and reporting completion. Activate when an inbox message is an action item, a task modification, a task query, or a completed-action report.
---

# Skill: task workflow

The `tasks` tool description lists every subcommand, its arguments
and its flags. Read it there. This skill covers only the judgement:
how to turn what Riaz said into the right call.

## Adding a task

Two tools, one confirm. `tasks add` queues the action in the buffer;
`buffer flush` writes it to the log and turns it into a tracked task.
Neither alone is enough.

Compose four things:

**Thread** — required. Resolve to `Kind/Name` via `threads list`.

**Description** — imperative, grammatical. Strip out the date words
and the thread hint; both are carried elsewhere in the call.

**Dates** — pass these as flags. Never write `due:2026-05-13` into
the description text: it stays there as dead words, and the task
then never appears in `tasks list --overdue`.
- `--due` — when it must be finished. "by Friday", "end of month".
- `--scheduled` — when he plans to start. "remind me Monday".
- Unsure which? Ask. It is the one ambiguity worth a question.
- Resolve "tomorrow", "next week" yourself against today's date.

**Assignee** — leave it out. A task with no `(Name)` prefix is Riaz's,
which is how nearly every task in the vault is written. Do not ask who
it is for, do not look him up, and do not write `(Riaz Arbi)`.

Add a prefix only when someone *else* owes the action — "Bern needs to
send me the accounts". Then it is `(Full Name)` from `people list`, and
if there is no match, load `create-person` first.

Then propose both steps together, execute both on one confirm, and
read the new uuid off the `ingested:` line of the flush output.
Relay it as `Added abcd1234.`

### Worked examples

Today is Friday 2026-05-08.

| Riaz says | You send |
|---|---|
| I must buy tomatoes tomorrow morning | `["add", "Topics/Wellness", "Buy tomatoes", "--scheduled", "2026-05-09"]` |
| Send Bern the SGB monthly report by Friday | `["add", "Processes/SGB", "Send Bern Sellmeyer the monthly report", "--due", "2026-05-15"]` |
| Bern needs to send me the management accounts by Friday | `["add", "Processes/SGB", "(Bern Sellmeyer) Send Riaz the management accounts", "--due", "2026-05-15"]` |
| Urgent: file AFT trustee update by end of month | `["add", "Processes/Arbi Family Trust", "File trustee update", "--due", "2026-05-31", "--priority", "H"]` |

Bern is the *recipient* in row two, so no prefix. He is the *actor*
in row three, so he gets one.

## Modifying a task

Find the uuid first — by prefix if Riaz gave one, else `tasks list`
filtered by thread. Then use the matching `set-*` subcommand.

Two cases need judgement:

- **"Not yet, look at it later"** — there is no hold attribute. Use
  `set-scheduled`; the task drops out of `next` until that date.
- **"Blocked on something else"** — add the blocking task first,
  then `add-depends` the blocked one on it. Propose both, execute in
  order.

## Querying

Read-only. No confirm — call it and relay the real output, formatted
per the role prompt's mobile rules.

"What's next" → `next`. "What's overdue" → `list --overdue`.
Anything thread-specific → `list --thread <Kind/Name>`, resolving the
abbreviation via `threads list` first.

## Reporting completion

Given a uuid, propose `done` against it.

Given a description ("I bought the tomatoes"), find the pending task
with `tasks list` and propose `done` on the match. Prefer this over
adding a new record — it keeps the original history intact.

Only if nothing matches: add the task, then mark it done. Two steps,
one proposal.
