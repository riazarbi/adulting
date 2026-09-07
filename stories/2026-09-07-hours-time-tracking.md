# hours — consulting time tracking

Date: 2026-09-07

## User story

As a consultant who bills by the hour across several threads, I want to log
billable time from the command line into `$ADULTING_HOME`, in a format robust
enough that a semicolon in a description can never corrupt a rate, and
compatible enough with Obsidian tooling that I can build my own views over the
raw data. Today this lives outside the vault in an iOS-Shortcut-fed CSV that has
silently corrupted itself.

## Problem

Time tracking lives in `~/Library/Mobile Documents/com~apple~CloudDocs/task_logging/work.txt`
(145 rows, Jun 2022 → Sep 2026), a semicolon-delimited CSV written by an iOS
Shortcut and processed by the separate `worklog` repo:

```
Timestamp;Category;Status;Duration;Project;Description;Rate
17 Jun 2022 at 11:42;work;start;60;Arbi Family Trust;Trustee meeting; 2000
```

Every defect below is present in the live file today, except where noted:

| Defect | Evidence |
|---|---|
| **Delimiter collision corrupts money.** A `;` in the description shifts every later column. | 3 rows have 8 fields. Their parsed `Rate` values are `codereviewwithNick`, `refactorofexistingdagintoextract,phase1andphase2dags`, `addbusinessintentandcodeintentdoctrinestoeachnodelevelfunction`. |
| **Positional transposition parses "successfully".** | `11 May 2025 at 13:57;work;start;Arbi Family Trust;60;…` — Duration and Project swapped. Corrected by hand in the live file, but it survives in the stale `~/projects/worklog/task_logging/work.txt` copy that the downstream repo actually reads. |
| **No referential integrity on the project.** | `Arbi Family Trust` appears in 5 spellings (case + trailing whitespace), splitting totals. |
| **No currency column at all.** | Arbi Family Trust bills BWP (payments land at FNB Botswana); SANA Partners bills ZAR. Currently indistinguishable — totals across threads are meaningless. |
| **Dead columns.** | `Category` is `work` in 145/145 rows; `Status` is `start` in 145/145. |
| **Blank rows.** | 1. |

It also sits outside the vault, so it is not covered by `lint`, not in the
vault's git history, and not visible in Obsidian.

## Goal

A `hours` CLI that logs time into `$ADULTING_HOME`, in JSON embedded in
markdown, keyed to threads that must resolve, with per-entry currency and rate.

## Non-goals

- **Payments.** Deferred at the time, and delivered immediately after as the
  `payments` CLI (`payments/` tree, `statement` subcommand). See the Resolved
  section.
- **Invoice/PDF generation.** `hours report` emits totals; rendering a document
  is downstream and out of scope.
- **Running timers.** Every entry is logged after the fact. The schema permits a
  null `endTime` (the plugin's "running" state) but `hours` never writes one.
- **Installing the Simple Time Tracker plugin.** We match its format; we do not
  depend on it.

## Format decision

**JSON inside a ` ```simple-time-tracker ` fence in a markdown file.**

*Why not TOML.* The repo's design goals forbid pip installs, and Python's stdlib
`tomllib` is **read-only** — there is no stdlib TOML writer. Adopting TOML means
hand-rolling a serializer, which is precisely the class of bug we are escaping.
`json` round-trips in stdlib and escapes delimiters correctly by construction.

*Why this specific shape.* It satisfies the robustness requirement and the
Obsidian-compatibility requirement simultaneously, with no compromise: Simple
Time Tracker's on-disk format already *is* JSON embedded in a markdown fence.

### Verified plugin contract

Read from a clone of `Ellpeck/ObsidianSimpleTimeTracker` at v1.3.0
(`~/projects/ObsidianSimpleTimeTracker`):

```ts
// src/tracker.ts:5-15
export interface Tracker { entries: Entry[]; }
export interface Entry {
    name: string;
    startTime?: string;   // ISO 8601 UTC, e.g. "2022-09-27T19:51:18.000Z"
    endTime?: string;     // absent/null = running
    subEntries?: Entry[];
    collapsed?: boolean;
}
```

Facts we rely on, each verified in source:

1. **Timestamps are ISO 8601 UTC strings with milliseconds** (`tracker.ts:167`,
   and every fixture in `test-vault/`). Unix epochs were pre-0.1.8;
   `updateLegacyInfo` (`tracker.ts:390-394`) still coerces numeric strings, but
   ISO is the modern form and what we write.
2. **Unknown keys survive a plugin round-trip.** `loadTracker` does
   `JSON.parse(json) as Tracker` — a TypeScript cast, a runtime no-op, so extra
   keys remain on the object; `saveTracker` (`tracker.ts:28`) then
   `JSON.stringify`s that same object. Our `id`/`rate`/`currency` keys are
   therefore safe *even if the plugin is later installed and used*.
3. **The plugin imposes no file structure.** It is a code-block processor
   (`main.ts:27`); filenames, headings, and frontmatter are invisible to it.
   `loadAllTrackers` finds blocks by exact line match on ` ```simple-time-tracker `.
   Multiple independent blocks per file are supported.
4. **`name` is rendered as markdown** (`tracker.ts:445` → `572`
   `MarkdownRenderer.render`). It is a free-text field; "Segment" is only a UI
   column header.
5. **Duration is derived solely from `endTime − startTime`** (`tracker.ts:161-170`).
   There is no duration field.

### Deviations from plugin defaults, and why

- **Pretty-print with `indent=2`.** The plugin defaults to `prettyPrintJson:
  false` (one enormous line). The vault is a git repo synced with obsidian-git;
  a single-line blob makes every append a whole-file change and conflicts
  unmergeably. We are the only writer, so we choose the git-friendly form. The
  plugin reads it fine.
- **`name` holds the description, not a label.** See below.

## On-disk shape

One file per thread, mirroring the `threads/` kind directories so that
thread → path is a pure function:

```
$ADULTING_HOME/hours/Processes/Arbi Family Trust.md
$ADULTING_HOME/hours/Projects/SANA Partners.md
```

One `simple-time-tracker` block per file, flat entries (no group nodes):

````markdown
---
thread: "[[Projects/SANA Partners]]"
currency: ZAR
---

# SANA Partners — hours

```simple-time-tracker
{
  "entries": [
    {
      "name": "Bitemporal table design",
      "startTime": "2026-07-25T07:29:00.000Z",
      "endTime": "2026-07-25T09:29:00.000Z",
      "id": "a1b2c3d4",
      "rate": 2000,
      "currency": "ZAR"
    }
  ]
}
```
````

### `name` is the description

The description goes in `name`. There is no separate `description` key.

- `name` is the **only** field the plugin renders. A synthetic label there would
  make the table, "Copy as table", and "Copy as CSV" all display a useless
  column while the real content stayed invisible — forfeiting the compatibility
  we are buying.
- The thread already supplies the category dimension. **Thread = what this is
  about; `name` = what was done.**
- These descriptions are invoice line items. They belong in the primary rendered
  field.

Because names are markdown-rendered, `[[people/Darryl]]` in a description
renders as a clickable link — but it will **not** create a backlink or graph
edge, because Obsidian's metadata cache skips fenced code blocks. Clickable, not
indexed. Do not rely on it for graph work.

### Extra keys

| key | type | notes |
|---|---|---|
| `id` | string | 8-char uuid, unique vault-wide. Matches the `task_anchor` convention. Required for `edit`/`rm`/`show`. |
| `rate` | number | Per-hour charge. `0` means unbillable and is an ordinary, frequently-used value (41 of 145 historical rows). Treated exactly like any other rate — hours count, money is `rate x hours`. No `billable` flag. |
| `currency` | string | ISO 4217, `^[A-Z]{3}$`. |

**Values are resolved at write time and stored literally.** Changing a thread's
default rate must never retroactively re-price history, and changing its
currency must never silently re-denominate past work. The redundancy against
frontmatter is deliberate and costs ~20 bytes per entry.

### Duration and timezone

`hours` captures a date, a start time, and a duration in minutes. It writes
`startTime` and `endTime = startTime + minutes`.

This synthesises an interval the capture does not actually measure — the entry
is logged after the fact, not stopwatched. It is lossless for this use, but the
file asserts a precision the data does not have. Recorded here so nobody later
mistakes `endTime` for an observation.

Local time is converted to UTC on write via the machine's timezone. For
`import`, the historical CSV carries no timezone; `--tz` defaults to `+02:00`.
This is unambiguous for the whole history — SAST and CAT are both UTC+2 with no
DST.

## Defaults cascade

Resolved at write time, most specific wins:

| value | 1. flag | 2. thread frontmatter | 3. vault default |
|---|---|---|---|
| minutes | `--minutes` | — | `60` |
| rate | `--rate` | `rate:` | `2500` (`.adulting/config.yaml: hours.rate`) |
| currency | `--currency` | `currency:` | **none — hard error** |

Currency has no safe default; guessing it silently corrupts totals, which is one
of the defects we are fixing. If a thread has no `currency:` and none is passed,
`hours log` fails with the fix in the message:

```
hours: thread 'Projects/SANA Partners' has no currency
  set `currency: ZAR` in threads/Projects/SANA Partners.md, or pass --currency
```

The defaults are confirmed by the historical data: duration `60` is the mode
(93/145 rows), rate `2500` is the mode (34 rows).

## CLI surface

Naming: **`hours`**, not `time` — `time` is a zsh/bash reserved word
(`time foo` times a command), which would be a shell hazard on every machine.

### Non-interactive

```
hours log <thread> <description...> [-m MIN] [-r RATE] [-c CCY] [-d DATE] [-t TIME]
```

```
$ hours log "SANA Partners" "Second close and latent gain" -m 180
logged a1b2c3d4  SANA Partners  2026-09-07 15:23  3h 0m @ 2500 ZAR = 7500 ZAR
```

`<thread>` accepts the same forms as `threads show`: bare name (`SGB`), path
(`Projects/SGB`), or wikilink (`[[Projects/SGB]]`).

### Interactive

Invoked with no arguments. Follows the existing `threads new` prompt style
(numbered list, `input()`):

```
$ hours log
Thread:
  1. Processes/Arbi Family Trust
  2. Projects/SANA Partners
  3. Projects/Solid Insight
Pick: 2
Description: Second close and latent gain
Minutes [60]: 180
Rate [2500 ZAR]:
logged a1b2c3d4  SANA Partners  2026-09-07 15:23  3h 0m @ 2500 ZAR = 7500 ZAR
```

Only open threads are listed by default (matching `threads list`); `--all`
includes paused/closed.

### Full surface

| Command | What it does |
|---|---|
| `hours log <thread> <desc> [opts]` | Append an entry |
| `hours log` | Interactive capture |
| `hours list [thread] [--since D] [--until D] [--all] [--json]` | List entries |
| `hours report [--thread T] [--since D] [--until D] [--json]` | Totals grouped by thread **and currency** — never summed across currencies |
| `hours show <id> [--json]` | One entry |
| `hours edit <id> [-m\|-r\|-c\|-d\|-t\|--description]` | Mutate one field |
| `hours rm <id> [-y]` | Delete, with confirm |
| `hours import <path> [--apply] [--tz ±HH:MM]` | One-shot CSV migration, dry-run unless `--apply` |

`--json` on `list`/`report`/`show`, and `emit_helpjson_if_requested(parser)`,
per repo convention.

### Thread resolution

**A thread must resolve to an existing thread file, or the command fails
non-zero.** No auto-creation, no free-text fallback — that is exactly how the
CSV accumulated 5 spellings of one client.

`tasks`, `threads`, and `lint` each carry their own resolver today
(`tasks:230 thread_resolves`, `threads:resolve_thread`, `lint:302
resolve_wikilink`), consistent with the "one self-contained file per utility"
design goal. `hours` follows suit rather than introducing a shared module.

Resolution is **case-sensitive and whitespace-trimmed**. Note that
`Arbi Family Trust` and `Arbi family trust` both appear to resolve on macOS
purely because the filesystem is case-insensitive — on Linux (which the
`Dockerfile` targets) they would not. `import` must normalise explicitly rather
than inherit this accident.

## Schema and lint

**`schemas/thread.md`** — two optional fields added to the Fields table:

| name | required | type | constraint |
|---|---|---|---|
| currency | no | string | `regex=^[A-Z]{3}$` |
| rate | no | number | |

Both stay optional; most threads are never billed. `hours log` enforces
currency at write time, not `lint`.

**`schemas/hours_file.md`** — new, `scope: file`, `directory: time`:

- frontmatter `thread` (wikilink, required, must resolve) and `currency`
  (required)
- body contains exactly one `simple-time-tracker` fence
- the fence contains parseable JSON matching the `Tracker` shape
- every entry has `name`, `startTime`, `endTime`, `id`, `rate`, `currency`
- `endTime >= startTime`

**`lint`** gains a cross-vault check for `id` uniqueness, following the existing
`cross_check_tasks` precedent (`lint:493`). Validating JSON inside a fence is a
new validator kind — the existing `scope: file`/`scope: line` DSL does not cover
it, so this is a genuine (small) extension, in the same style as the existing
`_task_anchor_per_line` special case.

## Migration (completed, then removed)

`hours import` read the legacy CSV, classified every row, and put anything it
could not read cleanly through interactive triage. It ran once, on 2026-09-07,
and was then **deleted along with its tests** — it was a one-shot tool and
keeping it would have implied an ongoing sync that no longer exists.

Outcome of the run against 145 data rows:

| Outcome | Rows |
|---|---|
| Migrated | 119 (115 clean + 3 repaired + 1 triaged by hand) |
| Quarantined to `.adulting/hours-import-orphans.txt` | 26 (25 dead projects, 1 blank line) |

Reconciled after the fact against the CSV: all four threads match to the minute.

Two things it caught that a naive importer would not have:

- **Three rows whose descriptions contained `;`** parsed their rate as
  `codereviewwithNick` and similar. The parse rule — first five fields fixed,
  last field is Rate, everything between rejoined — recovered all three exactly,
  and each was confirmed in triage rather than trusted.
- **Three `Arbi family trust` rows** resolved on macOS (APFS is
  case-insensitive) and would have silently failed on Linux. Import folded case
  explicitly and reported every fold.

`work.txt` was left untouched and the iOS Shortcut that fed it has been retired,
so nothing writes to it any more.

## Acceptance criteria

1. `hours log "SANA Partners" "test" -m 90 -r 2500` writes a valid entry to
   `hours/Projects/SANA Partners.md` and prints the id.
2. `hours log NoSuchThread "x"` exits non-zero and writes nothing.
3. `hours log` with no args runs the interactive flow and produces an identical
   record to the non-interactive equivalent.
4. Logging against a thread with no `currency:` fails with the remediation in
   the message.
5. A description containing `;`, `,`, `"`, and `[[wikilink]]` round-trips
   byte-identically through write → read → `hours show`. *(This is the specific
   failure that motivated the story.)*
6. `hours report` groups by currency and never emits a cross-currency total.
7. `lint` passes on a vault containing time files, and fails on a time file with
   a duplicate `id`, unparseable JSON, or an unresolvable `thread`.
8. Written files render correctly in Obsidian with the Simple Time Tracker
   plugin installed — table populated, durations and totals correct — confirming
   format compatibility.
9. Tests cover the above using the existing `tests/conftest.py` `vault`
    fixture, with a `write_time_file` helper added.

## Resolved

1. **`rate: 0` is an ordinary rate.** Unbillable work is logged often and is
   first-class. `hours` treats it identically to any other rate: hours always
   count toward duration totals, money is `rate x hours`, and a `0` row
   contributes real time and no money. No special-casing, no separate
   "unbilled" report line, no `billable` flag.
2. **Orphan projects do not need to be queryable.** They are quarantined to
   `.adulting/hours-import-orphans.txt` and go no further. No closed threads are
   created for them.
3. **The iOS Shortcut is retired.** `hours import` is therefore a *one-shot*
   migration, not an ongoing sync. It does not need to be idempotent against a
   growing file, and `work.txt` becomes a frozen historical artifact after the
   migration is verified. Capture moves entirely to the CLI.

## Delivered beyond the original spec

- **`time/` renamed to `hours/`** so the directory matches the command. The
  command could not become `time` — that is a zsh/bash reserved word.
- **`threads new` now collects `currency` and `rate`** (both optional, blank
  skips). Without it, every new billable thread needed a hand-edit of YAML
  before the first `hours log` would work.
- **`_vault.py`** extracts the ~200 lines `hours` and `payments` share —
  frontmatter, thread resolution, block splice, config, money formatting.
  Following the existing `_suggester.py` / `_argparse_helpjson.py` pattern
  rather than letting two copies of the block-splice logic drift.
- **`payments` CLI** with a `statement` subcommand: billed (from `hours/`) vs
  received vs outstanding, per thread and currency.
- **Decimal money arithmetic** throughout both tools, so `hours report` and
  `payments statement` agree exactly instead of drifting by float error.
- **`hours import` removed** after its single use.
