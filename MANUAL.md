# adulting — Operators Manual

## Before you start

All data lives in one directory, the vault. By default the vault is `~/vault/`. Set `ADULTING_HOME` to use a different directory. Every tool reads and writes under that directory.

External programs:

| Program | Needed by |
|---|---|
| Python 3.11 or newer | every tool |
| `git` | `commit` |
| `pandoc` and a LaTeX engine (`xelatex`) | `notes pdf`, `notes minutes`, `notes agenda` |

Everything is plain text on disk: Markdown, YAML frontmatter and JSON blocks. You can read it, grep it and back it up with your own tools. There is no database.

No command prompts you or opens an app. Every value comes from arguments. Every path a command prints is absolute.

## How the pieces fit

| Object | What it is | Where it lives |
|---|---|---|
| Thread | The thing you organise by. Its kind is `project`, `process` or `topic`. | `threads/Projects/`, `threads/Processes/`, `threads/Topics/` |
| Note | A document: meeting, correspondence, report, research and similar. | `notes/<stem>.md` |
| Person | A contact you track. Used as a link target only. | `people/<name>.md` |
| Time entry | A session of work on a thread, billable or not. | `hours/<Kind>/<Thread>.md` |
| Payment | Money received against a thread. | `payments/<Kind>/<Thread>.md` |
| Log | One file per thread per day. `buffer flush` writes it. | `logs/<Kind>/<Name>/<YYYY-MM-DD>.md` |
| Buffer | The staging inbox for quick captures. | `buffer.md` |
| Action / task | An `ACTION:` line in a note or log. Ingest rewrites it in place to a `TASK:` anchor with an 8-character uuid. | inside `notes/` and `logs/` |

How they link:

- A note belongs to one or more threads. A note lists people.
- A log belongs to exactly one thread and one day.
- A task lives inside a note or log. It can name one person as assignee. It can depend on other tasks.
- Time entries and payments are filed per thread. The file path mirrors the `threads/` layout.
- A thread's `currency` and `rate` are the defaults for `hours`.
- `notes new`, `hours log` and `payments log` each add a `REF:` to the buffer. After `buffer flush`, that REF appears in the thread's daily log.
- A person is never a thread.

## Command reference

### tasks

Turns `ACTION:` lines into tracked `TASK:` anchors, and changes those anchors.

**When to use it**

- You wrote `ACTION:` lines in a note and want them tracked.
- You want to see what to do next, or what is overdue.
- You finished a task, or need to change its due date, priority, assignee or dependencies.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| *(none)* | Same as `ingest`. | `tasks` |
| `ingest` | Rewrites every valid `ACTION:` line in `notes/` and `logs/` into a `TASK:` anchor. | `tasks ingest --dry-run` |
| `add` | Adds an ACTION entry to the buffer. Same as `buffer add-action`. | `tasks add Projects/<Name> "(<Person>) <description>" --due <YYYY-MM-DD>` |
| `done` | Changes `TASK` to `DONE` and stamps today as `end`. | `tasks done <uuid>` |
| `set-description` | Rewrites the task body. | `tasks set-description <uuid> "<text>"` |
| `set-assignee` | Rewrites the `(Assignee)` prefix. | `tasks set-assignee <uuid> "<Person>"` |
| `set-due` | Sets the due date. | `tasks set-due <uuid> <YYYY-MM-DD>` |
| `set-scheduled` | Sets the scheduled date. | `tasks set-scheduled <uuid> <YYYY-MM-DD>` |
| `set-priority` | Sets priority `H`, `M` or `L`. | `tasks set-priority <uuid> H` |
| `add-depends` | Makes this task wait on another task. | `tasks add-depends <uuid> <dep-uuid>` |
| `rm-depends` | Removes a dependency. | `tasks rm-depends <uuid> <dep-uuid>` |
| `list` | Lists pending tasks, grouped by thread A–Z, then by priority, due date and entry date. | `tasks list --overdue` |
| `next` | Shows the top 5 pending tasks by priority, due date and entry date. | `tasks next` |
| `show` | Shows one task in detail. | `tasks show <uuid>` |

A `<uuid>` is the task's 8-character id from `tasks list`. Any unique prefix works.

**Options**

Global: `--dry-run` and `--quiet` apply to bare `tasks` and to `tasks ingest`.

| Option | Effect |
|---|---|
| `--dry-run` | Shows what would be ingested. Writes nothing. |
| `--quiet` | Suppresses per-action output. |
| `--due <YYYY-MM-DD>` (`add`) | Sets the due date. |
| `--scheduled <YYYY-MM-DD>` (`add`) | Sets the scheduled date. |
| `--priority H\|M\|L` (`add`, `list`) | For `add`, sets the priority. For `list`, filters by it. |
| `--depends <uuid>` (`add`) | Adds a dependency. You can repeat it. |
| `--thread <Kind/Name>` (`list`) | Shows only tasks whose source note carries this thread. |
| `--assignee <Person>` (`list`) | Shows only tasks assigned to this person. |
| `--overdue` (`list`) | Shows only tasks whose due date is before today. |
| `--json` (`list`) | Prints JSON. |

**Notes**

- Ingest rewrites source files in place. Run `tasks --dry-run` first when you are unsure.
- `done`, every `set-*`, `add-depends` and `rm-depends` rewrite the source line in its note or log. Change `TASK:` lines with these commands only. Do not edit them by hand.
- `tasks add` writes to the buffer, not to a note. The task is anchored after `buffer flush` and ingest.
- Ingest skips a file that is not valid UTF-8. `lint` reports that file.
- Exit `1`: no task matches the uuid prefix, the prefix is empty, the date is not `YYYY-MM-DD`, the person has no `people/` file, a task depends on itself, or the description is empty.

### notes

Creates, lists, prints, copies, deletes and renders notes. You name a note by its stem.

A stem is the filename without `.md`, for example `2026-09-10-14-30-00`.

**When to use it**

- You are starting a meeting record, a correspondence log or a report.
- You need to find a note's stem, or print a note.
- You need minutes, an agenda or a PDF to send to someone.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Creates a note and prints its path. | `notes new --type Meeting --topic "<topic>" --thread Projects/<Name> --person "<Person>"` |
| `list` | Lists notes, oldest first, with stem, date, type, threads and topic. | `notes list <filter>` |
| `cat` | Prints a note. | `notes cat <stem>` |
| `last` | Prints the path of the newest note. | `notes last` |
| `copy` | Copies a note to a new timestamp. The copy's topic gets ` COPY` added. | `notes copy <stem>` |
| `delete` | Deletes a note permanently. | `notes delete <stem> -y` |
| `pdf` | Renders the note to Markdown and PDF, with callouts and an action table. | `notes pdf <stem>` |
| `minutes` | Renders meeting minutes: agreements, resolutions and action items. | `notes minutes <stem>` |
| `agenda` | Renders an agenda: the note with its outcome sections emptied. | `notes agenda <stem>` |

**Options**

| Option | Effect |
|---|---|
| `--type` (`new`, required) | One of `Meeting`, `Correspondence`, `Workshop`, `Report`, `Log`, `Research`, `Recipe`. |
| `--topic` (`new`, required) | What the note is about. |
| `--thread` (`new`, required) | Thread name, `Kind/Name` or wikilink. You can repeat it. |
| `--person` (`new`) | An attendee. Meeting and Correspondence only. You can repeat it. It becomes a link when `people/<name>.md` exists. |
| `--counterparty` (`new`) | The other party. Meeting only. |
| `--location` (`new`) | Where the meeting was held. Meeting only. |
| `--json` (`list`) | Prints JSON. |
| `-y`, `--yes` (`delete`) | Required. Confirms the permanent delete. |
| `--out <DIR>` (`pdf`, `minutes`, `agenda`) | Writes the output to `<DIR>`. The default is `~/Downloads`. |

**Notes**

- Every subcommand except `new` runs task ingest first. So `list`, `cat` and the others can rewrite `ACTION:` lines in place. If an ACTION line cannot be ingested, the command carries on.
- `new` adds a `REF:` to the buffer.
- `pdf`, `minutes` and `agenda` write `<stem>.md` and `<stem>.md.pdf`. They need `pandoc` and `xelatex`.
- Exit `1`: the topic is empty, `--person`, `--counterparty` or `--location` is used on the wrong note type, the stem is malformed, no note has that stem, or the PDF render failed.

### search

Finds notes and logs, and summarises thread activity. It is read-only.

**When to use it**

- You need notes or logs for a thread, a date range or a phrase.
- You want to see which threads were busy in a period.
- You want one chronology of everything that happened, for example today.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `notes` | Finds notes by thread, type, date or text. | `search notes --thread Projects/<Name> --type Meeting` |
| `logs` | Finds daily logs by thread, date or text. | `search logs --text "<phrase>" --since <YYYY-MM-DD>` |
| `activity` | Ranks threads by what happened in a date window. | `search activity --since <YYYY-MM-DD>` |
| `overview` | Shows the whole picture of one thread. | `search overview Projects/<Name>` |
| `stream` | Merges every dated record into one chronology. | `search stream --today` |

**Options**

Global: every subcommand takes `--since <YYYY-MM-DD>`, `--until <YYYY-MM-DD>` (both inclusive) and `--json`.

| Option | Effect |
|---|---|
| `--thread <T>` (`notes`, `logs`, `activity`, `stream`) | Limits results to one thread. |
| `--type <T>` (`notes`) | Filters by note type. Case-insensitive. |
| `--text <T>` | Case-insensitive literal match. `notes` searches topic and body. `logs` searches entry lines. `stream` searches thread and summary. |
| `--limit <N>` | Sets the maximum number of results. `0` means all. Defaults: 20 for `notes` and `logs`, 5 for `overview`, 100 for `stream`. |
| `--kind <list>` (`stream`) | Comma-separated. Any of `note`, `log`, `task`, `done`, `hours`, `payment`, `thread`, `person`, `pending`. The default is all. |
| `--today` (`stream`) | Shows today only. |
| `--reverse` (`stream`) | Shows oldest first. The default is newest first. |

**Notes**

- Results are pointers: absolute paths plus metadata, not file bodies. Open a result with `notes cat` or your own reader.
- A note's date is its frontmatter `timestamp`, which is when the event happened. The filename date is used only when `timestamp` is missing or malformed.
- `search` indexes notes and logs, not the descriptions of time entries.
- Exit `1`: `--kind` contains an unknown kind.

### threads

Creates, lists, shows and deletes thread files.

**When to use it**

- You are starting a new project, process or topic.
- You need a thread's exact `Kind/Name` for another command.
- You need to check a thread's status or its billing defaults.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists threads. Shows open threads only unless you add `--all`. An optional query ranks threads by fuzzy similarity. | `threads list <query>` |
| `show` | Shows one thread file. | `threads show Projects/<Name>` |
| `new` | Creates a thread file. | `threads new --name <Name> --kind project --category professional --currency <CUR> --rate <rate>` |
| `delete` | Deletes a thread file permanently. | `threads delete Projects/<Name> -y` |

**Options**

| Option | Effect |
|---|---|
| `--all` (`list`) | Includes paused and closed threads. |
| `--json` (`list`, `show`) | Prints JSON. |
| `--name` (`new`, required) | The thread name. It becomes the filename. |
| `--kind` (`new`, required) | `project`, `process` or `topic`. Picks `threads/Projects/`, `threads/Processes/` or `threads/Topics/`. |
| `--category` (`new`, required) | `professional`, `personal` or `voluntary`. |
| `--currency` (`new`) | The default 3-letter ISO currency for `hours`. A thread with a currency is billable. |
| `--rate` (`new`) | The default hourly rate for `hours`. Needs `--currency`. |
| `-y`, `--yes` (`delete`) | Required. Confirms the permanent delete. |

**Notes**

- A name cannot contain `/` and cannot start with `.`. These rules also apply to `people`.
- `delete` refuses to run without `-y`. The same rule applies to every other delete in these tools.
- Exit `1`: the name is empty or invalid, the thread already exists, `--rate` is given without `--currency`, or `-y` is missing on delete.

### people

Creates, lists, shows and deletes person files.

**When to use it**

- Before you assign a task to someone. The assignee must have a person file.
- Before you list someone on a note, so the name becomes a link.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists people. Shows open people only unless you add `--all`. An optional query ranks people by fuzzy similarity. | `people list <query>` |
| `show` | Shows one person file. | `people show "<Full Name>"` |
| `new` | Creates a person file. | `people new --name "<Full Name>" --category professional` |
| `delete` | Deletes a person file permanently. | `people delete "<Full Name>" -y` |

**Options**

| Option | Effect |
|---|---|
| `--all` (`list`) | Includes closed people. |
| `--json` (`list`, `show`) | Prints JSON. |
| `--name` (`new`, required) | The full name. It becomes the filename. |
| `--category` (`new`, required) | `professional`, `personal` or `voluntary`. |
| `-y`, `--yes` (`delete`) | Required. Confirms the permanent delete. |

**Notes**

- Exit `1`: the name is empty or invalid, the person already exists, the person is not found, or `-y` is missing on delete.

### hours

Records time spent on a thread, billable or not.

**When to use it**

- You finished a session of client work and need it on the invoice.
- You want to track unbilled time, such as exercise or admin.
- You need totals by thread and currency for a period.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Adds an entry. | `hours log Projects/<Name> -m 90 "<description>"` |
| `list` | Lists entries, optionally for one thread. | `hours list Projects/<Name> --since <YYYY-MM-DD>` |
| `report` | Totals by thread and currency. Unbilled time gets its own total. | `hours report --thread Projects/<Name> --since <YYYY-MM-DD> --until <YYYY-MM-DD>` |
| `show` | Shows one entry. | `hours show <id>` |
| `edit` | Changes one field of an entry. | `hours edit <id> -m 120` |
| `rm` | Deletes an entry. | `hours rm <id> -y` |

An `<id>` is the entry's 8-character id from `hours list`.

**Options**

| Option | Effect |
|---|---|
| `-m`, `--minutes` (`log`, `edit`) | Duration in minutes. The default is 60. `edit` keeps the start time. |
| `-r`, `--rate` (`log`, `edit`) | Hourly rate. `0` means unbillable. Needs a currency. |
| `-c`, `--currency` (`log`, `edit`) | ISO currency code. `log` defaults to the thread's currency. With no currency at all, the entry is unbilled. |
| `-d`, `--date` (`log`, `edit`) | `YYYY-MM-DD`. The default is today. `edit` keeps the duration. |
| `-t`, `--time` (`log`, `edit`) | Start time, `HH:MM`. The default is now. `edit` keeps the duration. |
| `--description` (`edit`) | Sets a new description. |
| `--thread` (`report`) | Limits the report to one thread. |
| `--since`, `--until` (`list`, `report`) | Date window, inclusive. |
| `--json` (`list`, `report`, `show`) | Prints JSON. |
| `-y`, `--yes` (`rm`) | Required. Confirms the permanent delete. |

**Notes**

- The description is an invoice line item. Keep it short. Put the detail in a log line with `buffer add-text`.
- An entry stores its rate and currency when you write it. Changing the thread's defaults later does not re-price old entries.
- `log` adds a `REF:` to the buffer, filed under the entry's date.
- Exit `1`: minutes are not positive, a rate is given with no currency, or the description is empty.

### payments

Records money received against a thread, and compares billed with received.

**When to use it**

- A client paid you.
- You need a statement of account, as text or as a PDF.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Records a receipt. | `payments log Projects/<Name> <amount> -a "<account>"` |
| `list` | Lists payments, optionally for one thread. | `payments list Projects/<Name>` |
| `statement` | Shows billed against received, by thread and currency. | `payments statement --thread Projects/<Name> --pdf <path>.pdf` |
| `show` | Shows one payment. | `payments show <id>` |
| `edit` | Changes one field of a payment. | `payments edit <id> --amount <amount>` |
| `rm` | Deletes a payment. | `payments rm <id> -y` |

An `<id>` is the payment's 8-character id from `payments list`.

**Options**

| Option | Effect |
|---|---|
| `--amount` (`edit`) | Sets a new amount. |
| `-c`, `--currency` (`log`, `edit`) | ISO currency code. `log` defaults to the thread's currency. |
| `-d`, `--date` (`log`, `edit`) | Date received, `YYYY-MM-DD`. For `log`, the default is today. |
| `-t`, `--time` (`log`, `edit`) | Time received, `HH:MM`. For `log`, the default is now. |
| `-a`, `--account` (`log`, `edit`) | The account the money landed in. |
| `-n`, `--note` (`log`, `edit`) | A free-text note. Put it last, because it takes every word after it. |
| `--thread` (`statement`) | Limits the statement to one thread. |
| `--since`, `--until` (`list`, `statement`) | Date window, inclusive. |
| `--as-of <YYYY-MM-DD>` (`statement`) | The statement date, which drives aging. The default is today. |
| `--pdf <path>` (`statement`) | Renders a PDF to this path. Requires `--thread`. |
| `--json` (`list`, `statement`, `show`) | Prints JSON. |
| `-y`, `--yes` (`rm`) | Required. Confirms the permanent delete. |

**Notes**

- A PDF statement needs `client_name` in the thread file's frontmatter.
- The statement ignores unbilled hours.
- `log` adds a `REF:` to the buffer, filed under the date received.
- Exit `1`: the amount is missing, invalid or not positive, `--pdf` is given without `--thread`, or there is nothing to state for that thread and date.

### buffer

Manages the capture inbox at `buffer.md` and flushes it into daily logs.

**When to use it**

- You want to record something about a thread without writing a note.
- You captured raw items quickly and now need to file them.
- It is the end of the day and the buffer needs to go into `logs/`.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `add` | Adds a raw UNKNOWN entry with no thread. | `buffer add "<text>"` |
| `add-text` | Adds a TEXT observation to a thread. | `buffer add-text Projects/<Name> "<text>"` |
| `add-ref` | Adds a REF pointing at another vault file. | `buffer add-ref Projects/<Name> notes/<stem> "<summary>"` |
| `add-action` | Adds an ACTION entry. Same as `tasks add`. | `buffer add-action Projects/<Name> "(<Person>) <description>" --priority H` |
| `list` | Shows the buffer with line numbers. | `buffer list <filter>` |
| `rm` | Removes one line by its number. | `buffer rm <line-number>` |
| `tend` | Regroups entries by thread and date, then validates them. Safe to repeat. | `buffer tend` |
| `flush` | Runs `tend`, writes entries to `logs/`, then clears the buffer. | `buffer flush` |

**Options**

Global: `--quiet` goes before the subcommand and suppresses info output. Example: `buffer --quiet flush`.

| Option | Effect |
|---|---|
| `--date <YYYY-MM-DD>` (every `add*`) | Files the entry under this day instead of today. Use the day the thing happened. |
| `--due`, `--scheduled <YYYY-MM-DD>` (`add-action`) | Set on the task when it is ingested. |
| `--priority H\|M\|L` (`add-action`) | Sets the task priority. |
| `--depends <uuid>` (`add-action`) | Adds a dependency. You can repeat it. |
| `--json` (`list`) | Prints JSON. |

The `add-ref` target is one of `notes/<stem>`, `logs/<path>`, `people/<name>`, `hours/<Kind>/<Thread>`, `payments/<Kind>/<Thread>` or `<Kind>/<Thread>`.

**Notes**

- UNKNOWN entries are invalid on purpose. `tend` reports them, and `flush` will not proceed while any remain. Remove each one with `buffer rm` and add it again with `add-text`, `add-ref` or `add-action`.
- Change the buffer only through these commands. Do not edit `buffer.md` by hand.
- `flush` clears the buffer.
- Exit `1`: the line number is not an integer, is out of range or points at an empty line, or validation failed.

### lint

Checks vault files against the schemas in the Data formats section.

**When to use it**

- Before you commit.
- After you edit vault files by hand.
- When another command seems to be missing a file. It may have skipped a file that is not valid UTF-8.

**Usage**

```
lint [--schemas <dir>] [--quiet] [<path> ...]
```

| Argument | Meaning |
|---|---|
| `<path> ...` | The files to check. With no paths, `lint` checks the whole vault. |

**Options**

| Option | Effect |
|---|---|
| `--schemas <dir>` | Loads schemas from `<dir>`. |
| `--quiet` | Prints nothing. Returns the exit code only. |

**Notes**

- Each error prints as `<path>:<line>: <message>`, with an absolute path.
- A file that is not valid UTF-8 prints as `<path>:0: file is not valid UTF-8`.
- Exit `0`: no violations. Exit `1`: at least one violation. Exit `2`: no schemas were loaded.

### commit

Reviews uncommitted vault changes, then stages and commits all of them with git.

**When to use it**

- At the end of a work session, to record what changed.
- Before a risky change, so you have a point to return to.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `review` | Shows everything that changed since the last commit. Read-only. | `commit review` |
| `save` | Stages every change in the vault and commits it. | `commit save --message "<summary>" --body "<detail>"` |

**Options**

| Option | Effect |
|---|---|
| `--max-file-lines <N>` (`review`) | Maximum diff lines shown per file. The default is 150. |
| `--max-lines <N>` (`review`) | Maximum output lines overall. The default is 3000. |
| `--message` (`save`, required) | Commit subject. It must be one line. |
| `--body` (`save`) | Commit body. It may span several lines. |
| `--dry-run` (`save`) | Reports what would be staged and committed. Changes nothing. |

**Notes**

- Run `review` first, then `save`. Base the message on what `review` showed.
- `commit` runs only `git add` and `git commit`. It never amends, rebases, resets, checks out or pushes.
- `ADULTING_HOME` must be the root of a git repository.
- Exit `1`: the message is empty or has more than one line, the vault is not a git repository, `ADULTING_HOME` is not the repository root, or a git call failed.

## Everyday procedures

### 1. Set up a new billable project

1. `threads new --name <Name> --kind project --category professional --currency <CUR> --rate <rate>` creates `threads/Projects/<Name>.md` with billing defaults.
2. `people new --name "<Client Contact>" --category professional` creates the contact, so you can link it and assign tasks to it.
3. Add `client_name` to the thread file's frontmatter. You need it for PDF statements.
4. `threads show Projects/<Name>` confirms the thread.
5. `lint` confirms that the new files are valid.

### 2. Capture a meeting and turn its actions into tracked tasks

1. `notes new --type Meeting --topic "<topic>" --thread Projects/<Name> --person "<Client Contact>" --counterparty "<org>"` creates the note and prints its path.
2. Edit that file. Write each action as `ACTION: (<Person>) <description>`. Use `AGREED:`, `RESOLVED:` and `!:` lines as needed.
3. `tasks --dry-run` shows which actions will be ingested.
4. `tasks` rewrites the actions into `TASK:` anchors.
5. `tasks list --thread Projects/<Name>` shows the new tasks.
6. `notes minutes <stem>` renders the minutes to `~/Downloads`.

### 3. Quick-capture through the day, then file it

1. `buffer add "<raw thought>"` captures something with no thread.
2. `buffer list` shows every entry with its line number.
3. `buffer rm <line-number>` removes a raw entry once you know where it belongs.
4. `buffer add-text Projects/<Name> "<text>"` re-adds it as an observation. Use `buffer add-action` for a commitment.
5. `buffer tend` validates the buffer. It must report no UNKNOWN entries.
6. `buffer flush` writes the entries to `logs/` and clears the buffer.
7. `tasks` turns the flushed `ACTION:` lines into tasks.

### 4. Work the task list

1. `tasks next` shows the top five pending tasks.
2. `tasks list --overdue` shows everything past due.
3. `tasks show <uuid>` shows one task in full.
4. `tasks set-due <uuid> <YYYY-MM-DD>` moves a deadline.
5. `tasks set-priority <uuid> H` raises the priority.
6. `tasks done <uuid>` marks the task complete and stamps today as `end`.

### 5. Log a session of work

1. `hours log Projects/<Name> -m <minutes> "<short invoice label>"` records the time. Add `-d <YYYY-MM-DD>` for a past day.
2. `buffer add-text Projects/<Name> "<what actually happened>"` records the detail where `search` can find it.
3. `hours list Projects/<Name> --since <YYYY-MM-DD>` shows the entry and its id.
4. `hours edit <id> -m <minutes>` corrects the duration if needed.

### 6. Bill a client for a month's work

1. `hours list Projects/<Name> --since <YYYY-MM-01> --until <YYYY-MM-DD>` lists the line items.
2. `hours report --thread Projects/<Name> --since <YYYY-MM-01> --until <YYYY-MM-DD>` gives the totals.
3. `payments statement --thread Projects/<Name> --as-of <YYYY-MM-DD>` shows billed against received.
4. `payments statement --thread Projects/<Name> --as-of <YYYY-MM-DD> --pdf <path>.pdf` renders the statement to send.

### 7. Record a payment

1. `payments log Projects/<Name> <amount> -d <YYYY-MM-DD> -a "<account>" -n "<reference>"` records the receipt.
2. `payments list Projects/<Name>` confirms it and shows its id.
3. `payments statement --thread Projects/<Name>` shows the updated balance.

### 8. Check the vault and commit it

1. `buffer flush` files any pending captures.
2. `lint` checks every file. Fix every reported violation.
3. `commit review` shows everything that changed.
4. `commit save --message "<one-line summary>" --body "<detail>" --dry-run` shows what will be committed.
5. `commit save --message "<one-line summary>" --body "<detail>"` commits.

## Data formats

`lint` enforces every format below. The date fields use `YYYY-MM-DD` unless stated otherwise.

### `hours_file`

The time entries for one thread. Each file lives at `hours/<Kind>/<Thread>.md`. The body holds exactly one `simple-time-tracker` fenced block. That block contains JSON of the form `{"entries": [...]}`. `hours` writes these files.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to an existing `Projects/`, `Processes/` or `Topics/` thread. |
| `currency` | no | 3-letter ISO code. Omitted for unbilled threads. |
| `entries[].name` | yes | The description. It appears as the invoice line item. |
| `entries[].startTime` | yes | ISO 8601 UTC, `YYYY-MM-DDTHH:MM:SS.mmmZ`. |
| `entries[].endTime` | yes | Same format as `startTime`. Must not be before `startTime`. Duration is `endTime` minus `startTime`. |
| `entries[].id` | yes | 8 hex characters. Unique across hours entries and payments. |
| `entries[].rate` | yes | Integer hourly charge. `0` means unbillable. |
| `entries[].currency` | no | ISO 4217 code. Absent or null means unbilled. |

### `log`

One thread's activity for one day. Each file lives at `logs/<Kind>/<Name>/<YYYY-MM-DD>.md`. `buffer flush` writes these files. Each body line is `TEXT:`, `REF:`, `ACTION:`, `TASK:` or `DONE:`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to a `Projects/`, `Processes/` or `Topics/` thread. |
| `date` | yes | The day the log covers. |
| `type` | yes | Always `Log`. |

### `note_correspondence`

A note recording email, message or letter exchanges. Files live at `notes/<YYYY-MM-DD-HH-MM-SS>.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about. |
| `type` | yes | `Correspondence`. |
| `threads` | yes | A list of thread wikilinks. Each must resolve to a thread file. |
| `timestamp` | yes | `YYYY-MM-DD-HH-MM-SS`. When the exchange happened. |
| `people` | no | A list. Each entry is a `[[people/<name>]]` link, which must resolve, or plain text. |

Body markers: `ACTION:`, `TASK:`, `AGREED:` and `RESOLVED:` appear in minutes. `!:` callouts appear in the PDF.

### `note_meeting`

A note recording a meeting. Files live at `notes/<YYYY-MM-DD-HH-MM-SS>.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the meeting was about. |
| `type` | yes | `Meeting`. |
| `threads` | yes | A list of thread wikilinks. Each must resolve to a thread file. |
| `timestamp` | yes | `YYYY-MM-DD-HH-MM-SS`. When the meeting happened. |
| `counterparty` | no | The other party. |
| `location` | no | Where the meeting was held. |
| `people` | no | A list. Each entry is a `[[people/<name>]]` link, which must resolve, or plain text. |

Body markers: the same as `note_correspondence`.

### `note_simple`

A note of type `Workshop`, `Report`, `Log`, `Research` or `Recipe`. Files live at `notes/<YYYY-MM-DD-HH-MM-SS>.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about. |
| `type` | yes | One of `Workshop`, `Report`, `Log`, `Research`, `Recipe`. |
| `threads` | yes | A list of thread wikilinks. Each must resolve to a thread file. |
| `timestamp` | yes | `YYYY-MM-DD-HH-MM-SS`. When the event happened. |
| `people` | no | A list. Each entry is a `[[people/<name>]]` link or plain text. |

Body markers: the same as `note_correspondence`.

### `payments_file`

The money received against one thread. Each file lives at `payments/<Kind>/<Thread>.md`. The body holds exactly one `adulting-payments` fenced block. That block contains JSON of the form `{"payments": [...]}`. `payments` writes these files.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to an existing `Projects/`, `Processes/` or `Topics/` thread. |
| `currency` | yes | 3-letter ISO code. |
| `payments[].id` | yes | 8 hex characters. Unique across payments and hours entries. |
| `payments[].received` | yes | ISO 8601 UTC, `YYYY-MM-DDTHH:MM:SS.mmmZ`. When the money landed. |
| `payments[].amount` | yes | A number greater than 0. |
| `payments[].currency` | yes | ISO 4217 code. |
| `payments[].account` | no | The account the money landed in. |
| `payments[].note` | no | Free text. |

### `person`

Someone you track. Files live at `people/<name>.md`. The body is free-form.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | When tracking began. |
| `ended` | no | When tracking ended. Required when `status` is `closed`. |
| `cadences` | no | A list of `{key, frequency, description}` objects. See `thread`. |

### `task_anchor`

A single `TASK:` or `DONE:` line in a note or log. It is the only record of a task's state. Only `tasks` writes or changes it.

```
TASK: [#H] (Riaz Arbi) Send quarterly report <!--abcd1234 entry:2026-05-27 due:2026-05-29-->
DONE: [#M] (Charlie) Review the contract <!--abc12340 entry:2026-05-24 end:2026-05-27-->
```

| Field | Required | Meaning |
|---|---|---|
| `kind` | yes | `TASK` (pending) or `DONE`. |
| `priority` | no | `H`, `M` or `L`, written as `[#X]` in the visible text. |
| `assignee` | no | A person in parentheses. Must resolve to `people/<name>.md`. |
| `body` | yes | The task description. |
| `uuid` | yes | 8 hex characters. Unique across the vault. |
| `entry` | yes | The date the task was ingested. |
| `end` | no | The completion date. Required for `DONE`. Must not be before `entry`. |
| `due` | no | The due date. |
| `scheduled` | no | The scheduled date. |
| `depends` | no | Comma-separated uuids of other tasks. Each must exist, and the dependencies must not form a loop. |

The comment attributes always appear in this order: `entry`, `end`, `due`, `scheduled`, `depends`.

### `thread`

A project, process or topic. Files live at `threads/<Projects|Processes|Topics>/<Name>.md`.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `kind` | yes | `project`, `process` or `topic`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | When the thread began. |
| `ended` | no | When the thread ended. Required when `status` is `closed`. |
| `cadences` | no | Recurring obligations. Each item has `key` (unique in the thread), `frequency` (interval in days) and `description`. A log entry tagged `#<key>` satisfies the cadence. |
| `currency` | no | Default 3-letter ISO currency for `hours`. Makes the thread billable. |
| `rate` | no | Default hourly rate, an integer. |
| `client_name` | no | The party billed. Required for `payments statement --pdf`. |
| `client_address` | no | The billing address, with lines separated by `\|`. |
| `client_vat` | no | The client's VAT number. |
| `client_email` | no | The client's email. |

Body lines of the form `- YYYY-MM-DD — <text>` must follow `thread_entry`.

### `thread_entry`

A dated top-level bullet in a thread file's body: `- YYYY-MM-DD — <text>`. `lint` does not check indented sub-bullets under it.

| Field | Required | Meaning |
|---|---|---|
| `date` | yes | The day of the entry. |
| `text` | yes | What happened. Must not be empty. |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `buffer flush` or `buffer tend` reports violations | The buffer still holds UNKNOWN entries from `buffer add`. | Run `buffer list`, then `buffer rm <line-number>`. Re-add each entry with `buffer add-text`, `add-ref` or `add-action`. |
| `refusing to delete ... without -y` | Every delete needs explicit confirmation. | Add `-y`. |
| `--rate needs a currency` from `hours` | You gave a rate, but neither the command nor the thread has a currency. | Pass `-c <CUR>`, or omit `-r` to record the time as unbilled. |
| `--rate needs a --currency` from `threads new` | You gave `--rate` without `--currency`. | Add `--currency <CUR>`. |
| `amount is required`, `amount must be positive` or `... is not a valid amount` | The payment amount is missing, zero, negative or not a number. | Pass a positive number as the amount. |
| `--pdf needs --thread; a statement is per client` | A PDF statement covers one thread only. | Add `--thread <Kind/Name>`. |
| `nothing to state for ... as at ...` | The thread has nothing to state for that date. | Check the thread name and `--as-of`. |
| `no task found with uuid prefix ...` | No task matches the prefix. | Run `tasks list` and copy the uuid. |
| `person ... does not resolve to people/<name>.md` | The assignee has no person file. | Run `people new --name "<name>" --category <category>`. |
| `--person is only for Meeting and Correspondence notes` or `--counterparty and --location are only for Meeting notes` | The option does not fit the note type. | Drop the option or change `--type`. |
| `PDF render failed` | `notes pdf`, `minutes` or `agenda` could not render the PDF. | Install `pandoc` and `xelatex`, then retry. |
| `not a git repository` or `ADULTING_HOME ... is not the root of its git repository` | `commit` needs the vault to be the root of a git repository. | Point `ADULTING_HOME` at the repository root. |
| A file is missing from listings, and `lint` reports `file is not valid UTF-8` | Commands skip files that are not valid UTF-8. | Re-save the file as UTF-8, or remove it. |
| `lint` exits `2` with `no schemas loaded` | The schemas directory is wrong or empty. | Fix the `--schemas <dir>` path, or drop the option. |

## Quick reference

| Command | Does |
|---|---|
| `tasks` | Turns ACTION lines into TASK anchors. |
| `tasks ingest` | Same as bare `tasks`. |
| `tasks add` | Adds an ACTION entry to the buffer. |
| `tasks done` | Marks a task complete. |
| `tasks set-description` | Rewrites a task's body. |
| `tasks set-assignee` | Changes a task's assignee. |
| `tasks set-due` | Sets a task's due date. |
| `tasks set-scheduled` | Sets a task's scheduled date. |
| `tasks set-priority` | Sets a task's priority. |
| `tasks add-depends` | Adds a dependency to a task. |
| `tasks rm-depends` | Removes a dependency from a task. |
| `tasks list` | Lists pending tasks. |
| `tasks next` | Shows the top 5 pending tasks. |
| `tasks show` | Shows one task. |
| `notes new` | Creates a note. |
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
| `search stream` | Shows a merged chronology. |
| `threads list` | Lists threads. |
| `threads show` | Shows a thread. |
| `threads new` | Creates a thread. |
| `threads delete` | Deletes a thread permanently. |
| `people list` | Lists people. |
| `people show` | Shows a person. |
| `people new` | Creates a person. |
| `people delete` | Deletes a person permanently. |
| `hours log` | Records a time entry. |
| `hours list` | Lists time entries. |
| `hours report` | Totals time by thread and currency. |
| `hours show` | Shows one time entry. |
| `hours edit` | Changes a time entry. |
| `hours rm` | Deletes a time entry. |
| `payments log` | Records a payment. |
| `payments list` | Lists payments. |
| `payments statement` | Shows billed against received. |
| `payments show` | Shows one payment. |
| `payments edit` | Changes a payment. |
| `payments rm` | Deletes a payment. |
| `buffer add` | Captures a raw UNKNOWN entry. |
| `buffer add-text` | Captures an observation. |
| `buffer add-ref` | Captures a pointer to a vault file. |
| `buffer add-action` | Captures an action. |
| `buffer list` | Shows the buffer with line numbers. |
| `buffer rm` | Removes a buffer line. |
| `buffer tend` | Regroups and validates the buffer. |
| `buffer flush` | Writes the buffer to logs and clears it. |
| `lint` | Checks files against the schemas. |
| `commit review` | Shows uncommitted changes. |
| `commit save` | Stages and commits all changes. |
