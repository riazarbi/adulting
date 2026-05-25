# Skill: task workflow

Loaded when an inbox message is an action item, a task modification,
a task query, or a completed-action report.

The single creation path is **`tasks add`** (delegates to
`buffer add-action`, which buffers a structured ACTION line that
becomes a real backend task on next ingest). All other lifecycle
operations go through `tasks <subcommand>`.

## Add a task

Compose:

- **Thread** — `Kind/Name`, resolved per the role prompt's rules
  (`Projects/SGB`, `Processes/Arbi Family Trust`, etc.).
- **Description** — imperative form. Strip out date phrases (they go
  in `--due` / `--scheduled`) and thread hints (already in the thread
  arg). Don't put bare `key:value` colons in the description.
- **`(Full Name)` prefix** — only when the actor isn't Riaz. Default
  actor is Riaz (no prefix). Full name must match an existing
  `~/vault/people/<Name>.md`. If no match, see `create-person`
  skill before adding.
- **`--due` / `--scheduled`** — ISO date `YYYY-MM-DD` only. Resolve
  any named/relative phrase yourself first using today's system date.
  - **due**: hard deadline. "by Friday", "before end of month".
  - **scheduled**: when Riaz plans to start, no hard deadline.
    "tomorrow morning", "in two weeks", "remind me Monday".
  - When unsure between due and scheduled, **prefer scheduled** —
    less aggressive; he can upgrade later.
- **`--priority H|M|L`** — only when explicitly hinted (urgent, low
  priority, can wait).

Propose:

```
Going to: tasks add <thread> "<text>" [--due ...] [--priority ...]
          then buffer flush

OK?
```

On confirm, run two tools in sequence (one confirm covers both):

1. `tasks ["add", "<thread>", "<text>", "--due", "<date>", ...]` — buffers the action.
2. `buffer ["flush"]` — writes to logs/, auto-runs ingest, creates the
   backend task. The output of this call contains the new 8-char uuid
   on the `ingested: <uuid>  ...` line.

Parse the uuid from the flush output and relay: `Added abcd1234.`

Why two steps: `tasks add` is the validated capture (returns
"buffered: ..."); `buffer flush` is the commit (writes to logs/ and
ingests into the backend). The buffer is a queue you can review with
`buffer list` and amend with `buffer rm` before flushing.

### Examples

(Assume today is `2026-05-08` (Friday). Recompute from system date.)

- `I must buy tomatoes tomorrow morning` →
  `tasks ["add", "Topics/Wellness", "Buy tomatoes", "--scheduled", "2026-05-09"]`
- `Send Bern the SGB monthly report by Friday` →
  `tasks ["add", "Processes/SGB", "Send Bern Sellmeyer the monthly report", "--due", "2026-05-15"]`
  (Bern is *recipient* in the description; actor is Riaz; no `(...)` prefix)
- `Bern needs to send me the management accounts by Friday`
  (`Bern Sellmeyer.md` exists) →
  `tasks ["add", "Processes/SGB", "(Bern Sellmeyer) Send Riaz the management accounts", "--due", "2026-05-15"]`
- `Urgent: file AFT trustee update by end of month` →
  `tasks ["add", "Processes/Arbi Family Trust", "File trustee update", "--priority", "H", "--due", "2026-05-31"]`

## Modify a task

For changes to an existing pending task — re-date, re-prioritize,
hold, depends.

Use the right subcommand:

- `tasks set-due <uuid> <YYYY-MM-DD>` — change deadline.
- `tasks set-scheduled <uuid> <YYYY-MM-DD>` — change start date.
- `tasks set-priority <uuid> <H|M|L>` — change urgency.
- `tasks set-description <uuid> "<text>"` — rewrite description.
- `tasks set-assignee <uuid> "<Full Name>"` — change actor prefix.
- `tasks add-depends <uuid> <dep-uuid>` — block on another task.
- `tasks rm-depends <uuid> <dep-uuid>` — remove a blocker.

Identify the subject task first — by uuid if given, else
`tasks list` (with thread or grep filter) to find one. UUIDs are
stable; numeric IDs aren't — always use 8-char uuid prefix.

### Hold vs. block

- **Time-based hold** — currently no `set-wait` (the backend has
  `wait:` but we don't expose it yet). Use `set-scheduled` instead;
  the task hides from `next` until that date.
- **Blocked on another task** — `tasks add-depends`. If "I can't do
  X because I'm waiting on Y, will check Y at time T":
  1. Add a new pending task for Y (with `--scheduled T`).
  2. `tasks add-depends <X-uuid> <Y-uuid>`.
  Both proposed in one block, executed in order on confirm.

### Examples

- `Push the tax returns to next month` →
  Find tax-returns uuid → `tasks ["set-due", "<uuid>", "2026-06-08"]`.
- `I can't do tax returns; waiting on accountants. Check next week.` →
  1. `tasks ["add", "Processes/Arbi Family Trust", "Check on accountants for management accounts", "--scheduled", "2026-05-15"]`
     → captures new uuid (call it `Y`).
  2. `tasks ["add-depends", "<X>", "<Y>"]`
- `Tax returns are urgent` →
  `tasks ["set-priority", "<uuid>", "H"]`

## Query tasks

Read-only — **no confirm**, just run.

- "what's my next task" → `tasks ["next"]`
- "what's my next SGB task" → `tasks ["next"]`, then filter the
  output (or use `tasks ["list", "--thread", "Processes/SGB"]`).
- "list my SGB tasks" → `tasks ["list", "--thread", "Processes/SGB"]`
- "what's overdue" → `tasks ["list", "+OVERDUE"]`

Resolve thread abbreviations against `threads/{Projects,Processes,Topics}/`
before filtering. Reformat output per the role prompt's mobile rules
(bullet list with 8-char uuid prefix, never raw column output).

## Report a completed action

When Riaz reports something is done:

1. **By uuid** ("task abcd1234 done") → propose
   `tasks done abcd1234`. On confirm:
   `tasks ["done", "abcd1234"]`. Reply: `Done.`

2. **By description** ("I bought the tomatoes", "called Bern this
   morning") → `tasks list` (with thread filter if available) to
   find a matching pending task.
   - **Match** → propose `tasks done <uuid>` and confirm.
   - **No match** → propose adding it as already-done. Note: we
     don't yet have an `--done` flag on `tasks add`. Until we do,
     two-step: `tasks add ...` (new task), then `tasks done <uuid>`.
     Propose both steps in one block, executed sequentially.

Prefer `tasks done` whenever a matching pending task exists — keeps
the original record clean rather than duplicating it.
