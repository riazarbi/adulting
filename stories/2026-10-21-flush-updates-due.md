# Flushing an ACTION that differs from an open task only by due date updates the due date

## What is changing

Today `buffer flush` (and so `tasks add`, which buffers an ACTION) drops an
ACTION that is a strict duplicate of an open task
([2026-09-23](2026-09-23-idempotent-task-flush.md)). An ACTION whose due date
differs is not a duplicate, so it becomes a second task.

After this change, an ACTION that matches an open task in everything **except
the due date** does not become a new task. Flush sets the open task's due date
to the ACTION's instead, and says so:

    due updated: 1a2b3c4d  /vault/threads/Projects/Northwind/logs/2026-09-20.md:7  Draft scope  due:2026-10-31 -> 2026-11-07

The reason: someone re-adding a task with a new date means "this is now due
then". Making them find the uuid and run `tasks set-due` asks them to read
the vault first, which the idempotent flush set out to avoid.

## Matching

An ACTION is a **due-only match** for an open task when every field of the
2026-09-23 strict identity is equal except `due`: threads, assignee,
description, priority, scheduled and depends (as a set).

The ACTION's due date must be set and must differ from the task's:

| Task's due | ACTION's due | Result |
|---|---|---|
| `2026-10-31` | `2026-10-31` | strict duplicate: `already a task:` (as today) |
| `2026-10-31` | `2026-11-07` | `due updated:` |
| none | `2026-11-07` | `due updated:` (`due:- -> 2026-11-07`) |
| `2026-10-31` | none | `already a task:` (see open question 1) |

## Output

`due updated:` is a result, like `already a task:`. It goes to stdout, beside
the skip lines, regardless of `--quiet`, and flush exits 0. Its location is
the anchor's, built with `V.where`.

Nothing is written to the daily log for an update, as `tasks set-due` writes
nothing today. The ACTION is dropped from the flush like a skipped one.

## Boundaries

All boundaries from 2026-09-23 hold: only open tasks count, only `buffer
flush`, multi-thread notes and unreadable files are not seen, un-ingested
ACTIONs in logs are not checked.

- **A strict duplicate wins.** If any open task matches exactly, the ACTION
  is `already a task:`, even if another open task is a due-only match.
- **Only due.** A difference in `scheduled`, priority or anything else still
  makes a new task.
- **The anchor is rewritten in place** with `mutate_anchor`, as `set-due`
  does. The uuid and entry date stay.

## Decisions

Agreed 2026-10-21.

1. **ACTION with no due, task with one:** `already a task:`. Re-adding
   without a date does not clear a date.
2. **Several open tasks are due-only matches** (e.g. the same task added
   twice by hand with different dates): update none, add none, and print
   `ambiguous: <thread>  <description>  matches <uuid>, <uuid>` on stdout,
   exit 0. If one of them has the ACTION's due date exactly, it is
   `already a task:` for that one instead.
3. **Two ACTIONs in one flush differ only by due:** they collapse to one
   with the latest (by buffer timestamp) due date given; the others print
   `already buffered:`. An ACTION with no due date never wins over one with
   a date, as in 1. Among those with the winning date, the first is kept,
   as identical ACTIONs are today. The one kept is then matched against
   the open tasks as above.
4. **Order of writes:** anchor updates happen after tend passes and before
   the logs are written, with the same non-atomic crash caveat as today.

## Cost

None beyond today's pass: `tasks.identity` drops `due`, and `open_tasks()`
keeps every anchor per identity, so one lookup finds the exact twin, the
due-only twin, or several.

## Done when

- The table and boundaries above are covered by tests that fail without the
  change, using the test names (`SQR`, `Remy Dorn`, …).
- `buffer flush` help names `due updated:`; `MANUAL.md` and
  `dev/tools/buffer.json` regenerated; `dev/ci` passes.
- README's "Flush is idempotent for tasks" bullet and CHANGELOG updated.

## The agent

In scope, at the owner's request. `task-workflow` relays `due updated:` as
`Already a task: abcd1234. Due date moved from <old> to <new>.`, and on
`ambiguous:` relays the uuids, asks which is meant, and runs `tasks
set-due` on that one.
