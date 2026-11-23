# adulting — Operators Manual

## Before you start

All data lives in one folder, the vault. The default is `~/vault`. To use a different folder, set `ADULTING_HOME` to its path. Every command reads and writes paths under that folder.

You need these programs:

| Program | Needed by |
|---|---|
| Python 3.11 or newer | every tool |
| `git` | `commit` |
| `pandoc` and a LaTeX engine (`xelatex`) | `notes pdf`, `notes minutes`, `notes agenda`, `payments statement --pdf` |

The vault is plain text: Markdown, YAML frontmatter and JSON blocks. You can read it, grep it and back it up with ordinary tools.

No command prompts for input or opens an app. Every command runs from its arguments alone. Every path a command prints is absolute.

## How the pieces fit

`<Kind>` is `Projects`, `Processes` or `Topics`. All paths are relative to the vault root.

| Object | What it is | Where it lives |
|---|---|---|
| Thread | A project, process or topic that other records belong to | `threads/<Kind>/<Name>.md` |
| Note | A typed document: a meeting, correspondence, report and so on | `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md` |
| Log | One thread's activity for one day, written by `buffer flush` | `threads/<Kind>/<Name>/logs/<YYYY-MM-DD>.md` |
| Time entry | A session of work, billable or not | `threads/<Kind>/<Name>/hours.md` |
| Payment | Money received against a thread | `threads/<Kind>/<Name>/payments.md` |
| Person | A contact you track | `people/<Name>.md` |
| Action / task | An `ACTION:` line, rewritten in place as a `TASK:` anchor | inside a note or log |
| Buffer | The staging queue for quick captures | `buffer.md` |
| Config | Vault-wide settings: hours defaults and billing details | `.adulting/config.yaml` |

Everything that belongs to a thread lives in the thread's folder, beside the thread file.

How they link:

- A note names one or more threads in its `threads:` list. It is filed under the first one.
- A note's `people` list and a task's `(Assignee)` link to people files. A person is never a thread.
- A task lives in the note or log where its `ACTION:` line was written. There is no separate task store.
- A task can depend on other tasks by uuid.
- `notes new`, `hours log` and `payments log` each add a `REF:` line to the buffer. After `buffer flush`, that line appears in the thread's daily log.
- A stat is declared in a thread file's `stats:` frontmatter. Each value you log becomes a `STAT:` line in that thread's logs.
- `payments statement` compares billed hours with payments received.

## Command reference

### tasks

Turns `ACTION:` lines into tracked `TASK:` anchors and changes those anchors where they sit in the file.

**When to use it**

- You wrote `ACTION:` lines in a note or log and want them tracked.
- You want to see what is due, or what to do next.
- You want to close a task, reassign it or change its dates.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| *(none)* | Same as `ingest` | `tasks` |
| `ingest` | Rewrites every `ACTION:` line in notes and logs as a `TASK:` anchor with a new uuid | `tasks ingest --dry-run` |
| `add` | Adds an `ACTION` to the buffer. Same as `buffer add-action` | `tasks add Projects/Northwind "(Sam Rivera) Send the revised scope" --due 2026-12-05 --priority H` |
| `done` | Changes `TASK` to `DONE` and stamps `end` with today's date | `tasks done abcd1234` |
| `drop` | Changes `TASK` to `DROPPED` and stamps `end`. Lists open tasks that depend on it, without changing them | `tasks drop abcd1234` |
| `set-description` | Replaces the task's text | `tasks set-description abcd1234 "Send the final scope"` |
| `set-assignee` | Replaces the `(Assignee)` prefix | `tasks set-assignee abcd1234 "Sam Rivera"` |
| `set-due` | Sets the due date | `tasks set-due abcd1234 2026-12-12` |
| `set-scheduled` | Sets the scheduled date | `tasks set-scheduled abcd1234 2026-12-08` |
| `set-priority` | Sets the priority to `H`, `M` or `L` | `tasks set-priority abcd1234 H` |
| `add-depends` | Makes this task wait on another task | `tasks add-depends abcd1234 ef567890` |
| `rm-depends` | Removes a dependency | `tasks rm-depends abcd1234 ef567890` |
| `list` | Lists pending tasks, grouped by thread, then sorted by priority, due date and entry date | `tasks list --thread Projects/Northwind` |
| `next` | Shows the top 5 pending tasks by priority, due date and entry date | `tasks next` |
| `show` | Shows one task in detail | `tasks show abcd1234` |

Wherever a subcommand takes a uuid, any unique prefix of it works.

**Options**

| Option | Effect |
|---|---|
| `--dry-run` (bare `tasks`, `ingest`) | Shows what would be ingested and writes nothing |
| `--quiet` (bare `tasks`, `ingest`) | Hides the line printed for each action |
| `--due <YYYY-MM-DD>` (`add`) | Sets the due date |
| `--scheduled <YYYY-MM-DD>` (`add`) | Sets the scheduled date |
| `--priority <H\|M\|L>` (`add`) | Sets the priority |
| `--depends <uuid>` (`add`) | Adds a dependency on an 8-character uuid. You can repeat it |
| `--priority <H\|M\|L>` (`list`) | Shows only tasks with this priority |
| `--thread <Kind/Name>` (`list`) | Shows only tasks whose source note carries this thread |
| `--assignee <person>` (`list`) | Shows only tasks assigned to this person |
| `--overdue` (`list`) | Shows only tasks whose due date is before today |
| `--json` (`list`) | Prints JSON |

**Notes**

- Ingest and every `set-*`, `done`, `drop`, `add-depends` and `rm-depends` command rewrite the source note or log in place.
- Ingest skips a file it cannot read as UTF-8. Run `lint` to find such files.
- Exit 1 means one of these: no task matches the uuid prefix, the prefix is empty, the date is not `YYYY-MM-DD`, the description is empty, the person has no file in `people/`, or a task would depend on itself.

### notes

Creates, lists, prints, copies, deletes and renders notes. A note is named by its stem, the filename without `.md`.

**When to use it**

- You need a new meeting, correspondence or report note on a thread.
- You want to find a note's stem or read a note.
- You need a PDF, meeting minutes or an agenda to send out.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Creates a note and prints its path | `notes new --type Meeting --topic "Scope review" --thread Projects/Northwind --person "Sam Rivera"` |
| `list` | Lists notes, oldest first, with stem, date, type, threads and topic. Takes an optional case-insensitive filter | `notes list northwind` |
| `cat` | Prints a note | `notes cat 2026-09-10-14-30-00` |
| `last` | Prints the path of the newest note | `notes last` |
| `copy` | Copies a note to a new timestamp and adds ` COPY` to its topic | `notes copy 2026-09-10-14-30-00` |
| `delete` | Permanently deletes a note | `notes delete 2026-09-10-14-30-00 -y` |
| `pdf` | Renders the note to Markdown and PDF, with callouts and an action table | `notes pdf 2026-09-10-14-30-00` |
| `minutes` | Renders meeting minutes: agreements, resolutions and action items | `notes minutes 2026-09-10-14-30-00` |
| `agenda` | Renders an agenda: the note with its outcome sections emptied | `notes agenda 2026-09-10-14-30-00 --out ~/Desktop` |

**Options**

| Option | Effect |
|---|---|
| `--type <type>` (`new`, required) | One of `Meeting`, `Correspondence`, `Workshop`, `Report`, `Log`, `Research`, `Recipe` |
| `--topic <text>` (`new`, required) | What the note is about |
| `--thread <Kind/Name>` (`new`, required) | A thread the note belongs to. You can repeat it. The first thread decides where the file goes |
| `--person <name>` (`new`) | An attendee. You can repeat it. Only for `Meeting` and `Correspondence`. It becomes a link when `people/<name>.md` exists |
| `--counterparty <text>` (`new`) | The other party. Only for `Meeting` |
| `--location <text>` (`new`) | Where the meeting was held. Only for `Meeting` |
| `--json` (`list`) | Prints JSON |
| `-y`, `--yes` (`delete`) | Confirms the delete. Without it, nothing is deleted |
| `--out <DIR>` (`pdf`, `minutes`, `agenda`) | Where to write the output. The default is `~/Downloads` |

**Notes**

- Every subcommand except `new` runs a task ingest first. This means `list`, `cat` and the renders can rewrite `ACTION:` lines in place. If an ACTION cannot be ingested, the command carries on.
- Renders write `<stem>.md` and `<stem>.md.pdf`.
- `delete` cannot be undone.
- Exit 1 means one of these: a `--person`, `--counterparty` or `--location` flag was used on the wrong note type, the topic is empty, the stem is malformed, the vault has no notes, or the PDF render failed.

### search

Finds notes and logs and summarises activity. It returns paths and metadata, never document bodies.

**When to use it**

- You need notes or logs about a thread, a person or a phrase.
- You want to see which threads were active in a period.
- You want the whole picture of one thread or one person.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `notes` | Finds notes by thread, type, person, date or text | `search notes --thread Projects/Northwind --type Meeting` |
| `logs` | Finds daily logs by thread, person, date or text | `search logs --text "revised scope"` |
| `activity` | Ranks threads by what happened in a time window | `search activity --since 2026-10-01 --until 2026-10-31` |
| `overview` | Shows the whole picture of one thread | `search overview Projects/Northwind` |
| `person` | Shows the whole picture of one person | `search person "Sam Rivera"` |
| `stream` | Merges every dated record into one timeline | `search stream --today` |

**Options**

| Option | Effect |
|---|---|
| `--thread <Kind/Name>` (`notes`, `logs`, `activity`, `stream`) | Limits results to one thread |
| `--person <name>` (`notes`, `logs`, `activity`, `stream`) | Matches a declared person by full name or a unique part of it. In `activity`, hours are not counted |
| `--type <type>` (`notes`) | Matches the note type. Not case-sensitive |
| `--text <text>` (`notes`, `logs`, `stream`) | Matches literal text, case-insensitive |
| `--since <YYYY-MM-DD>`, `--until <YYYY-MM-DD>` (all) | Sets the date window. Both ends are inclusive |
| `--limit <N>` | Caps the number of results. Defaults: 20 for `notes` and `logs`, 5 for `overview` and `person`, 100 for `stream`. `0` means all |
| `--kind <list>` (`stream`) | Comma-separated: `note`, `log`, `task`, `done`, `dropped`, `hours`, `payment`, `thread`, `person`, `pending` |
| `--today` (`stream`) | Shows today only |
| `--reverse` (`stream`) | Shows oldest first. The default is newest first |
| `--json` (all) | Prints JSON |

**Notes**

- Read-only.
- Dates are event dates: a note's frontmatter `timestamp`, not its filename. The filename is used only when the timestamp is missing or malformed.
- Exit 1 means `--kind` got an unknown kind.

### threads

Creates, lists and shows thread files.

**When to use it**

- You are starting a new project, process or topic.
- You need a thread's exact name or its settings.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists threads, open ones only by default. Takes an optional fuzzy query | `threads list north` |
| `show` | Shows one thread file | `threads show Projects/Northwind` |
| `new` | Creates a thread file | `threads new --name Northwind --kind project --category professional --currency ZAR --rate 1500` |

**Options**

| Option | Effect |
|---|---|
| `--all` (`list`) | Includes paused and closed threads |
| `--json` (`list`, `show`) | Prints JSON |
| `--name <name>` (`new`, required) | The thread name, which becomes the filename. It cannot contain `/` or start with `.` |
| `--kind <project\|process\|topic>` (`new`, required) | Puts the thread under `Projects`, `Processes` or `Topics` |
| `--category <professional\|personal\|voluntary>` (`new`, required) | The thread category |
| `--currency <ISO>` (`new`) | The default currency for `hours`, as a 3-letter code. A thread with a currency is billable |
| `--rate <N>` (`new`) | The default hourly rate for `hours`. It needs `--currency` |

**Notes**

- There is no close or delete command. To close a thread, set `status: closed` and `ended:` in its frontmatter. To remove a thread, delete its file and its folder by hand.
- Exit 1 means one of these: the thread already exists, the name is empty or invalid, or `--rate` was given without `--currency`.

### people

Creates, lists, shows and deletes person files.

**When to use it**

- Before you assign a task to someone or link them as a meeting attendee.
- To look up how a person's name is spelled in the vault.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists people, open ones only by default. Takes an optional fuzzy query | `people list sam` |
| `show` | Shows one person file | `people show "Sam Rivera"` |
| `new` | Creates a person file | `people new --name "Sam Rivera" --category professional` |
| `delete` | Permanently deletes a person file | `people delete "Sam Rivera" -y` |

**Options**

| Option | Effect |
|---|---|
| `--all` (`list`) | Includes closed people |
| `--json` (`list`, `show`) | Prints JSON |
| `--name <full name>` (`new`, required) | The full name, which becomes the filename |
| `--category <professional\|personal\|voluntary>` (`new`, required) | The relationship category |
| `-y`, `--yes` (`delete`) | Confirms the delete |

**Notes**

- `delete` cannot be undone. Without `-y` it refuses and exits 1.
- Exit 1 also means: the person already exists, the name is empty or invalid, or the person was not found.

### hours

Records time spent on a thread, billable or not.

**When to use it**

- You finished a session of client work.
- You want to track personal time, such as reading or exercise.
- You need totals for an invoice.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Adds an entry | `hours log Projects/Northwind -m 90 Scope workshop preparation` |
| `list` | Lists entries, optionally for one thread | `hours list Projects/Northwind --since 2026-10-01` |
| `report` | Totals time by thread and currency. Unbilled time is totalled separately | `hours report --since 2026-10-01 --until 2026-10-31` |
| `show` | Shows one entry | `hours show 1a2b3c4d` |
| `edit` | Changes one field of an entry | `hours edit 1a2b3c4d -m 120` |
| `rm` | Deletes an entry | `hours rm 1a2b3c4d -y` |

**Options**

| Option | Effect |
|---|---|
| `-m`, `--minutes <N>` (`log`) | Sets the duration. The default is 60 |
| `-r`, `--rate <N>` (`log`) | Sets the hourly rate. `0` means unbillable |
| `-c`, `--currency <ISO>` (`log`) | Sets the currency. The default is the thread's. With no currency at all, the entry is recorded as unbilled |
| `-d`, `--date <YYYY-MM-DD>` (`log`) | Sets the day. The default is today |
| `-t`, `--time <HH:MM>` (`log`) | Sets the start time. The default is now |
| `--thread <Kind/Name>` (`report`) | Limits the report to one thread |
| `--since`, `--until <YYYY-MM-DD>` (`list`, `report`) | Sets the date window |
| `--json` (`list`, `report`, `show`) | Prints JSON |
| `--description <text>` (`edit`) | Sets a new description |
| `-m`, `--minutes <N>` (`edit`) | Sets a new duration. The start time stays the same |
| `-r`, `--rate <N>` (`edit`) | Sets a new rate. The entry must have a currency |
| `-c`, `--currency <ISO>` (`edit`) | Sets a new currency |
| `-d`, `--date <YYYY-MM-DD>` (`edit`) | Moves the entry to another day. The duration stays the same |
| `-t`, `--time <HH:MM>` (`edit`) | Moves the start time. The duration stays the same |
| `-y`, `--yes` (`rm`) | Confirms the delete |

**Notes**

- The description is the invoice line item. Keep it short. Put detail in a log line instead, because `search` does not index hours.
- The rate and currency are fixed on each entry when you write it. Changing the thread's defaults later does not re-price old entries.
- If the thread has no `rate`, `hours` uses `hours.rate` from `.adulting/config.yaml`, then 2500.
- `log` also adds a `REF:` line to the buffer, filed under the day the work happened.
- `rm` cannot be undone.
- Exit 1 means one of these: the description is empty, `--minutes` is not positive, or a rate was given with no currency.

### payments

Records money received against a thread and compares it with what was billed.

**When to use it**

- A client paid you.
- You need a statement of account for a client, as a table or a PDF.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Records a payment | `payments log Projects/Northwind 15000 -a "Business account" -n "October invoice"` |
| `list` | Lists payments, optionally for one thread | `payments list Projects/Northwind` |
| `statement` | Shows billed against received, by thread and currency | `payments statement --thread Projects/Northwind --pdf ~/Downloads/northwind-statement.pdf` |
| `show` | Shows one payment | `payments show 5e6f7a8b` |
| `edit` | Changes one field of a payment | `payments edit 5e6f7a8b --amount 15500` |
| `rm` | Deletes a payment | `payments rm 5e6f7a8b -y` |

**Options**

| Option | Effect |
|---|---|
| `-c`, `--currency <ISO>` (`log`, `edit`) | Sets the currency. On `log`, the default is the thread's |
| `-d`, `--date <YYYY-MM-DD>` (`log`, `edit`) | Sets the date received. On `log`, the default is today |
| `-t`, `--time <HH:MM>` (`log`, `edit`) | Sets the time received. On `log`, the default is now |
| `-a`, `--account <text>` (`log`, `edit`) | Records which account the money landed in |
| `-n`, `--note <text>` (`log`, `edit`) | Adds a free-text note |
| `--amount <N>` (`edit`) | Sets a new amount |
| `--thread <Kind/Name>` (`statement`) | Limits the statement to one thread |
| `--since`, `--until <YYYY-MM-DD>` (`list`, `statement`) | Sets the date window |
| `--as-of <YYYY-MM-DD>` (`statement`) | Sets the statement date, which drives aging. The default is today |
| `--pdf <path>` (`statement`) | Renders a PDF to this path. Needs `--thread` |
| `--opening <YYYY-MM-DD>` (`statement`) | Sets the first day the PDF ledger shows. Earlier entries become one balance-brought-forward line. Needs `--pdf` and cannot be combined with `--since` or `--until` |
| `--json` (`list`, `statement`, `show`) | Prints JSON |
| `-y`, `--yes` (`rm`) | Confirms the delete |

**Notes**

- Amounts must be positive. A refund is not a negative payment.
- `statement` ignores unbilled hours.
- A statement PDF needs `client_name` in the thread file's frontmatter.
- `log` also adds a `REF:` line to the buffer, filed under the day the money was received.
- `rm` cannot be undone.
- Exit 1 means one of these: the amount is missing or not positive, `--pdf` was given without `--thread`, `--opening` was given without `--pdf` or together with `--since`/`--until`, or `--opening` is after `--as-of`.

### stats

Records numbers against declared stats, such as push-ups, steps or money spent, and shows them over time.

**When to use it**

- You want to track a number per day, week or month.
- You want to record that an event happened. Declare an `int` stat and log `1` each time.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Declares a stat in a thread file's frontmatter | `stats new pushups --thread Topics/Fitness --type int --agg sum` |
| `list` | Lists declared stats | `stats list` |
| `log` | Adds a value to the buffer | `stats log pushups 25` |
| `series` | Shows the stat's value per period, from logs and the unflushed buffer | `stats series pushups --by week` |

**Options**

| Option | Effect |
|---|---|
| `--thread <Kind/Name>` (`new`, required) | The thread that owns the stat |
| `--type <int\|decimal>` (`new`, required) | `int` takes whole numbers. `decimal` takes plain numbers such as `12.50` |
| `--agg <sum\|last\|max>` (`new`, required) | How a period's values combine: `sum` adds them, `last` takes the latest, `max` takes the largest |
| `-d`, `--date <YYYY-MM-DD>` (`log`) | Sets the day. The default is today |
| `-t`, `--time <HH:MM>` (`log`) | Sets the time. The default is now |
| `--by <day\|week\|month>` (`series`) | Sets the period length. The default is `day`. Weeks start on Monday |
| `--since`, `--until <YYYY-MM-DD>` (`series`) | Sets the date window |
| `--json` (`list`, `series`) | Prints JSON |

**Notes**

- A stat name uses lowercase letters, digits and `-`, and must be unique across the vault.
- `new` edits the thread file in place. There is no rename or delete command.
- In `series`, a period with no values shows `-` (or `null` in JSON), not `0`.
- Exit 1 means nothing was written. The usual causes: the name is undeclared or declared twice, the value has the wrong type, the date or time is malformed, `new` was given a bad or duplicate name or a thread that does not resolve, or `--since` is after `--until`.
- Exit 2 is a usage error: a missing argument, or an unknown `--type` or `--agg`.

### buffer

Manages `buffer.md`, the staging queue. Captures wait here until `flush` files them into each thread's daily log.

**When to use it**

- You want to jot something down now and file it later.
- You want to add an observation, a cross-reference or an action to a thread's log.
- At the end of the day, to file everything that is waiting.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `add` | Adds a raw `UNKNOWN` entry with no thread | `buffer add "ask Sam about the invoice date"` |
| `add-text` | Adds a `TEXT` observation | `buffer add-text Projects/Northwind "Client approved the revised scope"` |
| `add-ref` | Adds a `REF` pointer to another vault file | `buffer add-ref Projects/Northwind 2026-09-10-14-30-00 "Kickoff notes"` |
| `add-action` | Adds an `ACTION`. Same as `tasks add` | `buffer add-action Projects/Northwind "(Sam Rivera) Confirm workshop date" --due 2026-12-05` |
| `list` | Shows the buffer with line numbers. Takes an optional case-insensitive filter | `buffer list` |
| `rm` | Removes one line by its number | `buffer rm 3` |
| `tend` | Regroups entries by thread and date, then validates them. Safe to run repeatedly | `buffer tend` |
| `flush` | Runs `tend`, writes entries to each thread's logs, empties the buffer and ingests the flushed actions as tasks | `buffer flush` |

**Options**

Global: `--quiet` hides info output. Put it before the subcommand, for example `buffer --quiet flush`.

| Option | Effect |
|---|---|
| `--date <YYYY-MM-DD>` (`add`, `add-text`, `add-ref`, `add-action`) | Files the entry under this day. Use the day the thing happened |
| `--due <YYYY-MM-DD>` (`add-action`) | Sets the due date |
| `--scheduled <YYYY-MM-DD>` (`add-action`) | Sets the scheduled date |
| `--priority <H\|M\|L>` (`add-action`) | Sets the priority |
| `--depends <uuid>` (`add-action`) | Adds a dependency on an 8-character uuid. You can repeat it |
| `--json` (`list`) | Prints JSON |

**Notes**

- A `REF` target can be `<Kind>/<Name>`, `<Kind>/<Name>/hours`, `<Kind>/<Name>/payments`, `<Kind>/<Name>/logs/<date>`, a note's stem, or `people/<Name>`.
- `UNKNOWN` entries block `flush`. To fix one, remove it with `rm` and add it again with the matching `add-*` command.
- You do not need to run `tasks` after `flush`. During ingest, `flush` handles flushed ACTIONs that match open tasks like this:
  - An ACTION that is already an open task is skipped and reported as `already a task`.
  - A repeat within the buffer is reported as `already buffered`.
  - An ACTION that differs from an open task only by due date moves that task's due date. This is reported as `due updated`.
  - An ACTION that matches several open tasks changes nothing and is reported as `ambiguous`.
- Change the buffer only through these commands. Do not edit `buffer.md` by hand.
- Exit 1 from `rm` means the line number is not an integer, is out of range, or points to an empty line.

### lint

Checks vault files against the schemas.

**Usage**

```
lint [--quiet] [--schemas <dir>] [<path> ...]
```

| Argument | Meaning |
|---|---|
| `<path> ...` | The files to check. With no paths, `lint` checks the whole vault |

**Options**

| Option | Effect |
|---|---|
| `--quiet` | Prints nothing and reports through the exit code only |
| `--schemas <dir>` | Uses a different schemas directory |

**Notes**

- Read-only.
- Exit 0 means the files are clean. Exit 1 means there are violations. Exit 2 means no schemas were loaded.
- Each error prints as `<path>:<line>: <message>`.
- `lint` reports files that are not valid UTF-8, as `file is not valid UTF-8`. Other commands skip those files without saying so.

### commit

Reviews vault changes, then commits them to git.

**When to use it**

- At the end of a work session, to record what changed.
- Before you make risky edits, so you have a clean point to go back to.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `review` | Shows everything that changed since the last commit. Read-only | `commit review` |
| `save` | Stages every change in the vault and commits it | `commit save --message "Northwind: October hours and payment"` |

**Options**

| Option | Effect |
|---|---|
| `--max-file-lines <N>` (`review`) | Sets the most diff lines shown per file. The default is 150 |
| `--max-lines <N>` (`review`) | Sets the most output lines overall. The default is 3000 |
| `--message <text>` (`save`, required) | Sets the commit subject. It must be one line and not empty |
| `--body <text>` (`save`) | Sets the commit body. It can span several lines |
| `--dry-run` (`save`) | Reports what would be staged and committed, and changes nothing |

**Notes**

- `save` only ever adds a commit. It never amends, rebases, resets, checks out or pushes.
- Exit 1 means one of these: the message is empty or has more than one line, the vault is not a git repository, `ADULTING_HOME` is not the root of its git repository, or a git command failed.

## Everyday procedures

### 1. Set up a new billable project

1. `threads new --name Northwind --kind project --category professional --currency ZAR --rate 1500` creates the thread with its billing defaults.
2. `people new --name "Sam Rivera" --category professional` creates the client contact.
3. `threads show Projects/Northwind` checks the result. Add `client_name` to the frontmatter by hand if you will send statements.
4. `lint` confirms the new files are valid.

### 2. Capture a meeting and turn its actions into tracked tasks

1. `notes new --type Meeting --topic "Scope review" --thread Projects/Northwind --person "Sam Rivera" --counterparty Northwind --location "Video call"` creates the note and prints its path.
2. Open that path and write the meeting. Put each action on its own line, as `ACTION: (Sam Rivera) Send the revised scope`.
3. `tasks` rewrites every `ACTION:` line as a `TASK:` anchor.
4. `tasks list --thread Projects/Northwind` shows the new tasks with their uuids.
5. `notes list "Scope review"` finds the note's stem.
6. `notes minutes <stem>` renders the minutes to `~/Downloads`.

### 3. Quick-capture through the day, then file it

1. `buffer add "ask Sam about the invoice date"` captures a thought without a thread.
2. `buffer add-text Projects/Northwind "Client approved the revised scope"` captures an observation on a known thread.
3. `buffer list` shows every entry with its line number.
4. `buffer rm <line-number>` removes an `UNKNOWN` entry once you know where it belongs.
5. `buffer add-action Projects/Northwind "(Sam Rivera) Confirm the invoice date"` adds that entry back in its proper form.
6. `buffer tend` validates the buffer. Fix anything it reports.
7. `buffer flush` files everything into the daily logs and creates tasks from the actions.

### 4. Work the task list

1. `tasks next` shows the top five pending tasks.
2. `tasks list --overdue` shows tasks that are past due.
3. `tasks show <uuid>` shows the detail for one task.
4. `tasks set-due <uuid> <YYYY-MM-DD>` moves a deadline.
5. `tasks done <uuid>` closes a finished task.
6. `tasks drop <uuid>` closes an abandoned task and lists any tasks that still depend on it.

### 5. Log a session of work

1. `hours log Projects/Northwind -m 90 Scope workshop preparation` records the time under a short invoice label.
2. `buffer add-text Projects/Northwind "Drafted three workshop options; option B needs Sam's sign-off"` records what actually happened, so it can be searched later.
3. `hours list Projects/Northwind --since <YYYY-MM-DD>` checks the entry.
4. `buffer flush` files the log line and the time entry's `REF:` into the day's log.

### 6. Bill a client for a month's work

1. `hours report --thread Projects/Northwind --since 2026-10-01 --until 2026-10-31` totals the month.
2. `hours list Projects/Northwind --since 2026-10-01 --until 2026-10-31` lists the line items.
3. `hours edit <id> --description <text>` corrects a label before you send anything.
4. `threads show Projects/Northwind` confirms `client_name` is set.
5. `payments statement --thread Projects/Northwind --pdf ~/Downloads/northwind-statement.pdf` renders the statement of account.

### 7. Record a payment

1. `payments log Projects/Northwind 15000 -a "Business account" -n "October invoice"` records the payment.
2. `payments list Projects/Northwind` confirms it.
3. `payments statement --thread Projects/Northwind` shows the updated balance.
4. `buffer flush` files the payment's `REF:` into the day's log.

### 8. Check the vault and commit it

1. `buffer flush` files anything still waiting in the buffer.
2. `lint` checks every file. Fix all violations until it exits 0.
3. `commit review` shows what changed since the last commit.
4. `commit save --dry-run --message "<summary>"` previews the commit.
5. `commit save --message "<summary>" --body "<detail>"` stages and commits everything.

## Data formats

`lint` enforces every schema below. Paths are relative to the vault root.

### `hours_file`

A thread's time entries, kept as JSON inside one `simple-time-tracker` fenced block. Path: `threads/<Kind>/<Name>/hours.md`. Maintained by `hours`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | A wikilink to the thread that owns this folder |
| `currency` | no | The file's 3-letter ISO currency. Left out for unbilled threads |
| entry `name` | yes | What was done. This is the invoice line item |
| entry `startTime` | yes | The start, as an ISO 8601 UTC timestamp |
| entry `endTime` | yes | The end, in the same form. It is not earlier than `startTime` |
| entry `id` | yes | 8 hex characters, unique across all hours and payments |
| entry `rate` | yes | The whole-number hourly charge. `0` means unbillable |
| entry `currency` | no | A 3-letter ISO code. Absent or null means unbilled |

The duration is `endTime` minus `startTime`. There is no duration field.

### `log`

One thread's activity for one day, written by `buffer flush`. Path: `threads/<Kind>/<Name>/logs/<YYYY-MM-DD>.md`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | A wikilink to the thread that owns this folder |
| `date` | yes | The day, as `YYYY-MM-DD` |
| `type` | yes | Always `Log` |

Body lines start with `TEXT:`, `REF:`, `ACTION:`, `TASK:`, `DONE:`, `DROPPED:` or `STAT:`.

### `note_correspondence`

A record of emails, messages or letters. Path: `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md`, under the first thread it names.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about |
| `type` | yes | Always `Correspondence` |
| `threads` | yes | A list of thread wikilinks. Each must resolve |
| `timestamp` | yes | When it happened, as `YYYY-MM-DD-HH-MM-SS` |
| `people` | no | Participants, as `[[people/X]]` links or plain names |

Body markers: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:`, and `!:` for callouts.

### `note_meeting`

A record of a meeting. Path: `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md`, under the first thread it names.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the meeting was about |
| `type` | yes | Always `Meeting` |
| `threads` | yes | A list of thread wikilinks. Each must resolve |
| `timestamp` | yes | When it happened, as `YYYY-MM-DD-HH-MM-SS` |
| `counterparty` | no | The other party |
| `location` | no | Where it was held |
| `people` | no | Attendees, as `[[people/X]]` links or plain names |

Body markers: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:`, and `!:` for callouts.

### `note_simple`

A Workshop, Report, Log, Research or Recipe note. Path: `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md`, under the first thread it names.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about |
| `type` | yes | `Workshop`, `Report`, `Log`, `Research` or `Recipe` |
| `threads` | yes | A list of thread wikilinks. Each must resolve |
| `timestamp` | yes | When it happened, as `YYYY-MM-DD-HH-MM-SS` |
| `people` | no | `[[people/X]]` links or plain names |

Body markers: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:`, and `!:` for callouts.

### `payments_file`

A thread's payments, kept as JSON inside one `adulting-payments` fenced block. Path: `threads/<Kind>/<Name>/payments.md`. Maintained by `payments`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | A wikilink to the thread that owns this folder |
| `currency` | yes | A 3-letter ISO code |
| payment `id` | yes | 8 hex characters, unique across all hours and payments |
| payment `received` | yes | When the money landed, as an ISO 8601 UTC timestamp |
| payment `amount` | yes | A number greater than zero |
| payment `currency` | yes | A 3-letter ISO code |
| payment `account` | no | The account the money landed in |
| payment `note` | no | Free text |

### `person`

A contact you track. Path: `people/<Name>.md`.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed` |
| `category` | yes | `professional`, `personal` or `voluntary` |
| `started` | yes | The start date, as `YYYY-MM-DD` |
| `ended` | when closed | The end date, as `YYYY-MM-DD`. Required when `status` is `closed` |
| `cadences` | no | Recurring obligations, each with `key`, `frequency` and `description` |

### `stat_line`

One logged value of a stat, as a line in a log file under `threads/<Kind>/<Name>/logs/`. For example: `STAT: pushups 25 <!--2026-10-07T07:42:10-->`.

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | A stat declared on this log's own thread |
| `value` | yes | A number. It must be a whole number for an `int` stat |
| `ts` | yes | Local time, as `YYYY-MM-DDTHH:MM:SS`. Its date must match the log's date |

### `task_anchor`

One `TASK:`, `DONE:` or `DROPPED:` line in a note or log. Change it only with `tasks`. For example: `TASK: [#H] (Sam Rivera) Send quarterly report <!--abcd1234 entry:2026-05-27 due:2026-05-29-->`.

| Field | Required | Meaning |
|---|---|---|
| `kind` | yes | `TASK` is open, `DONE` is finished, `DROPPED` is abandoned |
| `priority` | no | `H`, `M` or `L`, shown as `[#X]` |
| `assignee` | no | A person who must have a file in `people/` |
| `body` | yes | The task text |
| `uuid` | yes | 8 hex characters, unique across the vault |
| `entry` | yes | The date the task was ingested |
| `end` | for DONE and DROPPED | The date it was finished or dropped. Not earlier than `entry` |
| `due` | no | The due date |
| `scheduled` | no | The scheduled date |
| `depends` | no | Comma-separated uuids of other tasks. Dependencies cannot form a loop |

### `thread`

A project, process or topic. Path: `threads/<Kind>/<Name>.md`.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed` |
| `kind` | yes | `project`, `process` or `topic` |
| `category` | yes | `professional`, `personal` or `voluntary` |
| `started` | yes | The start date, as `YYYY-MM-DD` |
| `ended` | when closed | The end date. Required when `status` is `closed` |
| `cadences` | no | Recurring obligations, each with `key`, `frequency` in days, and `description` |
| `stats` | no | Declared stats, each with `name`, `type` and `agg`. Written by `stats new` |
| `currency` | no | The default 3-letter ISO currency for `hours`. Setting it makes the thread billable |
| `rate` | no | The default whole-number hourly rate for `hours` |
| `client_name` | no | The billed party on a statement. Required to render a statement PDF |
| `client_address` | no | The client's address, with lines separated by `\|` |
| `client_vat` | no | The client's VAT number |
| `client_email` | no | The client's email address |

### `thread_entry`

A dated top-level bullet in a thread file's body, such as `- 2024-05-17 — Made progress on the rollout.`

| Field | Required | Meaning |
|---|---|---|
| `date` | yes | The date, as `YYYY-MM-DD` |
| `text` | yes | The entry text. It cannot be empty |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `buffer tend` reports violations and `buffer flush` will not file | The buffer holds an `UNKNOWN` entry from `buffer add` | Run `buffer list`, then `buffer rm <line-number>`, then re-add the entry with `buffer add-text`, `add-ref` or `add-action` |
| `lint` prints `<path>:0: file is not valid UTF-8` | A file in the vault is not UTF-8. Other commands skip it silently | Re-save the file as UTF-8, or remove it |
| `--rate needs a currency` | You gave a rate with no currency to express it in | Add `--currency <ISO>` to `threads new`, or `-c <ISO>` to `hours log` or `hours edit` |
| `no task found with uuid prefix ...` | The uuid prefix matches no task | Run `tasks list` and copy the uuid |
| `person ... does not resolve to people/....md` | The assignee has no person file | Run `people new --name "<name>" --category <category>` |
| `refusing to delete ... without -y` | A delete was run without confirmation | Add `-y` if you really mean to delete |
| `already exists: <path>` | `threads new` or `people new` was given a name already in use | Use the existing file, or choose another name |
| `--pdf needs --thread; a statement is per client` | You asked for a statement PDF without naming a thread | Add `--thread <Kind/Name>` |
| `--opening needs --pdf`, or `--opening cannot be combined with --since or --until` | You used `--opening` incorrectly | Use `--opening` only with `--pdf`, and without `--since` or `--until` |
| `buffer flush` reports `ambiguous` | A flushed ACTION matches several open tasks, so nothing changed | Change the task you mean directly with `tasks set-*` |
| `commit` fails with `not a git repository`, or `ADULTING_HOME ... is not the root of its git repository` | The vault is not its own git repository root | Make the vault folder the root of a git repository, then run `commit` again |
| `lint` exits 2 with `no schemas loaded` | `--schemas` points at a folder with no schemas | Remove `--schemas`, or point it at the schemas directory |

## Quick reference

| Command | Does |
|---|---|
| `tasks` | Turns `ACTION:` lines into `TASK:` anchors |
| `tasks ingest` | Same as bare `tasks` |
| `tasks add <thread> <text>` | Adds an ACTION to the buffer |
| `tasks done <uuid>` | Marks a task done |
| `tasks drop <uuid>` | Marks a task dropped |
| `tasks set-description <uuid> <text>` | Replaces a task's text |
| `tasks set-assignee <uuid> <person>` | Reassigns a task |
| `tasks set-due <uuid> <date>` | Sets the due date |
| `tasks set-scheduled <uuid> <date>` | Sets the scheduled date |
| `tasks set-priority <uuid> <H\|M\|L>` | Sets the priority |
| `tasks add-depends <uuid> <dep-uuid>` | Adds a dependency |
| `tasks rm-depends <uuid> <dep-uuid>` | Removes a dependency |
| `tasks list` | Lists pending tasks |
| `tasks next` | Shows the top 5 pending tasks |
| `tasks show <uuid>` | Shows one task |
| `notes new --type <T> --topic <X> --thread <K/N>` | Creates a note |
| `notes list` | Lists notes |
| `notes cat <stem>` | Prints a note |
| `notes last` | Prints the newest note's path |
| `notes copy <stem>` | Copies a note |
| `notes delete <stem> -y` | Deletes a note |
| `notes pdf <stem>` | Renders a note to Markdown and PDF |
| `notes minutes <stem>` | Renders meeting minutes |
| `notes agenda <stem>` | Renders a meeting agenda |
| `search notes` | Finds notes |
| `search logs` | Finds daily logs |
| `search activity` | Ranks threads by activity |
| `search overview <thread>` | Summarises one thread |
| `search person <person>` | Summarises one person |
| `search stream` | Shows a merged timeline |
| `threads list` | Lists threads |
| `threads show <thread>` | Shows a thread |
| `threads new --name <N> --kind <K> --category <C>` | Creates a thread |
| `people list` | Lists people |
| `people show <person>` | Shows a person |
| `people new --name <N> --category <C>` | Creates a person |
| `people delete <person> -y` | Deletes a person |
| `hours log <thread> <description>` | Records time |
| `hours list` | Lists time entries |
| `hours report` | Totals time |
| `hours show <id>` | Shows one entry |
| `hours edit <id>` | Changes an entry |
| `hours rm <id> -y` | Deletes an entry |
| `payments log <thread> <amount>` | Records a payment |
| `payments list` | Lists payments |
| `payments statement` | Shows billed against received |
| `payments show <id>` | Shows one payment |
| `payments edit <id>` | Changes a payment |
| `payments rm <id> -y` | Deletes a payment |
| `stats new <name> --thread <T> --type <t> --agg <a>` | Declares a stat |
| `stats list` | Lists stats |
| `stats log <name> <value>` | Adds a stat value to the buffer |
| `stats series <name>` | Shows a stat over time |
| `buffer add <text>` | Quick-captures an UNKNOWN entry |
| `buffer add-text <thread> <text>` | Adds a TEXT entry |
| `buffer add-ref <thread> <target>` | Adds a REF entry |
| `buffer add-action <thread> <text>` | Adds an ACTION entry |
| `buffer list` | Shows the buffer |
| `buffer rm <line-number>` | Removes a buffer line |
| `buffer tend` | Regroups and validates the buffer |
| `buffer flush` | Files the buffer into logs and ingests tasks |
| `lint` | Validates the vault |
| `commit review` | Shows uncommitted changes |
| `commit save --message <text>` | Stages and commits everything |
