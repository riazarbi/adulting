# adulting — Operators Manual

## Before you start

All data lives in one vault directory. The default is `~/vault/`. Set `ADULTING_HOME` to point the tools at a different directory.

The vault holds `notes/`, `threads/`, `people/`, `logs/`, `hours/`, `payments/`, `buffer.md`, and the hidden `.adulting/` for config.

External programs you need:

| Program | Needed by |
|---|---|
| `bash`, `python3`, `awk`, `sed`, `grep` | everything |
| `pandoc` and `xelatex` | `notes pdf`, `notes minutes`, `notes agenda` |
| `open` (macOS) or `xdg-open` (Linux) | opening notes in Obsidian |

Everything is plain text markdown on disk. You can read it, `grep` it, diff it and back it up yourself. No database, no import step.

## How the pieces fit

| Object | What it is | Where it lives |
|---|---|---|
| Note | A persisted record: meeting, correspondence, report, log, research, recipe. | `notes/` |
| Log file | Per-thread, per-day activity, written by flushing the buffer. | `logs/<Kind>/<Name>/<YYYY-MM-DD>.md` |
| Thread | An organising lens: project, process, or topic. | `threads/{Projects,Processes,Topics}/` |
| Person | A contact you track. | `people/` |
| Time entry | One session of work on a thread, billable or not. | `hours/{Projects,Processes,Topics}/<Thread>.md` |
| Payment | Money received against a thread. | `payments/{Projects,Processes,Topics}/<Thread>.md` |
| Action / task | An `ACTION:` line in a note or log, rewritten in place to a `TASK:` anchor. | inside the note or log file |
| Buffer entry | A staged capture, not yet filed. | `buffer.md` |

Relationships that matter:

- A note names one or more threads in its `threads` frontmatter list. Each must resolve to a thread file.
- A note may name people; wikilink entries must resolve to `people/<name>.md`.
- A task anchor lives in the note or log that is its only store. There is no task backend.
- A task's assignee must resolve to `people/<name>.md`.
- A task may depend on other task uuids. The dependency graph must be acyclic.
- Hours files and payments files are keyed by thread, one file per thread, mirroring the `threads/` layout.
- A thread's `currency` and `rate` are the defaults `hours` uses when logging against it.
- Buffer entries carry a thread wikilink; flushing writes them into `logs/`.

## Command reference

### `tasks`

Turns `ACTION:` lines in notes and logs into anchored `TASK:` lines, and edits those anchors.

**When to use it**

- You wrote `ACTION:` lines in a meeting note and want them tracked.
- You finished a task and need to mark it done.
- You want to see what to work on next.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| (none) | Walk `notes/` and `logs/`, validate every `ACTION:` line, rewrite it in place as a `TASK:` anchor. | `tasks` |
| `add` | Buffer-append a structured ACTION. | `tasks add Projects/SGB "(Riaz Arbi) Draft the scope note"` |
| `done` | Flip the source `TASK:` to `DONE:` and stamp `end:`. | `tasks done abcd1234` |
| `set-description` | Rewrite the task body. | `tasks set-description abcd1234 "Draft and circulate the scope note"` |
| `set-assignee` | Rewrite the `(Assignee)` prefix. | `tasks set-assignee abcd1234 "Riaz Arbi"` |
| `set-due` | Set the due date. | `tasks set-due abcd1234 2026-06-30` |
| `set-scheduled` | Set the scheduled date. | `tasks set-scheduled abcd1234 2026-06-24` |
| `set-priority` | Set priority; writes `[#X]` in the visible portion. | `tasks set-priority abcd1234 H` |
| `add-depends` | Add a dependency. | `tasks add-depends abcd1234 ef567890` |
| `rm-depends` | Remove a dependency. | `tasks rm-depends abcd1234 ef567890` |
| `list` | List pending tasks. | `tasks list --priority H` |
| `next` | Top 5 pending tasks by priority, due, entry. | `tasks next` |
| `show` | Detail view of one anchor. | `tasks show abcd1234` |

**Options**

| Option | Effect |
|---|---|
| `--dry-run` | Default invocation only. Show what would be ingested; write nothing. |
| `--quiet` | Default invocation only. Suppress per-action output. |
| `add --due <YYYY-MM-DD>` | Due date applied on ingest. |
| `add --scheduled <YYYY-MM-DD>` | Scheduled date. |
| `add --priority H\|M\|L` | Priority. |
| `add --depends <uuid8>` | 8-char uuid prefix; repeatable. |
| `list --priority H\|M\|L` | Filter to one priority. |
| `list --thread <Kind/Name>` | Filter to tasks whose source note carries this thread. |
| `list --assignee <person>` | Filter to one assignee. |
| `list --overdue` | Only tasks due before today. |

**Notes**

- The bare `tasks` invocation rewrites source note and log files in place. Use `--dry-run` first if you are unsure.
- Do not write `TASK:` lines by hand. `tasks` owns them.
- Exit code `1`: no task matches the uuid prefix, the prefix is ambiguous, the description is empty, the assignee does not resolve to `people/<name>.md`, or a task would depend on itself.

### `notes`

Creates, edits and renders notes.

**When to use it**

- You are about to sit in a meeting and need a note to type into.
- You want a PDF or minutes of a note you already wrote.
- You want to reopen the note you just made.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Create a new note and open it. Default when no subcommand is given. Interactive. | `notes new` |
| `copy` | Pick a note, copy its contents to a new timestamped note. Interactive. | `notes copy` |
| `strip` | Pick a note, copy it without the body, for use as a template. Interactive. | `notes strip` |
| `edit` | Pick a note, open it in the default editor. Interactive. | `notes edit SGB` |
| `nano` | Pick a note, open it in nano. Interactive. | `notes nano` |
| `last` | Open the most recently created note. Non-interactive. | `notes last` |
| `delete` | Pick a note and permanently delete it. Interactive. | `notes delete` |
| `cat` | Pick a note and print it to stdout. Interactive. | `notes cat` |
| `pdf` | Pick a note, render PDF and markdown with an ACTION/TASK summary. Interactive. | `notes pdf` |
| `minutes` | Pick a note, render minutes: TOC plus AGREED/RESOLVED/ACTION summary. Interactive. | `notes minutes` |
| `agenda` | Pick a note, render a meeting agenda. Interactive. | `notes agenda` |

**Options**

| Option | Effect |
|---|---|
| `[filter]` | Second positional argument. Case-insensitive substring filter on the picker list. |

**Notes**

- Every subcommand except `last` opens an interactive picker and reads a selection from stdin. An agent must never call them; only `notes last` is usable without a TTY.
- `notes delete` permanently removes the file.
- Keywords you type in a note body: `ACTION:` (ingested by `tasks`), `AGREED:`, `RESOLVED:`, `!:` (surfaced in `notes pdf`). Do not write `TASK:` by hand.
- Rendered output goes to `$EXPORT_DIR`, default `~/Downloads`.

### `threads`

Manages thread files.

**When to use it**

- You are starting a new project and need something for notes and hours to attach to.
- You want to find the exact thread label to pass to another tool.
- You need to set a billing rate and currency for a client.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | List thread files, open ones by default. | `threads list SGB` |
| `show` | Show one thread file. | `threads show Projects/SGB` |
| `new` | Create a thread file. | `threads new --name SGB --kind project --category professional` |
| `delete` | Permanently delete a thread file. | `threads delete Projects/SGB -y` |

**Options**

| Option | Effect |
|---|---|
| `list --all` | Include paused and closed threads. |
| `list --json` | JSON output. |
| `show --json` | JSON output. |
| `new --name <name>` | Thread name; skips the prompt. |
| `new --kind project\|process\|topic` | Kind; skips the prompt. |
| `new --category professional\|personal\|voluntary` | Category; skips the prompt. |
| `new --currency <ISO>` | Default currency for `hours`. Three-letter ISO code. |
| `new --rate <n>` | Default hourly rate for `hours`. Needs `--currency`. |
| `delete -y` | Skip the confirmation. |

**Notes**

- `threads new` prompts interactively for any field you do not pass as a flag. Pass `--name`, `--kind` and `--category` to run it without a TTY.
- `threads delete` permanently removes the file. Without `-y` it asks for confirmation.

### `people`

Manages person files.

**When to use it**

- You want to assign a task to someone and they have no file yet.
- You need the exact spelling of a name for `tasks set-assignee`.
- You are checking who you track in a category.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | List person files, open ones by default. | `people list Arbi` |
| `show` | Show one person file. | `people show "Riaz Arbi"` |
| `new` | Create a person file. | `people new --name "Riaz Arbi" --category professional` |
| `delete` | Permanently delete a person file. | `people delete "Riaz Arbi" -y` |

**Options**

| Option | Effect |
|---|---|
| `list --all` | Include closed people. |
| `list --json` | JSON output. |
| `show --json` | JSON output. |
| `new --name <full name>` | Full name; skips the prompt. |
| `new --category professional\|personal\|voluntary` | Category; skips the prompt. |
| `delete -y` | Skip the confirmation. |

**Notes**

- `people new` prompts for any field you do not pass. Pass `--name` and `--category` to run it without a TTY.
- A person is a link target only. A person can never be the value of a note's thread.

### `hours`

Records billable and unbillable time against threads.

**When to use it**

- You just finished a chunk of client work.
- You need a month's totals before invoicing.
- You logged the wrong duration and need to correct it.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Append a time entry. | `hours log Projects/SGB Drafted the scope note -m 90` |
| `list` | List entries. | `hours list Projects/SGB --since 2026-06-01 --until 2026-06-30` |
| `report` | Totals by thread and currency. | `hours report --thread Projects/SGB --since 2026-06-01` |
| `show` | Show one entry. | `hours show a1b2c3d4` |
| `edit` | Change one field of an entry. | `hours edit a1b2c3d4 -m 120` |
| `rm` | Delete an entry. | `hours rm a1b2c3d4 -y` |

**Options**

| Option | Effect |
|---|---|
| `log -m <minutes>` | Duration. Default 60. |
| `log -r <rate>` | Hourly rate. `0` means unbillable. |
| `log -c <ISO>` | Currency. Defaults to the thread's. |
| `log -d <YYYY-MM-DD>` | Date. Default today. |
| `log -t <HH:MM>` | Time. Default now. |
| `log --all` | Interactive mode only: list paused and closed threads too. |
| `list --since` / `--until` | Inclusive date bounds. |
| `list --json`, `report --json`, `show --json` | JSON output. |
| `report --thread`, `--since`, `--until` | Scope the totals. |
| `edit --description <text>`, `-m`, `-r`, `-c`, `-d`, `-t` | Change that field on the entry. |
| `rm -y` | Skip the confirmation. |

**Notes**

- `hours log` with no thread argument is interactive. Always pass a thread when driving it from a script.
- `hours log` requires a currency and refuses to write without one. Set `--currency` on the thread or pass `-c`.
- Rate and currency are stored on each entry at write time. Changing the thread's defaults never re-prices logged work.
- `rate: 0` is a normal value. The hours still count; the money is zero.
- `hours rm` deletes the entry.

### `payments`

Records money received against threads and produces statements.

**When to use it**

- A client's transfer has landed.
- You want to know what is billed but unpaid on a thread.
- You need a statement of account as a PDF.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Record a receipt. | `payments log Projects/SGB 15000 -a "Business current" -d 2026-06-15` |
| `list` | List payments. | `payments list Projects/SGB --since 2026-01-01` |
| `statement` | Billed versus received, by thread and currency. | `payments statement --thread Projects/SGB` |
| `show` | Show one payment. | `payments show 9f8e7d6c` |
| `edit` | Change one field of a payment. | `payments edit 9f8e7d6c --amount 15500` |
| `rm` | Delete a payment. | `payments rm 9f8e7d6c -y` |

**Options**

| Option | Effect |
|---|---|
| `log -c <ISO>` | Currency. Defaults to the thread's. |
| `log -d <YYYY-MM-DD>` | Date received. Default today. |
| `log -t <HH:MM>` | Time. Default now. |
| `log -a <account>` | Which account the money landed in. |
| `log -n <note>` | Free-text note. |
| `log --all` | Interactive mode only: list paused and closed threads too. |
| `list --since` / `--until` | Date bounds. |
| `statement --thread`, `--since`, `--until` | Scope the statement. |
| `statement --as-of <YYYY-MM-DD>` | Statement date; drives aging. Default today. |
| `statement --pdf <path>` | Render a PDF to that path. Requires `--thread`. |
| `list --json`, `statement --json`, `show --json` | JSON output. |
| `edit --amount`, `-c`, `-d`, `-t`, `-a`, `-n` | Change that field on the payment. |
| `rm -y` | Skip the confirmation. |

**Notes**

- `payments log` with no thread argument is interactive. Pass a thread and amount when scripting.
- Amounts must be positive. A refund is not a negative payment.
- `statement --pdf` needs `client_name` in the thread's frontmatter to render.
- `payments rm` deletes the record.

### `buffer`

The quick-capture inbox at `buffer.md`, and the commands that validate and file it.

**When to use it**

- You have a thought mid-call and no time to pick a thread.
- You want to capture an action against a thread without opening a note.
- End of day: you want everything captured filed into `logs/`.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `add` | Append an UNKNOWN entry: raw capture, no thread. | `buffer add "call the accountant about VAT"` |
| `suggest` | Propose a structured `add-*` for raw text; prompt to accept. | `buffer suggest "email SGB the scope note" -y` |
| `add-text` | Append a TEXT entry. | `buffer add-text Projects/SGB "Client prefers a fixed fee"` |
| `add-ref` | Append a REF entry. | `buffer add-ref Projects/SGB notes/2026-06-15-14-30-00 "Kickoff note"` |
| `add-action` | Append an ACTION entry. Same as `tasks add`. | `buffer add-action Projects/SGB "(Riaz Arbi) Send the invoice" --due 2026-06-30` |
| `list` | Show the buffer with line numbers. | `buffer list SGB` |
| `rm` | Remove one line by line number. | `buffer rm 3` |
| `tend` | Regroup by thread and date, then validate. Idempotent. | `buffer tend` |
| `flush` | Tend, write to `logs/`, clear the buffer. | `buffer flush` |

**Options**

| Option | Effect |
|---|---|
| `--quiet` | Global. Suppress info output. |
| `suggest -y` | Auto-accept the suggestion without prompting. |
| `add-action --due <YYYY-MM-DD>` | Due date applied on flush and ingest. |
| `add-action --scheduled <YYYY-MM-DD>` | Scheduled date. |
| `add-action --priority H\|M\|L` | Priority. |
| `add-action --depends <uuid8>` | 8-char uuid prefix; repeatable. |

**Notes**

- `buffer suggest` prompts unless you pass `-y`. Pass `-y` when running without a TTY.
- UNKNOWN entries are deliberately invalid. `tend` reports them as violations and they block `flush` until you remove them and re-add via the matching `add-*` command.
- `buffer flush` clears `buffer.md` after writing to `logs/`.
- Do not edit `buffer.md` by hand. Use `add-*`, `rm` and `tend`.
- Exit code `1`: empty text or description, `--due` or `--scheduled` not `YYYY-MM-DD`, or `--depends` not 8 hex characters.

### `lint`

Validates vault files against the schemas.

**When to use it**

- Before committing, to check nothing is malformed.
- After hand-editing frontmatter.
- To check one file you just changed.

**Usage**

`lint [<path> ...]`

| Argument | Meaning |
|---|---|
| `paths` | Files to validate. Omit to walk the whole vault. |

**Options**

| Option | Effect |
|---|---|
| `--schemas <dir>` | Use a different schemas directory. |
| `--quiet` | Suppress per-violation output; exit code only. |

**Notes**

- Read-only. It never changes files.
- Errors print as `<path>:<line>: <message>`.
- Exit `0` clean, `1` if there are violations, `2` on a usage failure.

### `commit`

Reviews uncommitted vault changes, then stages and commits them.

**When to use it**

- End of a work session, to see what you changed.
- After a flush or ingest, to record it in git.
- To check what would be committed without committing.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `review` | Show everything changed since the last commit. Read-only. | `commit review` |
| `save` | Stage every change in the vault and commit it. | `commit save --message "File Tuesday's captures"` |

**Options**

| Option | Effect |
|---|---|
| `review --max-file-lines <n>` | Max diff lines shown per file. Default 150. |
| `review --max-lines <n>` | Max lines of output overall. Default 3000. |
| `save --message <text>` | Required. Commit subject, single line. |
| `save --body <text>` | Commit body. May span lines. |
| `save --dry-run` | Report what would be staged and committed; change nothing. |

**Notes**

- `save` can only ever add a commit. It never amends, rebases, resets, checks out or pushes. The only mutating git calls are `git add` and `git commit`.
- Run `review` first, then write `--message` from what you saw.
- Exit code `1`: `--message` empty or multi-line, `ADULTING_HOME` is not a directory, `ADULTING_HOME` is not the root of its git repository, or the git call failed.

## Everyday procedures

### 1. Set up a new billable project

1. `threads new --name SGB --kind project --category professional --currency ZAR --rate 2500` — creates `threads/Projects/SGB.md` with billing defaults.
2. `threads show Projects/SGB` — confirm the file and the exact thread label.
3. `people new --name "Jane Client" --category professional` — create the counterparty so you can link and assign to them.
4. `lint threads/Projects/SGB.md` — confirm the frontmatter validates.
5. `commit save --message "Open Projects/SGB"` — record the new thread in git.

### 2. Capture a meeting and turn its actions into tracked tasks

1. `notes new` — interactive; creates the note and opens it. Do not call this without a TTY.
2. In the body, write `ACTION: (Jane Client) Confirm the fee` lines, plus `AGREED:` and `RESOLVED:` where relevant.
3. `tasks --dry-run` — see which ACTION lines would be ingested and whether they validate.
4. `tasks` — rewrites each ACTION line in place as a `TASK:` anchor with a fresh uuid.
5. `tasks list --thread Projects/SGB` — confirm the new tasks are there.
6. `notes minutes` — interactive; renders TOC plus AGREED/RESOLVED/ACTION summary.

### 3. Quick-capture through the day, then file it

1. `buffer add "chase the accountant"` — no thread needed; captures verbatim.
2. `buffer add-action Projects/SGB "(Riaz Arbi) Send the scope note" --due 2026-06-30 --priority H` — structured capture when you know the thread.
3. `buffer list` — review with line numbers.
4. `buffer rm 1` — remove the UNKNOWN line; it will block the flush otherwise.
5. `buffer add-action Processes/Admin "Chase the accountant"` — re-add it properly.
6. `buffer tend` — regroup by thread and date, and validate.
7. `buffer flush` — writes to `logs/` and clears the buffer.
8. `tasks` — ingest the new ACTION lines in `logs/` into TASK anchors.

### 4. Work the task list

1. `tasks next` — the top 5 pending tasks.
2. `tasks list --overdue` — everything past its due date.
3. `tasks show abcd1234` — full detail on one anchor.
4. `tasks set-priority abcd1234 H` — raise it.
5. `tasks set-scheduled abcd1234 2026-06-24` — decide when you will do it.
6. `tasks done abcd1234` — flips the source line to `DONE:` and stamps `end:`.

### 5. Log a session of work

1. `threads list` — find the exact thread label.
2. `hours log Projects/SGB Reviewed the vendor contract -m 90` — appends a 90-minute entry at the thread's rate and currency.
3. `hours list Projects/SGB` — confirm the entry and read its id.
4. `hours edit a1b2c3d4 -m 120` — correct the duration if you mis-estimated.
5. `commit save --message "Log SGB contract review"` — record it.

### 6. Bill a client for a month's work

1. `hours report --thread Projects/SGB --since 2026-06-01 --until 2026-06-30` — totals by currency for the month.
2. `hours list Projects/SGB --since 2026-06-01 --until 2026-06-30` — the entry descriptions, which are your invoice line items.
3. `hours edit a1b2c3d4 --description "Vendor contract review and markup"` — fix any line item that reads badly.
4. `threads show Projects/SGB` — confirm `client_name` and the other `client_*` fields are set.
5. `payments statement --thread Projects/SGB --as-of 2026-06-30 --pdf ~/Downloads/sgb-statement.pdf` — render the statement of account.

### 7. Record a payment

1. `payments log Projects/SGB 15000 -d 2026-07-05 -a "Business current" -n "June invoice"` — records the receipt.
2. `payments list Projects/SGB` — confirm it and read its id.
3. `payments statement --thread Projects/SGB` — billed versus received, with aging.
4. `commit save --message "Record SGB June payment"` — record it.

### 8. Check the vault and commit it

1. `lint` — walk the whole vault and report violations as `<path>:<line>: <message>`.
2. Fix each violation, using the owning tool rather than a hand edit.
3. `lint --quiet` — re-run for the exit code alone; `0` means clean.
4. `commit review` — read everything that changed since the last commit.
5. `commit save --dry-run --message "..."` — check what would be staged.
6. `commit save --message "File the day's work" --body "Flushed buffer, ingested actions, logged SGB hours."` — stage everything and commit.

## Data formats

`lint` enforces every schema below.

### `hours_file`

Billable time for one thread, one file per thread, at `hours/{Projects,Processes,Topics}/<Thread>.md`. The body holds exactly one ` ```simple-time-tracker ` fenced block containing JSON `{"entries": [...]}`.

Frontmatter fields:

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to the thread; must resolve to an existing thread file. |
| `currency` | yes | Three uppercase letters, ISO 4217. |

Entry object fields:

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | The description of what was done. This is the invoice line item. |
| `startTime` | yes | ISO 8601 UTC timestamp with milliseconds. |
| `endTime` | yes | Same form; not earlier than `startTime`. |
| `id` | yes | 8 hex characters, unique across the vault. |
| `rate` | yes | Per-hour charge. `0` means unbillable and is an ordinary value. |
| `currency` | yes | ISO 4217 code, three uppercase letters. |

Duration is derived from `endTime` minus `startTime`; there is no duration field. Rate and currency are stored per entry so changing thread defaults never re-prices history. JSON is pretty-printed at indent 2 for readable diffs.

### `log`

A per-thread per-day record of activity, written by `buffer flush`. Lives at `logs/<Kind>/<Name>/<YYYY-MM-DD>.md`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to `Projects/`, `Processes/` or `Topics/`. |
| `date` | yes | The day, `YYYY-MM-DD`. |
| `type` | yes | Always `Log`. |

Body lines: `REF: [[X]] ...` for a reference, `TEXT: ...` for an observation, `ACTION: ...` for an open action, `TASK: ...` and `DONE: ...` for ingested ones. `tasks` reads `logs/` and `notes/` identically. Sub-day timestamps are not preserved.

### `note_correspondence`

A note recording email, message or letter exchanges. Lives in `notes/`, filename `YYYY-MM-DD-HH-MM-SS.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about. |
| `type` | yes | `Correspondence`. |
| `threads` | yes | List of thread wikilinks; each must resolve. |
| `timestamp` | yes | Matches the filename stem. |
| `people` | no | List; wikilinks must resolve, plain strings are untracked participants. |

Body keywords: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:`, `!:`.

### `note_meeting`

A note recording a meeting. Lives in `notes/`, filename `YYYY-MM-DD-HH-MM-SS.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the meeting was about. |
| `type` | yes | `Meeting`. |
| `threads` | yes | List of thread wikilinks; each must resolve. |
| `timestamp` | yes | Matches the filename stem. |
| `counterparty` | no | The other party. |
| `location` | no | Where it happened. |
| `people` | no | List; wikilinks must resolve, plain strings are untracked attendees. |

Body keywords: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:`, `!:`.

### `note_simple`

A note of a bare-shape type, with no type-specific fields. Lives in `notes/`, filename `YYYY-MM-DD-HH-MM-SS.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about. |
| `type` | yes | One of `Workshop`, `Report`, `Log`, `Research`, `Recipe`. |
| `threads` | yes | List of thread wikilinks; each must resolve. |
| `timestamp` | yes | Matches the filename stem. |
| `people` | no | List; wikilinks or plain strings. |

Body keywords: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:`, `!:`.

### `payments_file`

Money received against one thread, one file per thread, at `payments/{Projects,Processes,Topics}/<Thread>.md`. The body holds exactly one ` ```adulting-payments ` fenced block containing JSON `{"payments": [...]}`.

Frontmatter fields:

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to the thread; must resolve. |
| `currency` | yes | Three uppercase letters, ISO 4217. |

Payment object fields:

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | 8 hex characters, unique across the vault. Shares one namespace with `hours` entry ids. |
| `received` | yes | ISO 8601 UTC timestamp; the date the money landed. |
| `amount` | yes | Must be greater than zero. Computed with decimals, never floats. |
| `currency` | yes | ISO 4217 code. |
| `account` | no | Which account the money landed in. |
| `note` | no | Free text. |

### `person`

A file for someone you track. Lives in `people/`. People are link targets for `note.people` and task assignees. They can never be a note's thread.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | `YYYY-MM-DD`. |
| `ended` | no | `YYYY-MM-DD`. Required when `status` is `closed`. |
| `cadences` | no | List of `{key, frequency, description}`. |

The body is free-form.

### `task_anchor`

A single `TASK:` or `DONE:` line in a note or log file. This is the vault's source of truth for task state; there is no backend. Written by `tasks` ingest and mutated only by `tasks` subcommands.

| Field | Required | Meaning |
|---|---|---|
| `kind` | yes | `TASK` or `DONE`. |
| `priority` | no | `H`, `M` or `L`. Lives in the visible `[#X]` token, never in the attrs comment. |
| `assignee` | no | Must resolve to `people/<name>.md`. |
| `body` | yes | The description; at least one character. |
| `uuid` | yes | 8 hex characters, unique across the vault. |
| `entry` | yes | The ingest date. |
| `end` | no | The completion date. Required when `kind` is `DONE`; must not be earlier than `entry`. |
| `due` | no | Due date. |
| `scheduled` | no | Scheduled date. |
| `depends` | no | Comma-separated 8-char uuids. Each must resolve to another anchor, and the graph must be acyclic. |

Attrs order in the comment is fixed: `entry`, `end`, `due`, `scheduled`, `depends`. Obsidian hides the comment, so the reader sees only the visible portion.

### `thread`

A markdown file holding a chronological log of a project, process, or relationship. Lives in `threads/`.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `kind` | yes | `project`, `process` or `topic`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | `YYYY-MM-DD`. |
| `ended` | no | `YYYY-MM-DD`. Required when `status` is `closed`. |
| `cadences` | no | List of objects with `key`, `frequency` in days, and `description`. |
| `currency` | no | Default currency for `hours`; three uppercase letters. |
| `rate` | no | Default hourly rate for `hours`. Falls back to `.adulting/config.yaml` `time.rate`, then 2500. |
| `client_name` | no | Party billed on a statement. Required to render `payments statement --pdf`. |
| `client_address` | no | Pipe-separated address, one line. |
| `client_vat` | no | Client VAT number. |
| `client_email` | no | Client email. |

The body holds dated bullets. A `#<cadence_key>` tag inside an entry satisfies that cadence. Supplier and banking details are vault-wide and live in `.adulting/config.yaml` under `billing:`. The payment reference on a statement is the thread name without its `Kind/` prefix.

### `thread_entry`

A single dated bullet at the top level of a thread file's body. Indented sub-bullets are continuation detail and are not separately validated.

| Field | Required | Meaning |
|---|---|---|
| `date` | yes | `YYYY-MM-DD` at the start of the bullet. |
| `text` | yes | The entry text; at least one character. |

Out-of-order dates are tolerated.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `tasks` exits 1: "no task found with uuid prefix" | The prefix does not match any anchor in the vault. | Run `tasks list` or `tasks show` to get the correct 8-char uuid. |
| `tasks` exits 1: "uuid prefix is ambiguous" | The prefix matches more than one anchor. | Use more characters of the uuid. |
| `tasks` exits 1: person does not resolve | The assignee has no `people/<name>.md`. | Run `people new --name "<full name>" --category <category>`, then retry. |
| `tasks add-depends` exits 1: "a task cannot depend on itself" | You passed the same uuid twice. | Pass the uuid of a different task. |
| `buffer flush` refuses to run | UNKNOWN entries in the buffer are reported as violations by `tend`. | `buffer list`, `buffer rm <line>`, then re-add via `buffer add-text`, `add-ref` or `add-action`. |
| `buffer add-action` exits 1: "--due must be YYYY-MM-DD" | The date is not in ISO form. | Pass the date as `YYYY-MM-DD`. |
| `buffer add-action` exits 1: "--depends must be 8 hex chars" | The dependency is not an 8-character hex uuid. | Take the uuid from `tasks show` or `tasks list`. |
| `hours log` refuses to write | No currency: neither `-c` nor a `currency` on the thread. | Pass `-c <ISO>`, or set it with `threads new --currency`. |
| `payments statement --pdf` will not render | `--pdf` requires `--thread`, and the thread needs `client_name`. | Add `--thread`, and set `client_name` in the thread frontmatter. |
| `lint` exits 1 with `<path>:<line>:` lines | A file violates its schema. | Fix the named line; use the owning tool rather than a hand edit. |
| `commit save` exits 1: "--message must be a single line" | The subject contains a newline. | Put the subject in `--message` and the detail in `--body`. |
| `commit` exits 1: ADULTING_HOME is not the root of its git repository | `ADULTING_HOME` points below or outside the repo root. | Point `ADULTING_HOME` at the vault directory that is the git root. |
| A `notes` command hangs with no output | Every subcommand except `last` reads a picker selection from stdin. | Run it in a terminal, or use `notes last`. |

## Quick reference

| Command | Does |
|---|---|
| `tasks` | Ingest ACTION lines in notes and logs into TASK anchors |
| `tasks add` | Buffer-append a structured ACTION |
| `tasks done` | Mark a task complete and stamp the end date |
| `tasks set-description` | Rewrite a task body |
| `tasks set-assignee` | Rewrite a task's assignee |
| `tasks set-due` | Set a task's due date |
| `tasks set-scheduled` | Set a task's scheduled date |
| `tasks set-priority` | Set a task's priority |
| `tasks add-depends` | Add a task dependency |
| `tasks rm-depends` | Remove a task dependency |
| `tasks list` | List pending tasks |
| `tasks next` | Top 5 pending tasks |
| `tasks show` | Detail view of one task |
| `notes new` | Create and open a note (interactive) |
| `notes copy` | Copy a note to a new timestamp (interactive) |
| `notes strip` | Copy a note without its body (interactive) |
| `notes edit` | Open a note in the default editor (interactive) |
| `notes nano` | Open a note in nano (interactive) |
| `notes last` | Open the most recent note |
| `notes delete` | Permanently delete a note (interactive) |
| `notes cat` | Print a note to stdout (interactive) |
| `notes pdf` | Render a note to PDF and markdown (interactive) |
| `notes minutes` | Render meeting minutes (interactive) |
| `notes agenda` | Render a meeting agenda (interactive) |
| `threads list` | List thread files |
| `threads show` | Show one thread file |
| `threads new` | Create a thread file |
| `threads delete` | Permanently delete a thread file |
| `people list` | List person files |
| `people show` | Show one person file |
| `people new` | Create a person file |
| `people delete` | Permanently delete a person file |
| `hours log` | Append a time entry |
| `hours list` | List time entries |
| `hours report` | Totals by thread and currency |
| `hours show` | Show one time entry |
| `hours edit` | Change a field of a time entry |
| `hours rm` | Delete a time entry |
| `payments log` | Record money received |
| `payments list` | List payments |
| `payments statement` | Billed versus received, with aging |
| `payments show` | Show one payment |
| `payments edit` | Change a field of a payment |
| `payments rm` | Delete a payment |
| `buffer add` | Append a raw UNKNOWN capture |
| `buffer suggest` | Propose a structured capture for raw text |
| `buffer add-text` | Append a TEXT entry |
| `buffer add-ref` | Append a REF entry |
| `buffer add-action` | Append an ACTION entry |
| `buffer list` | Show the buffer with line numbers |
| `buffer rm` | Remove one buffer line |
| `buffer tend` | Regroup and validate the buffer |
| `buffer flush` | Write the buffer to logs and clear it |
| `lint` | Validate vault files against the schemas |
| `commit review` | Show everything changed since the last commit |
| `commit save` | Stage all vault changes and commit them |
