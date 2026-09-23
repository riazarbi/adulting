# adulting — Operators Manual

## Before you start

All data lives in one vault directory. The default is `~/vault/`. Set `ADULTING_HOME` to use a different directory. Every tool reads and writes there.

You need these external programs:

| Program | Needed by |
|---|---|
| Python 3.11 or newer | every tool |
| `git` | `commit` |
| `pandoc` and a LaTeX engine (`xelatex`) | `notes pdf`, `notes minutes`, `notes agenda` |

Everything is plain text on disk: Markdown files with YAML frontmatter, and JSON inside fenced blocks. You can read the files, grep them, and back them up with any tool you like. There is no database and no backend.

## How the pieces fit

| Object | What it is | Where it lives |
|---|---|---|
| Thread | A project, process or topic that organises everything else. | `threads/Projects/`, `threads/Processes/`, `threads/Topics/` |
| Note | A typed document, such as a meeting record, correspondence or report. | `notes/` |
| Person | A contact you track. | `people/` |
| Log | One file per thread per day, written by `buffer flush`. | `logs/<Kind>/<Name>/<YYYY-MM-DD>.md` |
| Buffer | The capture inbox. Its entries become log lines. | `buffer.md` |
| Action / task | An `ACTION:` line in a note or log. After ingest it becomes a `TASK:` anchor, and later a `DONE:` anchor. | inside `notes/` and `logs/` files |
| Time entry | A session of work, billable or not. | `hours/<Kind>/<Thread>.md` |
| Payment | Money received. | `payments/<Kind>/<Thread>.md` |

Relationships:

- A note belongs to one or more threads. It can list people.
- A log belongs to exactly one thread and one day.
- A task lives inside the note or log that contains it. That file is the only store for the task.
- A task's assignee must be a person. A task can depend on other tasks.
- Time entries and payments are filed per thread, in one file per thread.
- `notes new`, `hours log` and `payments log` each add a `REF:` to the buffer. After `buffer flush`, the thread's daily log points to the record.
- A person is never a thread.

## Command reference

No command prompts or opens an app, so you can script any of them. Commands that delete need `-y`.

### tasks

Turns `ACTION:` lines into tracked `TASK:` anchors, and edits those anchors.

**When to use it**
- You wrote `ACTION:` lines in a note and want them tracked.
- You need to decide what to work on next, or close a task.
- You need to change a task's due date, priority, assignee or dependencies.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| *(none)* | Same as `ingest`. | `tasks` |
| `ingest` | Rewrites every `ACTION:` line in `notes/` and `logs/` as a `TASK:` anchor. | `tasks ingest --dry-run` |
| `add` | Adds an `ACTION:` entry to the buffer. Same as `buffer add-action`. | `tasks add Projects/<name> "(<Person>) <description>" --due <YYYY-MM-DD>` |
| `done` | Changes `TASK:` to `DONE:` and stamps today as the end date. | `tasks done <uuid>` |
| `set-description` | Replaces the task body. | `tasks set-description <uuid> "<text>"` |
| `set-assignee` | Replaces the `(Assignee)` prefix. | `tasks set-assignee <uuid> "<Person>"` |
| `set-due` | Sets the due date. | `tasks set-due <uuid> <YYYY-MM-DD>` |
| `set-scheduled` | Sets the scheduled date. | `tasks set-scheduled <uuid> <YYYY-MM-DD>` |
| `set-priority` | Sets priority `H`, `M` or `L`. | `tasks set-priority <uuid> H` |
| `add-depends` | Makes this task wait on another task. | `tasks add-depends <uuid> <dep-uuid>` |
| `rm-depends` | Removes a dependency. | `tasks rm-depends <uuid> <dep-uuid>` |
| `list` | Lists pending tasks grouped by thread. | `tasks list --overdue` |
| `next` | Shows the top 5 pending tasks by priority, then due date, then entry date. | `tasks next` |
| `show` | Shows one task in detail. | `tasks show <uuid>` |

**Options**

Top-level options apply to bare `tasks` and to `tasks ingest`:

| Option | Effect |
|---|---|
| `--dry-run` | Shows what would be ingested. Writes nothing. |
| `--quiet` | Hides the output for each action. |

| Option (subcommand) | Effect |
|---|---|
| `--due <YYYY-MM-DD>` (`add`) | Due date. |
| `--scheduled <YYYY-MM-DD>` (`add`) | Scheduled date. |
| `--priority H\|M\|L` (`add`) | Priority. |
| `--depends <uuid>` (`add`) | Task this one waits on. You can repeat it. |
| `--priority H\|M\|L` (`list`) | Shows only tasks with this priority. |
| `--thread <Kind/Name>` (`list`) | Shows only tasks whose source note carries this thread. |
| `--assignee <Person>` (`list`) | Shows only tasks assigned to this person. |
| `--overdue` (`list`) | Shows only tasks whose due date is before today. |
| `--json` (`list`) | Prints JSON. |

**Notes**
- Ingest and every `set-*`, `done`, `add-depends` and `rm-depends` command rewrite source note and log files in place. Do not edit anchors by hand.
- `tasks add` only writes to the buffer. The `TASK:` anchor appears after `buffer flush` and an ingest.
- Wherever a command takes `<uuid>`, any unique prefix works. Get uuids from `tasks list`.
- Exit code `1` means one of these: the task was not found, the date was malformed, the description was empty, the assignee has no file in `people/`, or a task was set to depend on itself.

### notes

Creates, lists, prints, copies, deletes and renders notes. You refer to a note by its stem.

**When to use it**
- You are starting a meeting, correspondence or report record.
- You need a note's stem, path or content.
- You need a PDF, minutes or an agenda from a note.

A stem is the filename without `.md`, for example `2026-09-10-14-30-00`.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Creates a note and prints its path. | `notes new --type Meeting --topic "<topic>" --thread Projects/<name>` |
| `list` | Lists notes oldest first: stem, date, type, threads and topic. | `notes list "<filter>"` |
| `cat` | Prints a note. | `notes cat <stem>` |
| `last` | Prints the path of the newest note. | `notes last` |
| `copy` | Copies a note to a new timestamp and appends ` COPY` to its topic. | `notes copy <stem>` |
| `delete` | Deletes a note permanently. | `notes delete <stem> -y` |
| `pdf` | Renders the note to Markdown and PDF, with callouts and an action table. | `notes pdf <stem>` |
| `minutes` | Renders minutes: agreements, resolutions and action items. | `notes minutes <stem>` |
| `agenda` | Renders an agenda: the note with its outcome sections emptied. | `notes agenda <stem>` |

**Options**

| Option | Effect |
|---|---|
| `--type <T>` (`new`, required) | One of `Meeting`, `Correspondence`, `Workshop`, `Report`, `Log`, `Research`, `Recipe`. |
| `--topic <text>` (`new`, required) | What the note is about. |
| `--thread <Kind/Name>` (`new`, required) | Thread the note belongs to. You can repeat it. |
| `--person <name>` (`new`) | Attendee, for `Meeting` and `Correspondence` notes only. You can repeat it. It becomes a link when `people/<name>.md` exists. |
| `--counterparty <text>` (`new`) | The other party, for `Meeting` notes only. |
| `--location <text>` (`new`) | Where the meeting was held, for `Meeting` notes only. |
| `-y`, `--yes` (`delete`) | Required. Confirms the delete. |
| `--out <dir>` (`pdf`, `minutes`, `agenda`) | Output directory. The default is `~/Downloads`. |
| `--json` (`list`) | Prints JSON. |

**Notes**
- Every subcommand except `new` runs a task ingest first. This can rewrite `ACTION:` lines in `notes/` and `logs/`. If an action cannot be ingested, the command still runs.
- Renders write `<stem>.md` and `<stem>.md.pdf`, then print both paths.
- Exit code `1` means one of these: a bad or unknown stem, an empty topic, a type-only option used on the wrong type, or a failed PDF render.

### search

Finds notes and logs, and summarises activity on threads. It prints pointers, not file bodies.

**When to use it**
- You need every note or log on a thread, or in a date range.
- You need to know which threads were active in a period.
- You need one chronology of everything that happened, for example today.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `notes` | Finds notes by thread, type, date or text. | `search notes --thread Projects/<name> --type Meeting` |
| `logs` | Finds daily logs by thread, date or text. | `search logs --text "<words>" --since <YYYY-MM-DD>` |
| `activity` | Ranks threads by what happened in a date window. | `search activity --since <YYYY-MM-DD>` |
| `overview` | Shows the whole picture of one thread. | `search overview Projects/<name>` |
| `stream` | Merges every dated record into one chronology. | `search stream --today` |

**Options**

Global: every subcommand takes `--since <YYYY-MM-DD>`, `--until <YYYY-MM-DD>` and `--json`.

| Option | Effect |
|---|---|
| `--thread <Kind/Name>` | Limits results to one thread (`notes`, `logs`, `activity`, `stream`). |
| `--type <T>` (`notes`) | Note type. Case does not matter. |
| `--text <text>` | Case-insensitive literal match. In `notes` it searches topic and body. In `logs` it searches entry lines. In `stream` it searches thread and summary. |
| `--limit <N>` | Maximum results. `0` means all. Defaults: 20 for `notes` and `logs`, 5 for `overview`, 100 for `stream`. |
| `--kind <list>` (`stream`) | Comma-separated. Any of `note`, `log`, `task`, `done`, `hours`, `payment`, `thread`, `person`, `pending`. The default is all. |
| `--today` (`stream`) | Today only. |
| `--reverse` (`stream`) | Oldest first. The default is newest first. |

**Notes**
- Paths are absolute, resolved against `ADULTING_HOME`.
- Dates are event dates: a note's frontmatter `timestamp`, not its filename.
- `search` does not index the text of time entries.
- Exit code `1` from `stream` means `--kind` included an unknown kind.

### threads

Creates, lists, shows and deletes thread files.

**When to use it**
- You are starting a new project, process or topic.
- You need a thread's exact `Kind/Name`, or its settings.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists open threads. An optional query ranks them by similarity. | `threads list --all "<query>"` |
| `show` | Shows one thread file. | `threads show Projects/<name>` |
| `new` | Creates a thread file. | `threads new --name "<name>" --kind project --category professional` |
| `delete` | Deletes a thread file permanently. | `threads delete Projects/<name> -y` |

**Options**

| Option | Effect |
|---|---|
| `--name <name>` (`new`, required) | Thread name. It becomes the filename. |
| `--kind project\|process\|topic` (`new`, required) | Directory: `Projects/`, `Processes/` or `Topics/`. |
| `--category professional\|personal\|voluntary` (`new`, required) | Thread category. |
| `--currency <ISO>` (`new`) | Default currency for `hours`. Setting it makes the thread billable. |
| `--rate <N>` (`new`) | Default hourly rate for `hours`. Needs `--currency`. |
| `--all` (`list`) | Includes paused and closed threads. |
| `-y`, `--yes` (`delete`) | Required. Confirms the delete. |
| `--json` (`list`, `show`) | Prints JSON. |

**Notes**
- A name cannot contain `/` or start with `.`.
- Exit code `1` means one of these: an empty name, a bad name, a file that already exists, `--rate` without `--currency`, or a delete without `-y`.

### people

Creates, lists, shows and deletes person files.

**When to use it**
- You need someone as a task assignee or as a linked attendee.
- You need to check that a person's name resolves.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists open people. An optional query ranks them by similarity. | `people list "<query>"` |
| `show` | Shows one person file. | `people show "<Full Name>"` |
| `new` | Creates a person file. | `people new --name "<Full Name>" --category professional` |
| `delete` | Deletes a person file permanently. | `people delete "<Full Name>" -y` |

**Options**

| Option | Effect |
|---|---|
| `--name <Full Name>` (`new`, required) | Full name. It becomes the filename. |
| `--category professional\|personal\|voluntary` (`new`, required) | Relationship category. |
| `--all` (`list`) | Includes closed people. |
| `-y`, `--yes` (`delete`) | Required. Confirms the delete. |
| `--json` (`list`, `show`) | Prints JSON. |

**Notes**
- Exit code `1` means one of these: an empty or bad name, a file that already exists, a person not found, or a delete without `-y`.

### hours

Records time spent on a thread, billable or not.

**When to use it**
- You finished a session of work, for a client or for yourself.
- You need totals for a thread or a period.
- You need to correct or remove an entry.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Adds an entry. | `hours log Projects/<name> -m 90 <description>` |
| `list` | Lists entries, optionally for one thread. | `hours list Projects/<name> --since <YYYY-MM-DD>` |
| `report` | Totals by thread and currency. Unbilled time gets its own row. | `hours report --since <YYYY-MM-DD> --until <YYYY-MM-DD>` |
| `show` | Shows one entry. | `hours show <id>` |
| `edit` | Changes a field of an entry. | `hours edit <id> --description <new description>` |
| `rm` | Deletes an entry. | `hours rm <id> -y` |

**Options**

| Option | Effect |
|---|---|
| `-m`, `--minutes <N>` | Duration in minutes. The default for `log` is 60. In `edit`, the start time stays fixed. |
| `-r`, `--rate <N>` | Hourly rate. `0` means unbillable. Needs a currency. |
| `-c`, `--currency <ISO>` | Currency. `log` defaults to the thread's currency. With no currency from either source, the entry is unbilled. |
| `-d`, `--date <YYYY-MM-DD>` | Day of the work. The default for `log` is today. In `edit`, the duration is kept. |
| `-t`, `--time <HH:MM>` | Start time. The default for `log` is now. In `edit`, the duration is kept. |
| `--description <text>` (`edit`) | New description. |
| `--thread <Kind/Name>` (`report`) | Limits the report to one thread. |
| `--since`, `--until <YYYY-MM-DD>` (`list`, `report`) | Date window. |
| `-y`, `--yes` (`rm`) | Required. Confirms the delete. |
| `--json` (`list`, `report`, `show`) | Prints JSON. |

**Notes**
- The description is an invoice line item. Keep it short. Put detail in a log line with `buffer add-text`.
- Each `log` adds a `REF:` to the buffer, filed under the day of the work.
- Exit code `1` means one of these: an empty description, minutes that are not positive, or a rate with no currency.

### payments

Records money received against a thread and produces statements.

**When to use it**
- A client paid you.
- You need billed-versus-received figures, or a statement PDF for a client.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Records a receipt. | `payments log Projects/<name> <amount> -a "<account>"` |
| `list` | Lists payments, optionally for one thread. | `payments list Projects/<name>` |
| `statement` | Shows billed versus received, by thread and currency. | `payments statement --thread Projects/<name> --pdf <path>.pdf` |
| `show` | Shows one payment. | `payments show <id>` |
| `edit` | Changes a field of a payment. | `payments edit <id> --amount <amount>` |
| `rm` | Deletes a payment. | `payments rm <id> -y` |

**Options**

| Option | Effect |
|---|---|
| `-c`, `--currency <ISO>` | Currency. `log` defaults to the thread's currency. |
| `-d`, `--date <YYYY-MM-DD>` | Date received. The default for `log` is today. |
| `-t`, `--time <HH:MM>` | Time received. The default for `log` is now. |
| `-a`, `--account <text>` | Account the money landed in. |
| `-n`, `--note <text>` | Free-text note. |
| `--amount <amount>` (`edit`) | New amount. |
| `--thread <Kind/Name>` (`statement`) | Limits the statement to one thread. |
| `--as-of <YYYY-MM-DD>` (`statement`) | Statement date. It drives aging. The default is today. |
| `--pdf <path>` (`statement`) | Writes a PDF to this path. Needs `--thread`. |
| `--since`, `--until <YYYY-MM-DD>` (`list`, `statement`) | Date window. |
| `-y`, `--yes` (`rm`) | Required. Confirms the delete. |
| `--json` (`list`, `statement`, `show`) | Prints JSON. |

**Notes**
- Amounts must be positive. A refund is not a negative payment.
- Statements ignore unbilled time.
- A statement PDF needs `client_name` in the thread's frontmatter.
- Each `log` adds a `REF:` to the buffer, filed under the date received.
- Exit code `1` means one of these: a missing, invalid or non-positive amount, `--pdf` without `--thread`, or nothing to state for that thread and date.

### buffer

Captures entries into `buffer.md`, checks them, and flushes them into the daily logs.

**When to use it**
- You want to record an observation, reference or action without writing a note.
- You captured something in a hurry and now need to file it.
- It is the end of the day and the buffer needs to go into the logs.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `add` | Adds an `UNKNOWN:` quick-capture with no thread. | `buffer add "<text>"` |
| `add-text` | Adds a `TEXT:` observation. | `buffer add-text Projects/<name> "<text>"` |
| `add-ref` | Adds a `REF:` link to another vault file. | `buffer add-ref Projects/<name> notes/<stem> "<summary>"` |
| `add-action` | Adds an `ACTION:` entry. | `buffer add-action Projects/<name> "(<Person>) <description>" --priority H` |
| `list` | Shows the buffer with line numbers. | `buffer list "<filter>"` |
| `rm` | Removes one line by its number. | `buffer rm <line-number>` |
| `tend` | Regroups entries by thread and date, then validates them. | `buffer tend` |
| `flush` | Tends, writes to `logs/`, then clears the buffer. | `buffer flush` |

**Options**

| Option | Effect |
|---|---|
| `--quiet` (top-level) | Hides info output. Example: `buffer --quiet flush`. |
| `--date <YYYY-MM-DD>` (all `add*`) | Files the entry under the day it happened, not today. |
| `--due`, `--scheduled <YYYY-MM-DD>` (`add-action`) | Dates set on the task at ingest. |
| `--priority H\|M\|L` (`add-action`) | Priority. |
| `--depends <uuid>` (`add-action`) | Task this one waits on. You can repeat it. |
| `--json` (`list`) | Prints JSON. |

**Notes**
- `UNKNOWN:` entries fail `tend` and block `flush`. Remove each one with `rm`, then re-add it with the right `add-*` command.
- Do not edit `buffer.md` by hand. Use these subcommands.
- `add-ref` targets are `notes/<stem>`, `logs/<path>`, `people/<name>`, `hours/<Kind>/<Thread>`, `payments/<Kind>/<Thread>` or `<Kind>/<Thread>`.
- Exit code `1` means a line number that is bad, empty or out of range, or a validation failure.

### lint

Checks vault files against the schemas in [Data formats](#data-formats).

**When to use it**
- Before you commit.
- After you edit a file by hand.

**Usage**

`lint [--schemas <dir>] [--quiet] [<path> ...]`

| Argument | Effect |
|---|---|
| `<path> ...` | Files to check. With none, it checks the whole vault. |
| `--schemas <dir>` | Uses a different schemas directory. |
| `--quiet` | Hides each violation. Only the exit code reports the result. |

**Notes**
- Each error prints as `<path>:<line>: <message>`.
- Exit codes: `0` means clean. `1` means at least one violation. `2` means no schemas were loaded.

### commit

Reviews uncommitted vault changes, then commits them to git.

**When to use it**
- At the end of a working session.
- Before and after large changes, so you have a restore point.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `review` | Shows everything changed since the last commit. Read-only. | `commit review` |
| `save` | Stages every change in the vault and commits it. | `commit save --message "<summary>"` |

**Options**

| Option | Effect |
|---|---|
| `--max-file-lines <N>` (`review`) | Maximum diff lines per file. The default is 150. |
| `--max-lines <N>` (`review`) | Maximum lines of output. The default is 3000. |
| `--message <text>` (`save`, required) | Commit subject. Must be a single line and not empty. |
| `--body <text>` (`save`) | Commit body. It can span several lines. |
| `--dry-run` (`save`) | Reports what would be staged and committed. Changes nothing. |

**Notes**
- `save` stages everything. It only ever adds a commit. It never amends, rebases, resets, checks out or pushes.
- `ADULTING_HOME` must be the root of its git repository.
- Exit code `1` means one of these: not a git repository, the vault is not the repository root, a bad `--message`, or a git failure.

## Everyday procedures

### 1. Set up a new billable project

1. `threads new --name "<name>" --kind project --category professional --currency <ISO> --rate <rate>` creates the thread with billing defaults.
2. `people new --name "<Client Contact>" --category professional` creates the client contact.
3. Add `client_name` (and optionally `client_address`, `client_vat`, `client_email`) to the thread file's frontmatter. Statements need these fields.
4. `threads show Projects/<name>` checks the result.
5. `lint` validates the vault.

### 2. Capture a meeting and turn its actions into tracked tasks

1. `notes new --type Meeting --topic "<topic>" --thread Projects/<name> --person "<Full Name>" --counterparty "<org>"` creates the note and prints its path.
2. In the note body, write lines such as `ACTION: (<Person>) <description>`, `AGREED: ...` and `RESOLVED: ...`.
3. `tasks --dry-run` previews the ingest.
4. `tasks` turns each `ACTION:` line into a `TASK:` anchor.
5. `tasks list --thread Projects/<name>` shows the new tasks.
6. `notes minutes <stem>` renders the minutes to `~/Downloads`.

### 3. Quick-capture through the day, then file it

1. `buffer add "<raw text>"` captures something when you have no time to pick a thread.
2. `buffer add-text Projects/<name> "<observation>"` captures something when you know the thread.
3. `buffer list` shows every entry with its line number.
4. `buffer rm <line-number>` removes an `UNKNOWN:` entry.
5. `buffer add-action Projects/<name> "<description>"` re-adds it in the right form. Use `add-text` or `add-ref` for other kinds.
6. `buffer tend` validates the buffer. Repeat steps 3–5 until it passes.
7. `buffer flush` writes the entries to the daily logs and clears the buffer.
8. `tasks` ingests any `ACTION:` lines that are now in the logs.

### 4. Work the task list

1. `tasks next` shows the top 5 pending tasks.
2. `tasks list --overdue` shows tasks past their due date.
3. `tasks show <uuid>` shows one task in detail.
4. `tasks set-due <uuid> <YYYY-MM-DD>` moves the due date.
5. `tasks set-priority <uuid> H` raises the priority.
6. `tasks add-depends <uuid> <dep-uuid>` records that one task waits on another.
7. `tasks done <uuid>` closes a task.

### 5. Log a session of work

1. `hours log Projects/<name> -m <minutes> <short description>` records the time. Use `-d <YYYY-MM-DD> -t <HH:MM>` if the work was earlier.
2. `buffer add-text Projects/<name> "<what actually happened>"` records the detail. Search can find it.
3. `hours list Projects/<name> --since <YYYY-MM-DD>` checks the entry.
4. `hours edit <id> -m <minutes>` corrects the duration if needed.
5. `buffer flush` files the log line and the time entry's `REF:`.

### 6. Bill a client for a month's work

1. `hours list Projects/<name> --since <YYYY-MM-01> --until <YYYY-MM-DD>` lists the month's entries.
2. `hours edit <id> --description <invoice line>` fixes any line item.
3. `hours report --thread Projects/<name> --since <YYYY-MM-01> --until <YYYY-MM-DD>` totals the month.
4. `payments statement --thread Projects/<name> --as-of <YYYY-MM-DD>` shows billed versus received.
5. `payments statement --thread Projects/<name> --as-of <YYYY-MM-DD> --pdf <path>.pdf` writes the statement PDF.

### 7. Record a payment

1. `payments log Projects/<name> <amount> -d <YYYY-MM-DD> -a "<account>" -n "<note>"` records the receipt.
2. `payments list Projects/<name>` checks it.
3. `payments statement --thread Projects/<name>` shows the updated balance.
4. `buffer flush` files the payment's `REF:` in the thread log.

### 8. Check the vault and commit it

1. `buffer tend` validates the buffer.
2. `lint` validates every file. Fix everything until it exits `0`.
3. `commit review` shows everything that changed.
4. `commit save --dry-run --message "<summary>"` previews what will be committed.
5. `commit save --message "<summary>" --body "<detail>"` stages all changes and commits them.

## Data formats

`lint` enforces every schema below. Dates are `YYYY-MM-DD` unless stated otherwise.

### `hours_file`

The time entries for one thread, as JSON in a single `simple-time-tracker` fenced block. Location: `hours/<Kind>/<Thread>.md`. The `hours` tool writes these files.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Link to an existing `Projects/`, `Processes/` or `Topics/` thread. |
| `currency` | no | 3-letter ISO code. Absent when the thread is not billable. |
| `entries[].name` | yes | Description of the work. It is the invoice line item. |
| `entries[].startTime` | yes | ISO 8601 UTC start time. |
| `entries[].endTime` | yes | ISO 8601 UTC end time. It must not be earlier than `startTime`. |
| `entries[].id` | yes | 8 hex characters, unique across hours and payments. |
| `entries[].rate` | yes | Integer rate per hour. `0` means unbillable. |
| `entries[].currency` | no | ISO 4217 code. Absent or null means unbilled. |

Duration is `endTime` minus `startTime`. There is no duration field.

### `log`

One thread's activity for one day, written by `buffer flush`. Location: `logs/<Kind>/<Name>/<YYYY-MM-DD>.md`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Link to a `Projects/`, `Processes/` or `Topics/` thread. |
| `date` | yes | The day the log covers. |
| `type` | yes | Always `Log`. |

The body holds `TEXT:`, `REF:`, `ACTION:`, `TASK:` and `DONE:` lines.

### `note_correspondence`

A note that records an email, message or letter exchange. Location: `notes/<YYYY-MM-DD-HH-MM-SS>.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about. |
| `type` | yes | `Correspondence`. |
| `threads` | yes | List of thread links. Each must resolve to a thread file. |
| `timestamp` | yes | When it happened, as `YYYY-MM-DD-HH-MM-SS`. |
| `people` | no | Participants: `[[people/X]]` links or plain names. |

The body can hold `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:` and `!:` (callout) lines.

### `note_meeting`

A note that records a meeting. Location: `notes/<YYYY-MM-DD-HH-MM-SS>.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the meeting was about. |
| `type` | yes | `Meeting`. |
| `threads` | yes | List of thread links. Each must resolve to a thread file. |
| `timestamp` | yes | When it happened, as `YYYY-MM-DD-HH-MM-SS`. |
| `counterparty` | no | The other party. |
| `location` | no | Where it was held. |
| `people` | no | Attendees: `[[people/X]]` links or plain names. |

The body can hold `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:` and `!:` (callout) lines.

### `note_simple`

A note of type Workshop, Report, Log, Research or Recipe. Location: `notes/<YYYY-MM-DD-HH-MM-SS>.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about. |
| `type` | yes | `Workshop`, `Report`, `Log`, `Research` or `Recipe`. |
| `threads` | yes | List of thread links. Each must resolve to a thread file. |
| `timestamp` | yes | When it happened, as `YYYY-MM-DD-HH-MM-SS`. |
| `people` | no | `[[people/X]]` links or plain names. |

### `payments_file`

The payments for one thread, as JSON in a single `adulting-payments` fenced block. Location: `payments/<Kind>/<Thread>.md`. The `payments` tool writes these files.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Link to an existing `Projects/`, `Processes/` or `Topics/` thread. |
| `currency` | yes | 3-letter ISO code. |
| `payments[].id` | yes | 8 hex characters, unique across hours and payments. |
| `payments[].received` | yes | ISO 8601 UTC time the money landed. |
| `payments[].amount` | yes | Amount. It must be greater than 0. |
| `payments[].currency` | yes | ISO 4217 code. |
| `payments[].account` | no | Account the money landed in. |
| `payments[].note` | no | Free text. |

### `person`

Someone you track. Location: `people/<Full Name>.md`.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | Start date. |
| `ended` | no | End date. Required when `status` is `closed`. |
| `cadences` | no | Recurring obligations. Each is a `key`, `frequency` and `description`. |

The body is free-form.

### `task_anchor`

A single `TASK:` or `DONE:` line inside a note or log. Only `tasks` writes these lines. Example:

`TASK: [#H] (Riaz Arbi) Send quarterly report <!--abcd1234 entry:2026-05-27 due:2026-05-29-->`

| Field | Required | Meaning |
|---|---|---|
| `kind` | yes | `TASK` or `DONE`. |
| `priority` | no | `H`, `M` or `L`, shown as `[#X]`. |
| `assignee` | no | A person. It must resolve to `people/<name>.md`. |
| `body` | yes | The task text. |
| `uuid` | yes | 8 hex characters, unique across the vault. |
| `entry` | yes | Ingest date. |
| `end` | no | Completion date. Required for `DONE`. It must not be earlier than `entry`. |
| `due` | no | Due date. |
| `scheduled` | no | Scheduled date. |
| `depends` | no | Comma-separated uuids of existing tasks. Dependencies must not form a cycle. |

### `thread`

A project, process or topic. Location: `threads/<Kind>/<Name>.md`, where `<Kind>` is `Projects`, `Processes` or `Topics`.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `kind` | yes | `project`, `process` or `topic`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | Start date. |
| `ended` | no | End date. Required when `status` is `closed`. |
| `cadences` | no | Recurring obligations. Each is a unique `key`, a `frequency` in days, and a `description`. |
| `currency` | no | 3-letter ISO code. Default currency for `hours`. |
| `rate` | no | Integer. Default hourly rate for `hours`. |
| `client_name` | no | The party billed on a statement. Needed for `payments statement --pdf`. |
| `client_address` | no | Address lines separated by `\|`. |
| `client_vat` | no | Client VAT number. |
| `client_email` | no | Client email. |

### `thread_entry`

A dated top-level bullet in a thread file's body, for example `- 2024-05-17 — Made progress.` Indented sub-bullets under an entry are not validated.

| Field | Required | Meaning |
|---|---|---|
| `date` | yes | Date of the entry. |
| `text` | yes | What happened. It cannot be empty. |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `buffer tend` or `buffer flush` fails and reports `UNKNOWN` entries | Quick-captures block the flush until you convert them. | Run `buffer list`, then `buffer rm <line-number>`. Re-add the entry with `buffer add-text`, `add-ref` or `add-action`. |
| `refusing to delete ... without -y` | Deletes need confirmation. | Run the command again with `-y`. |
| `--rate needs a currency` | You gave a rate but no currency was available. | Add `-c <ISO>`, or set `--currency` on the thread. |
| `hours report` shows time under `unbilled` | The entry had no currency. | Run `hours edit <id> -c <ISO> -r <rate>`. |
| `--pdf needs --thread; a statement is per client` | You asked for a statement PDF without naming a thread. | Add `--thread <Kind/Name>`. |
| `amount must be positive` or `is not a valid amount` | Payment amounts must be positive numbers. | Pass a positive decimal amount. |
| `PDF render failed` | `pandoc` or `xelatex` is missing or failed. | Install `pandoc` and a LaTeX engine, then rerun. |
| `no task found with uuid prefix` | The uuid prefix matches no task. | Get the uuid from `tasks list`. |
| `person ... does not resolve to people/<name>.md` | The assignee has no person file. | Run `people new --name "<Full Name>" --category <category>` first. |
| `lint` exits `1` | At least one file breaks its schema. | Fix each `<path>:<line>: <message>` shown, then rerun `lint`. |
| `lint` exits `2` | No schemas were loaded. | Pass `--schemas <dir>` pointing to the schemas directory. |
| `commit` reports `not a git repository` or `is not the root of its git repository` | `ADULTING_HOME` must be the root of a git repository. | Make the vault directory the root of a git repository, or point `ADULTING_HOME` at that root. |

## Quick reference

| Command | Does |
|---|---|
| `tasks` | Ingests `ACTION:` lines as `TASK:` anchors. |
| `tasks ingest` | Same as `tasks`. |
| `tasks add <thread> <text>` | Adds an `ACTION:` to the buffer. |
| `tasks done <uuid>` | Marks a task done. |
| `tasks set-description <uuid> <text>` | Rewrites a task body. |
| `tasks set-assignee <uuid> <person>` | Changes the assignee. |
| `tasks set-due <uuid> <date>` | Sets the due date. |
| `tasks set-scheduled <uuid> <date>` | Sets the scheduled date. |
| `tasks set-priority <uuid> <H\|M\|L>` | Sets the priority. |
| `tasks add-depends <uuid> <dep-uuid>` | Adds a dependency. |
| `tasks rm-depends <uuid> <dep-uuid>` | Removes a dependency. |
| `tasks list` | Lists pending tasks. |
| `tasks next` | Shows the top 5 pending tasks. |
| `tasks show <uuid>` | Shows one task. |
| `notes new --type <T> --topic <text> --thread <thread>` | Creates a note. |
| `notes list` | Lists notes. |
| `notes cat <stem>` | Prints a note. |
| `notes last` | Prints the newest note's path. |
| `notes copy <stem>` | Copies a note. |
| `notes delete <stem> -y` | Deletes a note. |
| `notes pdf <stem>` | Renders a note to Markdown and PDF. |
| `notes minutes <stem>` | Renders minutes. |
| `notes agenda <stem>` | Renders an agenda. |
| `search notes` | Finds notes. |
| `search logs` | Finds logs. |
| `search activity` | Ranks threads by activity. |
| `search overview <thread>` | Summarises one thread. |
| `search stream` | Shows a merged chronology. |
| `threads list` | Lists threads. |
| `threads show <thread>` | Shows a thread. |
| `threads new --name <name> --kind <kind> --category <category>` | Creates a thread. |
| `threads delete <thread> -y` | Deletes a thread. |
| `people list` | Lists people. |
| `people show <person>` | Shows a person. |
| `people new --name <name> --category <category>` | Creates a person. |
| `people delete <person> -y` | Deletes a person. |
| `hours log <thread> <description>` | Records time. |
| `hours list` | Lists time entries. |
| `hours report` | Totals time. |
| `hours show <id>` | Shows a time entry. |
| `hours edit <id>` | Edits a time entry. |
| `hours rm <id> -y` | Deletes a time entry. |
| `payments log <thread> <amount>` | Records a payment. |
| `payments list` | Lists payments. |
| `payments statement` | Shows billed versus received. |
| `payments show <id>` | Shows a payment. |
| `payments edit <id>` | Edits a payment. |
| `payments rm <id> -y` | Deletes a payment. |
| `buffer add <text>` | Captures an `UNKNOWN:` entry. |
| `buffer add-text <thread> <text>` | Captures a `TEXT:` entry. |
| `buffer add-ref <thread> <target>` | Captures a `REF:` entry. |
| `buffer add-action <thread> <text>` | Captures an `ACTION:` entry. |
| `buffer list` | Shows the buffer with line numbers. |
| `buffer rm <line-number>` | Removes a buffer line. |
| `buffer tend` | Regroups and validates the buffer. |
| `buffer flush` | Writes the buffer to logs and clears it. |
| `lint` | Validates vault files. |
| `commit review` | Shows uncommitted changes. |
| `commit save --message <text>` | Stages and commits all changes. |
