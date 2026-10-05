# Flushing an ACTION that is already an open task does nothing

## What is being added

`buffer flush` skips a buffered ACTION that is a strict duplicate of an open
task. It writes no log line for it, so the ingest makes no new anchor. It says
so and still succeeds:

    already a task: 1a2b3c4d  /vault/logs/Projects/SGB/2026-09-20.md:7  Draft scope

This is the default. There is no flag.

The reason: whoever adds a task should not have to read the vault first to
find out whether it is already there. Adding a task that is already open
should leave the vault as it was.

## Strict identity

An ACTION duplicates a task only when every one of these is equal, compared
exactly (case, spacing and all):

- **Threads.** The anchor's file threads must be exactly `[<the ACTION's
  thread>]`. A matching task in a note with several threads does not count.
- **Assignee.** Both have none, or both have the same one.
- **Description.**
- **Priority, due, scheduled.** Each is the same, or both lack it.
- **Depends.** The same set of uuids. Order does not matter.

The entry date and the uuid are not compared. An ACTION buffered with
`--date` is a duplicate of the same task whatever day it is filed under.

## Output

A skip is a result, not a problem, so it is reported where `ingested:` lines
are: on stdout. A flush that skips writes nothing to stderr for it, and exits
0.

The two skip lines have the shape of the `ingested:` line, and their location
is an absolute path built with `V.where`, as every location in output is:

    already a task: <uuid>  <abs path:line of the anchor>  <description>
    already buffered: <thread>  <description>

`already buffered` has no location: flush clears the buffer, so a buffer line
number would point at nothing.

`--quiet` treats skip lines as it treats `ingested:` lines. Today flush prints
the ingest report regardless of `--quiet` (`buffer.py`, after
`write_buffer([])`), so skip lines are printed regardless too.

## Boundaries

- **Only open tasks count.** A DONE twin does not block, so a recurring chore
  can be added again.
- **Only adding a task.** The commands that change a task are idempotent
  already: closing a closed task leaves it closed.
- **Only `buffer flush`.** Bare `tasks`, `tasks ingest` and the `notes`
  pre-pass ingest as before. Flush runs without anyone watching. A
  hand-written `ACTION:` in a note is ingested as before: whoever wrote it is
  there to see the result.
- **Duplicates in the same flush collapse.** When two identical ACTIONs are in
  the buffer, the first becomes the task and the second is skipped as
  `already buffered`. This holds across `--date`: the two need not be filed
  under the same day.
- **Un-ingested ACTIONs in logs are not checked.** They are not tasks yet.
- **Unreadable files are not checked.** The pass reads through `V.read_utf8`,
  as every walker does, and skips a file that is not valid UTF-8. An open
  task in such a file is not seen, so its twin is added; `lint` reports the
  file.

## Cost

One pass over `notes/` and `logs/` per flush, reading each file once. The pass
builds a set of the open tasks' identities, so each check is a set lookup.

This is a second pass, not a shared one. The check has to run before flush
writes the logs; the ingest walks the vault after them.

## Done when

- The behaviour above is covered by tests that fail without it.
- `MANUAL.md` and `dev/tools/buffer.json` are regenerated if the `buffer
  flush` help changes, so `manual-check` and `tools-check` pass in `dev/ci`.

## The agent

The image ships `dev/tools` and `agent/skills` and installs them on every
start, so the agent learns of a skip two ways:

- The `buffer flush` help names both skip lines, and the tool definition is
  generated from it.
- `task-workflow` says what to relay when flush prints `already a task:`
  instead of `ingested:`.

`footguns`' "Don't dedupe the buffer" stands: the buffer still takes
duplicates, and flush is what drops them.
