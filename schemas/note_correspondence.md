---
schema: note_correspondence
scope: file
applies_when: type == Correspondence
filename: \d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}\.md
---

# Correspondence note

A note recording email, message, or letter exchanges with one or more participants. Lives in `~/.adulting/notes/`.

## Fields

| name         | required | type   | constraint                                |
|--------------|----------|--------|-------------------------------------------|
| topic        | yes      | string |                                           |
| type         | yes      | enum   | Correspondence                            |
| thread       | yes      | string |                                           |
| timestamp    | yes      | string | regex=\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2} |
| participants | yes      | string |                                           |

## Body

| pattern         | meaning                                                         |
|-----------------|-----------------------------------------------------------------|
| `- [ ] ...`     | open action item — must conform to `action_item` schema         |
| `- [x] ...`     | completed action item — same schema                             |
| `AGREED: ...`   | formal agreement — surfaced in `notes --minutes`                |
| `RESOLVED: ...` | formal resolution — surfaced in `notes --minutes`               |
| `!: ...`        | important callout — surfaced in `notes --pdf`                   |
