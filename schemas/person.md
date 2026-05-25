---
schema: person
scope: file
directory: people
filename: ^[^.]+\.md$
---

# Person file

A markdown file for someone you track — a contact you want to maintain a relationship with. Lives in `~/vault/people/`. People are link targets (`[[people/<name>]]`) for `note.people` and action `assignee:`. They are *not* threads — they cannot be the value of `note.thread`.

## Fields

| name     | required | type   | constraint                                            |
|----------|----------|--------|-------------------------------------------------------|
| status   | yes      | enum   | open, paused, closed                                  |
| category | yes      | enum   | professional, personal, voluntary                     |
| started  | yes      | string | regex=\d{4}-\d{2}-\d{2}                               |
| ended    | no       | string | regex=\d{4}-\d{2}-\d{2}                               |
| cadences | no       | list   |                                                       |

`ended` is required when `status` is `closed`. Cadences follow the same shape as on threads (list of `{key, frequency, description}`).

## Body

Free-form. Bullets, prose, links — whatever helps you remember the person and your interactions with them.
