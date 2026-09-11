# adulting — Operators Manual

## Before you start

Everything lives under one directory. The default is `~/vault/`. Set `ADULTING_HOME` to point the tools at a different vault; every path below is relative to it.

The vault holds `notes/`, `threads/`, `people/`, `logs/`, `hours/`, `payments/`, `buffer.md`, and a hidden `.adulting/` for config.

External programs you need:

| Program | Needed by |
|---|---|
| `bash`, `python3`, `awk`, `sed`, `grep` | everything |
| `pandoc` and `xelatex` | `notes pdf`, `notes minutes`, `notes agenda` |
| `open` (macOS) or `xdg-open` (Linux) | launching Obsidian to edit notes |

All state is plain text markdown. You can read it, `grep` it, diff it and back it up without the tools. The tools are a convenience over the files, not a database in front of them.

## How the pieces fit

| Object | What it is | Where it lives |
|---|---|---|
| Note | A persisted record: meeting, correspondence, report, research, recipe, workshop, log. | `notes/` |
| Log | A per-thread per-day file of captured lines, written by `buffer flush`. | `logs/<Kind>/<Name>/<YYYY-MM-DD>.md` |
| Thread | The organising lens: a project, process, or topic. | `threads/{Projects,Processes,Topics}/` |
| Person | A contact you track; a link target, never a thread. | `people/` |
| Time entry | One session of work on a thread, billable or not. | `hours/{Projects,Processes,Topics}/<Thread>.md` |
| Payment | Money received against a thread. | `payments/{Projects,Processes,Topics}/<Thread>.md` |
| Action / task | An `ACTION:` line in a note or log, rewritten in place to a `TASK:` anchor with an 8-char uuid. | inside the note or log that holds it |
| Buffer entry | A staged capture waiting to become a log line. | `buffer.md` |

Relationships that matter:

- A note names one or more threads in its `threads` frontmatter list; each must resolve to a thread file.
- A note may name people; wikilinked people must resolve to `people/<name>.md`.
- A task's assignee must resolve to a person file. A task may depend on other tasks by uuid; the dependency graph must be acyclic.
- Tasks have no separate store. The source note or log line *is* the task.
- Hours and payments files each belong to one thread, and their directory layout mirrors `threads/`.
- A thread's `currency` and `rate` are the defaults `hours` applies. A thread with no currency is not billable.
- Hours entry ids and payment ids share one uuid namespace.

## Command reference

### `tasks`

Turns `ACTION:` lines in notes and logs into anchored `TASK:` lines, and mutates those anchors in place.

**When to use it**

- You wrote `ACTION:` lines in a meeting note and want them tracked.
- You finished something and need the source line flipped to `DONE:`.
- You want to see what to work on next.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| *(none)* | Walk `notes/` and `logs/`, validate every `ACTION:` line, rewrite each to a `TASK:` anchor. | `tasks` |
| `add` | Buffer-append a structured ACTION. | `tasks add Projects/SGB "(Riaz Arbi) Send the scope note" --due 2026-09-30` |
| `done` | Flip the source `TASK:` to `DONE:` and stamp `end:`. | `tasks done abcd1234` |
| `set-description` | Rewrite the task body. | `tasks set-description abcd1234 "Send the revised scope note"` |
| `set-assignee` | Rewrite the `(Assignee)` prefix. | `tasks set-assignee abcd1234 "Riaz Arbi"` |
| `set-due` | Set the due date. | `tasks set-due abcd1234 2026-10-01` |
| `set-scheduled` | Set the scheduled date. | `tasks set-scheduled abcd1234 2026-09-28` |
| `set-priority` | Set priority; writes `[#X]` in the visible portion. | `tasks set-priority abcd1234 H` |
| `add-depends` | Add a dependency. | `tasks add-depends abcd1234 ef567890` |
| `rm-depends` | Remove a dependency. | `tasks rm-depends abcd1234 ef567890` |
| `list` | List pending tasks. | `tasks list --priority H --overdue` |
| `next` | Top 5 pending by priority, due, entry. | `tasks next` |
| `show` | Detail view of one anchor. | `tasks show abcd1234` |

**Options**

| Option | Effect |
|---|---|
| `--dry-run` | Default invocation only. Show what would be ingested; write nothing. |
| `--quiet` | Default invocation only. Suppress per-action output. |
| `add --due <YYYY-MM-DD>` | Due date applied on ingest. |
| `add --scheduled <YYYY-MM-DD>` | Scheduled date. |
| `add --priority <H\|M\|L>` | Priority. |
| `add --depends <uuid8>` | 8-char uuid prefix; repeatable. |
| `list --priority <H\|M\|L>` | Filter to one priority. |
| `list --thread <Kind/Name>` | Filter to tasks whose source note carries this thread. |
| `list --assignee <person>` | Filter to one assignee. |
| `list --overdue` | Only tasks due before today. |

**Notes**

- The bare `tasks` invocation rewrites source notes and logs in place. Use `--dry-run` first if you are unsure.
- Do not hand-write `TASK:` or `DONE:` lines. `tasks` owns them.
- Exit code `1` when: no task matches the uuid prefix; the prefix is ambiguous; the description is empty; the assignee does not resolve to `people/<person>.md`; a task would depend on itself.
- `tasks add` does not create a task directly. It appends an ACTION to the buffer; the task appears after `buffer flush` and the next `tasks` run.

### `notes`

Create, edit, render and delete notes.

**When to use it**

- You are about to sit in a meeting and need a note to type into.
- You want a PDF, minutes or an agenda out of a note you wrote.
- You want to reopen the last note you made.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Create a new note and open it. Default when no subcommand is given. **Interactive.** | `notes new` |
| `copy` | Pick a note, copy its contents to a new timestamp. **Interactive.** | `notes copy` |
| `strip` | Pick a note, copy it and remove the body, for templating. **Interactive.** | `notes strip` |
| `edit` | Pick a note, open it in the default editor. **Interactive.** | `notes edit SGB` |
| `nano` | Pick a note, open it in nano. **Interactive.** | `notes nano` |
| `last` | Open the most recently-created note. Non-interactive. | `notes last` |
| `delete` | Pick a note and permanently delete it. **Interactive.** | `notes delete` |
| `cat` | Pick a note and print it to stdout. **Interactive.** | `notes cat` |
| `pdf` | Pick a note, render PDF + markdown with an ACTION/TASK summary. **Interactive.** | `notes pdf` |
| `minutes` | Pick a note, render minutes: TOC plus AGREED/RESOLVED/ACTION summary. **Interactive.** | `notes minutes` |
| `agenda` | Pick a note, render a meeting agenda. **Interactive.** | `notes agenda` |

**Options**

| Option | Effect |
|---|---|
| `<filter>` | Optional second argument. Case-insensitive substring filter on the picker list. |

**Notes**

- Every subcommand except `last` opens a picker and reads a selection from stdin. An agent with no TTY must call only `notes last`.
- `delete` is permanent.
- Rendered output goes to `$EXPORT_DIR`, default `~/Downloads`.
- Body keywords you can type: `ACTION:` (ingested by `tasks`), `AGREED:`, `RESOLVED:`, `!:` (callout surfaced in the PDF summary). Do not write `TASK:` by hand.

### `search`

Find notes and logs, and summarise thread activity.

**When to use it**

- You need the path of a note but remember only a phrase from it.
- You want to know what happened on a thread last month.
- You are about to write a status update and need the whole picture of one thread.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `notes` | Find notes by thread, type, date or text. | `search notes --thread Projects/SGB --type Meeting --since 2026-08-01` |
| `logs` | Find daily logs by thread, date or text. | `search logs --thread Projects/SGB --text invoice` |
| `activity` | Rank threads by what happened in a window. | `search activity --since 2026-08-01 --until 2026-08-31` |
| `overview` | The whole picture of one thread. | `search overview Projects/SGB` |

**Options**

Global to all four subcommands: `--since <YYYY-MM-DD>`, `--until <YYYY-MM-DD>`, `--json`.

| Option | Effect |
|---|---|
| `--thread <T>` | Thread name, `Kind/Name`, or wikilink. On `activity`, limits to one thread. |
| `--type <T>` | `notes` only. Note type, case-insensitive. |
| `--text <S>` | Case-insensitive literal. Over topic and body for notes; over entry lines for logs. |
| `--limit <N>` | Max results. Default 20 on `notes` and `logs`, 0 for all. Default 5 on `overview`. |

**Notes**

- `search` returns pointers, never bodies. Open the path yourself to read the document.
- Paths are emitted absolute, resolved against `ADULTING_HOME`.
- Dates filter on the event date from frontmatter `timestamp`. The filename date is used only when the frontmatter date is missing or malformed.
- Exit code `1` when a `--thread` or `thread` argument cannot be resolved.

### `threads`

Create, list, show and delete thread files.

**When to use it**

- A new client project starts and needs a home.
- You need a thread's billing defaults or client details.
- You want the list of everything currently open.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | List thread files, open by default. | `threads list SGB --all` |
| `show` | Show a single thread file. | `threads show Projects/SGB --json` |
| `new` | Create a thread file. Prompts for anything not supplied. | `threads new --name SGB --kind project --category professional --currency ZAR --rate 2500` |
| `delete` | Permanently delete a thread file. | `threads delete Projects/SGB -y` |

**Options**

| Option | Effect |
|---|---|
| `list --all` | Include paused and closed threads. |
| `list --json` / `show --json` | JSON output. |
| `new --name <NAME>` | Thread name; skips the prompt. |
| `new --kind <project\|process\|topic>` | Skips the prompt. |
| `new --category <professional\|personal\|voluntary>` | Skips the prompt. |
| `new --currency <ISO>` | Default currency for `hours`. Three-letter ISO code. |
| `new --rate <N>` | Default hourly rate for `hours`. Needs `--currency`. |
| `delete -y` | Skip the confirmation. |

**Notes**

- `threads new` prompts for any field you do not pass. To run it without a TTY, pass `--name`, `--kind` and `--category`.
- `threads delete` is permanent. Without `-y` it asks for confirmation, which needs a TTY.
- A thread with no `currency` is not billable. `hours` writes its entries with rate 0 and no currency.

### `people`

Create, list, show and delete person files.

**When to use it**

- You need a new assignee before `tasks` will accept one.
- You want a contact's file to check history before a call.
- Someone has left and you want them out of the open list.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | List person files, open by default. | `people list Arbi --all` |
| `show` | Show a single person file. | `people show "Riaz Arbi" --json` |
| `new` | Create a person file. Prompts for anything not supplied. | `people new --name "Riaz Arbi" --category professional` |
| `delete` | Permanently delete a person file. | `people delete "Riaz Arbi" -y` |

**Options**

| Option | Effect |
|---|---|
| `list --all` | Include closed people. |
| `list --json` / `show --json` | JSON output. |
| `new --name <NAME>` | Full name; skips the prompt. |
| `new --category <professional\|personal\|voluntary>` | Skips the prompt. |
| `delete -y` | Skip the confirmation. |

**Notes**

- `people new` prompts for any field you do not pass. Pass `--name` and `--category` to run it without a TTY.
- A person is a link target only. A person can never be the value of a note's thread.

### `hours`

Record and report time worked against threads.

**When to use it**

- You just finished a session of client work.
- You need the month's totals before invoicing.
- You mistyped a duration and need to fix one entry.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Append a time entry. Interactive if you give no thread. | `hours log Projects/SGB Drafted the migration plan -m 90` |
| `list` | List entries. | `hours list Projects/SGB --since 2026-08-01 --until 2026-08-31` |
| `report` | Totals by thread and currency, unbilled time totalled separately. | `hours report --since 2026-08-01 --until 2026-08-31` |
| `show` | Show one entry. | `hours show a1b2c3d4` |
| `edit` | Change one field of an entry. | `hours edit a1b2c3d4 -m 120` |
| `rm` | Delete an entry. | `hours rm a1b2c3d4 -y` |

**Options**

| Option | Effect |
|---|---|
| `log -m <MINUTES>` | Duration. Default 60. |
| `log -r <RATE>` | Hourly rate. `0` means unbillable. |
| `log -c <ISO>` | Currency. Defaults to the thread's. Without either, the entry is recorded as unbilled. |
| `log -d <YYYY-MM-DD>` | Date. Default today. |
| `log -t <HH:MM>` | Start time. Default now. |
| `log --all` | Interactive mode: list paused and closed threads too. |
| `list --since` / `--until` | Inclusive date bounds. |
| `report --thread <T>`, `--since`, `--until` | Scope the report. |
| `edit --description <TEXT>`, `-m`, `-r`, `-c`, `-d`, `-t` | Change that field on the entry. |
| `rm -y` | Skip the confirmation. |
| `--json` | Available on `list`, `report`, `show`. |

**Notes**

- `hours log` with no thread argument prompts interactively. Pass a thread to run it without a TTY.
- Rate and currency are resolved at write time and stored on each entry. Changing a thread's defaults never re-prices logged work.
- Entries on a thread with no currency are written with rate 0 and no currency, totalled under `unbilled` in `report`, and ignored by `payments statement`.
- `hours rm` deletes the entry from the file.

### `payments`

Record money received against threads and reconcile it against time billed.

**When to use it**

- A client transfer lands and you want it recorded.
- You need a statement of account to send out.
- You need to know who still owes you.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Record a receipt. Interactive if you give no thread. | `payments log Projects/SGB 25000 -d 2026-09-05 -a "FNB current"` |
| `list` | List payments. | `payments list Projects/SGB --since 2026-01-01` |
| `statement` | Billed versus received, by thread and currency. | `payments statement --thread Projects/SGB --as-of 2026-09-11` |
| `show` | Show one payment. | `payments show 1a2b3c4d` |
| `edit` | Change one field of a payment. | `payments edit 1a2b3c4d --amount 26000` |
| `rm` | Delete a payment. | `payments rm 1a2b3c4d -y` |

**Options**

| Option | Effect |
|---|---|
| `log -c <ISO>` | Currency. Defaults to the thread's. |
| `log -d <YYYY-MM-DD>` | Date received. Default today. |
| `log -t <HH:MM>` | Time. Default now. |
| `log -a <ACCOUNT>` | Which account it landed in. |
| `log -n <NOTE>` | Free-text note. |
| `log --all` | Interactive mode: list paused and closed threads too. |
| `list --since` / `--until` | Date bounds. |
| `statement --thread <T>`, `--since`, `--until` | Scope the statement. |
| `statement --as-of <YYYY-MM-DD>` | Statement date; drives aging. Default today. |
| `statement --pdf <PATH>` | Render a PDF there. Requires `--thread`. |
| `edit --amount <N>`, `-c`, `-d`, `-t`, `-a`, `-n` | Change that field. |
| `rm -y` | Skip the confirmation. |
| `--json` | Available on `list`, `statement`, `show`. |

**Notes**

- `payments log` with no thread argument prompts interactively. Pass a thread and amount to run it without a TTY.
- Money received must always name a currency. There is no unbilled fallback here.
- Amounts must be positive. There is no negative payment.
- `statement --pdf` renders the party in the thread's `client_*` fields. Only `client_name` is required.

### `buffer`

Capture items into `buffer.md`, validate them, and flush them into daily logs.

**When to use it**

- Something occurs to you mid-task and you have ten seconds to record it.
- You want to check the buffer is clean before flushing.
- End of day: turn the day's captures into log files.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `add` | Append an UNKNOWN entry: raw quick-capture. | `buffer add "chase the SGB invoice"` |
| `suggest` | Propose a structured `add-*` for raw text, then prompt to accept. | `buffer suggest "chase the SGB invoice" -y` |
| `add-text` | Append a TEXT entry. | `buffer add-text Projects/SGB "Client confirmed the scope"` |
| `add-ref` | Append a REF entry. | `buffer add-ref Projects/SGB notes/2026-09-11-14-30-00 "Scope call"` |
| `add-action` | Append an ACTION entry. Also reachable as `tasks add`. | `buffer add-action Projects/SGB "(Riaz Arbi) Chase the invoice" --priority H` |
| `list` | Show the buffer with line numbers. | `buffer list SGB` |
| `rm` | Remove a single line by line number. | `buffer rm 3` |
| `tend` | Regroup by thread and date, then validate. Idempotent. | `buffer tend` |
| `flush` | Tend, write to `logs/`, clear the buffer. | `buffer flush` |

**Options**

| Option | Effect |
|---|---|
| `--quiet` | Global. Suppress info output. |
| `suggest -y` | Auto-accept the suggestion without prompting. |
| `add-action --due <YYYY-MM-DD>` | Due date applied on flush and ingest. |
| `add-action --scheduled <YYYY-MM-DD>` | Scheduled date. |
| `add-action --priority <H\|M\|L>` | Priority. |
| `add-action --depends <uuid8>` | 8-char uuid prefix; repeatable. |

**Notes**

- `buffer suggest` without `-y` prompts for accept or reject, so it needs a TTY. With `-y` it is safe for an agent.
- UNKNOWN entries are intentionally invalid. `tend` reports them as violations and they block `flush` until you remove them and re-add them with the matching `add-*` command.
- `flush` clears `buffer.md`. Run `tend` first if you want to see the state before it changes.
- Do not edit `buffer.md` by hand. Use `tend` to fix things and `add-*` / `rm` for individual entries.
- Exit code `1` when: the text or description is empty; the description after the assignee is empty; `--due` or `--scheduled` is not `YYYY-MM-DD`; `--depends` is not 8 hex characters.

### `lint`

Validate vault files against the schemas.

**When to use it**

- Before committing, to check nothing is malformed.
- After hand-editing frontmatter.
- To check one file you just wrote.

**Usage**

`lint [<path> ...]`

| Argument | Meaning |
|---|---|
| `paths` | Files to validate. With none, walks the whole vault. |

**Options**

| Option | Effect |
|---|---|
| `--schemas <DIR>` | Schemas directory. |
| `--quiet` | Suppress per-violation output; exit code only. |

**Notes**

- Exit `0` when clean, `1` when there are violations, `2` on a usage error.
- Violations print as `<path>:<line>: <message>`.
- `lint` is read-only. It never repairs a file.

### `commit`

Review uncommitted vault changes, then stage and commit them.

**When to use it**

- End of a work session, to see everything that changed.
- After a flush and ingest, to record the day in git.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `review` | Show everything changed since the last commit. Read-only. | `commit review --max-file-lines 80` |
| `save` | Stage every change in the vault and commit it. | `commit save --message "Log SGB session and flush buffer"` |

**Options**

| Option | Effect |
|---|---|
| `review --max-file-lines <N>` | Max diff lines shown per file. Default 150. |
| `review --max-lines <N>` | Max lines of output overall. Default 3000. |
| `save --message <TEXT>` | Required. Commit subject. Single line. |
| `save --body <TEXT>` | Commit body. May span multiple lines. |
| `save --dry-run` | Report what would be staged and committed; change nothing. |

**Notes**

- `save` can only add a commit. It never amends, rebases, resets, checks out or pushes.
- Run `review` first so the message describes what actually changed.
- Exit code `1` when: `--message` is empty or spans more than one line; `ADULTING_HOME` is not a directory; `ADULTING_HOME` is not the root of its git repository; the `git` call fails.

## Everyday procedures

### 1. Set up a new billable project

1. `threads new --name SGB --kind project --category professional --currency ZAR --rate 2500` — create the thread with its billing defaults.
2. `people new --name "Jane Doe" --category professional` — create anyone you will assign work to.
3. `threads show Projects/SGB` — confirm the fields landed.
4. `lint` — check the new files validate.

### 2. Capture a meeting and turn its actions into tracked tasks

1. `notes new` — create the note and type into it during the meeting. **Interactive.**
2. Write `ACTION: (Jane Doe) Send the signed SOW` lines in the body as they come up.
3. `tasks --dry-run` — see what would be ingested.
4. `tasks` — rewrite each `ACTION:` line to a `TASK:` anchor in place.
5. `tasks list --thread Projects/SGB` — confirm the new tasks.
6. `notes minutes` — render minutes with the AGREED / RESOLVED / ACTION summary. **Interactive.**

### 3. Quick-capture through the day, then file it

1. `buffer add "chase the SGB invoice"` — record it in seconds, no thread needed.
2. `buffer list` — review what accumulated, with line numbers.
3. `buffer rm 1` — remove the raw UNKNOWN line you are about to replace.
4. `buffer add-action Projects/SGB "(Riaz Arbi) Chase the invoice" --priority H --due 2026-09-18` — re-add it structured.
5. `buffer tend` — regroup and validate; must report no violations.
6. `buffer flush` — write the entries into `logs/` and clear the buffer.
7. `tasks` — ingest the flushed ACTION lines into anchors.

### 4. Work the task list

1. `tasks next` — the top 5 by priority, due date, entry date.
2. `tasks list --overdue` — everything past its due date.
3. `tasks show abcd1234` — read one anchor in full.
4. `tasks set-scheduled abcd1234 2026-09-15` — move it to a day you can do it.
5. `tasks done abcd1234` — flip the source line to `DONE:` and stamp the end date.

### 5. Log a session of work

1. `hours log Projects/SGB Drafted the migration plan -m 90` — the description becomes an invoice line item.
2. `hours list Projects/SGB --since 2026-09-01` — check it landed on the right day.
3. `hours edit a1b2c3d4 -m 120` — correct the duration if it was wrong.

### 6. Bill a client for a month's work

1. `hours report --thread Projects/SGB --since 2026-08-01 --until 2026-08-31` — the month's totals by currency.
2. `hours list Projects/SGB --since 2026-08-01 --until 2026-08-31` — the line items behind the total.
3. `threads show Projects/SGB` — confirm the `client_*` fields are filled in.
4. `payments statement --thread Projects/SGB --pdf ~/Downloads/sgb-statement.pdf` — render the statement of account.

### 7. Record a payment

1. `payments log Projects/SGB 25000 -d 2026-09-05 -a "FNB current" -n "Aug invoice"` — record the receipt.
2. `payments list Projects/SGB` — confirm it is there.
3. `payments statement --thread Projects/SGB` — billed versus received, with aging.

### 8. Check the vault and commit it

1. `lint` — validate everything; exit 0 means clean.
2. `commit review` — read everything that changed since the last commit.
3. `commit save --message "Log SGB August work and August payment"` — stage it all and commit.

## Data formats

`lint` enforces every schema below.

### `hours_file`

Time entries for one thread, as JSON inside one ` ```simple-time-tracker ` fence. Lives at `hours/{Projects,Processes,Topics}/<Thread>.md`.

Frontmatter:

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to the thread; must resolve. |
| `currency` | no | Three-letter ISO code. Absent means the thread is not billable. |

Each element of `entries`:

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | The description of what was done. The invoice line item. |
| `startTime` | yes | ISO 8601 UTC start. |
| `endTime` | yes | ISO 8601 UTC end; not before `startTime`. |
| `id` | yes | 8 hex chars, unique across the whole vault. |
| `rate` | yes | Per-hour charge. `0` means unbillable and is an ordinary value. |
| `currency` | no | ISO 4217. Absent or null means unbilled. |

Duration is derived from `endTime − startTime`; there is no duration field. Rate and currency are stored per entry, so changing a thread's defaults never re-prices history.

### `log`

A per-thread per-day file of captured lines, written by `buffer flush`. Lives at `logs/<Kind>/<Name>/<YYYY-MM-DD>.md`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to a `Projects`, `Processes` or `Topics` thread. |
| `date` | yes | The day, `YYYY-MM-DD`. |
| `type` | yes | `Log`. |

Body lines are `REF:`, `TEXT:`, `ACTION:`, `TASK:` or `DONE:`. `tasks` ingests `ACTION:` lines from logs exactly as it does from notes.

### `note_correspondence`

A note recording email, message or letter exchanges. Lives in `notes/`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the exchange is about. |
| `type` | yes | `Correspondence`. |
| `threads` | yes | List of thread wikilinks; each must resolve. |
| `timestamp` | yes | `YYYY-MM-DD-HH-MM-SS`; when the thing happened. |
| `people` | no | List of `[[people/X]]` wikilinks or plain strings. |

Body lines may use `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:` and `!:`.

### `note_meeting`

A note recording a meeting with one or more counterparties. Lives in `notes/`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the meeting was about. |
| `type` | yes | `Meeting`. |
| `threads` | yes | List of thread wikilinks; each must resolve. |
| `timestamp` | yes | `YYYY-MM-DD-HH-MM-SS`; when the meeting happened. |
| `counterparty` | no | The other side. |
| `location` | no | Where it happened. |
| `people` | no | List of `[[people/X]]` wikilinks or plain strings. |

Body lines may use `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:` and `!:`.

### `note_simple`

A note of a bare-shape type: Workshop, Report, Log, Research or Recipe. Lives in `notes/`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about. |
| `type` | yes | One of Workshop, Report, Log, Research, Recipe. |
| `threads` | yes | List of thread wikilinks; each must resolve. |
| `timestamp` | yes | `YYYY-MM-DD-HH-MM-SS`. |
| `people` | no | List of `[[people/X]]` wikilinks or plain strings. |

Body lines may use `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:` and `!:`.

### `payments_file`

Money received against one thread, as JSON inside one ` ```adulting-payments ` fence. Lives at `payments/{Projects,Processes,Topics}/<Thread>.md`.

Frontmatter:

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to the thread; must resolve. |
| `currency` | yes | Three-letter ISO code. |

Each element of `payments`:

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | 8 hex chars, unique across the whole vault. Shares one namespace with `hours` ids. |
| `received` | yes | ISO 8601 UTC date the money landed. |
| `amount` | yes | Must be greater than zero. |
| `currency` | yes | ISO 4217. |
| `account` | no | Which account the money landed in. |
| `note` | no | Free text. |

### `person`

A contact you track. Lives in `people/`. People are link targets for a note's `people` and a task's assignee, never threads.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | `YYYY-MM-DD`. |
| `ended` | no | `YYYY-MM-DD`. Required when `status` is `closed`. |
| `cadences` | no | List of `{key, frequency, description}`. |

The body is free-form.

### `task_anchor`

A single `TASK:` or `DONE:` line in a note or log. The vault's source of truth for task state. Written and mutated only by `tasks`.

| Field | Required | Meaning |
|---|---|---|
| `kind` | yes | `TASK` or `DONE`. |
| `priority` | no | `H`, `M` or `L`, written as a visible `[#X]` token. |
| `assignee` | no | Must resolve to `people/<name>.md`. |
| `body` | yes | The description. |
| `uuid` | yes | 8 hex chars, unique across the vault. |
| `entry` | yes | The ingest date. |
| `end` | no | The completion date. Required when `kind` is `DONE`; not before `entry`. |
| `due` | no | Due date. |
| `scheduled` | no | Scheduled date. |
| `depends` | no | Comma-separated 8-char uuids; each must resolve, and the graph must be acyclic. |

Example: `TASK: [#H] (Riaz Arbi) Send quarterly report <!--abcd1234 entry:2026-05-27 due:2026-05-29-->`

The comment is hidden in Obsidian preview, so the reader sees only the visible portion.

### `thread`

The organising lens for notes, and the carrier of billing defaults. Lives in `threads/{Projects,Processes,Topics}/`.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `kind` | yes | `project`, `process` or `topic`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | `YYYY-MM-DD`. |
| `ended` | no | `YYYY-MM-DD`. Required when `status` is `closed`. |
| `cadences` | no | List of `{key, frequency, description}`; frequency is an interval in days. |
| `currency` | no | Default currency for `hours`. Three-letter ISO code. |
| `rate` | no | Default hourly rate for `hours`. |
| `client_name` | no | The party billed on a statement. Required to render one. |
| `client_address` | no | Pipe-separated address, e.g. `Unit 301\|2 Park Road\|Cape Town`. |
| `client_vat` | no | Client VAT number. |
| `client_email` | no | Client email. |

The payment reference printed on a statement is the thread name without its `Kind/` prefix. Supplier and banking details are vault-wide and live in `.adulting/config.yaml`. A cadence is satisfied when a log entry tagged `#<key>` is added to the thread.

### `thread_entry`

A single dated bullet at the top level of a thread file's body.

| Field | Required | Meaning |
|---|---|---|
| `date` | yes | `YYYY-MM-DD`. |
| `text` | yes | The entry text; at least one character. |

Shape: `- 2024-04-28 — Started on the IB integration.` Indented sub-bullets are continuation detail and are not separately validated. Out-of-order dates are tolerated.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `buffer flush` refuses to run | UNKNOWN entries are in the buffer; `tend` reports them as violations. | `buffer rm <line>` then re-add with `buffer add-text`, `add-ref` or `add-action`. |
| `tasks` exits 1: `no task found with uuid prefix` | The uuid prefix matches no anchor in the vault. | `tasks list` to find the real uuid. |
| `tasks` exits 1: uuid prefix is ambiguous | Two or more anchors share the prefix. | Pass more characters of the uuid. |
| `tasks` exits 1: person does not resolve | The assignee has no `people/<name>.md`. | `people new --name "<name>" --category professional`, then retry. |
| `tasks` exits 1: a task cannot depend on itself | `add-depends` was given the task's own uuid. | Pass a different task's uuid. |
| `buffer add-action` exits 1 on `--due` or `--scheduled` | The date is not `YYYY-MM-DD`. | Reformat the date. |
| `buffer add-action` exits 1 on `--depends` | The value is not 8 hex characters. | Use the full 8-char uuid. |
| `search` exits 1: could not resolve thread | The thread argument matches no file under `threads/`. | `threads list --all` to find the real name, then use `Kind/Name`. |
| `commit save` exits 1: `--message must be a single line` | The subject contains a newline. | Put the detail in `--body`. |
| `commit save` exits 1: not the root of its git repository | `ADULTING_HOME` points below the repository root, or at a non-directory. | Point `ADULTING_HOME` at the vault root. |
| `payments statement --pdf` will not render | `--pdf` requires `--thread`. | Add `--thread <Kind/Name>`. |
| `hours report` shows time under `unbilled` | The thread has no currency, so entries were written with rate 0 and no currency. | Add a `currency` to the thread, or log with `-c <ISO>`. Past entries keep their stored values. |
| `notes` hangs with no output | Every subcommand except `last` opens a picker on stdin. | Use `notes last`, or run the command at a TTY. |
| `lint` exits 2 | A usage error, not a validation failure. | Check the paths and `--schemas` argument. |

## Quick reference

| Command | Does |
|---|---|
| `tasks` | Rewrite every ACTION line in notes and logs to a TASK anchor. |
| `tasks add` | Buffer-append a structured ACTION. |
| `tasks done` | Flip a source TASK to DONE and stamp the end date. |
| `tasks set-description` | Rewrite a task body. |
| `tasks set-assignee` | Rewrite a task's assignee. |
| `tasks set-due` | Set a task's due date. |
| `tasks set-scheduled` | Set a task's scheduled date. |
| `tasks set-priority` | Set a task's priority. |
| `tasks add-depends` | Add a task dependency. |
| `tasks rm-depends` | Remove a task dependency. |
| `tasks list` | List pending tasks. |
| `tasks next` | Show the top 5 pending tasks. |
| `tasks show` | Show one task anchor in detail. |
| `notes new` | Create a note and open it (interactive). |
| `notes copy` | Copy a note to a new timestamp (interactive). |
| `notes strip` | Copy a note without its body (interactive). |
| `notes edit` | Open a note in the default editor (interactive). |
| `notes nano` | Open a note in nano (interactive). |
| `notes last` | Open the most recent note. |
| `notes delete` | Permanently delete a note (interactive). |
| `notes cat` | Print a note to stdout (interactive). |
| `notes pdf` | Render a note to PDF and markdown (interactive). |
| `notes minutes` | Render meeting minutes (interactive). |
| `notes agenda` | Render a meeting agenda (interactive). |
| `search notes` | Find notes by thread, type, date or text. |
| `search logs` | Find daily logs by thread, date or text. |
| `search activity` | Rank threads by activity in a window. |
| `search overview` | Summarise one thread. |
| `threads list` | List thread files. |
| `threads show` | Show one thread file. |
| `threads new` | Create a thread file. |
| `threads delete` | Permanently delete a thread file. |
| `people list` | List person files. |
| `people show` | Show one person file. |
| `people new` | Create a person file. |
| `people delete` | Permanently delete a person file. |
| `hours log` | Append a time entry. |
| `hours list` | List time entries. |
| `hours report` | Total time by thread and currency. |
| `hours show` | Show one time entry. |
| `hours edit` | Change one field of a time entry. |
| `hours rm` | Delete a time entry. |
| `payments log` | Record a receipt. |
| `payments list` | List payments. |
| `payments statement` | Show billed versus received. |
| `payments show` | Show one payment. |
| `payments edit` | Change one field of a payment. |
| `payments rm` | Delete a payment. |
| `buffer add` | Append a raw UNKNOWN capture. |
| `buffer suggest` | Propose a structured entry for raw text. |
| `buffer add-text` | Append a TEXT entry. |
| `buffer add-ref` | Append a REF entry. |
| `buffer add-action` | Append an ACTION entry. |
| `buffer list` | Show the buffer with line numbers. |
| `buffer rm` | Remove one buffer line. |
| `buffer tend` | Regroup and validate the buffer. |
| `buffer flush` | Write the buffer into logs and clear it. |
| `lint` | Validate vault files against the schemas. |
| `commit review` | Show everything changed since the last commit. |
| `commit save` | Stage all vault changes and commit them. |
