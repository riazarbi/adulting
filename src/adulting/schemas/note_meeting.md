---
schema: note_meeting
scope: file
applies_when: type == Meeting
path: threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md
---

# Meeting note

A note recording a meeting with one or more counterparties. Lives in the folder of the first thread it names, at `~/vault/threads/<Kind>/<Name>/notes/<stem>.md`.

## Fields

| name         | required | type   | constraint                                |
|--------------|----------|--------|-------------------------------------------|
| topic        | yes      | string |                                           |
| type         | yes      | enum   | Meeting                                   |
| threads      | yes      | list   | regex=\[\[(Projects\|Processes\|Topics)/[^\]]+\]\] |
| timestamp    | yes      | string | regex=\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2} |
| counterparty | no       | string |                                           |
| location     | no       | string |                                           |
| people       | no       | list   |                                           |

`threads` is a list of wikilinks; each entry must resolve to a thread file at `threads/<Kind>/<Name>.md` (Projects / Processes / Topics). A note can belong to multiple threads; it is filed under the first, and `lint` checks that the folder it is in is that first thread's. `people` is a list whose entries may be wikilinks `[[people/X]]` (validated to resolve) or plain strings (untracked attendees).

## Body

| pattern         | meaning                                                         |
|-----------------|-----------------------------------------------------------------|
| `ACTION: ...`   | open action item — ingested into the backend by `tasks`         |
| `TASK: ...`     | already-ingested action item (after `tasks` has run)            |
| `AGREED: ...`   | formal agreement — surfaced in `notes --minutes`                |
| `RESOLVED: ...` | formal resolution — surfaced in `notes --minutes`               |
| `!: ...`        | important callout — surfaced in `notes --pdf`                   |
