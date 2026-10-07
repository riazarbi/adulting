---
schema: log
scope: file
path: threads/<Kind>/<Name>/logs/<YYYY-MM-DD>.md
---

# Log file

A per-thread per-day log of activity, derived from the buffer by `buffer flush`. Lives in the thread's folder, at `~/vault/threads/<Kind>/<Name>/logs/<YYYY-MM-DD>.md`.

Logs are *output* of the buffer-flush ritual — not authored by hand in the way notes are. Each line is one buffer entry: a free-text observation (`TEXT:`), a reference to another file (`REF:`), an action item (`ACTION:` / `TASK:` / `DONE:`), or a value of a declared stat (`STAT:`). The day is the resolution; sub-day timestamps are not preserved, except on `STAT:` lines.

`tasks` ingest scans every thread's `logs/` as well as its `notes/`, so ACTION lines in a log become backend tasks just like ACTION lines in a note. The log file is the action's source for sync purposes.

## Fields

| name   | required | type   | constraint                                        |
|--------|----------|--------|---------------------------------------------------|
| thread | yes      | string | regex=\[\[(Projects\|Processes\|Topics)/[^\]]+\]\] |
| date   | yes      | string | regex=\d{4}-\d{2}-\d{2}                            |
| type   | yes      | enum   | Log                                                |

`thread` must name the thread whose folder the log is in; `lint` checks.

## Body

| pattern         | meaning                                                       |
|-----------------|---------------------------------------------------------------|
| `REF: [[X]] ...` | reference to another file in the vault (note, thread, person) |
| `TEXT: ...`     | free-text observation                                          |
| `ACTION: ...`   | open action item — ingested by `tasks`                         |
| `TASK: ...`     | already-ingested action item with UUID anchor                  |
| `DONE: ...`     | completed action item with UUID anchor                         |
| `STAT: <name> <value> <!--TS-->` | value of a stat declared on this thread — see `stat_line` |

The ACTION/TASK/DONE conventions match notes exactly — same line shape, same UUID anchoring. `tasks` ingest treats notes and logs identically as input domains.
