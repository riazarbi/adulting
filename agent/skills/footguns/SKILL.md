---
name: footguns
description: Behavioural pitfalls when working Riaz's vault — never narrating a tool result you didn't receive, never inventing people or threads, never deduping the buffer, one round-trip per intent, and which subcommands are refused outright. Activate at session start, and whenever a tool call is about to be made and something feels off.
---

# Skill: footguns

Mistakes that are easy to make and expensive to undo. Each tool's
own description covers its arguments and flags — this is about
behaviour, not syntax.

## Never narrate a result you didn't receive

If you have not actually invoked a tool in this conversation, you
have no output to relay. Do not say a call errored, returned
nothing, or found no match unless that text is visible above. Invoke
it, wait, then speak.

This bites hardest on reads, because there is no confirm step to
catch it — the fabricated answer goes straight to Riaz.

## Never invent a person or a thread

If a name doesn't come back from `people list`, don't coin it.
Resolving "Bern" to `Bern Sellmeyer` because the roster says so is
right; inventing a person called `Bern` is wrong. Load
`create-person` instead.

Same for threads: if it isn't in `threads list`, ask which existing
thread to use. Creating a thread is its own intent and needs an
explicit request — never bundle it into a capture.

## Some subcommands are refused

Some subcommands are blocked for you — the tool description says
which, under `BLOCKED:`. Read that line before reaching for one.

Nothing prompts. A command given too little exits with an argparse
error naming what is missing, so a guess costs a turn rather than
hanging a session. Pass every argument the tool description marks
required, and read the error rather than retrying blind.

## Don't dedupe the buffer

The buffer accepts duplicates. If Riaz says the same thing twice,
log it twice — he is the editor, not you. `buffer tend` regroups by
thread and date; it does not merge lines, and neither should you.

Stats are the sharpest case. Two `stats log pushups 25` calls are two
sets, and a stat summed over the day needs both. Drop one and the day
is halved.

## One round-trip per intent

State your inferences in the proposal and let the confirm step
correct them. One extra confirmation costs far less than three
clarifying questions. Don't stack questions on top of the
propose-confirm loop.

## Multi-thread is for notes, not buffer entries

A note can belong to several threads. A buffer entry routes to
exactly one, because flush writes one log line per entry and logs
are per-thread. Pick the primary thread and move on.

## Reads are free, writes are not

You can read vault files directly with `read_file`, `list_files` and
`rg` — use them when a domain tool doesn't answer the question.

Every write goes through the entity's own tool. There is no
file-writing tool, and hand-written files break the schemas and the
uuid anchors that `tasks` depends on.
