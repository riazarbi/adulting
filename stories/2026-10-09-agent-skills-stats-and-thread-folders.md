# Agent skills catch up with stats, thread folders and dated captures

Companion to `2026-10-07-stats.md` ("Updating the agent's skill and tool
definitions is a separate story") and `2026-10-05-thread-scoped-vault.md`.
This is the agent-skill side of both, plus one older gap: `buffer --date`
(2026-09-23), which `activity-capture` never picked up.

`dev/agent-check` passes today. It checks names, not intent: every skill
still uses real commands, but none uses `stats`, none reads a thread folder
directly, and the commit body ignores records that now exist. The question
this story answers is: given each skill's intent, what is the best way to
use the commands as they are now?

## Summary

| Skill | Change |
|---|---|
| `stats-workflow` | **New.** Declare, log, report and correct stats. |
| `activity-capture` | Numbers go to `stats log`. Log lines carry `--date` when backdated. |
| `buffer-workflow` | A number against a declared stat is `stats log`, not `add-text`. Backdated captures carry `--date`. |
| `recall` | Routes stats questions. Reads a thread's folder for thread-scoped questions. |
| `commit-workflow` | Activity covers `STAT:` lines, `payments.md` and stat declarations. |
| `footguns` | "Don't dedupe the buffer" names the stats case. |
| `task-workflow`, `time-workflow`, `billing-workflow`, `create-person` | No change. |

## New skill: `stats-workflow`

Same shape as `time-workflow`: the `stats` tool definition carries the
syntax, the skill carries the judgement.

**Description (trigger).** Riaz reports a number he tracks ("did 50
push-ups", "weighed 82.4", "had a drink"), asks to start tracking
something ("I want to track my runs"), or asks how a tracked number has
moved ("how many drinks this month"). For time spent, use `time-workflow`.

### Declaring

Declaring is its own intent, like creating a thread. It is never folded
silently into a capture. When a capture has no stat to land on, the skill
that found it says so and offers to declare one; the declaration is
proposed on its own.

Mistakes here last: names are unique across the vault and there is no
rename or delete. So the proposal states every choice:

- **Name.** Lowercase, digits, `-`. Put the unit in the name when the
  number alone is ambiguous: `run-km`, `weight-kg`, `spend-zar`. Check
  `stats list` first, so a near-duplicate (`pushups` vs `push-ups`) is
  not declared.
- **Thread.** Copied from the open threads, like any other capture. A
  health stat is usually `Processes/Wellness`.
- **Type.** `int` for counts and events, `decimal` for anything with a
  fractional part (distance, weight, money).
- **Agg.** The real judgement call. It decides what a week means:
  - `sum`: quantities that add up (push-ups across sets, km run, money spent).
  - `last`: readings where the latest one is the truth (weight, a step
    count read off a watch during the day).
  - `max`: best effort (heaviest lift, longest set).
  - Events: `int`, logged as `1`. `sum` counts occurrences, `max` only
    says whether it happened. Default to `sum` unless he says he only
    cares whether it happened.

### Logging

- `stats log <name> <value>`, with `-d`/`-t` when he describes an earlier
  time. Propose, log on confirm.
- The name comes from `stats list`, never from memory. An undeclared name
  exits `1` and suggests names: read them, don't retry blind.
- `stats log` writes to the buffer. It does not need a flush to show in
  `stats series`, and the skill does not flush on its own.

### Reporting

Read-only, no confirm.

- "How many push-ups this week/month" → `stats series <name> --by week`
  (or `month`) bounded with `--since`/`--until`.
- A `-` (JSON `null`) is a period with nothing logged. Never report it as
  zero, and never sum across it as if it were.
- Never state a number the tool did not print (as in `billing-workflow`).

### Correcting

Entries have no id.

- Before flush: `buffer list`, then `buffer rm <line>`, then log again.
- After flush: the value is a `STAT:` line in a log file, which the agent
  cannot write. Say so and leave it for Riaz.

Because a wrong value is hard to fix once flushed, the propose step is
not skipped for stats, even for a single number.

## `activity-capture`

### Stats: a third record

Today "5k run" becomes a 30-minute hours entry and, by the skill's own
rule, nothing is left over. The 5 km is lost.

- Run `stats list` once, alongside the `tasks list` it already runs.
- An item carrying a number that matches a declared stat gets a stat
  line as well as its hours entry. Hours are coverage (how long); the
  stat is magnitude (how much). They do not replace each other.
- The number does not also go in the label or the log line.
- No matching stat: say so in the proposal, like an item with no
  matching thread, and offer to declare one (`stats-workflow`). Don't
  declare it as part of the capture.

Proposal format gains a `+ stat:` line:

```
- Processes/Wellness   30m  5k run
       + stat: run-km 5
```

Execution order becomes: `hours log` calls, `buffer add-text` calls,
`stats log` calls, then `buffer flush`, then `tasks done`. `stats log`
writes to the buffer, so it must come before the flush or it sits
unflushed until the next one.

The closing message counts stat values logged, built from tool results
like everything else.

### Backdated items: `--date` on the log line (2026-09-23 gap)

The skill tells the agent to pass `-d`/`-t` to `hours log` for an earlier
part of the day or an earlier day. It says nothing about the log line.
`buffer add-text` without `--date` files under today, so yesterday's work
puts its hours REF in yesterday's log and its detail in today's.

- Every record for an item carries the same day: `hours log -d`,
  `buffer add-text --date`, `stats log -d`.
- `-t` has no counterpart on `add-text`; the date is what matters for
  which log the line lands in.

## `buffer-workflow`

The description covers "an observation, status update, half-formed
thought". "Had a drink last night" and "weighed 82.4 this morning" land
here today and become `TEXT:` lines.

- Check the capture against `stats list`. A number (or event) that
  matches a declared stat is `stats log`, following `stats-workflow`. A
  message with both a number and an observation is two entries, proposed
  together.
- A number with no declared stat stays an `add-text` capture, in his
  words. Offer to declare a stat; don't declare one silently.
- Mirror the existing boundary: "Never call `add-action` here" gets a
  sibling pointing stats at `stats-workflow`.
- The description names stats as out of scope, as it does for actions.
- The same `--date` gap as `activity-capture`: a capture about an
  earlier day passes `--date`, so it files under that day's log.

## `recall`

### Stats questions

`recall`'s description already sends hours and money to their own
skills. Stats join them: "how many", "how often", "how has my weight
moved" → `stats-workflow`. One table row points there.

### Thread folders

Goal 2 of the thread-scoped-vault story was that the agent can read a
thread's folder instead of running searches. `recall` still only uses
`search`.

- A question about one thread's content ("everything on SGB", "what did
  we say about the lease on SGB") → `list_files` on
  `threads/<Kind>/<Name>/`, then `rg <term>` inside it. This is a
  smaller, scoped read, and `rg` reaches `hours.md` descriptions, which
  `search` cannot.
- `search` stays the tool for questions across threads, for event-date
  ordering ("the last meeting"), and for `stream`/`activity`.
- The "read one, not ten" rule still holds: listing a folder is not a
  licence to open every file in it.

## `commit-workflow`

The Activity table, updated on 2026-10-05, misses three record types:

| Source | Missing today | Should read as |
|---|---|---|
| `STAT:` lines in `logs/<date>.md` | Summarised from `TEXT:`/`TASK:`/`REF:` only | "Logged 60 push-ups, run-km 5" |
| `threads/<Kind>/<Name>/payments.md` | Not in the table, so it falls into Vault changes | "Received R15,000 (September invoice)", from each **added** payment |
| `threads/<Kind>/<Name>.md` frontmatter gaining `stats:` | Not in the table | "Declared stat `pushups`" |

`payments.md` gets the same rule the skill already gives `hours.md`:
never listed under Vault changes. Payments predate this week, but the
folder move made them siblings of hours and the omission is now
conspicuous.

## `footguns`

"Don't dedupe the buffer" stands, and now has its sharpest case: two
`stats log pushups 25` calls are two sets. Under `sum`, deduping one
halves the day. Add that as the example.

## No change

- `task-workflow`: already relays `already a task:` (2026-10-05).
- `time-workflow`, `billing-workflow`: hours and payments behaviour did
  not change. The "a run with a distance is also a stat" case lives in
  `activity-capture`, which is where combined reports arrive.
- `create-person`: still correct.

## Verification

- `dev/agent-check` passes, including the new skill's frontmatter
  (`name` equals the folder name, description non-empty, no extra keys).
- `dev/ci` passes.
- Each skill change is read against `MANUAL.md` for the commands it now
  uses: `stats new|list|log|series`, `buffer add-text --date`,
  `buffer list|rm`.
- Walk-through, against a testbed vault with `pushups` (int, sum) and
  `run-km` (decimal, sum) declared on `Processes/Wellness`:
  1. "Yesterday I did a 5k run and fixed the alarm, the battery was
     dead" → proposal has hours `-d <yesterday>`, `stat: run-km 5 -d
     <yesterday>`, `add-text --date <yesterday>`; after flush, all three
     are in yesterday's logs.
  2. "Had a drink" with no `alcohol` stat → `add-text` plus an offer to
     declare one; nothing declared.
  3. "How many push-ups this week" → `stats series pushups --by week`;
     a day with nothing logged is reported as nothing logged, not 0.
  4. `commit review` after (1)–(3) → Activity lists the stat values and
     any payment added; nothing from `hours.md` or `payments.md` is
     under Vault changes.

## Out of scope

- CLI changes. Every command used here exists today.
- Regenerating `dev/tools/` or `MANUAL.md`.
- A `BLOCKED:` entry for `stats new`. The skill keeps declaration behind
  its own proposal; whether the tool should also refuse it is a separate
  question.
