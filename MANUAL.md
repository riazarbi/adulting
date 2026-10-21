# adulting — Operators Manual

## Before you start

**Where data lives.** Everything lives under one vault directory, `~/vault` by default. Set `ADULTING_HOME` to use a different directory. Every command builds its paths from that root.

```
export ADULTING_HOME=<path-to-vault>
```

**External programs.**

| Program | Needed by |
|---|---|
| Python 3.11 or newer | every tool |
| `git` | `commit` |
| `pandoc` and a LaTeX engine (`xelatex`) | `notes pdf`, `notes minutes`, `notes agenda`, `payments statement --pdf` |

**Plain text.** All state is Markdown, YAML frontmatter and fenced JSON on disk. There is no database. You can read, grep and back up the vault yourself.

**No prompts.** No command is interactive. Every value comes from arguments, and deleting needs `-y`.

## How the pieces fit

`<Kind>` is `Projects`, `Processes` or `Topics`. Paths are relative to the vault root.

| Object | What it is | Where it lives |
|---|---|---|
| Thread | A project, process or topic that organises everything else | `threads/<Kind>/<Name>.md` |
| Note | A typed document: meeting, correspondence, report and so on | `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md` |
| Log | One file per thread per day, written by `buffer flush` | `threads/<Kind>/<Name>/logs/<YYYY-MM-DD>.md` |
| Person | A contact you track | `people/<Name>.md` |
| Time entry | One session of work, billable or not | `threads/<Kind>/<Name>/hours.md` |
| Payment | Money received against a thread | `threads/<Kind>/<Name>/payments.md` |
| Action / task | An `ACTION:` line that becomes a `TASK:` anchor, then `DONE:` | a line inside a note or log |
| Buffer | The staging queue for quick captures | `buffer.md` |
| Config | Vault-wide settings: hours defaults, billing | `.adulting/config.yaml` |

A thread's file sits beside its folder. The folder holds everything that belongs to that thread.

**Relationships**

- A note belongs to one or more threads. It is filed under the first thread it names.
- A note can list people as attendees.
- A task can have a person as its assignee. It can depend on other tasks.
- Time entries and payments belong to exactly one thread.
- `notes new`, `hours log` and `payments log` each add a `REF:` to the buffer. `buffer flush` files it in the thread's log for the day the event happened.
- A person is never a thread.

## Command reference

### tasks

Turns `ACTION:` lines into tracked `TASK:` anchors and edits those anchors in place.

**When to use it**

- You wrote `ACTION:` lines in a note and want them tracked.
- You need to see what to do next, or what is overdue.
- You finished a task, or need to change its due date, priority, assignee or dependencies.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `ingest` | Rewrites every `ACTION:` line in notes and logs as a `TASK:` anchor. Bare `tasks` does the same. | `tasks ingest --dry-run` |
| `add` | Adds an ACTION to the buffer. Same as `buffer add-action`. | `tasks add Projects/Northwind "(Sam Rivera) Send revised scope" --due 2026-10-31 --priority H` |
| `done` | Changes `TASK` to `DONE` and stamps `end:` with today's date. | `tasks done <uuid>` |
| `set-description` | Rewrites the task text. | `tasks set-description <uuid> "Send revised scope and budget"` |
| `set-assignee` | Rewrites the `(Assignee)` prefix. | `tasks set-assignee <uuid> "Sam Rivera"` |
| `set-due` | Sets the due date. | `tasks set-due <uuid> 2026-11-07` |
| `set-scheduled` | Sets the scheduled date. | `tasks set-scheduled <uuid> 2026-11-03` |
| `set-priority` | Sets priority `H`, `M` or `L`. | `tasks set-priority <uuid> H` |
| `add-depends` | Makes this task wait on another task. | `tasks add-depends <uuid> <dep-uuid>` |
| `rm-depends` | Removes a dependency. | `tasks rm-depends <uuid> <dep-uuid>` |
| `list` | Lists pending tasks, grouped by thread. | `tasks list --overdue` |
| `next` | Shows the top 5 pending tasks by priority, then due date, then entry date. | `tasks next` |
| `show` | Shows one task in detail. | `tasks show <uuid>` |

**Options**

Global (bare `tasks` and `tasks ingest`):

| Option | Effect |
|---|---|
| `--dry-run` | Shows what would be ingested. Writes nothing. |
| `--quiet` | Suppresses per-action output. |

| Option | Effect |
|---|---|
| `add --due <YYYY-MM-DD>` | Sets the due date. |
| `add --scheduled <YYYY-MM-DD>` | Sets the scheduled date. |
| `add --priority <H\|M\|L>` | Sets the priority. |
| `add --depends <uuid>` | Adds a dependency. You can repeat it. |
| `list --priority <H\|M\|L>` | Shows only that priority. |
| `list --thread <Kind/Name>` | Shows only tasks whose source note carries that thread. |
| `list --assignee <person>` | Shows only tasks assigned to that person. |
| `list --overdue` | Shows only tasks whose due date is before today. |
| `list --json` | Prints JSON. |

**Notes**

- Every subcommand except `list`, `next` and `show` rewrites note or log files in place. Those files are the only task store.
- A `<uuid>` argument accepts any unique prefix of the 8-character uuid shown by `tasks list`.
- `tasks add` only adds to the buffer. The task exists after `buffer flush`.
- Exit `1` means one of these: no task matches the prefix, the prefix is empty, the date is not `YYYY-MM-DD`, the description is empty, a task depends on itself, or the person has no `people/<name>.md`.

### notes

Creates, lists, prints, copies, deletes and renders notes. Each note is identified by its stem.

**When to use it**

- You are starting a meeting record, a correspondence log or a report.
- You need a note's content, or the path of the note you just wrote.
- You need minutes, an agenda or a PDF to send someone.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Creates a note and prints its path. | `notes new --type Meeting --topic "Scope review" --thread Projects/Northwind --person "Sam Rivera"` |
| `list` | Lists notes, oldest first: stem, date, type, threads, topic. | `notes list northwind` |
| `cat` | Prints a note. | `notes cat 2026-09-10-14-30-00` |
| `last` | Prints the path of the newest note. | `notes last` |
| `copy` | Copies a note to a new timestamp and appends ` COPY` to its topic. | `notes copy 2026-09-10-14-30-00` |
| `delete` | Deletes a note permanently. | `notes delete 2026-09-10-14-30-00 -y` |
| `pdf` | Renders the note to Markdown and PDF, with callouts and an action table. | `notes pdf 2026-09-10-14-30-00` |
| `minutes` | Renders meeting minutes: agreements, resolutions and action items. | `notes minutes 2026-09-10-14-30-00` |
| `agenda` | Renders the note as an agenda, with the outcome sections emptied. | `notes agenda 2026-09-10-14-30-00 --out <dir>` |

**Options**

| Option | Effect |
|---|---|
| `new --type <type>` | Required. One of `Meeting`, `Correspondence`, `Workshop`, `Report`, `Log`, `Research`, `Recipe`. |
| `new --topic <text>` | Required. What the note is about. |
| `new --thread <Kind/Name>` | Required. You can repeat it. The first thread decides where the note is filed. |
| `new --person <name>` | `Meeting` and `Correspondence` only. Adds an attendee. You can repeat it. The name is linked when `people/<name>.md` exists. |
| `new --counterparty <text>` | `Meeting` only. The other party. |
| `new --location <text>` | `Meeting` only. Where the meeting was held. |
| `list <filter>` | Case-insensitive match in any column. |
| `list --json` | Prints JSON. |
| `delete -y`, `--yes` | Required to delete. |
| `pdf`/`minutes`/`agenda --out <dir>` | Output directory. The default is `~/Downloads`. |

**Notes**

- Every subcommand except `new` runs task ingest first. That rewrites `ACTION:` lines in source files, even for `list` and `cat`.
- `notes new` adds a `REF:` to the buffer.
- Renders are written as `<stem>.md` and `<stem>.md.pdf`.
- `delete` cannot be undone.
- Exit `1` means one of these: an option was used with the wrong note type, the topic is empty, the stem is malformed, the vault has no notes, or the PDF render failed.

### search

Finds notes and logs, and summarises thread activity. It is read-only.

**When to use it**

- You need to find a past meeting or log entry by thread, type, date or text.
- You want to see which threads were active in a period.
- You want everything that happened on one thread, or today, in date order.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `notes` | Finds notes by thread, type, date or text. | `search notes --thread Projects/Northwind --type Meeting` |
| `logs` | Finds daily logs by thread, date or text. | `search logs --text "scope" --since 2026-09-01` |
| `activity` | Ranks threads by activity in a date window. | `search activity --since 2026-10-01` |
| `overview` | Shows the whole picture of one thread. | `search overview Projects/Northwind` |
| `stream` | Merges every dated record into one chronology. | `search stream --today` |

**Options**

| Option | Effect |
|---|---|
| `--since <YYYY-MM-DD>`, `--until <YYYY-MM-DD>` | Date window, inclusive. Available on all subcommands. |
| `--json` | Prints JSON. Available on all subcommands. |
| `--thread <Kind/Name>` | Limits results to one thread. Available on `notes`, `logs`, `activity` and `stream`. |
| `--text <text>` | Case-insensitive literal match. `notes` searches topic and body, `logs` searches entry lines, and `stream` searches thread and summary. |
| `notes --type <type>` | Note type, case-insensitive. |
| `--limit <n>` | Maximum results. `0` means all. Defaults are 20 for `notes` and `logs`, 5 for `overview` and 100 for `stream`. |
| `stream --kind <list>` | Comma-separated: `note`, `log`, `task`, `done`, `hours`, `payment`, `thread`, `person`, `pending`. The default is all. |
| `stream --today` | Same as `--since` and `--until` today. |
| `stream --reverse` | Oldest first. The default is newest first. |

**Notes**

- Results are absolute paths plus metadata, never file bodies. Open the files with `notes cat` or a reader.
- Dates are event dates from frontmatter `timestamp`, not file creation dates.
- Time entries are not searched by `--text`. Put detail in a log line, not in an hours description.
- Exit `1` means `--kind` was given an unknown kind.

### threads

Creates and shows thread files.

**When to use it**

- You are starting a new project, process or topic.
- You need a thread's exact `Kind/Name` for another command.
- You want to check a thread's status or billing defaults.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists thread files. Open threads only by default. | `threads list north` |
| `show` | Shows one thread file. | `threads show Projects/Northwind` |
| `new` | Creates a thread file. | `threads new --name Northwind --kind project --category professional --currency EUR --rate 120` |

**Options**

| Option | Effect |
|---|---|
| `list <query>` | Fuzzy search, ranked by similarity. |
| `list --all` | Includes paused and closed threads. |
| `list`/`show --json` | Prints JSON. |
| `new --name <name>` | Required. Becomes the filename. Cannot contain `/` or start with `.`. |
| `new --kind <project\|process\|topic>` | Required. Selects `Projects/`, `Processes/` or `Topics/`. |
| `new --category <professional\|personal\|voluntary>` | Required. |
| `new --currency <ISO>` | Default currency for `hours`. Its presence makes the thread billable. |
| `new --rate <n>` | Default hourly rate for `hours`. Needs `--currency`. |

**Notes**

- There is no close or delete command. To close a thread, set `status: closed` and `ended:` in its frontmatter. To remove one, delete its file and folder by hand.
- Exit `1` means one of these: the name is empty or invalid, the thread already exists, or `--rate` was given without `--currency`.

### people

Manages person files.

**When to use it**

- You need someone as a meeting attendee or task assignee.
- You need to look up a contact's file.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists person files. Open people only by default. | `people list sam` |
| `show` | Shows one person file. | `people show "Sam Rivera"` |
| `new` | Creates a person file. | `people new --name "Sam Rivera" --category professional` |
| `delete` | Deletes a person file permanently. | `people delete "Sam Rivera" -y` |

**Options**

| Option | Effect |
|---|---|
| `list <query>` | Fuzzy search, ranked by similarity. |
| `list --all` | Includes closed people. |
| `list`/`show --json` | Prints JSON. |
| `new --name <name>` | Required. Full name. Becomes the filename. |
| `new --category <professional\|personal\|voluntary>` | Required. |
| `delete -y`, `--yes` | Required to delete. |

**Notes**

- `delete` cannot be undone. Links to that person in notes and tasks will no longer resolve.
- Exit `1` means one of these: the name is empty or invalid, the person already exists, the person was not found, or `-y` is missing on delete.

### hours

Records time spent on a thread, billable or not.

**When to use it**

- You finished a session of client work.
- You want to track unbilled time, such as reading or exercise.
- You need hour and money totals for a period.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Adds an entry. | `hours log Projects/Northwind -m 90 Scope workshop` |
| `list` | Lists entries. | `hours list Projects/Northwind --since 2026-09-01` |
| `report` | Totals by thread and currency. Unbilled time is totalled separately. | `hours report --since 2026-09-01 --until 2026-09-30` |
| `show` | Shows one entry. | `hours show <id>` |
| `edit` | Changes one field of an entry. | `hours edit <id> -m 120` |
| `rm` | Deletes an entry permanently. | `hours rm <id> -y` |

**Options**

| Option | Effect |
|---|---|
| `log -m`, `--minutes <n>` | Duration in minutes. The default is 60. It must be positive. |
| `log -r`, `--rate <n>` | Hourly rate. `0` means unbillable. |
| `log -c`, `--currency <ISO>` | Currency. Defaults to the thread's. With no currency from either, the entry is unbilled. |
| `log -d`, `--date <YYYY-MM-DD>` | Date. The default is today. |
| `log -t`, `--time <HH:MM>` | Start time. The default is now. |
| `list <thread>`, `report --thread <thread>` | Limits results to one thread. |
| `list`/`report --since`, `--until <YYYY-MM-DD>` | Date window. |
| `--json` | Prints JSON. Available on `list`, `report` and `show`. |
| `edit --description <text>` | New description. |
| `edit -m <n>` | New duration. The start time stays the same. |
| `edit -r <n>` | New rate. Needs a currency. |
| `edit -c <ISO>` | New currency. |
| `edit -d <YYYY-MM-DD>` / `-t <HH:MM>` | Moves the entry. The duration stays the same. |
| `rm -y`, `--yes` | Required to delete. |

**Notes**

- Give `hours log` a description. It becomes the invoice line item. Keep it short.
- Each `log` adds a `REF:` to the buffer, filed under the day the work happened.
- Rate and currency are stored on each entry when you log it. Changing a thread's defaults later does not re-price old entries.
- Exit `1` means one of these: the minutes are not positive, a rate was given without a currency, the description is empty, or an entry has a rate but no currency.

### payments

Records money received against a thread and compares it with what was billed.

**When to use it**

- A client payment landed.
- You need a billed-versus-received statement, or a PDF statement for a client.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Records a payment received. | `payments log Projects/Northwind 4500.00 -d 2026-10-05 -a "Business account"` |
| `list` | Lists payments. | `payments list Projects/Northwind` |
| `statement` | Shows billed versus received, by thread and currency. | `payments statement --thread Projects/Northwind` |
| `show` | Shows one payment. | `payments show <id>` |
| `edit` | Changes one field of a payment. | `payments edit <id> --amount 4550.00` |
| `rm` | Deletes a payment permanently. | `payments rm <id> -y` |

**Options**

| Option | Effect |
|---|---|
| `log -c`, `--currency <ISO>` | Currency. Defaults to the thread's. |
| `log -d`, `--date <YYYY-MM-DD>` | Date received. The default is today. |
| `log -t`, `--time <HH:MM>` | Time received. The default is now. |
| `log -a`, `--account <text>` | Account the money landed in. |
| `log -n`, `--note <text>` | Free-text note. |
| `list <thread>`, `statement --thread <thread>` | Limits results to one thread. |
| `list`/`statement --since`, `--until <YYYY-MM-DD>` | Date window. |
| `statement --as-of <YYYY-MM-DD>` | Statement date, which drives aging. The default is today. |
| `statement --pdf <path>` | Renders a PDF to that path. Needs `--thread`. |
| `--json` | Prints JSON. Available on `list`, `statement` and `show`. |
| `edit --amount`, `-c`, `-d`, `-t`, `-a`, `-n` | Replace that field. |
| `rm -y`, `--yes` | Required to delete. |

**Notes**

- Always give `log` an amount. It must be positive. A refund is not a negative payment.
- Each `log` adds a `REF:` to the buffer, filed under the day the money was received.
- `statement` ignores unbilled hours.
- `statement --pdf` takes the client from the thread's `client_name` field. Only `client_name` is required.
- Exit `1` means one of these: the amount is missing, invalid or not positive, `--pdf` was given without `--thread`, or there is nothing to state for the thread at that date.

### stats

Declares measured numbers on a thread, logs values, and shows them over time.

**When to use it**

- You want to track a count or measurement, such as push-ups, steps or kilometres run.
- You want to record that an event happened. Use an `int` stat and log `1`.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Declares a stat in a thread file's frontmatter. | `stats new pushups --thread Topics/Fitness --type int --agg sum` |
| `list` | Lists declared stats. | `stats list` |
| `log` | Adds a value to the buffer. | `stats log pushups 25` |
| `series` | Shows the value per day, week or month. | `stats series pushups --by week --since 2026-09-01` |

**Options**

| Option | Effect |
|---|---|
| `new --thread <Kind/Name>` | Required. The thread that owns the stat. |
| `new --type <int\|decimal>` | Required. `int` takes whole numbers. `decimal` takes plain numbers such as `12.50`. |
| `new --agg <sum\|last\|max>` | Required. How a period's values combine: add them, take the latest, or take the largest. |
| `log -d`, `--date <YYYY-MM-DD>` | Date. The default is today. |
| `log -t`, `--time <HH:MM>` | Time. The default is now. |
| `series --by <day\|week\|month>` | Period length. The default is `day`. Weeks start on Monday. |
| `series --since`, `--until <YYYY-MM-DD>` | Date window. |
| `list`/`series --json` | Prints JSON. |

**Notes**

- Stat names use lowercase letters, digits and `-`. They are unique across the vault, so `log` needs no thread.
- `new` edits the thread file's frontmatter.
- There is no rename or delete. Edit the frontmatter by hand. Values already logged are not rewritten.
- In `series`, a period with no values shows `-` (`null` in JSON), not `0`.
- Exit `1` means nothing was written. The reason is on stderr: an undeclared or duplicate name, the wrong value type, a bad date or time, `--since` after `--until`, or a bad logged value. Exit `2` is a usage error.

### buffer

The staging queue. Captures land here, then `flush` files them into thread logs.

**When to use it**

- You want to record something quickly without writing a note.
- You need to fix or remove a capture before filing.
- At the end of a session, to file everything into daily logs.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `add` | Adds a raw `UNKNOWN` entry with no thread. | `buffer add "ask Sam about the second workshop"` |
| `add-text` | Adds a `TEXT` observation to a thread. | `buffer add-text Projects/Northwind "Client approved the revised scope"` |
| `add-ref` | Adds a `REF` pointer to another vault file. | `buffer add-ref Projects/Northwind 2026-09-10-14-30-00 "scope review notes"` |
| `add-action` | Adds an `ACTION` entry. | `buffer add-action Projects/Northwind "(Sam Rivera) Send signed SOW" --due 2026-10-31` |
| `list` | Shows the buffer with line numbers. | `buffer list` |
| `rm` | Removes one line by its number. | `buffer rm 3` |
| `tend` | Regroups entries by thread and date, then validates them. | `buffer tend` |
| `flush` | Tends, writes each thread's logs, clears the buffer, and ingests the flushed ACTIONs. | `buffer flush` |

**Options**

Global:

| Option | Effect |
|---|---|
| `--quiet` | Suppresses info output. |

| Option | Effect |
|---|---|
| `--date <YYYY-MM-DD>` | Files the entry under the day the thing happened. Available on every `add*` subcommand. |
| `add-action --due`, `--scheduled <YYYY-MM-DD>` | Due date and scheduled date for the task. |
| `add-action --priority <H\|M\|L>` | Task priority. |
| `add-action --depends <uuid>` | Task dependency. You can repeat it. |
| `list <filter>` | Shows only lines containing that text, ignoring case. |
| `list --json` | Prints JSON. |

**Notes**

- `UNKNOWN` entries fail `tend` and block `flush`. Remove them with `rm` and re-add them with an `add-*` subcommand.
- Use these commands to change `buffer.md`. Do not edit it by hand.
- `flush` ingests tasks itself. You do not need to run `tasks` after it.
- `flush` reports:
  - `already a task`: the ACTION matches an open task and was skipped.
  - `already buffered`: the ACTION repeats another buffer entry.
  - `due updated`: the ACTION differs from an open task only by due date, so that task's due date was moved.
  - `ambiguous`: the ACTION matches several open tasks. Nothing changed.
- Line numbers change after `rm` or `tend`. Run `list` again before the next `rm`.
- Exit `1` means one of these: the line number is not an integer, is out of range or is empty, or validation failed.

### lint

Validates vault files against the schemas in [Data formats](#data-formats).

**Usage**

```
lint [--quiet] [--schemas <dir>] [<path> ...]
```

| Argument | Effect |
|---|---|
| `<path> ...` | Files to validate. With none, it checks the whole vault. |
| `--quiet` | Prints nothing. Only the exit code reports the result. |
| `--schemas <dir>` | Uses a different schemas directory. |

**Notes**

- Read-only.
- Errors print as `<path>:<line>: <message>`, with an absolute path.
- Exit `0` means clean. Exit `1` means violations. Exit `2` means no schemas were loaded.
- `lint` is the only command that reports files that are not valid UTF-8. Other commands skip those files silently.

### commit

Reviews and commits vault changes to git.

**When to use it**

- At the end of a session, to record what changed.
- Before a risky edit, so you have a clean point to return to.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `review` | Shows everything changed since the last commit. Read-only. | `commit review` |
| `save` | Stages every change in the vault and commits it. | `commit save --message "Northwind: scope review and September hours" --body "Logged 6h; recorded payment."` |

**Options**

| Option | Effect |
|---|---|
| `review --max-file-lines <n>` | Maximum diff lines per file. The default is 150. |
| `review --max-lines <n>` | Maximum output lines overall. The default is 3000. |
| `save --message <text>` | Required. A single-line commit subject. |
| `save --body <text>` | Commit body. It can span several lines. |
| `save --dry-run` | Reports what would be staged and committed. Changes nothing. |

**Notes**

- `save` only ever adds a commit. It never amends, rebases, resets, checks out or pushes.
- `ADULTING_HOME` must be the root of its own git repository.
- Exit `1` means one of these: the message is empty or multi-line, the vault is not a git repository, `ADULTING_HOME` is not the repository root, or a git command failed.

## Everyday procedures

### 1. Set up a new billable project

1. `threads new --name Northwind --kind project --category professional --currency EUR --rate 120`: creates `threads/Projects/Northwind.md` with billing defaults.
2. `people new --name "Sam Rivera" --category professional`: creates the client contact.
3. Add `client_name` (and optionally `client_address`, `client_vat`, `client_email`) to the frontmatter of `threads/Projects/Northwind.md`. Statements need `client_name`.
4. `lint threads/Projects/Northwind.md`: checks the edited file.
5. `threads show Projects/Northwind`: confirms the result.

### 2. Capture a meeting and turn its actions into tracked tasks

1. `notes new --type Meeting --topic "Scope review" --thread Projects/Northwind --person "Sam Rivera" --counterparty Northwind --location "Cape Town"`: creates the note and prints its path.
2. Open that path and write the body. Put each commitment on its own line, for example `ACTION: (Sam Rivera) Send the revised scope`.
3. `tasks --dry-run`: previews which ACTION lines will be ingested.
4. `tasks`: rewrites them as `TASK:` anchors.
5. `tasks list --thread Projects/Northwind`: shows the new tasks with their uuids.
6. `notes minutes <stem>`: renders the minutes to `~/Downloads`.
7. `buffer flush`: files the note's `REF:` into the thread's daily log.

### 3. Quick-capture through the day, then file it

1. `buffer add "ask Sam about the second workshop"`: captures a thought with no thread.
2. `buffer add-text Projects/Northwind "Client approved the revised scope"`: captures an observation against a thread.
3. `tasks add Projects/Northwind "(Sam Rivera) Send signed SOW" --due 2026-10-31`: captures a commitment.
4. `buffer list`: shows each entry with its line number.
5. `buffer rm <line-number>`: removes the `UNKNOWN` entry, then re-add it with `buffer add-text` or `buffer add-action`.
6. `buffer tend`: validates the buffer. Fix anything it reports.
7. `buffer flush`: writes the daily logs, clears the buffer and creates the tasks.

### 4. Work the task list

1. `tasks next`: shows the top five pending tasks.
2. `tasks list --overdue`: shows tasks past their due date.
3. `tasks show <uuid>`: shows one task in full.
4. `tasks set-due <uuid> 2026-11-07`: moves a deadline.
5. `tasks set-priority <uuid> H`: raises a task's priority.
6. `tasks add-depends <uuid> <dep-uuid>`: makes a task wait on another task.
7. `tasks done <uuid>`: marks a task complete.

### 5. Log a session of work

1. `hours log Projects/Northwind -m 90 Scope workshop`: records 90 minutes, ending now, at the thread's rate.
2. `hours log Projects/Northwind -m 60 -d 2026-10-20 -t 14:00 Draft proposal`: records a backdated session.
3. `buffer add-text Projects/Northwind "Agreed to split delivery into two phases"`: records what happened. Hours descriptions are not searchable.
4. `hours list Projects/Northwind --since 2026-10-20`: checks the entries and their ids.
5. `hours edit <id> -m 120`: corrects a duration if needed.
6. `buffer flush`: files the `REF:` pointers into the daily logs.

### 6. Bill a client for a month's work

1. `hours list Projects/Northwind --since 2026-09-01 --until 2026-09-30`: checks each line item.
2. `hours edit <id> --description "Scope workshop"`: fixes any line item before it reaches the client.
3. `hours report --thread Projects/Northwind --since 2026-09-01 --until 2026-09-30`: shows the month's totals.
4. `payments statement --thread Projects/Northwind --as-of 2026-09-30`: shows billed versus received.
5. `payments statement --thread Projects/Northwind --as-of 2026-09-30 --pdf <path>.pdf`: renders the statement for the client.

### 7. Record a payment

1. `payments log Projects/Northwind 4500.00 -d 2026-10-05 -a "Business account" -n "September statement"`: records the money received.
2. `payments list Projects/Northwind`: confirms the entry and shows its id.
3. `payments statement --thread Projects/Northwind`: shows the updated balance.
4. `buffer flush`: files the payment's `REF:` into that day's log.

### 8. Check the vault and commit it

1. `buffer flush`: files anything still in the buffer.
2. `lint`: validates the whole vault. Exit `0` means clean.
3. `commit review`: shows everything changed since the last commit.
4. `commit save --message "<summary>" --dry-run`: previews what will be committed.
5. `commit save --message "<summary>" --body "<detail>"`: commits.

## Data formats

`lint` enforces every format below. Paths are relative to the vault root. `<Kind>` is `Projects`, `Processes` or `Topics`.

### `hours_file`

A thread's time entries, kept as JSON inside one `simple-time-tracker` fenced block. It lives at `threads/<Kind>/<Name>/hours.md` and is maintained by `hours`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to the owning thread. It must resolve, and it must be the thread whose folder holds the file. |
| `currency` | no | Three-letter ISO code. Omitted for unbilled threads. |
| `entries[].name` | yes | The description, which is the invoice line item. |
| `entries[].startTime` | yes | ISO 8601 UTC start time. |
| `entries[].endTime` | yes | ISO 8601 UTC end time. Not before `startTime`. |
| `entries[].id` | yes | 8 hex characters. Unique across hours and payments. |
| `entries[].rate` | yes | Hourly charge. `0` means unbillable. |
| `entries[].currency` | no | ISO code. Absent or null means unbilled. |

Duration is `endTime` minus `startTime`. There is no duration field.

### `log`

One thread's activity for one day, written by `buffer flush`. It lives at `threads/<Kind>/<Name>/logs/<YYYY-MM-DD>.md`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to the owning thread. It must be the thread whose folder holds the file. |
| `date` | yes | The day, `YYYY-MM-DD`. |
| `type` | yes | Always `Log`. |

Body lines are `TEXT:`, `REF:`, `ACTION:`, `TASK:`, `DONE:` and `STAT:`.

### `note_correspondence`

A record of emails, messages or letters. It lives at `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md`, under its first thread.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about. |
| `type` | yes | `Correspondence`. |
| `threads` | yes | List of thread wikilinks. Each must resolve. The first decides the folder. |
| `timestamp` | yes | When it happened, `YYYY-MM-DD-HH-MM-SS`. |
| `people` | no | Participants: `[[people/X]]` links, which must resolve, or plain names. |

Body markers are `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:` and `!:` for callouts.

### `note_meeting`

A record of a meeting. It lives at `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md`, under its first thread.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the meeting was about. |
| `type` | yes | `Meeting`. |
| `threads` | yes | List of thread wikilinks. Each must resolve. The first decides the folder. |
| `timestamp` | yes | When it happened, `YYYY-MM-DD-HH-MM-SS`. |
| `counterparty` | no | The other party. |
| `location` | no | Where it was held. |
| `people` | no | Attendees: `[[people/X]]` links, which must resolve, or plain names. |

Body markers are `ACTION:`, `TASK:`, `AGREED:` and `RESOLVED:`, which appear in minutes, and `!:` for callouts.

### `note_simple`

A Workshop, Report, Log, Research or Recipe note. It lives at `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md`, under its first thread.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about. |
| `type` | yes | `Workshop`, `Report`, `Log`, `Research` or `Recipe`. |
| `threads` | yes | List of thread wikilinks. Each must resolve. The first decides the folder. |
| `timestamp` | yes | When it happened, `YYYY-MM-DD-HH-MM-SS`. |
| `people` | no | `[[people/X]]` links or plain names. |

The body uses the same markers as `note_meeting`.

### `payments_file`

A thread's received payments, kept as JSON inside one `adulting-payments` fenced block. It lives at `threads/<Kind>/<Name>/payments.md` and is maintained by `payments`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to the owning thread. It must resolve, and it must be the thread whose folder holds the file. |
| `currency` | yes | Three-letter ISO code. |
| `payments[].id` | yes | 8 hex characters. Unique across hours and payments. |
| `payments[].received` | yes | ISO 8601 UTC time the money landed. |
| `payments[].amount` | yes | Greater than zero. |
| `payments[].currency` | yes | ISO code. |
| `payments[].account` | no | Account the money landed in. |
| `payments[].note` | no | Free text. |

### `person`

A contact you track. It lives at `people/<Name>.md`. The body is free-form.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | `YYYY-MM-DD`. |
| `ended` | no | `YYYY-MM-DD`. Required when `status` is `closed`. |
| `cadences` | no | List of `{key, frequency, description}`, the same as on threads. |

### `stat_line`

One value of a declared stat, as a line in a log (`threads/<Kind>/<Name>/logs/<YYYY-MM-DD>.md`). For example: `STAT: pushups 25 <!--2026-10-07T07:42:10-->`.

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | A stat declared in this log's thread. |
| `value` | yes | A number. Whole numbers only for `int` stats. |
| `ts` | yes | Local time, `YYYY-MM-DDTHH:MM:SS`. Its date must equal the log's `date`. |

A `STAT:` line belongs only in a log, never in a note or thread file.

### `task_anchor`

A `TASK:` or `DONE:` line in a note or log. It is the only record of a task's state. Change it with `tasks` subcommands, not by hand. For example: `TASK: [#H] (Sam Rivera) Send quarterly report <!--abcd1234 entry:2026-05-27 due:2026-05-29-->`.

| Field | Required | Meaning |
|---|---|---|
| `kind` | yes | `TASK` or `DONE`. |
| `priority` | no | `H`, `M` or `L`, shown as `[#X]`. |
| `assignee` | no | Shown as `(Name)`. Must resolve to `people/<name>.md`. |
| `body` | yes | The task text. |
| `uuid` | yes | 8 hex characters. Unique across the vault. |
| `entry` | yes | Ingest date. |
| `end` | no | Completion date. Required for `DONE`. Not before `entry`. |
| `due` | no | Due date. |
| `scheduled` | no | Scheduled date. |
| `depends` | no | Comma-separated uuids of other tasks. The dependencies must not form a cycle. |

### `thread`

A project, process or topic. It lives at `threads/<Kind>/<Name>.md`, beside its folder. The body is a dated log of `thread_entry` lines.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `kind` | yes | `project`, `process` or `topic`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | `YYYY-MM-DD`. |
| `ended` | no | `YYYY-MM-DD`. Required when `status` is `closed`. |
| `cadences` | no | List of `{key, frequency, description}`. `frequency` is in days. |
| `stats` | no | List of `{name, type, agg}`, written by `stats new`. |
| `currency` | no | Default ISO currency for `hours`. |
| `rate` | no | Default hourly rate for `hours`. |
| `client_name` | no | Billed party on a PDF statement. Required to render one. |
| `client_address` | no | Lines separated by `\|`, for example `Unit 301\|2 Park Road\|Cape Town`. |
| `client_vat` | no | Client VAT number. |
| `client_email` | no | Client email. |

### `thread_entry`

A dated top-level bullet in a thread file's body (`threads/<Kind>/<Name>.md`). For example: `- 2024-05-17 — Made progress on rblncr.` Indented sub-bullets are not validated.

| Field | Required | Meaning |
|---|---|---|
| `date` | yes | `YYYY-MM-DD`. |
| `text` | yes | The entry text. Not empty. |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `buffer tend` or `buffer flush` reports `UNKNOWN` entries | Raw captures from `buffer add` block flushing. | Run `buffer list`, then `buffer rm <line-number>`. Re-add the entry with `buffer add-text` or `buffer add-action`. |
| `buffer flush` reports `ambiguous` | The ACTION matches several open tasks, so nothing changed. | Run `tasks list`, then change the right task with a `tasks set-*` subcommand. |
| `no task found with uuid prefix ...` | The uuid prefix matches no task. | Get the uuid from `tasks list`. |
| `person '...' does not resolve to people/....md` | The assignee has no person file. | Run `people new --name "<name>" --category <category>`. |
| `--rate needs a --currency` | A rate was given with no currency to express it in. | Add `--currency <ISO>` (`-c` on `hours`). |
| `--person is only for Meeting and Correspondence notes` | `notes new` was given an option that does not apply to that type. | Remove the option, or use `--type Meeting`. `--counterparty` and `--location` are for Meeting only. |
| `refusing to delete ... without -y` | Deletes need confirmation. | Add `-y` to the command. |
| `--pdf needs --thread; a statement is per client` | `payments statement --pdf` was run without a thread. | Add `--thread <Kind/Name>`. |
| `PDF render failed: ...` | The render step failed. It needs `pandoc` and `xelatex`. | Install `pandoc` and a LaTeX engine, then run the command again. |
| `lint` shows `<path>:0: file is not valid UTF-8` | A non-UTF-8 file is in the vault. Other commands skip it silently. | Re-save the file as UTF-8, or remove it. |
| `lint` exits `2` with `no schemas loaded` | `--schemas` points at a directory with no schemas. | Drop `--schemas`, or point it at the correct directory. |
| `commit` reports `not a git repository` or `... is not the root of its git repository` | `ADULTING_HOME` is not the top of a git repository. | Run `git init` in the vault root, or set `ADULTING_HOME` to the repository root. |

## Quick reference

| Command | Does |
|---|---|
| `tasks` / `tasks ingest` | Turn `ACTION:` lines into `TASK:` anchors |
| `tasks add` | Add an ACTION to the buffer |
| `tasks done` | Mark a task complete |
| `tasks set-description` | Rewrite a task's text |
| `tasks set-assignee` | Change a task's assignee |
| `tasks set-due` | Set a task's due date |
| `tasks set-scheduled` | Set a task's scheduled date |
| `tasks set-priority` | Set a task's priority |
| `tasks add-depends` | Make a task wait on another |
| `tasks rm-depends` | Remove a task dependency |
| `tasks list` | List pending tasks |
| `tasks next` | Show the top 5 pending tasks |
| `tasks show` | Show one task |
| `notes new` | Create a note and print its path |
| `notes list` | List notes |
| `notes cat` | Print a note |
| `notes last` | Print the newest note's path |
| `notes copy` | Copy a note to a new timestamp |
| `notes delete` | Delete a note permanently |
| `notes pdf` | Render a note to Markdown and PDF |
| `notes minutes` | Render meeting minutes |
| `notes agenda` | Render a meeting agenda |
| `search notes` | Find notes |
| `search logs` | Find daily logs |
| `search activity` | Rank threads by activity |
| `search overview` | Summarise one thread |
| `search stream` | Show every dated record in date order |
| `threads list` | List threads |
| `threads show` | Show a thread |
| `threads new` | Create a thread |
| `people list` | List people |
| `people show` | Show a person |
| `people new` | Create a person |
| `people delete` | Delete a person permanently |
| `hours log` | Record a time entry |
| `hours list` | List time entries |
| `hours report` | Total hours and money |
| `hours show` | Show a time entry |
| `hours edit` | Change a time entry |
| `hours rm` | Delete a time entry permanently |
| `payments log` | Record a payment received |
| `payments list` | List payments |
| `payments statement` | Show billed versus received |
| `payments show` | Show a payment |
| `payments edit` | Change a payment |
| `payments rm` | Delete a payment permanently |
| `stats new` | Declare a stat on a thread |
| `stats list` | List declared stats |
| `stats log` | Add a stat value to the buffer |
| `stats series` | Show a stat over time |
| `buffer add` | Capture a raw `UNKNOWN` entry |
| `buffer add-text` | Capture an observation |
| `buffer add-ref` | Capture a pointer to a vault file |
| `buffer add-action` | Capture an action |
| `buffer list` | Show the buffer with line numbers |
| `buffer rm` | Remove one buffer line |
| `buffer tend` | Regroup and validate the buffer |
| `buffer flush` | File the buffer into logs and ingest tasks |
| `lint` | Validate the vault or given files |
| `commit review` | Show uncommitted changes |
| `commit save` | Stage and commit all changes |
