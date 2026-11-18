# adulting — Operators Manual

## Before you start

All data lives in one folder, the vault. The default is `~/vault`. To use another folder, set `ADULTING_HOME`:

```
export ADULTING_HOME=<path-to-vault>
```

Every command reads and writes under that folder. Every path a command prints is absolute.

The tools need these programs:

| Program | Needed by |
|---|---|
| Python 3.11 or newer | every tool |
| `git` | `commit` |
| `pandoc` and a LaTeX engine (`xelatex`) | `notes pdf`, `notes minutes`, `notes agenda`, `payments statement --pdf` |

Everything is plain text on disk: Markdown files with YAML frontmatter, plus JSON inside fenced blocks. You can read the files, grep them and back them up with your own tools.

## How the pieces fit

| Object | What it is | Where it lives |
|---|---|---|
| Thread | A project, process or topic that organises everything else | `threads/<Kind>/<Name>.md` |
| Note | A typed document, such as a meeting record, correspondence or report | `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md` |
| Log | One thread's activity for one day, one line per item | `threads/<Kind>/<Name>/logs/<YYYY-MM-DD>.md` |
| Person | A contact you track | `people/<Name>.md` |
| Time entry | A session of work, billable or not | `threads/<Kind>/<Name>/hours.md` |
| Payment | Money received against a thread | `threads/<Kind>/<Name>/payments.md` |
| Action / task | An `ACTION:` line in a note or log, rewritten in place to a `TASK:` anchor | inside the note or log |
| Buffer | The staging queue for quick captures | `buffer.md` |
| Config | Vault-wide settings | `.adulting/config.yaml` |

`<Kind>` is `Projects`, `Processes` or `Topics`. Everything that belongs to a thread lives in the thread's folder, next to its thread file.

Relationships:

- A note names one or more threads in its `threads:` field. It is filed under the first one.
- A note's `people:` entries and a task's assignee link to person files. A person is never a thread.
- Tasks live in notes and logs. Those files are the only task store.
- `buffer flush` turns buffer lines into a thread's daily logs.
- `notes new`, `hours log` and `payments log` each add a `REF:` pointer to the buffer. After a flush, that pointer appears in the thread's log for the day the event happened.
- A thread's `currency` and `rate` are the defaults for its time entries.

## Command reference

No command prompts for input or opens an app. Any permanent delete needs `-y`. Every command and subcommand accepts `--help-json`.

### tasks

Turns `ACTION:` lines into tracked `TASK:` anchors and changes those anchors.

**When to use it**

- You wrote `ACTION:` lines in a note and want them tracked.
- You want to see what to do next, or what is overdue.
- You finished or abandoned a task, or need to change its date, owner or priority.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| *(none)* | Same as `ingest` | `tasks` |
| `ingest` | Rewrites every `ACTION:` line in notes and logs into a `TASK:` anchor with a new 8-character uuid | `tasks ingest --dry-run` |
| `add` | Adds an `ACTION:` line to the buffer. Same as `buffer add-action` | `tasks add Projects/Northwind "(Sam Rivera) Send the revised scope" --due 2026-11-30 --priority H` |
| `done` | Changes `TASK` to `DONE` and stamps `end` with today's date | `tasks done abcd1234` |
| `drop` | Changes `TASK` to `DROPPED` and stamps `end`. Lists open tasks that depend on it but does not change them | `tasks drop abcd1234` |
| `set-description` | Replaces the task's text | `tasks set-description abcd1234 "Send the final scope"` |
| `set-assignee` | Replaces the `(Assignee)` prefix | `tasks set-assignee abcd1234 "Sam Rivera"` |
| `set-due` | Sets the due date | `tasks set-due abcd1234 2026-12-05` |
| `set-scheduled` | Sets the scheduled date | `tasks set-scheduled abcd1234 2026-12-01` |
| `set-priority` | Sets priority `H`, `M` or `L` | `tasks set-priority abcd1234 M` |
| `add-depends` | Makes the task wait on another task | `tasks add-depends abcd1234 ef567890` |
| `rm-depends` | Removes a dependency | `tasks rm-depends abcd1234 ef567890` |
| `list` | Lists pending tasks, grouped by thread | `tasks list --overdue` |
| `next` | Shows the top 5 pending tasks by priority, then due date, then entry date | `tasks next` |
| `show` | Shows one task in detail | `tasks show abcd1234` |

A uuid argument accepts any unique prefix. Get uuids from `tasks list`.

**Options**

| Option | Effect |
|---|---|
| `--dry-run` | On bare `tasks` or `ingest`: shows what would be ingested and writes nothing |
| `--quiet` | On bare `tasks` or `ingest`: suppresses per-action output |
| `add --due <YYYY-MM-DD>` | Sets the due date |
| `add --scheduled <YYYY-MM-DD>` | Sets the scheduled date |
| `add --priority <H\|M\|L>` | Sets priority |
| `add --depends <uuid>` | Adds a dependency. Repeatable |
| `list --priority <H\|M\|L>` | Shows one priority only |
| `list --thread <Kind/Name>` | Shows tasks from one thread only |
| `list --assignee <person>` | Shows one person's tasks only |
| `list --overdue` | Shows only tasks due before today |
| `list --json` | Prints JSON |

**Notes**

- `ingest` and every `set-*`, `done`, `drop`, `add-depends` and `rm-depends` rewrite lines in your note and log files in place.
- `tasks add` only writes to the buffer. The task exists after `buffer flush`.
- Do not edit `TASK:`, `DONE:` or `DROPPED:` lines by hand. Use these subcommands.
- A file that is not valid UTF-8 is skipped. `lint` reports it.
- Exit `1`: unknown or empty uuid prefix, bad date, empty description, an assignee with no `people/` file, or a task made to depend on itself.

### notes

Creates, finds, prints, copies, deletes and renders notes. You refer to each note by its stem.

**When to use it**

- You are starting a meeting record, correspondence log or report.
- You need minutes, an agenda or a PDF of a note to send.
- You need the path of the note you just created.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Creates a note and prints its path | `notes new --type Meeting --topic "Scope review" --thread Projects/Northwind --person "Sam Rivera"` |
| `list` | Lists notes oldest first: stem, date, type, threads and topic | `notes list northwind` |
| `cat` | Prints a note | `notes cat 2026-09-10-14-30-00` |
| `last` | Prints the path of the newest note | `notes last` |
| `copy` | Copies a note to a new timestamp and adds ` COPY` to its topic | `notes copy 2026-09-10-14-30-00` |
| `delete` | Permanently deletes a note | `notes delete 2026-09-10-14-30-00 -y` |
| `pdf` | Renders a note to Markdown and PDF, with callouts and an action table | `notes pdf 2026-09-10-14-30-00` |
| `minutes` | Renders meeting minutes: agreements, resolutions and action items | `notes minutes 2026-09-10-14-30-00` |
| `agenda` | Renders an agenda: the note with the outcome sections emptied | `notes agenda 2026-09-10-14-30-00 --out ~/Desktop` |

**Options**

| Option | Effect |
|---|---|
| `new --type <type>` | Required. One of `Meeting`, `Correspondence`, `Workshop`, `Report`, `Log`, `Research`, `Recipe` |
| `new --topic <text>` | Required. What the note is about |
| `new --thread <Kind/Name>` | Required. Repeatable. The note is filed under the first thread |
| `new --person <name>` | Meeting and Correspondence only. Repeatable. Linked when `people/<name>.md` exists |
| `new --counterparty <text>` | Meeting only. The other party |
| `new --location <text>` | Meeting only. Where the meeting was held |
| `list <filter>` | Case-insensitive match in any column |
| `list --json` | Prints JSON |
| `delete -y` | Required to delete |
| `--out <DIR>` | On `pdf`, `minutes`, `agenda`: output folder. The default is `~/Downloads` |

**Notes**

- Every subcommand except `new` first ingests `ACTION:` lines into tasks. This rewrites source files, even for `list` and `cat`.
- Renders write `<stem>.md` and `<stem>.md.pdf`. They need `pandoc` and `xelatex`.
- `new` creates the file. You write the body yourself.
- Exit `1`: empty topic, an option used with the wrong note type, a malformed stem, no notes in the vault, or a failed PDF render.

### search

Finds notes and logs and summarises activity. It returns absolute paths and metadata, never file bodies.

**When to use it**

- You need every Meeting note for a thread in a date range.
- You want to know which threads were active this week.
- You want one thread's full picture, or today's timeline.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `notes` | Finds notes by thread, type, date or text | `search notes --thread Projects/Northwind --type Meeting --since 2026-10-01` |
| `logs` | Finds daily logs by thread, date or text | `search logs --text "revised scope"` |
| `activity` | Ranks threads by activity in a date window | `search activity --since 2026-11-01` |
| `overview` | Shows the whole picture of one thread | `search overview Projects/Northwind` |
| `stream` | Merges every dated record into one timeline | `search stream --today` |

**Options**

| Option | Effect |
|---|---|
| `--since <YYYY-MM-DD>` / `--until <YYYY-MM-DD>` | Date window, inclusive. All subcommands |
| `--json` | Prints JSON. All subcommands |
| `--thread <Kind/Name>` | One thread only. On `notes`, `logs`, `activity`, `stream` |
| `--text <text>` | Case-insensitive literal. `notes` searches topic and body. `logs` searches entry lines. `stream` searches thread and summary |
| `--type <type>` | On `notes`: one note type, case-insensitive |
| `--limit <N>` | Maximum results. Defaults: 20 for `notes` and `logs`, 5 for `overview`, 100 for `stream`. `0` means all |
| `stream --kind <list>` | Comma-separated: `note`, `log`, `task`, `done`, `dropped`, `hours`, `payment`, `thread`, `person`, `pending`. The default is all |
| `stream --today` | Today only |
| `stream --reverse` | Oldest first. The default is newest first |

**Notes**

- Read-only.
- Dates are event dates: a note's frontmatter `timestamp`, not its filename. The filename is used only when the timestamp is missing or malformed.
- Time-entry descriptions are not searched by `notes` or `logs`. `activity` counts hours.
- Exit `1`: unknown value in `--kind`.

### threads

Creates, lists and shows thread files.

**When to use it**

- You are starting a new project, process or topic.
- You need a thread's exact `Kind/Name` for another command.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists open threads. An optional query ranks them by fuzzy match | `threads list north` |
| `show` | Shows one thread file | `threads show Projects/Northwind` |
| `new` | Creates a thread file | `threads new --name Northwind --kind project --category professional --currency ZAR --rate 1500` |

**Options**

| Option | Effect |
|---|---|
| `list --all` | Includes paused and closed threads |
| `--json` | Prints JSON. On `list` and `show` |
| `new --name <name>` | Required. Becomes the filename |
| `new --kind <project\|process\|topic>` | Required. Selects `Projects/`, `Processes/` or `Topics/` |
| `new --category <professional\|personal\|voluntary>` | Required |
| `new --currency <ISO>` | Default currency for `hours`. Makes the thread billable |
| `new --rate <N>` | Default hourly rate for `hours`. Needs `--currency` |

**Notes**

- There is no delete. To remove a thread, delete its file and its folder by hand.
- To close a thread, set `status: closed` and `ended:` in its frontmatter. Nothing moves.
- Exit `1`: empty name, a name containing `/` or starting with `.`, a thread that already exists, or `--rate` without `--currency`.

### people

Creates, lists, shows and deletes person files.

**When to use it**

- You want to assign tasks to someone or link them from notes.
- You need a person's exact name as it is stored.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists open people. An optional query ranks them by fuzzy match | `people list sam` |
| `show` | Shows one person file | `people show "Sam Rivera"` |
| `new` | Creates a person file | `people new --name "Sam Rivera" --category professional` |
| `delete` | Permanently deletes a person file | `people delete "Sam Rivera" -y` |

**Options**

| Option | Effect |
|---|---|
| `list --all` | Includes closed people |
| `--json` | Prints JSON. On `list` and `show` |
| `new --name <name>` | Required. Full name. Becomes the filename |
| `new --category <professional\|personal\|voluntary>` | Required |
| `delete -y` | Required to delete |

**Notes**

- Exit `1`: empty or invalid name, a person who already exists, a person not found, or `delete` without `-y`.

### hours

Records time against a thread, billable or not.

**When to use it**

- You finished a session of client work.
- You want to track unbilled personal time, such as exercise or admin.
- You need totals by thread and currency before billing.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Adds an entry | `hours log -m 90 Projects/Northwind Scope workshop` |
| `list` | Lists entries | `hours list Projects/Northwind --since 2026-10-01` |
| `report` | Shows totals by thread and currency. Unbilled time is totalled separately | `hours report --since 2026-10-01 --until 2026-10-31` |
| `show` | Shows one entry | `hours show 1a2b3c4d` |
| `edit` | Changes fields of one entry | `hours edit 1a2b3c4d -m 120` |
| `rm` | Permanently deletes an entry | `hours rm 1a2b3c4d -y` |

Entry ids are 8 characters. Get them from `hours list`.

**Options**

| Option | Effect |
|---|---|
| `log -m <minutes>` | Duration. The default is 60 |
| `log -r <rate>` | Hourly rate. `0` means unbillable |
| `log -c <ISO>` | Currency. Defaults to the thread's. Without either, the entry is unbilled |
| `log -d <YYYY-MM-DD>` | Date. The default is today |
| `log -t <HH:MM>` | Start time. The default is now |
| `list <thread>` / `report --thread <thread>` | One thread only |
| `--since` / `--until <YYYY-MM-DD>` | Date window. On `list` and `report` |
| `--json` | Prints JSON. On `list`, `report`, `show` |
| `edit --description <text>` | New description |
| `edit -m <minutes>` | New duration. The start time stays the same |
| `edit -r <rate>` / `edit -c <ISO>` | New rate or currency |
| `edit -d <YYYY-MM-DD>` / `edit -t <HH:MM>` | Moves the entry. The duration stays the same |
| `rm -y` | Required to delete |

**Notes**

- With `log`, put options before the thread. The description is every word after the thread.
- The description is an invoice line item and appears on the client's statement. Keep it short. Put detail in a log line, because `search` does not index hours.
- A thread with no currency is not billable. Its entries get rate 0 and no currency.
- The thread's rate and currency are copied into each entry. Changing the thread's defaults later does not reprice old entries.
- `log` adds a `REF:` pointer to the buffer, filed under the day the work happened.
- Exit `1`: empty description, minutes not positive, or a rate with no currency.

### payments

Records money received against a thread and compares it with what you billed.

**When to use it**

- A client paid you.
- You need a billed-versus-received statement, or a PDF statement of account.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Records a payment | `payments log -c ZAR -d 2026-11-03 -a Business Projects/Northwind 18000` |
| `list` | Lists payments | `payments list Projects/Northwind` |
| `statement` | Shows billed versus received, by thread and currency | `payments statement --thread Projects/Northwind` |
| `show` | Shows one payment | `payments show 9f8e7d6c` |
| `edit` | Changes fields of one payment | `payments edit 9f8e7d6c --amount 18500` |
| `rm` | Permanently deletes a payment | `payments rm 9f8e7d6c -y` |

Payment ids are 8 characters. Get them from `payments list`.

**Options**

| Option | Effect |
|---|---|
| `log <amount>` | The amount received. Required in practice, and must be positive |
| `-c <ISO>` | Currency. On `log`, it defaults to the thread's |
| `-d <YYYY-MM-DD>` | Date received. On `log`, the default is today |
| `-t <HH:MM>` | Time received. On `log`, the default is now |
| `-a <account>` | The account the money landed in |
| `-n <text>` | Free-text note. Put it last; it takes every word after it |
| `edit --amount <amount>` | New amount |
| `list <thread>` / `statement --thread <thread>` | One thread only |
| `--since` / `--until <YYYY-MM-DD>` | Date window. On `list` and `statement` |
| `--json` | Prints JSON. On `list`, `statement`, `show` |
| `statement --as-of <YYYY-MM-DD>` | Statement date. It drives aging. The default is today |
| `statement --pdf <path>` | Writes a PDF statement to `<path>`. Needs `--thread` |
| `statement --opening <YYYY-MM-DD>` | First day the PDF ledger shows. Earlier items become one balance brought forward. Needs `--pdf` |
| `rm -y` | Required to delete |

**Notes**

- A PDF statement needs `client_name` in the thread's frontmatter, plus `pandoc` and `xelatex`.
- The payment reference on the statement is the thread name without its `Kind/` prefix.
- `statement` ignores unbilled hours.
- `log` adds a `REF:` pointer to the buffer, filed under the day the money was received.
- Exit `1`: missing or non-positive amount, `--pdf` without `--thread`, `--opening` without `--pdf`, `--opening` with `--since` or `--until`, or `--opening` after `--as-of`.

### stats

Declares numbers to measure on a thread, logs values and shows them over time.

**When to use it**

- You track a count or measure, such as push-ups, steps or kilometres run.
- You track whether an event happened. Declare an `int` stat and log `1` each time.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Declares a stat in a thread file's frontmatter | `stats new pushups --thread Topics/Fitness --type int --agg sum` |
| `list` | Lists declared stats | `stats list` |
| `log` | Adds a value to the buffer | `stats log pushups 25` |
| `series` | Shows values per day, week or month, from logs and the unflushed buffer | `stats series pushups --by week` |

**Options**

| Option | Effect |
|---|---|
| `new --thread <Kind/Name>` | Required. The thread that owns the stat |
| `new --type <int\|decimal>` | Required. `int` for whole numbers, `decimal` for the rest |
| `new --agg <sum\|last\|max>` | Required. How a period's values combine: add them, take the latest, or take the largest |
| `log -d <YYYY-MM-DD>` / `log -t <HH:MM>` | Date and time. The defaults are today and now |
| `series --by <day\|week\|month>` | Period length. The default is `day`. Weeks start on Monday |
| `series --since` / `--until <YYYY-MM-DD>` | Date window |
| `--json` | Prints JSON. On `list` and `series` |

**Notes**

- Names use lowercase letters, digits and `-`, and are unique across the vault. Put a unit in the name if needed, such as `run-km`.
- A `decimal` value is a plain number such as `12.50`, never `1e3`.
- An empty period shows `-` (or `null` in JSON), not `0`.
- There is no rename or delete. To change a declaration, edit the thread frontmatter. Values already logged are not rewritten.
- Exit `1`: unknown or duplicate name, a value of the wrong type, a bad date or time, a thread that does not resolve, a bad logged value found by `series`, or `--since` after `--until`. Nothing is written.
- Exit `2`: usage error, such as a missing argument or an unknown `--type` or `--agg`.

### buffer

Manages `buffer.md`, the staging queue that `flush` files into each thread's daily logs.

**When to use it**

- You need to capture something fast, with or without a thread.
- You want queued captures filed into logs and actions turned into tasks.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `add` | Adds a raw `UNKNOWN:` entry with no thread | `buffer add "ask Sam about the invoice address"` |
| `add-text` | Adds a `TEXT:` observation | `buffer add-text Projects/Northwind "Sam approved the revised scope"` |
| `add-ref` | Adds a `REF:` pointer to another vault file | `buffer add-ref Projects/Northwind "people/Sam Rivera" "new contact"` |
| `add-action` | Adds an `ACTION:` entry. Same as `tasks add` | `buffer add-action Projects/Northwind "(Sam Rivera) Confirm the start date" --due 2026-11-25` |
| `list` | Shows the buffer with line numbers | `buffer list` |
| `rm` | Removes one line by number | `buffer rm 3` |
| `tend` | Regroups lines by thread and date, then validates | `buffer tend` |
| `flush` | Runs `tend`, writes each thread's logs, clears the buffer, and ingests flushed actions into tasks | `buffer flush` |

**Options**

| Option | Effect |
|---|---|
| `--quiet` | Global; put it before the subcommand. Suppresses info output: `buffer --quiet flush` |
| `--date <YYYY-MM-DD>` | On `add`, `add-text`, `add-ref`, `add-action`: files the entry under the day it happened |
| `add-action --due`, `--scheduled`, `--priority`, `--depends` | Same as `tasks add` |
| `list <filter>` | Only lines containing this text, ignoring case |
| `list --json` | Prints JSON |

**Notes**

- `UNKNOWN:` entries fail `tend` and block `flush`. Remove each one with `rm` and re-add it with the right `add-*` command.
- A `REF:` target is `<Kind>/<Name>`, `<Kind>/<Name>/hours`, `<Kind>/<Name>/payments`, `<Kind>/<Name>/logs/<date>`, a note stem, or `people/<Name>`.
- You do not need to run `tasks` after `flush`.
- `flush` reports actions it did not add as new tasks:

  | Report | Meaning |
  |---|---|
  | `already a task` | The action matches an open task and was skipped |
  | `already buffered` | The action appears more than once in the buffer |
  | `due updated` | The action differs from an open task only by due date, so that task's due date moved |
  | `ambiguous` | The action matches several open tasks, so nothing changed |
- Do not edit `buffer.md` by hand. Use these subcommands.
- Exit `1`: line number is not an integer, is out of range or is empty, or validation fails.

### lint

Checks vault files against the schemas.

**When to use it**

- Before you commit.
- After you edit frontmatter by hand.
- When a file seems to be missing from listings.

**Usage**

```
lint [<path> ...]
```

| Argument | Meaning |
|---|---|
| `<path>` | Files to check. With none, it checks the whole vault |

**Options**

| Option | Effect |
|---|---|
| `--schemas <dir>` | Uses another schemas directory |
| `--quiet` | Prints nothing. Use the exit code only |

**Notes**

- Read-only.
- Errors print as `<path>:<line>: <message>`.
- Exit `0`: clean. Exit `1`: violations found. Exit `2`: no schemas loaded.

### commit

Reviews uncommitted vault changes, then commits them with git.

**When to use it**

- At the end of a work session.
- Before and after a large edit, so you can see and record what changed.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `review` | Shows everything changed since the last commit. Read-only | `commit review` |
| `save` | Stages every change in the vault and commits | `commit save --message "Northwind: scope review and October hours"` |

**Options**

| Option | Effect |
|---|---|
| `review --max-file-lines <N>` | Maximum diff lines per file. The default is 150 |
| `review --max-lines <N>` | Maximum lines overall. The default is 3000 |
| `save --message <text>` | Required. A single-line subject |
| `save --body <text>` | Commit body. It may span several lines |
| `save --dry-run` | Reports what would be staged and committed. Changes nothing |

**Notes**

- Run `review` first, then write the summary, then `save`.
- `save` only adds commits. It never amends, rebases, resets, checks out or pushes.
- Exit `1`: empty or multi-line `--message`, the vault is not a git repository, `ADULTING_HOME` is not the root of its repository, or a git command fails.

## Everyday procedures

### 1. Set up a new billable project

1. `people new --name "Sam Rivera" --category professional` — create the client contact.
2. `threads new --name Northwind --kind project --category professional --currency ZAR --rate 1500` — create the billable thread.
3. In `threads/Projects/Northwind.md`, add `client_name: Northwind` to the frontmatter. A PDF statement needs it.
4. `lint threads/Projects/Northwind.md` — check the thread file.
5. `threads show Projects/Northwind` — confirm the currency, rate and client fields.

### 2. Capture a meeting and turn its actions into tracked tasks

1. `notes new --type Meeting --topic "Scope review" --thread Projects/Northwind --person "Sam Rivera" --counterparty Northwind` — create the note and get its path.
2. Edit that file. Write each action as one line, for example `ACTION: (Sam Rivera) Send the revised scope`.
3. `tasks ingest` — turn the `ACTION:` lines into `TASK:` anchors.
4. `tasks list --thread Projects/Northwind` — check the new tasks and their uuids.
5. `notes minutes <stem>` — render the minutes to `~/Downloads`.
6. `buffer flush` — file the note's `REF:` pointer into today's log.

### 3. Quick-capture through the day, then file it

1. `buffer add "ask Sam about the invoice address"` — capture without choosing a thread.
2. `buffer add-text Projects/Northwind "Sam approved the revised scope"` — capture an observation on a known thread.
3. `buffer list` — review the queue and find line numbers.
4. `buffer rm <line-number>` — remove an `UNKNOWN:` line.
5. `buffer add-action Projects/Northwind "(Sam Rivera) Confirm the invoice address"` — re-add it in the right form.
6. `buffer tend` — validate. Fix anything it reports.
7. `buffer flush` — write the logs and create the tasks.

### 4. Work the task list

1. `tasks next` — see the top five.
2. `tasks list --overdue` — see what is late.
3. `tasks show <uuid>` — read one task in detail.
4. `tasks set-due <uuid> 2026-12-05` — move a date.
5. `tasks done <uuid>` — close a finished task.
6. `tasks drop <uuid>` — close an abandoned task. Then fix any dependents it lists.

### 5. Log a session of work

1. `hours log -m 90 Projects/Northwind Scope workshop` — record the time under a short invoice label.
2. `buffer add-text Projects/Northwind "Agreed phase two starts after sign-off"` — record what happened, so it can be searched.
3. `hours list Projects/Northwind --since 2026-11-01` — check the entry and get its id.
4. `hours edit <id> -m 120` — correct the duration if needed.
5. `buffer flush` — file both lines into the day's log.

### 6. Bill a client for a month's work

1. `hours list Projects/Northwind --since 2026-10-01 --until 2026-10-31` — check every entry for the month.
2. `hours edit <id> --description Scope workshop` — tidy any line item that will appear on the statement.
3. `hours report --thread Projects/Northwind --since 2026-10-01 --until 2026-10-31` — get the month's totals.
4. `payments statement --thread Projects/Northwind --as-of 2026-10-31` — check billed against received.
5. `payments statement --thread Projects/Northwind --as-of 2026-10-31 --opening 2026-10-01 --pdf ~/Downloads/northwind-statement.pdf` — write the PDF statement of account.

### 7. Record a payment

1. `payments log -c ZAR -d 2026-11-03 -a Business Projects/Northwind 18000` — record the receipt.
2. `payments list Projects/Northwind` — confirm it and get its id.
3. `payments statement --thread Projects/Northwind` — see the new balance.
4. `buffer flush` — file the payment's `REF:` pointer into that day's log.

### 8. Check the vault and commit it

1. `buffer flush` — file anything still queued.
2. `lint` — check the whole vault. Fix every reported line until it exits `0`.
3. `commit review` — read what changed.
4. `commit save --message "Northwind: October billing and November payment" --body "<detail>"` — commit everything.

## Data formats

`lint` enforces every format below.

### `hours_file`

The time entries for one thread. Location: `threads/<Kind>/<Name>/hours.md`. The body holds exactly one `simple-time-tracker` fenced block containing JSON `{"entries": [...]}`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to the thread whose folder holds this file |
| `currency` | no | Three-letter uppercase ISO code. Omitted for unbilled threads |
| entry `name` | yes | The description: an invoice line item |
| entry `startTime` | yes | UTC start, `YYYY-MM-DDTHH:MM:SS.mmmZ` |
| entry `endTime` | yes | UTC end, in the same form. Not before `startTime` |
| entry `id` | yes | 8 hex characters, unique across hours and payments |
| entry `rate` | yes | Hourly charge, a whole number. `0` means unbillable |
| entry `currency` | no | Three-letter ISO code. Absent or null means unbilled |

Duration is `endTime` minus `startTime`. There is no duration field.

### `log`

One thread's activity for one day, written by `buffer flush`. Location: `threads/<Kind>/<Name>/logs/<YYYY-MM-DD>.md`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to the thread whose folder holds this log |
| `date` | yes | The day, `YYYY-MM-DD` |
| `type` | yes | Always `Log` |

Body lines start with `TEXT:`, `REF:`, `ACTION:`, `TASK:`, `DONE:`, `DROPPED:` or `STAT:`.

### `note_correspondence`

A note recording an email, message or letter exchange. Location: `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md`, under its first thread.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about |
| `type` | yes | `Correspondence` |
| `threads` | yes | List of thread wikilinks. Each must resolve. The first sets the folder |
| `timestamp` | yes | When it happened, `YYYY-MM-DD-HH-MM-SS` |
| `people` | no | Participants: `[[people/<Name>]]` links or plain names |

Body lines can start with `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:` or `!:` (callout).

### `note_meeting`

A note recording a meeting. Location: `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md`, under its first thread.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the meeting was about |
| `type` | yes | `Meeting` |
| `threads` | yes | List of thread wikilinks. Each must resolve. The first sets the folder |
| `timestamp` | yes | When it happened, `YYYY-MM-DD-HH-MM-SS` |
| `counterparty` | no | The other party |
| `location` | no | Where it was held |
| `people` | no | Attendees: `[[people/<Name>]]` links or plain names |

Body lines can start with `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:` or `!:`. `notes minutes` shows the agreements, resolutions and action items. `notes pdf` shows the callouts and an action table.

### `note_simple`

A note of type Workshop, Report, Log, Research or Recipe. Location: `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md`, under its first thread.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about |
| `type` | yes | `Workshop`, `Report`, `Log`, `Research` or `Recipe` |
| `threads` | yes | List of thread wikilinks. Each must resolve. The first sets the folder |
| `timestamp` | yes | When it happened, `YYYY-MM-DD-HH-MM-SS` |
| `people` | no | `[[people/<Name>]]` links or plain names |

### `payments_file`

The money received against one thread. Location: `threads/<Kind>/<Name>/payments.md`. The body holds exactly one `adulting-payments` fenced block containing JSON `{"payments": [...]}`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to the thread whose folder holds this file |
| `currency` | yes | Three-letter uppercase ISO code |
| payment `id` | yes | 8 hex characters, unique across hours and payments |
| payment `received` | yes | UTC date and time received, `YYYY-MM-DDTHH:MM:SS.mmmZ` |
| payment `amount` | yes | Greater than 0. Refunds are not negative payments |
| payment `currency` | yes | Three-letter ISO code |
| payment `account` | no | The account the money landed in |
| payment `note` | no | Free text |

### `person`

A contact you track. Location: `people/<Name>.md`.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed` |
| `category` | yes | `professional`, `personal` or `voluntary` |
| `started` | yes | Start date, `YYYY-MM-DD` |
| `ended` | no | End date. Required when `status` is `closed` |
| `cadences` | no | List of `key`, `frequency`, `description` |

The body is free-form.

### `stat_line`

One value of a declared stat, written by `buffer flush`. It appears as a line in a log, `threads/<Kind>/<Name>/logs/<YYYY-MM-DD>.md`. Example: `STAT: pushups 25 <!--2026-10-07T07:42:10-->`.

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | A stat declared on this log's own thread |
| `value` | yes | A number. Must be a whole number for an `int` stat |
| `ts` | yes | Local time, `YYYY-MM-DDTHH:MM:SS`. Its date must match the log's date |

A `STAT:` line belongs only in a log.

### `task_anchor`

One `TASK:`, `DONE:` or `DROPPED:` line, the record of a task's state. It appears as a line in a note or log. Example: `TASK: [#H] (Sam Rivera) Send quarterly report <!--abcd1234 entry:2026-05-27 due:2026-05-29-->`.

| Field | Required | Meaning |
|---|---|---|
| `kind` | yes | `TASK` (open), `DONE` (finished) or `DROPPED` (abandoned) |
| `priority` | no | `H`, `M` or `L`, shown as `[#X]` |
| `assignee` | no | A person with a file in `people/` |
| `body` | yes | The task text |
| `uuid` | yes | 8 hex characters, unique across the vault |
| `entry` | yes | Date ingested |
| `end` | no | Date done or dropped. Required for `DONE` and `DROPPED`. Not before `entry` |
| `due` | no | Due date |
| `scheduled` | no | Scheduled date |
| `depends` | no | Comma-separated uuids of other tasks. No cycles allowed |

Change these lines only with `tasks` subcommands.

### `thread`

A project, process or topic. Location: `threads/<Kind>/<Name>.md`.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed` |
| `kind` | yes | `project`, `process` or `topic` |
| `category` | yes | `professional`, `personal` or `voluntary` |
| `started` | yes | Start date, `YYYY-MM-DD` |
| `ended` | no | End date. Required when `status` is `closed` |
| `cadences` | no | Recurring obligations: list of `key`, `frequency` (days), `description` |
| `stats` | no | Declared stats: list of `name`, `type`, `agg`. Written by `stats new` |
| `currency` | no | Default currency for `hours`. Three-letter uppercase ISO code |
| `rate` | no | Default hourly rate for `hours`, a whole number |
| `client_name` | no | The party billed. Needed for `payments statement --pdf` |
| `client_address` | no | Address, with lines separated by `\|` |
| `client_vat` | no | Client VAT number |
| `client_email` | no | Client email |

### `thread_entry`

A dated bullet at the top level of a thread file's body, in `threads/<Kind>/<Name>.md`. Example: `- 2024-05-17 — Made progress on rblncr.` Indented sub-bullets are not checked.

| Field | Required | Meaning |
|---|---|---|
| `date` | yes | `YYYY-MM-DD` |
| `text` | yes | The entry, after ` — ` |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `buffer tend` or `buffer flush` reports `UNKNOWN` lines and does not flush | Raw `buffer add` entries block a flush | `buffer list`, then `buffer rm <line-number>`, then re-add with `buffer add-text` or `buffer add-action` |
| `buffer flush` reports `ambiguous` | The action matches several open tasks | Use `tasks list` to find the task, then change it with `tasks set-*` |
| `hours log` or `hours edit` exits 1: `--rate needs a currency` | A rate was given with no currency | Add `-c <ISO>`, or set the thread's `currency` |
| `notes new` exits 1: `--person is only for Meeting and Correspondence notes` | Wrong option for the note type | Remove `--person`, or change `--type` |
| `notes pdf`, `minutes` or `agenda` exits 1: `PDF render failed` | `pandoc` or `xelatex` is missing or failed | Install `pandoc` and a LaTeX engine |
| `payments statement` exits 1: `--pdf needs --thread` | A statement is for one client | Add `--thread <Kind/Name>` |
| `payments statement` exits 1 because of `--opening` | `--opening` needs `--pdf` and cannot be used with `--since` or `--until` | Use `--opening` only with `--pdf`, and drop `--since` and `--until` |
| `tasks set-assignee` exits 1: `does not resolve to people/...` | No person file exists for that name | `people new --name "<name>" --category <category>` |
| `tasks done` exits 1: `no task found with uuid prefix` | The uuid prefix matches no task | `tasks list` and copy the uuid |
| `stats log` exits 1 because the name is not declared | The stat is not declared on any thread | `stats list`, or `stats new <name> --thread <Kind/Name> --type <type> --agg <agg>` |
| A file is missing from listings and searches | The file is not valid UTF-8, so it is skipped | Run `lint`. It reports `file is not valid UTF-8` |
| `commit save` exits 1: `not a git repository`, or `ADULTING_HOME` is not the root of its repository | The vault is not the root of a git repository | Make the vault folder the root of its own git repository |
| `lint` exits 2: `no schemas loaded` | The schemas directory is empty or wrong | Run `lint` without `--schemas`, or point `--schemas` at the right directory |

## Quick reference

| Command | Does |
|---|---|
| `tasks` | Ingests `ACTION:` lines into `TASK:` anchors |
| `tasks ingest` | Ingests `ACTION:` lines into `TASK:` anchors |
| `tasks add` | Adds an `ACTION:` to the buffer |
| `tasks done` | Marks a task done |
| `tasks drop` | Marks a task dropped |
| `tasks set-description` | Rewrites a task's text |
| `tasks set-assignee` | Changes a task's assignee |
| `tasks set-due` | Sets a task's due date |
| `tasks set-scheduled` | Sets a task's scheduled date |
| `tasks set-priority` | Sets a task's priority |
| `tasks add-depends` | Adds a task dependency |
| `tasks rm-depends` | Removes a task dependency |
| `tasks list` | Lists pending tasks |
| `tasks next` | Shows the top 5 pending tasks |
| `tasks show` | Shows one task |
| `notes new` | Creates a note |
| `notes list` | Lists notes |
| `notes cat` | Prints a note |
| `notes last` | Prints the newest note's path |
| `notes copy` | Copies a note to a new timestamp |
| `notes delete` | Permanently deletes a note |
| `notes pdf` | Renders a note to Markdown and PDF |
| `notes minutes` | Renders meeting minutes |
| `notes agenda` | Renders a meeting agenda |
| `search notes` | Finds notes |
| `search logs` | Finds daily logs |
| `search activity` | Ranks threads by activity |
| `search overview` | Shows one thread's whole picture |
| `search stream` | Shows every dated record as one timeline |
| `threads list` | Lists threads |
| `threads show` | Shows a thread file |
| `threads new` | Creates a thread |
| `people list` | Lists people |
| `people show` | Shows a person file |
| `people new` | Creates a person |
| `people delete` | Permanently deletes a person |
| `hours log` | Records a time entry |
| `hours list` | Lists time entries |
| `hours report` | Totals time by thread and currency |
| `hours show` | Shows one time entry |
| `hours edit` | Changes a time entry |
| `hours rm` | Permanently deletes a time entry |
| `payments log` | Records a payment |
| `payments list` | Lists payments |
| `payments statement` | Shows billed versus received, or writes a PDF statement |
| `payments show` | Shows one payment |
| `payments edit` | Changes a payment |
| `payments rm` | Permanently deletes a payment |
| `stats new` | Declares a stat on a thread |
| `stats list` | Lists declared stats |
| `stats log` | Adds a stat value to the buffer |
| `stats series` | Shows a stat over time |
| `buffer add` | Adds a raw `UNKNOWN:` capture |
| `buffer add-text` | Adds a `TEXT:` entry |
| `buffer add-ref` | Adds a `REF:` entry |
| `buffer add-action` | Adds an `ACTION:` entry |
| `buffer list` | Shows the buffer with line numbers |
| `buffer rm` | Removes one buffer line |
| `buffer tend` | Regroups and validates the buffer |
| `buffer flush` | Files the buffer into logs and creates tasks |
| `lint` | Checks vault files against the schemas |
| `commit review` | Shows uncommitted changes |
| `commit save` | Stages and commits all vault changes |
