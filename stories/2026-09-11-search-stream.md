# search stream — one chronological view of the vault

## The question it answers

"What actually happened, in order?" — and, more sharply, "did the thing I
just asked for actually land?"

Today's check-in reported four time entries and wrote one. Nothing surfaced
the gap: `hours list` shows hours, `tasks list` shows tasks, `search logs`
shows logs, and no view puts them on one timeline. `search activity`
aggregates to counts, which hides which records exist.

`search stream` merges every dated record in the vault into a single
time-ordered stream and prints it.

## Effective time, not record time

Every event is placed at **the date the thing happened**, taken from the
record itself — never file mtime, never the moment it was written down.

| Source | Event | Effective time from | Precision |
|---|---|---|---|
| Note | note written / meeting held | `timestamp` frontmatter, else filename | date, usually time |
| Log line | an observation or reference | the log's `date` frontmatter | date |
| Task anchor | task created | `entry:` in the anchor | date |
| Task anchor | task completed | `end:` in the anchor | date |
| Hours entry | time worked | `startTime` (ISO, rendered local) | date + time |
| Payment | money received | `received` (ISO, rendered local) | date + time |
| Thread | thread opened | `started:` frontmatter | date |
| Person | person added | `started:` frontmatter | date |

Two consequences worth stating plainly.

**One anchor yields two events.** A `DONE:` line carrying
`entry:2026-06-02 end:2026-09-10` appears twice — created in June, completed
in September. That is the point: it is how a completion becomes visible on
the day it happened rather than the day the task was born.

**`due:` and `scheduled:` are not event times.** They are intent, not
activity. A task due tomorrow did not happen today.

## The unit is a record, not a file

A log file with four body lines is four events. An hours file with 121
entries is 121 events. A note is one event.

**Task anchors are task events, never log events.** A `TASK:`/`DONE:` line
inside a log would otherwise appear twice — once as a log line and once as a
task. Only `TEXT:` and `REF:` lines become log events.

## Output

Grouped by day, so a heavy day is visually obvious rather than a wall.

```
2026-09-11
  08:00  hours    Projects/Agent               1h 0m   Added a dedicated skills tool
  09:00  hours    Projects/Zeke                4h 0m   Agent reliability and skill refinement
  13:30  hours    Processes/Personal Finance   1h 15m  Chased mom's missing FNB cash
  14:52  payment  Processes/Arbi Family Trust  49399 BWP
         log      Projects/AXA DORA            Cleaned up the code repo and removed tech debt…
         done     Projects/AXA DORA            Validate SQL detection patterns with Igor
         task     Projects/AXA DORA            Log AXA engagement proof of work

2026-09-10
  …
```

Time column is blank for date-only events rather than faked. Within a day,
timed events sort first in time order, then date-only events.

Paths are omitted from the text output — a stream is a scan view, and
absolute paths are long enough to wreck the line. `--json` carries the path
for every event.

## Filters

    search stream [--thread T] [--kind K[,K…]] [--since D] [--until D]
                  [--text P] [--limit N] [--reverse] [--json]

- `--kind` — `note`, `log`, `task`, `done`, `hours`, `payment`, `thread`,
  `person`. Comma-separated, default all.
- `--thread` — resolved the usual fuzzy way. Person events have no thread
  and drop out of a thread-filtered stream, which is correct.
- `--since` defaults to 7 days ago. **`--until` has no default**, so
  future-dated records (an agenda written for next month's meeting) still
  appear. Seeing them is useful.
- `--limit` defaults to 100 events, with a trailing line naming how many
  more were suppressed.
- `--reverse` for oldest-first. Default is newest day first, matching the
  rest of `search` and putting today where the eye lands.

## Volume, measured

Across the whole vault: **1313 events** — 475 task creations, 433 task
completions, 127 hours entries, 110 notes, 76 log lines, 64 people, 24
threads, 4 payments. Building that in memory is the same order of work
`search notes` already does.

In the last seven days: **66 events**, between 1 and 15 on a normal day, and
32 on 2026-09-10 — 30 of them completions from a bulk tidy-up. That spike is
real and the stream should show it.

But 77% of a typical week is task lifecycle. The default must be everything,
because completeness is the point of a stream; `--kind` is how you quieten
it when you want the substance rather than the churn.

## The log REFs do not change the implementation

`hours log`, `payments log` and `notes new` each drop a `REF:` into the
buffer, which suggests the stream could just read logs. It cannot, for two
reasons, both measured.

**A REF exists only after a flush, and only for records written since the
convention landed.** `buffer add-ref --date` now files each pointer under
the day the thing happened, so the dates are right — but the vault's 127
existing hours entries and 4 payments have no REF at all, and anything not
yet flushed has none either. A stream reading logs alone would silently omit
both.

**A completion is not in the day's file.** A `DONE:` anchor is rewritten in
place, so its `end:` date lives inside the anchor while the file stays filed
under the day the task was created — true for **136 of 167** completed tasks.

So the stream reads every source directly, exactly as planned, and takes the
effective date from the record itself.

**But it must exclude `REF:` lines whose target is `hours/` or
`payments/`.** Those records are already in the stream from their own files.
Now that the REF carries the right date the duplicate would sit directly on
top of the original, which is tidier and no less wrong. This exclusion is
mandatory, not cosmetic — unlike the same exclusion in `search activity`,
which only affects a count.

REFs pointing at `notes/` stay in: a note's REF is the only trace of it in
that thread's log, and the note itself is a separate event at its own date.

## What it deliberately does not do

**It shows creations, not mutations.** Changing a task's due date, editing
an hours description, or renaming a thread produces no dated event, so none
of those appear. Today's failure — four entries claimed, one written — would
have been caught, because those were creations. An edit silently reverted
would not be.

Git is the audit trail for mutations, and `commit review` already reads it.
The stream answers "what happened in my life"; `commit review` answers "what
changed in the vault". Conflating them would make both worse.

**It does not replace `activity` or `overview`.** `activity` ranks threads
by weight over a window; `overview` is one thread in full; `stream` is the
flat chronology. Different questions.

## Built

All four questions were answered and the subcommand exists.

1. **Threads and people are in the default set** — they read `started:`.
2. **The time column was dropped.** 81% of events (1079 of 1316) are
   date-only, so a dedicated column would have been mostly blank and a
   `00:00` on everything would have been a visible lie. The clock time is
   appended in parentheses on the rows that have one.
3. **Unflushed buffer entries appear as `pending`.** `search` never flushes:
   it is declared `read_only` to the agent, and flushing writes logs, clears
   the buffer and runs task ingest.
4. **`--today`** bounds both ends.

One correction found during the build: the `hours/`/`payments/` self-REF
exclusion had to apply to *pending* entries as well as flushed log lines.
Without it an unflushed hours REF duplicated its own entry. A test now
asserts the record appears exactly once both before and after a flush,
which is the property that actually matters.

## Still open

- **`buffer add-text` has no `--date`.** `add-ref` got one so that hours and
  payments file under the day the work happened. A `TEXT:` line written
  about last week still lands on today's date. It has not bitten yet because
  the agent writes detail lines about work it is recording in the moment.
- **`search activity` counts REF lines**, so a thread's `ENTRIES` now
  includes the pointers from hours and payments. Deliberately left: no
  figure is inflated, the `HOURS` column reads its own store, and the
  columns are honest about what the logs contain.
