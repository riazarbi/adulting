---
name: commit-workflow
description: Reviews every uncommitted change in the vault, then stages and commits them with the `commit` tool — a short subject plus a body carrying a per-thread timeline of activity and a list of non-note changes. Activate when Riaz asks to commit, save, snapshot, or check in the vault — e.g. "commit the vault", "save my changes", "commit what's outstanding" — and when an automated prompt calls for an end-of-day commit.
---

# Skill: commit workflow

Loaded when the vault's uncommitted work needs to be written to git
history. The whole operation runs through the `commit` tool; there is
no other git access, and none is needed.

`commit` can only ever add a commit. It never amends, rebases,
resets, or pushes. A wrong message is fixed forward in the next
commit, never by rewriting.

## Review before save, always

`review` is read-only and stages nothing. Never call `save` without
having called `review` in this conversation — the body has to
describe changes you actually saw.

## Steps

1. **Review.** Invoke `commit ["review"]`.
2. **Build the timeline** from that output, per the rules below.
   Don't open files individually — `review` already carries the
   content.
3. **Compose the subject** — under 30 words, one line.
4. **Propose** the full subject and body, ending in `OK?`.
5. **On confirm**, invoke `commit ["save", ...]` and relay the short
   hash and path count it returns.

## Automated (non-interactive) runs

When the message is an automated prompt — it contains
`THIS IS AN AUTOMATED PROMPT` — **skip steps 4 and 5's confirm
round-trip entirely**. Nobody is reading; a proposal ending in `OK?`
would simply hang until the message expires and the commit would
never happen.

In that mode:

1. Call `commit ["review"]`.
2. Compose the subject and body exactly as specified below.
3. Call `commit ["save", ...]` immediately, in the same turn.
4. Report the short hash and path count, plus any truncation you
   could not resolve.

Never ask a clarifying question on an automated run. If something is
ambiguous, take the most likely reading, commit, and note the choice
in the report. This is the one place the role prompt's "writes require
confirmation" rule does not apply — the automated prompt is the
confirmation.

Everything else in this skill is unchanged: same review, same subject
rules, same two body sections.

## Reading `review` output

Three sections, in order:

- `Changed paths:` — every path, each tagged `modified`, `added`,
  `deleted`, `renamed`, `untracked`, and so on. This is the
  authoritative list of what `save` will commit.
- `Changes to tracked files:` — unified diffs of edits to files git
  already knows about.
- `New files:` — full content of untracked files, rendered as
  add-diffs. New notes and logs land here, not in the section above.

On a clean tree the whole output is
`no uncommitted changes; working tree clean` — relay that and stop.

### Truncation

Long files are capped at 150 lines and the whole report at 3000.
Both announce themselves in-band as `[truncated: ...]`.

If a truncated file matters for the timeline — a long note you can
only half-see — re-run with a higher cap (`--max-file-lines`,
`--max-lines`) rather than guessing. Raise it only for the file you
actually need. If you leave any truncation unresolved, say so in the
proposal.

## The subject

- Fewer than 30 words. One line. A multi-line value is rejected.
- Imperative mood — "Add measures spec", not "Added measures spec".
- Describes the commit as a whole, not any single file. Spanning
  many threads, pitch it at that level: "Log a week of Zeke, Syncro
  EV and Azania activity".

## The body

Two sections, in this order. Omit a section entirely if it has no
content — never emit an empty heading.

### Activity

A timeline of Riaz's activity across threads, drawn from the note
and log files in the review output.

Every one of these files lives in a thread's folder,
`threads/<Kind>/<Name>/`, so the path always names the thread: take
`<Kind>/<Name>`, the two folders after `threads/`.

| Source | Date from | Summarise from |
|--------|-----------|----------------|
| `threads/<Kind>/<Name>/logs/<date>.md` | the filename | `TEXT:` / `TASK:` / `REF:` / `STAT:` lines |
| `threads/<Kind>/<Name>/notes/<timestamp>.md` | `timestamp` frontmatter | `topic` frontmatter + body |
| `threads/<Kind>/<Name>/hours.md` | each entry's `startTime` | each **added** entry's `name` and duration |
| `threads/<Kind>/<Name>/payments.md` | each payment's `received` | each **added** payment's amount, currency and `note` |
| `threads/<Kind>/<Name>.md` gaining a `stats:` item | the day of the commit | "Declared stat `<name>`" |

`STAT: <name> <value>` lines are numbers he tracks. Gather a day's
values per stat into one phrase — "60 push-ups in three sets, run-km
5" — rather than one bullet per line.

Hours files matter as much as notes and logs. Much of Riaz's day leaves no
note and no log — it is captured only as time, and a timeline that skipped
it would report a quiet day when the opposite was true. The diff shows JSON,
so read the entries that were *added* and render them as activity, not as a
file edit:

```
### Processes/SGB
- 2026-09-11 — 1h 30m reviewing the finance pack, 15m circulating the
  August minutes.
```

Never list an hours or payments file under **Vault changes** — that
section is for configuration and assets. A changed hours or payments
file is always activity. Payments are JSON too: render each added one
as "Received ZAR 15,000.00 — September invoice", never add two
currencies together.

Group by thread, then order by date ascending within each thread.
Threads themselves in alphabetical order.

```
## Activity

### Projects/AXA DORA
- 2026-06-09 — Note "Visualising DORA metrics": reviewed the DORA
  website's visual management approach.

### Projects/Zeke
- 2026-08-15 — Specced a measures feature: per-thread typed
  measures, a `measure` command, and an agent tool and skill for
  logging them.
```

The `Kind/Name` in the path is already canonical — use it verbatim,
no `threads list` call needed.

A note can belong to several threads. It is filed under the first,
and its `threads:` frontmatter lists them all (as
`"[[Projects/AXA DORA]]"`; strip the brackets and quotes). List it
under each one.

### Vault changes

Everything that is **not** a note or a log — agent config, skills,
tool definitions, `.gitignore`, assets, anything else.

```
## Vault changes
- `.agent/skills/commit-workflow/` — this skill.
- `.agent/tools/commit.json` — regenerated tool definitions.
- `assets/` — 23 pasted images and a CAD export, referenced from
  the notes above.
```

## Passing the body

The whole body is ONE argument, with `\n` escapes for line breaks and
`\n\n` between paragraphs. Never split it across several arguments,
and never flatten it onto one line.

## Rules

- **Only report what `review` showed.** Never infer a change from a
  filename whose content you did not see, and never describe a file
  the review did not list. See the footguns skill on narrating
  results you did not receive.
- **Group assets, don't enumerate them.** Twenty pasted images are
  one bullet with a count, not twenty bullets.
- **The body is prose for a human reading `git log` in a year.**
  Say what happened and why it mattered; the diff already records
  which bytes changed. Don't restate the file list as the timeline.
- **Preserve Riaz's voice** when summarising a log line, as in the
  buffer workflow — compress, don't rewrite or improve.
- **One commit per invocation.** Don't try to split the working
  tree into themed commits; `save` stages everything with
  `git add -A`.
- **Nothing to commit is a success**, not an error. `save` on a
  clean tree prints `nothing to commit; working tree clean` and
  exits 0. Relay it and stop.

## Optional dry run

If the change set looks unlike what Riaz described, add `--dry-run`
to the `save` call before proposing. It prints what would be staged
and changes nothing.
