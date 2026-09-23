# adulting — Operators Manual

## Before you start

All data lives in one directory, the vault. The default is `~/vault/`. To use another directory, set the `ADULTING_HOME` environment variable. Every tool then reads and writes there.

You need these programs:

| Program | Needed by |
|---|---|
| Python 3.11 or newer | every tool |
| `git` | `commit` |
| `pandoc` and a LaTeX engine (`xelatex`) | `notes pdf`, `notes minutes`, `notes agenda` |

Everything is plain text on disk: Markdown files with frontmatter, plus JSON blocks inside Markdown. You can read, grep and back up the vault with ordinary tools. Tool settings live in the hidden `.adulting/` directory inside the vault.

## How the pieces fit

| Object | What it is | Where it lives |
|---|---|---|
| Note | A document: a meeting, correspondence, report, research and so on | `notes/` |
| Thread | Groups related work. Kinds: project (bounded), process (ongoing), topic (interest area) | `threads/Projects/`, `threads/Processes/`, `threads/Topics/` |
| Person | A contact you track. Other records link to people. | `people/` |
| Time entry | A session of work on a thread, billable or not | `hours/<Kind>/<Thread>.md` |
| Payment | Money received against a thread | `payments/<Kind>/<Thread>.md` |
| Action / task | An `ACTION:` line, rewritten into a `TASK:` or `DONE:` line. The line in its source file is the task. | Inside files in `notes/` and `logs/` |
| Log | One file per thread per day, written by `buffer flush` | `logs/<Kind>/<Name>/<YYYY-MM-DD>.md` |
| Buffer | The inbox for quick captures | `buffer.md` |

Relationships:

- A note belongs to one or more threads. It can list people.
- A person is never a thread.
- A task can have an assignee, which must be a person. It can depend on other tasks.
- Each thread has at most one hours file and one payments file. Their paths mirror the thread's path.
- A thread's `currency` and `rate` are the defaults for `hours log`.
- `notes new`, `hours log` and `payments log` each add a `REF:` line to the buffer. The next `buffer flush` files it in the thread's log for that day.

## Command reference

Every command is non-interactive. Each one takes all its values from arguments. Nothing prompts you, and nothing opens an editor or app. Every command and subcommand accepts `--help`. These flags are left out of the tables below.

### tasks

Turns `ACTION:` lines into tracked `TASK:` lines and changes those lines in place.

**When to use it**

- You wrote `ACTION:` lines in a note and want them tracked.
- You want to see what to do next, or what is overdue.
- You finished a task, or need to change its due date, priority, assignee or dependencies.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| *(none)* | Same as `ingest`. | `tasks` |
| `ingest` | Rewrites every `ACTION:` line in `notes/` and `logs/` as a `TASK:` line with a new 8-character uuid. | `tasks ingest --dry-run` |
| `add` | Adds an `ACTION:` line to the buffer. Same as `buffer add-action`. | `tasks add Projects/Acme "(Jane Doe) Send the proposal" --due <YYYY-MM-DD> --priority H` |
| `done` | Changes `TASK:` to `DONE:` and records today as the end date. | `tasks done <uuid>` |
| `set-description` | Replaces the task's text. | `tasks set-description <uuid> "Send the revised proposal"` |
| `set-assignee` | Replaces the `(Assignee)` part. | `tasks set-assignee <uuid> "Jane Doe"` |
| `set-due` | Sets the due date. | `tasks set-due <uuid> <YYYY-MM-DD>` |
| `set-scheduled` | Sets the scheduled date. | `tasks set-scheduled <uuid> <YYYY-MM-DD>` |
| `set-priority` | Sets priority `H`, `M` or `L`. | `tasks set-priority <uuid> H` |
| `add-depends` | Makes the task wait on another task. | `tasks add-depends <uuid> <dep-uuid>` |
| `rm-depends` | Removes a dependency. | `tasks rm-depends <uuid> <dep-uuid>` |
| `list` | Lists pending tasks, grouped by thread. | `tasks list --overdue` |
| `next` | Shows the top 5 pending tasks by priority, then due date, then entry date. | `tasks next` |
| `show` | Shows one task in detail. | `tasks show <uuid>` |

A `<uuid>` can be any prefix that picks out exactly one task. Get uuids from `tasks list`.

**Options**

Global: `--dry-run` shows what would be ingested and writes nothing. `--quiet` hides the per-action output. Both work on bare `tasks` and on `tasks ingest`.

| Option | Effect |
|---|---|
| `add --due <YYYY-MM-DD>` | Due date. |
| `add --scheduled <YYYY-MM-DD>` | Scheduled date. |
| `add --priority <H\|M\|L>` | Priority. |
| `add --depends <uuid>` | 8-character uuid of a task this one waits on. You can repeat it. |
| `list --priority <H\|M\|L>` | Show only one priority. |
| `list --thread <Kind/Name>` | Show only tasks whose source note carries this thread. |
| `list --assignee <person>` | Show only tasks assigned to this person. |
| `list --overdue` | Show only tasks due before today. |
| `list --json` | JSON output. |

**Notes**

- Ingest and every `set-*`, `done`, `add-depends` and `rm-depends` command rewrite the source file in place. Do not edit `TASK:` or `DONE:` lines by hand.
- `tasks add` only writes to the buffer. The task appears after `buffer flush` and an ingest.
- Exit code `1` means one of these: no task matches the uuid prefix, the prefix is empty, a date is not `YYYY-MM-DD`, the description is empty, the person has no file in `people/`, or a task depends on itself.

### notes

Creates, lists, prints, copies, deletes and renders notes. Each note is named by its stem.

**When to use it**

- You are starting a meeting, correspondence or report note.
- You need to find a note's stem, or print a note.
- You need minutes, an agenda or a PDF of a note.

The stem is the filename without `.md`, for example `2026-09-10-14-30-00`.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Creates a note and prints its path. | `notes new --type Meeting --topic "Kickoff" --thread Projects/Acme --person "Jane Doe"` |
| `list` | Lists notes, oldest first: stem, date, type, threads, topic. | `notes list acme` |
| `cat` | Prints a note. | `notes cat <stem>` |
| `last` | Prints the path of the newest note. | `notes last` |
| `copy` | Copies a note under a new timestamp. `COPY` is added to the end of its topic. | `notes copy <stem>` |
| `delete` | Deletes a note permanently. | `notes delete <stem> -y` |
| `pdf` | Writes the note as Markdown and PDF, with callouts and an action table. | `notes pdf <stem>` |
| `minutes` | Writes meeting minutes: agreements, resolutions and action items. | `notes minutes <stem>` |
| `agenda` | Writes a meeting agenda: the note with its outcome sections emptied. | `notes agenda <stem> --out <dir>` |

**Options**

| Option | Effect |
|---|---|
| `new --type <type>` | Required. One of `Meeting`, `Correspondence`, `Workshop`, `Report`, `Log`, `Research`, `Recipe`. |
| `new --topic <text>` | Required. What the note is about. |
| `new --thread <thread>` | Required. Takes a thread name, `Kind/Name` or a wikilink. You can repeat it. |
| `new --person <name>` | Meeting and Correspondence only. Adds an attendee. You can repeat it. The name is linked when `people/<name>.md` exists. |
| `new --counterparty <text>` | Meeting only. The other party. |
| `new --location <text>` | Meeting only. Where the meeting was held. |
| `list [<filter>]` | Case-insensitive text matched against every column. |
| `list --json` | JSON output. |
| `delete -y`, `--yes` | Required. Confirms the delete. |
| `pdf`/`minutes`/`agenda --out <dir>` | Output directory. The default is `~/Downloads`. |

**Notes**

- Every subcommand except `new` first ingests `ACTION:` lines, like `tasks`. This rewrites source files. If an `ACTION:` line fails, the command continues. It prints a one-line warning when stderr is a terminal.
- `notes new` adds a `REF:` line to the buffer.
- Renders are written as `<stem>.md` and `<stem>.md.pdf`.
- `delete` cannot be undone.
- Exit code `1` means one of these: a bad or unknown stem, an empty `--topic`, an option used with the wrong note type, or a failed PDF render.

### search

Finds notes and logs, and summarises activity on threads. It only reads.

**When to use it**

- You need notes or logs by thread, type, date range or text.
- You want to see which threads were active in a period.
- You want everything that happened on one thread, or today, in date order.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `notes` | Finds notes. | `search notes --thread Projects/Acme --type Meeting --since <YYYY-MM-DD>` |
| `logs` | Finds daily logs. | `search logs --text invoice` |
| `activity` | Ranks threads by what happened in a date range. | `search activity --since <YYYY-MM-DD>` |
| `overview` | Shows the whole picture of one thread. | `search overview Projects/Acme` |
| `stream` | Merges every dated record into one timeline. | `search stream --today` |

**Options**

Global: every subcommand takes `--since <YYYY-MM-DD>` (on or after), `--until <YYYY-MM-DD>` (on or before) and `--json`.

| Option | Effect |
|---|---|
| `--thread <thread>` | Only this thread (`notes`, `logs`, `activity`, `stream`). |
| `notes --type <type>` | Note type, case-insensitive. |
| `notes --text <text>` | Case-insensitive literal text, matched in the topic and body. |
| `logs --text <text>` | Case-insensitive literal text, matched in the entry lines. |
| `stream --text <text>` | Case-insensitive literal text, matched in the thread and summary. |
| `--limit <n>` | Maximum number of results. Defaults: `notes` and `logs` 20, `overview` 5, `stream` 100. `0` returns all. |
| `stream --kind <list>` | Comma-separated: `note`, `log`, `task`, `done`, `hours`, `payment`, `thread`, `person`, `pending`. The default is all. |
| `stream --today` | Today only. |
| `stream --reverse` | Oldest first. The default is newest first. |

**Notes**

- Results are pointers: absolute paths plus metadata, never file contents. Open a file in a separate step.
- Dates are event dates, taken from the note's frontmatter `timestamp`. The filename date is used only when that field is missing or malformed.
- `search` does not index the text of time entries.
- Exit code `1` means `--kind` got an unknown kind.

### threads

Creates, lists, shows and deletes thread files.

**When to use it**

- You are starting a new project, process or topic.
- You need a thread's exact name or its billing defaults.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists threads. Shows open threads unless you pass `--all`. | `threads list acme` |
| `show` | Shows one thread file. | `threads show Projects/Acme` |
| `new` | Creates a thread file. | `threads new --name Acme --kind project --category professional --currency ZAR --rate 1500` |
| `delete` | Deletes a thread file permanently. | `threads delete Projects/Acme -y` |

**Options**

| Option | Effect |
|---|---|
| `list [<query>]` | Fuzzy search. Results are ranked by similarity. |
| `list --all` | Include paused and closed threads. |
| `list`/`show --json` | JSON output. |
| `new --name <name>` | Required. Becomes the filename. |
| `new --kind <project\|process\|topic>` | Required. Chooses the directory: `Projects`, `Processes` or `Topics`. |
| `new --category <professional\|personal\|voluntary>` | Required. |
| `new --currency <ISO>` | 3-letter currency code. Makes the thread billable. It is the default currency for `hours`. |
| `new --rate <n>` | Default hourly rate for `hours`. Needs `--currency`. |
| `delete -y`, `--yes` | Required. Confirms the delete. |

**Notes**

- Exit code `1` means one of these: an empty name, a name containing `/` or starting with `.`, a thread that already exists, `--rate` without `--currency`, or `delete` without `-y`.

### people

Creates, lists, shows and deletes person files.

**When to use it**

- Before you assign a task to someone. The assignee must have a file.
- Before you link an attendee in a note.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists people. Shows open people unless you pass `--all`. | `people list jane` |
| `show` | Shows one person file. | `people show "Jane Doe"` |
| `new` | Creates a person file. | `people new --name "Jane Doe" --category professional` |
| `delete` | Deletes a person file permanently. | `people delete "Jane Doe" -y` |

**Options**

| Option | Effect |
|---|---|
| `list [<query>]` | Fuzzy search. Results are ranked by similarity. |
| `list --all` | Include closed people. |
| `list`/`show --json` | JSON output. |
| `new --name <name>` | Required. The full name. Becomes the filename. |
| `new --category <professional\|personal\|voluntary>` | Required. |
| `delete -y`, `--yes` | Required. Confirms the delete. |

**Notes**

- Exit code `1` means one of these: an empty name, a name containing `/` or starting with `.`, a person that already exists, a person not found, or `delete` without `-y`.

### hours

Records time worked on a thread, billable or not.

**When to use it**

- You finished a session of work and want to record its length.
- You need totals for a thread over a period.
- You need to correct or remove an entry.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Adds an entry. | `hours log -m 90 Projects/Acme "Drafted the proposal"` |
| `list` | Lists entries. | `hours list Projects/Acme --since <YYYY-MM-DD>` |
| `report` | Totals by thread and currency. Unbilled time is totalled separately. | `hours report --thread Projects/Acme --since <YYYY-MM-DD> --until <YYYY-MM-DD>` |
| `show` | Shows one entry. | `hours show <id>` |
| `edit` | Changes one field of an entry. | `hours edit <id> -m 120` |
| `rm` | Deletes an entry. | `hours rm <id> -y` |

`<id>` is the entry's 8-character id from `hours list`.

**Options**

| Option | Effect |
|---|---|
| `log -m`, `--minutes <n>` | Duration in minutes. The default is 60. |
| `log -r`, `--rate <n>` | Hourly rate. `0` means unbillable. |
| `log -c`, `--currency <ISO>` | The default is the thread's currency. With no currency from either, the entry is unbilled. |
| `log -d`, `--date <YYYY-MM-DD>` | The default is today. |
| `log -t`, `--time <HH:MM>` | Start time. The default is now. |
| `list [<thread>]`, `report --thread <thread>` | Only this thread. |
| `list`/`report --since`, `--until <YYYY-MM-DD>` | Date range. |
| `list`/`report`/`show --json` | JSON output. |
| `edit --description <text>` | New description. |
| `edit -m`, `--minutes <n>` | New duration. The start time does not change. |
| `edit -r`, `--rate <n>` | New rate. Needs a currency. |
| `edit -c`, `--currency <ISO>` | New currency. |
| `edit -d`, `--date <YYYY-MM-DD>` | Moves the entry to this day. The duration does not change. |
| `edit -t`, `--time <HH:MM>` | Moves the start to this time. The duration does not change. |
| `rm -y`, `--yes` | Required. Confirms the delete. |

**Notes**

- The description is an invoice line item. Keep it short. `search` does not index it. Record details in a log line with `buffer add-text`.
- On a thread with no currency, entries get rate 0 and no currency. They count as unbilled time.
- `hours log` adds a `REF:` line to the buffer, filed under the day the work happened.
- Exit code `1` means one of these: minutes that are not positive, a rate with no currency, or an empty description.

### payments

Records money received against a thread and compares billed with received.

**When to use it**

- A client paid you.
- You need a statement of account, as a table or a PDF.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Records a payment received. | `payments log Projects/Acme 15000 -a "Business account" -n "Invoice 12"` |
| `list` | Lists payments. | `payments list Projects/Acme` |
| `statement` | Shows billed against received, by thread and currency. | `payments statement --thread Projects/Acme --pdf <path>.pdf` |
| `show` | Shows one payment. | `payments show <id>` |
| `edit` | Changes one field of a payment. | `payments edit <id> --amount 14500` |
| `rm` | Deletes a payment. | `payments rm <id> -y` |

`<id>` is the payment's 8-character id from `payments list`.

**Options**

| Option | Effect |
|---|---|
| `log <thread> <amount>` | Always give the amount. It must be positive. |
| `log`/`edit -c`, `--currency <ISO>` | The default is the thread's currency. |
| `log`/`edit -d`, `--date <YYYY-MM-DD>` | Date received. The default is today. |
| `log`/`edit -t`, `--time <HH:MM>` | The default is now. |
| `log`/`edit -a`, `--account <text>` | The account the money went into. |
| `log`/`edit -n`, `--note <text>` | Free-text note. Put it last, because it takes several words. |
| `edit --amount <n>` | New amount. |
| `list [<thread>]`, `statement --thread <thread>` | Only this thread. |
| `list`/`statement --since`, `--until <YYYY-MM-DD>` | Date range. |
| `statement --as-of <YYYY-MM-DD>` | Statement date. It drives aging. The default is today. |
| `statement --pdf <path>` | Writes a PDF to this path. Needs `--thread`. |
| `list`/`statement`/`show --json` | JSON output. |
| `rm -y`, `--yes` | Required. Confirms the delete. |

**Notes**

- A PDF statement needs `client_name` in the thread file. The `client_address`, `client_vat` and `client_email` fields are optional.
- Amounts must be positive. There are no negative payments.
- `payments log` adds a `REF:` line to the buffer, filed under the day the money was received.
- Exit code `1` means one of these: a missing, invalid or non-positive amount, `--pdf` without `--thread`, or nothing to state for that thread and date.

### buffer

Captures items into `buffer.md`, checks them, and files them into daily logs.

**When to use it**

- You want to jot something down now and sort it later.
- You want to record an observation, pointer or action against a thread without writing a note.
- At the end of a session, to file captures into `logs/`.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `add` | Adds a raw `UNKNOWN:` line. It blocks `tend` and `flush` until you convert it. | `buffer add "call the accountant about VAT"` |
| `add-text` | Adds a `TEXT:` observation to a thread. | `buffer add-text Projects/Acme "Client approved the scope"` |
| `add-ref` | Adds a `REF:` pointer to another vault file. | `buffer add-ref Projects/Acme notes/<stem> "kickoff notes"` |
| `add-action` | Adds an `ACTION:` line. | `buffer add-action Projects/Acme "(Jane Doe) Send the contract" --due <YYYY-MM-DD>` |
| `list` | Shows the buffer with line numbers. | `buffer list` |
| `rm` | Removes one line by its number. | `buffer rm <line-number>` |
| `tend` | Regroups lines by thread and date, then checks them. Safe to repeat. | `buffer tend` |
| `flush` | Runs `tend`, writes lines to `logs/`, then clears the buffer. | `buffer flush` |

**Options**

Global: `--quiet` hides info output. Put it before the subcommand: `buffer --quiet flush`.

| Option | Effect |
|---|---|
| `add*` `--date <YYYY-MM-DD>` | Files the line under this day. Use the date the thing happened. |
| `add-ref <target>` | One of `notes/<stem>`, `logs/<path>`, `people/<name>`, `hours/<Kind>/<Thread>`, `payments/<Kind>/<Thread>`, `<Kind>/<Thread>`. |
| `add-action --due`, `--scheduled <YYYY-MM-DD>` | Dates for the task. |
| `add-action --priority <H\|M\|L>` | Priority. |
| `add-action --depends <uuid>` | 8-character uuid of a task this one waits on. You can repeat it. |
| `list [<filter>]` | Only lines containing this text, ignoring case. |
| `list --json` | JSON output. |

**Notes**

- To convert an `UNKNOWN:` line, remove it with `buffer rm`. Then add it again with the matching `add-*` command.
- Do not edit `buffer.md` by hand. Use these commands.
- `flush` clears the buffer after it writes the logs.
- Exit code `1` means one of these: a line number that is not an integer, out of range or empty, or a failed check.

### lint

Checks vault files against the schemas in [Data formats](#data-formats).

**When to use it**

- Before you commit.
- After you edit a vault file by hand.

**Usage**

```
lint [--quiet] [--schemas <dir>] [<path> ...]
```

| Argument | Effect |
|---|---|
| `<path> ...` | Files to check. With none, the whole vault is checked. |
| `--quiet` | No per-problem output. Only the exit code. |
| `--schemas <dir>` | Load schemas from another directory. |

**Notes**

- Exit code `0` means clean. Exit code `1` means problems were found. Exit code `2` means no schemas were loaded.
- Each problem prints as `<path>:<line>: <message>`.

### commit

Reviews the vault's uncommitted changes and commits them to git.

**When to use it**

- At the end of a session, to record what changed.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `review` | Shows everything changed since the last commit. It only reads. | `commit review` |
| `save` | Stages every change in the vault and commits it. | `commit save --message "Log Acme kickoff and hours" --body "Added meeting note and three tasks."` |

**Options**

| Option | Effect |
|---|---|
| `review --max-file-lines <n>` | Maximum diff lines per file. The default is 150. |
| `review --max-lines <n>` | Maximum output lines in total. The default is 3000. |
| `save --message <text>` | Required. The commit subject, on a single line. |
| `save --body <text>` | The commit body. It can span several lines. |
| `save --dry-run` | Reports what would be staged and committed. Changes nothing. |

**Notes**

- `save` only ever adds a commit. It never amends, rebases, resets, checks out or pushes.
- `ADULTING_HOME` must be the root of a git repository.
- Exit code `1` means one of these: an empty or multi-line `--message`, a vault that is not a git repository or not its root, or a failed git command.

## Everyday procedures

### 1. Set up a new billable project

1. `threads new --name Acme --kind project --category professional --currency ZAR --rate 1500`: creates `threads/Projects/Acme.md` with billing defaults.
2. `people new --name "Jane Doe" --category professional`: creates the client contact so tasks and notes can link to them.
3. Add `client_name` to the thread file's frontmatter. PDF statements need it.
4. `threads show Projects/Acme`: confirms the file.
5. `lint threads/Projects/Acme.md`: checks the file against the `thread` schema.

### 2. Capture a meeting and turn its actions into tracked tasks

1. `notes new --type Meeting --topic "Kickoff" --thread Projects/Acme --person "Jane Doe" --counterparty "Acme Ltd"`: creates the note and prints its path.
2. Write the meeting in that file. Start each action line with `ACTION: (Jane Doe)`, followed by the action.
3. `tasks`: rewrites each `ACTION:` line as a `TASK:` line with a uuid.
4. `tasks list --thread Projects/Acme`: shows the new tasks and their uuids.
5. `tasks set-due <uuid> <YYYY-MM-DD>`: adds a due date where you need one.
6. `notes minutes <stem>`: writes the minutes as Markdown and PDF to `~/Downloads`.

### 3. Quick-capture through the day, then file it

1. `buffer add "<text>"`: captures a thought with no thread.
2. `buffer list`: shows every line with its number.
3. `buffer rm <line-number>`: removes a raw `UNKNOWN:` line.
4. `buffer add-text Projects/Acme "<text>"` or `buffer add-action Projects/Acme "<text>"`: adds it again in the right form.
5. `buffer tend`: regroups and checks the buffer. Repeat steps 2 to 4 until it passes.
6. `buffer flush`: writes the lines into `logs/` and clears the buffer.
7. `tasks`: turns the flushed `ACTION:` lines into tasks.

### 4. Work the task list

1. `tasks next`: shows the top 5 pending tasks.
2. `tasks list --overdue`: shows tasks past their due date.
3. `tasks show <uuid>`: shows one task in detail.
4. `tasks set-priority <uuid> H`: raises its priority.
5. `tasks add-depends <uuid> <dep-uuid>`: records that it waits on another task.
6. `tasks done <uuid>`: marks it complete with today's date.

### 5. Log a session of work

1. `hours log -m 90 Projects/Acme "Drafted the proposal"`: records 90 minutes under a short label.
2. `buffer add-text Projects/Acme "<what actually happened>"`: records the detail as a log line.
3. `hours list Projects/Acme --since <YYYY-MM-DD>`: confirms the entry and shows its id.
4. `hours edit <id> -m 120`: corrects the duration if you need to.
5. `buffer flush`: files the log line and the entry's `REF:` into the day's log.

### 6. Bill a client for a month's work

1. `hours list Projects/Acme --since <YYYY-MM-01> --until <YYYY-MM-DD>`: shows the month's line items.
2. `hours report --thread Projects/Acme --since <YYYY-MM-01> --until <YYYY-MM-DD>`: shows the month's totals by currency.
3. `payments statement --thread Projects/Acme`: shows billed against received as of today.
4. `payments statement --thread Projects/Acme --pdf <path>.pdf`: writes the statement as a PDF.

### 7. Record a payment

1. `payments log Projects/Acme 15000 -d <YYYY-MM-DD> -a "Business account" -n "Invoice 12"`: records the payment on the day it arrived.
2. `payments list Projects/Acme`: confirms it and shows its id.
3. `payments statement --thread Projects/Acme`: shows the updated balance.
4. `buffer flush`: files the payment's `REF:` into the day's log.

### 8. Check the vault and commit it

1. `buffer tend`: checks the buffer.
2. `lint`: checks the whole vault. Fix each reported `<path>:<line>` until the exit code is `0`.
3. `commit review`: shows everything that changed.
4. `commit save --message "<one-line summary>" --dry-run`: shows what would be committed.
5. `commit save --message "<one-line summary>" --body "<detail>"`: commits the changes.

## Data formats

`lint` enforces every schema below. Paths are relative to the vault.

### `hours_file`

The time entries for one thread. Each file is at `hours/<Kind>/<Thread>.md`. The body holds exactly one `simple-time-tracker` fenced block with JSON `{"entries": [...]}`. The `hours` tool writes it.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to an existing thread. |
| `currency` | no | 3-letter uppercase code. Left out for unbilled threads. |
| `entries[].name` | yes | The description, an invoice line item. |
| `entries[].startTime` | yes | UTC start, `YYYY-MM-DDTHH:MM:SS.mmmZ`. |
| `entries[].endTime` | yes | UTC end, same form. Not before `startTime`. |
| `entries[].id` | yes | 8 hex characters, unique across hours and payments. |
| `entries[].rate` | yes | Hourly charge, a whole number. `0` means unbillable. |
| `entries[].currency` | no | 3-letter code. If absent or null, the entry is unbilled. |

The duration is `endTime` minus `startTime`. There is no duration field.

### `log`

One thread's activity for one day, written by `buffer flush`. Each file is at `logs/<Kind>/<Name>/<YYYY-MM-DD>.md`. Body lines are `TEXT:`, `REF:`, `ACTION:`, `TASK:` or `DONE:`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to a `Projects`, `Processes` or `Topics` thread. |
| `date` | yes | `YYYY-MM-DD`. |
| `type` | yes | Always `Log`. |

### `note_correspondence`

A note about emails, messages or letters. It applies when `type` is `Correspondence`. Files are in `notes/`, named `YYYY-MM-DD-HH-MM-SS.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about. |
| `type` | yes | `Correspondence`. |
| `threads` | yes | List of thread wikilinks. Each must resolve. |
| `timestamp` | yes | When it happened, `YYYY-MM-DD-HH-MM-SS`. |
| `people` | no | List of `[[people/X]]` wikilinks, which must resolve, or plain names. |

Body markers: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:`, and `!:` for callouts.

### `note_meeting`

A note about a meeting. It applies when `type` is `Meeting`. Files are in `notes/`, named `YYYY-MM-DD-HH-MM-SS.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the meeting was about. |
| `type` | yes | `Meeting`. |
| `threads` | yes | List of thread wikilinks. Each must resolve. |
| `timestamp` | yes | When it happened, `YYYY-MM-DD-HH-MM-SS`. |
| `counterparty` | no | The other party. |
| `location` | no | Where it was held. |
| `people` | no | List of `[[people/X]]` wikilinks, which must resolve, or plain names. |

Body markers: `ACTION:`, `TASK:`, `AGREED:` and `RESOLVED:` (shown in minutes), and `!:` (callouts in the PDF).

### `note_simple`

A note of type `Workshop`, `Report`, `Log`, `Research` or `Recipe`. Files are in `notes/`, named `YYYY-MM-DD-HH-MM-SS.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about. |
| `type` | yes | One of `Workshop`, `Report`, `Log`, `Research`, `Recipe`. |
| `threads` | yes | List of thread wikilinks. Each must resolve. |
| `timestamp` | yes | When it happened, `YYYY-MM-DD-HH-MM-SS`. |
| `people` | no | List of `[[people/X]]` wikilinks or plain names. |

Body markers: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:`, `!:`.

### `payments_file`

The money received against one thread. Each file is at `payments/<Kind>/<Thread>.md`. The body holds exactly one `adulting-payments` fenced block with JSON `{"payments": [...]}`. The `payments` tool writes it.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to an existing thread. |
| `currency` | yes | 3-letter uppercase code. |
| `payments[].id` | yes | 8 hex characters, unique across hours and payments. |
| `payments[].received` | yes | When the money arrived, UTC `YYYY-MM-DDTHH:MM:SS.mmmZ`. |
| `payments[].amount` | yes | Number greater than 0. |
| `payments[].currency` | yes | 3-letter code. |
| `payments[].account` | no | The account the money went into. |
| `payments[].note` | no | Free text. |

### `person`

A contact you track. Files are at `people/<Name>.md`. The body is free-form.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | `YYYY-MM-DD`. |
| `ended` | no | `YYYY-MM-DD`. Required when `status` is `closed`. |
| `cadences` | no | List of `{key, frequency, description}`, as on threads. |

### `task_anchor`

One `TASK:` or `DONE:` line in a file in `notes/` or `logs/`. Only `tasks` should change it.

```
TASK: [#H] (Riaz Arbi) Send quarterly report <!--abcd1234 entry:2026-05-27 due:2026-05-29-->
```

| Field | Required | Meaning |
|---|---|---|
| `kind` | yes | `TASK` or `DONE`. |
| `priority` | no | `H`, `M` or `L`, shown as `[#X]`. |
| `assignee` | no | Shown as `(Name)`. Must resolve to `people/<name>.md`. |
| `body` | yes | The task text. |
| `uuid` | yes | 8 hex characters, unique across the vault. |
| `entry` | yes | Date ingested, `YYYY-MM-DD`. |
| `end` | no | Date completed. Required for `DONE`. Not before `entry`. |
| `due` | no | `YYYY-MM-DD`. |
| `scheduled` | no | `YYYY-MM-DD`. |
| `depends` | no | Comma-separated uuids of existing tasks. Must not form a cycle. |

The attributes inside the comment always appear in this order: `entry`, `end`, `due`, `scheduled`, `depends`.

### `thread`

A project, process or topic. Files are at `threads/<Kind>/<Name>.md`, where `<Kind>` is `Projects`, `Processes` or `Topics`.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `kind` | yes | `project`, `process` or `topic`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | `YYYY-MM-DD`. |
| `ended` | no | `YYYY-MM-DD`. Required when `status` is `closed`. |
| `cadences` | no | Recurring obligations. See below. |
| `currency` | no | 3-letter code. Default currency for `hours`. |
| `rate` | no | Default hourly rate for `hours`, a whole number. |
| `client_name` | no | The billed party. Required for `payments statement --pdf`. |
| `client_address` | no | Lines separated by `\|`, for example `Unit 301\|2 Park Road\|Cape Town`. |
| `client_vat` | no | The client's VAT number. |
| `client_email` | no | The client's email address. |
| `cadences[].key` | yes | Unique within the thread. A `#<key>` tag in an entry satisfies it. |
| `cadences[].frequency` | yes | Interval in days. |
| `cadences[].description` | yes | What the cadence is for. |

The body is a list of dated entries. Each follows `thread_entry`.

### `thread_entry`

One top-level dated bullet in a thread file's body, for example `- 2024-05-17 — Made progress.`. Indented sub-bullets are not checked.

| Field | Required | Meaning |
|---|---|---|
| `date` | yes | `YYYY-MM-DD`. |
| `text` | yes | At least one character, after ` — `. |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `buffer tend` or `buffer flush` reports a violation for an `UNKNOWN:` line | Raw captures always fail the check. | Run `buffer list`, then `buffer rm <line-number>`. Add it again with `buffer add-text`, `add-ref` or `add-action`. |
| `buffer rm` fails: out of range, empty line, or not an integer | Wrong line number. | Run `buffer list` and use a number it shows. |
| `tasks` says `person ... does not resolve to people/<name>.md` | The assignee has no person file. | Run `people new --name "<name>" --category <category>`. |
| `tasks` says `no task found with uuid prefix` | Wrong or stale uuid. | Get the uuid from `tasks list`. |
| `hours` says `--rate needs a currency` | A rate was given with no currency on the entry or thread. | Add `-c <ISO>`, or create the thread with `--currency`. |
| `refusing to delete ... without -y` | Deletes need confirmation. | Add `-y` to the command. |
| `notes` says `PDF render failed` | `pandoc` or `xelatex` is missing or failed. | Install `pandoc` and a LaTeX engine. Then rerun. |
| `notes new` says `--person` or `--counterparty`/`--location` is not allowed | The option does not fit the note type. | Use `--person` only for Meeting and Correspondence. Use the other two only for Meeting. |
| `payments` says `amount is required` or `must be positive` | The amount is missing, zero or negative. | Give a positive amount after the thread. |
| `payments statement` says `--pdf needs --thread` | A statement covers one client. | Add `--thread <thread>`. |
| `commit` says `not a git repository` or `is not the root of its git repository` | `ADULTING_HOME` is not a git repository root. | Point `ADULTING_HOME` at the repository root, or run `git init` there. |
| `commit save` says `--message must be a single line` | The subject has a line break. | Put the detail in `--body`. |
| `lint` exits `1` | A file breaks a schema. | Fix each `<path>:<line>: <message>`, then rerun `lint`. |
| `lint` exits `2` | No schemas were loaded. | Check the `--schemas` directory. |

## Quick reference

| Command | Does |
|---|---|
| `tasks` / `tasks ingest` | Turns `ACTION:` lines into `TASK:` lines, rewriting files. |
| `tasks add` | Adds an `ACTION:` line to the buffer. |
| `tasks done` | Marks a task done. |
| `tasks set-description` | Replaces a task's text. |
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
| `notes copy` | Copies a note under a new timestamp. |
| `notes delete` | Deletes a note permanently. Needs `-y`. |
| `notes pdf` | Writes a note as Markdown and PDF. |
| `notes minutes` | Writes meeting minutes. |
| `notes agenda` | Writes a meeting agenda. |
| `search notes` | Finds notes. Read-only. |
| `search logs` | Finds logs. Read-only. |
| `search activity` | Ranks threads by activity. Read-only. |
| `search overview` | Summarises one thread. Read-only. |
| `search stream` | Shows a merged timeline of records. Read-only. |
| `threads list` | Lists threads. |
| `threads show` | Shows a thread. |
| `threads new` | Creates a thread. |
| `threads delete` | Deletes a thread permanently. Needs `-y`. |
| `people list` | Lists people. |
| `people show` | Shows a person. |
| `people new` | Creates a person. |
| `people delete` | Deletes a person permanently. Needs `-y`. |
| `hours log` | Records time. |
| `hours list` | Lists time entries. |
| `hours report` | Totals time by thread and currency. |
| `hours show` | Shows one entry. |
| `hours edit` | Changes one entry. |
| `hours rm` | Deletes an entry. Needs `-y`. |
| `payments log` | Records a payment. |
| `payments list` | Lists payments. |
| `payments statement` | Shows billed against received, or writes a PDF. |
| `payments show` | Shows one payment. |
| `payments edit` | Changes one payment. |
| `payments rm` | Deletes a payment. Needs `-y`. |
| `buffer add` | Captures a raw `UNKNOWN:` line. |
| `buffer add-text` | Adds a `TEXT:` line. |
| `buffer add-ref` | Adds a `REF:` line. |
| `buffer add-action` | Adds an `ACTION:` line. |
| `buffer list` | Shows the buffer with line numbers. |
| `buffer rm` | Removes a buffer line. |
| `buffer tend` | Regroups and checks the buffer. |
| `buffer flush` | Writes the buffer to `logs/` and clears it. |
| `lint` | Checks vault files against the schemas. |
| `commit review` | Shows uncommitted changes. Read-only. |
| `commit save` | Stages and commits all vault changes. |
