---
name: activity-capture
description: Turns a free-text account of what Riaz has been doing into time entries, log lines and stat values — usually his reply to a midday or end-of-day check-in, but also any unprompted "here's what I've been up to". Activate when a message is a list of things he has done over a period, rather than a single completed task or a single observation.
---

# Skill: activity capture

He tells you what he did in one sentence. You turn it into records.

> i had a 5k run, fixed the broken alarm, and circulated the sgb minutes

Three items, three threads. Your job is to file them with as little of his
attention as possible.

## Three records, different jobs

**Every item gets a time entry.** That is the coverage record: which thread,
how long. The `name` is a **short label of about six words** naming the
work — "Fixed the broken alarm", "Zeke agent reliability work". It is an
invoice line item on billable threads, and `search` cannot read it.

**`hours log` already writes a `REF:` into the log for you.** You never have
to record *that* the work happened — the tool does it. Your log line is only
ever for the detail.

**Whatever he said that does not fit in the label becomes that log line.**
Mechanical, not a judgement call: write the label, then look at what is left
over. If anything is, it is a `TEXT:` line on the same thread. That is where
detail belongs, because `search --text` reads logs and never reads hours.

> "got sucked into the zeke stuff, adding tools, refining skills, making the
> agent more reliable — probably 4 hours"

  label    → "Zeke agent reliability work"          (the hours entry)
  left over → "Added tools and refined skills to make the agent more
               reliable and effective."             (the log line)

A short item leaves nothing over. "Fixed the gate" is a label and a
duration and that is all — no log line. Never pad one to fill the slot,
and never cram the leftovers into the label instead.

**A number he tracks becomes a stat value.** "5k run" is 30 minutes on
`Processes/Wellness` *and* 5 on `run-km`. The hours entry says how long;
the stat says how much. Neither replaces the other, and the number does
not also go in the label or a log line.

Run `stats list` once, beside `tasks list`, and match numbers against it:
distance, reps, weight, money, or an event logged as `1` ("had a drink").
Several sets are several values — follow `stats-workflow` for that and
for anything else about the values themselves.

If a number has no declared stat, it stays in the label or the log line
as it would have, and the proposal says so: "no stat for run distance —
want one?" Never declare a stat inside a capture; that is its own intent,
proposed on its own via `stats-workflow`.

**A named person always forces a log line.** People cannot live in an hours
entry: a wikilink inside one renders but creates no backlink and no graph
edge, because Obsidian skips fenced code blocks, and `search` cannot read it
either. So a name in the label is a name that has gone nowhere.

Keep names out of the label and put them in the log line, wikilinked:

> "1 hour call with my sisters, Nadia Arbi and Taz Arbi"

  label → "Call with my sisters"                         (the hours entry)
  log   → "Call with [[people/Nadia Arbi]] and
           [[people/Taz Arbi]]."                         (the log line)

Resolve every name against `people ["list"]` and use the exact entry it
returns. If someone does not appear there, load `create-person` and fold
creating them into the same proposal — never invent a person, and never
quietly drop the name instead.

```
hours:  Processes/Toil  1h 0m  "Fixed the broken alarm"
log:    TEXT: Alarm was the backup battery, not the panel. Replaced it;
              the callout would have been R3k.
```

A commitment he picked up is neither — that is `tasks add`.

## Build the plan

Split the reply into items. For each:

**Thread** — the open threads are listed in your context on every turn.
**Every thread you use must be copied from that list, character for
character.** If it is somehow not there, call `threads ["list"]` before you
compose anything. Never write a thread name from memory.

Kinds are only `Projects`, `Processes` and `Topics`. There is no
`Personal/`. If you find yourself typing a thread you have not just read in
the list, you are inventing one — stop and look again.

Match against the list you fetched: a run or gym session is usually
`Processes/Wellness`; chores and admin `Processes/Toil`; money matters
`Processes/Personal Finance`. Client and project work almost always names
itself, but the name he says is rarely the name on the file — "AXA" is
`Projects/AXA DORA`.

If an item matches no open thread, say so in the proposal and leave it out
rather than forcing it into the nearest one.

**Duration** — he will rarely give one. Estimate, and show the estimate:
- A stated duration wins: "two hours on X" → 120.
- A quantity that implies one: a 5k run is about 30 minutes.
- Otherwise judge from the item. A circulated email is 10 minutes; a repair
  an hour; a meeting an hour unless he says otherwise.
- Round to 15-minute steps. This is coverage, not a stopwatch.

**Already a task?** Run `tasks list` once and check the items against it. If
one matches a pending task, closing it is part of the plan — an activity can
both consume time and complete a commitment.

**A tracked number?** Check against the `stats list` you ran once (above).

**Which day?** If he is describing an earlier day, every record for that
item carries it: `-d` on `hours log` and `stats log`, `--date` on
`buffer add-text`. Without it the log line files under today, and the
detail lands in a different log from the time it explains.

## Propose once

One message, everything in it, ending in `OK?`. He corrects durations in one
word; never ask about them individually.

```
Logging:
- Processes/Wellness   30m  5k run
       + stat: run-km 5
- Processes/Toil       60m  Fixed the broken alarm
       + log: backup battery, not the panel; a callout would have been R3k
- Projects/AXA DORA   4h 0m  Code cleanup and dbt integration
       + log: removed tech debt, tried confluence/git sync
- Topics/Relationships 1h 0m  Call with my sisters
       + log: call with [[people/Nadia Arbi]] and [[people/Taz Arbi]]

Also closing: "Circulate SGB minutes" (a1b2c3d4)

OK?
```

Every `+ log` line is a `buffer add-text` and every `+ stat` line a
`stats log` you will actually make. If you show one, write it.

## Corrections

If he corrects part of the plan — a wrong thread, a wrong duration — the
**whole plan still runs**, not just the bit he corrected. Restate the full
corrected list, then execute every line of it. Fixing one item and silently
dropping the other three is the worst outcome available: he believes his day
is captured when most of it is missing.

## Execute, then report what actually happened

On confirm: the `hours log` calls, then any `buffer add-text`, then any
`stats log`, then `buffer flush`, then any `tasks done`. `stats log`
writes to the buffer, so it must come before the flush or it waits for
the next one.

**Build the closing message from the tool results, never from the plan.**
Count the `logged` lines you actually got back. If a call failed or you
never made it, it is not in the summary — say what did not go in and why.
Reporting an entry you did not write is worse than reporting nothing: it
tells him the time is recorded when it is not, and he will not find out
until the month is wrong.

One line: how many entries, total time, how many stat values, anything
you could not place.

**Do not commit.** The nightly job at 21:00 commits the day's work. A commit
here would fragment the history and duplicate that job.

## Rules

**Never invent activity.** Only what he actually said. "Not much, admin" is
one short entry against `Processes/Toil` — an empty half-day is real data.

**Never ask for durations one at a time.** The whole point is that this
costs him one message.

**Don't chase precision.** "Morning was all SANA" logs the morning against
SANA. Approximate coverage beats exact nothing.

**Unbilled is normal.** Personal threads carry no currency and record time
with no money attached. Never pass `--rate`, and never ask whether something
is billable — the thread already knows.

**Use `-d` and `-t` when he describes an earlier part of the day.** An
end-of-day reply covering the morning should carry a morning start time, not
the moment you filed it. For an earlier *day*, the log line needs
`--date` too (see "Which day?" above).
