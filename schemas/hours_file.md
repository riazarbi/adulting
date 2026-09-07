---
schema: hours_file
scope: file
directory: hours
filename: ^[^.]+\.md$
---

# Hours file

Billable time for one thread. One file per thread, living at
`~/vault/hours/{Projects,Processes,Topics}/<Thread>.md` — mirroring the
`threads/` layout so that thread → path is a pure function.

The body carries exactly one ` ```simple-time-tracker ` fenced block containing
JSON in the shape Obsidian's Super Simple Time Tracker plugin reads, so the
entries render natively and any tool that understands that format can query
them. Written and maintained by the `hours` CLI.

## Fields

| name     | required | type   | constraint                        |
|----------|----------|--------|-----------------------------------|
| thread   | yes      | string |                                   |
| currency | yes      | string | regex=^[A-Z]{3}$                  |

## Body

| pattern                     | meaning                                          |
|-----------------------------|--------------------------------------------------|
| ` ```simple-time-tracker `  | opens the entry block — exactly one per file      |
| JSON `{"entries": [...]}`   | the block's sole content; must parse              |

### Entry object

Each element of `entries` is one logged session.

| name      | required | type   | constraint                                          |
|-----------|----------|--------|------------------------------------------------------|
| name      | yes      | string | the description — what was done. Rendered as markdown by the plugin |
| startTime | yes      | string | ISO 8601 UTC, `YYYY-MM-DDTHH:MM:SS.mmmZ`             |
| endTime   | yes      | string | same form; must be >= startTime                      |
| id        | yes      | string | 8 hex chars, unique across the whole vault           |
| rate      | yes      | int    | per-hour charge; `0` means unbillable and is ordinary |
| currency  | yes      | string | ISO 4217, `^[A-Z]{3}$`                               |

## Notes

- `thread` must be a wikilink to `Projects/X`, `Processes/X`, or `Topics/X`, and
  must resolve to an existing thread file. `lint` enforces resolution for any
  scalar `thread` field, so the constraint cell is deliberately empty.

- `name` holds the description, not a label. It is the only field the plugin
  renders, and these descriptions are invoice line items.
- `rate: 0` is a normal value, not a sentinel. Hours still count toward
  duration totals; the money is simply zero.
- `rate` and `currency` are stored per entry, resolved at write time, so that
  changing a thread's defaults never retroactively re-prices or
  re-denominates history. The redundancy against frontmatter is deliberate.
- Duration is derived from `endTime - startTime`; there is no duration field.
  The interval is synthesised from a logged start plus a duration, so it
  asserts more precision than the capture actually has.
- The plugin's `subEntries` (grouping) and `collapsed` keys are valid in the
  format but unused by `hours`.
- JSON is pretty-printed at `indent=2` rather than the plugin's single-line
  default, so that appends produce readable, mergeable git diffs.
