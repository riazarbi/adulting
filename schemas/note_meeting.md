---
schema: note_meeting
scope: file
applies_when: type == Meeting
filename: \d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}\.md
---

# Meeting note

A note recording a meeting with one or more counterparties. Lives in `~/.adulting/notes/`.

## Fields

| name         | required | type   | constraint                                |
|--------------|----------|--------|-------------------------------------------|
| topic        | yes      | string |                                           |
| type         | yes      | enum   | Meeting                                   |
| thread       | yes      | string |                                           |
| timestamp    | yes      | string | regex=\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2} |
| counterparty | no       | string |                                           |
| location     | yes      | string |                                           |
| attendees    | yes      | string |                                           |

## Body

| pattern         | meaning                                                         |
|-----------------|-----------------------------------------------------------------|
| `- [ ] ...`     | open action item — must conform to `action_item` schema         |
| `- [x] ...`     | completed action item — same schema                             |
| `AGREED: ...`   | formal agreement — surfaced in `notes --minutes`                |
| `RESOLVED: ...` | formal resolution — surfaced in `notes --minutes`               |
| `!: ...`        | important callout — surfaced in `notes --pdf`                   |
