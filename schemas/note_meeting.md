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
| thread       | yes      | string | regex=\[\[(Projects\|Processes\|Topics)/[^\]]+\]\] |
| timestamp    | yes      | string | regex=\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2} |
| counterparty | no       | string |                                           |
| location     | yes      | string |                                           |
| people       | no       | list   |                                           |

`thread` is a single wikilink to a project, process, or topic thread. `people` is a list whose entries may be wikilinks `[[people/X]]` (validated to resolve) or plain strings (untracked attendees).

## Body

| pattern         | meaning                                                         |
|-----------------|-----------------------------------------------------------------|
| `ACTION: ...`   | open action item — ingested into taskwarrior by `tasks`         |
| `TASK: ...`     | already-ingested action item (after `tasks` has run)            |
| `AGREED: ...`   | formal agreement — surfaced in `notes --minutes`                |
| `RESOLVED: ...` | formal resolution — surfaced in `notes --minutes`               |
| `!: ...`        | important callout — surfaced in `notes --pdf`                   |
