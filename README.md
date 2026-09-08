# adulting

Scripts to help me organise my day-to-day life. Everything stores plain-text state under `~/vault/` so the data outlives any one tool — you can grep it, back it up, sync it, or browse the whole directory as an Obsidian vault.

## Conceptual model

- **Note** — a persisted piece of information. The workhorse object: meeting records, correspondence, reports, ad-hoc logs, research. Notes live in `~/vault/notes/` and have YAML frontmatter (topic, type, thread, timestamp, etc.) plus a free-form body.
- **Thread** — an organising lens for notes. Three kinds: `project` (bounded), `process` (ongoing), `topic` (interest area / catchall). Threads live in `~/vault/threads/{Projects,Processes,Topics}/`.
- **Person** — a contact you track. People live in `~/vault/people/` and are link targets — never threads themselves.
- **Time entry** — a billable (or unbillable) session of work on a thread. Entries live in `~/vault/hours/` as JSON inside a ```simple-time-tracker fence, so Obsidian's Super Simple Time Tracker format renders them natively.
- **Payment** — money received against a thread. Records live in `~/vault/payments/`, same shape as hours.
- **Action** — a task. Notes contain `ACTION:` lines that the `tasks` bridge ingests by rewriting them in place to `TASK:` anchors with an 8-char uuid and inline attrs (`entry`, `due`, `scheduled`, `priority`, `depends`). Source notes are the only store — there is no backend.

# Installation

Drop the repo onto your `PATH`. I keep a `bin` directory in my home folder and clone into it:

```zsh
cd ~
mkdir -p bin
cd bin
git clone git@github.com:riazarbi/adulting.git
```

Then add this to the bottom of `.zshrc` or `.bashrc`:

```zsh
export PATH=/Users/riaz/bin/adulting:$PATH
```

## Dependencies

- `bash`, `python3`, `awk`, `sed`, `grep` — required by everything
- `pandoc` and a LaTeX engine (`xelatex` via e.g. MacTeX or TeX Live) — required by `notes pdf`, `notes minutes`, `notes agenda`
- macOS `open` (or Linux `xdg-open`) — used to launch Obsidian for note editing

## One-time setup

Nothing to install — task state lives in source notes themselves. The vault location follows `ADULTING_HOME` if set (default `~/vault`).

# Scripts

## notes

Markdown note taker. Notes live in `~/vault/notes/` as `<timestamp>.md` files with YAML frontmatter and a free-form body.

### Frontmatter

| Field        | Required | Notes                                                                                  |
|--------------|----------|----------------------------------------------------------------------------------------|
| topic        | yes      | Free-form title                                                                        |
| type         | yes      | `Meeting`, `Correspondence`, `Workshop`, `Report`, `Log`, `Research`, `Recipe`         |
| threads      | yes      | List of wikilinks `[[Projects/X]]` / `[[Processes/Y]]` / `[[Topics/Z]]`; a note may belong to several |
| timestamp    | yes      | `YYYY-MM-DD-HH-MM-SS`, matches filename prefix                                         |
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

`ACTION:` lines may carry an optional assignee in parens: `ACTION: (Riaz Arbi) Send the invite`. The assignee must match an existing `people/<name>.md` file or `tasks` will surface an error.

### Subcommands

| Command              | What it does                                                    |
|----------------------|-----------------------------------------------------------------|
| `notes` / `--new`    | Create a new note (interactive: type → thread → topic → people → meeting extras → opens editor) |
| `--edit` / `--nano`  | Pick a note, edit in default editor / nano                      |
| `--last`             | Open most recent note                                           |
| `--copy` / `--strip` / `--delete` / `--cat` | Pick a note, do the thing                |
| `--pdf` / `--minutes` / `--agenda` | Pick a note, render PDF                           |
| `--help`             | Full help                                                       |

Every non-`--new` invocation runs `tasks` first to ingest any pending `ACTION:` lines.

The files `notes_new`, `notes_pdf`, `notes_minutes`, `notes_agenda`, `notes_strip` are helpers invoked by `notes`. They fail loudly if called directly (env-var guards).

## threads

Skeleton management for thread files. Daily-review / tail / overdue tooling will be rebuilt later from notes data.

| Command                              | What it does                                                  |
|--------------------------------------|---------------------------------------------------------------|
| `threads new`                        | Interactive: pick kind, category, name, optional currency/rate; creates the file |
| `threads delete <thread> [-y]`       | Delete a thread (with confirm)                                |
| `threads list [--json]`              | List all threads (kind, status, category, name)               |
| `threads show <thread> [--json]`     | Print frontmatter + body (or JSON of frontmatter)             |

`<thread>` accepts a bare name (`SGB`) or a path (`Processes/SGB`). Bare names error if ambiguous across kinds.

`threads new` also asks for a `currency` (blank to skip) and, if you give one, a `rate` — the billing defaults `hours` reads. Both are optional: most threads are never billed. Flags `--currency` / `--rate` skip the prompts, and passing `--kind --category --name` together suppresses all prompting for scripted use.

## people

Same skeleton shape, applied to people files.

| Command                              | What it does                                                  |
|--------------------------------------|---------------------------------------------------------------|
| `people new`                         | Interactive: pick category, name; creates the file            |
| `people delete <name> [-y]`          | Delete a person (with confirm)                                |
| `people list [--json]`               | List all people                                               |
| `people show <name> [--json]`        | Print the file (or JSON of frontmatter)                       |

## tasks

Bridge from `ACTION:` lines in notes/logs into anchored `TASK:` lines, plus per-anchor mutations. Source notes are the entire store — there is no backend.

| Command                  | What it does                                                                                |
|--------------------------|---------------------------------------------------------------------------------------------|
| `tasks`                  | Walk notes/logs, validate every `ACTION:` line, ingest valid ones (rewrite in place to `TASK:` anchors with a fresh uuid and `entry:<today>`) |
| `tasks --dry-run`        | Show what would be ingested without writing                                                 |
| `tasks --quiet`          | Suppress per-action output                                                                  |
| `tasks <subcommand>`     | See `tasks --help` for `done`, `set-{description,assignee,due,scheduled,priority}`, `add-depends`, `rm-depends`, `list`, `next`, `show` |

Anchor shape on disk (validated by the `task_anchor` schema):
```
TASK: [#H] (Assignee) <body> <!--<uuid8> entry:YYYY-MM-DD [end:…] [due:…] [scheduled:…] [depends:<u8>,…]-->
```

Validation rules at ingest:
- Each entry in the note's `threads:` list must resolve to an existing thread file.
- If the action has `(Assignee)`, that name must resolve to `people/<name>.md`.
- Description must be non-empty.
- Any inline attrs in the `ACTION:`'s trailing HTML comment (`due:`, `scheduled:`, `priority:`, `depends:`) are validated and carried onto the resulting `TASK:` anchor.

Failures are printed; the source line is left as `ACTION:` so you can fix and re-run.

## hours

Consulting time tracking. One file per thread at `~/vault/hours/<Kind>/<Thread>.md`, holding a ` ```simple-time-tracker ` fenced JSON block in the format Obsidian's Super Simple Time Tracker plugin reads — so entries render natively and you can build your own views over the raw data.

| Command | What it does |
|---|---|
| `hours log <thread> <description...>` | Append an entry |
| `hours log` | Interactive: pick thread → description → minutes → rate |
| `hours list [thread] [--since] [--until] [--json]` | List entries |
| `hours report [--thread] [--since] [--until] [--json]` | Totals by thread **and currency** |
| `hours show <id> [--json]` | One entry |
| `hours edit <id> [-m/-r/-c/-d/-t/--description]` | Change one field |
| `hours rm <id> [-y]` | Delete an entry |

`log` flags: `-m/--minutes` (default 60), `-r/--rate`, `-c/--currency`, `-d/--date`, `-t/--time`.

The thread must resolve to an existing thread file or the command fails — matching is case-sensitive, deliberately, so results don't differ between macOS and Linux.

Defaults resolve most-specific-first and are **stored literally on each entry at write time**, so changing a thread's defaults never re-prices work already logged:

| value | 1. flag | 2. thread frontmatter | 3. vault default |
|---|---|---|---|
| minutes | `--minutes` | — | 60 |
| rate | `--rate` | `rate:` | 2500 (`.adulting/config.yaml` → `hours.rate`) |
| currency | `--currency` | `currency:` | none — hard error |

Currency is never guessed: a wrong one silently corrupts totals. Set `currency: ZAR` on the thread, or pass `--currency`.

`rate: 0` means unbillable. It is an ordinary value, not a sentinel — the hours still count, the money is just zero.

### On-disk shape

```markdown
---
thread: "[[Projects/SANA Partners]]"
currency: ZAR
---

# SANA Partners — hours

```simple-time-tracker
{
  "entries": [
    {
      "name": "Further decomposition; code review, with \"Nick\"",
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

`name` holds the description, not a label — it is the only field the plugin renders, and these descriptions are invoice line items. `id`, `rate`, and `currency` are extra keys; the plugin round-trips unknown keys unharmed. Duration is derived from `endTime - startTime` (the plugin has no duration field), so a logged start plus a duration is written as an interval. JSON is pretty-printed rather than the plugin's single-line default, so appends produce readable git diffs.

## payments

Money received, per thread. One file per thread at `~/vault/payments/<Kind>/<Thread>.md`, holding an ` ```adulting-payments ` fenced JSON block — same structure as `hours`, but its own fence since no external plugin is involved.

| Command | What it does |
|---|---|
| `payments log <thread> <amount>` | Record a receipt |
| `payments log` | Interactive: pick thread → amount → date → account → note |
| `payments list [thread] [--since] [--until] [--json]` | List payments |
| `payments statement [--thread] [--since] [--until] [--as-of] [--json]` | Billed vs received vs outstanding, by thread **and currency** |
| `payments statement --thread T --pdf out.pdf [--as-of D]` | Render a statement of account as a PDF |
| `payments show <id> [--json]` | One payment |
| `payments edit <id> [--amount/-c/-d/-t/-a/-n]` | Change one field |
| `payments rm <id> [-y]` | Delete a payment |

`log` flags: `-c/--currency`, `-d/--date`, `-t/--time`, `-a/--account`, `-n/--note`.

`statement` is the payoff: it reads the `hours/` side for billed and the `payments/` side for received, and reports the difference per thread and currency. It never sums across currencies.

Amounts accept `47300`, `47300.50`, or `47,300.50`, and must be positive — a refund is not a negative payment. All money arithmetic uses `decimal.Decimal`, so `hours report` and `payments statement` agree exactly rather than drifting by float error.

Payment ids share one namespace with `hours` entry ids; `lint` enforces uniqueness across both.

### Statement of account (PDF)

```
payments statement --thread "SANA Partners" --as-of 2026-08-31 --pdf statement.pdf
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
  supplier_name: Riaz Arbi
  supplier_address: 14 Kinnoull Road|Camps Bay|Cape Town
  supplier_phone: +27 72 605 1357
  bank_account_name: ...
  bank_name: ...
  bank_account_number: ...
  bank_branch_code: ...
  bank_account_type: ...
```

Addresses are pipe-separated because the frontmatter and config readers are single-line only.

The payment reference printed on the statement is the thread name without its `Kind/` prefix — `SANA Partners`, not `Projects/SANA Partners`. It is derived rather than configured, so it can never drift from the thread or carry another client's code.

**Banking details are required for a usable statement.** While any bank field is missing or still says `TODO`, the PDF prints "Banking details not yet supplied" instead of a payment table and the command warns on stderr — a document that asks for money must say where to send it.

## lint

Validates everything in `~/vault/` against schemas in `schemas/`. Reports `path:line: message` for each violation. Exit 0 clean, 1 if any.

| Command          | What it does                                              |
|------------------|-----------------------------------------------------------|
| `lint`           | Walk the vault, validate every file, report violations    |
| `lint <path>`    | Validate one file (good for pre-save hooks)               |
| `lint --quiet`   | Suppress per-violation output, exit-code only             |

Schemas live in `schemas/` as markdown files with YAML frontmatter and a `## Fields` table. See `schemas/note_meeting.md` for the canonical shape.

# Data store

```
~/vault/                    # ADULTING_HOME (override via env var)
├── .obsidian/                  # Obsidian vault config
├── .adulting/                  # operational state (hidden, like .git or .obsidian)
│   └── config.yaml             # vault-wide config (owner, etc.)
├── notes/                      # markdown notes (one file per note)
├── threads/
│   ├── Projects/               # bounded efforts
│   ├── Processes/              # ongoing operations
│   └── Topics/                 # interest areas / catchalls
├── people/                     # people files (relationship link targets)
├── hours/                      # billable time, one file per thread
│   ├── Projects/
│   ├── Processes/
│   └── Topics/
├── payments/                   # money received, one file per thread
│   ├── Projects/
│   ├── Processes/
│   └── Topics/
└── buffer.md                   # quick-capture inbox (processed by an agent ritual; not yet automated)
```

The visible top level (what Obsidian shows in its sidebar) is only user content: notes, threads, people, logs, and the buffer. Tooling state lives in the hidden `.adulting/` subdir, the same pattern `.git/` and `.obsidian/` use in the same directory.

# Schemas

| File                          | Validates                                                       |
|-------------------------------|-----------------------------------------------------------------|
| `note_meeting.md`             | Meeting notes                                                   |
| `note_correspondence.md`      | Correspondence notes                                            |
| `note_simple.md`              | Workshop / Report / Log / Research / Recipe notes                |
| `log.md`                      | Per-thread per-day log files in `logs/`                         |
| `thread.md`                   | Thread files in `threads/{Projects,Processes,Topics}/`          |
| `person.md`                   | Person files in `people/`                                       |
| `thread_entry.md`             | Bullet entries within thread bodies (legacy; rare today)        |
| `task_anchor.md`              | `TASK:`/`DONE:` lines in notes/logs (uuid, attrs, depends)      |
| `hours_file.md`                | Time files in `hours/` (tracker block, entry objects)            |
| `payments_file.md`            | Payments files in `payments/` (payments block, payment objects) |

Each schema is a markdown file with YAML frontmatter (`schema`, `scope`, `directory`, `filename`, optionally `applies_when`) and a `## Fields` table describing required fields, types, and constraints. Pipes inside cells (e.g. inside a regex) must be escaped as `\|`.

Constraint cell DSL (single cell, semicolon-separated):
- `regex=<pattern>` — value must match
- `min=<N>` — string length ≥ N
- `must_contain_digit` — flag
- bare values (comma-separated) — enum

# Buffer / agent ritual (deferred)

`~/vault/buffer.md` is an append-only inbox for quick-capture entries. Routing those entries to notes (resolving threads, fixing references, applying schemas) is intended as a periodic ritual run by an AI agent against a tool-call API; the routing logic is not yet automated.

# Vault hygiene

- All `notes_*` helpers fail loudly if invoked outside `notes` (env-var guards)
- `notes pdf` / `--minutes` / `--agenda` run inside a `mktemp -d` workdir — no scratch files leak into your CWD

# Obsidian roadmap

What's done:
- All notes use YAML frontmatter; thread / people / counterparty / location all populate Obsidian's Properties panel
- Threads and people render as Obsidian files with `[[wikilinks]]` between them — graph view, backlinks, Bases all work natively

What remains:
- **Topic-discoverable filenames.** Notes are timestamp-named (`2024-04-29-09-03-15.md`); the file picker is opaque without an `aliases:` field. Adding `aliases: [<topic>]` in frontmatter makes Cmd-O find notes by topic without renaming files. Unimplemented.
- **Compiled views.** A future `threads tail` / `report` / `overdue` should query notes data, not thread bodies. Skeleton today is just `new` / `delete` / `list` / `show`.

# Known issues

- `nano_note` Linux branch calls `nano -"$@" note` (literal "note" filename, almost certainly a bug). Never noticed because it isn't run on Linux.

# Design goals

- Run on macOS or Linux.
- One self-contained file per utility (with thin `notes_*` helpers).
- Require no Python libraries beyond the standard library; no pip installs.
- Be operated from the command line.
- Maintain state in simple text-based file formats.
- Maintain all state under a single vault directory (default `~/vault/`, override with `ADULTING_HOME`).
