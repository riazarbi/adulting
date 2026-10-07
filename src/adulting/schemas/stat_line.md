---
schema: stat_line
scope: line
applies_when: line =~ ^STAT:
shape: ^STAT:\s+(?P<name>\S+)\s+(?P<value>\S+)\s+<!--(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})-->\s*$
---

# Stat line

One value of a declared stat, in a thread's daily log. Written by
`buffer flush` from a `stats log` entry; a mistake is fixed by editing it.

## Fields

| name  | required | type   | constraint                           |
|-------|----------|--------|--------------------------------------|
| name  | yes      | string | regex=[a-z0-9]+(-[a-z0-9]+)*          |
| value | yes      | string | regex=-?\d+(\.\d+)?                   |
| ts    | yes      | string | regex=\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2} |

## Cross-cutting rules (enforced in `lint`, not declarable in schema)

- A `STAT:` line belongs in a log, not in a note or a thread file.
- `name` must be declared in the `stats:` of the log's own thread.
- `value` must be a whole number when the stat's `type` is `int`.
- The date of `ts` must be the log's `date`.

## Examples

```
STAT: pushups 25 <!--2026-10-07T07:42:10-->
STAT: run-km 5.2 <!--2026-10-07T18:05:00-->
```

## Notes

- The timestamp is local time, as the buffer writes it. It is the only
  log line that keeps one: a series orders a day's values by it.
- The comment is hidden in Obsidian preview, so the reader sees
  `STAT: pushups 25`.
