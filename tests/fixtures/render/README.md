# Render fixtures

`<name>.md` is a note; `<name>.<kind>.expected.md` is what `notes pdf`,
`notes minutes` or `notes agenda` prints for it today, byte for byte.

They were captured from the bash renderers these replaced, so "matches the
old script" is all they prove. Where the old output is wrong, it is listed
below and in the deferred bugs at the end of
`stories/2026-09-17-python-package-refactor.md`. A fixture may not be
changed by accident: regenerate deliberately, and say so in the changelog.

## KNOWN-WRONG output pinned here

| Where | What | Deferred bug |
|---|---|---|
| `*.minutes.expected.md` action table | An empty table prints `\| None \| None \| None \|` instead of saying there are none | 12 |
| `*.minutes.expected.md` summary | `No minutes agreements were made.` (for *minuted* agreements), beside `No Resolutions were passed.` with its odd capital | 13 |
| every header | `date: 2026-07-15 ` carries a trailing space; a note with no frontmatter gets `subtitle: ` and `date:  ` | 14 |
| `meeting_full.*.expected.md` | `- [[Projects/Not A Person]]` is listed as an attendee, wikilink and all | 11 |
| `meeting_full.minutes.expected.md` | A `TASK:` line's `[#H]` lands in the task text and the row is credited to the owner | 2 |
| `*.pdf.expected.md` | The callouts replace the note's own `# Summary` section, taking its `## Minuted Agreements` heading with it | 10 |
