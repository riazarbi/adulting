# Skill: footguns

Common mistakes to avoid. Read once at session start and again
whenever something feels off.

## Never call `task` directly

The taskwarrior binary is the storage backend; it's not your
interface. Use `tasks <subcommand>`. `task add`, `task <id> modify`,
`task <id> done` skip the validation gates that ensure source notes
and tw stay in sync. The source-wins sync policy specifically
assumes nothing else is mutating tw description fields.

If you find yourself reaching for `task`, stop. There's a `tasks`
subcommand for what you want.

## UUIDs over IDs

Numeric IDs (`#42`, `#185`) are unstable — they shift as tasks
complete. The 8-char UUID prefix (`abcd1234`) is stable and matches
the source-anchor format embedded in note files.

When relaying tasks to Riaz, use the uuid prefix. When invoking
`tasks <subcommand>`, accept either (the resolver handles both) but
prefer uuids in proposals so the user can copy-reference them.

## Dates are always ISO

`YYYY-MM-DD`. Always. Resolve "tomorrow", "Friday", "next month",
"in two weeks", "eod", "eom" yourself **before** calling the tool.
The tool will reject anything else.

To resolve, use today's date from the system prompt's context
section. Don't ask Riaz to clarify a relative date he just typed —
just compute it.

## Threads are paths, not bare names

Pass `Processes/SGB`, not `SGB`. Pass `Projects/AXA DORA`, not
`AXA DORA`. The `Kind/` prefix is required everywhere — schema
regex enforces it. Bare names won't resolve and the call will fail.

## Don't fabricate person files

If the actor doesn't exist as `~/.adulting/people/<Name>.md`, **don't
just write the file from a tool call**. Load the `create-person`
skill, follow its protocol (capture metadata, propose the compound
plan, confirm), then create.

Inventing a `Bern.md` because Riaz typed "Bern" is wrong. Resolving
to `Bern Sellmeyer.md` because that file exists is right.

## Don't dedupe the buffer

The buffer accepts duplicates. `buffer tend` regroups by (thread,
date) but doesn't merge identical lines. If Riaz says the same thing
twice, log it twice. He's the editor, not you.

If something genuinely feels like a duplicate write, propose it
anyway and let the confirm step catch it.

## One round-trip per intent

Don't layer Socratic clarifying questions on the propose-confirm
loop. State your inferences in the proposal; let Riaz correct via
the confirm step. The cost of one extra confirmation round is much
less than the cost of three back-and-forth questions.

## Multi-thread is for notes, not buffer entries

A note can belong to multiple threads (`threads:` list in
frontmatter). A buffer entry routes to **one** thread (because flush
writes one log line per entry, and the log file is per-thread).
Don't try to multi-thread a buffer entry — pick the primary thread
and proceed.

## Pass arguments as a list, not a string

Tools accept argv as a JSON array of strings:

```
tasks ["add", "Processes/SGB", "(Bern) Send report", "--due", "2026-05-15"]
```

Not:

```
tasks "add Processes/SGB \"(Bern) Send report\" --due 2026-05-15"
```

The list form avoids shell-escaping headaches and ensures spaces in
arg values (people names, descriptions) are preserved correctly.
