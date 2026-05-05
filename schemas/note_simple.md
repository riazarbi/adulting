---
schema: note_simple
scope: file
applies_when: type in [Workshop, Report, Log, Research]
filename: \d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}\.md
---

# Simple note

A note for any of the bare-shape types: Workshop, Report, Log, or Research. No type-specific fields beyond the common four. Lives in `~/.adulting/notes/`.

## Fields

| name      | required | type   | constraint                                |
|-----------|----------|--------|-------------------------------------------|
| topic     | yes      | string |                                           |
| type      | yes      | enum   | Workshop, Report, Log, Research           |
| thread    | yes      | string |                                           |
| timestamp | yes      | string | regex=\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2} |

## Body

| pattern         | meaning                                                         |
|-----------------|-----------------------------------------------------------------|
| `- [ ] ...`     | open action item — must conform to `action_item` schema         |
| `- [x] ...`     | completed action item — same schema                             |
| `AGREED: ...`   | formal agreement — surfaced in `notes --minutes`                |
| `RESOLVED: ...` | formal resolution — surfaced in `notes --minutes`               |
| `!: ...`        | important callout — surfaced in `notes --pdf`                   |
