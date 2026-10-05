---
schema: note_correspondence
scope: file
applies_when: type == Correspondence
path: threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md
---

# Correspondence note

A note recording email, message, or letter exchanges with one or more participants. Lives in the folder of the first thread it names, at `~/vault/threads/<Kind>/<Name>/notes/<stem>.md`.

## Fields

| name      | required | type   | constraint                                |
|-----------|----------|--------|-------------------------------------------|
| topic     | yes      | string |                                           |
| type      | yes      | enum   | Correspondence                            |
| threads   | yes      | list   | regex=\[\[(Projects\|Processes\|Topics)/[^\]]+\]\] |
| timestamp | yes      | string | regex=\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2} |
| people    | no       | list   |                                           |

`threads` is a list of wikilinks; each entry must resolve to a thread file at `threads/<Kind>/<Name>.md`. A note can belong to multiple threads; it is filed under the first, and `lint` checks that the folder it is in is that first thread's. `people` is a list whose entries may be wikilinks `[[people/X]]` (validated to resolve) or plain strings (untracked participants).

## Body

| pattern         | meaning                                                         |
|-----------------|-----------------------------------------------------------------|
| `ACTION: ...`   | open action item — ingested into the backend by `tasks`         |
| `TASK: ...`     | already-ingested action item                                    |
| `AGREED: ...`   | formal agreement — surfaced in `notes --minutes`                |
| `RESOLVED: ...` | formal resolution — surfaced in `notes --minutes`               |
| `!: ...`        | important callout — surfaced in `notes --pdf`                   |
