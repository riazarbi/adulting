# adulting — Operators Manual

## Before you start

Everything lives under one vault directory. The default is `~/vault/`. Set `ADULTING_HOME` to point the tools at a different directory; every path below is relative to it.

The vault holds plain text. Notes, threads, people, logs, hours and payments are all markdown on disk. You can read them, `grep` them, back them up and diff them in git without any of these tools.

External programs the tools need:

| Program | Needed by |
|---|---|
| `bash`, `python3`, `awk`, `sed`, `grep` | everything |
| `pandoc` and a LaTeX engine (`xelatex`) | `notes pdf`, `notes minutes`, `notes agenda` |
| macOS `open` or Linux `xdg-open` | launching Obsidian for note editing |

Tooling state lives in the hidden `.adulting/` directory, including `.adulting/config.yaml`.

## How the pieces fit

The objects:

| Object | What it is | Where it lives |
|---|---|---|
| Note | A persisted record: meeting, correspondence, report, research, log, workshop, recipe. | `notes/` |
| Thread | The organising lens for everything else: a project, process or topic. | `threads/Projects/`, `threads/Processes/`, `threads/Topics/` |
| Person | A contact you track. | `people/` |
| Time entry | One session of work on a thread, billable or not. | `hours/<Kind>/<Thread>.md` |
| Payment | Money received against a thread. | `payments/<Kind>/<Thread>.md` |
| Action / task | A line of work, stored as a `TASK:`/`DONE:` line in its source file. | inside `notes/` and `logs/` |
| Buffer entry | A quick capture waiting to be filed. | `buffer.md` |
| Log | One thread's activity for one day, written by `buffer flush`. | `logs/<Kind>/<Name>/<YYYY-MM-DD>.md` |

The relationships:

- A note names one or more threads in its `threads` frontmatter list, and may name people.
- A thread file is the link target every other object resolves against. Hours, payments and logs mirror the thread's `Kind/Name` path.
- A person is a link target only. A person can never be a note's thread. A task's assignee must resolve to `people/<name>.md`.
- A time entry carries the rate and currency resolved at write time, from the thread's `currency` and `rate`.
- `payments statement` compares billed time against money received, per thread.
- An `ACTION:` line in a note or log becomes a `TASK:` anchor with an 8-character uuid when `tasks` runs. The source file is the only store; there is no backend.
- A task may depend on other tasks by uuid.

## Command reference

### `tasks`

Turns `ACTION:` lines in notes and logs into anchored `TASK:` lines, and edits those anchors.

**When to use it**

- You have written `ACTION:` lines in a meeting note and want them tracked.
- You finished something and want the source line flipped to `DONE:`.
- You want to see what to work on next.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| *(none)* | Walk `notes/` and `logs/`, validate every `ACTION:` line, rewrite it in place as a `TASK:` anchor. | `tasks` |
| `add` | Buffer-append a structured ACTION. | `tasks add Projects/SGB "(Riaz Arbi) Draft the scope"` |
| `done` | Flip the source `TASK:` to `DONE:` and stamp `end:`. | `tasks done abcd1234` |
| `set-description` | Rewrite the task body. | `tasks set-description abcd1234 "Draft and circulate the scope"` |
| `set-assignee` | Rewrite the `(Assignee)` prefix. | `tasks set-assignee abcd1234 "Riaz Arbi"` |
| `set-due` | Set the due date. | `tasks set-due abcd1234 2026-10-01` |
| `set-scheduled` | Set the scheduled date. | `tasks set-scheduled abcd1234 2026-09-28` |
| `set-priority` | Set priority; writes `[#X]` in the visible portion. | `tasks set-priority abcd1234 H` |
| `add-depends` | Add a dependency. | `tasks add-depends abcd1234 ef567890` |
| `rm-depends` | Remove a dependency. | `tasks rm-depends abcd1234 ef567890` |
| `list` | List pending tasks. | `tasks list --overdue` |
| `next` | Top 5 pending tasks by priority, due, entry. | `tasks next` |
| `show` | Detail view of one anchor. | `tasks show abcd1234` |

**Options**

| Option | Effect |
|---|---|
| `--dry-run` | No-argument invocation only. Show what would be ingested; write nothing. |
| `--quiet` | No-argument invocation only. Suppress per-action output. |
| `add --due <YYYY-MM-DD>` | Due date. |
| `add --scheduled <YYYY-MM-DD>` | Scheduled date. |
| `add --priority {H,M,L}` | Priority. |
| `add --depends <uuid8>` | 8-character uuid prefix; repeatable. |
| `list --priority {H,M,L}` | Filter to one priority. |
| `list --thread <Kind/Name>` | Filter to tasks whose source note carries this thread. |
| `list --assignee <name>` | Filter to one assignee. |
| `list --overdue` | Only tasks due before today. |

**Notes**

- The bare `tasks` invocation rewrites source notes and logs in place. Use `--dry-run` first if you are unsure.
- Do not write `TASK:` lines by hand. `tasks` owns them.
- `tasks add` writes to the buffer, not to a note. It becomes a task only after `buffer flush` and a `tasks` run.
- Exit code `1` on: empty description, no task matching the uuid prefix, an ambiguous uuid prefix, an assignee that does not resolve to `people/<name>.md`, or a task depending on itself.

### `notes`

Creates, edits, queries and renders notes.

**When to use it**

- You are about to sit in a meeting and need a note to type into.
- You want a PDF of minutes to send round after a meeting.
- You want to reopen the note you just wrote.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Create a new note and open it. Default when no subcommand is given. | `notes new` |
| `copy` | Pick a note, copy its contents to a new timestamped note. | `notes copy` |
| `strip` | Pick a note, copy it and remove the body — a template. | `notes strip` |
| `edit` | Pick a note, open it in the default editor. | `notes edit` |
| `nano` | Pick a note, open it in nano. | `notes nano` |
| `last` | Open the most recently created note. | `notes last` |
| `delete` | Pick a note and permanently delete it. | `notes delete` |
| `cat` | Pick a note and print it to stdout. | `notes cat` |
| `pdf` | Pick a note, render to PDF and markdown with an ACTION/TASK summary. | `notes pdf` |
| `minutes` | Pick a note, render minutes: TOC plus AGREED/RESOLVED/ACTION summary. | `notes minutes` |
| `agenda` | Pick a note, render a meeting agenda. | `notes agenda` |

**Options**

| Option | Effect |
|---|---|
| `<filter>` (second positional) | Case-insensitive substring filter on the picker list. |

**Notes**

- Every subcommand except `last` opens an interactive picker and reads a selection from stdin. An agent must never call them. Only `notes last` is usable without a TTY.
- `notes delete` is permanent.
- Rendered output goes to `$EXPORT_DIR`, default `~/Downloads`.
- Body keywords you can type: `ACTION:`, `AGREED:`, `RESOLVED:`, `!:`. Do not type `TASK:` by hand.

### `search`

Finds notes and logs, and summarises thread activity.

**When to use it**

- You remember a phrase from a note but not which note.
- You want every log entry on a thread for last month.
- You are picking a thread back up and want the whole picture.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `notes` | Find notes by thread, type, date or text. | `search notes --thread Projects/SGB --type Meeting` |
| `logs` | Find daily logs by thread, date or text. | `search logs --since 2026-08-01 --until 2026-08-31` |
| `activity` | Rank threads by what happened in a window. | `search activity --since 2026-08-01` |
| `overview` | The whole picture of one thread. | `search overview Projects/SGB` |

**Options**

| Option | Effect |
|---|---|
| `--thread <thread>` | Thread name, `Kind/Name`, or wikilink. On `activity`, limits to one thread. |
| `--type <type>` | `notes` only. Note type, case-insensitive. |
| `--text <string>` | Case-insensitive literal. Over topic and body for notes; over entry lines for logs. |
| `--since <YYYY-MM-DD>` | On or after this date. |
| `--until <YYYY-MM-DD>` | On or before this date. |
| `--limit <n>` | `notes` and `logs`: max results, default 20, `0` for all. `overview`: recent items to list, default 5. |
| `--json` | JSON output. |

**Notes**

- Read-only. Nothing here changes the vault.
- Results are pointers — a path plus metadata. Open the file separately to read the body.
- Dates filter on the event date from a note's frontmatter `timestamp`, not the filename. The filename is used only when the frontmatter date is missing or malformed.
- Exit code `1` when a thread argument cannot be resolved.

### `threads`

Manages thread files.

**When to use it**

- You are starting a new client project and need something to log against.
- You want the rate and currency for a billable engagement recorded.
- You are looking for a thread whose exact name you forget.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | List thread files, open ones by default. | `threads list SGB` |
| `show` | Show a single thread file. | `threads show Projects/SGB` |
| `new` | Create a thread file. | `threads new --name SGB --kind project --category professional --currency ZAR --rate 2500` |
| `delete` | Permanently delete a thread file. | `threads delete Projects/SGB -y` |

**Options**

| Option | Effect |
|---|---|
| `list --all` | Include paused and closed threads. |
| `list --json`, `show --json` | JSON output. |
| `new --name <name>` | Thread name; skips the prompt. |
| `new --kind {project,process,topic}` | Skips the prompt. |
| `new --category {professional,personal,voluntary}` | Skips the prompt. |
| `new --currency <ISO>` | Default currency for `hours`. Three-letter ISO code. |
| `new --rate <n>` | Default hourly rate for `hours`. Needs `--currency`. |
| `delete -y` | Skip the confirmation. |

**Notes**

- `threads new` prompts interactively for any field you do not supply. Supply `--name`, `--kind` and `--category` to run it without a TTY.
- `threads delete` is permanent and prompts unless you pass `-y`.
- A thread with no `currency` is not billable. Its time is totalled as unbilled.

### `people`

Manages person files.

**When to use it**

- Someone new joins a project and you want to assign tasks to them.
- You want to check what you have recorded about a contact.
- You are checking the exact spelling of a name before assigning a task.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | List person files, open ones by default. | `people list Arbi` |
| `show` | Show a single person file. | `people show "Riaz Arbi"` |
| `new` | Create a person file. | `people new --name "Riaz Arbi" --category professional` |
| `delete` | Permanently delete a person file. | `people delete "Riaz Arbi" -y` |

**Options**

| Option | Effect |
|---|---|
| `list --all` | Include closed people. |
| `list --json`, `show --json` | JSON output. |
| `new --name <full name>` | Skips the prompt. |
| `new --category {professional,personal,voluntary}` | Skips the prompt. |
| `delete -y` | Skip the confirmation. |

**Notes**

- `people new` prompts for anything you do not supply. Pass `--name` and `--category` to run it without a TTY.
- A person is never a thread. Do not use a person as a note's thread value.

### `hours`

Records time worked against a thread, billable or not.

**When to use it**

- You just finished a two-hour session on a client project.
- The client asks how many hours you have put in this month.
- You typed the wrong duration yesterday.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Append an entry. Interactive if you give no thread. | `hours log Projects/SGB -m 120 "Drafted the integration spec"` |
| `list` | List entries. | `hours list Projects/SGB --since 2026-08-01` |
| `report` | Totals by thread and currency, unbilled time totalled separately. | `hours report --since 2026-08-01 --until 2026-08-31` |
| `show` | Show one entry. | `hours show a1b2c3d4` |
| `edit` | Change one field of an entry. | `hours edit a1b2c3d4 -m 90` |
| `rm` | Delete an entry. | `hours rm a1b2c3d4 -y` |

**Options**

| Option | Effect |
|---|---|
| `-m, --minutes <n>` | Duration. Default 60. |
| `-r, --rate <n>` | Hourly rate. `0` means unbillable. |
| `-c, --currency <ISO>` | ISO code. Defaults to the thread's. Without either, the entry is recorded as unbilled. |
| `-d, --date <YYYY-MM-DD>` | Default today. |
| `-t, --time <HH:MM>` | Default now. |
| `log --all` | Interactive mode: list paused and closed threads too. |
| `edit --description <text>` | Replace the entry description. |
| `list/report --since`, `--until` | Inclusive date bounds. |
| `report --thread <thread>` | Limit to one thread. |
| `--json` | JSON output on `list`, `report`, `show`. |
| `rm -y` | Skip the confirmation. |

**Notes**

- `hours log` with no thread argument is interactive. Always pass a thread when running without a TTY.
- `hours rm` deletes the entry; it prompts unless you pass `-y`.
- The description is the invoice line item. Write it for the client to read.
- Rate and currency are stored on each entry at write time. Changing a thread's defaults never re-prices logged work.
- Asking for a rate with no currency to express it in is refused.

### `payments`

Records money received against a thread and reports billed against received.

**When to use it**

- An invoice has been paid and you want the receipt recorded.
- You need a statement of account for a client.
- You want to know what is still outstanding.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Record a receipt. Interactive if you give no thread. | `payments log Projects/SGB 15000 -d 2026-09-01 -a "Business current"` |
| `list` | List payments. | `payments list Projects/SGB --since 2026-01-01` |
| `statement` | Billed against received, by thread and currency. | `payments statement --thread Projects/SGB` |
| `show` | Show one payment. | `payments show 0fa1b2c3` |
| `edit` | Change one field of a payment. | `payments edit 0fa1b2c3 --amount 16000` |
| `rm` | Delete a payment. | `payments rm 0fa1b2c3 -y` |

**Options**

| Option | Effect |
|---|---|
| `-c, --currency <ISO>` | ISO code. Defaults to the thread's. |
| `-d, --date <YYYY-MM-DD>` | Date received. Default today. |
| `-t, --time <HH:MM>` | Default now. |
| `-a, --account <name>` | Which account the money landed in. |
| `-n, --note <text>` | Free-text note. |
| `log --all` | Interactive mode: list paused and closed threads too. |
| `edit --amount <n>` | Replace the amount. |
| `list/statement --since`, `--until` | Date bounds. |
| `statement --thread <thread>` | Limit to one thread. |
| `statement --as-of <YYYY-MM-DD>` | Statement date; drives aging. Default today. |
| `statement --pdf <path>` | Render a PDF to this path. Requires `--thread`. |
| `--json` | JSON output on `list`, `statement`, `show`. |

**Notes**

- `payments log` with no thread argument is interactive. Pass a thread when running without a TTY.
- `payments rm` prompts unless you pass `-y`.
- Amounts must be positive. There is no negative payment.
- Unbilled hours are ignored by `payments statement`.
- Rendering a statement PDF needs `client_name` on the thread.

### `buffer`

The capture inbox: append items through the day, then file them into logs.

**When to use it**

- Something comes up mid-call and you have no time to open a note.
- You want to queue an action against a thread from the command line.
- End of day: you want the day's captures written into the logs.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `add` | Append an UNKNOWN entry — raw quick-capture. | `buffer add "chase the SGB invoice"` |
| `suggest` | Propose a structured `add-*` for raw text, then prompt. | `buffer suggest "chase the SGB invoice" -y` |
| `add-text` | Append a TEXT entry. | `buffer add-text Projects/SGB "Client prefers Thursday calls"` |
| `add-ref` | Append a REF entry. | `buffer add-ref Projects/SGB notes/2026-09-01-14-30-00 "Kickoff note"` |
| `add-action` | Append an ACTION entry. Same as `tasks add`. | `buffer add-action Projects/SGB "(Riaz Arbi) Send the invoice" --due 2026-09-30` |
| `list` | Show the buffer with line numbers. | `buffer list SGB` |
| `rm` | Remove a single line by line number. | `buffer rm 3` |
| `tend` | Regroup by thread and date, then validate. | `buffer tend` |
| `flush` | Tend, then write to `logs/` and clear the buffer. | `buffer flush` |

**Options**

| Option | Effect |
|---|---|
| `--quiet` | Suppress info output. Goes before the subcommand. |
| `suggest -y` | Auto-accept the suggestion without prompting. |
| `add-action --due <YYYY-MM-DD>` | Due date applied on flush and ingest. |
| `add-action --scheduled <YYYY-MM-DD>` | Scheduled date. |
| `add-action --priority {H,M,L}` | Priority. |
| `add-action --depends <uuid8>` | 8-character uuid prefix; repeatable. |

**Notes**

- `buffer suggest` prompts unless you pass `-y`. An agent must pass `-y`.
- UNKNOWN entries are deliberately invalid. `tend` reports them as violations, and they block `flush` until you remove them and re-add them with the matching `add-*` command.
- `buffer flush` empties `buffer.md`. Run `buffer tend` first to see what will be written.
- `tend` is idempotent.
- Do not edit `buffer.md` by hand. Use `buffer rm` and the `add-*` commands.
- Exit code `1` on: empty text, empty description, an empty description after the assignee, a `--depends` value that is not 8 hex characters, or a `--due`/`--scheduled` value that is not `YYYY-MM-DD`.

### `lint`

Validates vault files against the schemas.

**When to use it**

- Before committing, to check nothing is malformed.
- After hand-editing a thread or person file.
- To check one file you just changed.

**Usage**

`lint [<path> ...]`

| Argument | Meaning |
|---|---|
| `paths` | Files to validate. With none, walks the vault. |

**Options**

| Option | Effect |
|---|---|
| `--schemas <dir>` | Use a different schemas directory. |
| `--quiet` | Suppress per-violation output; exit code only. |

**Notes**

- Read-only. It reports; it never fixes.
- Violations print as `<path>:<line>: <message>`.
- Exit `0` when clean, `1` when there are violations, `2` on a usage failure.

### `commit`

Reviews uncommitted vault changes, then stages and commits them.

**When to use it**

- End of a work session, to record what changed.
- Before you trust the vault to a backup.
- To see everything that has changed since the last commit.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `review` | Show everything changed since the last commit. Read-only. | `commit review` |
| `save` | Stage every change in the vault and commit it. | `commit save --message "Log September SGB hours"` |

**Options**

| Option | Effect |
|---|---|
| `review --max-file-lines <n>` | Max diff lines shown per file. Default 150. |
| `review --max-lines <n>` | Max lines of output overall. Default 3000. |
| `save --message <text>` | Required. Commit subject; must be a single non-empty line. |
| `save --body <text>` | Commit body. May span multiple lines. |
| `save --dry-run` | Report what would be staged and committed; change nothing. |

**Notes**

- `save` only ever adds a commit. It never amends, rebases, resets, checks out or pushes.
- `save` stages every change in the vault. There is no partial staging.
- Run `review` first and write the message from what you see.
- Exit code `1` when: `--message` is empty or spans more than one line, `ADULTING_HOME` is not a directory, `ADULTING_HOME` is not the root of its git repository, or a git call fails.

## Everyday procedures

### 1. Set up a new billable project

1. `threads new --name SGB --kind project --category professional --currency ZAR --rate 2500` — create the thread with its billing defaults.
2. `people new --name "Jane Doe" --category professional` — create a person file for each counterparty you will assign work to.
3. `threads show Projects/SGB` — confirm the frontmatter reads as you expect.
4. `lint` — check the new files against the schemas.

### 2. Capture a meeting and turn its actions into tracked tasks

1. `notes new` — create the note and type into it during the meeting. Interactive; TTY only.
2. Write `ACTION:` lines in the body for each thing someone agreed to do.
3. `tasks --dry-run` — see which ACTION lines would be ingested and whether they validate.
4. `tasks` — rewrite each ACTION line in place as a `TASK:` anchor with a uuid.
5. `tasks list --thread Projects/SGB` — confirm the new tasks are there.
6. `notes minutes` — render minutes with the AGREED/RESOLVED/ACTION summary. Interactive; TTY only.

### 3. Quick-capture through the day, then file it

1. `buffer add "chase the SGB invoice"` — capture when you have no time to pick a thread.
2. `buffer add-text Projects/SGB "Client prefers Thursday calls"` — capture an observation against a thread.
3. `buffer add-action Projects/SGB "(Jane Doe) Send the signed SOW" --due 2026-09-30 --priority H` — capture an action.
4. `buffer list` — see everything queued, with line numbers.
5. `buffer tend` — regroup and validate; UNKNOWN entries are reported here.
6. `buffer rm <line-number>` then re-add with the right `add-*` command — fix each UNKNOWN.
7. `buffer flush` — write the entries into `logs/` and clear the buffer.
8. `tasks` — ingest the new ACTION lines in `logs/` into task anchors.

### 4. Work the task list

1. `tasks next` — the top 5 by priority, due date and entry date.
2. `tasks list --overdue` — what is past due.
3. `tasks show <uuid>` — read the detail for one anchor.
4. `tasks set-priority <uuid> H` — raise the priority if it has become urgent.
5. `tasks set-due <uuid> 2026-10-01` — move the due date.
6. `tasks done <uuid>` — flip the source line to `DONE:` and stamp the end date.

### 5. Log a session of work

1. `hours log Projects/SGB -m 120 "Drafted the integration spec"` — record two hours, using the thread's rate and currency.
2. `hours log Projects/SGB -m 45 -d 2026-09-09 -t 14:00 "Client call"` — record a session from an earlier day.
3. `hours list Projects/SGB --since 2026-09-01` — check what is recorded.
4. `hours edit <id> -m 90` — fix a duration you got wrong.

### 6. Bill a client for a month's work

1. `hours report --thread Projects/SGB --since 2026-09-01 --until 2026-09-30` — the month's totals by currency.
2. `hours list Projects/SGB --since 2026-09-01 --until 2026-09-30` — the line items, one per entry description.
3. `hours edit <id> --description "Integration spec — drafting and review"` — tidy any line item the client will read.
4. `threads show Projects/SGB` — confirm `client_name` and the other `client_*` fields are set.
5. `payments statement --thread Projects/SGB --pdf ~/Downloads/sgb-statement.pdf` — render the statement of account.

### 7. Record a payment

1. `payments log Projects/SGB 15000 -d 2026-09-05 -a "Business current" -n "Invoice 2026-09"` — record the receipt.
2. `payments list Projects/SGB` — confirm it landed.
3. `payments statement --thread Projects/SGB --as-of 2026-09-30` — billed against received, with aging.
4. `payments edit <id> --amount 16000` — correct the amount if it was wrong.

### 8. Check the vault and commit it

1. `lint` — validate every file against the schemas.
2. `lint <path>` — re-check the one file after you fix a violation.
3. `commit review` — read everything that has changed since the last commit.
4. `commit save --message "Log September SGB hours and payment" --dry-run` — confirm what would be staged.
5. `commit save --message "Log September SGB hours and payment"` — stage everything and commit.

## Data formats

`lint` enforces every schema below.

### `hours_file`

Billable and unbillable time for one thread, as JSON inside one ` ```simple-time-tracker ` fence. Files live at `hours/{Projects,Processes,Topics}/<Thread>.md`.

Frontmatter fields:

| Field | Required | Meaning |
|---|---|---|
| `thread` | Yes | Wikilink to the thread; must resolve. |
| `currency` | No | Three-letter uppercase ISO code. Omitted for an unbillable thread. |

Entry object fields:

| Field | Required | Meaning |
|---|---|---|
| `name` | Yes | The description of what was done. This is the invoice line item. |
| `startTime` | Yes | ISO 8601 UTC timestamp with milliseconds. |
| `endTime` | Yes | Same form; must not be earlier than `startTime`. |
| `id` | Yes | 8 hex characters, unique across the whole vault. |
| `rate` | Yes | Per-hour charge. `0` means unbillable and is an ordinary value. |
| `currency` | No | ISO 4217 code. Absent or null means unbilled. |

Duration is derived from `endTime` minus `startTime`; there is no duration field. The plugin's `subEntries` and `collapsed` keys are valid but unused. JSON is pretty-printed at indent 2.

### `log`

One thread's activity for one day, written by `buffer flush`. Files live at `logs/<Kind>/<Name>/<YYYY-MM-DD>.md`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | Yes | Wikilink to a `Projects`, `Processes` or `Topics` thread. |
| `date` | Yes | The day, `YYYY-MM-DD`. |
| `type` | Yes | Always `Log`. |

Body lines: `REF:` for a reference to another vault file, `TEXT:` for a free-text observation, `ACTION:` for an open action item, `TASK:` and `DONE:` for ingested items. `tasks` scans `logs/` exactly as it scans `notes/`. Sub-day timestamps are not preserved.

### `note_correspondence`

A note recording email, message or letter exchanges. Files live in `notes/`, named for a `YYYY-MM-DD-HH-MM-SS` timestamp.

| Field | Required | Meaning |
|---|---|---|
| `topic` | Yes | What the exchange is about. |
| `type` | Yes | `Correspondence`. |
| `threads` | Yes | List of thread wikilinks; each must resolve. |
| `timestamp` | Yes | When the exchange happened. |
| `people` | No | List of `[[people/X]]` wikilinks or plain strings for untracked participants. |

Body lines: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:`, `!:`.

### `note_meeting`

A note recording a meeting with one or more counterparties. Files live in `notes/`, named for a `YYYY-MM-DD-HH-MM-SS` timestamp.

| Field | Required | Meaning |
|---|---|---|
| `topic` | Yes | What the meeting was about. |
| `type` | Yes | `Meeting`. |
| `threads` | Yes | List of thread wikilinks; each must resolve. |
| `timestamp` | Yes | When the meeting happened. |
| `counterparty` | No | The other party. |
| `location` | No | Where it happened. |
| `people` | No | List of `[[people/X]]` wikilinks or plain strings for untracked attendees. |

Body lines: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:`, `!:`.

### `note_simple`

A note with no type-specific fields, for the bare-shape types. Files live in `notes/`, named for a `YYYY-MM-DD-HH-MM-SS` timestamp.

| Field | Required | Meaning |
|---|---|---|
| `topic` | Yes | What the note is about. |
| `type` | Yes | One of `Workshop`, `Report`, `Log`, `Research`, `Recipe`. |
| `threads` | Yes | List of thread wikilinks; each must resolve. |
| `timestamp` | Yes | When the thing happened. |
| `people` | No | List of wikilinks or plain strings. |

Body lines: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:`, `!:`.

### `payments_file`

Money received against one thread, as JSON inside one ` ```adulting-payments ` fence. Files live at `payments/{Projects,Processes,Topics}/<Thread>.md`.

Frontmatter fields:

| Field | Required | Meaning |
|---|---|---|
| `thread` | Yes | Wikilink to the thread; must resolve. |
| `currency` | Yes | Three-letter uppercase ISO code. |

Payment object fields:

| Field | Required | Meaning |
|---|---|---|
| `id` | Yes | 8 hex characters, unique across the whole vault. |
| `received` | Yes | ISO 8601 UTC timestamp for the date the money landed. |
| `amount` | Yes | Must be greater than zero. |
| `currency` | Yes | ISO 4217 code. |
| `account` | No | Which account the money landed in. |
| `note` | No | Free text. |

Payment ids share one namespace with hours entry ids; `lint` checks uniqueness across both. Amounts are computed as decimals, never floats. JSON is pretty-printed at indent 2.

### `person`

A contact you track. Files live in `people/`, one per person, named for the full name.

| Field | Required | Meaning |
|---|---|---|
| `status` | Yes | `open`, `paused` or `closed`. |
| `category` | Yes | `professional`, `personal` or `voluntary`. |
| `started` | Yes | `YYYY-MM-DD`. |
| `ended` | No | `YYYY-MM-DD`. Required when `status` is `closed`. |
| `cadences` | No | List of `{key, frequency, description}` objects. |

The body is free-form. A person is a link target for `note.people` and for a task's assignee, never a thread.

### `task_anchor`

A single `TASK:` or `DONE:` line inside a note or log. This line is the vault's source of truth for task state.

| Field | Required | Meaning |
|---|---|---|
| `kind` | Yes | `TASK` or `DONE`. |
| `priority` | No | `H`, `M` or `L`, written as a visible `[#X]` token. |
| `assignee` | No | Person name in parentheses; must resolve to `people/<name>.md`. |
| `body` | Yes | The description. |
| `uuid` | Yes | 8 hex characters, unique across the vault. |
| `entry` | Yes | The ingest date. |
| `end` | No | The completion date. Required when `kind` is `DONE`; must not be earlier than `entry`. |
| `due` | No | Due date. |
| `scheduled` | No | Scheduled date. |
| `depends` | No | Comma-separated 8-character uuids. Each must resolve to another anchor, and the graph must be acyclic. |

Attribute order in the trailing comment is fixed: `entry`, `end`, `due`, `scheduled`, `depends`. Priority never appears in the comment. The comment is hidden in Obsidian preview. Written and mutated only by `tasks`.

Example:

```
TASK: [#H] (Riaz Arbi) Send quarterly report <!--abcd1234 entry:2026-05-27 due:2026-05-29-->
```

### `thread`

A project, process or topic, holding a chronological log. Files live in `threads/{Projects,Processes,Topics}/`.

| Field | Required | Meaning |
|---|---|---|
| `status` | Yes | `open`, `paused` or `closed`. |
| `kind` | Yes | `project`, `process` or `topic`. |
| `category` | Yes | `professional`, `personal` or `voluntary`. |
| `started` | Yes | `YYYY-MM-DD`. |
| `ended` | No | `YYYY-MM-DD`. Required when `status` is `closed`. |
| `cadences` | No | List of `{key, frequency, description}` objects. |
| `currency` | No | Three-letter uppercase ISO code; the default `hours` applies. |
| `rate` | No | Default hourly rate for `hours`. |
| `client_name` | No | The party billed on a statement. Required to render a statement PDF. |
| `client_address` | No | Pipe-separated, one line: `Unit 301\|2 Park Road\|Cape Town`. |
| `client_vat` | No | Client VAT number. |
| `client_email` | No | Client email address. |

Per-cadence fields are `key` (unique within the thread, used as a tag), `frequency` (interval in days) and `description`. A cadence is satisfied when a log entry tagged `#<key>` is added.

`rate` falls back to `time.rate` in `.adulting/config.yaml`, then to 2500. Both rate and currency are resolved at write time and stored on each hours entry. The supplier side and banking details are vault-wide and live in `.adulting/config.yaml` under `billing:`. The payment reference on a statement is the thread name without its `Kind/` prefix.

### `thread_entry`

A single dated bullet at the top level of a thread file's body.

| Field | Required | Meaning |
|---|---|---|
| `date` | Yes | `YYYY-MM-DD`, at the start of the bullet. |
| `text` | Yes | The entry text, after an em dash. |

Indented sub-bullets are continuation detail and are not separately validated. Out-of-order dates are tolerated. For an entry that needs structure, write a note and link to it from the bullet.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `buffer tend` reports violations and `flush` will not run | UNKNOWN entries are in the buffer. They are invalid by design. | `buffer rm <line-number>`, then re-add with `buffer add-text`, `add-ref` or `add-action`. |
| `buffer add-action` exits 1 with a `--due must be YYYY-MM-DD` message | The date is not in `YYYY-MM-DD` form. | Re-run with a full ISO date. |
| `buffer add-action` exits 1 on `--depends` | The value is not exactly 8 hex characters. | Pass the 8-character uuid prefix from `tasks list` or `tasks show`. |
| `tasks done <uuid>` exits 1 with "no task found with uuid prefix" | No anchor in the vault matches that prefix. | Find the real uuid with `tasks list` or `tasks show`. |
| `tasks` exits 1 with "uuid prefix is ambiguous" | The prefix matches more than one anchor. | Use more characters of the uuid. |
| `tasks set-assignee` exits 1 with "does not resolve" | There is no `people/<name>.md` for that person. | `people new --name "<name>" --category professional`, then retry. |
| `tasks add-depends` exits 1 with "a task cannot depend on itself" | The dependency uuid equals the task uuid. | Pass a different task's uuid. |
| `search` exits 1 with "could not resolve thread" | The thread argument does not match a thread file. | Find the name with `threads list <query>`, then pass `Kind/Name`. |
| `hours log` refuses to write | A rate was given with no currency to express it in. | Pass `-c <ISO>`, or set `currency` on the thread with `threads new --currency`. |
| Hours appear under an `unbilled` row and never in a statement | The thread has no currency, so entries are written with rate 0 and no currency. | Set a currency on the thread if the work is billable, then log new entries. |
| `commit save` exits 1 with "must be a single line" | The `--message` value contains a newline. | Keep `--message` to one line and put the detail in `--body`. |
| `commit save` exits 1 with "not the root of its git repository" | `ADULTING_HOME` points inside a repo, not at its root. | Point `ADULTING_HOME` at the repository root. |
| `lint` exits 1 and prints `<path>:<line>: <message>` | A file breaks a schema rule. | Fix the named field or line, then `lint <path>` to re-check. |
| `notes` hangs or fails with no output when scripted | Every subcommand except `last` reads a picker selection from stdin. | Use `notes last`, or run the others at a terminal. |

## Quick reference

| Command | Does |
|---|---|
| `tasks` | Ingest ACTION lines into TASK anchors in place. |
| `tasks add <thread> <text>` | Buffer-append a structured ACTION. |
| `tasks done <uuid>` | Mark a task complete. |
| `tasks set-description <uuid> <text>` | Rewrite the task body. |
| `tasks set-assignee <uuid> <person>` | Set the assignee. |
| `tasks set-due <uuid> <date>` | Set the due date. |
| `tasks set-scheduled <uuid> <date>` | Set the scheduled date. |
| `tasks set-priority <uuid> <H\|M\|L>` | Set the priority. |
| `tasks add-depends <uuid> <dep-uuid>` | Add a dependency. |
| `tasks rm-depends <uuid> <dep-uuid>` | Remove a dependency. |
| `tasks list` | List pending tasks. |
| `tasks next` | Top 5 pending tasks. |
| `tasks show <uuid>` | Detail view of one anchor. |
| `notes new` | Create a note (interactive). |
| `notes copy` | Copy a note to a new timestamp (interactive). |
| `notes strip` | Copy a note without its body (interactive). |
| `notes edit` | Edit a note in the default editor (interactive). |
| `notes nano` | Edit a note in nano (interactive). |
| `notes last` | Open the most recent note. |
| `notes delete` | Permanently delete a note (interactive). |
| `notes cat` | Print a note to stdout (interactive). |
| `notes pdf` | Render a note to PDF and markdown (interactive). |
| `notes minutes` | Render meeting minutes (interactive). |
| `notes agenda` | Render a meeting agenda (interactive). |
| `search notes` | Find notes by thread, type, date or text. |
| `search logs` | Find daily logs by thread, date or text. |
| `search activity` | Rank threads by activity in a window. |
| `search overview <thread>` | The whole picture of one thread. |
| `threads list` | List thread files. |
| `threads show <thread>` | Show one thread file. |
| `threads new` | Create a thread file. |
| `threads delete <thread>` | Permanently delete a thread file. |
| `people list` | List person files. |
| `people show <person>` | Show one person file. |
| `people new` | Create a person file. |
| `people delete <person>` | Permanently delete a person file. |
| `hours log <thread> <description>` | Append a time entry. |
| `hours list` | List time entries. |
| `hours report` | Totals by thread and currency. |
| `hours show <id>` | Show one time entry. |
| `hours edit <id>` | Change one field of a time entry. |
| `hours rm <id>` | Delete a time entry. |
| `payments log <thread> <amount>` | Record a receipt. |
| `payments list` | List payments. |
| `payments statement` | Billed against received, by thread and currency. |
| `payments show <id>` | Show one payment. |
| `payments edit <id>` | Change one field of a payment. |
| `payments rm <id>` | Delete a payment. |
| `buffer add <text>` | Append a raw UNKNOWN capture. |
| `buffer suggest <text>` | Propose a structured entry for raw text. |
| `buffer add-text <thread> <text>` | Append a TEXT entry. |
| `buffer add-ref <thread> <target>` | Append a REF entry. |
| `buffer add-action <thread> <text>` | Append an ACTION entry. |
| `buffer list` | Show the buffer with line numbers. |
| `buffer rm <line-number>` | Remove one buffer line. |
| `buffer tend` | Regroup and validate the buffer. |
| `buffer flush` | Write the buffer to logs and clear it. |
| `lint` | Validate vault files against the schemas. |
| `commit review` | Show everything changed since the last commit. |
| `commit save --message <text>` | Stage every vault change and commit it. |
