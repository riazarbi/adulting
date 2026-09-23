# Flushing an ACTION that is already an open task does nothing

## What is being added

`buffer flush` skips a buffered ACTION that is a strict duplicate of an open
task. It writes no log line for it, so the ingest makes no new anchor. It says
so and still succeeds:

    already a task: 1a2b3c4d  Draft scope

This is the default. There is no flag.

The reason: agents add tasks through `tasks add` without reading the vault
first. Re-adding a task that is already open should leave the vault as it was.

## Strict identity

An ACTION duplicates a task only when every one of these is equal, compared
exactly (case, spacing and all):

- **Threads.** The anchor's file threads must be exactly `[<the ACTION's
  thread>]`. A matching task in a note with several threads does not count.
- **Assignee.** Both have none, or both have the same one.
- **Description.**
- **Priority, due, scheduled.** Each is the same, or both lack it.
- **Depends.** The same set of uuids. Order does not matter.

The entry date and the uuid are not compared.

## Boundaries

- **Only open tasks count.** A DONE twin does not block, so a recurring chore
  can be added again.
- **Only adding a task.** The commands that change a task are idempotent
  already: closing a closed task leaves it closed.
- **Only `buffer flush`.** Flush runs without anyone watching. A hand-written
  `ACTION:` in a note is ingested as before: whoever wrote it is there to see
  the result.
- **Duplicates in the same flush collapse.** When two identical ACTIONs are in
  the buffer, the first becomes the task and the second is skipped as
  `already buffered`.
- **Un-ingested ACTIONs in logs are not checked.** They are not tasks yet.

## Cost

One pass over `notes/` and `logs/` per flush, reading each file once. The pass
builds a set of the open tasks' identities, so each check is a set lookup.
Flush already makes this pass for its ingest.
