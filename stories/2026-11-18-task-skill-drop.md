# task-workflow proposes `drop` for an abandoned task

Companion to `2026-11-18-tasks-drop.md`, which added `tasks drop` and left
the agent skill to a separate story.

## What is changing

`task-workflow` knows one way to close a task: `done`. Told "forget the
Northwind scope, they went elsewhere", it would either mark the task done,
which records something that never happened, or leave it open.

The skill gains a **Dropping a task** section:

- **When.** The owner says the task won't happen: "forget it", "cancel",
  "not doing that any more", "no longer needed", the other party pulled
  out. `done` is only for things that happened. If it's unclear whether
  it was done or abandoned ("that's off my plate"), ask, because the two
  records say opposite things.
- **Not for "later".** "Not yet" stays `set-scheduled`, as today.
- **Finding the task.** As for completion: by uuid prefix, else
  `tasks list` filtered by thread. If nothing matches, there is nothing
  to drop: say so. Don't add a task only to drop it.
- **A reason.** `drop` records none. If the owner gives one worth keeping,
  propose a `buffer add-text` to the task's thread alongside the drop, and
  run both on one confirm.
- **Relay.** `Dropped abcd1234.` For each `still depended on by:` line,
  relay the uuid and description and ask whether to `rm-depends` it or drop
  it too. Change nothing without asking.
- **Refusals.** `drop` on a done task (`is done`) and `done` on a dropped
  one (`was dropped`): relay the error. Neither is reversible from the CLI.

The frontmatter `description` also mentions abandoned tasks, so the skill
loads for them.

`activity-capture` is unchanged: a day's account reports work done, so
its `tasks done` stays.

`dev/agent-check` passes: `drop` is a real subcommand of `tasks`.
