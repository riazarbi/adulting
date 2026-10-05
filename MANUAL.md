# adulting — Operators Manual

## Before you start

All data lives in one directory, the vault. The default is `~/vault`. To use a different vault, set `ADULTING_HOME`:

```
export ADULTING_HOME=<path-to-vault>
```

Every command reads and writes under that directory.

External programs:

| Program | Needed by |
|---|---|
| Python 3.11 or newer | every tool |
| `git` | `commit` |
| `pandoc` and a LaTeX engine (`xelatex`) | `notes pdf`, `notes minutes`, `notes agenda` |

Everything is plain text on disk: Markdown, YAML frontmatter and JSON blocks. You can read it, grep it and back it up with your own tools.

## How the pieces fit

Every path below is relative to the vault root. `<Kind>` is `Projects`, `Processes` or `Topics`.

| Object | What it is | Where it lives |
|---|---|---|
| Thread | A project, process or topic that organises everything else | `threads/<Kind>/<Name>.md` |
| Note | A typed document: meeting, correspondence, report and so on | `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md` |
| Log | One thread's activity for one day, written by `buffer flush` | `threads/<Kind>/<Name>/logs/<YYYY-MM-DD>.md` |
| Time entry | One session of work, billable or not | `threads/<Kind>/<Name>/hours.md` |
| Payment | Money received against a thread | `threads/<Kind>/<Name>/payments.md` |
| Person | A contact you track | `people/<Name>.md` |
| Action / task | An `ACTION:` line that becomes a `TASK:` anchor (later `DONE:`) inside a note or log | inside the note or log |
| Buffer | Staging queue for quick captures | `buffer.md` |
| Config | Vault-wide settings | `.adulting/config.yaml` |

Everything that belongs to a thread lives in the thread's folder, beside its thread file.

Relationships:

- A note names one or more threads. It is filed under the first one.
- A note's `people` and a task's assignee link to person files.
- People are never threads.
- A task can depend on other tasks by uuid.
- `notes new`, `hours log` and `payments log` each drop a `REF:` into the buffer. The REF reaches the thread's daily log on the next `buffer flush`.
- Tasks have no separate store. The `TASK:` line in the source file is the task.

## Command reference

Every command and subcommand accepts `--help-json`. It prints the arguments as JSON and exits 0. Every path a command prints is absolute. No command prompts or opens an app, so every command is safe to run without a terminal.

### tasks

Turns `ACTION:` lines into tracked `TASK:` anchors and edits those anchors in place.

**When to use it**

- You wrote `ACTION:` lines in a note and want them tracked.
- You want to know what to do next, or what is overdue.
- You need to change a task's due date, priority, assignee or dependencies, or mark it done.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| *(none)* | Same as `ingest` | `tasks` |
| `ingest` | Rewrites every `ACTION:` line in notes and logs as a `TASK:` anchor with a new uuid | `tasks ingest --dry-run` |
| `add` | Appends an ACTION to the buffer (same as `buffer add-action`) | `tasks add Projects/Acme "(Jane Doe) Send draft contract" --due 2026-10-15 --priority H` |
| `done` | Changes `TASK:` to `DONE:` and stamps `end:` with today's date | `tasks done ab12` |
| `set-description` | Rewrites the task body | `tasks set-description ab12 "Send signed contract"` |
| `set-assignee` | Rewrites the `(Assignee)` prefix | `tasks set-assignee ab12 "Jane Doe"` |
| `set-due` | Sets the due date | `tasks set-due ab12 2026-10-20` |
| `set-scheduled` | Sets the scheduled date | `tasks set-scheduled ab12 2026-10-18` |
| `set-priority` | Sets the priority to `H`, `M` or `L` | `tasks set-priority ab12 H` |
| `add-depends` | Makes the task wait on another task | `tasks add-depends ab12 cd34` |
| `rm-depends` | Removes a dependency | `tasks rm-depends ab12 cd34` |
| `list` | Lists pending tasks, grouped by thread | `tasks list --thread Projects/Acme` |
| `next` | Shows the top 5 pending tasks by priority, then due date, then entry date | `tasks next` |
| `show` | Shows the detail of one task | `tasks show ab12` |

**Options**

| Option | Effect |
|---|---|
| `--dry-run` | Bare `tasks` and `ingest` only. Shows what would be ingested and writes nothing. |
| `--quiet` | Bare `tasks` and `ingest` only. Suppresses per-action output. |
| `add --due <YYYY-MM-DD>` | Sets the due date. |
| `add --scheduled <YYYY-MM-DD>` | Sets the scheduled date. |
| `add --priority <H\|M\|L>` | Sets the priority. |
| `add --depends <uuid8>` | Adds a dependency. You can repeat it. |
| `list --priority <H\|M\|L>` | Shows only that priority. |
| `list --thread <Kind/Name>` | Shows only tasks whose source note carries this thread. |
| `list --assignee <person>` | Shows only tasks assigned to this person. |
| `list --overdue` | Shows only tasks whose due date is before today. |
| `list --json` | Prints JSON. |

**Notes**

- Every subcommand except `list`, `next` and `show` rewrites lines in your note and log files in place. Use `--dry-run` to preview an ingest.
- A uuid argument accepts any unique prefix of the 8-character uuid.
- `tasks add` only queues the action. It becomes a task when you run `buffer flush`.
- Exit code `1` means one of these: no task matches the prefix, the prefix is empty, the date is not `YYYY-MM-DD`, the description is empty, the person has no file in `people/`, or a task would depend on itself.

### notes

Creates, lists, prints, copies, deletes and renders notes. Each note is identified by its stem, for example `2026-09-10-14-30-00`.

**When to use it**

- You are about to hold a meeting or write up an exchange.
- You need to find a note's stem, or print a note.
- You need a PDF, minutes or an agenda to send to someone.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Creates a note and prints its path | `notes new --type Meeting --topic "Kickoff" --thread Projects/Acme --person "Jane Doe"` |
| `list` | Lists notes, oldest first: stem, date, type, threads, topic | `notes list acme` |
| `cat` | Prints a note | `notes cat 2026-09-10-14-30-00` |
| `last` | Prints the path of the newest note | `notes last` |
| `copy` | Copies a note to a new timestamp and adds ` COPY` to the topic | `notes copy 2026-09-10-14-30-00` |
| `delete` | Permanently deletes a note | `notes delete 2026-09-10-14-30-00 -y` |
| `pdf` | Renders the note to Markdown and PDF, with callouts and an action table | `notes pdf 2026-09-10-14-30-00` |
| `minutes` | Renders meeting minutes: agreements, resolutions and action items | `notes minutes 2026-09-10-14-30-00` |
| `agenda` | Renders an agenda: the note with its outcome sections emptied | `notes agenda 2026-09-10-14-30-00 --out <dir>` |

**Options**

| Option | Effect |
|---|---|
| `new --type <type>` | Required. One of `Meeting`, `Correspondence`, `Workshop`, `Report`, `Log`, `Research`, `Recipe`. |
| `new --topic <text>` | Required. What the note is about. |
| `new --thread <Kind/Name>` | Required. You can repeat it. The note is filed under the first thread. |
| `new --person <name>` | Meeting and Correspondence only. Adds an attendee. You can repeat it. It becomes a link when `people/<name>.md` exists. |
| `new --counterparty <text>` | Meeting only. Names the other party. |
| `new --location <text>` | Meeting only. Records where the meeting was held. |
| `list --json` | Prints JSON. |
| `pdf`/`minutes`/`agenda --out <dir>` | Writes the output files to `<dir>` instead of `~/Downloads`. |

**Notes**

- Every subcommand except `new` first ingests `ACTION:` lines into tasks, which rewrites source files. A failed ingest does not stop the command.
- `delete` is permanent and needs `-y` (or `--yes`).
- A render writes `<stem>.md` and `<stem>.md.pdf`.
- Exit code `1` means one of these: the topic is empty, a Meeting-only or Meeting/Correspondence-only option was used on the wrong type, the stem is malformed, the vault has no notes, or the PDF render failed.

### search

Finds notes and logs, and summarises thread activity. It returns paths and metadata, not file contents.

**When to use it**

- You need the note or log where something was discussed.
- You want to see which threads were active in a period.
- You want everything about one thread, or one day, in one view.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `notes` | Finds notes by thread, type, date or text | `search notes --thread Projects/Acme --type Meeting --since 2026-09-01` |
| `logs` | Finds daily logs by thread, date or text | `search logs --text "contract"` |
| `activity` | Ranks threads by what happened in a window | `search activity --since 2026-09-01 --until 2026-09-30` |
| `overview` | Shows the whole picture of one thread | `search overview Projects/Acme` |
| `stream` | Merges every dated record into one chronology | `search stream --today` |

**Options**

| Option | Effect |
|---|---|
| `--since <YYYY-MM-DD>` / `--until <YYYY-MM-DD>` | All subcommands. Limits results to dates on or after / on or before the given date. |
| `--json` | All subcommands. Prints JSON. |
| `--thread <Kind/Name>` | `notes`, `logs`, `activity`, `stream`. Limits results to one thread. |
| `--text <text>` | `notes`: searches topic and body. `logs`: searches entry lines. `stream`: searches thread and summary. Case-insensitive literal match. |
| `notes --type <type>` | Limits results to one note type. Case-insensitive. |
| `--limit <n>` | Caps the results. Defaults: `notes` and `logs` 20, `overview` 5, `stream` 100. `0` means all. |
| `stream --kind <list>` | Comma-separated: `note`, `log`, `task`, `done`, `hours`, `payment`, `thread`, `person`, `pending`. Default is all. |
| `stream --today` | Shows today only. |
| `stream --reverse` | Shows oldest first. The default is newest first. |

**Notes**

- Read-only.
- Dates are event dates (the frontmatter `timestamp`), not the date the file was written.
- Exit code `1` means `--kind` named an unknown kind.

### threads

Creates and inspects thread files.

**When to use it**

- You are starting a new project, process or topic.
- You need a thread's exact `Kind/Name` label.
- You want to check a thread's status or billing defaults.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists thread files, open threads only by default | `threads list acme` |
| `show` | Shows one thread file | `threads show Projects/Acme` |
| `new` | Creates a thread file | `threads new --name Acme --kind project --category professional --currency ZAR --rate 1500` |

**Options**

| Option | Effect |
|---|---|
| `list <query>` | Fuzzy search. Ranks results by similarity. |
| `list --all` | Includes paused and closed threads. |
| `list`/`show --json` | Prints JSON. |
| `new --name <name>` | Required. Becomes the filename. Cannot contain `/` or start with `.`. |
| `new --kind <project\|process\|topic>` | Required. Chooses the directory: `Projects`, `Processes` or `Topics`. |
| `new --category <professional\|personal\|voluntary>` | Required. |
| `new --currency <ISO>` | Sets the default currency for `hours` (3 letters). Makes the thread billable. |
| `new --rate <n>` | Sets the default hourly rate for `hours`. Needs `--currency`. |

**Notes**

- There is no close command and no delete command. To close a thread, set `status: closed` and `ended:` in its frontmatter. To remove a thread, delete its file and its folder by hand.
- Exit code `1` means one of these: the name is empty or invalid, the thread already exists, or `--rate` was given without `--currency`.

### people

Creates, inspects and deletes person files.

**When to use it**

- You need to assign tasks to someone, or link someone from notes.
- You want to check whether a person file exists.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists person files, open only by default | `people list jane` |
| `show` | Shows one person file | `people show "Jane Doe"` |
| `new` | Creates a person file | `people new --name "Jane Doe" --category professional` |
| `delete` | Permanently deletes a person file | `people delete "Jane Doe" -y` |

**Options**

| Option | Effect |
|---|---|
| `list <query>` | Fuzzy search. Ranks results by similarity. |
| `list --all` | Includes closed people. |
| `list`/`show --json` | Prints JSON. |
| `new --name <name>` | Required. The full name. Becomes the filename. |
| `new --category <professional\|personal\|voluntary>` | Required. |

**Notes**

- `delete` is permanent and needs `-y` (or `--yes`).
- Exit code `1` means one of these: the name is empty or invalid, the file already exists, the file was not found, or `delete` was run without `-y`.

### hours

Records time spent on a thread, billable or not.

**When to use it**

- You finished a session of work and want it on the record.
- You need totals for a period before billing.
- You logged an entry wrongly and need to fix or remove it.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Appends an entry | `hours log Projects/Acme -m 90 Contract review` |
| `list` | Lists entries | `hours list Projects/Acme --since 2026-09-01` |
| `report` | Totals time by thread and currency, with unbilled time on its own row | `hours report --thread Projects/Acme --since 2026-09-01 --until 2026-09-30` |
| `show` | Shows one entry | `hours show 1a2b3c4d` |
| `edit` | Changes a field of an entry | `hours edit 1a2b3c4d -m 120` |
| `rm` | Deletes an entry | `hours rm 1a2b3c4d -y` |

**Options**

| Option | Effect |
|---|---|
| `log -m, --minutes <n>` | Sets the duration. Default 60. Must be positive. |
| `log -r, --rate <n>` | Sets the hourly rate. `0` means unbillable. |
| `log -c, --currency <ISO>` | Sets the currency. Defaults to the thread's currency. With neither, the entry is unbilled. |
| `log -d, --date <YYYY-MM-DD>` | Sets the date. Default today. |
| `log -t, --time <HH:MM>` | Sets the start time. Default now. |
| `list`/`report --since`, `--until` | Limits results to a date window. |
| `report --thread <Kind/Name>` | Limits the report to one thread. |
| `list`/`report`/`show --json` | Prints JSON. |
| `edit --description <text>` | Sets a new description. |
| `edit -m <n>` | Sets a new duration. The start time stays. |
| `edit -r <n>` / `-c <ISO>` | Sets a new rate or currency. A rate needs a currency. |
| `edit -d <YYYY-MM-DD>` / `-t <HH:MM>` | Moves the entry. The duration is kept. |

**Notes**

- On a billable thread, the rate falls back to `hours.rate` in `.adulting/config.yaml`, then to 2500.
- Rate and currency are stored on each entry. Changing a thread's defaults later does not re-price old entries.
- Keep descriptions short. They appear on statements. `search` does not index hours, so put detail in a log line instead.
- `rm` is permanent and needs `-y` (or `--yes`).
- Exit code `1` means one of these: the minutes are not positive, a rate was given without a currency, or the description is empty.

### payments

Records money received against a thread and produces statements.

**When to use it**

- A client paid you.
- You need billed against received for a thread, as text or a PDF.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Records a receipt | `payments log Projects/Acme 13500 -a "Business account" -n Invoice 12` |
| `list` | Lists payments | `payments list Projects/Acme` |
| `statement` | Shows billed against received, by thread and currency | `payments statement --thread Projects/Acme --pdf <path>.pdf` |
| `show` | Shows one payment | `payments show 9f8e7d6c` |
| `edit` | Changes a field of a payment | `payments edit 9f8e7d6c --amount 13250` |
| `rm` | Deletes a payment | `payments rm 9f8e7d6c -y` |

**Options**

| Option | Effect |
|---|---|
| `log -c, --currency <ISO>` | Sets the currency. Defaults to the thread's currency. |
| `log -d, --date <YYYY-MM-DD>` | Sets the date received. Default today. |
| `log -t, --time <HH:MM>` | Sets the time received. Default now. |
| `log -a, --account <text>` | Records which account the money landed in. |
| `log -n, --note <text>` | Adds a free-text note. |
| `list`/`statement --since`, `--until` | Limits results to a date window. |
| `statement --thread <Kind/Name>` | Limits the statement to one thread. |
| `statement --as-of <YYYY-MM-DD>` | Sets the statement date, which drives aging. Default today. |
| `statement --pdf <path>` | Renders a PDF to `<path>`. Requires `--thread`. |
| `list`/`statement`/`show --json` | Prints JSON. |
| `edit --amount`, `-c`, `-d`, `-t`, `-a`, `-n` | Sets a new value for that field. |

**Notes**

- A PDF statement needs `client_name` in the thread's frontmatter. The supplier and banking details come from `billing:` in `.adulting/config.yaml`.
- `statement` ignores unbilled time.
- `rm` is permanent and needs `-y` (or `--yes`).
- Exit code `1` means one of these: the amount is missing, invalid or not positive, `--pdf` was used without `--thread`, or there is nothing to state for that thread and date.

### buffer

Stages quick captures in `buffer.md`, then files them into each thread's daily log.

**When to use it**

- You want to record something now and sort it out later.
- You want an observation, a pointer or an action in a thread's log without writing a note.
- It is time to file the day's captures.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `add` | Appends a raw `UNKNOWN` entry with no thread | `buffer add "call bank about fees"` |
| `add-text` | Appends a `TEXT` observation | `buffer add-text Projects/Acme "Client wants weekly updates"` |
| `add-ref` | Appends a `REF` pointer to another vault file | `buffer add-ref Projects/Acme people/Jane\ Doe "new contact"` |
| `add-action` | Appends an `ACTION` | `buffer add-action Projects/Acme "(Jane Doe) Confirm scope" --due 2026-10-10` |
| `list` | Shows the buffer with line numbers | `buffer list` |
| `rm` | Removes one line by number | `buffer rm 3` |
| `tend` | Regroups entries by thread and date, then validates them | `buffer tend` |
| `flush` | Tends, writes each thread's `logs/`, clears the buffer and ingests the flushed ACTIONs into tasks | `buffer flush` |

**Options**

| Option | Effect |
|---|---|
| `--quiet` | Global: put it before the subcommand. Suppresses info output. |
| `--date <YYYY-MM-DD>` | Every `add*` subcommand. Files the entry under the day the thing happened. |
| `add-action --due`, `--scheduled`, `--priority`, `--depends` | Same as `tasks add`. |
| `list <filter>` | Shows only lines containing this text. Case-insensitive. |
| `list --json` | Prints JSON. |

**Notes**

- An `UNKNOWN` entry blocks `tend` and `flush`. Remove it with `rm`, then re-add it with the matching `add-*` subcommand.
- `rm` takes effect at once. It does not ask for confirmation.
- Do not edit `buffer.md` by hand. Use these subcommands.
- You do not need to run `tasks` after `flush`. `flush` skips an ACTION that is already an open task and reports `already a task`. It reports a duplicate within the buffer as `already buffered`.
- Exit code `1` means one of these: a bad line number, an empty line, a line out of range, or a validation error.

### lint

Validates vault files against the schemas in [Data formats](#data-formats).

**When to use it**

- Before you commit.
- After you edit vault files by hand.
- When a command skipped a file and you want to know why.

**Usage**

```
lint [--schemas <dir>] [--quiet] [<path> ...]
```

| Argument | Meaning |
|---|---|
| `<path> ...` | Files to validate. With none, `lint` checks the whole vault. |

**Options**

| Option | Effect |
|---|---|
| `--quiet` | Suppresses per-violation output. Only the exit code reports the result. |
| `--schemas <dir>` | Uses a different schemas directory. |

**Notes**

- Read-only.
- Each error prints as `<path>:<line>: <message>`, with an absolute path.
- Exit code `0` means the files are clean. `1` means there are violations. `2` means no schemas were loaded.

### commit

Reviews changes to the vault and commits them to git.

**When to use it**

- At the end of a working session.
- After a bulk change, so you have a restore point.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `review` | Shows everything that changed since the last commit. Read-only. | `commit review` |
| `save` | Stages every change in the vault and commits it | `commit save --message "Log Acme kickoff and hours"` |

**Options**

| Option | Effect |
|---|---|
| `review --max-file-lines <n>` | Sets the maximum diff lines shown per file. Default 150. |
| `review --max-lines <n>` | Sets the maximum lines of output overall. Default 3000. |
| `save --message <text>` | Required. The commit subject, on a single line. |
| `save --body <text>` | Sets the commit body. It can span several lines. |
| `save --dry-run` | Reports what would be staged and committed, and changes nothing. |

**Notes**

- `save` stages every change in the vault, not just the files you choose.
- `save` only ever adds a commit. It never amends, rebases, resets, checks out or pushes.
- `ADULTING_HOME` must be the root of a git repository.
- Exit code `1` means one of these: the message is empty or longer than one line, the vault is not a git repository or not its root, or a git command failed.

## Everyday procedures

### 1. Set up a new billable project

1. `people new --name "Jane Doe" --category professional` creates the client contact.
2. `threads new --name Acme --kind project --category professional --currency ZAR --rate 1500` creates a billable thread.
3. `threads show Projects/Acme` confirms the file and its billing defaults.

### 2. Capture a meeting and turn its actions into tracked tasks

1. `notes new --type Meeting --topic "Kickoff" --thread Projects/Acme --person "Jane Doe" --counterparty "Acme Ltd"` creates the note and prints its path.
2. Open that path in your editor. Write the body, with one `ACTION: (Jane Doe) <task>` line per action.
3. `tasks --dry-run` previews which ACTION lines will become tasks.
4. `tasks` rewrites them as `TASK:` anchors.
5. `tasks list --thread Projects/Acme` shows the new tasks and their uuids.
6. `notes minutes <stem>` renders minutes to `~/Downloads`.

### 3. Quick-capture through the day, then file it

1. `buffer add "<anything>"` captures a thought with no thread.
2. `buffer add-text Projects/Acme "<observation>"` captures an observation when you know the thread.
3. `buffer list` shows every entry with its line number.
4. `buffer rm <line-number>` removes an `UNKNOWN` entry.
5. `buffer add-action Projects/Acme "<task>"` (or `add-text`) re-adds that entry in its proper shape.
6. `buffer tend` validates the buffer. Fix anything it reports.
7. `buffer flush` writes the daily logs, clears the buffer and creates the tasks.

### 4. Work the task list

1. `tasks next` shows the top five tasks.
2. `tasks list --overdue` shows what is late.
3. `tasks show <uuid>` shows the detail of one task.
4. `tasks set-due <uuid> <YYYY-MM-DD>` moves a deadline.
5. `tasks set-priority <uuid> H` raises a task's priority.
6. `tasks done <uuid>` closes the task.

### 5. Log a session of work

1. `hours log Projects/Acme -m 120 Contract review` records the time under a short label.
2. `buffer add-text Projects/Acme "<what actually happened>"` records the detail where `search` can find it.
3. `hours list Projects/Acme --since <YYYY-MM-DD>` confirms the entry.
4. `buffer flush` files the log line and the hours pointer.

### 6. Bill a client for a month's work

1. `hours list Projects/Acme --since 2026-09-01 --until 2026-09-30` checks each entry.
2. `hours edit <id> --description <text>` fixes any label that will appear on the statement.
3. `hours report --thread Projects/Acme --since 2026-09-01 --until 2026-09-30` totals the month.
4. `payments statement --thread Projects/Acme --as-of 2026-09-30` shows billed against received.
5. `payments statement --thread Projects/Acme --as-of 2026-09-30 --pdf <path>.pdf` renders the statement to send.

### 7. Record a payment

1. `payments log Projects/Acme 13500 -d 2026-10-02 -a "Business account" -n Invoice 12` records the receipt.
2. `payments list Projects/Acme` confirms it.
3. `payments statement --thread Projects/Acme` shows the updated balance.
4. `buffer flush` files the payment pointer in the thread's log.

### 8. Check the vault and commit it

1. `lint` validates the whole vault. Fix every reported line.
2. `commit review` shows what changed.
3. `commit save --message "<one-line summary>" --body "<detail>"` commits everything.

## Data formats

`lint` enforces every format below. Paths are relative to the vault root.

### `hours_file`

One thread's time entries. Location: `threads/<Kind>/<Name>/hours.md`. The body holds exactly one `simple-time-tracker` fenced block containing JSON `{"entries": [...]}`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to the thread whose folder holds the file |
| `currency` | no | 3-letter currency code. Omitted for unbilled threads. |
| `entries[].name` | yes | The description, as shown on statements |
| `entries[].startTime` | yes | UTC start, `YYYY-MM-DDTHH:MM:SS.mmmZ` |
| `entries[].endTime` | yes | UTC end, same form. Not before `startTime`. |
| `entries[].id` | yes | 8 hex characters. Unique across hours and payments. |
| `entries[].rate` | yes | Hourly charge as an integer. `0` means unbillable. |
| `entries[].currency` | no | 3-letter code. Absent or null means unbilled. |

### `log`

One thread's activity for one day, written by `buffer flush`. Location: `threads/<Kind>/<Name>/logs/<YYYY-MM-DD>.md`. Body lines are `TEXT:`, `REF:`, `ACTION:`, `TASK:` or `DONE:`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to the thread whose folder holds the log |
| `date` | yes | The day, `YYYY-MM-DD` |
| `type` | yes | Always `Log` |

### `note_correspondence`

A note recording an email, message or letter exchange. Location: `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md`, under the first thread it names.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about |
| `type` | yes | `Correspondence` |
| `threads` | yes | List of thread wikilinks. Each must resolve. The note is filed under the first. |
| `timestamp` | yes | When it happened, `YYYY-MM-DD-HH-MM-SS` |
| `people` | no | Participants: `[[people/X]]` links or plain names |

### `note_meeting`

A note recording a meeting. Location: `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md`, under the first thread it names.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the meeting was about |
| `type` | yes | `Meeting` |
| `threads` | yes | List of thread wikilinks. Each must resolve. The note is filed under the first. |
| `timestamp` | yes | When it happened, `YYYY-MM-DD-HH-MM-SS` |
| `counterparty` | no | The other party |
| `location` | no | Where it was held |
| `people` | no | Attendees: `[[people/X]]` links or plain names |

Body markers for the three note formats:

| Marker | Meaning |
|---|---|
| `ACTION:` | Open action, ingested by `tasks` |
| `TASK:` | Ingested action |
| `AGREED:` | Agreement, shown in `notes minutes` |
| `RESOLVED:` | Resolution, shown in `notes minutes` |
| `!:` | Callout, shown in `notes pdf` |

### `note_simple`

A note of type Workshop, Report, Log, Research or Recipe. Location: `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md`, under the first thread it names.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about |
| `type` | yes | `Workshop`, `Report`, `Log`, `Research` or `Recipe` |
| `threads` | yes | List of thread wikilinks. Each must resolve. The note is filed under the first. |
| `timestamp` | yes | When it happened, `YYYY-MM-DD-HH-MM-SS` |
| `people` | no | `[[people/X]]` links or plain names |

### `payments_file`

One thread's payments received. Location: `threads/<Kind>/<Name>/payments.md`. The body holds exactly one `adulting-payments` fenced block containing JSON `{"payments": [...]}`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to the thread whose folder holds the file |
| `currency` | yes | 3-letter currency code |
| `payments[].id` | yes | 8 hex characters. Unique across hours and payments. |
| `payments[].received` | yes | UTC date and time received, `YYYY-MM-DDTHH:MM:SS.mmmZ` |
| `payments[].amount` | yes | Amount. Must be greater than 0. |
| `payments[].currency` | yes | 3-letter currency code |
| `payments[].account` | no | Account the money landed in |
| `payments[].note` | no | Free text |

### `person`

A contact you track. Location: `people/<Name>.md`. The body is free-form.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed` |
| `category` | yes | `professional`, `personal` or `voluntary` |
| `started` | yes | `YYYY-MM-DD` |
| `ended` | no | `YYYY-MM-DD`. Required when `status` is `closed`. |
| `cadences` | no | List of `{key, frequency, description}` |

### `task_anchor`

A single `TASK:` or `DONE:` line in a note or log. Only `tasks` subcommands should change it. Example:

```
TASK: [#H] (Jane Doe) Send quarterly report <!--abcd1234 entry:2026-05-27 due:2026-05-29-->
```

| Field | Required | Meaning |
|---|---|---|
| `kind` | yes | `TASK` or `DONE` |
| `priority` | no | `H`, `M` or `L`, shown as `[#X]` |
| `assignee` | no | A person. Must resolve to `people/<name>.md`. |
| `body` | yes | The task description |
| `uuid` | yes | 8 hex characters. Unique across the vault. |
| `entry` | yes | Ingest date, `YYYY-MM-DD` |
| `end` | no | Completion date. Required for `DONE`. Not before `entry`. |
| `due` | no | Due date, `YYYY-MM-DD` |
| `scheduled` | no | Scheduled date, `YYYY-MM-DD` |
| `depends` | no | Comma-separated uuids of other tasks. Each must resolve. The dependencies must not form a cycle. |

### `thread`

A project, process or topic. Location: `threads/<Kind>/<Name>.md`, beside the folder `threads/<Kind>/<Name>/`.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed` |
| `kind` | yes | `project`, `process` or `topic` |
| `category` | yes | `professional`, `personal` or `voluntary` |
| `started` | yes | `YYYY-MM-DD` |
| `ended` | no | `YYYY-MM-DD`. Required when `status` is `closed`. |
| `cadences` | no | List of `{key, frequency, description}`. `frequency` is in days. |
| `currency` | no | Default 3-letter currency for `hours` |
| `rate` | no | Default hourly rate for `hours` |
| `client_name` | no | Party billed. Needed for `payments statement --pdf`. |
| `client_address` | no | Address lines separated by `\|` |
| `client_vat` | no | Client VAT number |
| `client_email` | no | Client email |

### `thread_entry`

A dated bullet at the top level of a thread file's body, in the form `- YYYY-MM-DD — <text>`. Indented sub-bullets below it are not validated.

| Field | Required | Meaning |
|---|---|---|
| `date` | yes | `YYYY-MM-DD` |
| `text` | yes | The entry. Must not be empty. |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `lint` reports `<path>:0: file is not valid UTF-8` | The file is not UTF-8. Other commands skip it silently. | Re-save the file as UTF-8, or remove it. |
| `lint` exits 2 with `no schemas loaded` | The schemas directory is missing or empty | Pass `--schemas <dir>`. |
| `buffer tend` or `buffer flush` fails | An `UNKNOWN` entry or another invalid line is in the buffer | Run `buffer list`, then `buffer rm <line-number>`, then re-add the entry with `buffer add-text`, `add-ref` or `add-action`. |
| `buffer rm` reports `out of range` | The line number does not exist | Run `buffer list` and use a number it shows. |
| `tasks` reports `no task found with uuid prefix` | The prefix matches no task | Run `tasks list` and copy the uuid. |
| `tasks set-assignee` reports `does not resolve to people/<name>.md` | No person file exists for that name | Run `people new --name "<name>" --category <category>`. |
| `hours log` reports `--rate needs a currency` | A rate was given and neither the entry nor the thread has a currency | Add `-c <ISO>`. |
| `payments statement` reports `--pdf needs --thread` | A PDF statement covers one client | Add `--thread <Kind/Name>`. |
| `payments log` reports `amount is required` or `is not a valid amount` | The amount is missing or not a number | Pass a positive number as the second argument. |
| `notes new` reports `--person is only for Meeting and Correspondence notes` | A type-specific option was used on the wrong note type | Drop the option, or change `--type`. |
| `notes pdf` reports `PDF render failed` | `pandoc` or `xelatex` is missing or failed | Install `pandoc` and a LaTeX engine. |
| `commit` reports `not a git repository` or `is not the root of its git repository` | `ADULTING_HOME` is not a git repository root | Run `git init` in the vault root, or point `ADULTING_HOME` at the root. |

## Quick reference

| Command | Does |
|---|---|
| `tasks` | Ingest ACTION lines into TASK anchors |
| `tasks ingest` | Ingest ACTION lines into TASK anchors |
| `tasks add <thread> <text>` | Queue an ACTION in the buffer |
| `tasks done <uuid>` | Mark a task done |
| `tasks set-description <uuid> <text>` | Rewrite a task's body |
| `tasks set-assignee <uuid> <person>` | Change a task's assignee |
| `tasks set-due <uuid> <date>` | Set a due date |
| `tasks set-scheduled <uuid> <date>` | Set a scheduled date |
| `tasks set-priority <uuid> <H\|M\|L>` | Set a priority |
| `tasks add-depends <uuid> <dep-uuid>` | Add a dependency |
| `tasks rm-depends <uuid> <dep-uuid>` | Remove a dependency |
| `tasks list` | List pending tasks |
| `tasks next` | Show the top 5 pending tasks |
| `tasks show <uuid>` | Show one task |
| `notes new --type <type> --topic <text> --thread <Kind/Name>` | Create a note |
| `notes list` | List notes |
| `notes cat <stem>` | Print a note |
| `notes last` | Print the newest note's path |
| `notes copy <stem>` | Copy a note |
| `notes delete <stem> -y` | Delete a note permanently |
| `notes pdf <stem>` | Render a note to PDF |
| `notes minutes <stem>` | Render meeting minutes |
| `notes agenda <stem>` | Render a meeting agenda |
| `search notes` | Find notes |
| `search logs` | Find daily logs |
| `search activity` | Rank threads by activity |
| `search overview <thread>` | Show one thread's whole picture |
| `search stream` | Show one merged chronology |
| `threads list` | List threads |
| `threads show <thread>` | Show a thread |
| `threads new --name <name> --kind <kind> --category <category>` | Create a thread |
| `people list` | List people |
| `people show <person>` | Show a person |
| `people new --name <name> --category <category>` | Create a person |
| `people delete <person> -y` | Delete a person permanently |
| `hours log <thread> <description>` | Record time |
| `hours list` | List time entries |
| `hours report` | Total time by thread and currency |
| `hours show <id>` | Show a time entry |
| `hours edit <id>` | Change a time entry |
| `hours rm <id> -y` | Delete a time entry |
| `payments log <thread> <amount>` | Record a payment |
| `payments list` | List payments |
| `payments statement` | Show billed against received |
| `payments show <id>` | Show a payment |
| `payments edit <id>` | Change a payment |
| `payments rm <id> -y` | Delete a payment |
| `buffer add <text>` | Capture a raw UNKNOWN entry |
| `buffer add-text <thread> <text>` | Capture an observation |
| `buffer add-ref <thread> <target>` | Capture a pointer |
| `buffer add-action <thread> <text>` | Capture an action |
| `buffer list` | Show the buffer |
| `buffer rm <line-number>` | Remove a buffer line |
| `buffer tend` | Regroup and validate the buffer |
| `buffer flush` | File the buffer into logs and tasks |
| `lint` | Validate the vault |
| `commit review` | Show uncommitted changes |
| `commit save --message <text>` | Commit every change |
