# adulting

Scripts to help me organise my day-to-day life. Everything stores plain-text state under `~/.adulting/` so the data outlives any one tool — you can grep it, back it up, sync it, or browse the whole directory as an Obsidian vault.

## Conceptual model

- **Note** — a persisted piece of information. The workhorse object: meeting records, correspondence, reports, ad-hoc logs, research. Notes live in `~/.adulting/notes/` and have YAML frontmatter (topic, type, thread, timestamp, etc.) plus a free-form body.
- **Thread** — an organising lens for notes. Three kinds: `project` (bounded), `process` (ongoing), `topic` (interest area / catchall). Threads live in `~/.adulting/threads/{Projects,Processes,Topics}/`.
- **Person** — a contact you track. People live in `~/.adulting/people/` and are link targets — never threads themselves.
- **Action** — a task. Notes contain `ACTION:` lines that get ingested into [taskwarrior](https://taskwarrior.org) by the `tasks` bridge, then rewritten in place to `TASK:`.

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
- [`task`](https://taskwarrior.org) (taskwarrior) — required by the `tasks` bridge. Install via `brew install task` on macOS.
- macOS `open` (or Linux `xdg-open`) — used to launch Obsidian for note editing

# Scripts

## notes

Markdown note taker. Notes live in `~/.adulting/notes/` as `<timestamp>.md` files with YAML frontmatter and a free-form body.

### Frontmatter

| Field        | Required | Notes                                                                                  |
|--------------|----------|----------------------------------------------------------------------------------------|
| topic        | yes      | Free-form title                                                                        |
| type         | yes      | `Meeting`, `Correspondence`, `Workshop`, `Report`, `Log`, `Research`                   |
| thread       | yes      | Single wikilink `[[Projects/X]]` / `[[Processes/Y]]` / `[[Topics/Z]]`                  |
| timestamp    | yes      | `YYYY-MM-DD-HH-MM-SS`, matches filename prefix                                         |
| people       | optional | List of wikilinks `[[people/<name>]]` (or plain strings for untracked attendees)       |
| counterparty | optional | Meeting only                                                                           |
| location     | yes      | Meeting only                                                                           |

### Body keywords

| Keyword     | Meaning                                                                  |
|-------------|--------------------------------------------------------------------------|
| `ACTION:`   | Action item — ingested by `tasks` into taskwarrior, then rewritten to `TASK:` |
| `TASK:`     | Already-ingested action (set by `tasks`; don't write by hand)            |
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
| `threads new`                        | Interactive: pick kind, category, name; creates the file      |
| `threads delete <thread> [-y]`       | Delete a thread (with confirm)                                |
| `threads list [--json]`              | List all threads (kind, status, category, name)               |
| `threads show <thread> [--json]`     | Print frontmatter + body (or JSON of frontmatter)             |

`<thread>` accepts a bare name (`SGB`) or a path (`Processes/SGB`). Bare names error if ambiguous across kinds.

## people

Same skeleton shape, applied to people files.

| Command                              | What it does                                                  |
|--------------------------------------|---------------------------------------------------------------|
| `people new`                         | Interactive: pick category, name; creates the file            |
| `people delete <name> [-y]`          | Delete a person (with confirm)                                |
| `people list [--json]`               | List all people                                               |
| `people show <name> [--json]`        | Print the file (or JSON of frontmatter)                       |

## tasks

Bridge from `ACTION:` lines in notes into taskwarrior.

| Command                  | What it does                                                                                |
|--------------------------|---------------------------------------------------------------------------------------------|
| `tasks`                  | Walk notes, validate every `ACTION:` line, ingest valid ones via `task add`, rewrite to `TASK:` |
| `tasks --dry-run`        | Show what would be ingested without calling `task` or modifying files                       |
| `tasks --quiet`          | Suppress per-action output                                                                  |

Validation rules:
- Each entry in the note's `threads:` list must resolve to an existing thread file.
- If the action has `(Assignee)`, that name must resolve to `people/<name>.md`.
- Description must be non-empty.
- Any inline attrs (in the trailing HTML comment, e.g. `due:2026-05-08 priority:H`) are validated and applied to the new taskwarrior task at create time.

Failures are printed; the source line is left as `ACTION:` so you can fix it and re-run. `task` (taskwarrior) is checked lazily — only errors when there's something to ingest.

## lint

Validates everything in `~/.adulting/` against schemas in `schemas/`. Reports `path:line: message` for each violation. Exit 0 clean, 1 if any.

| Command          | What it does                                              |
|------------------|-----------------------------------------------------------|
| `lint`           | Walk the vault, validate every file, report violations    |
| `lint <path>`    | Validate one file (good for pre-save hooks)               |
| `lint --quiet`   | Suppress per-violation output, exit-code only             |

Schemas live in `schemas/` as markdown files with YAML frontmatter and a `## Fields` table. See `schemas/note_meeting.md` for the canonical shape.

# Data store

```
~/.adulting/
├── .obsidian/                  # Obsidian vault config
├── notes/                      # markdown notes (one file per note)
├── threads/
│   ├── Projects/               # bounded efforts
│   ├── Processes/              # ongoing operations
│   └── Topics/                 # interest areas / catchalls
├── people/                     # people files (relationship link targets)
├── buffer.md                   # quick-capture inbox (processed by an agent ritual; not yet automated)
└── actions_log.json            # legacy, no longer maintained — delete when you're done with cross-checks
```

# Schemas

| File                          | Validates                                                       |
|-------------------------------|-----------------------------------------------------------------|
| `note_meeting.md`             | Meeting notes                                                   |
| `note_correspondence.md`      | Correspondence notes                                            |
| `note_simple.md`              | Workshop / Report / Log / Research notes                        |
| `thread.md`                   | Thread files in `threads/{Projects,Processes,Topics}/`          |
| `person.md`                   | Person files in `people/`                                       |
| `thread_entry.md`             | Bullet entries within thread bodies (legacy; rare today)        |

Each schema is a markdown file with YAML frontmatter (`schema`, `scope`, `directory`, `filename`, optionally `applies_when`) and a `## Fields` table describing required fields, types, and constraints. Pipes inside cells (e.g. inside a regex) must be escaped as `\|`.

Constraint cell DSL (single cell, semicolon-separated):
- `regex=<pattern>` — value must match
- `min=<N>` — string length ≥ N
- `must_contain_digit` — flag
- bare values (comma-separated) — enum

# Buffer / agent ritual (deferred)

`~/.adulting/buffer.md` is an append-only inbox for quick-capture entries. Routing those entries to notes (resolving threads, fixing references, applying schemas) is intended as a periodic ritual run by an AI agent against a tool-call API; the routing logic is not yet automated.

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
- Maintain all state under the `~/.adulting/` hidden directory.
