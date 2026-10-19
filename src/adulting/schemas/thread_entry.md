---
schema: thread_entry
scope: line
applies_when: line =~ ^- \d{4}-\d{2}-\d{2} —
shape: ^- (?P<date>\d{4}-\d{2}-\d{2}) — (?P<text>.+)$
---

# Thread log entry

A single dated bullet at the top level of a thread file's body. Indented sub-bullets are continuation / detail and are not separately validated.

## Fields

| name | required | type   | constraint                |
|------|----------|--------|---------------------------|
| date | yes      | string | regex=\d{4}-\d{2}-\d{2}   |
| text | yes      | string | min=1                     |

## Examples

```
- 2024-04-28 — Started on the IB integration.
    - Got the docker image working
    - Hit auth wall, debugging
- 2024-05-17 — Made progress on rblncr.
- 2024-06-01 — Vendor decision finalised [[2024-06-01-14-30-00]].
```
