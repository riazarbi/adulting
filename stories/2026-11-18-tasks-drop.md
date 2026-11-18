# `tasks drop`: close a task without saying it was done

## What is changing

Today a `TASK:` anchor can only leave the open list one way: `tasks done`,
which rewrites it to `DONE:` and stamps `end:`. A task that has been
abandoned — the client went elsewhere, the plan changed, it stopped
mattering — has two bad options: stay open forever and clutter `tasks list`
and `tasks next`, or be marked done and make the record lie. The second one
also inflates `tasks_done` in `search overview` and adds a false `done` event
to `search stream`.

After this change, `tasks drop <uuid>` rewrites the anchor to `DROPPED:` and
stamps `end:<today>`:

    $ tasks drop 1a2b
    dropped: 1a2b3c4d  Send Northwind the revised scope

    before: TASK: (Jordan Blake) Send Northwind the revised scope <!--1a2b3c4d entry:2026-10-02 due:2026-10-31-->
    after:  DROPPED: (Jordan Blake) Send Northwind the revised scope <!--1a2b3c4d entry:2026-10-02 end:2026-11-18 due:2026-10-31-->

The line stays where it is. Nothing is deleted: the vault still records that
the task existed, when it was taken on and when it was given up.

## Why a new keyword, not a flag on `DONE:`

`DONE:` with a `dropped` attr would keep the schema smaller, but every
reader that counts or renders `DONE:` today (search counts, the activity
stream, meeting-note rendering) would report a dropped task as finished
unless each one learned to look for the attr. A distinct keyword fails
safe: a reader that doesn't know `DROPPED:` ignores the line rather than
miscounting it. `drop` / `DROPPED:` mirrors `done` / `DONE:`.

## Behaviour

| Anchor is | `tasks drop` | `tasks done` |
|---|---|---|
| `TASK:` | → `DROPPED:`, `end:<today>`, prints `dropped:` | as today |
| `DROPPED:` | `<uuid> already dropped`, exit 0 | error: `<uuid> was dropped`, exit 1 |
| `DONE:` | error: `<uuid> is done`, exit 1 | `already done`, as today |

- `--dry-run` is refused, as it is for `done` and every subcommand but
  ingest.
- Exit codes and uuid-prefix resolution are `find_anchor`'s, as for every
  other mutation.

## Every reader of anchors

| Where | Change |
|---|---|
| `tasks` anchor regex, `task_anchor` schema | `kind` enum gains `DROPPED`; `kind=DROPPED` requires `end` |
| `log` schema | `DROPPED:` listed as a log line kind |
| `lint` | same `end` rule as `DONE` |
| `tasks list` / `next` | no change — they already show `TASK` only |
| `tasks show` | prints `kind: DROPPED` |
| `buffer flush` dedup | no change — it matches open `TASK`s only, so re-adding a dropped task creates a fresh task. That is the right outcome: picking it back up is a new commitment |
| `search stream` | a `DROPPED:` anchor emits `task` at `entry` and a new `dropped` event at `end` (not `done`); `dropped` joins `STREAM_KINDS` |
| `search overview` | new `tasks_dropped` count beside `tasks_open` / `tasks_done` |
| `search` log entry count (`ENTRY_RE`) | counts `DROPPED:` lines |
| `render` (meeting agenda / minutes) | action status `Dropped` |

Then: README `tasks` table, CHANGELOG, `dev/ci generate` for MANUAL and the
tool JSON.

## Tests

- drop an open task: keyword, `end:`, other attrs unchanged, line position unchanged
- drop is idempotent; drop on `DONE` and done on `DROPPED` refuse
- lint flags `DROPPED:` without `end`
- `search stream` emits `dropped`, not `done`; `search overview` counts it separately
- flush of an ACTION identical to a dropped task creates a new task

## Out of scope

- **Undo.** There is no `tasks reopen` for `DONE` either. If it is wanted,
  one command should handle both.
- **The agent's `task-workflow` skill** learning when to propose `drop`
  instead of `done`. That goes in its own story once this ships.

## Decisions

1. **No reason.** `drop` takes no `--reason` and the anchor carries no
   reason attr. If the reason matters, `buffer add-text` a `TEXT:` line to
   the thread's log.
2. **Dependents are printed, not changed.** Nothing in the CLI enforces
   `depends:`, so a task depending on a dropped one isn't blocked. After
   dropping, `drop` lists each open task whose `depends:` names the dropped
   uuid, one per line on stdout, and leaves them alone:

       dropped: 1a2b3c4d  Send Northwind the revised scope
       still depended on by: 5e6f7a8b  Invoice Northwind for scoping

   `rm-depends` or `drop` them yourself. Nothing printed when there are none.
   Only open (`TASK:`) dependents are listed.
3. **Name.** `drop` / `DROPPED:`.

Tests add: dependents listed after a drop; none listed when there are none.
