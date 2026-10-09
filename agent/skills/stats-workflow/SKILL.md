---
name: stats-workflow
description: Records and reports numbers Riaz tracks over time — push-ups, kilometres run, weight, money spent, or an event such as a drink — and declares a new stat when he wants to start tracking something. Activate when he reports a tracked number ("did 50 push-ups", "weighed 82.4", "had a drink"), asks to start tracking something, or asks how a tracked number has moved ("how many drinks this month"). For time spent, use time-workflow.
---

# Skill: stats workflow

For magnitudes: how many, how much, how often. The `stats` tool
description carries the subcommands and flags; this is the judgement
around them.

A stat is not time. "A 5k run" is 30 minutes on `hours` and 5 on
`run-km`; the two records answer different questions and neither
replaces the other. When a report mixes activities, `activity-capture`
owns it and uses this skill for the numbers.

## Declaring a stat

Declaring is its own intent, like creating a thread. Never declare one
as a side effect of logging. When a number has no stat to land on, say
so and offer to declare one; if he agrees, propose the declaration on
its own.

Mistakes here last. Names are unique across the vault, and there is no
rename or delete — a bad name is fixed by hand, by Riaz. So the
proposal states every choice and he confirms it once.

**Name** — lowercase letters, digits and `-`. Put the unit in the name
when the number alone is ambiguous: `run-km`, `weight-kg`, `spend-zar`.
Run `stats list` first and reuse what is there; never declare
`push-ups` beside an existing `pushups`.

**Thread** — copied from the open threads like any other capture. A
health number is usually `Processes/Wellness`.

**Type** — `int` for counts and events, `decimal` for anything that can
have a fractional part: distance, weight, money.

**Agg** — the real judgement call. It decides what a week's figure
means:

- `sum` — quantities that add up. Push-ups across sets, km run, money
  spent.
- `last` — readings where the latest one is the truth. Body weight, a
  step count read off a watch during the day.
- `max` — best effort. Heaviest lift, longest set.

**Events** — something that happens or doesn't ("had a drink", "missed
my meds") is an `int` stat logged as `1` each time. Use `sum` so a week
counts occurrences. Use `max` only if he says he cares whether it
happened at all, not how often.

```
Declaring:
- run-km on Processes/Wellness — decimal, sum (a week is total distance)

OK?
```

## Logging a value

1. **Resolve the name** from `stats list`. Never from memory. An
   undeclared name exits `1` and suggests close names — read them
   rather than retrying blind.
2. **Date and time** — default to now. Pass `-d` when he describes an
   earlier day, `-t` when the time of day matters.
3. **Propose**, ending in `OK?`. On confirm, `stats log <name> <value>`.

Always propose, even for one number. A value that has been flushed
cannot be corrected by you (see below), so the confirm step is the only
check it gets.

Several sets are several values. "Did 20, 25 and 15 push-ups" is three
`stats log` calls, not one call with 60 — `sum` adds them, and `max`
needs to see each one.

`stats log` writes to the buffer. You do not flush; Riaz flushes when
he's ready, or the daily job does. `stats series` already reads the
buffer, so an unflushed value still shows up.

## Reporting

Read-only — no confirm.

- "How many push-ups this week" → `stats series pushups --by week`
  with `--since` on Monday.
- "How has my weight moved this month" → `stats series weight-kg`
  with `--since` and `--until` on the month. Daily is the default.
- "How often did I drink in September" → `--by month`, bounded on
  the month.

Compute the period boundaries yourself from today's date. Weeks start
on Monday.

**A `-` is not a zero.** A period with nothing logged prints `-`
(`null` in JSON). It means nothing was recorded, which is not the same
as a logged 0. Say "nothing logged" for it, and never fold it into an
average or a total as if it were 0.

Never state a number the tool did not print.

## Correcting a value

Entries have no id.

- **Still in the buffer** — `buffer list`, then `buffer rm <line>`
  using the number from that fresh list, then log the right value.
  Propose all three as one plan.
- **Already flushed** — the value is a `STAT:` line in a log file, and
  you cannot write files. Say which day and which value, and leave it
  for Riaz.

## Example

> Did 3 sets of push-ups this morning, 20, 25 and 15

→ `["log", "pushups", "20", "-t", "07:30"]`,
`["log", "pushups", "25", "-t", "07:30"]`,
`["log", "pushups", "15", "-t", "07:30"]`
