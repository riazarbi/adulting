# adulting

Scripts to help me organise my day-to-day life. Everything stores plain-text state under `~/vault/` so the data outlives any one tool — you can grep it, back it up, sync it, or browse the whole directory as an Obsidian vault.

## Conceptual model

- **Note** — a persisted piece of information. The workhorse object: meeting records, correspondence, reports, ad-hoc logs, research. Notes live in the folder of the first thread they name, `~/vault/threads/<Kind>/<Name>/notes/`, and have YAML frontmatter (topic, type, threads, timestamp, etc.) plus a free-form body.
- **Thread** — an organising lens for notes. Three kinds: `project` (bounded), `process` (ongoing), `topic` (interest area / catchall). A thread is a file, `~/vault/threads/<Kind>/<Name>.md` (`<Kind>` is Projects, Processes or Topics), and a folder beside it, `~/vault/threads/<Kind>/<Name>/`, that holds everything belonging to the thread: its notes, logs, hours and payments. Closing a thread is setting `status: closed`; nothing moves.
- **Person** — a contact you track. People live in `~/vault/people/` and are link targets — never threads themselves.
- **Time entry** — a billable (or unbillable) session of work on a thread. Entries live in the thread's `hours.md` as JSON inside a ```simple-time-tracker fence, so Obsidian's Super Simple Time Tracker format renders them natively.
- **Payment** — money received against a thread. Records live in the thread's `payments.md`, same shape as hours.
- **Log** — a per-thread, per-day file at `~/vault/threads/<Kind>/<Name>/logs/<date>.md`, written by `buffer flush`. Its body is a list of statements: `TEXT:` observations, `REF:` pointers to other vault files, and the `TASK:`/`DONE:` anchors that `tasks` manages.
- **Action** — a task. Notes and logs contain `ACTION:` lines that the `tasks` bridge ingests by rewriting them in place to `TASK:` anchors with an 8-char uuid and inline attrs (`entry`, `due`, `scheduled`, `priority`, `depends`). Source files are the only store — there is no backend.
- **Stat** — a number tracked over time: push-ups, steps, money spent. A stat is declared once in a thread file's frontmatter (`stats:`), and each value lands in that thread's log as a `STAT:` line. An event is an `int` stat logged as `1`.
- **Buffer** — `~/vault/buffer.md`, the staging queue for quick captures. `buffer add-*`, `tasks add`, `stats log` and the `REF:` pointers other commands drop all go here first; `buffer flush` files them into the threads' daily logs.

### Notes, logs and hours

Three stores, three questions. They are not competing for the same content.

| Store | Answers | Weight |
|---|---|---|
| **Note** | what was said, decided, researched | heavyweight — frontmatter, structure, a document |
| **Log** | what happened on this thread today | lightweight — one line, no ceremony |
| **Time entry** | how long it took | a label and a duration |

**Logs are the general-purpose capture surface.** They exist so that recording something about a thread does not require writing a note. Anything worth remembering that does not justify a document belongs there: an observation, a decision, a pointer to another file, a half-formed thought.

**Hours answer a different question and should not be asked to hold content.** An entry's `name` is an invoice line item — a short label naming the work, not a narrative. Two reasons to keep it that way:

- It is the only field the Obsidian tracker plugin renders, and it appears verbatim on a client's statement of account.
- **`search` indexes notes and logs, not hours.** Detail written into an entry's `name` cannot be found later by `search --text`. Content in hours is content you have hidden.

So a rich afternoon produces both: a log line carrying what actually happened, and a time entry carrying the duration under a short label.

**Every record points at itself from the log.** `notes new`, `hours log` and `payments log` each drop a `REF:` into the buffer, which lands in the thread's daily log on the next `buffer flush`. A thread's log for a day is therefore the chronology of everything that touched it — notes written, time worked, money received, tasks opened and closed — and not just the part somebody remembered to write down. Each pointer is filed under the day the thing happened, not the day of the flush, so backdated work lands in the right day's log. These pointers are best-effort: the record is written whether or not the buffer can be.

```
log:    TEXT: Validated the SQL detection patterns with [[people/Priya ...]]; the
              join semantics on multi-repo commits are still unresolved.
hours:  Projects/Fabrikam DORA   3h 0m   "DORA metric validation"
```

A trivial item needs no log line — "5k run, 30 minutes" is a duration and a label and nothing more. Write a log line when there is something to say beyond the label.

Commitments are neither: `tasks add` writes an `ACTION:` line that becomes a `TASK:` anchor inside a log.

This division is why `hours` accepts threads with no currency: a 5k run and a client's afternoon are both blocks of time, and only one is billable. `search activity` rolls notes, logs and hours together, so a thread you worked on but never wrote about still shows up.

# Installation

The commands are console scripts of the `adulting` Python package. Install it
with pipx, which puts each command on your `PATH` in its own environment:

```zsh
git clone git@github.com:riazarbi/adulting.git ~/projects/adulting
pipx install ~/projects/adulting
```

To work on the code, install it editable in a venv instead, which is what the
tests use:

```zsh
cd ~/projects/adulting
uv venv .venv && uv pip install --python .venv/bin/python -e '.[dev]'
dev/ci                 # lint + tests + coverage
```

Installed commands: `tasks`, `notes`, `search`, `threads`, `people`, `hours`,
`payments`, `stats`, `buffer`, `lint`, `commit`. They are generic names; if one clashes
with something else on your `PATH`, the clash is yours to resolve.

## Dependencies

- Python 3.11 or newer. No third-party runtime dependencies.
- `git` — required by `commit`
- `pandoc` and a LaTeX engine (`xelatex` via e.g. MacTeX or TeX Live) — required by `notes pdf`, `notes minutes`, `notes agenda` and `payments statement --pdf`

## One-time setup

Nothing to install — task state lives in source notes themselves. The vault location follows `ADULTING_HOME` if set (default `~/vault`).

- For `commit`, make the vault the root of a git repository (`git init ~/vault`).
- For Obsidian, set the two link options in [INTEGRATIONS.md](INTEGRATIONS.md); without them Obsidian writes links `lint` rejects.
- Optionally, create `~/vault/.adulting/config.yaml`. Every key is optional:

```yaml
# .adulting/config.yaml
owner: Your Name          # named on rendered notes; supplier name fallback
hours:
  rate: 2500              # default hourly rate for billable threads
  minutes: 60             # default duration for `hours log`
billing:                  # supplier and banking details for PDF statements
  supplier_name: ...
```

See [payments](#payments) for the full `billing:` section.

## Reference

[MANUAL.md](MANUAL.md) is the operator's manual: every subcommand and flag, everyday procedures, data formats and troubleshooting. It is generated from the CLI itself and checked against it in CI, so where this README and the manual disagree, the manual is right. Every command also answers `--help` and `--help-json`.

# Commands

What follows is the design and the reasoning behind each command. For exact syntax, see [MANUAL.md](MANUAL.md).

## notes

Markdown note taker. Notes live in their first thread's folder, `~/vault/threads/<Kind>/<Name>/notes/`, as `<timestamp>.md` files with YAML frontmatter and a free-form body. The stem is unique across the vault, so a note is named by its stem alone.

### Frontmatter

| Field        | Required | Notes                                                                                  |
|--------------|----------|----------------------------------------------------------------------------------------|
| topic        | yes      | Free-form title                                                                        |
| type         | yes      | `Meeting`, `Correspondence`, `Workshop`, `Report`, `Log`, `Research`, `Recipe`         |
| threads      | yes      | List of wikilinks `[[Projects/X]]` / `[[Processes/Y]]` / `[[Topics/Z]]`; a note may belong to several |
| timestamp    | yes      | `YYYY-MM-DD-HH-MM-SS`, matches filename prefix                                         |
| aliases      | written  | `[<topic>]`, so Obsidian's file picker finds a timestamp-named note by its topic       |
| people       | optional | List of wikilinks `[[people/<name>]]` (or plain strings for untracked attendees)       |
| counterparty | optional | Meeting only                                                                           |
| location     | optional | Meeting only                                                                           |

### Body keywords

| Keyword     | Meaning                                                                  |
|-------------|--------------------------------------------------------------------------|
| `ACTION:`   | Action item — ingested by `tasks` and rewritten to a `TASK:` anchor    |
| `TASK:`     | Anchored open action (managed by `tasks`; don't write by hand)         |
| `DONE:`     | Anchored completed action (set by `tasks done`)                        |
| `AGREED:`   | Formal agreement — surfaced in `notes minutes`                         |
| `RESOLVED:` | Formal resolution — surfaced in `notes minutes`                        |
| `!:`        | Important callout — surfaced in `notes pdf` summary                    |

`ACTION:` lines may carry an optional assignee in parens: `ACTION: (Sam Rivera) Send the invite`. The assignee must match an existing `people/<name>.md` file or `tasks` will surface an error.

### Subcommands

A note is named by its stem — the filename without `.md`, e.g. `2026-09-10-14-30-00`. `notes list` shows the stems.

| Command | What it does |
|---|---|
| `notes new --type T --topic X --thread K/N [--thread ...] [--person N ...] [--counterparty C] [--location L]` | Create a note; print its path. `--person` is for Meeting and Correspondence, `--counterparty`/`--location` for Meeting |
| `notes list [filter] [--json]` | Stem, date, type, threads and topic of every note, oldest first |
| `notes cat <stem>` | Print a note |
| `notes last` | Print the path of the newest note |
| `notes copy <stem>` | Copy a note to a new timestamp; its topic gets ` COPY` |
| `notes delete <stem> -y` | Delete a note; refuses without `-y` |
| `notes pdf\|minutes\|agenda <stem> [--out DIR]` | Render to `<stem>.md` and `<stem>.md.pdf` (default `~/Downloads`); print both paths |

Every subcommand except `new` runs a task ingest first, to pick up pending `ACTION:` lines. If any line fails to ingest, a one-line warning goes to stderr when it is a terminal.

## threads

Skeleton management for thread files. Views over a thread's activity live in `search` (`overview`, `stream`, `activity`).

| Command                              | What it does                                                  |
|--------------------------------------|---------------------------------------------------------------|
| `threads new --name N --kind K --category C [--currency X --rate R]` | Create a thread file; name, kind and category required |
| `threads list [query] [--all] [--json]` | List open threads (kind, status, category, name); a query ranks by fuzzy match, `--all` adds paused and closed |
| `threads show <thread> [--json]`     | Print frontmatter + body (or JSON of frontmatter)             |

`<thread>` accepts a bare name (`Northwind`) or a path (`Processes/Northwind`). Bare names error if ambiguous across kinds.

There is no close or delete command. Closing a thread is setting `status: closed` and `ended:` in its frontmatter; removing one is deleting its file and folder by hand.

`threads new` also takes `--currency` and `--rate`, the billing defaults `hours` reads. Both are optional: most threads are never billed. `--rate` needs `--currency`. Without `--rate`, `hours` falls back to `.adulting/config.yaml` `hours.rate`, then 2500.

## people

Same skeleton shape, applied to people files.

| Command                              | What it does                                                  |
|--------------------------------------|---------------------------------------------------------------|
| `people new --name N --category C`   | Create a person file; both flags required                     |
| `people delete <name> -y`            | Delete a person; refuses without `-y`                         |
| `people list [query] [--all] [--json]` | List open people; a query ranks by fuzzy match, `--all` adds closed |
| `people show <name> [--json]`        | Print the file (or JSON of frontmatter)                       |

## tasks

Bridge from `ACTION:` lines in notes and logs into anchored `TASK:` lines, plus per-anchor mutations. Source notes are the entire store — there is no backend.

| Command                  | What it does                                                                                |
|--------------------------|---------------------------------------------------------------------------------------------|
| `tasks` / `tasks ingest` | Walk every thread's notes and logs, validate every `ACTION:` line, ingest valid ones (rewrite in place to `TASK:` anchors with a fresh uuid and `entry:<today>`) |
| `tasks --dry-run`        | Show what would be ingested without writing                                                 |
| `tasks --quiet`          | Suppress per-action output                                                                  |
| `tasks add <thread> <text>` | Buffer a structured `ACTION:` (same as `buffer add-action`); it becomes a task on `buffer flush` |
| `tasks <subcommand>`     | See `tasks --help` for `done`, `set-{description,assignee,due,scheduled,priority}`, `add-depends`, `rm-depends`, `list`, `next`, `show` |

Anchor shape on disk (validated by the `task_anchor` schema):
```
TASK: [#H] (Assignee) <body> <!--<uuid8> entry:YYYY-MM-DD [end:…] [due:…] [scheduled:…] [depends:<u8>,…]-->
```

Validation rules at ingest:
- Each thread the file names (a note's `threads:` list, a log's `thread:`) must resolve to an existing thread file.
- If the action has `(Assignee)`, that name must resolve to `people/<name>.md`.
- Description must be non-empty.
- Any inline attrs in the `ACTION:`'s trailing HTML comment (`due:`, `scheduled:`, `priority:`, `depends:`) are validated and carried onto the resulting `TASK:` anchor.

Failures are printed; the source line is left as `ACTION:` so you can fix and re-run.

## hours

Consulting time tracking. One file per thread at `~/vault/threads/<Kind>/<Thread>/hours.md`, holding a ` ```simple-time-tracker ` fenced JSON block in the format Obsidian's Super Simple Time Tracker plugin reads — so entries render natively and you can build your own views over the raw data.

| Command | What it does |
|---|---|
| `hours log <thread> <description...>` | Append an entry |
| `hours list [thread] [--since] [--until] [--json]` | List entries |
| `hours report [--thread] [--since] [--until] [--json]` | Totals by thread **and currency**; unbilled time totalled separately |
| `hours show <id> [--json]` | One entry |
| `hours edit <id> [-m/-r/-c/-d/-t/--description]` | Change one field |
| `hours rm <id> -y` | Delete an entry; refuses without `-y` |

`log` flags: `-m/--minutes` (default 60), `-r/--rate`, `-c/--currency`, `-d/--date`, `-t/--time`.

The thread must resolve to an existing thread file or the command fails — matching is case-sensitive, deliberately, so results don't differ between macOS and Linux.

Defaults resolve most-specific-first and are **stored literally on each entry at write time**, so changing a thread's defaults never re-prices work already logged:

| value | 1. flag | 2. thread frontmatter | 3. vault default |
|---|---|---|---|
| minutes | `--minutes` | — | 60 (`.adulting/config.yaml` → `hours.minutes`) |
| rate | `--rate` | `rate:` | 2500 (`.adulting/config.yaml` → `hours.rate`) |
| currency | `--currency` | `currency:` | none — the entry is unbilled |

Currency is never guessed: a wrong one silently corrupts totals. Where none is available the entry is simply **unbilled** — rate 0, no currency stored — because `hours` tracks time and money is an overlay on it. That is what makes it usable for personal threads (reading, exercise, admin) alongside client work. `hours report` totals unbilled duration in its own row, and `payments statement` ignores it. Asking for a `--rate` with no currency to express it in is the one refused combination.

`rate: 0` means unbillable. It is an ordinary value, not a sentinel — the hours still count, the money is just zero.

### On-disk shape

```markdown
---
thread: "[[Projects/Contoso Partners]]"
currency: ZAR
---

# Contoso Partners — hours

```simple-time-tracker
{
  "entries": [
    {
      "name": "Further decomposition; code review, with \"Tom\"",
      "startTime": "2026-08-01T06:30:00.000Z",
      "endTime": "2026-08-01T09:30:00.000Z",
      "id": "5048f86e",
      "rate": 2500,
      "currency": "ZAR"
    }
  ]
}
```
```

The frontmatter `currency` and the per-entry `currency` are both optional: a file holding only unbilled time omits them.

`name` holds the description, not a label — it is the only field the plugin renders, and these descriptions are invoice line items. `id`, `rate`, and `currency` are extra keys; the plugin round-trips unknown keys unharmed. Duration is derived from `endTime - startTime` (the plugin has no duration field), so a logged start plus a duration is written as an interval. JSON is pretty-printed rather than the plugin's single-line default, so appends produce readable git diffs.

## payments

Money received, per thread. One file per thread at `~/vault/threads/<Kind>/<Thread>/payments.md`, holding an ` ```adulting-payments ` fenced JSON block — same structure as `hours`, but its own fence since no external plugin is involved.

| Command | What it does |
|---|---|
| `payments log <thread> <amount>` | Record a receipt |
| `payments list [thread] [--since] [--until] [--json]` | List payments |
| `payments statement [--thread] [--since] [--until] [--as-of] [--json]` | Billed vs received vs outstanding, by thread **and currency** |
| `payments statement --thread T --pdf out.pdf [--as-of D]` | Render a statement of account as a PDF |
| `payments show <id> [--json]` | One payment |
| `payments edit <id> [--amount/-c/-d/-t/-a/-n]` | Change one field |
| `payments rm <id> -y` | Delete a payment; refuses without `-y` |

`log` flags: `-c/--currency`, `-d/--date`, `-t/--time`, `-a/--account`, `-n/--note`.

`statement` is the payoff: it reads each thread's `hours.md` for billed and `payments.md` for received, and reports the difference per thread and currency. It never sums across currencies.

Amounts accept `47300`, `47300.50`, or `47,300.50`, and must be positive — a refund is not a negative payment. All money arithmetic uses `decimal.Decimal`, so `hours report` and `payments statement` agree exactly rather than drifting by float error.

Payment ids share one namespace with `hours` entry ids; `lint` enforces uniqueness across both.

### Statement of account (PDF)

```
payments statement --thread "Contoso Partners" --as-of 2026-08-31 --pdf statement.pdf
```

Renders a one-client statement: parties, summary, a dated ledger of every charge and payment with a running balance, aging buckets (current / 30 / 60 / 90+), and banking details. Rendered with pandoc + xelatex — the same toolchain `notes pdf` uses, so it needs no Python packages beyond the standard library.

`--as-of` is the statement date and drives aging: work logged after it has not happened yet as far as the document is concerned, so `--as-of` never ages future charges into `current`. It applies to the text view too, so the two always agree.

A statement is per client, so `--pdf` requires `--thread`. Charges round to whole cents at each line, so the printed lines always sum to the printed total, and the aging buckets always sum to the balance — both are asserted before anything is written.

Party details come from two places:

| what | where |
|---|---|
| Supplier (you) and banking | `.adulting/config.yaml`, under `billing:` |
| Client name, address, VAT | the thread's frontmatter (`client_name`, `client_address`, `client_vat`, `client_email`) |

```yaml
# .adulting/config.yaml
billing:
  supplier_name: <your name>
  supplier_address: <line 1>|<line 2>|<city>
  supplier_phone: <phone>
  bank_account_name: ...
  bank_name: ...
  bank_account_number: ...
  bank_branch_code: ...
  bank_account_type: ...
```

Addresses are pipe-separated because the frontmatter and config readers are single-line only.

The payment reference printed on the statement is the thread name without its `Kind/` prefix — `Contoso Partners`, not `Projects/Contoso Partners`. It is derived rather than configured, so it can never drift from the thread or carry another client's code.

`supplier_name` falls back to the top-level `owner` key.

**Banking details are required for a usable statement.** While any bank field is missing or still says `TODO`, the PDF prints "Banking details not yet supplied" instead of a payment table and the command warns on stderr — a document that asks for money must say where to send it.

## stats

Numbers tracked over time, against stats declared on threads. One command for every measure, rather than a command per measure.

| Command | What it does |
|---|---|
| `stats new <name> --thread T --type int\|decimal --agg sum\|last\|max` | Declare a stat in the thread file's `stats:` frontmatter |
| `stats list [--json]` | List declared stats |
| `stats log <name> <value> [-d] [-t]` | Buffer a value; `buffer flush` files it as a `STAT:` line in the thread's log |
| `stats series <name> [--by day\|week\|month] [--since] [--until] [--json]` | The value per period, from the logs and the unflushed buffer |

- **Names are unique across the vault**, so `stats log pushups 25` needs no thread. Names are lowercase letters, digits and `-`. There is no unit field: put the unit in the name when it is unclear (`run-km`, `spend-zar`).
- **`agg` says how a period's values combine:** `sum` for sets of push-ups, `last` for a running total such as steps, `max` for a personal best.
- **A period with nothing logged is `-`** (`null` in JSON), not `0`: not having logged is not the same as zero.
- **Events are counts.** To record that something happened, declare an `int` stat with `--agg sum` and log `1` each time.
- There is no rename or delete. Edit the thread's frontmatter; values already logged are not rewritten.

A `STAT:` line is the only log line that keeps its timestamp: `STAT: pushups 25 <!--2026-10-07T07:30:00-->`.

## buffer

The staging queue between a capture and a thread's log. `~/vault/buffer.md` holds one line per pending entry; `buffer flush` turns them into per-thread, per-day log files.

| Command | What it does |
|---|---|
| `buffer add <text>` | A raw `UNKNOWN` capture with no thread, to be sorted later |
| `buffer add-text <thread> <text>` | A `TEXT:` observation |
| `buffer add-ref <thread> <target> <text>` | A `REF:` pointer to another vault file |
| `buffer add-action <thread> <text> [--due] [--scheduled] [--priority] [--depends]` | An `ACTION:`, same as `tasks add` |
| `buffer list [filter] [--json]` | The buffer with line numbers |
| `buffer rm <n>` | Remove one line by number |
| `buffer tend` | Regroup by thread and date, then validate. Safe to repeat. |
| `buffer flush` | Tend, write each thread's logs, clear the buffer, and ingest the flushed ACTIONs as tasks |

Every `add*` takes `--date` to file the entry under the day it happened rather than today.

- **`UNKNOWN` lines block a flush.** A raw capture has to be given a thread before it can be filed: `buffer rm` it, then add it again with the right `add-*`.
- **Flush is idempotent for tasks.** An ACTION identical to an open task is dropped with `already a task: <uuid>`, and repeats within one flush collapse with `already buffered`. Whoever adds a task does not have to read the vault first.
- **Don't edit `buffer.md` by hand.** The commands keep it in the shape `tend` and `flush` expect.

A `REF:` target is a thread (`<Kind>/<Name>`), its `hours` or `payments` file (`<Kind>/<Name>/hours`), a daily log (`<Kind>/<Name>/logs/<date>`), a note stem, or a person (`people/<Name>`).

## lint

Validates everything in `~/vault/` against schemas in `src/adulting/schemas/`. Reports `path:line: message` for each violation. Exit 0 clean, 1 if any.

| Command          | What it does                                              |
|------------------|-----------------------------------------------------------|
| `lint`           | Walk the vault, validate every file, report violations    |
| `lint <path> ...`| Validate only these files (good for pre-save hooks)       |
| `lint --quiet`   | Suppress per-violation output, exit-code only             |
| `lint --schemas <dir>` | Validate against a different schemas directory      |

Exit 2 means no schemas were loaded.

Beyond each file's own schema, `lint` checks the vault as a whole: a file filed under a thread that is not its folder's, a note stem or record id used twice, a task dependency cycle, a stat declared on two threads, and anything left in the pre-2026-10 root folders (`notes/`, `logs/`, `hours/`, `payments/`).

Schemas live in `src/adulting/schemas/` as markdown files with YAML frontmatter and a `## Fields` table. See `src/adulting/schemas/note_meeting.md` for the canonical shape.

## search

Read-only views over notes and logs: finding records, and summarising what happened on a thread.

| Command | What it does |
|---|---|
| `search notes` | Notes by `--thread`, `--type`, `--since`/`--until` or `--text` |
| `search logs` | Daily logs by thread, date or text |
| `search activity` | Threads ranked by what happened in a period — notes, logs and hours together |
| `search overview <thread>` | The whole picture of one thread |
| `search stream` | Every dated record merged into one chronology, the unflushed buffer included |

Results are absolute paths plus metadata, never file bodies. Dates are event dates — a note's frontmatter `timestamp`, not its filename. Hours descriptions are not searched (see [Notes, logs and hours](#notes-logs-and-hours)).

## commit

The vault's only sync mechanism: git, behind two subcommands an agent can be trusted with.

| Command | What it does |
|---|---|
| `commit review [--max-file-lines N] [--max-lines N]` | Everything changed since the last commit. Read-only. |
| `commit save --message <subject> [--body <text>] [--dry-run]` | Stage every change in the vault and commit it |

`save` only ever adds a commit: it never amends, rebases, resets, checks out or pushes. `$ADULTING_HOME` must be the root of its git repository.

# Data store

```
~/vault/                    # ADULTING_HOME (override via env var)
├── .obsidian/                  # Obsidian vault config
├── .adulting/                  # operational state (hidden, like .git or .obsidian)
│   └── config.yaml             # vault-wide config (owner, hours defaults, billing)
├── threads/
│   ├── Projects/               # bounded efforts
│   │   ├── Northwind.md              # the thread file
│   │   └── Northwind/                # everything that belongs to the thread
│   │       ├── notes/          # its notes, <timestamp>.md
│   │       ├── logs/           # its daily logs, <YYYY-MM-DD>.md
│   │       ├── hours.md        # its billable time
│   │       └── payments.md     # money received against it
│   ├── Processes/              # ongoing operations (same shape)
│   └── Topics/                 # interest areas / catchalls (same shape)
├── people/                     # people files (relationship link targets)
├── assets/                     # images and attachments, linked by name
└── buffer.md                   # staging queue for quick captures, emptied by `buffer flush`
```

The visible top level (what Obsidian shows in its sidebar) is only user content: threads, people, assets and the buffer. Everything about one thread is in one place: the thread file and the folder beside it. A note in several threads is filed under the first it names; its `threads:` frontmatter says which threads it belongs to. People stay global, because the people who matter most span threads. Tooling state lives in the hidden `.adulting/` subdir, the same pattern `.git/` and `.obsidian/` use in the same directory.

# Schemas

| File                          | Validates                                                       |
|-------------------------------|-----------------------------------------------------------------|
| `note_meeting.md`             | Meeting notes                                                   |
| `note_correspondence.md`      | Correspondence notes                                            |
| `note_simple.md`              | Workshop / Report / Log / Research / Recipe notes                |
| `log.md`                      | Per-day log files in a thread's `logs/`                         |
| `thread.md`                   | Thread files, `threads/<Kind>/<Name>.md`                        |
| `person.md`                   | Person files in `people/`                                       |
| `thread_entry.md`             | Bullet entries within thread bodies (legacy; rare today)        |
| `task_anchor.md`              | `TASK:`/`DONE:` lines in notes and logs (uuid, attrs, depends)  |
| `stat_line.md`                | `STAT:` lines in a thread's logs (declared name, typed value, timestamp on the log's date) |
| `hours_file.md`               | A thread's `hours.md` (tracker block, entry objects)            |
| `payments_file.md`            | A thread's `payments.md` (payments block, payment objects)      |

Each schema is a markdown file with YAML frontmatter (`schema`, `scope`, `path` — where its files live, one of the patterns in `vault.LAYOUT` — optionally `applies_when`) and a `## Fields` table describing required fields, types, and constraints. Pipes inside cells (e.g. inside a regex) must be escaped as `\|`.

Constraint cell DSL (single cell, semicolon-separated):
- `regex=<pattern>` — value must match
- `min=<N>` — string length ≥ N
- `must_contain_digit` — flag
- bare values (comma-separated) — enum

# Output conventions

These hold for every command.

- **Every path a command prints is absolute.** A path in output is there to be
  opened, and a reader resolves a relative path against its own working
  directory, which is not the vault — in a container the vault is often mounted
  somewhere else entirely. Vault-relative strings do appear, but as identifiers
  rather than paths: a thread ref (`Projects/Northwind`), a wikilink target
  (`people/Sam Rivera`).
- **A file that cannot be read as UTF-8 is skipped, not fatal.** A vault
  collects files nobody here wrote: a stray binary, a sync-conflict copy,
  something saved in another encoding. A command that walks the vault skips
  such a file and carries on, so one bad file cannot cost you a listing.
  `lint` is where it is reported, as `<path>:0: file is not valid UTF-8`. A
  command asked for one file by name stops instead, with `<path> is not valid
  UTF-8`, because skipping would answer a question about that file by
  pretending it is not there.
- **A skipped file is named only when stderr is a terminal.** Piped output is
  the answer to a question, and an agent harness discards stdout whenever
  stderr is non-empty, so a warning there would cost the caller the answer.
- **Every command and subcommand answers `--help-json`**, printing its own
  arguments as JSON and exiting 0. `tasks --help-json` describes the whole
  command and its subcommands; `tasks list --help-json` describes `list`.

# Vault hygiene

- `notes pdf` / `minutes` / `agenda` run pandoc inside a temporary directory — no scratch files leak into your CWD

# Obsidian

- All notes use YAML frontmatter; thread / people / counterparty / location all populate Obsidian's Properties panel.
- Threads and people render as Obsidian files with `[[wikilinks]]` between them — graph view, backlinks, Bases all work natively.
- `notes new` writes `aliases: [<topic>]`, so Cmd-O finds a timestamp-named note by its topic.
- `hours.md` renders natively in the Super Simple Time Tracker plugin.

Setup is in [INTEGRATIONS.md](INTEGRATIONS.md).

# Running under the agent

`Dockerfile` builds an image that layers these commands under the agent from `ghcr.io/riazarbi/agent`, with the vault mounted at `/vault`. The image carries the agent's tool definitions (`dev/tools/*.json`) and skills (`agent/skills/`) beside the commands they describe, and `container/entrypoint.sh` installs both into the agent's state directory on every start, so they cannot drift from the installed CLI. The system prompt is deliberately not shipped. The image leaves out pandoc and LaTeX, so `notes pdf|minutes|agenda` and `payments statement --pdf` do not render inside it.

# Development

```zsh
uv venv .venv && uv pip install --python .venv/bin/python -e '.[dev]'
dev/ci              # the gate: lint (syntax, ruff, contracts, manual, skills, tools) + tests with coverage
dev/ci test         # tests only
dev/ci generate     # regenerate MANUAL.md and dev/tools/ from the CLI (needs `claude`)
```

- Tests live in `tests/unit/` and `tests/cli/`; the CLI tests run the installed console scripts against a throwaway vault.
- `MANUAL.md` and `dev/tools/*.json` are generated from the commands' `--help-json`, docstrings, the schemas and the README sections listed in `dev/manual-harvest`. Don't edit them by hand: change the source and regenerate. `dev/ci` fails when either has drifted from the CLI, and `dev/agent-check` does the same for `agent/skills/`.
- A new command goes in `pyproject.toml`'s `[project.scripts]` and in `dev/commands.py`.
- Changes are recorded in `CHANGELOG.md`, newest first; user stories live in `stories/`.

# Design goals

- Run on macOS or Linux.
- One module per command in the `adulting` package, sharing one vault module.
- Require no third-party Python libraries at runtime; `pytest`, `coverage` and `ruff` for development only.
- Be non-interactive: every command runs from its arguments, so a person and an agent drive it the same way.
- Be operated from the command line.
- Maintain state in simple text-based file formats.
- Maintain all state under a single vault directory (default `~/vault/`, override with `ADULTING_HOME`).
