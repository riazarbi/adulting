# adulting — Operators Manual

## Before you start

Everything lives in one directory: `~/vault/`. Set `ADULTING_HOME` to point the tools at a different vault root. Every subdirectory — `notes/`, `logs/`, `threads/{Projects,Processes,Topics}/`, `people/`, `hours/`, `payments/` — sits under that root, plus `buffer.md` and the hidden `.adulting/` for config.

External programs you need:

| Program | Needed by |
|---|---|
| `bash`, `python3`, `awk`, `sed`, `grep` | everything |
| `pandoc` plus `xelatex` | `notes pdf`, `notes minutes`, `notes agenda` |
| `open` (macOS) or `xdg-open` (Linux) | opening notes in Obsidian |

All state is plain text on disk: markdown files with YAML frontmatter, and JSON inside fenced blocks. You can read it, `grep` it, diff it and back it up without any of these tools.

## How the pieces fit

| Object | What it is | Where it lives |
|---|---|---|
| Note | A persisted record: meeting, correspondence, report, research, log, recipe, workshop. | `notes/` |
| Log | A per-thread per-day file written by `buffer flush`. | `logs/<Kind>/<Name>/<YYYY-MM-DD>.md` |
| Thread | An organising lens: a project, process, or topic. | `threads/{Projects,Processes,Topics}/` |
| Person | A contact you track; a link target only. | `people/` |
| Time entry | One session of work on a thread, billable or not. | `hours/{Projects,Processes,Topics}/<Thread>.md` |
| Payment | Money received against a thread. | `payments/{Projects,Processes,Topics}/<Thread>.md` |
| Action / task | An `ACTION:` line, ingested in place into a `TASK:` anchor. | inside notes and logs |
| Buffer entry | A staged capture, not yet filed. | `buffer.md` |

Relationships that matter:

- A note lists one or more threads in `threads:`; each must resolve to a thread file.
- A note may list people; wikilink entries must resolve to `people/<name>.md`.
- A task's assignee must resolve to `people/<name>.md`.
- A task's `depends` ids must resolve to other task uuids, and the graph must be acyclic.
- Hours files and payments files each name one thread and mirror the `threads/` layout.
- A thread's `currency` and `rate` are the defaults `hours` applies; `client_*` fields feed the payment statement PDF.
- Source notes and logs are the only task store. There is no backend.

## Command reference

### `tasks`

Turns `ACTION:` lines in notes and logs into anchored `TASK:` lines, and edits those anchors.

**When to use it**

- You wrote `ACTION:` lines in a note and want them tracked.
- You finished a task and need to close it.
- You want to see what to work on next.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| (none) | Scans `notes/` and `logs/`, validates every `ACTION:` line, rewrites it in place as a `TASK:` anchor with a fresh uuid. | `tasks` |
| `add` | Buffer-appends a structured ACTION. | `tasks add Projects/SGB "(Riaz Arbi) Draft the scope"` |
| `done` | Flips the source `TASK:` to `DONE:` and stamps `end:` with today. | `tasks done abcd1234` |
| `set-description` | Rewrites the task body. | `tasks set-description abcd1234 "Draft and send the scope"` |
| `set-assignee` | Rewrites the `(Assignee)` prefix. | `tasks set-assignee abcd1234 "Riaz Arbi"` |
| `set-due` | Sets the due date. | `tasks set-due abcd1234 2026-05-29` |
| `set-scheduled` | Sets the scheduled date. | `tasks set-scheduled abcd1234 2026-05-27` |
| `set-priority` | Sets priority; writes `[#X]` in the visible portion. | `tasks set-priority abcd1234 H` |
| `add-depends` | Adds a dependency. | `tasks add-depends abcd1234 ef567890` |
| `rm-depends` | Removes a dependency. | `tasks rm-depends abcd1234 ef567890` |
| `list` | Lists pending tasks. | `tasks list --priority H --overdue` |
| `next` | Top 5 pending tasks by priority, due, entry. | `tasks next` |
| `show` | Detail view of one anchor. | `tasks show abcd1234` |

**Options**

| Option | Effect |
|---|---|
| `--dry-run` | Default invocation only. Shows what would be ingested; writes nothing. |
| `--quiet` | Default invocation only. Suppresses per-action output. |
| `add --due <YYYY-MM-DD>` | Due date. |
| `add --scheduled <YYYY-MM-DD>` | Scheduled date. |
| `add --priority H\|M\|L` | Priority. |
| `add --depends <uuid8>` | 8-char uuid prefix; repeatable. |
| `list --priority H\|M\|L` | Filter to one priority. |
| `list --thread <Kind/Name>` | Filter to tasks whose source note carries this thread. |
| `list --assignee <person>` | Filter to one assignee. |
| `list --overdue` | Only tasks due before today. |

**Notes**

- The no-argument invocation rewrites source notes and logs in place. Use `--dry-run` first if you want to see the effect.
- Do not write `TASK:` lines by hand. `tasks` owns them.
- Exit code `1` on: empty description, a task depending on itself, no task matching a uuid prefix, an ambiguous uuid prefix, or an assignee that does not resolve to `people/<person>.md`.

### `notes`

Creates, edits, queries and renders note files.

**When to use it**

- You are about to take minutes in a meeting.
- You need a PDF of a note to send to someone.
- You want to reread the last thing you wrote.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Creates a new note and opens it. Interactive, TTY only. | `notes new` |
| `copy` | Picks a note, copies its contents to a new timestamp. Interactive. | `notes copy` |
| `strip` | Picks a note, copies it and removes the body, for templating. Interactive. | `notes strip` |
| `edit` | Picks a note, opens it in the default editor. Interactive. | `notes edit SGB` |
| `nano` | Picks a note, opens it in nano. Interactive. | `notes nano` |
| `last` | Opens the most recently created note. | `notes last` |
| `delete` | Picks a note and deletes it permanently. Interactive. | `notes delete` |
| `cat` | Picks a note and prints it to stdout. | `notes cat SGB` |
| `pdf` | Renders a note to PDF plus markdown, with an ACTION/TASK summary. | `notes pdf SGB` |
| `minutes` | Renders meeting minutes: TOC plus AGREED/RESOLVED/ACTION summary. | `notes minutes SGB` |
| `agenda` | Renders a meeting agenda. | `notes agenda SGB` |

**Options**

| Option | Effect |
|---|---|
| `[filter]` | Optional second argument. Filters the picker list, case-insensitive. |

**Notes**

- `new`, `copy`, `strip`, `edit`, `nano` and `delete` are interactive and need a TTY. An agent must not call them.
- `delete` is permanent.
- Rendered output goes to `$EXPORT_DIR`, default `~/Downloads`.
- Body keywords you can write by hand: `ACTION:`, `AGREED:`, `RESOLVED:`, `!:`. Do not write `TASK:` by hand.

### `threads`

Manages thread files.

**When to use it**

- You are starting a new client project and need somewhere to hang notes and hours.
- You need to check a thread's billing rate and currency.
- You want a list of what is open.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists thread files, open only by default. | `threads list SGB` |
| `show` | Shows one thread file. | `threads show Projects/SGB` |
| `new` | Creates a thread file; prompts for missing fields. | `threads new --name SGB --kind project --category professional --currency ZAR --rate 2500` |
| `delete` | Deletes a thread file permanently. | `threads delete Projects/SGB -y` |

**Options**

| Option | Effect |
|---|---|
| `list --all` | Include paused and closed threads. |
| `list --json` / `show --json` | JSON output. |
| `new --name <name>` | Thread name; skips the prompt. |
| `new --kind project\|process\|topic` | Kind; skips the prompt. |
| `new --category professional\|personal\|voluntary` | Category; skips the prompt. |
| `new --currency <ISO>` | Default currency for `hours`. |
| `new --rate <int>` | Default hourly rate. Requires `--currency`. |
| `delete -y` | Skips the confirmation prompt. |

**Notes**

- `threads new` prompts for any field you do not pass. Pass `--name`, `--kind` and `--category` to run it without a TTY.
- `threads delete` is permanent. Without `-y` it asks for confirmation, so an agent must pass `-y`.

### `people`

Manages person files.

**When to use it**

- Someone new is now an assignee on tasks.
- You want to check who you track and in what category.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | Lists person files, open only by default. | `people list Arbi` |
| `show` | Shows one person file. | `people show "Riaz Arbi"` |
| `new` | Creates a person file; prompts for missing fields. | `people new --name "Riaz Arbi" --category professional` |
| `delete` | Deletes a person file permanently. | `people delete "Riaz Arbi" -y` |

**Options**

| Option | Effect |
|---|---|
| `list --all` | Include closed people. |
| `list --json` / `show --json` | JSON output. |
| `new --name <full name>` | Full name; skips the prompt. |
| `new --category professional\|personal\|voluntary` | Category; skips the prompt. |
| `delete -y` | Skips the confirmation prompt. |

**Notes**

- People are link targets only. A person can never be the value of a note's thread.
- Pass `--name` and `--category` to `people new` to avoid the prompts.

### `hours`

Tracks time worked against a thread.

**When to use it**

- You just finished a block of work and want it billable.
- A client asks how many hours went into a month.
- You typed the wrong duration and need to fix it.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Appends a time entry. Interactive if you give no thread. | `hours log Projects/SGB Drafted the scope document -m 90` |
| `list` | Lists entries. | `hours list Projects/SGB --since 2026-05-01 --until 2026-05-31` |
| `report` | Totals by thread and currency. | `hours report --thread Projects/SGB --since 2026-05-01 --until 2026-05-31` |
| `show` | Shows one entry. | `hours show abcd1234` |
| `edit` | Changes one field of an entry. | `hours edit abcd1234 -m 120` |
| `rm` | Deletes an entry. | `hours rm abcd1234 -y` |

**Options**

| Option | Effect |
|---|---|
| `log -m, --minutes <n>` | Duration in minutes. Default 60. |
| `log -r, --rate <n>` | Hourly rate. `0` means unbillable; the hours still count. |
| `log -c, --currency <ISO>` | Currency code. Defaults to the thread's. |
| `log -d, --date <YYYY-MM-DD>` | Date. Default today. |
| `log -t, --time <HH:MM>` | Start time. Default now. |
| `log --all` | Interactive mode: list paused and closed threads too. |
| `list --since` / `--until <YYYY-MM-DD>` | Inclusive date bounds. |
| `report --thread <Kind/Name>` | Limit the report to one thread. |
| `report --since` / `--until <YYYY-MM-DD>` | Date bounds. |
| `list --json`, `report --json`, `show --json` | JSON output. |
| `edit --description <text>`, `-m`, `-r`, `-c`, `-d`, `-t` | Change that field on the entry. |
| `rm -y` | Skips the confirmation prompt. |

**Notes**

- `hours log` with no thread is interactive. An agent must always pass a thread.
- Rate and currency are resolved at write time and stored on each entry. Changing a thread's defaults never re-prices logged work.
- The entry description becomes an invoice line item. Write it for the client.

### `payments`

Records money received against a thread and reports billed versus received.

**When to use it**

- A client's transfer landed.
- You need a statement of account to send.
- You want to know what is still outstanding.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Records a receipt. Interactive if you give no thread. | `payments log Projects/SGB 12500 -a "Business current" -n "May invoice"` |
| `list` | Lists payments. | `payments list Projects/SGB --since 2026-05-01` |
| `statement` | Billed versus received, by thread and currency. | `payments statement --thread Projects/SGB --as-of 2026-06-01` |
| `show` | Shows one payment. | `payments show ef567890` |
| `edit` | Changes one field of a payment. | `payments edit ef567890 --amount 12750` |
| `rm` | Deletes a payment. | `payments rm ef567890 -y` |

**Options**

| Option | Effect |
|---|---|
| `log -c, --currency <ISO>` | Currency. Defaults to the thread's. |
| `log -d, --date <YYYY-MM-DD>` | Date received. Default today. |
| `log -t, --time <HH:MM>` | Time. Default now. |
| `log -a, --account <name>` | Which account the money landed in. |
| `log -n, --note <text>` | Free-text note. |
| `log --all` | Interactive mode: list paused and closed threads too. |
| `list --since` / `--until <YYYY-MM-DD>` | Date bounds. |
| `statement --thread <Kind/Name>` | Limit to one thread. |
| `statement --since` / `--until <YYYY-MM-DD>` | Date bounds. |
| `statement --as-of <YYYY-MM-DD>` | Statement date; drives aging. Default today. |
| `statement --pdf <path>` | Renders a PDF to that path. Requires `--thread`. |
| `list --json`, `statement --json`, `show --json` | JSON output. |
| `edit --amount`, `-c`, `-d`, `-t`, `-a`, `-n` | Change that field on the payment. |
| `rm -y` | Skips the confirmation prompt. |

**Notes**

- `payments log` with no thread is interactive. An agent must always pass a thread and an amount.
- Amounts must be positive. There is no negative payment.
- `statement --pdf` needs `client_name` on the thread to render.

### `buffer`

Operates the quick-capture queue at `buffer.md`.

**When to use it**

- You think of something mid-task and cannot stop to pick a thread.
- You have a pile of captures and want them filed into `logs/`.
- You need to fix or drop a bad capture line.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `add` | Appends an UNKNOWN entry. Raw capture. | `buffer add "chase the SGB invoice"` |
| `suggest` | Proposes a structured `add-*` for raw text; prompts to accept. | `buffer suggest "chase the SGB invoice" -y` |
| `add-text` | Appends a TEXT entry. | `buffer add-text Projects/SGB "Client prefers Friday calls"` |
| `add-ref` | Appends a REF entry. | `buffer add-ref Projects/SGB notes/2026-05-27-14-30-00 "Scope meeting"` |
| `add-action` | Appends an ACTION entry. Same as `tasks add`. | `buffer add-action Projects/SGB "(Riaz Arbi) Send the invoice" --due 2026-06-01` |
| `list` | Shows the buffer with line numbers. | `buffer list SGB` |
| `rm` | Removes one line by number. | `buffer rm 3` |
| `tend` | Regroups by thread and date, then validates. Idempotent. | `buffer tend` |
| `flush` | Tends, writes to `logs/`, then clears the buffer. | `buffer flush` |

**Options**

| Option | Effect |
|---|---|
| `--quiet` | Suppresses info output. Global; applies to all subcommands. |
| `suggest -y` | Auto-accepts the suggestion without prompting. |
| `add-action --due <YYYY-MM-DD>` | Due date, applied on flush and ingest. |
| `add-action --scheduled <YYYY-MM-DD>` | Scheduled date. |
| `add-action --priority H\|M\|L` | Priority. |
| `add-action --depends <uuid8>` | 8-char uuid prefix; repeatable. |

**Notes**

- `buffer suggest` prompts unless you pass `-y`. An agent must pass `-y`.
- UNKNOWN entries are invalid by design. `tend` reports them and they block `flush` until you remove them and re-add via an `add-*` command.
- `flush` empties `buffer.md`. Run `tend` first if you want to check it will pass.
- Do not edit `buffer.md` by hand; use `add-*`, `rm` and `tend`.
- Exit code `1` on: empty text, empty description, empty description after an assignee, a `--depends` value that is not 8 hex chars, or a `--due` / `--scheduled` value that is not `YYYY-MM-DD`.

### `lint`

Validates vault files against the schemas.

**When to use it**

- Before committing, to check nothing is malformed.
- After hand-editing frontmatter.
- To check one file you just wrote.

**Usage**

`lint [<path> ...]`

| Argument | Meaning |
|---|---|
| `paths` | Files to validate. Default: walk the whole vault. |

**Options**

| Option | Effect |
|---|---|
| `--schemas <dir>` | Use a different schemas directory. |
| `--quiet` | Exit code only; no per-violation output. |

**Notes**

- Exit `0` when clean, `1` when there are violations, `2` on a usage failure.
- Violations print as `<path>:<line>: <message>`.

### `commit`

Reviews uncommitted vault changes, then stages and commits them.

**When to use it**

- End of a working session, to record what changed.
- Before a flush or a bulk edit, to see the current state.
- To write an accurate commit message from a real diff.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `review` | Shows everything changed since the last commit. Read-only. | `commit review` |
| `save` | Stages every change in the vault and commits it. | `commit save --message "Log May SGB hours"` |

**Options**

| Option | Effect |
|---|---|
| `review --max-file-lines <n>` | Max diff lines per file. Default 150. |
| `review --max-lines <n>` | Max output lines overall. Default 3000. |
| `save --message <text>` | Commit subject. Required. Single line. |
| `save --body <text>` | Commit body. May span lines. |
| `save --dry-run` | Reports what would be staged and committed; changes nothing. |

**Notes**

- `save` only ever adds a commit. It never amends, rebases, resets, checks out or pushes.
- Exit code `1` on: an empty `--message`, a multi-line `--message`, `ADULTING_HOME` not being a directory, `ADULTING_HOME` not being the root of its git repository, or a failing git call.

## Everyday procedures

### 1. Set up a new billable project

1. `threads new --name SGB --kind project --category professional --currency ZAR --rate 2500` — creates the thread with billing defaults.
2. `threads show Projects/SGB` — confirms the file and its fields.
3. `people new --name "Jane Client" --category professional` — adds anyone you will assign tasks to.
4. `lint` — checks the new files validate.
5. `commit save --message "Open Projects/SGB"` — records the setup.

### 2. Capture a meeting and turn its actions into tracked tasks

1. `notes new` — creates the meeting note and opens it. Interactive; run it yourself at a terminal.
2. Write the body, using `ACTION:`, `AGREED:`, `RESOLVED:` and `!:` lines.
3. `tasks --dry-run` — shows which ACTION lines would be ingested.
4. `tasks` — rewrites each ACTION line in place as a `TASK:` anchor.
5. `notes minutes SGB` — renders minutes with the TOC and the AGREED/RESOLVED/ACTION summary.
6. `lint` — checks the note and its anchors.

### 3. Quick-capture through the day, then file it

1. `buffer add "chase the SGB invoice"` — raw capture when you cannot stop to pick a thread.
2. `buffer add-text Projects/SGB "Client prefers Friday calls"` — a shaped observation.
3. `buffer list` — shows the queue with line numbers.
4. `buffer rm 1` — drops the UNKNOWN line so it stops blocking.
5. `buffer add-action Projects/SGB "(Riaz Arbi) Send the invoice" --due 2026-06-01` — re-adds it properly.
6. `buffer tend` — regroups and validates.
7. `buffer flush` — writes `logs/` and clears the buffer.
8. `tasks` — ingests the flushed ACTION lines into anchors.

### 4. Work the task list

1. `tasks next` — the top 5 by priority, due, entry.
2. `tasks list --overdue` — what has slipped.
3. `tasks show abcd1234` — the detail on one anchor.
4. `tasks set-priority abcd1234 H` — raise it.
5. `tasks set-due abcd1234 2026-06-05` — move the deadline.
6. `tasks done abcd1234` — close it and stamp `end:`.

### 5. Log a session of work

1. `hours log Projects/SGB Drafted the scope document -m 90` — appends the entry.
2. `hours list Projects/SGB` — confirms it landed.
3. `hours edit abcd1234 -m 120` — fixes the duration if it was wrong.
4. `commit save --message "Log SGB scope drafting"` — records it.

### 6. Bill a client for a month's work

1. `hours report --thread Projects/SGB --since 2026-05-01 --until 2026-05-31` — the month's totals by currency.
2. `hours list Projects/SGB --since 2026-05-01 --until 2026-05-31` — the line items, in entry-description form.
3. `threads show Projects/SGB` — confirms `client_name` and the other `client_*` fields are set.
4. `payments statement --thread Projects/SGB --as-of 2026-06-01 --pdf ~/Downloads/sgb-statement.pdf` — renders the statement of account.

### 7. Record a payment

1. `payments log Projects/SGB 12500 -d 2026-06-03 -a "Business current" -n "May invoice"` — records the receipt.
2. `payments list Projects/SGB` — confirms it.
3. `payments statement --thread Projects/SGB` — billed versus received after the receipt.
4. `commit save --message "Record SGB May payment"` — records it.

### 8. Check the vault and commit it

1. `lint` — validates everything; exit `0` means clean.
2. `commit review` — shows every change since the last commit.
3. `commit save --message "Weekly vault update" --body "Flushed buffer, logged SGB hours, closed three tasks." --dry-run` — checks what would be staged.
4. `commit save --message "Weekly vault update" --body "Flushed buffer, logged SGB hours, closed three tasks."` — stages and commits.

## Data formats

`lint` enforces every schema below.

### `hours_file`

Billable time for one thread, one file per thread, at `~/vault/hours/{Projects,Processes,Topics}/<Thread>.md`. The body holds exactly one ` ```simple-time-tracker ` fence containing JSON `{"entries": [...]}`.

Frontmatter:

| Field | Required | Meaning |
|---|---|---|
| `thread` | Yes | Wikilink to the thread; must resolve. |
| `currency` | Yes | Three-letter uppercase ISO code. |

Entry object:

| Field | Required | Meaning |
|---|---|---|
| `name` | Yes | The description of what was done. Becomes an invoice line item. |
| `startTime` | Yes | ISO 8601 UTC start. |
| `endTime` | Yes | ISO 8601 UTC end; not earlier than `startTime`. |
| `id` | Yes | 8 hex chars, unique across the vault. |
| `rate` | Yes | Per-hour charge. `0` means unbillable and is an ordinary value. |
| `currency` | Yes | ISO 4217 code, stored per entry. |

Duration is derived from `endTime` minus `startTime`; there is no duration field. The plugin's `subEntries` and `collapsed` keys are valid but unused.

### `log`

A per-thread per-day record of activity, written by `buffer flush`, at `~/vault/logs/<Kind>/<Name>/<YYYY-MM-DD>.md`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | Yes | Wikilink to `Projects/`, `Processes/` or `Topics/`. |
| `date` | Yes | The day, `YYYY-MM-DD`. |
| `type` | Yes | Always `Log`. |

Body lines: `REF:` a reference to another file, `TEXT:` a free-text observation, `ACTION:` an open action item, `TASK:` an ingested one, `DONE:` a completed one. `tasks` ingest treats logs and notes identically.

### `note_correspondence`

A note recording email, message or letter exchanges. Lives in `~/vault/notes/`, filename `YYYY-MM-DD-HH-MM-SS.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | Yes | What the note is about. |
| `type` | Yes | `Correspondence`. |
| `threads` | Yes | List of thread wikilinks; each must resolve. |
| `timestamp` | Yes | Matches the filename stem. |
| `people` | No | List; wikilinks must resolve, plain strings are untracked participants. |

### `note_meeting`

A note recording a meeting with one or more counterparties. Lives in `~/vault/notes/`, filename `YYYY-MM-DD-HH-MM-SS.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | Yes | What the meeting was about. |
| `type` | Yes | `Meeting`. |
| `threads` | Yes | List of thread wikilinks; each must resolve. |
| `timestamp` | Yes | Matches the filename stem. |
| `counterparty` | No | Who you met. |
| `location` | No | Where it happened. |
| `people` | No | List; wikilinks must resolve, plain strings are untracked attendees. |

### `note_simple`

A note of a bare-shape type. Lives in `~/vault/notes/`, filename `YYYY-MM-DD-HH-MM-SS.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | Yes | What the note is about. |
| `type` | Yes | One of `Workshop`, `Report`, `Log`, `Research`, `Recipe`. |
| `threads` | Yes | List of thread wikilinks; each must resolve. |
| `timestamp` | Yes | Matches the filename stem. |
| `people` | No | List; wikilinks or plain strings. |

### `payments_file`

Money received against one thread, one file per thread, at `~/vault/payments/{Projects,Processes,Topics}/<Thread>.md`. The body holds exactly one ` ```adulting-payments ` fence containing JSON `{"payments": [...]}`.

Frontmatter:

| Field | Required | Meaning |
|---|---|---|
| `thread` | Yes | Wikilink to the thread; must resolve. |
| `currency` | Yes | Three-letter uppercase ISO code. |

Payment object:

| Field | Required | Meaning |
|---|---|---|
| `id` | Yes | 8 hex chars, unique across the vault and shared with `hours` ids. |
| `received` | Yes | ISO 8601 UTC date the money landed. |
| `amount` | Yes | Must be greater than zero. |
| `currency` | Yes | ISO 4217 code. |
| `account` | No | Which account it landed in. |
| `note` | No | Free text. |

Amounts are computed as decimals, never floats. A refund is not a negative payment.

### `person`

A file for someone you track, in `~/vault/people/`. People are link targets for note `people` entries and task assignees; they can never be a note's thread.

| Field | Required | Meaning |
|---|---|---|
| `status` | Yes | `open`, `paused` or `closed`. |
| `category` | Yes | `professional`, `personal` or `voluntary`. |
| `started` | Yes | `YYYY-MM-DD`. |
| `ended` | No | `YYYY-MM-DD`. Required when `status` is `closed`. |
| `cadences` | No | List of `{key, frequency, description}`. |

The body is free-form.

### `task_anchor`

A single `TASK:` or `DONE:` line inside a note or log file. This is the source of truth for task state.

| Field | Required | Meaning |
|---|---|---|
| `kind` | Yes | `TASK` or `DONE`. |
| `priority` | No | `H`, `M` or `L`, written as `[#X]` in the visible portion. |
| `assignee` | No | Written as `(Name)`; must resolve to `people/<name>.md`. |
| `body` | Yes | The task description. |
| `uuid` | Yes | 8 hex chars, unique across the vault. |
| `entry` | Yes | The ingest date. |
| `end` | No | The completion date. Required when `kind` is `DONE`; not earlier than `entry`. |
| `due` | Yes/No — No | The due date. |
| `scheduled` | No | The scheduled date. |
| `depends` | No | Comma-separated uuids; each must resolve, and the graph must be acyclic. |

The attrs live in an HTML comment, hidden in Obsidian preview. Attr order is fixed: `entry`, `end`, `due`, `scheduled`, `depends`. Only `tasks` writes these lines.

### `thread`

A markdown file holding the chronological log of one project, process or relationship. Lives in `~/vault/threads/`.

| Field | Required | Meaning |
|---|---|---|
| `status` | Yes | `open`, `paused` or `closed`. |
| `kind` | Yes | `project`, `process` or `topic`. |
| `category` | Yes | `professional`, `personal` or `voluntary`. |
| `started` | Yes | `YYYY-MM-DD`. |
| `ended` | No | `YYYY-MM-DD`. Required when `status` is `closed`. |
| `cadences` | No | List of `{key, frequency, description}`; `frequency` is an interval in days. |
| `currency` | No | Three-letter uppercase ISO code; the default `hours` uses. |
| `rate` | No | Default hourly rate. Falls back to `.adulting/config.yaml`'s `time.rate`, then 2500. |
| `client_name` | No | Party billed on a statement. Required to render one. |
| `client_address` | No | Pipe-separated address, e.g. `Unit 301\|2 Park Road\|Cape Town`. |
| `client_vat` | No | Client VAT number. |
| `client_email` | No | Client email. |

`hours log` refuses to write without a currency. Supplier and banking details live vault-wide in `.adulting/config.yaml` under `billing:`.

### `thread_entry`

A single dated bullet at the top level of a thread file's body, of the form `- YYYY-MM-DD — text`.

| Field | Required | Meaning |
|---|---|---|
| `date` | Yes | `YYYY-MM-DD`. |
| `text` | Yes | The entry text; at least one character. |

Indented sub-bullets are continuation detail and are not separately validated. Out-of-order dates are tolerated.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `buffer flush` refuses to run | UNKNOWN entries in the buffer are invalid by design and `tend` reports them. | `buffer list`, `buffer rm <line>`, then re-add with `buffer add-text`, `add-ref` or `add-action`. |
| `buffer add-action` exits 1 with a `--due` message | The date is not `YYYY-MM-DD`. | Re-run with the full ISO date. |
| `buffer add-action` exits 1 with a `--depends` message | The value is not 8 hex characters. | Pass the 8-char uuid prefix exactly. |
| `tasks` exits 1: person does not resolve | The assignee has no `people/<person>.md`. | `people new --name "<person>" --category <category>`, then retry. |
| `tasks` exits 1: uuid prefix is ambiguous | More than one anchor matches the prefix. | Use more characters of the uuid, or `tasks list` to find the full one. |
| `tasks` exits 1: no task found with uuid prefix | No anchor matches. | `tasks list` or `tasks show` to get the right uuid. |
| `tasks` exits 1: a task cannot depend on itself | `add-depends` was given the task's own uuid. | Pass a different task's uuid. |
| `hours log` refuses to write | The thread has no currency and none was passed. | Set `currency` on the thread, or pass `-c <ISO>`. |
| `payments statement --pdf` will not render | `--pdf` requires `--thread`, and the thread needs `client_name`. | Pass `--thread`, and add `client_name` to the thread file. |
| `lint` exits 1 with `<path>:<line>:` messages | A file breaks its schema. | Fix the named field on the named line, then re-run `lint`. |
| `commit save` exits 1 about `--message` | The message is empty or spans more than one line. | Give a single-line `--message` and put detail in `--body`. |
| `commit save` exits 1 about `ADULTING_HOME` | It is not a directory, or not the root of its git repository. | Point `ADULTING_HOME` at the vault root, which must be the repo root. |
| `notes pdf`, `minutes` or `agenda` fails | `pandoc` or `xelatex` is missing. | Install pandoc and a LaTeX engine. |

## Quick reference

| Command | Does |
|---|---|
| `tasks` | Ingests ACTION lines into TASK anchors in place. |
| `tasks add` | Buffer-appends a structured ACTION. |
| `tasks done` | Marks a task complete and stamps `end:`. |
| `tasks set-description` | Rewrites a task body. |
| `tasks set-assignee` | Rewrites the assignee. |
| `tasks set-due` | Sets a due date. |
| `tasks set-scheduled` | Sets a scheduled date. |
| `tasks set-priority` | Sets priority H, M or L. |
| `tasks add-depends` | Adds a dependency. |
| `tasks rm-depends` | Removes a dependency. |
| `tasks list` | Lists pending tasks. |
| `tasks next` | Top 5 pending tasks. |
| `tasks show` | Detail on one task. |
| `notes new` | Creates a note. Interactive. |
| `notes copy` | Copies a note to a new timestamp. Interactive. |
| `notes strip` | Copies a note without its body. Interactive. |
| `notes edit` | Opens a note in the default editor. Interactive. |
| `notes nano` | Opens a note in nano. Interactive. |
| `notes last` | Opens the most recent note. |
| `notes delete` | Deletes a note permanently. Interactive. |
| `notes cat` | Prints a note to stdout. |
| `notes pdf` | Renders a note to PDF and markdown. |
| `notes minutes` | Renders meeting minutes. |
| `notes agenda` | Renders a meeting agenda. |
| `threads list` | Lists threads. |
| `threads show` | Shows one thread. |
| `threads new` | Creates a thread. |
| `threads delete` | Deletes a thread permanently. |
| `people list` | Lists people. |
| `people show` | Shows one person. |
| `people new` | Creates a person. |
| `people delete` | Deletes a person permanently. |
| `hours log` | Appends a time entry. |
| `hours list` | Lists time entries. |
| `hours report` | Totals hours by thread and currency. |
| `hours show` | Shows one time entry. |
| `hours edit` | Changes a field on a time entry. |
| `hours rm` | Deletes a time entry. |
| `payments log` | Records a receipt. |
| `payments list` | Lists payments. |
| `payments statement` | Billed versus received, optionally as PDF. |
| `payments show` | Shows one payment. |
| `payments edit` | Changes a field on a payment. |
| `payments rm` | Deletes a payment. |
| `buffer add` | Appends a raw UNKNOWN capture. |
| `buffer suggest` | Proposes a structured entry for raw text. |
| `buffer add-text` | Appends a TEXT entry. |
| `buffer add-ref` | Appends a REF entry. |
| `buffer add-action` | Appends an ACTION entry. |
| `buffer list` | Shows the buffer with line numbers. |
| `buffer rm` | Removes one buffer line. |
| `buffer tend` | Regroups and validates the buffer. |
| `buffer flush` | Writes the buffer to logs and clears it. |
| `lint` | Validates vault files against the schemas. |
| `commit review` | Shows uncommitted vault changes. |
| `commit save` | Stages and commits the vault. |
