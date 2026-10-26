# adulting — Operators Manual

## Before you start

All data lives in one directory, the vault. The default is `~/vault`. Set `ADULTING_HOME` to use a different directory:

```
export ADULTING_HOME=<path-to-vault>
```

Every command reads and writes only inside the vault.

The tools need Python 3.11 or newer. Some commands also need these external programs:

| Program | Needed by |
|---|---|
| `git` | `commit` |
| `pandoc` and a LaTeX engine (`xelatex`) | `notes pdf`, `notes minutes`, `notes agenda`, `payments statement --pdf` |

Everything is stored as plain text: Markdown files with YAML frontmatter, plus JSON inside fenced blocks. You can read the files, grep them and back them up with your own tools. Vault-wide settings live in `.adulting/config.yaml`.

## How the pieces fit

Paths are relative to the vault root. `<Kind>` is `Projects`, `Processes` or `Topics`.

| Object | What it is | Where it lives |
|---|---|---|
| Thread | A project, process or topic that organises everything else | `threads/<Kind>/<Name>.md` |
| Note | A typed document: meeting, correspondence, report, research and so on | `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md` |
| Log | One thread's activity for one day, written by `buffer flush` | `threads/<Kind>/<Name>/logs/<YYYY-MM-DD>.md` |
| Time entry | A session of work, billable or not | `threads/<Kind>/<Name>/hours.md` |
| Payment | Money received against a thread | `threads/<Kind>/<Name>/payments.md` |
| Action / task | An `ACTION:` line becomes a `TASK:` anchor, then `DONE:` | Inside the note or log that holds it |
| Person | A contact you track | `people/<Name>.md` |
| Buffer | The staging queue for quick captures | `buffer.md` |

Everything that belongs to a thread lives in the thread's folder, beside the thread file.

Relationships:

- A note names one or more threads in `threads:`. It is filed under the first one.
- A note's `people:` and a task's assignee link to person files. A person is never a thread.
- A task lives in a note or log. There is no other task store.
- A task can depend on other tasks by uuid.
- `notes new`, `hours log` and `payments log` each put a `REF:` pointer in the buffer. After `buffer flush`, the pointer appears in that day's thread log.
- A stat is declared in a thread file. Its values are `STAT:` lines in that thread's logs.
- `payments statement` compares billed hours with payments received.

## Command reference

No command prompts for input or opens an app, so every command is safe to run unattended. Every command and subcommand accepts `--help-json`. That option prints the command's arguments as JSON and exits 0. Every path a command prints is absolute. Wherever a command takes a thread, you can give it as `Kind/Name` (for example `Projects/Northwind`) or as a wikilink.

### tasks

Turns `ACTION:` lines into tracked `TASK:` anchors and edits those anchors in place.

**When to use it**

- You wrote `ACTION:` lines in a note and want them tracked.
- You need to see what to do next, or what is overdue.
- You finished a task, or its due date, priority or assignee changed.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| *(none)* | Same as `ingest`. Writes. | `tasks` |
| `ingest` | Rewrites every `ACTION:` line in notes and logs as a `TASK:` anchor with a new uuid. Writes. | `tasks ingest --dry-run` |
| `add` | Appends an `ACTION:` to the buffer. Same as `buffer add-action`. Writes. | `tasks add Projects/Northwind "(Sam Rivera) Send quarterly report" --due 2026-11-06 --priority H` |
| `done` | Changes `TASK` to `DONE` in the source file and stamps `end:` with today's date. Writes. | `tasks done abcd1234` |
| `set-description` | Rewrites the task text. Writes. | `tasks set-description abcd1234 "Send revised quarterly report"` |
| `set-assignee` | Rewrites the `(Assignee)` prefix. Writes. | `tasks set-assignee abcd1234 "Sam Rivera"` |
| `set-due` | Sets the due date. Writes. | `tasks set-due abcd1234 2026-11-13` |
| `set-scheduled` | Sets the scheduled date. Writes. | `tasks set-scheduled abcd1234 2026-11-10` |
| `set-priority` | Sets priority `H`, `M` or `L`. Writes. | `tasks set-priority abcd1234 H` |
| `add-depends` | Makes the task wait on another task. Writes. | `tasks add-depends abcd1234 ef567890` |
| `rm-depends` | Removes a dependency. Writes. | `tasks rm-depends abcd1234 ef56` |
| `list` | Lists pending tasks, grouped by thread, then sorted by priority, due date and entry date. Read-only. | `tasks list --thread Projects/Northwind` |
| `next` | Shows the top 5 pending tasks by priority, due date and entry date. Read-only. | `tasks next` |
| `show` | Shows one task in detail. Read-only. | `tasks show abcd1234` |

**Options**

Global: `--dry-run` and `--quiet` work with bare `tasks` and with `tasks ingest`.

| Option | Effect |
|---|---|
| `--dry-run` | (bare / `ingest`) Shows what would be ingested. Writes nothing. |
| `--quiet` | (bare / `ingest`) Hides the per-action output. |
| `--due <YYYY-MM-DD>` | (`add`) Due date. |
| `--scheduled <YYYY-MM-DD>` | (`add`) Scheduled date. |
| `--priority <H\|M\|L>` | (`add`) Priority. (`list`) Shows only this priority. |
| `--depends <uuid>` | (`add`) An 8-character task uuid that this task waits on. You can repeat it. |
| `--thread <thread>` | (`list`) Shows only tasks whose source note carries this thread. |
| `--assignee <person>` | (`list`) Shows only tasks assigned to this person. |
| `--overdue` | (`list`) Shows only tasks whose due date is before today. |
| `--json` | (`list`) Prints JSON. |

**Notes**

- `ingest` and every mutating subcommand rewrite your note and log files in place.
- Wherever a subcommand takes a uuid, you can give any unique prefix.
- `tasks add` only writes to the buffer. The task appears after `buffer flush`.
- Files that are not valid UTF-8 are skipped. `lint` reports them.
- The command exits with code 1 when a uuid prefix is empty or matches no task. It also exits 1 if a date is not `YYYY-MM-DD`, a description is empty, an assignee has no `people/<Name>.md`, or a task would depend on itself.

### notes

Creates, lists, prints, copies, deletes and renders notes, addressed by stem.

**When to use it**

- You are starting a meeting, correspondence or research record.
- You need a note's stem or path, or need to print a note.
- You need minutes, an agenda or a PDF for a meeting.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Creates a note and prints its path. Writes. | `notes new --type Meeting --topic "Quarterly review" --thread Projects/Northwind --person "Sam Rivera"` |
| `list` | Lists notes, oldest first, with stem, date, type, threads and topic. | `notes list northwind` |
| `cat` | Prints a note. | `notes cat 2026-09-10-14-30-00` |
| `last` | Prints the path of the newest note. | `notes last` |
| `copy` | Copies a note to a new timestamp and adds ` COPY` to the topic. Writes. | `notes copy 2026-09-10-14-30-00` |
| `delete` | Deletes a note permanently. Needs `-y`. | `notes delete 2026-09-10-14-30-00 -y` |
| `pdf` | Renders the note to Markdown and PDF, with callouts and an action table. | `notes pdf 2026-09-10-14-30-00` |
| `minutes` | Renders meeting minutes: agreements, resolutions and action items. | `notes minutes 2026-09-10-14-30-00` |
| `agenda` | Renders a meeting agenda: the note with its outcome sections emptied. | `notes agenda 2026-09-10-14-30-00` |

**Options**

| Option | Effect |
|---|---|
| `--type <type>` | (`new`, required) One of `Meeting`, `Correspondence`, `Workshop`, `Report`, `Log`, `Research`, `Recipe`. |
| `--topic <text>` | (`new`, required) What the note is about. |
| `--thread <thread>` | (`new`, required) A thread. You can repeat it. The first thread decides where the note is filed. |
| `--person <name>` | (`new`) An attendee. You can repeat it. Meeting and Correspondence notes only. |
| `--counterparty <text>` | (`new`) The other party. Meeting notes only. |
| `--location <text>` | (`new`) Where the meeting was held. Meeting notes only. |
| `--json` | (`list`) Prints JSON. |
| `--out <dir>` | (`pdf`, `minutes`, `agenda`) Output directory. The default is `~/Downloads`. |
| `-y`, `--yes` | (`delete`) Required. Confirms the permanent delete. |

**Notes**

- Every subcommand except `new` first ingests `ACTION:` lines into tasks. This means `list`, `cat` and the other subcommands can rewrite note and log files.
- A stem is a note's filename without `.md`, for example `2026-09-10-14-30-00`. Stems are unique across the vault.
- Renders are written as `<stem>.md` and `<stem>.md.pdf`.
- The command exits with code 1 if the topic is empty, a stem is malformed, or the vault has no notes. It also exits 1 if a meeting-only or person option is used on the wrong note type, or the PDF render fails.

### search

Finds notes and logs and summarises thread activity. Read-only.

**When to use it**

- You need notes or logs for a thread, a date range or some text.
- You want to see which threads were active in a period.
- You want a timeline of everything that happened on a thread or on a day.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `notes` | Finds notes by thread, type, date or text. | `search notes --thread Projects/Northwind --type Meeting` |
| `logs` | Finds daily logs by thread, date or text. | `search logs --text pilot --since 2026-10-01` |
| `activity` | Ranks threads by what happened in a date window. | `search activity --since 2026-10-01 --until 2026-10-31` |
| `overview` | Shows the whole picture of one thread. | `search overview Projects/Northwind` |
| `stream` | Merges every dated record into one timeline. | `search stream --today` |

**Options**

| Option | Effect |
|---|---|
| `--thread <thread>` | (`notes`, `logs`, `activity`, `stream`) Limits results to one thread. |
| `--type <type>` | (`notes`) Note type, for example `Meeting`. Not case-sensitive. |
| `--text <text>` | Literal text, not case-sensitive. `notes` searches topic and body. `logs` searches entry lines. `stream` searches thread and summary. |
| `--since <YYYY-MM-DD>` | On or after this date. |
| `--until <YYYY-MM-DD>` | On or before this date. |
| `--limit <n>` | Maximum results. The default is 20 for `notes` and `logs`, 5 for `overview` and 100 for `stream`. `0` means all. |
| `--kind <list>` | (`stream`) Comma-separated kinds: `note`, `log`, `task`, `done`, `hours`, `payment`, `thread`, `person`, `pending`. The default is all. |
| `--today` | (`stream`) Today only. |
| `--reverse` | (`stream`) Oldest first. The default is newest first. |
| `--json` | Prints JSON. |

**Notes**

- Results are paths and metadata, never note or log bodies. Use `notes cat` or your own reader to see the contents.
- Dates are event dates: a note's frontmatter `timestamp`, not its filename. The filename is used only when the timestamp is missing or malformed.
- `search` does not search the text of time entries.
- The command exits with code 1 when `--kind` contains an unknown kind.

### threads

Creates and shows thread files.

**When to use it**

- You are starting a new project, process or topic.
- You need a thread's exact name or its frontmatter.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists threads. Shows open threads only unless you add `--all`. Read-only. | `threads list north` |
| `show` | Shows one thread file. Read-only. | `threads show Projects/Northwind` |
| `new` | Creates a thread file. Writes. | `threads new --name Northwind --kind project --category professional --currency ZAR --rate 1500` |

**Options**

| Option | Effect |
|---|---|
| `--all` | (`list`) Includes paused and closed threads. |
| `--json` | (`list`, `show`) Prints JSON. |
| `--name <name>` | (`new`, required) The thread name, which becomes the filename. |
| `--kind <project\|process\|topic>` | (`new`, required) Decides which directory the thread goes in. |
| `--category <professional\|personal\|voluntary>` | (`new`, required) Thread category. |
| `--currency <ISO>` | (`new`) The default currency for `hours`. Setting it makes the thread billable. |
| `--rate <n>` | (`new`) The default hourly rate for `hours`. Needs `--currency`. |

**Notes**

- There is no delete command. To remove a thread, delete its file and its folder by hand.
- To close a thread, set `status: closed` and `ended:` in its frontmatter. Nothing moves.
- The command exits with code 1 if the name is empty, contains `/`, starts with `.` or already exists. It also exits 1 if `--rate` is given without `--currency`.

### people

Creates, lists, shows and deletes person files.

**When to use it**

- You want someone as a note attendee or task assignee.
- You need a person's exact name as stored.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists people. Shows open people only unless you add `--all`. Read-only. | `people list sam` |
| `show` | Shows one person file. Read-only. | `people show "Sam Rivera"` |
| `new` | Creates a person file. Writes. | `people new --name "Sam Rivera" --category professional` |
| `delete` | Deletes a person file permanently. Needs `-y`. | `people delete "Sam Rivera" -y` |

**Options**

| Option | Effect |
|---|---|
| `--all` | (`list`) Includes closed people. |
| `--json` | (`list`, `show`) Prints JSON. |
| `--name <name>` | (`new`, required) Full name, which becomes the filename. |
| `--category <professional\|personal\|voluntary>` | (`new`, required) Relationship category. |
| `-y`, `--yes` | (`delete`) Required. Confirms the permanent delete. |

**Notes**

- The command exits with code 1 if the name is empty, contains `/`, starts with `.` or already exists. It also exits 1 if the person is not found, or `delete` is run without `-y`.

### hours

Records time spent on threads, billable or not.

**When to use it**

- You finished a session of client work.
- You want to track unbilled time, such as exercise or admin.
- You need totals for a period, by thread and currency.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Adds a time entry. Writes. | `hours log Projects/Northwind "Pilot data review" -m 90` |
| `list` | Lists entries. Read-only. | `hours list Projects/Northwind --since 2026-10-01` |
| `report` | Totals time by thread and currency, with unbilled time totalled separately. Read-only. | `hours report --since 2026-10-01 --until 2026-10-31` |
| `show` | Shows one entry. Read-only. | `hours show 1a2b3c4d` |
| `edit` | Changes fields of one entry. Writes. | `hours edit 1a2b3c4d -m 120` |
| `rm` | Deletes an entry permanently. Needs `-y`. | `hours rm 1a2b3c4d -y` |

**Options**

| Option | Effect |
|---|---|
| `-m`, `--minutes <n>` | (`log`) Duration in minutes. The default is 60. (`edit`) New duration. The start time stays the same. |
| `-r`, `--rate <n>` | Hourly rate. `0` means unbillable. The entry also needs a currency. |
| `-c`, `--currency <ISO>` | (`log`) Defaults to the thread's currency. With no currency from either, the entry is recorded as unbilled. (`edit`) New currency. |
| `-d`, `--date <YYYY-MM-DD>` | (`log`) The date of the work. The default is today. (`edit`) Moves the entry to this day and keeps its duration. |
| `-t`, `--time <HH:MM>` | (`log`) Start time. The default is now. (`edit`) Moves the start time and keeps the duration. |
| `--description <text>` | (`edit`) New description. |
| `--since`, `--until <YYYY-MM-DD>` | (`list`, `report`) Date window. |
| `--thread <thread>` | (`report`) Shows only this thread. |
| `--json` | (`list`, `report`, `show`) Prints JSON. |
| `-y`, `--yes` | (`rm`) Required. Confirms the permanent delete. |

**Notes**

- Keep the description short. It appears as a line item on the client's statement, and `search` does not index it.
- Rate and currency are stored on each entry when you log it. Changing the thread's defaults later does not change entries you already logged.
- `log` also puts a `REF:` in the buffer, dated on the day of the work.
- The command exits with code 1 if the description is empty, `--minutes` is not positive, or a rate has no currency.

### payments

Records money received and compares it with what you billed.

**When to use it**

- A client paid you.
- You need a statement of what was billed versus what was received, as text or as a PDF.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Records a payment received. Writes. | `payments log Projects/Northwind 12000.00 -a <account> -n October invoice` |
| `list` | Lists payments. Read-only. | `payments list Projects/Northwind` |
| `statement` | Shows billed versus received, by thread and currency. Writes a file only with `--pdf`. | `payments statement --thread Projects/Northwind --as-of 2026-10-31` |
| `show` | Shows one payment. Read-only. | `payments show 9f8e7d6c` |
| `edit` | Changes fields of one payment. Writes. | `payments edit 9f8e7d6c --amount 11500.00` |
| `rm` | Deletes a payment permanently. Needs `-y`. | `payments rm 9f8e7d6c -y` |

**Options**

| Option | Effect |
|---|---|
| `-c`, `--currency <ISO>` | (`log`) Defaults to the thread's currency. (`edit`) New currency. |
| `-d`, `--date <YYYY-MM-DD>` | The date the money arrived. The default is today. |
| `-t`, `--time <HH:MM>` | The time it arrived. The default is now. |
| `-a`, `--account <text>` | The account the money landed in. |
| `-n`, `--note <text>` | A free-text note. It can be several words. |
| `--amount <n>` | (`edit`) New amount. |
| `--thread <thread>` | (`statement`) Shows only this thread. |
| `--since`, `--until <YYYY-MM-DD>` | (`list`, `statement`) Date window. |
| `--as-of <YYYY-MM-DD>` | (`statement`) The statement date, which drives aging. The default is today. |
| `--pdf <path>` | (`statement`) Writes a PDF to this path. Needs `--thread`. |
| `--opening <YYYY-MM-DD>` | (`statement`) The first day the PDF ledger shows. Earlier entries become one balance-brought-forward line. Needs `--pdf`. |
| `--json` | (`list`, `statement`, `show`) Prints JSON. |
| `-y`, `--yes` | (`rm`) Required. Confirms the permanent delete. |

**Notes**

- `log` needs an amount, and the amount must be positive. A refund is not a negative payment.
- Unbilled time does not appear on statements.
- A PDF statement needs `client_name` in the thread's frontmatter.
- `log` also puts a `REF:` in the buffer, dated on the day the money arrived.
- The command exits with code 1 if the amount is missing or not positive. It also exits 1 if `--pdf` has no `--thread`, `--opening` has no `--pdf`, `--opening` is combined with `--since` or `--until`, or `--opening` is after `--as-of`.

### stats

Logs numbers against declared stats and shows how they change over time.

**When to use it**

- You track a count or measurement, such as push-ups, steps, kilometres run or money spent.
- You track whether an event happened. Use an `int` stat and log `1` each time.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Declares a stat in a thread's frontmatter. Writes. | `stats new pushups --thread Topics/Fitness --type int --agg sum` |
| `list` | Lists declared stats. Read-only. | `stats list` |
| `log` | Puts a value in the buffer. Writes. | `stats log pushups 25` |
| `series` | Shows the value per day, week or month. Read-only. | `stats series pushups --by week` |

**Options**

| Option | Effect |
|---|---|
| `--thread <thread>` | (`new`, required) The thread that owns the stat. |
| `--type <int\|decimal>` | (`new`, required) `int` for whole numbers. `decimal` for everything else. |
| `--agg <sum\|last\|max>` | (`new`, required) How a period's values combine: add them, take the latest, or take the largest. |
| `-d`, `--date <YYYY-MM-DD>` | (`log`) The date of the value. The default is today. |
| `-t`, `--time <HH:MM>` | (`log`) The time of the value. The default is now. |
| `--by <day\|week\|month>` | (`series`) Period length. The default is `day`. Weeks start on Monday. |
| `--since`, `--until <YYYY-MM-DD>` | (`series`) Date window. |
| `--json` | (`list`, `series`) Prints JSON. |

**Notes**

- A stat name uses lowercase letters, digits and `-`. It must be unique across the vault.
- There is no rename or delete. To change a declaration, edit the thread's frontmatter. Values already logged are not rewritten.
- `series` reads the logs and the buffer that has not been flushed yet. A period with no values shows `-`, not `0`.
- Exit code 1 means nothing was written. Causes: the name is undeclared or declared twice; the value does not match the stat's type; a date or time is malformed; `new` received a bad name or thread; a logged value is invalid; or `--since` is after `--until`.
- Exit code 2 is a usage error, such as a missing argument or an unknown `--type` or `--agg`.

### buffer

Captures items in a staging queue and files them into thread logs.

**When to use it**

- You want to record something now without writing a note.
- You want to file the day's captures into thread logs.
- You need to remove or fix a captured line.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `add` | Appends an `UNKNOWN` raw capture. It blocks `flush` until you convert it. Writes. | `buffer add "ask Sam about pilot dates"` |
| `add-text` | Appends a `TEXT:` observation. Writes. | `buffer add-text Projects/Northwind "Pilot slipped a week"` |
| `add-ref` | Appends a `REF:` pointer to another vault file. Writes. | `buffer add-ref Projects/Northwind "people/Sam Rivera" "Intro call"` |
| `add-action` | Appends an `ACTION:`. Writes. | `buffer add-action Projects/Northwind "(Sam Rivera) Confirm pilot dates" --due 2026-11-06` |
| `list` | Shows the buffer with line numbers. Read-only. | `buffer list northwind` |
| `rm` | Removes one line by its number. Writes. | `buffer rm 3` |
| `tend` | Regroups entries by thread and date, and validates them. Safe to repeat. Writes. | `buffer tend` |
| `flush` | Tends, writes each thread's logs, clears the buffer and ingests the flushed actions into tasks. Writes. | `buffer flush` |

**Options**

Global: `--quiet` goes before the subcommand and hides info output, for example `buffer --quiet flush`.

| Option | Effect |
|---|---|
| `--date <YYYY-MM-DD>` | (`add`, `add-text`, `add-ref`, `add-action`) Files the entry under this day. Use the day the thing happened. |
| `--due <YYYY-MM-DD>` | (`add-action`) Due date. |
| `--scheduled <YYYY-MM-DD>` | (`add-action`) Scheduled date. |
| `--priority <H\|M\|L>` | (`add-action`) Priority. |
| `--depends <uuid>` | (`add-action`) An 8-character task uuid. You can repeat it. |
| `--json` | (`list`) Prints JSON. |

**Notes**

- Change `buffer.md` only through these commands. Do not edit it by hand.
- A `REF:` target can be one of:
  - `<Kind>/<Name>`
  - `<Kind>/<Name>/hours`
  - `<Kind>/<Name>/payments`
  - `<Kind>/<Name>/logs/<date>`
  - a note stem
  - `people/<Name>`
- `flush` already ingests tasks, so you do not need to run `tasks` afterwards. It reports actions in these ways:
  - `already a task`: the action matches an open task and is skipped.
  - `already buffered`: the action repeats another buffer line.
  - `due updated`: the action differs from an open task only by due date. That task's due date moves.
  - `ambiguous`: the action matches several open tasks. Nothing changes.
- The command exits with code 1 if a line number is not an integer, is out of range, or points to an empty line.

### lint

Checks vault files against the schemas in [Data formats](#data-formats). Read-only.

**When to use it**

- Before you commit.
- After you edit vault files by hand.
- When a command skipped a file and you want to know why.

**Usage**

```
lint [<path> ...]
```

| Argument | Meaning |
|---|---|
| `<path>` | Files to check. With no paths, `lint` checks the whole vault. |

**Options**

| Option | Effect |
|---|---|
| `--schemas <dir>` | Uses a different schemas directory. |
| `--quiet` | Prints nothing. The exit code is the only result. |

**Notes**

- Each violation prints as `<path>:<line>: <message>`, with an absolute path.
- Exit code 0 means no violations. Exit code 1 means there are violations. Exit code 2 means no schemas could be loaded.

### commit

Reviews vault changes and commits them to git.

**When to use it**

- At the end of a work session.
- Before you make large changes, so you have a restore point.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `review` | Shows everything that changed since the last commit. Read-only. | `commit review` |
| `save` | Stages every change in the vault and commits it. Writes. | `commit save --message "Northwind: October hours and payment"` |

**Options**

| Option | Effect |
|---|---|
| `--max-file-lines <n>` | (`review`) Maximum diff lines shown per file. The default is 150. |
| `--max-lines <n>` | (`review`) Maximum output lines in total. The default is 3000. |
| `--message <text>` | (`save`, required) The commit subject, on a single line. |
| `--body <text>` | (`save`) The commit body. It can span several lines. |
| `--dry-run` | (`save`) Reports what would be staged and committed. Changes nothing. |

**Notes**

- `save` only ever adds a commit. It never amends, rebases, resets, checks out or pushes.
- The vault directory must be the root of a git repository.
- The command exits with code 1 if the message is empty or spans several lines, the vault is not a git repository, the vault is not the repository root, or a git command fails.

## Everyday procedures

### 1. Set up a new billable project

1. `threads new --name Northwind --kind project --category professional --currency ZAR --rate 1500` creates the thread with billing defaults.
2. `people new --name "Sam Rivera" --category professional` adds your client contact.
3. Open `threads/Projects/Northwind.md` and add `client_name:` to the frontmatter. PDF statements need it.
4. `threads show Projects/Northwind` confirms the frontmatter.
5. `lint threads/Projects/Northwind.md` checks the thread file.

### 2. Capture a meeting and turn its actions into tracked tasks

1. `notes new --type Meeting --topic "Quarterly review" --thread Projects/Northwind --person "Sam Rivera" --counterparty Northwind` creates the note and prints its path.
2. Open that path and write one line per action, for example `ACTION: (Sam Rivera) Send quarterly report`.
3. `tasks --dry-run` shows which actions will be ingested.
4. `tasks` turns each `ACTION:` line into a `TASK:` anchor.
5. `tasks list --thread Projects/Northwind` shows the new tasks and their uuids.
6. `notes minutes <stem>` renders the minutes to `~/Downloads`.

### 3. Quick-capture through the day, then file it

1. `buffer add "ask Sam about pilot dates"` captures a line when you have no time to choose a thread.
2. `buffer add-text Projects/Northwind "Pilot slipped a week"` captures an observation on a thread.
3. `tasks add Projects/Northwind "(Sam Rivera) Confirm pilot dates" --due 2026-11-06` captures an action.
4. `buffer list` shows every capture with its line number.
5. `buffer rm <line-number>` removes the `UNKNOWN` line. Re-add it with `buffer add-text` or `tasks add`.
6. `buffer tend` validates the buffer. Fix anything it reports.
7. `buffer flush` files everything into the thread logs and creates the tasks.

### 4. Work the task list

1. `tasks next` shows the top 5 tasks.
2. `tasks list --overdue` shows tasks that are past their due date.
3. `tasks show <uuid>` shows one task in full.
4. `tasks set-due <uuid> 2026-11-13` moves a deadline.
5. `tasks set-priority <uuid> H` raises a task's priority.
6. `tasks done <uuid>` marks a task complete.

### 5. Log a session of work

1. `hours log Projects/Northwind "Pilot data review" -m 90` records 90 minutes at the thread's rate.
2. `buffer add-text Projects/Northwind "Join logic on multi-repo commits still unresolved"` records what happened, so `search` can find it.
3. `hours list Projects/Northwind --since 2026-10-26` checks the entry and shows its id.
4. `hours edit <id> -m 120` corrects the duration if needed.
5. `buffer flush` files the log line and the time-entry `REF:` into today's log.

### 6. Bill a client for a month's work

1. `hours report --thread Projects/Northwind --since 2026-10-01 --until 2026-10-31` totals the month.
2. `hours list Projects/Northwind --since 2026-10-01 --until 2026-10-31` shows the line items.
3. `payments statement --thread Projects/Northwind --as-of 2026-10-31` shows billed versus received.
4. `payments statement --thread Projects/Northwind --as-of 2026-10-31 --opening 2026-10-01 --pdf ~/Downloads/Northwind-statement.pdf` writes the PDF statement.

### 7. Record a payment

1. `payments log Projects/Northwind 12000.00 -d 2026-11-03 -a <account> -n October invoice` records the receipt.
2. `payments list Projects/Northwind` confirms it and shows its id.
3. `payments statement --thread Projects/Northwind` shows the new balance.
4. `buffer flush` files the payment's `REF:` into that day's log.

### 8. Check the vault and commit it

1. `buffer flush` files any pending captures.
2. `lint` checks the whole vault. Fix every violation it reports.
3. `commit review` shows what changed since the last commit.
4. `commit save --message "<summary>" --dry-run` shows what would be committed.
5. `commit save --message "<summary>" --body "<detail>"` commits the changes.

## Data formats

`lint` enforces every schema below. Paths are relative to the vault root.

### `hours_file`

The time entries for one thread. Path: `threads/<Kind>/<Name>/hours.md`. The body holds exactly one `simple-time-tracker` fenced block, containing JSON `{"entries": [...]}`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to this file's own thread. It must resolve. |
| `currency` | no | Three-letter ISO code. Omitted for unbilled threads. |
| `entries[].name` | yes | Description of the work, used as an invoice line item. |
| `entries[].startTime` | yes | ISO 8601 UTC, `YYYY-MM-DDTHH:MM:SS.mmmZ`. |
| `entries[].endTime` | yes | Same form. Must not be earlier than `startTime`. Duration is `endTime` minus `startTime`. |
| `entries[].id` | yes | 8 hex characters, unique across all hours and payments. |
| `entries[].rate` | yes | Hourly charge as an integer. `0` means unbillable. |
| `entries[].currency` | no | ISO 4217 code. Absent or null means unbilled. |

### `log`

One thread's activity for one day, written by `buffer flush`. Path: `threads/<Kind>/<Name>/logs/<YYYY-MM-DD>.md`. Body lines are `TEXT:`, `REF:`, `ACTION:`, `TASK:`, `DONE:` or `STAT:`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to this log's own thread. |
| `date` | yes | `YYYY-MM-DD`. |
| `type` | yes | Always `Log`. |

### `note_correspondence`

A record of emails, messages or letters. Path: `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md`, under the first thread listed.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about. |
| `type` | yes | `Correspondence`. |
| `threads` | yes | List of thread wikilinks. Each must resolve. The first one decides where the note is filed. |
| `timestamp` | yes | When the exchange happened, `YYYY-MM-DD-HH-MM-SS`. |
| `people` | no | Participants: `[[people/<Name>]]` links, or plain names for people you do not track. |

Body markers: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:`, `!:` (callout).

### `note_meeting`

A record of a meeting. Path: `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md`, under the first thread listed.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the meeting was about. |
| `type` | yes | `Meeting`. |
| `threads` | yes | List of thread wikilinks. Each must resolve. The first one decides where the note is filed. |
| `timestamp` | yes | When the meeting happened, `YYYY-MM-DD-HH-MM-SS`. |
| `counterparty` | no | The other party. |
| `location` | no | Where it was held. |
| `people` | no | Attendees: `[[people/<Name>]]` links, or plain names for people you do not track. |

Body markers: `ACTION:`, `TASK:`, `AGREED:` and `RESOLVED:` (shown in minutes), `!:` (callout, shown in the PDF).

### `note_simple`

A Workshop, Report, Log, Research or Recipe note. Path: `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md`, under the first thread listed.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about. |
| `type` | yes | `Workshop`, `Report`, `Log`, `Research` or `Recipe`. |
| `threads` | yes | List of thread wikilinks. Each must resolve. The first one decides where the note is filed. |
| `timestamp` | yes | When the event happened, `YYYY-MM-DD-HH-MM-SS`. |
| `people` | no | `[[people/<Name>]]` links or plain names. |

### `payments_file`

The money received against one thread. Path: `threads/<Kind>/<Name>/payments.md`. The body holds exactly one `adulting-payments` fenced block, containing JSON `{"payments": [...]}`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to this file's own thread. It must resolve. |
| `currency` | yes | Three-letter ISO code. |
| `payments[].id` | yes | 8 hex characters, unique across all hours and payments. |
| `payments[].received` | yes | When the money landed, ISO 8601 UTC `YYYY-MM-DDTHH:MM:SS.mmmZ`. |
| `payments[].amount` | yes | Greater than 0. |
| `payments[].currency` | yes | ISO 4217 code. |
| `payments[].account` | no | The account the money landed in. |
| `payments[].note` | no | Free text. |

### `person`

Someone you track. Path: `people/<Name>.md`. The body is free-form.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | `YYYY-MM-DD`. |
| `ended` | no | `YYYY-MM-DD`. Required when `status` is `closed`. |
| `cadences` | no | A list of `{key, frequency, description}`, the same as on threads. |

### `stat_line`

One value of a declared stat. It is a line in a log file, `threads/<Kind>/<Name>/logs/<YYYY-MM-DD>.md`, shaped like `STAT: pushups 25 <!--2026-10-07T07:42:10-->`.

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | A stat declared on this log's own thread. |
| `value` | yes | A number. It must be a whole number if the stat type is `int`. |
| `ts` | yes | Local time, `YYYY-MM-DDTHH:MM:SS`. Its date must match the log's date. |

`STAT:` lines belong only in logs.

### `task_anchor`

One `TASK:` or `DONE:` line in a note or log. It is the only record of a task. Change it only with `tasks` subcommands. Example: `TASK: [#H] (Sam Rivera) Send quarterly report <!--abcd1234 entry:2026-05-27 due:2026-05-29-->`.

| Field | Required | Meaning |
|---|---|---|
| `kind` | yes | `TASK` or `DONE`. |
| `priority` | no | `H`, `M` or `L`, shown as `[#X]`. |
| `assignee` | no | A person. Must resolve to `people/<Name>.md`. |
| `body` | yes | The task text. |
| `uuid` | yes | 8 hex characters, unique across the vault. |
| `entry` | yes | Date the task was ingested. |
| `end` | no | Completion date. Required for `DONE`. Must not be earlier than `entry`. |
| `due` | no | Due date. |
| `scheduled` | no | Scheduled date. |
| `depends` | no | Comma-separated uuids of existing tasks. Dependencies must not form a cycle. |

### `thread`

A project, process or topic. Path: `threads/<Kind>/<Name>.md`.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `kind` | yes | `project`, `process` or `topic`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | `YYYY-MM-DD`. |
| `ended` | no | `YYYY-MM-DD`. Required when `status` is `closed`. |
| `cadences` | no | A list of `{key, frequency, description}`. `frequency` is in days, and `key` is unique within the thread. |
| `stats` | no | A list of `{name, type, agg}`, written by `stats new`. |
| `currency` | no | Default currency for `hours`. Setting it makes the thread billable. |
| `rate` | no | Default hourly rate (an integer). |
| `client_name` | no | The billed party. Required for a PDF statement. |
| `client_address` | no | Address lines separated by `\|`, for example `Unit 301\|2 Park Road\|Cape Town`. |
| `client_vat` | no | The client's VAT number. |
| `client_email` | no | The client's email address. |

### `thread_entry`

A dated bullet at the top level of a thread file's body, such as `- 2024-05-17 — Made progress.`. Path: inside `threads/<Kind>/<Name>.md`. Indented sub-bullets are not checked.

| Field | Required | Meaning |
|---|---|---|
| `date` | yes | `YYYY-MM-DD`. |
| `text` | yes | The entry text. It must not be empty. |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `lint` reports `file is not valid UTF-8`; other commands silently miss a file | Commands skip files they cannot read as UTF-8 | Re-save the file as UTF-8, or remove it. |
| `buffer flush` will not run; `tend` reports an `UNKNOWN` entry | `buffer add` entries are invalid by design | Run `buffer rm <line-number>`, then re-add the entry with `buffer add-text`, `buffer add-ref` or `tasks add`. |
| `buffer flush` reports `ambiguous` | The action matches several open tasks | Change the existing tasks with `tasks set-*` instead. |
| `--rate needs a currency` from `hours` or `threads new` | A rate needs a currency | Add `--currency <ISO>`, or set `currency` on the thread. |
| `person ... does not resolve to people/...` | The assignee has no person file | Run `people new --name "<Name>" --category <category>`. |
| `no task found with uuid prefix` | The prefix matches no task | Get the uuid from `tasks list`. |
| `refusing to delete ... without -y` | The delete was not confirmed | Add `-y` to `people delete`, `notes delete`, `hours rm` or `payments rm`. |
| `--pdf needs --thread` or `--opening needs --pdf` | A statement PDF covers one client, and only the PDF has an opening ledger | Add `--thread <thread>` or `--pdf <path>`. |
| `PDF render failed` | `pandoc` or `xelatex` is missing or failed | Install `pandoc` and a LaTeX engine. |
| `stats log` exits 1 | The stat is undeclared, or the value does not match its type | Check `stats list`. Declare the stat with `stats new`. Use a whole number for `int` stats. |
| `not a git repository` or `is not the root of its git repository` from `commit` | The vault is not the root of a git repository | Make `ADULTING_HOME` the root of its own git repository. |
| `lint` exits 2 | No schemas were loaded | Point `--schemas` at a valid schemas directory. |

## Quick reference

| Command | Does |
|---|---|
| `tasks` | Turns `ACTION:` lines into `TASK:` anchors. |
| `tasks ingest` | Same as bare `tasks`. |
| `tasks add` | Puts an action in the buffer. |
| `tasks done` | Marks a task done. |
| `tasks set-description` | Rewrites a task's text. |
| `tasks set-assignee` | Changes a task's assignee. |
| `tasks set-due` | Sets a due date. |
| `tasks set-scheduled` | Sets a scheduled date. |
| `tasks set-priority` | Sets priority H, M or L. |
| `tasks add-depends` | Adds a dependency. |
| `tasks rm-depends` | Removes a dependency. |
| `tasks list` | Lists pending tasks. |
| `tasks next` | Shows the top 5 pending tasks. |
| `tasks show` | Shows one task. |
| `notes new` | Creates a note and prints its path. |
| `notes list` | Lists notes. |
| `notes cat` | Prints a note. |
| `notes last` | Prints the newest note's path. |
| `notes copy` | Copies a note to a new timestamp. |
| `notes delete` | Deletes a note permanently. |
| `notes pdf` | Renders a note to Markdown and PDF. |
| `notes minutes` | Renders meeting minutes. |
| `notes agenda` | Renders a meeting agenda. |
| `search notes` | Finds notes. |
| `search logs` | Finds daily logs. |
| `search activity` | Ranks threads by activity. |
| `search overview` | Summarises one thread. |
| `search stream` | Shows a merged timeline of records. |
| `threads list` | Lists threads. |
| `threads show` | Shows a thread file. |
| `threads new` | Creates a thread. |
| `people list` | Lists people. |
| `people show` | Shows a person file. |
| `people new` | Creates a person. |
| `people delete` | Deletes a person permanently. |
| `hours log` | Records a time entry. |
| `hours list` | Lists time entries. |
| `hours report` | Totals time by thread and currency. |
| `hours show` | Shows one time entry. |
| `hours edit` | Changes a time entry. |
| `hours rm` | Deletes a time entry. |
| `payments log` | Records a payment received. |
| `payments list` | Lists payments. |
| `payments statement` | Shows billed versus received; optionally writes a PDF. |
| `payments show` | Shows one payment. |
| `payments edit` | Changes a payment. |
| `payments rm` | Deletes a payment. |
| `stats new` | Declares a stat on a thread. |
| `stats list` | Lists declared stats. |
| `stats log` | Puts a stat value in the buffer. |
| `stats series` | Shows a stat's values over time. |
| `buffer add` | Captures a raw `UNKNOWN` line. |
| `buffer add-text` | Captures an observation. |
| `buffer add-ref` | Captures a pointer to a vault file. |
| `buffer add-action` | Captures an action. |
| `buffer list` | Shows the buffer with line numbers. |
| `buffer rm` | Removes a buffer line. |
| `buffer tend` | Regroups and validates the buffer. |
| `buffer flush` | Files the buffer into logs and ingests tasks. |
| `lint` | Checks vault files against the schemas. |
| `commit review` | Shows uncommitted changes. |
| `commit save` | Stages and commits all changes. |
