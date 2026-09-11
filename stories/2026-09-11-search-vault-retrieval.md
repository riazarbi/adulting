# search — vault retrieval

## Problem

Every entity in the vault has a filtered, non-interactive query except the
two that hold the actual content.

| Entity   | Query available                                     |
|----------|-----------------------------------------------------|
| tasks    | `list --thread --priority --assignee --overdue`     |
| hours    | `list` / `report --since --until --thread`          |
| payments | `list` / `statement --since --until --thread`       |
| threads  | `list`; `show` (whole body, no filter)              |
| people   | `list`, `show`                                      |
| notes    | none                                                |
| logs     | none                                                |

110 notes and 145 log files across 20 threads are reachable only by generic
grep. The agent's `rg` is a single exec with no shell and no pipes, so it
cannot intersect two predicates: "notes on SGB" and "notes of type Meeting"
are two calls whose results it must combine itself.

Measured consequences, against the real vault:

- "Last SGB meeting" costs 42 paths plus 80 paths into context, intersected
  by the model. The shortcut it will actually take — thread matches sorted
  by filename — returns the wrong note for 3 of the 7 threads that have
  meetings, one of them out by 13 months.
- "Most active threads last week" costs 145 paths (5.6 KB), filtered on a
  date embedded in each filename, grouped by path segment, then ranked.

The correct answer to the second is four rows. Neither is reliable on a 4B
model, and both are trivial server-side.

## Scope

`search` covers **notes and logs** — the content layer, the part with no
query surface.

It does not cover threads or people: those have `list` and `show`, and in
this tool they are filter dimensions rather than things searched. It does
not cover tasks, hours or payments, which already have filtered lists.

`search` returns **pointers with enough metadata to choose**. Retrieval is
`read_file`. The two stay separate so a broad search never drags bodies into
context.

## Subcommands

    search notes     [--thread T] [--type T] [--since D] [--until D]
                     [--text P] [--limit N] [--json]
    search logs      [--thread T] [--since D] [--until D]
                     [--text P] [--limit N] [--json]
    search activity  [--thread T] [--since D] [--until D] [--json]
    search overview  THREAD [--since D] [--until D] [--json]

Named subcommands rather than one with a `--kind` flag: a small model picks
a name more reliably than a mode, and notes and logs genuinely differ in
shape — a note has a topic and a type, a log has a date and entries.

The two motivating questions each become one call:

    "key takeaways from the last SGB meeting"
      search notes --thread SGB --type Meeting --limit 1

    "most active threads over the last week"
      search activity

## The goal is a global view

The point is not file-finding, it is forming a complete picture of a
subject in one call. Two axes, two subcommands:

- **Across threads, one window** — `activity` ranks where attention went.
- **One thread, everything** — `overview` is the whole picture of a single
  thread: its metadata, how much of each record type exists, open and done
  tasks, hours logged, money received, and the most recent items.

Without `overview` that picture costs six calls — `threads show`,
`tasks list --thread`, `hours report --thread`, `payments statement`,
`search notes`, `search logs` — and the model must stitch them together.

`overview` overlaps `threads show` deliberately and they answer different
questions: `threads show` prints the thread FILE, `overview` summarises
everything in the vault that points AT that thread.

## Ordering: event date, not capture date

Notes carry both. The filename is when the note was created; frontmatter
`timestamp` is when the thing happened. They diverge in both directions —
an agenda written on 2024-08-22 for a meeting held on 2024-08-27, a session
on 2024-07-15 written up on the 18th. 29 of 110 notes differ.

Order and filter by the **event date**: frontmatter `timestamp` for notes,
`date` for logs, falling back to the filename when absent or malformed
(4 notes today). Newest first, always.

This changes no answer to "the last meeting" today — the two agree for all
7 threads — but it is the correct key for range queries, and for any note
prepared in advance of its event.

## Defaults

The common case should be one call with no arguments to compose.

- `--limit` defaults to 20. Metadata lines are short; 20 hits is ~1.6 KB.
- `search activity` defaults to the last 7 days.
- `--thread` accepts a bare name, `Kind/Name`, or a wikilink, resolved with
  the same helper `hours` and `payments` use. `SGB` works; no `threads list`
  round-trip needed first.
- `--type` is case-insensitive.
- `--text` is a case-insensitive literal. For notes it covers the topic and
  the body; for logs it covers the entry lines, which is where day-to-day
  detail actually lives.

## Response shape

Path first, so the left edge is constant and the value the agent feeds to
`read_file` is never pushed around by a long topic. Variable-length fields
last.

    notes/2026-08-31-17-22-38.md  2026-08-31  Meeting  Processes/SGB  Camps Bay Primary School Parents Meeting

With `--text`, each hit gains one indented snippet line showing the match.

`search logs` is the same minus type and topic:

    logs/Projects/SANA Partners/2026-09-10.md  2026-09-10  Projects/SANA Partners  6 entries

`search activity` aggregates rather than listing:

    THREAD                        NOTES  LOGS  ENTRIES  HOURS  LAST
    Projects/SANA Partners            0     2       11   6h 30m  2026-09-10
    Projects/Agent                    1     1        4        -  2026-09-09

Ranked by notes+logs descending, then by LAST descending. `ENTRIES` counts
body lines within the logs, which distinguishes a thread touched once from
one worked all week. `HOURS` is time logged in the same window — the
strongest single signal of where attention actually went, and the reason
activity is not just a file count.

`--json` on all three, matching house style.

## Non-goals

- **No bodies.** `--full` was considered and dropped; `read_file` retrieves.
- **No relevance ranking.** Recency answers the questions that are actually
  asked, and ranking is a rabbit hole.
- **No interactivity, ever.** `search` must never prompt. The `hours log`
  and `payments log` pattern — interactive when an argument is absent —
  must not be repeated here.

## Properties

Read-only. Never writes, never prompts, never launches an application. In
the agent tool policy it is `read_only: true` with no `forbidden_args`.

Files that do not parse are skipped rather than reported inline; the count
is available in `--json` output. The vault currently holds a handful,
including a Syncthing conflict file that `lint` already flags.
