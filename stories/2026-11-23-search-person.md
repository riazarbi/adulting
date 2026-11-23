# search — people as a filter dimension

## Problem

A person file is a name and some frontmatter. Everything worth knowing
about the person is elsewhere: the meetings they attended, the log lines
that mention them, the tasks they owe. That picture is a projection of the
whole vault along the person's name, and `search` cannot draw it.

`search` filters on thread, type, date and text. Thread is an attribute
of a record, read from frontmatter, not a folder namespace: a note filed
under its first thread still matches `--thread` for every other thread it
names. People fit the same model, since they were never folders, but no
subcommand accepts one.

People appear in the vault in several forms. Counted against the real
vault (773 files under `threads/`):

| Form                                               | Count |
|----------------------------------------------------|-------|
| `[[people/X]]` in a note's `people:` frontmatter   | 422   |
| `[[people/X]]` in a note body or log line          | 34    |
| Assignee on an `ACTION/TASK/DONE/DROPPED` line     | 252   |
| Plain string in `people:` (no person file)         | 31    |
| Full name in body text, not linked (file × person) | 148   |

No link was broken or wrongly cased. A link-only view, such as an Obsidian
backlink query, sees the first two rows. It misses every assignee and every
unlinked mention.

Today the nearest call is `search notes --text "Jordan Blake"`, and then
`search logs --text …`. That matches substrings, cannot tell an attendee
from a passing mention, ignores assignees as such, and cannot be combined
with a person on `stream` or `activity`.

## Scope

`search` gains a person dimension that sits beside thread:

- a `--person` filter wherever `--thread` exists
- a `person` subcommand, which does for one person what `overview` does
  for one thread

This story covers CLI behaviour for any caller. The `recall` skill row
("everything with Jordan", "when did I last speak to Dana") is a separate
agent story.

Out of scope: hours and payments (neither record carries people), person
file schema changes, and lint suggestions for unlinked mentions.

## One rule for "this record refers to X"

A single function finds references to a person in a record and says how
each was found. Every person-aware command uses it, so they cannot drift.

| via        | Matches                                                                 |
|------------|-------------------------------------------------------------------------|
| `link`     | `[[people/X]]` anywhere, including `[[people/X|alias]]`                 |
| `assignee` | `(X)` heading an `ACTION/TASK/DONE/DROPPED` line                        |
| `attendee` | a plain string `X` in a note's `people:` list                           |
| `text`     | `X`'s full name as a whole word sequence in the body, case-insensitive, not inside a link |

`X` is always a declared person: one with a `people/<X>.md` file. Plain
text counts only because it spells a declared person's full name, so the
person file is what makes the match. A name with no file is not a person
to `search`. Use `--text` for that.

A record that matches more than one way reports the strongest, in the
order above. The README states the rule.

## Resolving `NAME`

`--person` and `search person` take a name and resolve it the way
`--thread` resolves a thread:

- an exact match on a `people/<Name>.md` stem, with `people/` allowed as
  a prefix
- otherwise a single case-insensitive fuzzy match against the people
  roster
- several candidates: exit non-zero and list them
- no candidate: exit non-zero with `person not found: NAME`, and point
  at `--text` for names that have no person file

## `--person` on existing subcommands

    search notes    [--person P] …
    search logs     [--person P] …
    search stream   [--person P] …
    search activity [--person P] …

Combines with every other filter: `--thread Northwind --person "Jordan
Blake"` is Jordan on Northwind.

- **notes / logs**: a file matches if any reference is found. The row
  gains a `via` field. The snippet is the matching line, as it is for
  `--text`. With both `--text` and `--person`, the snippet follows `--text`.
- **stream**: line-level. A log line, task event or pending buffer line
  matches on its own content. A note event matches if the note matches.
  Events gain a `via` field.
- **activity**: counts only records that match, so the ranking answers
  "which threads does this person come up on, and how much".

## `search person NAME`

    search person NAME [--since D] [--until D] [--limit N] [--json]

The person equivalent of `overview`. Pointers and counts, never bodies:

    Jordan Blake

      first seen   2025-03-13
      last seen    2026-11-23
      notes          24   (Meeting 19, Correspondence 5)
      log lines      11
      tasks          3 open, 14 done, 1 dropped   (assigned)

      threads:
        Projects/Northwind              29   2026-11-23
        Processes/Rivera Family Trust    6   2026-08-03

      recent:
        <path>  2026-11-23  Meeting   link      Quarterly review
        <path>  2026-11-16  Log       assignee  (Jordan Blake) Send the management accounts
        …

`--limit` caps `recent` (default 5, 0 for all), as on `overview`. With
`--json`, the same data as one object.

The full chronology is `search stream --person NAME`. `search person`
does not repeat it.

## Decisions

1. **Plain-text matching is on**, reported as `via: text`, but only for
   the full name of a declared person. Without it, 148 known mentions are
   invisible.
2. **Full name only.** First names alone collide (`Leah Rivera`, `Mia
   Rivera`, and the owner is `Sam Rivera`). Optional `aliases:` on the
   person file is a later story.
3. **Undeclared names are rejected.** `--person` and `search person`
   need a person file. Anything else is `--text`.
4. **Performance is measured.** `search` re-reads the vault on every
   call. Adding a person scan to each record must keep `stream` within
   its current time on the real vault, measured before and after.

## Acceptance

- Each `via` form has a test, using the test names (`Remy Dorn`, `Bram
  Halvorsen`, `SQR`, `SARO Partners`).
- `--thread X --person Y` returns the intersection.
- An ambiguous `NAME` exits non-zero and lists the candidates.
- A `NAME` with no person file exits non-zero with `person not found`,
  on every subcommand that takes one.
- A full name with no person file, written in a body, is never reported
  as a person reference.
- A link `[[people/Remy Dorn|Remy]]` matches as `link`, not `text`.
- A full name inside a link is not counted again as `text`.
- `search person` counts agree with `search notes --person`, `search logs
  --person` and `search stream --person --kind task,done,dropped` over the
  same window.
- `MANUAL.md` and `dev/tools/search.json` regenerate from the help strings.
- `dev/ci` passes.
