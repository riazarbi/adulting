---
name: task-workflow
description: Handles the lifecycle of an action item — adding one, modifying an existing one, querying the list, reporting completion, and dropping one that was abandoned. Activate when an inbox message is an action item, a task modification, a task query, a completed-action report, or says a task is no longer happening.
---

# Skill: task workflow

The `tasks` tool description lists every subcommand, its arguments
and its flags. Read it there. This skill covers only the judgement:
how to turn what the owner said into the right call.

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

**Assignee** — leave it out. A task with no `(Name)` prefix is the owner's,
which is how nearly every task in the vault is written. Do not ask who
it is for, do not look him up, and do not write `(Sam Rivera)`.

Add a prefix only when someone *else* owes the action — "Jordan needs to
send me the accounts". Then it is `(Full Name)` from `people list`, and
if there is no match, load `create-person` first.

Then propose both steps together, execute both on one confirm, and
read the new uuid off the `ingested:` line of the flush output.
Relay it as `Added abcd1234.`

If flush prints `already a task: abcd1234` instead, the task was
already open and nothing was added. Relay it as
`Already a task: abcd1234.`

If flush prints `due updated: abcd1234 … due:2026-05-15 -> 2026-05-22`,
the task was already open with another due date, and flush moved it.
Nothing was added. Relay it as
`Already a task: abcd1234. Due date moved from 2026-05-15 to 2026-05-22.`

If flush prints `ambiguous: <thread>  <description>  matches abcd1234, ef567890`,
several open tasks differ from it only by due date. Nothing was added or
changed. Relay the uuids and ask which one the owner means; then
`tasks set-due` that one.

### Worked examples

Today is Friday 2026-05-08.

| The owner says | You send |
|---|---|
| I must buy tomatoes tomorrow morning | `["add", "Topics/Fitness", "Buy tomatoes", "--scheduled", "2026-05-09"]` |
| Send Jordan the Northwind monthly report by Friday | `["add", "Processes/Northwind", "Send Jordan Blake the monthly report", "--due", "2026-05-15"]` |
| Jordan needs to send me the management accounts by Friday | `["add", "Processes/Northwind", "(Jordan Blake) Send Sam the management accounts", "--due", "2026-05-15"]` |
| Urgent: file AFT trustee update by end of month | `["add", "Processes/Rivera Family Trust", "File trustee update", "--due", "2026-05-31", "--priority", "H"]` |

Jordan is the *recipient* in row two, so no prefix. He is the *actor*
in row three, so he gets one.

## Modifying a task

Find the uuid first — by prefix if the owner gave one, else `tasks list`
filtered by thread. Then use the matching `set-*` subcommand.

Two cases need judgement:

- **"Not yet, look at it later"** — there is no hold attribute. Use
  `set-scheduled`; the task drops out of `next` until that date. This is
  not `drop`: the task is still going to happen.
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

## Dropping a task

`drop` closes a task that is not going to happen. `done` closes one that
did. Never use `done` for an abandoned task: the record would say it
happened.

Drop when the owner says the task is off: "forget it", "cancel the
Northwind scope", "not doing that any more", "no longer needed", the
other party pulled out. If it is unclear whether it was done or abandoned
("that's off my plate"), ask. The two records say opposite things.

Find the uuid as for completion: by prefix if given, else `tasks list`
filtered by thread. If nothing matches, there is nothing to drop; say so.
Never add a task only to drop it.

`drop` records no reason. If the owner gives one worth keeping ("they
went with another firm"), propose a `buffer add-text` to the task's
thread alongside the drop, and run both on one confirm.

Relay it as `Dropped abcd1234.` If the output has
`still depended on by: ef567890  Invoice Northwind for scoping` lines,
those tasks were left alone. List them and ask, for each one, whether to
`rm-depends` it from the dropped task or drop it too. Change nothing
until the owner answers.

`drop` refuses a done task (`is done`) and `done` refuses a dropped one
(`was dropped`). Relay the error; the CLI cannot reverse either.
