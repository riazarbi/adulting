---
schema: note_correspondence
scope: file
applies_when: type == Correspondence
filename: \d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}\.md
---

# Correspondence note

A note recording email, message, or letter exchanges with one or more participants. Lives in `~/.adulting/notes/`.

## Fields

| name      | required | type   | constraint                                |
|-----------|----------|--------|-------------------------------------------|
| topic     | yes      | string |                                           |
| type      | yes      | enum   | Correspondence                            |
| thread    | yes      | string | regex=\[\[(Projects\|Processes\|Topics)/[^\]]+\]\] |
| timestamp | yes      | string | regex=\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2} |
| people    | no       | list   |                                           |

`thread` is a single wikilink to a project, process, or topic thread. `people` is a list whose entries may be wikilinks `[[people/X]]` (validated to resolve) or plain strings (untracked participants).

## Body

| pattern         | meaning                                                         |
|-----------------|-----------------------------------------------------------------|
| `ACTION: ...`   | open action item — ingested into taskwarrior by `tasks`         |
| `TASK: ...`     | already-ingested action item                                    |
| `AGREED: ...`   | formal agreement — surfaced in `notes --minutes`                |
| `RESOLVED: ...` | formal resolution — surfaced in `notes --minutes`               |
| `!: ...`        | important callout — surfaced in `notes --pdf`                   |
