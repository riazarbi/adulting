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

Prints a one-screen dashboard of your overdue contacts (from `networker`) and the latest log line on each open thread (from `threads`). Add `summary` to the bottom of `.zshrc`/`.bashrc` to see it on every new shell.

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

Append-only logs for ongoing projects. Each thread is a file in `~/.adulting/threads/<thread name>` containing one log line per row, formatted `YYYY-MM-DD | <text>`.

What's a thread? Anything you want to keep an eye on — `Beetle Restoration`, `JIRA-1234`, `PTA Bake Sale`. I run `threads` at the end of each day to walk through every open thread and add a log line. Hit Enter to skip; type `CLOSED` to retire one.

| Command                       | What it does                                                  |
|-------------------------------|---------------------------------------------------------------|
| `threads`                     | Daily review loop                                             |
| `threads --tail`              | Last log line for each open thread (status snapshot)          |
| `threads --report`            | Every log entry from the last 7 days, grouped by thread       |
| `threads --daily YYYY-MM-DD`  | Every log entry on that date — useful for time tracking       |

## networker

Tracks contacts and reminds you when you haven't reached out in a while. Each contact has a cadence (the `time_bucket`):

| Bucket      | Reminder cadence       |
|-------------|------------------------|
| `week`      | every 7 days           |
| `month`     | every 30 days          |
| `quarter`   | every 91 days          |
| `bi-annual` | every 182 days         |
| `year`      | every 365 days         |
| `adhoc`     | never overdue (mute)   |

State lives in two CSV files under `~/.adulting/`:

- `network_data.csv` — name, time_bucket, date_added
- `network_interactions.csv` — name, date, channel, notes

Run `networker` for the interactive menu, or jump straight to a menu option with the number, e.g. `networker 4` for overdue interactions:

| # | Action               |
|---|----------------------|
| 1 | Add Contact          |
| 2 | Update Time Bucket   |
| 3 | View Contact         |
| 4 | Overdue Interactions |
| 5 | List All Contacts    |
| 6 | Log Interaction      |
| 7 | Exit                 |

Don't want to see someone in your overdue list anymore? Set their bucket to `adhoc` (this mutes — it doesn't delete; the history stays in the CSVs).

## work

Lightweight billable-time logger. Each entry records date, task type, status, duration in minutes, project, description, and rate. State lives under `~/.adulting/work/`:

- `projects.txt` — one project name per line (created on the fly when you log against a new project)
- `rates.txt` — one hourly rate (integer) per line; **must be seeded before logging**
- `work_log.txt` — semicolon-delimited log entries

| Command         | What it does                                                       |
|-----------------|--------------------------------------------------------------------|
| `work`          | Log a new entry interactively                                      |
| `work --report` | Show the last 10 entries for a selected project (hours/rate/total) |

# Data store

Everything lives under `~/.adulting/`:

```
~/.adulting/
├── .obsidian/                  # Obsidian vault config (already set up)
├── notes/                      # markdown notes (one file per note)
├── threads/                    # thread logs (one file per thread, no extension)
├── work/                       # work logger state (projects, rates, log)
├── network_data.csv            # contacts
├── network_interactions.csv    # contact interactions
├── actions_log.json            # full history of every action item ever seen
└── pandoc.css                  # styling for HTML rendering (optional)
```

Files are plain text on purpose — back them up, version them, grep them, sync them across machines.

# Obsidian compatibility

The `~/.adulting/` directory is set up as an Obsidian vault: `.obsidian/` already lives in there with the standard core plugins enabled (Properties, Backlinks, Graph, Bases, Daily Notes, etc.). Open the folder in Obsidian and your notes render natively.

## What works today

- `notes/` markdown files render and are fully searchable
- Action checkboxes are picked up by Obsidian's task tracker
- The Daily Notes plugin is enabled (no script integration yet)

## Recent fixes for vault hygiene

- `actions` no longer drops its `.action_items.md` working file inside `notes/` — it now lives in the system temp directory, so it doesn't show up as a stray note in the vault while you edit.
- `notes --pdf` / `--minutes` / `--agenda` no longer scatter scratch files (`clean_output.md`, `agreed_lines.txt`, etc.) into your current directory — they now run inside a `mktemp -d` workdir.

## Roadmap

To make the vault first-class in Obsidian:

1. **Migrate note headers from bold-markdown to YAML frontmatter.** Today's metadata (`**Type**: ...`) renders fine but doesn't populate Obsidian's Properties panel and can't be queried with Bases. Switching to a YAML block (`---\ntype: ...\nthread: ...\n---`) on new notes — and updating `notes_minutes`, `notes_agenda`, `notes_pdf`, and `actions` to read both formats — would unlock Properties, Bases queries, and templated dashboards. Existing notes can stay on the legacy format until backfilled.
2. **Give thread files a `.md` extension and reformat as bullet lists.** Obsidian only indexes `.md` files, so `threads/` is invisible in the file explorer today. Renaming to `<thread>.md` and writing each entry as `- 2024-04-28 — note text` would make threads browsable, searchable, and linkable. The pipe-delimited parser in `threads --tail`/`--report`/`--daily` would need to match.
3. **Use `[[wikilinks]]` between notes and threads.** Notes name their thread as a string today; turning it into `[[Threads/<thread name>]]` would surface backlinks and graph edges. Same for assignees in action items (`[[People/Riaz]]`).
4. **Slug topics into note filenames.** `2024-04-29-09-03-15--sgb-onboarding.md` keeps the timestamp prefix (so existing parsing still works) but makes the file picker readable. Alternative: emit `aliases:` in the YAML frontmatter once that lands.
5. **Render markdown mirrors of CSV/JSON state.** `networker` could keep `Network/_index.md` updated (overdue table + per-contact pages); `actions` could keep `Actions/_index.md`. The CSVs/JSON stay canonical; the markdown is a read-only view for browsing inside the vault.
6. **Hook into the Daily Notes plugin.** `threads` could append your thread updates as bullets on today's daily note; `notes --new` could backlink the new note to the daily note. Closes the loop between journaling and project tracking.

# Suggestions / known issues beyond Obsidian

- `notes` portability: the `open -g` calls in `notes`, `notes_new`, and the renderers are macOS-only. README says the scripts run on Linux, but they currently won't open notes there. A `uname` switch to `xdg-open` would fix it.
- `notes_*` helpers depend on env vars (`NOTES_DIR`, `THREAD_DIR`, `CSS_LOCATION`, `DOWNLOADS_DIR`) exported by `notes`. Calling them directly silently produces broken output. Adding a small "if unset, default and warn" block at the top of each helper would make them self-contained.
- `actions` keeps a long-running JSON log (`actions_log.json`) but never garbage-collects entries for notes that were deleted. A `--prune` option that drops orphans would keep the log honest.
- `work` records hours per project but has no reporting across projects (totals, monthly summaries). A `--summary` mode would round it out.

# Design goals

Each script should:

- Run on macOS or Linux (a few `open` calls assume macOS — see Suggestions above).
- Be one self-contained file per utility (with thin `notes_*` helpers).
- Require no libraries beyond what ships with the system.
- Be operated from the command line.
- Maintain state in simple text-based file formats.
- Maintain all state under the `~/.adulting/` hidden directory.
