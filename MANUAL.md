# adulting — Operators Manual

## Before you start

All data lives in one directory, the vault. The default is `~/vault`. Set `ADULTING_HOME` to use a different directory. Every command reads and writes under it.

```sh
export ADULTING_HOME=~/vault
```

External programs:

| Program | Needed by |
|---|---|
| Python 3.11 or newer | every tool |
| `git` | `commit` |
| `pandoc` and a LaTeX engine (`xelatex`) | `notes pdf`, `notes minutes`, `notes agenda` |

Everything is plain text on disk: Markdown with YAML frontmatter, plus JSON blocks inside Markdown. You can read the files, grep them and back them up with your own tools.

No command prompts for input or opens an app. Every value comes from arguments, so a person and an agent run the tools the same way. Every path a command prints is absolute.

## How the pieces fit

| Object | What it is | Where it lives |
|---|---|---|
| Thread | A project, process or topic that other records belong to | `threads/<Kind>/<Name>.md` |
| Note | A typed document, such as a meeting record, correspondence or a report | `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md` |
| Log | A thread's one-line records for one day, written by `buffer flush` | `threads/<Kind>/<Name>/logs/<YYYY-MM-DD>.md` |
| Time entry | One session of work on a thread, billable or not | `threads/<Kind>/<Name>/hours.md` |
| Payment | Money received against a thread | `threads/<Kind>/<Name>/payments.md` |
| Person | A contact you track | `people/<Name>.md` |
| Action / task | An `ACTION:` line in a note or log. Ingest rewrites it in place as a `TASK:` anchor. | inside notes and logs |
| Buffer | The staging queue for quick captures | `buffer.md` |
| Config | Vault-wide settings | `.adulting/config.yaml` |

`<Kind>` is `Projects`, `Processes` or `Topics`. Everything that belongs to a thread lives in the thread's folder, beside its thread file.

Relationships:

- A note names one or more threads in its `threads:` frontmatter. It is filed under the first thread it names.
- A note's `people:` list and a task's assignee point at person files. A person is never a thread.
- Time entries and payments each belong to exactly one thread.
- Tasks live in the note or log that contains them. There is no separate task store.
- `notes new`, `hours log` and `payments log` each add a `REF:` to the buffer. The next `buffer flush` files that pointer in the thread's log for the day the event happened.
- Stats are declared in a thread file's frontmatter. Their values become `STAT:` lines in that thread's logs.

## Command reference

### tasks

Turns `ACTION:` lines into tracked `TASK:` anchors and edits those anchors in place.

**When to use it**

- You wrote `ACTION:` lines in a note and want them tracked as tasks.
- You want to see what is due, overdue or next.
- You need to complete a task or change its date, priority, assignee or dependencies.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| *(none)* | Same as `ingest` | `tasks` |
| `ingest` | Rewrites every `ACTION:` line in all notes and logs as a `TASK:` anchor with a new 8-character uuid | `tasks ingest --dry-run` |
| `add` | Adds a structured ACTION to the buffer. Same as `buffer add-action`. | `tasks add Projects/SGB "(Riaz Arbi) Send quarterly report" --due 2026-05-29 --priority H` |
| `done` | Changes `TASK` to `DONE` in the source file and stamps `end:` with today's date | `tasks done <uuid>` |
| `set-description` | Rewrites the task body | `tasks set-description <uuid> "Send revised quarterly report"` |
| `set-assignee` | Rewrites the `(Assignee)` prefix | `tasks set-assignee <uuid> "Riaz Arbi"` |
| `set-due` | Sets the due date | `tasks set-due <uuid> 2026-05-29` |
| `set-scheduled` | Sets the scheduled date | `tasks set-scheduled <uuid> 2026-05-28` |
| `set-priority` | Sets priority H, M or L, written as `[#X]` in the visible text | `tasks set-priority <uuid> H` |
| `add-depends` | Makes the task wait on another task | `tasks add-depends <uuid> <dep-uuid>` |
| `rm-depends` | Removes one dependency | `tasks rm-depends <uuid> <dep-uuid>` |
| `list` | Lists pending tasks, grouped by thread (A–Z), then by priority, due date and entry date | `tasks list --overdue` |
| `next` | Shows the top 5 pending tasks by priority, due date and entry date | `tasks next` |
| `show` | Shows one task in detail | `tasks show <uuid>` |

`<uuid>` comes from `tasks list`. Any unique prefix works.

**Options**

Global: `--dry-run` and `--quiet` apply to bare `tasks` and to `tasks ingest`.

| Option | Effect |
|---|---|
| `--dry-run` | Shows what would be ingested and writes nothing |
| `--quiet` | Suppresses per-action output |
| `--due <YYYY-MM-DD>` (`add`) | Sets the due date |
| `--scheduled <YYYY-MM-DD>` (`add`) | Sets the scheduled date |
| `--priority <H, M or L>` (`add`) | Sets the priority |
| `--depends <uuid>` (`add`) | Adds a dependency on another task. Repeatable. |
| `--priority <H, M or L>` (`list`) | Shows only tasks with this priority |
| `--thread <Kind/Name>` (`list`) | Shows only tasks whose source note carries this thread |
| `--assignee <person>` (`list`) | Shows only tasks assigned to this person |
| `--overdue` (`list`) | Shows only tasks whose due date is before today |
| `--json` (`list`) | Prints JSON |

**Notes**

- Bare `tasks`, `ingest`, `done` and every `set-*`, `add-depends` and `rm-depends` command rewrite note and log files in place.
- `tasks add` only writes to the buffer. The task appears after `buffer flush`.
- Ingest skips files that are not valid UTF-8 and does not count them as failures. `lint` reports them.
- Exit `1` means one of these: no task matches the uuid prefix, an empty prefix, a date that is not `YYYY-MM-DD`, an empty description, a person with no file in `people/`, or a task set to depend on itself.

### notes

Creates, lists, prints, copies, deletes and renders notes. Each note is identified by its stem.

A stem is the filename without `.md`, for example `2026-09-10-14-30-00`. Stems are unique across the vault.

**When to use it**

- You are starting a meeting record, a piece of correspondence or a report.
- You need to find a note's stem or print a note.
- You need minutes, an agenda or a PDF of a note.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Creates a note and prints its path | `notes new --type Meeting --topic "Kick-off" --thread Projects/SGB --person "Riaz Arbi"` |
| `list` | Lists notes oldest first, showing stem, date, type, threads and topic | `notes list sgb` |
| `cat` | Prints a note | `notes cat 2026-09-10-14-30-00` |
| `last` | Prints the path of the newest note | `notes last` |
| `copy` | Copies a note to a new timestamp and adds ` COPY` to its topic | `notes copy 2026-09-10-14-30-00` |
| `delete` | Permanently deletes a note | `notes delete 2026-09-10-14-30-00 -y` |
| `pdf` | Renders the note to Markdown and PDF, with callouts and an action table | `notes pdf 2026-09-10-14-30-00` |
| `minutes` | Renders meeting minutes: agreements, resolutions and action items | `notes minutes 2026-09-10-14-30-00` |
| `agenda` | Renders an agenda: the note with its outcome sections emptied | `notes agenda 2026-09-10-14-30-00` |

**Options**

| Option | Effect |
|---|---|
| `--type <type>` (`new`, required) | One of `Meeting`, `Correspondence`, `Workshop`, `Report`, `Log`, `Research` or `Recipe` |
| `--topic <text>` (`new`, required) | What the note is about |
| `--thread <thread>` (`new`, required) | A thread name, `Kind/Name` or wikilink. Repeatable. The first thread decides where the note is filed. |
| `--person <name>` (`new`) | An attendee. Meeting and Correspondence only. Repeatable. Linked when `people/<name>.md` exists. |
| `--counterparty <text>` (`new`) | The other party. Meeting only. |
| `--location <text>` (`new`) | Where the meeting was held. Meeting only. |
| `[filter]` (`list`) | Shows only notes with this text in any column. The match ignores case. |
| `--json` (`list`) | Prints JSON |
| `--out <dir>` (`pdf`, `minutes`, `agenda`) | Writes the output files here instead of `~/Downloads` |

**Notes**

- `new` writes the note's frontmatter. To add the body, edit the file at the path it prints.
- Every subcommand except `new` first ingests `ACTION:` lines into tasks. This means `list`, `cat` and the renders can rewrite source files. If an ACTION line cannot be ingested, the command still runs.
- `delete` needs `-y` (`--yes`). It cannot be undone.
- Renders write `<stem>.md` and `<stem>.md.pdf`.
- Exit `1` means one of these: an empty topic, an option used with the wrong note type, a malformed stem, no notes in the vault, or a failed PDF render.

### search

Finds notes and logs, and summarises activity on threads.

**When to use it**

- You need to find the notes or logs on a thread, in a date range, or containing some text.
- You want to see which threads were active in a period.
- You want a full picture or chronology of one thread.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `notes` | Finds notes by thread, type, date or text | `search notes --thread Projects/SGB --type Meeting` |
| `logs` | Finds daily logs by thread, date or text | `search logs --text invoice --since 2026-09-01` |
| `activity` | Ranks threads by what happened in a period | `search activity --since 2026-09-01 --until 2026-09-30` |
| `overview` | Shows the whole picture of one thread | `search overview Projects/SGB` |
| `stream` | Merges every dated record into one chronology | `search stream --today` |

**Options**

| Option | Effect |
|---|---|
| `--thread <thread>` | Limits results to one thread (`notes`, `logs`, `activity`, `stream`) |
| `--since <YYYY-MM-DD>` / `--until <YYYY-MM-DD>` | Includes only records on or after / on or before this date (all subcommands) |
| `--type <type>` (`notes`) | Filters by note type. Ignores case. |
| `--text <text>` | Matches literal text, ignoring case. `notes` searches topic and body. `logs` searches entry lines. `stream` searches thread and summary. |
| `--limit <n>` | Sets the maximum number of results. Defaults: `notes` and `logs` 20, `overview` 5, `stream` 100. `0` returns all. |
| `--kind <list>` (`stream`) | A comma-separated subset of `note`, `log`, `task`, `done`, `hours`, `payment`, `thread`, `person`, `pending`. The default is all. |
| `--today` (`stream`) | Shows today only |
| `--reverse` (`stream`) | Lists oldest first. The default is newest first. |
| `--json` | Prints JSON (all subcommands) |

**Notes**

- Results are absolute paths plus metadata, never file bodies. Open a file with `notes cat` or any reader.
- Dates are event dates: a note's frontmatter `timestamp`, not its filename. The filename is used only when the timestamp is missing or malformed.
- Hours descriptions are not searched.
- Exit `1` means `--kind` was given an unknown value.

### threads

Creates, lists and shows thread files.

**When to use it**

- You are starting a new project, process or topic.
- You need a thread's exact `Kind/Name` for another command.
- You want to check a thread's frontmatter, such as its status or billing defaults.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists open threads. An optional query ranks results by fuzzy match. | `threads list sgb --all` |
| `show` | Shows one thread file | `threads show Projects/SGB` |
| `new` | Creates a thread file | `threads new --name SGB --kind project --category professional --currency ZAR --rate 1500` |

**Options**

| Option | Effect |
|---|---|
| `--all` (`list`) | Includes paused and closed threads |
| `--json` (`list`, `show`) | Prints JSON |
| `--name <name>` (`new`, required) | The thread name. It becomes the filename. |
| `--kind <kind>` (`new`, required) | `project`, `process` or `topic`. Files the thread under `Projects`, `Processes` or `Topics`. |
| `--category <category>` (`new`, required) | `professional`, `personal` or `voluntary` |
| `--currency <ISO>` (`new`) | Sets the 3-letter default currency for `hours`. This makes the thread billable. |
| `--rate <n>` (`new`) | Sets the default hourly rate for `hours`. Needs `--currency`. |

**Notes**

- There is no close or delete command. To close a thread, set `status: closed` and `ended:` in its frontmatter. To remove a thread, delete its file and its folder by hand.
- Exit `1` means one of these: an empty name, a name containing `/` or starting with `.`, a thread that already exists, or `--rate` without `--currency`.

### people

Creates, lists, shows and deletes person files.

**When to use it**

- You want to link a new contact from notes or assign tasks to them.
- You need the exact name of a person for `--person` or `set-assignee`.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists open people. An optional query ranks results by fuzzy match. | `people list riaz` |
| `show` | Shows one person file | `people show "Riaz Arbi"` |
| `new` | Creates a person file | `people new --name "Riaz Arbi" --category professional` |
| `delete` | Permanently deletes a person file | `people delete "Riaz Arbi" -y` |

**Options**

| Option | Effect |
|---|---|
| `--all` (`list`) | Includes closed people |
| `--json` (`list`, `show`) | Prints JSON |
| `--name <full name>` (`new`, required) | The person's full name. It becomes the filename. |
| `--category <category>` (`new`, required) | `professional`, `personal` or `voluntary` |
| `-y`, `--yes` (`delete`) | Confirms the delete. Required. |

**Notes**

- Exit `1` means one of these: an empty or invalid name, a person who already exists, a person not found, or `delete` without `-y`.

### hours

Records time spent on threads, billable or not, and totals it.

**When to use it**

- You finished a session of work and want to record it.
- You need totals for a thread or a period, for example to invoice.
- You need to correct or remove an entry.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Appends an entry | `hours log Projects/SGB -m 90 DORA metric validation` |
| `list` | Lists entries | `hours list Projects/SGB --since 2026-09-01` |
| `report` | Totals by thread and currency. Unbilled time gets its own row. | `hours report --since 2026-09-01 --until 2026-09-30` |
| `show` | Shows one entry | `hours show <id>` |
| `edit` | Changes fields of an entry | `hours edit <id> -m 120` |
| `rm` | Permanently deletes an entry | `hours rm <id> -y` |

`<id>` is the entry's 8-character id, from `hours list`.

**Options**

| Option | Effect |
|---|---|
| `-m`, `--minutes <n>` (`log`, `edit`) | Sets the duration. The default for `log` is 60. In `edit`, the start time stays the same. |
| `-r`, `--rate <n>` (`log`, `edit`) | Sets the hourly rate. `0` means unbillable. Needs a currency. |
| `-c`, `--currency <ISO>` (`log`, `edit`) | Sets the currency. `log` defaults to the thread's currency. With neither, the entry is recorded as unbilled. |
| `-d`, `--date <YYYY-MM-DD>` (`log`, `edit`) | Sets the day. The default for `log` is today. In `edit`, the duration is kept. |
| `-t`, `--time <HH:MM>` (`log`, `edit`) | Sets the start time. The default for `log` is now. In `edit`, the duration is kept. |
| `--description <text>` (`edit`) | Sets a new description |
| `[thread]` (`list`) / `--thread <thread>` (`report`) | Limits output to one thread |
| `--since` / `--until <YYYY-MM-DD>` (`list`, `report`) | Limits output to a date range |
| `--json` (`list`, `report`, `show`) | Prints JSON |
| `-y`, `--yes` (`rm`) | Confirms the delete. Required. |

**Notes**

- The description becomes an invoice line item. Keep it a short label, and put narrative in a log line instead (`buffer add-text`).
- Rate and currency are stored on each entry when it is written. Changing a thread's defaults later never re-prices past work.
- `log` also adds a `REF:` to the buffer, filed under the day the work happened.
- Exit `1` means one of these: an empty description, minutes that are not positive, or a rate with no currency.

### payments

Records money received against threads and compares it with what was billed.

**When to use it**

- A client paid you.
- You want a billed-versus-received statement, or a PDF statement for a client.
- You need to correct or remove a payment.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Records a payment received | `payments log Projects/SGB 15000.00 -a "Business account" -n September invoice` |
| `list` | Lists payments | `payments list Projects/SGB` |
| `statement` | Shows billed versus received, by thread and currency | `payments statement --thread Projects/SGB --as-of 2026-09-30` |
| `show` | Shows one payment | `payments show <id>` |
| `edit` | Changes fields of a payment | `payments edit <id> --amount 14500.00` |
| `rm` | Permanently deletes a payment | `payments rm <id> -y` |

`<id>` is the payment's 8-character id, from `payments list`.

**Options**

| Option | Effect |
|---|---|
| `<amount>` (`log`) / `--amount <n>` (`edit`) | Sets the amount received. Must be positive. |
| `-c`, `--currency <ISO>` (`log`, `edit`) | Sets the currency. `log` defaults to the thread's currency. |
| `-d`, `--date <YYYY-MM-DD>` (`log`, `edit`) | Sets the date received. The default for `log` is today. |
| `-t`, `--time <HH:MM>` (`log`, `edit`) | Sets the time received. The default for `log` is now. |
| `-a`, `--account <text>` (`log`, `edit`) | Records which account the money landed in |
| `-n`, `--note <text>` (`log`, `edit`) | Adds a free-text note |
| `[thread]` (`list`) / `--thread <thread>` (`statement`) | Limits output to one thread |
| `--since` / `--until <YYYY-MM-DD>` (`list`, `statement`) | Limits output to a date range |
| `--as-of <YYYY-MM-DD>` (`statement`) | Sets the statement date, which drives aging. The default is today. |
| `--pdf <path>` (`statement`) | Renders a PDF statement to this path. Requires `--thread`. |
| `--json` (`list`, `statement`, `show`) | Prints JSON |
| `-y`, `--yes` (`rm`) | Confirms the delete. Required. |

**Notes**

- `amount` is optional in the usage line, but `log` exits `1` without it.
- A PDF statement needs `client_name` in the thread file's frontmatter.
- `log` also adds a `REF:` to the buffer, filed under the day the money was received.
- Exit `1` means one of these: a missing, invalid or non-positive amount; `--pdf` without `--thread`; or nothing to state for the thread on that date.

### stats

Logs numbers against declared stats and shows how they change over time.

**When to use it**

- You want to track a number such as push-ups, steps or money spent.
- You want to record that an event happened. Declare an `int` stat and log `1` each time.
- You want a daily, weekly or monthly series.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Declares a stat in a thread file's frontmatter | `stats new pushups --thread Topics/Health --type int --agg sum` |
| `list` | Lists declared stats | `stats list` |
| `log` | Adds a value to the buffer | `stats log pushups 25` |
| `series` | Shows the value per period, from logs and the unflushed buffer | `stats series pushups --by week` |

**Options**

| Option | Effect |
|---|---|
| `--thread <thread>` (`new`, required) | The thread to declare the stat on |
| `--type <type>` (`new`, required) | `int` for whole numbers, counts and events. `decimal` for other numbers. |
| `--agg <agg>` (`new`, required) | How a period's values combine: `sum` adds them, `last` takes the latest, `max` takes the largest |
| `-d`, `--date <YYYY-MM-DD>` (`log`) | Sets the date. The default is today. |
| `-t`, `--time <HH:MM>` (`log`) | Sets the time. The default is now. |
| `--by <period>` (`series`) | `day` (default), `week` or `month`. Weeks start on Monday. |
| `--since` / `--until <YYYY-MM-DD>` (`series`) | Limits the series to a date range |
| `--json` (`list`, `series`) | Prints JSON |

**Notes**

- Stat names use lowercase letters, digits and `-`, and are unique across the vault. Put a unit in the name if it helps, such as `run-km`.
- There is no rename or delete. Edit the thread's frontmatter instead. Values already logged are not rewritten.
- In `series`, a period with no values shows `-` (`null` in JSON), not `0`.
- Exit `1` means nothing was written. Causes: an undeclared or duplicate name, a value of the wrong type, a bad date or time, a thread that does not resolve, a malformed logged value, or `--since` later than `--until`. `int` takes whole numbers. `decimal` takes plain numbers such as `12.50`, never `1e3`.
- Exit `2` is a usage error, such as a missing argument or an unknown `--type` or `--agg`.

### buffer

Stages quick captures in `buffer.md` and files them into thread logs.

**When to use it**

- You want to note something about a thread without writing a note.
- You want to capture something now and decide its thread later.
- You are ready to move staged captures into the daily logs.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `add` | Appends a raw `UNKNOWN` capture with no thread | `buffer add "call bank about card"` |
| `add-text` | Appends a `TEXT:` observation | `buffer add-text Projects/SGB "Client approved the scope"` |
| `add-ref` | Appends a `REF:` pointer to another file | `buffer add-ref Projects/SGB 2026-09-10-14-30-00 "kick-off notes"` |
| `add-action` | Appends an `ACTION:`. Same as `tasks add`. | `buffer add-action Projects/SGB "(Riaz Arbi) Draft contract" --due 2026-10-15` |
| `list` | Shows the buffer with line numbers | `buffer list sgb` |
| `rm` | Removes one line by its number | `buffer rm 3` |
| `tend` | Regroups entries by thread and date, then validates them. Safe to repeat. | `buffer tend` |
| `flush` | Tends, writes each thread's logs, clears the buffer and ingests the flushed ACTIONs as tasks | `buffer flush` |

**Options**

Global: `--quiet` suppresses info output. Put it before the subcommand, for example `buffer --quiet flush`.

| Option | Effect |
|---|---|
| `--date <YYYY-MM-DD>` (`add`, `add-text`, `add-ref`, `add-action`) | Files the entry under the day the thing happened instead of today |
| `--due`, `--scheduled <YYYY-MM-DD>` (`add-action`) | Sets the due or scheduled date |
| `--priority <H, M or L>` (`add-action`) | Sets the priority |
| `--depends <uuid>` (`add-action`) | Adds a dependency on another task. Repeatable. |
| `[filter]` (`list`) | Shows only lines containing this text, ignoring case |
| `--json` (`list`) | Prints JSON |

**Notes**

- `UNKNOWN` entries block `flush`. Remove each one with `rm` and add it again with the matching `add-*` command.
- A `REF:` target is one of: `<Kind>/<Name>`, `<Kind>/<Name>/hours`, `<Kind>/<Name>/payments`, `<Kind>/<Name>/logs/<date>`, a note stem, or `people/<Name>`.
- Do not edit `buffer.md` by hand. Use these commands.
- `flush` ingests ACTIONs itself, so you do not need to run `tasks` afterwards. It skips an ACTION that is already an open task and reports `already a task`. It skips a repeat within the buffer and reports `already buffered`.
- Take the line number for `rm` from a fresh `buffer list`.
- Exit `1` means a bad line number (not an integer, empty, or out of range) or a validation failure.

### lint

Validates vault files against the schemas in [Data formats](#data-formats).

**When to use it**

- Before committing the vault.
- After you edit frontmatter by hand.
- When another command skipped a file and you want to know why.

**Usage**

```sh
lint [--schemas <dir>] [--quiet] [<path> ...]
```

| Argument | Effect |
|---|---|
| `<path> ...` | Validates only these files. With no paths, it checks the whole vault. |

**Options**

| Option | Effect |
|---|---|
| `--schemas <dir>` | Uses a different schemas directory |
| `--quiet` | Prints nothing. Only the exit code reports the result. |

**Notes**

- Each error prints as `<path>:<line>: <message>`, with an absolute path.
- A file that is not valid UTF-8 is reported as `file is not valid UTF-8`.
- Exit `0` means clean. Exit `1` means violations were found. Exit `2` means no schemas were loaded.

### commit

Reviews uncommitted vault changes, then stages and commits them with git.

**When to use it**

- At the end of a working session.
- After bulk changes, such as a flush or task updates, that you want recorded.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `review` | Shows everything that changed since the last commit. Read-only. | `commit review` |
| `save` | Stages every change in the vault and commits it | `commit save --message "Log SGB kick-off and tasks"` |

**Options**

| Option | Effect |
|---|---|
| `--max-file-lines <n>` (`review`) | Sets the maximum diff lines shown per file. The default is 150. |
| `--max-lines <n>` (`review`) | Sets the maximum output lines overall. The default is 3000. |
| `--message <text>` (`save`, required) | The commit subject. Must be one line. |
| `--body <text>` (`save`) | The commit body. Can span several lines. |
| `--dry-run` (`save`) | Reports what would be staged and committed, and changes nothing |

**Notes**

- `save` only ever adds a commit. It never amends, rebases, resets, checks out or pushes.
- `$ADULTING_HOME` must be the root of its git repository.
- Exit `1` means one of these: an empty or multi-line `--message`, a vault that is not a git repository or not its root, or a failed git command.

## Everyday procedures

### 1. Set up a new billable project

1. Create the thread with billing defaults:
   `threads new --name SGB --kind project --category professional --currency ZAR --rate 1500`
2. Create the client contact:
   `people new --name "<Client Contact>" --category professional`
3. To make PDF statements possible, add `client_name` to the thread file's frontmatter, then check the file:
   `lint ~/vault/threads/Projects/SGB.md`
4. Confirm the result:
   `threads show Projects/SGB`

### 2. Capture a meeting and turn its actions into tracked tasks

1. Create the note. It prints the note's path:
   `notes new --type Meeting --topic "Kick-off" --thread Projects/SGB --person "<Client Contact>" --counterparty "<Client>"`
2. Edit that file. Write the outcomes as `AGREED:`, `RESOLVED:` and `ACTION: (<Person>) <what>` lines.
3. Preview what will be ingested:
   `tasks --dry-run`
4. Turn the ACTION lines into tasks:
   `tasks`
5. Check the new tasks:
   `tasks list --thread Projects/SGB`
6. Render the minutes to `~/Downloads`:
   `notes minutes <stem>`
7. File the note's pointer in today's log:
   `buffer flush`

### 3. Quick-capture through the day, then file it

1. Capture without choosing a thread:
   `buffer add "<anything>"`
2. Capture an observation on a known thread:
   `buffer add-text Projects/SGB "<observation>"`
3. Validate the buffer. `UNKNOWN` lines are reported:
   `buffer tend`
4. Find the line numbers:
   `buffer list`
5. Remove a raw capture:
   `buffer rm <line-number>`
6. Add it again with the right shape:
   `buffer add-action Projects/SGB "<task>"` or `buffer add-text Projects/SGB "<text>"`
7. File everything into the thread logs and ingest the actions:
   `buffer flush`

### 4. Work the task list

1. See what to do next:
   `tasks next`
2. See what is overdue:
   `tasks list --overdue`
3. Inspect one task:
   `tasks show <uuid>`
4. Reschedule a task:
   `tasks set-due <uuid> <YYYY-MM-DD>`
5. Reprioritise a task:
   `tasks set-priority <uuid> H`
6. Record that one task waits on another:
   `tasks add-depends <uuid> <dep-uuid>`
7. Complete a task:
   `tasks done <uuid>`

### 5. Log a session of work

1. Record the time under a short label:
   `hours log Projects/SGB -m 90 DORA metric validation`
2. Record what actually happened as a log line:
   `buffer add-text Projects/SGB "<what happened>"`
3. Check the entry and its id:
   `hours list Projects/SGB --since <YYYY-MM-DD>`
4. Correct it if needed:
   `hours edit <id> -m 120`
5. File the log lines and the hours pointer:
   `buffer flush`

### 6. Bill a client for a month's work

1. Get the totals for the month:
   `hours report --thread Projects/SGB --since 2026-09-01 --until 2026-09-30`
2. List the line items:
   `hours list Projects/SGB --since 2026-09-01 --until 2026-09-30`
3. Check billed versus received:
   `payments statement --thread Projects/SGB --as-of 2026-09-30`
4. Render the statement as a PDF:
   `payments statement --thread Projects/SGB --as-of 2026-09-30 --pdf ~/Downloads/SGB-statement.pdf`

### 7. Record a payment

1. Record the receipt:
   `payments log Projects/SGB 15000.00 -d <YYYY-MM-DD> -a "<account>" -n <note>`
2. Confirm it:
   `payments list Projects/SGB`
3. Check what is still outstanding:
   `payments statement --thread Projects/SGB`
4. File the payment pointer in the log:
   `buffer flush`

### 8. Check the vault and commit it

1. Validate the staged captures:
   `buffer tend`
2. File them:
   `buffer flush`
3. Validate the whole vault:
   `lint`
4. Read every change since the last commit:
   `commit review`
5. Preview the commit:
   `commit save --message "<summary>" --dry-run`
6. Commit:
   `commit save --message "<summary>" --body "<detail>"`

## Data formats

`lint` enforces every format below. Paths are relative to `$ADULTING_HOME`.

### `hours_file`

A thread's time entries, kept as JSON in a single `simple-time-tracker` fenced block. The `hours` command writes it.

Location: `threads/<Kind>/<Name>/hours.md`

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Frontmatter. A wikilink to the thread whose folder holds the file. |
| `currency` | no | Frontmatter. The 3-letter currency. Omitted for unbilled threads. |
| `entries[].name` | yes | The description. It becomes an invoice line item. |
| `entries[].startTime` | yes | Start, as an ISO 8601 UTC time with milliseconds |
| `entries[].endTime` | yes | End, in the same form. Not before `startTime`. Duration is end minus start. |
| `entries[].id` | yes | 8 hex characters. Unique across all hours and payments. |
| `entries[].rate` | yes | Hourly charge. `0` means unbillable. |
| `entries[].currency` | no | ISO 4217 code. Absent or null means unbilled. |

### `log`

A thread's one-line records for one day, written by `buffer flush`.

Location: `threads/<Kind>/<Name>/logs/<YYYY-MM-DD>.md`

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | A wikilink to the thread whose folder holds the log |
| `date` | yes | The day, `YYYY-MM-DD` |
| `type` | yes | Always `Log` |

Body lines are `TEXT:`, `REF:`, `ACTION:`, `TASK:`, `DONE:` and `STAT:`.

### `note_correspondence`

A note recording an exchange of email, messages or letters.

Location: `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md`, in the folder of the first thread it names.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about |
| `type` | yes | `Correspondence` |
| `threads` | yes | A list of thread wikilinks. Each must resolve. |
| `timestamp` | yes | When it happened, `YYYY-MM-DD-HH-MM-SS` |
| `people` | no | `[[people/X]]` links, which must resolve, or plain names |

### `note_meeting`

A note recording a meeting.

Location: `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md`, in the folder of the first thread it names.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the meeting was about |
| `type` | yes | `Meeting` |
| `threads` | yes | A list of thread wikilinks. Each must resolve. |
| `timestamp` | yes | When it happened, `YYYY-MM-DD-HH-MM-SS` |
| `counterparty` | no | The other party |
| `location` | no | Where it was held |
| `people` | no | `[[people/X]]` links, which must resolve, or plain names |

Body lines can include `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:` and `!:` (a callout). `notes minutes` uses `AGREED:` and `RESOLVED:`. `notes pdf` shows `!:` callouts.

### `note_simple`

A note of type Workshop, Report, Log, Research or Recipe.

Location: `threads/<Kind>/<Name>/notes/<YYYY-MM-DD-HH-MM-SS>.md`, in the folder of the first thread it names.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about |
| `type` | yes | `Workshop`, `Report`, `Log`, `Research` or `Recipe` |
| `threads` | yes | A list of thread wikilinks. Each must resolve. |
| `timestamp` | yes | When it happened, `YYYY-MM-DD-HH-MM-SS` |
| `people` | no | `[[people/X]]` links or plain names |

### `payments_file`

A thread's payments received, kept as JSON in a single `adulting-payments` fenced block. The `payments` command writes it.

Location: `threads/<Kind>/<Name>/payments.md`

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Frontmatter. A wikilink to the thread whose folder holds the file. |
| `currency` | yes | Frontmatter. The 3-letter currency. |
| `payments[].id` | yes | 8 hex characters. Unique across all hours and payments. |
| `payments[].received` | yes | When the money landed, as an ISO 8601 UTC time with milliseconds |
| `payments[].amount` | yes | The amount. Must be greater than 0. |
| `payments[].currency` | yes | ISO 4217 code |
| `payments[].account` | no | The account it landed in |
| `payments[].note` | no | Free text |

### `person`

A contact you track.

Location: `people/<Name>.md`

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed` |
| `category` | yes | `professional`, `personal` or `voluntary` |
| `started` | yes | Start date, `YYYY-MM-DD` |
| `ended` | no | End date. Required when `status` is `closed`. |
| `cadences` | no | A list of `key`, `frequency` and `description` entries |

### `stat_line`

One value of a declared stat, as a line in a thread's log: `STAT: <name> <value> <!--<YYYY-MM-DDTHH:MM:SS>-->`.

Location: inside `threads/<Kind>/<Name>/logs/<YYYY-MM-DD>.md`

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | A stat declared on this log's own thread |
| `value` | yes | A number. Whole numbers only for `int` stats. |
| `ts` | yes | Local timestamp. Its date must match the log's date. |

### `task_anchor`

One `TASK:` or `DONE:` line in a note or log. This line is the task's state. Change it only with `tasks` subcommands.

Location: inside notes and logs.

| Field | Required | Meaning |
|---|---|---|
| `kind` | yes | `TASK` (open) or `DONE` (complete) |
| `priority` | no | `H`, `M` or `L`, shown as `[#X]` |
| `assignee` | no | A person who must have a file in `people/` |
| `body` | yes | The task description |
| `uuid` | yes | 8 hex characters. Unique across the vault. |
| `entry` | yes | Ingest date |
| `end` | no | Completion date. Required on `DONE`. Not before `entry`. |
| `due` | no | Due date |
| `scheduled` | no | Scheduled date |
| `depends` | no | Comma-separated uuids of other tasks. No cycles allowed. |

Example: `TASK: [#H] (Riaz Arbi) Send quarterly report <!--abcd1234 entry:2026-05-27 due:2026-05-29-->`

### `thread`

A project, process or topic file.

Location: `threads/<Kind>/<Name>.md`

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed` |
| `kind` | yes | `project`, `process` or `topic` |
| `category` | yes | `professional`, `personal` or `voluntary` |
| `started` | yes | Start date, `YYYY-MM-DD` |
| `ended` | no | End date. Required when `status` is `closed`. |
| `cadences` | no | Recurring obligations: a list of `key`, `frequency` (in days) and `description` entries |
| `stats` | no | Declared stats: a list of `name`, `type` and `agg` entries. Written by `stats new`. |
| `currency` | no | Default 3-letter currency for `hours`. Makes the thread billable. |
| `rate` | no | Default hourly rate for `hours` |
| `client_name` | no | The party billed on a PDF statement. Required to render one. |
| `client_address` | no | Address lines separated by `\|`, for example `Unit 301\|2 Park Road\|Cape Town` |
| `client_vat` | no | The client's VAT number |
| `client_email` | no | The client's email address |

### `thread_entry`

A dated top-level bullet in a thread file's body: `- <YYYY-MM-DD> — <text>`. Indented sub-bullets under it are not checked.

Location: inside `threads/<Kind>/<Name>.md`

| Field | Required | Meaning |
|---|---|---|
| `date` | yes | `YYYY-MM-DD` |
| `text` | yes | The entry. Must not be empty. |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `buffer flush` stops and reports violations | The buffer holds `UNKNOWN` captures | `buffer list`, then `buffer rm <line-number>`, then add it again with `buffer add-text`, `add-ref` or `add-action` |
| `hours log` exits `1`: `--rate needs a currency` | A rate was given and there is no currency to express it in | Add `-c <ISO>`, or create the thread with `--currency` |
| `threads new` exits `1`: `--rate needs a --currency` | `--rate` was given without `--currency` | Add `--currency <ISO>` |
| `payments statement` exits `1`: `--pdf needs --thread` | A statement covers one client | Add `--thread <thread>` |
| `notes pdf`, `minutes` or `agenda` exits `1`: `PDF render failed` | The render needs `pandoc` and `xelatex` | Install `pandoc` and a LaTeX engine |
| `tasks` exits `1`: `no task found with uuid prefix` | The prefix matches no task | Copy the uuid from `tasks list` |
| `tasks set-assignee` exits `1`: person does not resolve | There is no `people/<name>.md` | `people new --name "<name>" --category <category>` |
| `people delete` exits `1`: `refusing to delete ... without -y` | Deletes need confirmation | Add `-y` |
| `commit save` exits `1`: `not a git repository` or `is not the root of its git repository` | `$ADULTING_HOME` is not a git repository root | Make `$ADULTING_HOME` the root of a git repository |
| `commit save` exits `1`: `--message must be a single line` | The subject has line breaks | Put the detail in `--body` |
| `stats log` exits `1` and suggests names | The stat is not declared | `stats list`, or `stats new <name> --thread <thread> --type <type> --agg <agg>` |
| `lint` reports `file is not valid UTF-8` | Other commands skip this file without saying so | Fix the file's encoding or remove the file |

## Quick reference

| Command | Does |
|---|---|
| `tasks` | Ingests ACTION lines as TASK anchors |
| `tasks ingest` | Ingests ACTION lines as TASK anchors |
| `tasks add` | Adds an ACTION to the buffer |
| `tasks done` | Marks a task complete |
| `tasks set-description` | Rewrites a task's body |
| `tasks set-assignee` | Changes a task's assignee |
| `tasks set-due` | Sets a task's due date |
| `tasks set-scheduled` | Sets a task's scheduled date |
| `tasks set-priority` | Sets a task's priority |
| `tasks add-depends` | Adds a task dependency |
| `tasks rm-depends` | Removes a task dependency |
| `tasks list` | Lists pending tasks |
| `tasks next` | Shows the top 5 pending tasks |
| `tasks show` | Shows one task |
| `notes new` | Creates a note and prints its path |
| `notes list` | Lists notes |
| `notes cat` | Prints a note |
| `notes last` | Prints the path of the newest note |
| `notes copy` | Copies a note to a new timestamp |
| `notes delete` | Permanently deletes a note |
| `notes pdf` | Renders a note to Markdown and PDF |
| `notes minutes` | Renders meeting minutes |
| `notes agenda` | Renders a meeting agenda |
| `search notes` | Finds notes |
| `search logs` | Finds daily logs |
| `search activity` | Ranks threads by activity |
| `search overview` | Summarises one thread |
| `search stream` | Shows a merged chronology |
| `threads list` | Lists threads |
| `threads show` | Shows a thread file |
| `threads new` | Creates a thread |
| `people list` | Lists people |
| `people show` | Shows a person file |
| `people new` | Creates a person file |
| `people delete` | Permanently deletes a person file |
| `hours log` | Records a time entry |
| `hours list` | Lists time entries |
| `hours report` | Totals time by thread and currency |
| `hours show` | Shows one time entry |
| `hours edit` | Changes a time entry |
| `hours rm` | Permanently deletes a time entry |
| `payments log` | Records a payment received |
| `payments list` | Lists payments |
| `payments statement` | Shows billed versus received |
| `payments show` | Shows one payment |
| `payments edit` | Changes a payment |
| `payments rm` | Permanently deletes a payment |
| `stats new` | Declares a stat on a thread |
| `stats list` | Lists declared stats |
| `stats log` | Adds a stat value to the buffer |
| `stats series` | Shows a stat over time |
| `buffer add` | Captures raw text as UNKNOWN |
| `buffer add-text` | Captures an observation |
| `buffer add-ref` | Captures a pointer to a file |
| `buffer add-action` | Captures an action |
| `buffer list` | Shows the buffer with line numbers |
| `buffer rm` | Removes one buffer line |
| `buffer tend` | Regroups and validates the buffer |
| `buffer flush` | Files the buffer into logs and ingests actions |
| `lint` | Validates vault files |
| `commit review` | Shows uncommitted changes (read-only) |
| `commit save` | Stages and commits all vault changes |
