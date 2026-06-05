---
schema: thread
scope: file
directory: threads
filename: ^[^.]+\.md$
---

# Thread file

Markdown file holding a chronological log of an ongoing project, process, or relationship. One file per thread. Lives in `~/vault/threads/` (top-level for projects/processes; commonly under `~/vault/threads/People/` for relationships, but flat layouts are also valid).

## Fields

| name      | required | type   | constraint                                            |
|-----------|----------|--------|-------------------------------------------------------|
| status    | yes      | enum   | open, paused, closed                                  |
| kind      | yes      | enum   | project, process, topic                               |
| category  | yes      | enum   | professional, personal, voluntary                     |
| started   | yes      | string | regex=\d{4}-\d{2}-\d{2}                               |
| ended     | no       | string | regex=\d{4}-\d{2}-\d{2}                               |
| cadences  | no       | list   | list of objects with `key`, `frequency`, `description` |

`ended` is required when `status` is `closed`.

### Cadences

If a thread has recurring obligations (a tax return, a quarterly review, a monthly catch-up with a person), declare them as a list under `cadences`:

```yaml
cadences:
  - key: tax_return
    frequency: 31
    description: Monthly tax return, file before 7th
  - key: quarterly_review
    frequency: 90
    description: All-hands with trustees
```

Per-cadence fields:

| name        | required | type   | constraint                              |
|-------------|----------|--------|-----------------------------------------|
| key         | yes      | string | unique within the thread; used as a tag |
| frequency   | yes      | int    | interval in days (e.g. 7, 31, 90, 365)  |
| description | yes      | string | what this cadence is for                |

A cadence is "satisfied" when a log entry tagged `#<key>` is added to the thread. `threads --overdue` reports cadences whose most-recent matching entry is older than `frequency` days (or that have never been satisfied).

## Body

| pattern              | meaning                                                          |
|----------------------|------------------------------------------------------------------|
| `- YYYY-MM-DD — ...` | log entry — must conform to `thread_entry` schema                |
| `#<cadence_key>`     | tag inside an entry that satisfies the named cadence             |
| indented sub-bullets | continuation / detail for the entry above (not separately validated) |

## Notes

- Out-of-order dates are tolerated — manual edits happen.
- An H1 with the thread name in the body is optional but encouraged for standalone readability in Obsidian.
- For an entry that warrants structure (multiple fields, links, action items), spawn a *note* and link to it from the thread bullet (`- 2024-04-28 — Vendor decision [[2024-04-28-14-30-00]]`). Threads stay a cheap chronological log; notes are the home for typed records.
