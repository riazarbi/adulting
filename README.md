# adulting

Scripts to help me organise my day to day life. Everything stores plain-text state under `~/.adulting/` so the data outlives any one tool — you can grep it, back it up, sync it, or browse the whole directory as an Obsidian vault (see [Obsidian compatibility](#obsidian-compatibility)).

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

The scripts lean on base system tools wherever possible. A few features need extras:

- `bash`, `python3`, `awk`, `sed`, `grep` — required by everything
- `nano` — used by `actions` and `notes --nano`
- `pandoc` and a LaTeX engine (`xelatex` via e.g. MacTeX or TeX Live) — required by `notes --pdf`, `notes --minutes`, `notes --agenda`
- `open` (macOS) — used by `notes` to launch the system default markdown editor (Linux users will need to swap it for `xdg-open`)

# Scripts

## summary

Prints a one-screen dashboard of the latest log line on each open thread. Add `summary` to the bottom of `.zshrc`/`.bashrc` to see it on every new shell.

## notes

Markdown note taker. Notes are stored in `~/.adulting/notes/` as `<timestamp>.md` files. Each note carries a metadata header (Topic, Type, Thread, Timestamp — plus Counterparty/Location/Attendees for meetings, or Participants for correspondence) followed by free-form content.

The body recognises a handful of keywords that downstream tools look for:

| Keyword     | Meaning                                                      |
|-------------|--------------------------------------------------------------|
| `- [ ]`     | Open action item — tracked across all notes by `actions`     |
| `- [x]`     | Completed action item                                        |
| `AGREED:`   | Formal agreement — surfaced in `notes --minutes`             |
| `RESOLVED:` | Formal resolution — surfaced in `notes --minutes`            |
| `!:`        | Important callout — surfaced in the `notes --pdf` summary    |

Action items can be prefixed with `(Assignee)` and `actions` will parse it out, e.g. `- [ ] (Riaz) Send the invite`.

### Subcommands

| Command              | What it does                                                    |
|----------------------|-----------------------------------------------------------------|
| `notes` / `--new`    | Create a new note and open it in the default markdown editor    |
| `--edit`             | Pick an existing note and edit it                               |
| `--nano`             | Pick an existing note and edit it in `nano`                     |
| `--last`             | Open the most recent note                                       |
| `--copy`             | Clone a note (keeps the original timestamp inside)              |
| `--strip`            | Clone a note keeping only headers — handy for templates         |
| `--delete`           | Delete a note                                                   |
| `--cat`              | Print a note to stdout                                          |
| `--actions`          | See [actions](#actions)                                         |
| `--pdf`              | Render selected note as PDF (saved to `~/Downloads`)            |
| `--minutes`          | Render as Meeting Minutes PDF (TOC, AGREED/RESOLVED/Action summary) |
| `--agenda`           | Render as Meeting Agenda PDF                                    |
| `--help`             | Full help                                                       |

The files `notes_new`, `notes_pdf`, `notes_minutes`, `notes_agenda`, and `notes_strip` are helpers invoked by `notes`. They expect environment variables exported by the parent script and are not meant to be called directly.

## actions

Indexes every `- [ ]` checkbox across all your notes, assigns each one a stable 5-character key the first time it sees it, and lets you edit the global list as a single text file in `nano`. Saving propagates the edits back to the original notes.

A history of every action ever seen — open, completed, or removed — is kept in `~/.adulting/actions_log.json`.

| Command                                       | What it does                                                                 |
|-----------------------------------------------|------------------------------------------------------------------------------|
| `actions`                                     | Open all open action items in `nano`; saving propagates back into the notes  |
| `actions --noninteractive`                    | Print the action items file instead of opening it (good for piping)          |
| `actions --update`                            | Refresh keys + log without opening anything                                  |
| `actions --query [--<field> <value>...]`      | Query the log; returns JSON                                                  |
| `actions --report [--<field> <value>...]`     | Same as `--query`, rendered as a table                                       |
| `actions --delete`                            | Open the JSON log directly for manual surgery                                |

Available query fields: `key`, `filename`, `topic`, `timestamp`, `current_time`, `thread`, `action_item_text`, `assignee`, `text`, `status`, `days_interval`. Example: `actions --query --thread SGB --status x`.

`notes` runs `actions --update` on every invocation, so the log stays current while you work.

## threads

Append-only logs for ongoing projects. Each thread is a markdown file in `~/.adulting/threads/<thread name>.md` with YAML frontmatter and a chronological list of bullets:

```markdown
---
status: open                # open | paused | closed
kind: process               # process (ongoing) | project (time-delimited)
category: professional      # professional | personal | voluntary
started: 2024-04-28
---

# <thread name>

- 2024-04-28 — Started on the IB integration.
    - Got the docker image working
    - Hit auth wall, debugging tomorrow
- 2024-05-17 — Made progress on rblncr.
- 2024-06-01 — Vendor decision finalised [[2024-06-01-14-30-00]].
```

What's a thread? Anything you want to keep an eye on — `Beetle Restoration`, `JIRA-1234`, `PTA Bake Sale`. I run `threads` at the end of each day to walk through every open thread and add a log line. Hit Enter to skip; type `CLOSED` to flip the thread to `status: closed` (and set `ended:` to today).

For an entry that warrants structure (multiple fields, action items, links), spawn a *note* and link to it from the thread bullet. Threads stay a cheap chronological log; notes are the home for typed records.

| Command                       | What it does                                                  |
|-------------------------------|---------------------------------------------------------------|
| `threads`                     | Daily review loop                                             |
| `threads --tail`              | Last log line for each open thread (status snapshot)          |
| `threads --report`            | Every log entry from the last 7 days, grouped by thread       |
| `threads --daily YYYY-MM-DD`  | Every log entry on that date — useful for time tracking       |
| `threads --overdue`           | Cadences past due, sorted worst-first                         |

### Cadences and overdue tracking

A thread can declare any number of recurring obligations under `cadences:`:

```yaml
cadences:
  - key: tax_return
    frequency: 31
    description: Monthly tax return, file before 7th
  - key: quarterly_review
    frequency: 90
    description: All-hands with trustees
```

A cadence is satisfied when a log entry is tagged with `#<key>`:

```markdown
- 2024-04-01 — #tax_return Filed for March
```

`threads --overdue` reports cadences whose most-recent matching entry is older than `frequency` days (or that have never been satisfied), sorted worst-first.

### Relationships (people)

Relationships are threads with `kind: relationship`, conventionally stored under `~/.adulting/threads/People/<Name>.md`. Each relationship typically has one cadence (`catch_up`) representing how often you want to be in touch. The same `threads --overdue` mechanism surfaces lapsed relationships alongside lapsed project obligations.

```yaml
---
status: open
kind: relationship
category: personal
started: 2024-04-26
cadences:
  - key: catch_up
    frequency: 30
    description: Catch up at least every month
---

# Charlie

- 2024-04-26 — #catch_up phone: He's moving out of his place end of April.
- 2024-05-08 — #catch_up message: Asked for guidance on rust.
```

## lint

Validates everything in `~/.adulting/` against the schemas in `schemas/`. Reports violations as `path:line: message` and exits 1 if any. Designed to be reused — other tools (or a save hook) can shell out to `lint <file>` for pre-save validation.

| Command          | What it does                                              |
|------------------|-----------------------------------------------------------|
| `lint`           | Walk the vault, validate every file, report violations    |
| `lint <path>`    | Validate one file (good for CI / pre-save hooks)          |
| `lint --quiet`   | Suppress per-violation output; just exit code             |

Schemas live in `schemas/` as markdown files with YAML frontmatter and a `## Fields` table. See `schemas/note_meeting.md` for the canonical shape; the format is simple enough to extend by hand.

# Data store

Everything lives under `~/.adulting/`:

```
~/.adulting/
├── .obsidian/                  # Obsidian vault config (already set up)
├── notes/                      # markdown notes (one file per note)
├── threads/                    # thread logs (one .md file per thread)
│   └── People/                 # relationship threads (kind: relationship)
└── actions_log.json            # full history of every action item ever seen
```

Files are plain text on purpose — back them up, version them, grep them, sync them across machines.

# Obsidian compatibility

The `~/.adulting/` directory is set up as an Obsidian vault: `.obsidian/` already lives in there with the standard core plugins enabled (Properties, Backlinks, Graph, Bases, Daily Notes, etc.). Open the folder in Obsidian and your notes render natively.

## What works today

- `notes/` markdown files render and are fully searchable
- All notes use YAML frontmatter, so Topic, Type, Thread, Timestamp, and meeting fields populate Obsidian's Properties panel and are queryable via Bases.
- `threads/` files are now `.md` with YAML frontmatter (`status`, `kind`, `category`, `started`, `ended`) and bullet-list entries — fully browsable in Obsidian and queryable in Bases ("show me all `kind: project` threads with `status: open`").
- Action checkboxes are picked up by Obsidian's task tracker
- The Daily Notes plugin is enabled (no script integration yet)

## Vault hygiene

- `actions`'s working file lives in the system temp directory — never appears as a stray note in the vault.
- `notes --pdf` / `--minutes` / `--agenda` run inside a `mktemp -d` workdir — no scratch files leak into your CWD.

## Roadmap

To make the vault first-class in Obsidian:

1. **Use `[[wikilinks]]` between notes and threads.** Notes name their thread as a string today; turning it into `[[Threads/<thread name>]]` would surface backlinks and graph edges. Same for assignees in action items (`[[People/Riaz]]`).
2. **Slug topics into note filenames.** `2024-04-29-09-03-15--sgb-onboarding.md` keeps the timestamp prefix (so existing parsing still works) but makes the file picker readable. Alternative: emit `aliases:` in the YAML frontmatter.
3. **Render markdown mirrors of remaining JSON state.** `actions` could keep `Actions/_index.md` updated (open items by thread/assignee); the JSON stays canonical, the markdown is a read-only view for browsing inside the vault.

# Suggestions / known issues beyond Obsidian

- `notes` portability: the `open -g` calls in `notes`, `notes_new`, and the renderers are macOS-only. README says the scripts run on Linux, but they currently won't open notes there. A `uname` switch to `xdg-open` would fix it.
- `actions` keeps a long-running JSON log (`actions_log.json`) but never garbage-collects entries for notes that were deleted. A `--prune` option that drops orphans would keep the log honest.

# Design goals

Each script should:

- Run on macOS or Linux (a few `open` calls assume macOS — see Suggestions above).
- Be one self-contained file per utility (with thin `notes_*` helpers).
- Require no libraries beyond what ships with the system.
- Be operated from the command line.
- Maintain state in simple text-based file formats.
- Maintain all state under the `~/.adulting/` hidden directory.
