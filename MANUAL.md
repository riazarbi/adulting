# adulting — Operators Manual

## Before you start

All data lives in one vault directory. The default is `~/vault/`. Set `ADULTING_HOME` to use a different directory. Every tool reads and writes under it.

| Program | Needed by |
|---|---|
| Python 3.11 or newer | every tool |
| `git` | `commit` |
| `pandoc` and a LaTeX engine (`xelatex`) | `notes pdf`, `notes minutes`, `notes agenda` |

There is no database. Everything is plain text on disk: Markdown files, YAML frontmatter and JSON blocks. Tasks live as lines inside notes and logs, so there is no separate task store. You can read, grep, edit and back up the vault with ordinary tools. Vault-wide settings live in `.adulting/config.yaml`.

## How the pieces fit

| Object | What it is | Where it lives |
|---|---|---|
| Thread | An organising lens: a `project` (bounded), `process` (ongoing) or `topic` (catchall). | `threads/Projects/`, `threads/Processes/`, `threads/Topics/` |
| Note | A typed document, such as a meeting, correspondence or report. | `notes/<stem>.md` |
| Person | A contact you track, used as a link target. | `people/<name>.md` |
| Log | One file per thread per day, written by `buffer flush`. | `logs/<Kind>/<Name>/<YYYY-MM-DD>.md` |
| Buffer | The quick-capture inbox that feeds logs. | `buffer.md` |
| Time entry | A session of work on a thread, billable or not. | `hours/<Kind>/<Thread>.md` |
| Payment | Money received against a thread. | `payments/<Kind>/<Thread>.md` |
| Action / task | An `ACTION:` line that becomes a `TASK:` anchor, then a `DONE:` anchor. | Inside files in `notes/` and `logs/` |

Relationships:

- Every note, log, time entry and payment belongs to a thread. A note can belong to several threads.
- People are linked from notes (`people`) and from tasks (the assignee). A person is never a thread.
- Actions live inside notes and logs. The file that holds an action is its only store.
- `notes new`, `hours log` and `payments log` each add a `REF:` line to the buffer. After `buffer flush`, that line appears in the thread's log for the day the thing happened.
- `payments statement` compares billed hours with payments received, per thread.

## Command reference

These rules apply to every tool:

- No command prompts for input or opens an app. No command is interactive or TTY-only.
- A permanent delete needs `-y`. Without it, the command refuses and exits `1`.
- Errors print a message and exit `1`, unless a tool says otherwise.
- Every printed path is absolute.
- `--json` gives machine-readable output wherever it is offered.

### tasks

Turns `ACTION:` lines into tracked `TASK:` anchors and edits those anchors.

**When to use it**

- You wrote `ACTION:` lines into a note and want them tracked.
- You want to see what to work on next.
- You need to change a task's due date, priority, assignee or dependencies, or mark it done.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| *(none)* | Same as `ingest`. | `tasks` |
| `ingest` | Rewrites every `ACTION:` line in `notes/` and `logs/` as a `TASK:` anchor with a new 8-character uuid. | `tasks ingest --dry-run` |
| `add` | Adds an `ACTION:` to the buffer. Same as `buffer add-action`. | `tasks add Projects/<Name> "(<Person>) <description>" --due <YYYY-MM-DD>` |
| `done` | Changes `TASK:` to `DONE:` and stamps today as `end`. | `tasks done <uuid>` |
| `set-description` | Rewrites the task body. | `tasks set-description <uuid> "<new text>"` |
| `set-assignee` | Rewrites the `(Assignee)` prefix. | `tasks set-assignee <uuid> "<Person>"` |
| `set-due` | Sets the due date. | `tasks set-due <uuid> <YYYY-MM-DD>` |
| `set-scheduled` | Sets the scheduled date. | `tasks set-scheduled <uuid> <YYYY-MM-DD>` |
| `set-priority` | Sets priority `H`, `M` or `L`. Writes `[#X]` into the visible text. | `tasks set-priority <uuid> H` |
| `add-depends` | Makes this task wait on another task. | `tasks add-depends <uuid> <dep-uuid>` |
| `rm-depends` | Removes a dependency. | `tasks rm-depends <uuid> <dep-uuid>` |
| `list` | Lists pending tasks, grouped by thread and sorted by priority, due date and entry date. | `tasks list --overdue` |
| `next` | Shows the top 5 pending tasks by priority, due date and entry date. | `tasks next` |
| `show` | Shows the detail of one task. | `tasks show <uuid>` |

**Options**

Global options apply to bare `tasks` and to `tasks ingest`:

| Option | Effect |
|---|---|
| `--dry-run` | Shows what would be ingested and writes nothing. |
| `--quiet` | Suppresses the per-action output. |

| Option | Effect |
|---|---|
| `add --due <YYYY-MM-DD>` | Sets the due date. |
| `add --scheduled <YYYY-MM-DD>` | Sets the scheduled date. |
| `add --priority H\|M\|L` | Sets the priority. |
| `add --depends <uuid8>` | Waits on another task. You can repeat it. |
| `list --priority H\|M\|L` | Shows one priority only. |
| `list --thread <Kind/Name>` | Shows tasks whose source note carries this thread. |
| `list --assignee <Person>` | Shows tasks assigned to this person. |
| `list --overdue` | Shows only tasks with a due date before today. |
| `list --json` | Gives JSON output. |

**Notes**

- A `<uuid>` argument accepts any unique prefix. Get uuids from `tasks list`.
- Every subcommand except `list`, `next` and `show` rewrites the source note or log in place.
- Ingest checks that the thread and assignee resolve and that the attributes are well formed.
- An assignee must have a file at `people/<name>.md`. You can write the name with or without `people/` in front.
- A task cannot depend on itself.
- Dates must be in `YYYY-MM-DD` form.

### notes

Creates, lists, prints, copies, deletes and renders notes. Each note is named by its stem.

**When to use it**

- You are starting a meeting, correspondence or report record.
- You need a note's stem, or its contents.
- You need meeting minutes, an agenda or a PDF to send.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Creates a note and prints its path. | `notes new --type Meeting --topic "<topic>" --thread Projects/<Name> --person "<Person>"` |
| `list` | Lists notes, oldest first, with stem, date, type, threads and topic. | `notes list <filter>` |
| `cat` | Prints a note. | `notes cat <stem>` |
| `last` | Prints the path of the newest note. | `notes last` |
| `copy` | Copies a note to a new timestamp and adds ` COPY` to its topic. | `notes copy <stem>` |
| `delete` | Deletes a note permanently. | `notes delete <stem> -y` |
| `pdf` | Renders a note to Markdown and PDF, with callouts and an action table. | `notes pdf <stem>` |
| `minutes` | Renders meeting minutes: agreements, resolutions and action items. | `notes minutes <stem>` |
| `agenda` | Renders an agenda: the note with its outcome sections emptied. | `notes agenda <stem>` |

**Options**

| Option | Effect |
|---|---|
| `new --type <T>` | Required. One of `Meeting`, `Correspondence`, `Workshop`, `Report`, `Log`, `Research` or `Recipe`. |
| `new --topic <text>` | Required. What the note is about. |
| `new --thread <Kind/Name>` | Required. You can repeat it. |
| `new --person <Person>` | `Meeting` and `Correspondence` only. You can repeat it. The name is linked when `people/<name>.md` exists. |
| `new --counterparty <text>` | `Meeting` only. The other party. |
| `new --location <text>` | `Meeting` only. Where the meeting was held. |
| `list [filter]` | Matches case-insensitive text in any column. |
| `list --json` | Gives JSON output. |
| `delete -y`, `--yes` | Required. Confirms the delete. |
| `pdf`/`minutes`/`agenda --out <DIR>` | Sets the output directory. The default is `~/Downloads`. |

**Notes**

- A stem is the filename without `.md`, for example `2026-09-10-14-30-00`.
- Every subcommand except `new` first ingests `ACTION:` lines. This rewrites source files, even for `list` and `cat`. If an action fails to ingest, the command carries on.
- `new` adds a `REF:` to the buffer.
- Renders write `<stem>.md` and `<stem>.md.pdf`.

### search

Finds notes and logs, and summarises activity on threads. Read-only.

**When to use it**

- You need the notes or logs on a thread, or in a date range.
- You want to see which threads were busy in a period.
- You want one thread's full picture, or a merged timeline.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `notes` | Finds notes by thread, type, date or text. | `search notes --thread Projects/<Name> --type Meeting` |
| `logs` | Finds daily logs by thread, date or text. | `search logs --text "<words>" --since <YYYY-MM-DD>` |
| `activity` | Ranks threads by what happened in a date window. | `search activity --since <YYYY-MM-DD>` |
| `overview` | Shows the whole picture of one thread. | `search overview Projects/<Name>` |
| `stream` | Merges every dated record into one timeline. | `search stream --today` |

**Options**

| Option | Effect |
|---|---|
| `--thread <Kind/Name>` | Limits results to one thread. Takes a name, `Kind/Name` or a wikilink. |
| `--since <YYYY-MM-DD>` / `--until <YYYY-MM-DD>` | Sets the date window. Both ends are inclusive. |
| `--text <words>` | Case-insensitive literal match. `notes` searches topic and body. `logs` searches entry lines. `stream` searches thread and summary. |
| `notes --type <T>` | Filters by note type. Case-insensitive. |
| `--limit <N>` | Sets the maximum results. Defaults: 20 for `notes` and `logs`, 5 for `overview`, 100 for `stream`. `0` returns all. |
| `stream --kind <list>` | Comma-separated. Any of `note`, `log`, `task`, `done`, `hours`, `payment`, `thread`, `person`, `pending`. The default is all. |
| `stream --today` | Shows today only. |
| `stream --reverse` | Shows oldest first. The default is newest first. |
| `--json` | Gives JSON output. |

**Notes**

- Results are absolute paths with metadata, never file bodies. Open the files yourself.
- Dates are event dates, from the note's `timestamp` field. The filename is used only when that field is missing or malformed.
- An unknown `--kind` value exits `1`.

### threads

Creates, lists, shows and deletes thread files.

**When to use it**

- You are starting a new project, process or topic.
- You need the exact name of a thread.
- You want a thread to carry a default currency and rate for billing.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists threads. Shows open threads by default. | `threads list <query>` |
| `show` | Shows one thread file. | `threads show Projects/<Name>` |
| `new` | Creates a thread file. | `threads new --name <Name> --kind project --category professional` |
| `delete` | Deletes a thread file permanently. | `threads delete Projects/<Name> -y` |

**Options**

| Option | Effect |
|---|---|
| `list [query]` | Fuzzy search, ranked by similarity. |
| `list --all` | Includes paused and closed threads. |
| `list`/`show --json` | Gives JSON output. |
| `new --name <Name>` | Required. Becomes the filename. |
| `new --kind project\|process\|topic` | Required. Sets the directory: `Projects/`, `Processes/` or `Topics/`. |
| `new --category professional\|personal\|voluntary` | Required. |
| `new --currency <ISO>` | Sets the default currency for `hours`. Use a 3-letter code. A thread with a currency is billable. |
| `new --rate <N>` | Sets the default hourly rate for `hours`. Needs `--currency`. |

**Notes**

- A name cannot contain `/` or start with `.`. A name that already exists is refused.

### people

Creates, lists, shows and deletes person files.

**When to use it**

- You need to assign a task to someone who has no file yet.
- You want attendees on a note to be linked.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists people. Shows open people by default. | `people list <query>` |
| `show` | Shows one person file. | `people show "<Full Name>"` |
| `new` | Creates a person file. | `people new --name "<Full Name>" --category professional` |
| `delete` | Deletes a person file permanently. | `people delete "<Full Name>" -y` |

**Options**

| Option | Effect |
|---|---|
| `list [query]` | Fuzzy search, ranked by similarity. |
| `list --all` | Includes closed people. |
| `list`/`show --json` | Gives JSON output. |
| `new --name <Full Name>` | Required. Becomes the filename. |
| `new --category professional\|personal\|voluntary` | Required. |

**Notes**

- A name cannot contain `/` or start with `.`. A name that already exists is refused.

### hours

Records time spent on a thread, billable or not.

**When to use it**

- You finished a session of client work.
- You want to track unbilled time, such as exercise or admin, next to client work.
- You need totals for a period before you invoice.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Appends an entry. | `hours log Projects/<Name> -m 90 "<description>"` |
| `list` | Lists entries. | `hours list Projects/<Name> --since <YYYY-MM-DD>` |
| `report` | Totals time by thread and currency. Unbilled time gets its own total. | `hours report --since <YYYY-MM-DD> --until <YYYY-MM-DD>` |
| `show` | Shows one entry. | `hours show <id>` |
| `edit` | Changes one field of an entry. | `hours edit <id> -m 120` |
| `rm` | Deletes an entry permanently. | `hours rm <id> -y` |

**Options**

| Option | Effect |
|---|---|
| `log -m`, `--minutes <N>` | Sets the duration in minutes. The default is 60. Must be positive. |
| `log -r`, `--rate <N>` | Sets the hourly rate. `0` means unbillable. Needs a currency. |
| `log -c`, `--currency <ISO>` | Sets the currency. Defaults to the thread's currency. With neither, the entry is recorded as unbilled. |
| `log -d`, `--date <YYYY-MM-DD>` | Sets the day. The default is today. |
| `log -t`, `--time <HH:MM>` | Sets the start time. The default is now. |
| `edit --description <text>` | Sets a new description. |
| `edit -m`, `--minutes <N>` | Sets a new duration. The start time stays the same. |
| `edit -r`, `--rate <N>` | Sets a new rate. Needs a currency. |
| `edit -c`, `--currency <ISO>` | Sets a new currency. |
| `edit -d`, `--date <YYYY-MM-DD>` / `-t`, `--time <HH:MM>` | Moves the entry. The duration stays the same. |
| `list [thread]`, `report --thread <Kind/Name>` | Limits results to one thread. |
| `--since` / `--until <YYYY-MM-DD>` | Sets the date window for `list` and `report`. |
| `--json` | Gives JSON output from `list`, `report` and `show`. |
| `rm -y`, `--yes` | Required. Confirms the delete. |

**Notes**

- Keep the description short. It appears as an invoice line item. `search` does not index hours, so put any detail in a log line.
- Each `log` adds a `REF:` to the buffer, filed under the day the work happened.
- The rate and currency are stored on each entry. Changing a thread's defaults later does not change past entries.
- An `<id>` is 8 characters. Get it from `hours list`.

### payments

Records money received against a thread and produces statements.

**When to use it**

- A client paid you.
- You want billed versus received for a client, or a PDF statement of account.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Records a payment received. | `payments log Projects/<Name> <amount> -a "<account>"` |
| `list` | Lists payments. | `payments list Projects/<Name>` |
| `statement` | Shows billed versus received, by thread and currency. | `payments statement --thread Projects/<Name> --pdf <path>.pdf` |
| `show` | Shows one payment. | `payments show <id>` |
| `edit` | Changes one field of a payment. | `payments edit <id> --amount <amount>` |
| `rm` | Deletes a payment permanently. | `payments rm <id> -y` |

**Options**

| Option | Effect |
|---|---|
| `log -c`, `--currency <ISO>` | Sets the currency. Defaults to the thread's currency. |
| `log -d`, `--date <YYYY-MM-DD>` | Sets the date received. The default is today. |
| `log -t`, `--time <HH:MM>` | Sets the time received. The default is now. |
| `log -a`, `--account <text>` | Records the account the money landed in. |
| `log -n`, `--note <text>` | Adds a free-text note. |
| `edit --amount`, `-c`, `-d`, `-t`, `-a`, `-n` | Each sets a new value for that field. |
| `statement --thread <Kind/Name>` | Limits the statement to one thread. |
| `statement --as-of <YYYY-MM-DD>` | Sets the statement date, which drives aging. The default is today. |
| `statement --pdf <path>` | Renders a PDF to this path. Requires `--thread`. |
| `--since` / `--until <YYYY-MM-DD>` | Sets the date window for `list` and `statement`. |
| `--json` | Gives JSON output from `list`, `statement` and `show`. |
| `rm -y`, `--yes` | Required. Confirms the delete. |

**Notes**

- The amount is required and must be positive. A refund is not a negative payment.
- The statement ignores unbilled hours.
- A PDF statement needs `client_name` in the thread file.
- If there is nothing to state for the thread and date, the statement exits `1`.
- Each `log` adds a `REF:` to the buffer, filed under the day the money was received.

### buffer

Manages the quick-capture inbox at `buffer.md` and flushes it into daily logs.

**When to use it**

- You want to capture something now and sort it out later.
- You want to record an observation or a pointer on a thread without writing a note.
- At the end of a day, you want everything filed into logs and tasks.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `add` | Adds an `UNKNOWN` entry: raw text with no thread. | `buffer add "<text>"` |
| `add-text` | Adds a `TEXT` observation to a thread. | `buffer add-text Projects/<Name> "<text>"` |
| `add-ref` | Adds a `REF` pointer to another vault file. | `buffer add-ref Projects/<Name> notes/<stem> "<summary>"` |
| `add-action` | Adds an `ACTION` entry. Same as `tasks add`. | `buffer add-action Projects/<Name> "(<Person>) <description>" --priority H` |
| `list` | Shows the buffer with line numbers. | `buffer list` |
| `rm` | Removes one line by its number. | `buffer rm <line-number>` |
| `tend` | Regroups entries by thread and date, and validates them. Safe to repeat. | `buffer tend` |
| `flush` | Tends the buffer, writes `logs/`, clears the buffer and ingests the flushed actions into tasks. | `buffer flush` |

**Options**

| Option | Effect |
|---|---|
| `--quiet` (global) | Suppresses info output. |
| `add*` `--date <YYYY-MM-DD>` | Files the entry under the day the thing happened. The default is today. |
| `add-ref <target>` | Takes `notes/<stem>`, `logs/<path>`, `people/<name>`, `hours/<Kind>/<Thread>`, `payments/<Kind>/<Thread>` or `<Kind>/<Thread>`. |
| `add-action --due`, `--scheduled <YYYY-MM-DD>` | Sets the task dates. |
| `add-action --priority H\|M\|L` | Sets the priority. |
| `add-action --depends <uuid8>` | Waits on another task. You can repeat it. |
| `list [filter]` | Shows only lines containing this text. Case-insensitive. |
| `list --json` | Gives JSON output. |

**Notes**

- `UNKNOWN` entries fail `tend` and block `flush`. To convert one, remove it with `rm` and add it again with the matching `add-*` command.
- `flush` changes `logs/`, `buffer.md` and the task anchors. You do not need to run `tasks` afterwards.
- `flush` skips an action that is already an open task and reports `already a task: <uuid> <path:line> <description>`. A repeat inside the buffer is reported as `already buffered`.
- Line numbers change after `rm` and `tend`. Run `buffer list` again before the next `rm`.
- Change the buffer only with these commands. Do not edit `buffer.md` by hand.

### lint

Checks vault files against the schemas in [Data formats](#data-formats). Read-only.

**Usage**

```
lint [--schemas <dir>] [--quiet] [<path> ...]
```

| Argument | Effect |
|---|---|
| `<path> ...` | Checks these files only. With no paths, it checks the whole vault. |
| `--schemas <dir>` | Uses schemas from this directory instead of the built-in ones. |
| `--quiet` | Prints nothing. Only the exit code reports the result. |

**Notes**

- Exit `0` means the files are clean. Exit `1` means there are violations. Exit `2` means no schemas loaded.
- Each violation prints as `<path>:<line>: <message>`, with an absolute path.
- Other tools skip files that are not valid UTF-8. `lint` reports them as `<path>:0: file is not valid UTF-8`.

### commit

Reviews vault changes and commits them to git.

**When to use it**

- At the end of a session, you want to record what changed.
- You want to see every change since the last commit.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `review` | Shows everything that changed since the last commit. Read-only. | `commit review` |
| `save` | Stages every change in the vault and commits it. | `commit save --message "<subject>" --body "<detail>"` |

**Options**

| Option | Effect |
|---|---|
| `review --max-file-lines <N>` | Sets the maximum diff lines per file. The default is 150. |
| `review --max-lines <N>` | Sets the maximum output lines overall. The default is 3000. |
| `save --message <text>` | Required. The commit subject. Must be one line and not empty. |
| `save --body <text>` | Sets the commit body. It can span several lines. |
| `save --dry-run` | Reports what would be staged and committed. Changes nothing. |

**Notes**

- `save` only adds commits. It never amends, rebases, resets, checks out or pushes.
- The vault must be the root of a git repository. If it is not, `save` exits `1`.

## Everyday procedures

### 1. Set up a new billable project

1. `threads new --name <Name> --kind project --category professional --currency <ISO> --rate <rate>` creates the thread with billing defaults.
2. `people new --name "<Full Name>" --category professional` adds your client contact.
3. Open `threads/Projects/<Name>.md` and set `client_name`, plus any other `client_*` fields, so you can render statements.
4. `lint threads/Projects/<Name>.md` checks the thread file.

### 2. Capture a meeting and turn its actions into tracked tasks

1. `notes new --type Meeting --topic "<topic>" --thread Projects/<Name> --person "<Full Name>" --counterparty "<org>"` creates the note and prints its path.
2. Open the printed path. Add `ACTION: (<Full Name>) <description>` lines, plus `AGREED:` and `RESOLVED:` lines where they apply.
3. `tasks` turns the `ACTION:` lines into `TASK:` anchors.
4. `tasks list --thread Projects/<Name>` confirms the new tasks.
5. `notes minutes <stem>` renders the minutes to `~/Downloads`.

### 3. Quick-capture through the day, then file it

1. `buffer add "<raw thought>"` captures an entry without a thread.
2. `buffer list` shows every entry with its line number.
3. `buffer rm <line-number>` removes the raw entry.
4. `buffer add-text Projects/<Name> "<observation>"` re-adds it as an observation. Use `buffer add-action` instead if it is a task.
5. `buffer tend` validates the buffer. Fix anything it reports.
6. `buffer flush` writes the logs and creates the tasks.

### 4. Work the task list

1. `tasks next` shows the top 5 pending tasks.
2. `tasks list --overdue` shows tasks past their due date.
3. `tasks show <uuid>` shows the detail of one task.
4. `tasks set-due <uuid> <YYYY-MM-DD>` moves a deadline.
5. `tasks set-priority <uuid> H` raises a task's priority.
6. `tasks done <uuid>` marks a task complete.

### 5. Log a session of work

1. `hours log Projects/<Name> -m <minutes> "<short label>"` records the time.
2. `buffer add-text Projects/<Name> "<what actually happened>"` records the detail, if there is any.
3. `buffer flush` files the log line and the time entry's `REF:` into the day's log.

### 6. Bill a client for a month's work

1. `hours list Projects/<Name> --since <YYYY-MM-01> --until <YYYY-MM-DD>` shows the line items for the month.
2. `hours edit <id> --description "<label>"` corrects any label before it reaches the client.
3. `hours report --thread Projects/<Name> --since <YYYY-MM-01> --until <YYYY-MM-DD>` shows the totals.
4. `payments statement --thread Projects/<Name> --pdf <path>.pdf` renders the statement of account.

### 7. Record a payment

1. `payments log Projects/<Name> <amount> -d <YYYY-MM-DD> -a "<account>"` records the money received.
2. `payments statement --thread Projects/<Name>` confirms the new balance.
3. `buffer flush` files the payment's `REF:` into that day's log.

### 8. Check the vault and commit it

1. `buffer flush` files anything still in the buffer.
2. `lint` checks the whole vault. Fix any violations before you continue.
3. `commit review` shows everything that changed.
4. `commit save --message "<one-line summary>" --body "<detail>"` stages and commits the changes.

## Data formats

`lint` enforces every format below. Paths are relative to the vault.

### `hours_file`

The time entries for one thread. `hours` writes and maintains it. Location: `hours/{Projects,Processes,Topics}/<Thread>.md`. The body holds exactly one `simple-time-tracker` fenced block. That block contains JSON shaped as `{"entries": [...]}`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to an existing `Projects/`, `Processes/` or `Topics/` thread. |
| `currency` | no | 3-letter ISO code. Omitted for unbilled threads. |

Each entry:

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | The description, used as an invoice line item. |
| `startTime` | yes | UTC timestamp, `YYYY-MM-DDTHH:MM:SS.mmmZ`. |
| `endTime` | yes | Same form. Must not be before `startTime`. The duration is `endTime` minus `startTime`. |
| `id` | yes | 8 hex characters. Unique across hours and payments. |
| `rate` | yes | Hourly charge as an integer. `0` means unbillable. |
| `currency` | no | ISO 4217 code. Absent or null means unbilled. |

### `log`

A per-thread, per-day activity file written by `buffer flush`. Location: `logs/<Kind>/<Name>/<YYYY-MM-DD>.md`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to a `Projects/`, `Processes/` or `Topics/` thread. |
| `date` | yes | The day, `YYYY-MM-DD`. |
| `type` | yes | Always `Log`. |

Body lines start with `TEXT:`, `REF:`, `ACTION:`, `TASK:` or `DONE:`.

### `note_correspondence`

A note recording emails, messages or letters. Location: `notes/<YYYY-MM-DD-HH-MM-SS>.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about. |
| `type` | yes | `Correspondence`. |
| `threads` | yes | List of thread wikilinks. Each must resolve. |
| `timestamp` | yes | When it happened, `YYYY-MM-DD-HH-MM-SS`. |
| `people` | no | List of `[[people/X]]` links, which must resolve, or plain names. |

Body markers: `ACTION:`, `TASK:`, `AGREED:` and `RESOLVED:` (shown in minutes), and `!:` (a callout, shown in the PDF).

### `note_meeting`

A note recording a meeting. Location: `notes/<YYYY-MM-DD-HH-MM-SS>.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the meeting was about. |
| `type` | yes | `Meeting`. |
| `threads` | yes | List of thread wikilinks. Each must resolve. |
| `timestamp` | yes | When it happened, `YYYY-MM-DD-HH-MM-SS`. |
| `counterparty` | no | The other party. |
| `location` | no | Where it was held. |
| `people` | no | List of `[[people/X]]` links, which must resolve, or plain names. |

Body markers: the same as `note_correspondence`.

### `note_simple`

A note of type Workshop, Report, Log, Research or Recipe. Location: `notes/<YYYY-MM-DD-HH-MM-SS>.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about. |
| `type` | yes | `Workshop`, `Report`, `Log`, `Research` or `Recipe`. |
| `threads` | yes | List of thread wikilinks. Each must resolve. |
| `timestamp` | yes | When it happened, `YYYY-MM-DD-HH-MM-SS`. |
| `people` | no | List of `[[people/X]]` links or plain names. |

Body markers: the same as `note_correspondence`.

### `payments_file`

The payments received for one thread. `payments` writes and maintains it. Location: `payments/{Projects,Processes,Topics}/<Thread>.md`. The body holds exactly one `adulting-payments` fenced block. That block contains JSON shaped as `{"payments": [...]}`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to an existing thread. |
| `currency` | yes | 3-letter ISO code. |

Each payment:

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | 8 hex characters. Unique across hours and payments. |
| `received` | yes | When the money landed, as a UTC timestamp `YYYY-MM-DDTHH:MM:SS.mmmZ`. |
| `amount` | yes | Must be greater than 0. |
| `currency` | yes | ISO 4217 code. |
| `account` | no | The account the money landed in. |
| `note` | no | Free text. |

### `person`

A contact you track. Location: `people/<Full Name>.md`. The body is free-form.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | `YYYY-MM-DD`. |
| `ended` | no | `YYYY-MM-DD`. Required when `status` is `closed`. |
| `cadences` | no | List of `{key, frequency, description}`. |

### `task_anchor`

One `TASK:` or `DONE:` line in a note or log. Only `tasks` writes or changes these lines. Do not edit them by hand. Example:

```
TASK: [#H] (Riaz Arbi) Send quarterly report <!--abcd1234 entry:2026-05-27 due:2026-05-29-->
```

| Field | Required | Meaning |
|---|---|---|
| `kind` | yes | `TASK` or `DONE`. |
| `priority` | no | `H`, `M` or `L`, written as `[#X]`. |
| `assignee` | no | Must resolve to `people/<name>.md`. |
| `body` | yes | The task text. |
| `uuid` | yes | 8 hex characters. Unique across the vault. |
| `entry` | yes | Ingest date. |
| `end` | no | Completion date. Required for `DONE`. Must not be before `entry`. |
| `due` | no | Due date. |
| `scheduled` | no | Scheduled date. |
| `depends` | no | Comma-separated uuids. Each must resolve to another task. Dependencies cannot form a cycle. |

### `thread`

One project, process or topic. Location: `threads/{Projects,Processes,Topics}/<Name>.md`.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `kind` | yes | `project`, `process` or `topic`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | `YYYY-MM-DD`. |
| `ended` | no | `YYYY-MM-DD`. Required when `status` is `closed`. |
| `cadences` | no | List of `{key, frequency, description}`. `frequency` is in days. |
| `currency` | no | 3-letter ISO code. Makes the thread billable. |
| `rate` | no | Default hourly rate, as an integer. |
| `client_name` | no | The billed party. Required for `payments statement --pdf`. |
| `client_address` | no | Pipe-separated lines, for example `Unit 301\|2 Park Road\|Cape Town`. |
| `client_vat` | no | The client's VAT number. |
| `client_email` | no | The client's email address. |

### `thread_entry`

A dated top-level bullet in a thread file's body, in the form `- <YYYY-MM-DD> — <text>`. Indented sub-bullets under it are not checked.

| Field | Required | Meaning |
|---|---|---|
| `date` | yes | `YYYY-MM-DD`. |
| `text` | yes | The entry. Cannot be empty. |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `buffer tend` or `buffer flush` reports violations on `UNKNOWN` lines | Quick-capture entries block the flush until they are converted. | Run `buffer list`, then `buffer rm <line-number>`, then re-add the entry with `buffer add-text`, `add-ref` or `add-action`. |
| `refusing to delete ... without -y` | Every delete needs confirmation. | Run the command again with `-y`. |
| `--rate needs a currency` from `hours` or `threads new` | A rate needs a currency. | Add `-c <ISO>` to `hours`, or `--currency <ISO>` to `threads new`. |
| `--pdf needs --thread` | A statement covers one client. | Add `--thread <Kind/Name>`. |
| `amount is required` or `amount must be positive` | `payments log` needs a positive amount. | Give the amount as the second argument. |
| `person '<X>' does not resolve to people/<X>.md` | The assignee has no person file. | Run `people new --name "<X>" --category <category>`. |
| `no task found with uuid prefix` | The uuid is wrong or the prefix matches nothing. | Get the uuid from `tasks list`. |
| `PDF render failed` | `pandoc` or the LaTeX engine is missing or failed. | Install `pandoc` and `xelatex`, then render again. |
| `--person is only for Meeting and Correspondence notes` | `--person` was used on another note type. `--counterparty` and `--location` are for `Meeting` only. | Drop the option or change `--type`. |
| `not a git repository` or `ADULTING_HOME ... is not the root of its git repository` | `commit` needs the vault to be a git repository root. | Make the vault directory itself the repository root. |
| A file is missing from listings and searches | The file is not valid UTF-8, so tools skip it. | Run `lint`. It reports `<path>:0: file is not valid UTF-8`. Fix or remove the file. |
| `lint` exits `2` with `no schemas loaded` | The `--schemas` directory holds no schemas. | Fix the `--schemas` path, or drop the option. |

## Quick reference

| Command | Does |
|---|---|
| `tasks` | Ingests `ACTION:` lines as `TASK:` anchors. |
| `tasks ingest` | Same as bare `tasks`. |
| `tasks add <thread> <text>` | Adds an action to the buffer. |
| `tasks done <uuid>` | Marks a task done. |
| `tasks set-description <uuid> <text>` | Rewrites the task body. |
| `tasks set-assignee <uuid> <person>` | Changes the assignee. |
| `tasks set-due <uuid> <date>` | Sets the due date. |
| `tasks set-scheduled <uuid> <date>` | Sets the scheduled date. |
| `tasks set-priority <uuid> <H\|M\|L>` | Sets the priority. |
| `tasks add-depends <uuid> <dep-uuid>` | Adds a dependency. |
| `tasks rm-depends <uuid> <dep-uuid>` | Removes a dependency. |
| `tasks list` | Lists pending tasks. |
| `tasks next` | Shows the top 5 pending tasks. |
| `tasks show <uuid>` | Shows one task. |
| `notes new --type <T> --topic <text> --thread <Kind/Name>` | Creates a note. |
| `notes list` | Lists notes. |
| `notes cat <stem>` | Prints a note. |
| `notes last` | Prints the newest note's path. |
| `notes copy <stem>` | Copies a note. |
| `notes delete <stem> -y` | Deletes a note. |
| `notes pdf <stem>` | Renders a note to Markdown and PDF. |
| `notes minutes <stem>` | Renders meeting minutes. |
| `notes agenda <stem>` | Renders a meeting agenda. |
| `search notes` | Finds notes. |
| `search logs` | Finds logs. |
| `search activity` | Ranks threads by activity. |
| `search overview <thread>` | Shows one thread's full picture. |
| `search stream` | Shows a merged timeline. |
| `threads list` | Lists threads. |
| `threads show <thread>` | Shows a thread. |
| `threads new --name <Name> --kind <kind> --category <category>` | Creates a thread. |
| `threads delete <thread> -y` | Deletes a thread. |
| `people list` | Lists people. |
| `people show <person>` | Shows a person. |
| `people new --name <Full Name> --category <category>` | Creates a person. |
| `people delete <person> -y` | Deletes a person. |
| `hours log <thread> <description>` | Records time. |
| `hours list` | Lists time entries. |
| `hours report` | Totals time. |
| `hours show <id>` | Shows a time entry. |
| `hours edit <id>` | Changes a time entry. |
| `hours rm <id> -y` | Deletes a time entry. |
| `payments log <thread> <amount>` | Records a payment. |
| `payments list` | Lists payments. |
| `payments statement` | Shows billed versus received. |
| `payments show <id>` | Shows a payment. |
| `payments edit <id>` | Changes a payment. |
| `payments rm <id> -y` | Deletes a payment. |
| `buffer add <text>` | Captures raw text. |
| `buffer add-text <thread> <text>` | Captures an observation. |
| `buffer add-ref <thread> <target>` | Captures a pointer. |
| `buffer add-action <thread> <text>` | Captures an action. |
| `buffer list` | Shows the buffer. |
| `buffer rm <line-number>` | Removes a buffer line. |
| `buffer tend` | Regroups and validates the buffer. |
| `buffer flush` | Writes logs, clears the buffer and ingests actions. |
| `lint` | Validates the vault. |
| `commit review` | Shows uncommitted changes. |
| `commit save --message <text>` | Commits all changes. |
