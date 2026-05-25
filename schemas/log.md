---
schema: log
scope: file
directory: logs
filename: ^\d{4}-\d{2}-\d{2}\.md$
---

# Log file

A per-thread per-day log of activity, derived from the buffer by `buffer flush`. Lives at `~/vault/logs/<Kind>/<Name>/<YYYY-MM-DD>.md`.

Logs are *output* of the buffer-flush ritual — not authored by hand in the way notes are. Each line is one buffer entry: a free-text observation (`TEXT:`), a reference to another file (`REF:`), or an action item (`ACTION:` / `TASK:` / `DONE:`). The day is the resolution; sub-day timestamps are not preserved.

`tasks` ingest scans `logs/` in addition to `notes/`, so ACTION lines in a log become backend tasks just like ACTION lines in a note. The log file is the action's source for sync purposes.

## Fields

| name   | required | type   | constraint                                        |
|--------|----------|--------|---------------------------------------------------|
| thread | yes      | string | regex=\[\[(Projects\|Processes\|Topics)/[^\]]+\]\] |
| date   | yes      | string | regex=\d{4}-\d{2}-\d{2}                            |
| type   | yes      | enum   | Log                                                |

## Body

| pattern         | meaning                                                       |
|-----------------|---------------------------------------------------------------|
| `REF: [[X]] ...` | reference to another file in the vault (note, thread, person) |
| `TEXT: ...`     | free-text observation                                          |
| `ACTION: ...`   | open action item — ingested by `tasks`                         |
| `TASK: ...`     | already-ingested action item with UUID anchor                  |
| `DONE: ...`     | completed action item with UUID anchor                         |

The ACTION/TASK/DONE conventions match notes exactly — same line shape, same UUID anchoring. `tasks` ingest treats notes/ and logs/ identically as input domains.
