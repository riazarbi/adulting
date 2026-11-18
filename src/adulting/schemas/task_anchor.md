---
schema: task_anchor
scope: line
applies_when: line =~ ^(TASK|DONE|DROPPED):
shape: ^(?P<kind>TASK|DONE|DROPPED):\s+(?:\[#(?P<priority>[^\]]+)\]\s+)?(?:\((?P<assignee>[^)]+)\)\s+)?(?P<body>.+?)\s+<!--\s*(?P<uuid>[a-f0-9]{8})\s+entry:(?P<entry>\d{4}-\d{2}-\d{2})(?:\s+end:(?P<end>\d{4}-\d{2}-\d{2}))?(?:\s+due:(?P<due>\d{4}-\d{2}-\d{2}))?(?:\s+scheduled:(?P<scheduled>\d{4}-\d{2}-\d{2}))?(?:\s+depends:(?P<depends>[a-f0-9,]+))?\s*-->\s*$
---

# Task anchor

A single `TASK:`, `DONE:` or `DROPPED:` line in a note or log file. `DONE:`
is a finished task, `DROPPED:` an abandoned one. The vault's
source-of-truth for task state — there is no separate backend. Written by
`tasks` ingest of `ACTION:` lines and mutated only via `tasks <subcommand>`;
not edited by hand.

## Fields

| name      | required | type   | constraint                          |
|-----------|----------|--------|-------------------------------------|
| kind      | yes      | enum   | TASK, DONE, DROPPED                 |
| priority  | no       | enum   | H, M, L                             |
| assignee  | no       | string | min=1                               |
| body      | yes      | string | min=1                               |
| uuid      | yes      | string | regex=[a-f0-9]{8}                   |
| entry     | yes      | string | regex=\d{4}-\d{2}-\d{2}             |
| end       | no       | string | regex=\d{4}-\d{2}-\d{2}             |
| due       | no       | string | regex=\d{4}-\d{2}-\d{2}             |
| scheduled | no       | string | regex=\d{4}-\d{2}-\d{2}             |
| depends   | no       | string | regex=[a-f0-9]{8}(,[a-f0-9]{8})*    |

## Cross-cutting rules (enforced in `lint`, not declarable in schema)

- `assignee` must resolve to `people/<name>.md`.
- `uuid` must be unique across the vault.
- Each id in `depends` must resolve to another `task_anchor.uuid`.
- The `depends` graph must be acyclic.
- `kind=DONE` and `kind=DROPPED` require `end`.
- `end >= entry` (string comparison; ISO dates sort lexically).

## Examples

```
TASK: [#H] (Sam Rivera) Send quarterly report <!--abcd1234 entry:2026-05-27 due:2026-05-29-->
TASK: Pick up dry cleaning <!--ef567890 entry:2026-05-27-->
DONE: [#M] (Charlie) Review the contract <!--abc12340 entry:2026-05-24 end:2026-05-27-->
DROPPED: (Jordan Blake) Send Northwind the revised scope <!--1a2b3c4d entry:2026-10-02 end:2026-11-18 due:2026-10-31-->
```

## Notes

- Priority lives in the visible `[#X]` token, never in the attrs blob.
- `entry` is the ingest date; `end` the date it was done or dropped. Day resolution —
  same-day tasks sort by other keys.
- Attrs order in the comment is fixed (`entry`, `end`, `due`, `scheduled`,
  `depends`) and produced by a single writer in `tasks`.
- The comment is hidden in Obsidian preview, so the reader sees only the
  visible portion (`TASK: [#H] (Sam Rivera) Send quarterly report`).
