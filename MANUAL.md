# adulting — Operators Manual

## Before you start

All data lives in one vault directory. The default is `~/vault/`. Set `ADULTING_HOME` to use a different directory:

```
export ADULTING_HOME=<path-to-vault>
```

You need these programs:

| Program | Needed by |
|---|---|
| Python 3.11 or newer | every tool |
| `git` | `commit` |
| `pandoc` and a LaTeX engine (`xelatex`) | `notes pdf`, `notes minutes`, `notes agenda` |

Everything is stored as plain text files on disk: Markdown, YAML frontmatter and JSON. You can read, grep and back up the vault with your own tools. The `commit` tool needs the vault to be the root of its own git repository.

## How the pieces fit

| Object | What it is | Where it lives |
|---|---|---|
| Note | A document: a meeting, correspondence, report, research, recipe and so on. | `notes/<stem>.md` |
| Thread | Something that notes, logs, time and money are filed against. It is a `project`, `process` or `topic`. | `threads/{Projects,Processes,Topics}/<Name>.md` |
| Person | A contact you track. Other files link to a person. A person is never a thread. | `people/<Full Name>.md` |
| Log | One file per thread per day. `buffer flush` writes it. | `logs/<Kind>/<Name>/<YYYY-MM-DD>.md` |
| Buffer | The inbox where you capture lines before they are filed into logs. | `buffer.md` |
| Time entry | A session of work on a thread, billable or not. | `hours/<Kind>/<Thread>.md` |
| Payment | Money received against a thread. | `payments/<Kind>/<Thread>.md` |
| Action / task | An `ACTION:` line in a note or log. `tasks` rewrites it in place as a `TASK:` anchor, which becomes `DONE:` when finished. | Inside `notes/` and `logs/` files |

How they link:

- A note belongs to one or more threads. It can list people.
- A log belongs to exactly one thread and one day.
- A task's assignee must be a person with a file in `people/`.
- A task can depend on other tasks, by uuid.
- Time entries and payments are filed per thread. Their files mirror the `threads/` layout.
- `notes new`, `hours log` and `payments log` each add a `REF:` line to the buffer. After `buffer flush`, that line appears in the thread's log for the day the event happened.
- A thread's `currency` and `rate` are the defaults for billing. `payments statement` compares billed hours with payments received.

## Command reference

No command prompts for input or opens an app. Every value comes from arguments. Every delete needs `-y`.

### tasks

Turns `ACTION:` lines into tracked `TASK:` anchors and changes those anchors in place.

**When to use it**

- You have written `ACTION:` lines in notes, or flushed them into logs, and want them tracked.
- You want to see what to do next, or what is overdue.
- You finished a task or need to change its date, priority, assignee or dependencies.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| *(none)* | Same as `ingest`. | `tasks` |
| `ingest` | Rewrites every `ACTION:` line in `notes/` and `logs/` as a `TASK:` anchor with a new 8-character uuid. | `tasks ingest --dry-run` |
| `add` | Adds an `ACTION` to the buffer. It is the same as `buffer add-action`. | `tasks add Projects/<Name> "(<Full Name>) <description>" --due <YYYY-MM-DD>` |
| `done` | Changes `TASK` to `DONE` and stamps `end:` with today's date. | `tasks done <uuid>` |
| `set-description` | Replaces the task text. | `tasks set-description <uuid> "<new text>"` |
| `set-assignee` | Replaces the `(Assignee)` prefix. | `tasks set-assignee <uuid> "<Full Name>"` |
| `set-due` | Sets the due date. | `tasks set-due <uuid> <YYYY-MM-DD>` |
| `set-scheduled` | Sets the scheduled date. | `tasks set-scheduled <uuid> <YYYY-MM-DD>` |
| `set-priority` | Sets the priority, written as `[#H]`, `[#M]` or `[#L]`. | `tasks set-priority <uuid> H` |
| `add-depends` | Makes this task wait on another task. | `tasks add-depends <uuid> <dep-uuid>` |
| `rm-depends` | Removes a dependency. | `tasks rm-depends <uuid> <dep-uuid>` |
| `list` | Lists pending tasks, grouped by thread. | `tasks list --overdue` |
| `next` | Shows the top 5 pending tasks, sorted by priority, then due date, then entry date. | `tasks next` |
| `show` | Shows the detail of one task. | `tasks show <uuid>` |

**Options**

Global: `--dry-run` and `--quiet` apply to bare `tasks` and to `tasks ingest`.

| Option | Effect |
|---|---|
| `--dry-run` | Shows what would be ingested and writes nothing. |
| `--quiet` | Hides the output for each action. |
| `--due <YYYY-MM-DD>` | `add`: sets the due date. |
| `--scheduled <YYYY-MM-DD>` | `add`: sets the scheduled date. |
| `--priority <H\|M\|L>` | `add`: sets the priority. `list`: shows only this priority. |
| `--depends <uuid>` | `add`: waits on this task. You can repeat it. |
| `--thread <Kind/Name>` | `list`: shows only tasks whose source note carries this thread. |
| `--assignee <person>` | `list`: shows only tasks assigned to this person. |
| `--overdue` | `list`: shows only tasks whose due date is before today. |
| `--json` | `list`: prints JSON. |

**Notes**

- `ingest` and every `set-*`, `done` and `*-depends` subcommand rewrite source files in `notes/` and `logs/` in place.
- A uuid argument accepts any unique prefix. Get uuids from `tasks list`.
- Exit `1` means one of these: no task matches the prefix, the prefix is empty, the date is not `YYYY-MM-DD`, the description is empty, a task would depend on itself, or the person has no `people/<person>.md` file.

### notes

Creates, lists, prints, copies, deletes and renders notes. Each note is named by its stem.

**When to use it**

- You need a new meeting, correspondence, report or other note.
- You want to find a note, or print one.
- You want minutes, an agenda or a PDF of a note.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Creates a note and prints its path. | `notes new --type Report --topic "<topic>" --thread Projects/<Name>` |
| `list` | Lists notes, oldest first, showing stem, date, type, threads and topic. | `notes list <filter>` |
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
| `--type <type>` | `new`, required. One of `Meeting`, `Correspondence`, `Workshop`, `Report`, `Log`, `Research`, `Recipe`. |
| `--topic <text>` | `new`, required. What the note is about. |
| `--thread <Kind/Name>` | `new`, required. You can repeat it. |
| `--person <Full Name>` | `new`, for Meeting and Correspondence only. An attendee. You can repeat it. It becomes a link when `people/<name>.md` exists. |
| `--counterparty <text>` | `new`, for Meeting only. The other party. |
| `--location <text>` | `new`, for Meeting only. Where the meeting was held. |
| `--json` | `list`: prints JSON. |
| `-y`, `--yes` | `delete`, required. Confirms the delete. |
| `--out <DIR>` | `pdf`, `minutes`, `agenda`: sets the output directory. The default is `~/Downloads`. |

**Notes**

- A stem is the filename without `.md`, for example `2026-09-10-14-30-00`.
- Every subcommand except `new` runs a task ingest first. This rewrites `ACTION:` lines into `TASK:` anchors in source files. If an ACTION line fails to ingest, the command still continues.
- Renders write `<stem>.md` and `<stem>.md.pdf`.
- `delete` cannot be undone.
- Exit `1` means one of these: a bad stem, no such note, an empty topic, an option used on the wrong note type, or a failed PDF render.

### search

Finds notes and logs, and summarises activity. It is read-only.

**When to use it**

- You want notes or logs for a thread, a type, a date range or some text.
- You want to know which threads were active in a period.
- You want everything about one thread, or one timeline across the whole vault.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `notes` | Finds notes by thread, type, date or text. | `search notes --thread Projects/<Name> --type Meeting` |
| `logs` | Finds daily logs by thread, date or text. | `search logs --text "<words>" --since <YYYY-MM-DD>` |
| `activity` | Ranks threads by what happened in a date range. | `search activity --since <YYYY-MM-DD>` |
| `overview` | Shows the whole picture of one thread. | `search overview Projects/<Name>` |
| `stream` | Merges every dated record into one timeline. | `search stream --today` |

**Options**

Global: every subcommand accepts `--since <YYYY-MM-DD>`, `--until <YYYY-MM-DD>` and `--json`.

| Option | Effect |
|---|---|
| `--thread <Kind/Name>` | Shows only this thread. |
| `--type <type>` | `notes`: filters by note type. Case does not matter. |
| `--text <text>` | Matches literal text, ignoring case. `notes` searches topic and body. `logs` searches entry lines. `stream` searches thread and summary. |
| `--limit <n>` | Sets the maximum number of results. `0` means all. The default is 20 for `notes` and `logs`, 5 for `overview` and 100 for `stream`. |
| `--kind <list>` | `stream`: a comma-separated list from `note`, `log`, `task`, `done`, `hours`, `payment`, `thread`, `person`, `pending`. The default is all. |
| `--today` | `stream`: shows today only. |
| `--reverse` | `stream`: shows oldest first. The default is newest first. |

**Notes**

- Results are absolute file paths plus metadata. Search never returns note or log bodies.
- Dates are the date of the event, taken from the note's `timestamp`. The filename date is used only when `timestamp` is missing or malformed.
- Search indexes notes and logs. It does not search the text of time entries.
- Exit `1` means `--kind` contains an unknown kind.

### threads

Creates, lists, shows and deletes thread files.

**When to use it**

- You are starting a new project, process or topic.
- You need the exact name of a thread for another command.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists thread files. It shows open threads unless you add `--all`. | `threads list <query>` |
| `show` | Shows one thread file. | `threads show Projects/<Name>` |
| `new` | Creates a thread file. | `threads new --name <Name> --kind project --category professional` |
| `delete` | Deletes a thread file permanently. | `threads delete Projects/<Name> -y` |

**Options**

| Option | Effect |
|---|---|
| `--all` | `list`: also shows paused and closed threads. |
| `--json` | `list`, `show`: prints JSON. |
| `--name <Name>` | `new`, required. Becomes the filename. It cannot contain `/` or start with `.`. |
| `--kind <kind>` | `new`, required. One of `project`, `process`, `topic`. Sets the directory. |
| `--category <category>` | `new`, required. One of `professional`, `personal`, `voluntary`. |
| `--currency <ISO>` | `new`: the default currency for `hours`. Setting it makes the thread billable. |
| `--rate <n>` | `new`: the default hourly rate for `hours`. It needs `--currency`. |
| `-y`, `--yes` | `delete`, required. |

**Notes**

- `list <query>` is a fuzzy search. Results are ranked by similarity.
- Exit `1` means one of these: an empty or invalid name, the thread already exists, `--rate` was given without `--currency`, or `delete` was run without `-y`.

### people

Creates, lists, shows and deletes person files.

**When to use it**

- Before you assign a task to someone, or link them from a note.
- You need a person's exact filename.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists person files. It shows open people unless you add `--all`. | `people list <query>` |
| `show` | Shows one person file. | `people show "<Full Name>"` |
| `new` | Creates a person file. | `people new --name "<Full Name>" --category professional` |
| `delete` | Deletes a person file permanently. | `people delete "<Full Name>" -y` |

**Options**

| Option | Effect |
|---|---|
| `--all` | `list`: also shows closed people. |
| `--json` | `list`, `show`: prints JSON. |
| `--name <Full Name>` | `new`, required. Becomes the filename. It cannot contain `/` or start with `.`. |
| `--category <category>` | `new`, required. One of `professional`, `personal`, `voluntary`. |
| `-y`, `--yes` | `delete`, required. |

**Notes**

- Exit `1` means one of these: an empty or invalid name, the person already exists, the person was not found, or `delete` was run without `-y`.

### hours

Records time spent on a thread, billable or not.

**When to use it**

- You finished a session of work, for a client or for yourself.
- You need totals before you bill a client.
- You need to correct or remove an entry.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Adds an entry. | `hours log -m 90 Projects/<Name> "<short label>"` |
| `list` | Lists entries. | `hours list Projects/<Name> --since <YYYY-MM-DD>` |
| `report` | Totals time by thread and currency. Unbilled time is totalled separately. | `hours report --since <YYYY-MM-DD> --until <YYYY-MM-DD>` |
| `show` | Shows one entry. | `hours show <id>` |
| `edit` | Changes one field of an entry. | `hours edit <id> -m 45` |
| `rm` | Deletes an entry. | `hours rm <id> -y` |

**Options**

| Option | Effect |
|---|---|
| `-m`, `--minutes <n>` | `log`: the duration. The default is 60. `edit`: a new duration; the start time does not move. |
| `-r`, `--rate <n>` | `log`, `edit`: the hourly rate. `0` means unbillable. It needs a currency. |
| `-c`, `--currency <ISO>` | `log`: defaults to the thread's currency. With no currency from either source, the entry is unbilled. `edit`: sets a new currency. |
| `-d`, `--date <YYYY-MM-DD>` | `log`: the default is today. `edit`: moves the entry to this day and keeps its duration. |
| `-t`, `--time <HH:MM>` | `log`: the default is now. `edit`: moves the start time and keeps the duration. |
| `--description <text>` | `edit`: sets a new description. |
| `--thread <Kind/Name>` | `report`: shows only this thread. |
| `--since`, `--until <YYYY-MM-DD>` | `list`, `report`: sets the date range. |
| `--json` | `list`, `report`, `show`: prints JSON. |
| `-y`, `--yes` | `rm`, required. |

**Notes**

- Put options before the thread in `hours log`. For example, `hours log -m 90 Projects/<Name> "<label>"`.
- The description is required. It appears as an invoice line item, so keep it short. Record the detail with `buffer add-text` instead, because search does not look inside time entries.
- Each `log` adds a `REF:` to the buffer. It is filed under the day the work happened.
- Get an entry's 8-character id from `hours list`.
- Exit `1` means one of these: an empty description, minutes that are not positive, or a rate given without a currency.

### payments

Records money received against a thread and compares billed amounts with received amounts.

**When to use it**

- A client paid you.
- You need a statement of account, as text or as a PDF.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Records a payment received. | `payments log -c <ISO> Projects/<Name> <amount>` |
| `list` | Lists payments. | `payments list Projects/<Name>` |
| `statement` | Shows billed against received, by thread and currency. | `payments statement --thread Projects/<Name>` |
| `show` | Shows one payment. | `payments show <id>` |
| `edit` | Changes one field of a payment. | `payments edit <id> --amount <amount>` |
| `rm` | Deletes a payment. | `payments rm <id> -y` |

**Options**

| Option | Effect |
|---|---|
| `-c`, `--currency <ISO>` | `log`: defaults to the thread's currency. `edit`: sets a new currency. |
| `-d`, `--date <YYYY-MM-DD>` | `log`, `edit`: the date received. The default is today. |
| `-t`, `--time <HH:MM>` | `log`, `edit`: the time received. The default is now. |
| `-a`, `--account <text>` | `log`, `edit`: the account the money landed in. |
| `-n`, `--note <text>` | `log`, `edit`: a free-text note. |
| `--amount <amount>` | `edit`: sets a new amount. |
| `--thread <Kind/Name>` | `statement`: shows only this thread. |
| `--since`, `--until <YYYY-MM-DD>` | `list`, `statement`: sets the date range. |
| `--as-of <YYYY-MM-DD>` | `statement`: the statement date, which drives aging. The default is today. |
| `--pdf <path>` | `statement`: renders a PDF to this path. It needs `--thread`. |
| `--json` | `list`, `statement`, `show`: prints JSON. |
| `-y`, `--yes` | `rm`, required. |

**Notes**

- Put options before the thread in `payments log`. Put `-n` last, because it takes every word after it.
- The amount is required and must be positive. Every payment needs a currency.
- `statement --pdf` needs `client_name` in the thread file's frontmatter.
- Each `log` adds a `REF:` to the buffer. It is filed under the day the money was received.
- Exit `1` means one of these: the amount is missing, invalid or not positive, `--pdf` was given without `--thread`, or there is nothing to state for that thread and date.

### buffer

Captures lines into `buffer.md`, checks them, and files them into daily logs.

**When to use it**

- You want to capture something now and file it later.
- You want to record an observation, a pointer or an action against a thread.
- It is the end of the day and the buffer needs filing.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `add` | Adds a raw `UNKNOWN` line. It blocks `flush` until you replace it. | `buffer add "<raw text>"` |
| `add-text` | Adds a `TEXT` observation. | `buffer add-text Projects/<Name> "<observation>"` |
| `add-ref` | Adds a `REF` pointer to another vault file. | `buffer add-ref Projects/<Name> notes/<stem> "<summary>"` |
| `add-action` | Adds an `ACTION`. It is the same as `tasks add`. | `buffer add-action Projects/<Name> "(<Full Name>) <description>" --priority H` |
| `list` | Shows the buffer with line numbers. | `buffer list` |
| `rm` | Removes one line by its number. | `buffer rm <line-number>` |
| `tend` | Regroups lines by thread and date, then validates them. It is safe to repeat. | `buffer tend` |
| `flush` | Runs `tend`, writes lines to `logs/`, and clears the buffer. | `buffer flush` |

**Options**

Global: `--quiet` hides info output.

| Option | Effect |
|---|---|
| `--date <YYYY-MM-DD>` | Every `add*` subcommand: files the line under this day. Use the day the thing happened. |
| `--due`, `--scheduled <YYYY-MM-DD>` | `add-action`: dates that are applied when the task is ingested. |
| `--priority <H\|M\|L>` | `add-action`: sets the priority. |
| `--depends <uuid>` | `add-action`: waits on this task. You can repeat it. |
| `--json` | `list`: prints JSON. |

**Notes**

- Change `buffer.md` only through these commands. Do not edit it by hand.
- `add-ref` accepts these targets: `notes/<stem>`, `logs/<path>`, `people/<name>`, `hours/<Kind>/<Thread>`, `payments/<Kind>/<Thread>` or `<Kind>/<Thread>`.
- `tend` regroups lines, which can change their numbers. Take the number for `rm` from a fresh `buffer list`.
- `flush` does not create tasks. Run `tasks` afterwards to turn the flushed `ACTION:` lines into anchors.
- Exit `1` means one of these: the line number is bad, empty or out of range, or validation failed.

### lint

Checks vault files against the schemas in [Data formats](#data-formats).

**When to use it**

- Before you commit.
- After you edit any vault file by hand.

**Usage**

```
lint [--schemas <dir>] [--quiet] [<path> ...]
```

| Argument | Effect |
|---|---|
| `<path> ...` | Checks only these files. With no paths, it checks the whole vault. |
| `--schemas <dir>` | Uses a different directory of schemas. |
| `--quiet` | Prints nothing. Only the exit code reports the result. |

**Notes**

- Errors print as `<path>:<line>: <message>`.
- Exit `0` means the files are clean. Exit `1` means there are violations. Exit `2` means no schemas were loaded.

### commit

Reviews changes to the vault, then commits them to git.

**When to use it**

- At the end of a work session.
- After a large batch of edits.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `review` | Shows everything that changed since the last commit. It is read-only. | `commit review` |
| `save` | Stages every change in the vault and commits it. | `commit save --message "<one-line summary>"` |

**Options**

| Option | Effect |
|---|---|
| `--max-file-lines <n>` | `review`: the maximum diff lines shown per file. The default is 150. |
| `--max-lines <n>` | `review`: the maximum lines of output overall. The default is 3000. |
| `--message <text>` | `save`, required. The commit subject. It must be one line and not empty. |
| `--body <text>` | `save`: the commit body. It can span several lines. |
| `--dry-run` | `save`: reports what would be committed and changes nothing. |

**Notes**

- `save` only adds a commit. It never amends, rebases, resets, checks out or pushes.
- Exit `1` means one of these: the vault is not a git repository, `ADULTING_HOME` is not the root of its repository, the message is bad, or a git command failed.

## Everyday procedures

### 1. Set up a new billable project

1. `people new --name "<Full Name>" --category professional` creates the client contact.
2. `threads new --name <Name> --kind project --category professional --currency <ISO> --rate <rate>` creates the billable thread.
3. `threads show Projects/<Name>` confirms the thread file.
4. `lint` checks that the new files are valid.

### 2. Capture a meeting and turn its actions into tracked tasks

1. `notes new --type Meeting --topic "<topic>" --thread Projects/<Name> --person "<Full Name>" --counterparty "<party>" --location "<place>"` creates the note and prints its path.
2. Open that path in your editor. Add the notes, and one `ACTION: (<Full Name>) <description>` line for each action.
3. `tasks ingest --dry-run` previews the tasks that will be created.
4. `tasks ingest` rewrites the ACTION lines as TASK anchors.
5. `tasks list --thread Projects/<Name>` shows the new tasks.
6. `notes minutes <stem>` renders the minutes to `~/Downloads`.

### 3. Quick-capture through the day, then file it

1. `buffer add "<raw text>"` captures something before you know which thread it belongs to.
2. `buffer add-text Projects/<Name> "<observation>"` captures an observation against a thread.
3. `buffer list` shows the lines and their numbers, including `UNKNOWN` lines.
4. `buffer rm <line-number>` removes an `UNKNOWN` line.
5. `buffer add-action Projects/<Name> "(<Full Name>) <description>" --due <YYYY-MM-DD>` re-adds that line in its proper form.
6. `buffer tend` validates the buffer. Fix anything it reports.
7. `buffer flush` writes the lines to `logs/` and clears the buffer.
8. `tasks` turns the flushed ACTION lines into TASK anchors.

### 4. Work the task list

1. `tasks next` shows your top 5 tasks.
2. `tasks list --overdue` shows tasks that are past due.
3. `tasks show <uuid>` shows the detail of one task.
4. `tasks set-due <uuid> <YYYY-MM-DD>` changes a due date.
5. `tasks set-priority <uuid> H` raises the priority.
6. `tasks add-depends <uuid> <dep-uuid>` marks a task that is blocked by another.
7. `tasks done <uuid>` marks a task complete.

### 5. Log a session of work

1. `hours log -m <minutes> Projects/<Name> "<short label>"` records the time with a short invoice label.
2. `buffer add-text Projects/<Name> "<what actually happened>"` records the detail where search can find it.
3. `hours list Projects/<Name> --since <YYYY-MM-DD>` checks the entry and shows its id.
4. `hours edit <id> -m <minutes>` corrects the duration if needed.
5. `buffer flush` files the time pointer and the observation into the day's log.

### 6. Bill a client for a month's work

1. `hours report --thread Projects/<Name> --since <YYYY-MM-DD> --until <YYYY-MM-DD>` shows the month's totals.
2. `hours list Projects/<Name> --since <YYYY-MM-DD> --until <YYYY-MM-DD>` shows the line items.
3. `payments statement --thread Projects/<Name> --as-of <YYYY-MM-DD>` shows billed against received.
4. `payments statement --thread Projects/<Name> --as-of <YYYY-MM-DD> --pdf <path>.pdf` renders the statement as a PDF. The thread file must have `client_name`.

### 7. Record a payment

1. `payments log -d <YYYY-MM-DD> -a "<account>" Projects/<Name> <amount> -n "<note>"` records the money received.
2. `payments list Projects/<Name>` checks the record and shows its id.
3. `payments edit <id> --amount <amount>` corrects the amount if needed.
4. `payments statement --thread Projects/<Name>` shows the updated balance.
5. `buffer flush` files the payment pointer into the day's log.

### 8. Check the vault and commit it

1. `buffer tend` validates the buffer.
2. `lint` validates the whole vault. Fix any `<path>:<line>` errors.
3. `commit review` shows what changed.
4. `commit save --message "<one-line summary>" --dry-run` previews the commit.
5. `commit save --message "<one-line summary>" --body "<detail>"` commits the changes.

## Data formats

`lint` enforces every schema below. Dates are `YYYY-MM-DD` unless a field says otherwise.

### `hours_file`

Time entries for one thread. The files live at `hours/{Projects,Processes,Topics}/<Thread>.md`. The body holds exactly one `simple-time-tracker` fenced block. That block contains JSON of the form `{"entries": [...]}`.

Frontmatter:

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Link to an existing thread under `Projects/`, `Processes/` or `Topics/`. |
| `currency` | no | Three-letter ISO code. Leave it out for unbilled threads. |

Each entry:

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | The description. It appears as an invoice line item. |
| `startTime` | yes | UTC time, `YYYY-MM-DDTHH:MM:SS.mmmZ`. |
| `endTime` | yes | Same form. It must not be earlier than `startTime`. Duration is `endTime` minus `startTime`. |
| `id` | yes | 8 hex characters, unique across all hours and payments. |
| `rate` | yes | Integer charge per hour. `0` means unbillable. |
| `currency` | no | Three-letter ISO code. If it is missing or null, the entry is unbilled. |

### `log`

One thread's activity for one day, written by `buffer flush`. The files live at `logs/<Kind>/<Name>/<YYYY-MM-DD>.md`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Link to a thread under `Projects/`, `Processes/` or `Topics/`. |
| `date` | yes | The day the log covers. |
| `type` | yes | Always `Log`. |

Body lines start with `TEXT:`, `REF:`, `ACTION:`, `TASK:` or `DONE:`.

### `note_correspondence`

A note about an exchange of emails, messages or letters. The files live in `notes/`, named `<YYYY-MM-DD-HH-MM-SS>.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about. |
| `type` | yes | Always `Correspondence`. |
| `threads` | yes | List of links to existing threads. |
| `timestamp` | yes | When the exchange happened, `YYYY-MM-DD-HH-MM-SS`. |
| `people` | no | List of `[[people/X]]` links, which must resolve, or plain names. |

Body markers: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:` and `!:`, which marks a callout.

### `note_meeting`

A note about a meeting. The files live in `notes/`, named `<YYYY-MM-DD-HH-MM-SS>.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the meeting was about. |
| `type` | yes | Always `Meeting`. |
| `threads` | yes | List of links to existing threads. |
| `timestamp` | yes | When the meeting happened, `YYYY-MM-DD-HH-MM-SS`. |
| `counterparty` | no | The other party. |
| `location` | no | Where the meeting was held. |
| `people` | no | List of `[[people/X]]` links, which must resolve, or plain names. |

Body markers: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:` and `!:`.

### `note_simple`

A note of type Workshop, Report, Log, Research or Recipe. The files live in `notes/`, named `<YYYY-MM-DD-HH-MM-SS>.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about. |
| `type` | yes | One of `Workshop`, `Report`, `Log`, `Research`, `Recipe`. |
| `threads` | yes | List of links to existing threads. |
| `timestamp` | yes | When the event happened, `YYYY-MM-DD-HH-MM-SS`. |
| `people` | no | List of `[[people/X]]` links or plain names. |

Body markers: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:` and `!:`.

### `payments_file`

Money received for one thread. The files live at `payments/{Projects,Processes,Topics}/<Thread>.md`. The body holds exactly one `adulting-payments` fenced block. That block contains JSON of the form `{"payments": [...]}`.

Frontmatter:

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Link to an existing thread. |
| `currency` | yes | Three-letter ISO code. |

Each payment:

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | 8 hex characters, unique across all hours and payments. |
| `received` | yes | When the money landed, UTC `YYYY-MM-DDTHH:MM:SS.mmmZ`. |
| `amount` | yes | A number greater than 0. |
| `currency` | yes | Three-letter ISO code. |
| `account` | no | The account the money landed in. |
| `note` | no | Free text. |

### `person`

A contact you track. The files live at `people/<Full Name>.md`.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | Start date. |
| `ended` | no | End date. It is required when `status` is `closed`. |
| `cadences` | no | List of `{key, frequency, description}` entries. |

### `task_anchor`

A single `TASK:` or `DONE:` line in a note or log. It is written and changed only by `tasks`.

```
TASK: [#H] (Riaz Arbi) Send quarterly report <!--abcd1234 entry:2026-05-27 due:2026-05-29-->
```

| Field | Required | Meaning |
|---|---|---|
| `kind` | yes | `TASK` or `DONE`. |
| `priority` | no | `H`, `M` or `L`, shown as `[#X]`. |
| `assignee` | no | A person. It must resolve to `people/<name>.md`. |
| `body` | yes | The task text. |
| `uuid` | yes | 8 hex characters, unique across the vault. |
| `entry` | yes | The date the task was ingested. |
| `end` | no | The completion date. It is required for `DONE` and must not be earlier than `entry`. |
| `due` | no | The due date. |
| `scheduled` | no | The scheduled date. |
| `depends` | no | Comma-separated uuids of other tasks. Dependencies cannot form a loop. |

### `thread`

A project, process or topic. The files live at `threads/{Projects,Processes,Topics}/<Name>.md`.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `kind` | yes | `project`, `process` or `topic`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | Start date. |
| `ended` | no | End date. It is required when `status` is `closed`. |
| `cadences` | no | List of `{key, frequency, description}` entries. `frequency` is in days. |
| `currency` | no | Three-letter ISO code. It is the default currency for `hours`. |
| `rate` | no | Integer. It is the default hourly rate for `hours`. |
| `client_name` | no | The party billed on a statement. It is required for `payments statement --pdf`. |
| `client_address` | no | Address lines separated by `\|`. |
| `client_vat` | no | Client VAT number. |
| `client_email` | no | Client email address. |

### `thread_entry`

A dated bullet at the top level of a thread file's body, written as `- YYYY-MM-DD — <text>`. Indented sub-bullets are not checked.

| Field | Required | Meaning |
|---|---|---|
| `date` | yes | The date of the entry. |
| `text` | yes | The entry text. It cannot be empty. |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `buffer tend` or `buffer flush` reports violations. | The buffer has `UNKNOWN` lines, or a line is invalid. | Run `buffer list`, then `buffer rm <line-number>`. Re-add the line with `buffer add-text` or `buffer add-action`. |
| `tasks` exits 1: `no task found with uuid prefix`. | No task matches the prefix. | Get the uuid from `tasks list`. |
| `tasks set-assignee` exits 1: `does not resolve to people/...`. | The person has no file. | Run `people new --name "<Full Name>" --category <category>`. |
| `notes new` exits 1: `--person is only for Meeting and Correspondence notes`. | You used a person option on the wrong note type. | Drop `--person`, or use `--type Meeting` or `--type Correspondence`. |
| `notes new` exits 1: `--counterparty and --location are only for Meeting notes`. | You used a meeting-only option on another type. | Drop the option, or use `--type Meeting`. |
| `notes pdf`, `minutes` or `agenda` exits 1: `PDF render failed`. | The render failed. These commands need `pandoc` and `xelatex`. | Install `pandoc` and a LaTeX engine. |
| `hours log` or `hours edit` exits 1: `--rate needs a currency`. | You gave a rate, but no currency is set. | Add `-c <ISO>`, or create the thread with `--currency`. |
| `payments statement` exits 1: `--pdf needs --thread`. | A statement PDF covers one client only. | Add `--thread Projects/<Name>`. |
| `threads new` or `people new` exits 1: `already exists` or `cannot contain '/'`. | The name is taken or invalid. | Use a bare name, with no `/` and no leading `.`. Pass the kind with `--kind`. |
| `threads delete` or `people delete` exits 1: `refusing to delete ... without -y`. | You did not confirm the delete. | Add `-y`. |
| `commit` exits 1: `not a git repository`, or `ADULTING_HOME ... is not the root of its git repository`. | The vault is not the root of its own git repository. | Point `ADULTING_HOME` at the repository root. |
| `lint` exits 2: `no schemas loaded`. | `--schemas` points at a directory with no schemas. | Drop `--schemas`, or give the correct directory. |

## Quick reference

| Command | Does |
|---|---|
| `tasks` | Ingests ACTION lines into TASK anchors. |
| `tasks ingest` | Ingests ACTION lines into TASK anchors. |
| `tasks add` | Adds an ACTION to the buffer. |
| `tasks done` | Marks a task complete. |
| `tasks set-description` | Replaces a task's text. |
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
| `search stream` | Shows all dated records as one timeline. |
| `threads list` | Lists threads. |
| `threads show` | Shows one thread. |
| `threads new` | Creates a thread. |
| `threads delete` | Deletes a thread permanently. |
| `people list` | Lists people. |
| `people show` | Shows one person. |
| `people new` | Creates a person. |
| `people delete` | Deletes a person permanently. |
| `hours log` | Records a time entry. |
| `hours list` | Lists time entries. |
| `hours report` | Totals time by thread and currency. |
| `hours show` | Shows one time entry. |
| `hours edit` | Changes one field of a time entry. |
| `hours rm` | Deletes a time entry. |
| `payments log` | Records a payment received. |
| `payments list` | Lists payments. |
| `payments statement` | Shows billed against received. |
| `payments show` | Shows one payment. |
| `payments edit` | Changes one field of a payment. |
| `payments rm` | Deletes a payment. |
| `buffer add` | Captures a raw UNKNOWN line. |
| `buffer add-text` | Captures a TEXT line. |
| `buffer add-ref` | Captures a REF line. |
| `buffer add-action` | Captures an ACTION line. |
| `buffer list` | Shows the buffer with line numbers. |
| `buffer rm` | Removes one buffer line. |
| `buffer tend` | Regroups and validates the buffer. |
| `buffer flush` | Files the buffer into logs and clears it. |
| `lint` | Validates vault files against the schemas. |
| `commit review` | Shows changes since the last commit. |
| `commit save` | Stages and commits all vault changes. |
