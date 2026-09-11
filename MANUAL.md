# adulting — Operators Manual

## Before you start

Everything lives under one vault directory. The default is `~/vault/`. Set `ADULTING_HOME` to point the tools at a different directory; every path below is relative to it.

The vault holds only plain text: markdown files with YAML frontmatter, plus JSON inside fenced code blocks. You can read, grep, diff and back it up with ordinary tools. `commit` puts it under git.

External programs the tools need:

| Program | Needed by |
|---|---|
| `bash`, `python3`, `awk`, `sed`, `grep` | everything |
| `pandoc` and a LaTeX engine (`xelatex`) | `notes pdf`, `notes minutes`, `notes agenda` |
| macOS `open` or Linux `xdg-open` | launching Obsidian for note editing |

Tooling state lives in the hidden `.adulting/` directory, including `.adulting/config.yaml`. The visible top level is user content only.

## How the pieces fit

| Object | What it is | Where it lives |
|---|---|---|
| Note | A persisted document: meeting, correspondence, report, research, recipe, workshop, log | `notes/` |
| Thread | The organising lens: a project, process or topic | `threads/{Projects,Processes,Topics}/` |
| Person | A contact you track; a link target, never a thread | `people/` |
| Time entry | One session of work on a thread, billable or not | `hours/{Projects,Processes,Topics}/` |
| Payment | Money received against a thread | `payments/{Projects,Processes,Topics}/` |
| Log | One thread's activity for one day | `logs/<Kind>/<Name>/<YYYY-MM-DD>.md` |
| Action / task | A commitment, stored as a line inside a note or log | `notes/` and `logs/` |
| Buffer | The quick-capture inbox | `buffer.md` |

Relationships that matter:

- A note names one or more threads in `threads`, and may name people in `people`.
- A log belongs to exactly one thread and one date.
- A buffer entry names a thread; `buffer flush` turns buffer entries into log lines.
- An `ACTION:` line in a note or log becomes a `TASK:` anchor with an 8-char uuid. The source file is the only store — there is no separate task backend.
- A task may name an assignee, which must resolve to a person file.
- A task may depend on other tasks by uuid.
- An hours file and a payments file each belong to one thread, and mirror the `threads/` layout.
- A thread may carry `currency` and `rate`, which `hours` uses as defaults, and `client_*` fields, which `payments statement --pdf` uses.

## Command reference

### tasks

Turns `ACTION:` lines in notes and logs into anchored `TASK:` lines, and edits those anchors in place.

**When to use it**

- You wrote `ACTION:` lines in a note and want them tracked.
- You finished something and want it marked done.
- You want to see what to work on next.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| (none) | Scan `notes/` and `logs/`, rewrite every `ACTION:` line as a `TASK:` anchor | `tasks` |
| `add` | Buffer-append a structured ACTION | `tasks add Projects/SGB "(Riaz Arbi) Send the draft" --priority H` |
| `done` | Flip source `TASK:` to `DONE:` and stamp the end date | `tasks done abcd1234` |
| `set-description` | Rewrite the task body | `tasks set-description abcd1234 "Send the revised draft"` |
| `set-assignee` | Rewrite the `(Assignee)` prefix | `tasks set-assignee abcd1234 "Riaz Arbi"` |
| `set-due` | Set the due date | `tasks set-due abcd1234 2026-10-01` |
| `set-scheduled` | Set the scheduled date | `tasks set-scheduled abcd1234 2026-09-25` |
| `set-priority` | Set priority H, M or L | `tasks set-priority abcd1234 H` |
| `add-depends` | Add a dependency | `tasks add-depends abcd1234 ef567890` |
| `rm-depends` | Remove a dependency | `tasks rm-depends abcd1234 ef567890` |
| `list` | List pending tasks | `tasks list --overdue` |
| `next` | Top 5 pending tasks by priority, due, entry | `tasks next` |
| `show` | Detail view of one anchor | `tasks show abcd1234` |

**Options**

| Option | Effect |
|---|---|
| `--dry-run` | No-arg invocation only. Show what would be ingested; write nothing. |
| `--quiet` | No-arg invocation only. Suppress per-action output. |
| `add --due <YYYY-MM-DD>` | Due date. |
| `add --scheduled <YYYY-MM-DD>` | Scheduled date. |
| `add --priority {H,M,L}` | Priority. |
| `add --depends <uuid8>` | 8-char uuid prefix; repeatable. |
| `list --priority {H,M,L}` | Filter to one priority. |
| `list --thread <thread>` | Filter to tasks whose source note carries this thread. |
| `list --assignee <person>` | Filter to tasks assigned to this person. |
| `list --overdue` | Only tasks due before today. |

**Notes**

- The no-arg invocation rewrites source notes and logs in place. Use `--dry-run` first if you are unsure.
- `tasks add` does not create a task directly. It appends an ACTION to the buffer; the task appears after `buffer flush` and ingest.
- Uuid arguments are prefixes. Exit code 1 if the prefix matches nothing or matches more than one task.
- Exit code 1 if the assignee does not resolve to `people/<person>.md`, if the description is empty, or if a task is made to depend on itself.
- Do not hand-write `TASK:` or `DONE:` lines. `tasks` owns them.

### notes

Creates, edits and renders note documents.

**When to use it**

- You are about to take minutes in a meeting.
- You want to reopen the note you just wrote.
- A client wants a PDF of the meeting record.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Create a note and open it (default with no subcommand) | `notes new` |
| `copy` | Pick a note, copy its contents to a new timestamp | `notes copy` |
| `strip` | Pick a note, copy it and remove the body, for templating | `notes strip` |
| `edit` | Pick a note, open in the default editor | `notes edit SGB` |
| `nano` | Pick a note, open in nano | `notes nano` |
| `last` | Open the most recently-created note | `notes last` |
| `delete` | Pick a note and permanently delete it | `notes delete` |
| `cat` | Pick a note and print it to stdout | `notes cat` |
| `pdf` | Pick a note, render PDF plus markdown | `notes pdf` |
| `minutes` | Pick a note, render minutes: TOC plus AGREED/RESOLVED/ACTION summary | `notes minutes` |
| `agenda` | Pick a note, render a meeting agenda | `notes agenda` |

**Options**

| Option | Effect |
|---|---|
| `<filter>` (second positional) | Case-insensitive substring filter for the picker. |

**Notes**

- Every subcommand except `last` opens an interactive picker and reads a selection from stdin. An agent must never call them. Only `notes last` is usable without a TTY.
- `notes delete` is permanent.
- Rendered output goes to `$EXPORT_DIR`, default `~/Downloads`.
- Body keywords you can write: `ACTION:` (ingested by `tasks`), `AGREED:`, `RESOLVED:`, `!:` (surfaced in the `pdf` summary). Do not write `TASK:` by hand.

### search

Finds notes and logs, and summarises thread activity. Returns pointers, never bodies.

**When to use it**

- You need the path of a note you wrote months ago.
- You want to know what happened on a thread last quarter.
- You want a single view of everything on one thread.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `notes` | Find notes by thread, type, date or text | `search notes --thread Projects/SGB --type Meeting` |
| `logs` | Find daily logs by thread, date or text | `search logs --thread Projects/SGB --since 2026-08-01` |
| `activity` | Rank threads by what happened in a window | `search activity --since 2026-08-01 --until 2026-08-31` |
| `overview` | The whole picture of one thread | `search overview Projects/SGB` |

**Options**

Global for all four subcommands: `--since <YYYY-MM-DD>`, `--until <YYYY-MM-DD>`, `--json`.

| Option | Effect |
|---|---|
| `--thread <thread>` | Thread name, `Kind/Name`, or wikilink. On `activity`, limits to one thread. |
| `--type <type>` | `notes` only. Note type, case-insensitive. |
| `--text <text>` | Case-insensitive literal. Over topic and body for notes; over entry lines for logs. |
| `--limit <n>` | Max results. Default 20 for `notes` and `logs` (0 for all); default 5 for `overview`. |

**Notes**

- Paths are absolute, resolved against `ADULTING_HOME`. Hand them straight to a reader.
- Dates are the event date, from a note's frontmatter `timestamp`. The filename is used only when the frontmatter date is missing or malformed.
- `search` indexes notes and logs. It does not index hours.
- Exit code 1 if a thread argument cannot be resolved.

### threads

Creates, lists, shows and deletes thread files.

**When to use it**

- A new project starts and needs a thread.
- You need a thread's billing defaults or client details.
- You want the list of open work.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | List thread files, open by default | `threads list SGB --all` |
| `show` | Show a single thread file | `threads show Projects/SGB` |
| `new` | Create a thread file | `threads new --name SGB --kind project --category professional --currency ZAR --rate 2500` |
| `delete` | Permanently delete a thread file | `threads delete Projects/SGB -y` |

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
| `delete -y` | Skip confirmation. |

**Notes**

- `threads new` prompts interactively for any field you do not pass. Supply `--name`, `--kind` and `--category` to run it without a TTY.
- `threads delete` is permanent and prompts unless you pass `-y`.
- `list` takes an optional fuzzy `query` that ranks results by similarity.

### people

Creates, lists, shows and deletes person files.

**When to use it**

- You want to assign a task to someone for the first time.
- You want to check who you track in a category.
- A contact record is wrong and must go.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | List person files, open by default | `people list --all` |
| `show` | Show a single person file | `people show "Riaz Arbi"` |
| `new` | Create a person file | `people new --name "Riaz Arbi" --category professional` |
| `delete` | Permanently delete a person file | `people delete "Riaz Arbi" -y` |

**Options**

| Option | Effect |
|---|---|
| `list --all` | Include closed people. |
| `list --json`, `show --json` | JSON output. |
| `new --name <name>` | Full name; skips the prompt. |
| `new --category {professional,personal,voluntary}` | Skips the prompt. |
| `delete -y` | Skip confirmation. |

**Notes**

- `people new` prompts interactively for any field you do not pass. Supply `--name` and `--category` to run it without a TTY.
- A person must exist before a task can be assigned to them; `tasks set-assignee` exits 1 otherwise.
- `people show` and `people delete` match the filename without `.md`.

### hours

Records time spent on a thread, billable or not.

**When to use it**

- You finished a block of client work and need it on the invoice.
- You want this month's totals per thread.
- You logged the wrong duration and need to fix it.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Append an entry | `hours log Projects/SGB "DORA metric validation" -m 180` |
| `list` | List entries | `hours list Projects/SGB --since 2026-08-01 --until 2026-08-31` |
| `report` | Totals by thread and currency, unbilled totalled separately | `hours report --thread Projects/SGB --since 2026-08-01` |
| `show` | Show one entry | `hours show a1b2c3d4` |
| `edit` | Change one field of an entry | `hours edit a1b2c3d4 -m 90` |
| `rm` | Delete an entry | `hours rm a1b2c3d4 -y` |

**Options**

| Option | Effect |
|---|---|
| `log -m, --minutes <n>` | Duration. Default 60. |
| `log -r, --rate <n>` | Hourly rate. 0 means unbillable. |
| `log -c, --currency <ISO>` | ISO code. Defaults to the thread's. Without either, the entry is recorded as unbilled. |
| `log -d, --date <YYYY-MM-DD>` | Default today. |
| `log -t, --time <HH:MM>` | Default now. |
| `log --all` | Interactive mode only: list paused and closed threads too. |
| `list --since`, `list --until` | Inclusive date bounds, `YYYY-MM-DD`. |
| `report --thread <thread>`, `--since`, `--until` | Scope the report. |
| `edit --description <text>`, `-m`, `-r`, `-c`, `-d`, `-t` | Change one field. |
| `rm -y` | Skip confirmation. |
| `--json` | On `list`, `report`, `show`. |

**Notes**

- `hours log` with no thread is interactive. Always pass a thread when running without a TTY.
- Rate and currency are resolved at write time and stored on each entry. Changing a thread's defaults never re-prices logged work.
- A thread with no currency is not billable. Its entries are written with rate 0 and no currency, and total under an `unbilled` row.
- Entry descriptions are invoice line items, not narrative. Put detail in a log line instead — `search` does not index hours.
- `hours rm` is permanent and prompts unless you pass `-y`.

### payments

Records money received against a thread and reconciles it against billed time.

**When to use it**

- A client's transfer lands.
- You need a statement of account for a client.
- You typed the wrong amount.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Record a receipt | `payments log Projects/SGB 15000 -a "FNB current" -d 2026-09-01` |
| `list` | List payments | `payments list Projects/SGB --since 2026-01-01` |
| `statement` | Billed vs received, by thread and currency | `payments statement --thread Projects/SGB --pdf ~/Downloads/sgb.pdf` |
| `show` | Show one payment | `payments show a1b2c3d4` |
| `edit` | Change one field of a payment | `payments edit a1b2c3d4 --amount 16000` |
| `rm` | Delete a payment | `payments rm a1b2c3d4 -y` |

**Options**

| Option | Effect |
|---|---|
| `log -c, --currency <ISO>` | ISO code. Defaults to the thread's. |
| `log -d, --date <YYYY-MM-DD>` | Date received. Default today. |
| `log -t, --time <HH:MM>` | Default now. |
| `log -a, --account <name>` | Which account it landed in. |
| `log -n, --note <text>` | Free text. |
| `log --all` | Interactive mode only: list paused and closed threads too. |
| `list --since`, `list --until` | Date bounds. |
| `statement --thread <thread>`, `--since`, `--until` | Scope the statement. |
| `statement --as-of <YYYY-MM-DD>` | Statement date; drives aging. Default today. |
| `statement --pdf <path>` | Render a PDF to this path. Requires `--thread`. |
| `edit --amount <n>`, `-c`, `-d`, `-t`, `-a`, `-n` | Change one field. |
| `rm -y` | Skip confirmation. |
| `--json` | On `list`, `statement`, `show`. |

**Notes**

- `payments log` with no thread is interactive. Pass thread and amount when running without a TTY.
- Money received must always name a currency; there is no unbilled fallback.
- Amounts must be positive. There is no negative payment.
- `payments statement` ignores unbilled hours.
- `--pdf` needs the thread's `client_name`. The payment reference printed is the thread name without its `Kind/` prefix.
- `payments rm` is permanent and prompts unless you pass `-y`.

### buffer

The quick-capture inbox at `buffer.md`, and the commands that shape and drain it.

**When to use it**

- You are between things and want to note something without picking a thread.
- You want to file an observation against a thread in one line.
- End of day: you want the buffer written into logs.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `add` | Append an UNKNOWN entry | `buffer add "chase the SARS letter"` |
| `suggest` | Propose a structured add for raw text, then prompt | `buffer suggest "call Igor about DORA" -y` |
| `add-text` | Append a TEXT entry | `buffer add-text Projects/SGB "Join semantics still unresolved"` |
| `add-ref` | Append a REF entry | `buffer add-ref Projects/SGB notes/2026-09-01-14-30-00 "Vendor decision"` |
| `add-action` | Append an ACTION entry | `buffer add-action Projects/SGB "(Riaz Arbi) Send the draft" --due 2026-09-30` |
| `list` | Show the buffer with line numbers | `buffer list SGB` |
| `rm` | Remove a single line by line number | `buffer rm 3` |
| `tend` | Regroup by thread and date, then validate | `buffer tend` |
| `flush` | Tend, then write to `logs/` and clear the buffer | `buffer flush` |

**Options**

| Option | Effect |
|---|---|
| `--quiet` | Global. Suppress info output. |
| `suggest -y` | Auto-accept the suggestion without prompting. |
| `add-action --due <YYYY-MM-DD>` | Due date, applied on flush and ingest. |
| `add-action --scheduled <YYYY-MM-DD>` | Scheduled date. |
| `add-action --priority {H,M,L}` | Priority. |
| `add-action --depends <uuid8>` | 8-char uuid prefix; repeatable. |

**Notes**

- `buffer suggest` prompts unless you pass `-y`. Without a TTY, always pass `-y`.
- UNKNOWN entries are intentionally invalid. `tend` reports them as violations and they block `flush` until you remove them and re-add them with the matching `add-*` command.
- `flush` clears the buffer. Run `tend` first if you want to see the state before it is drained.
- `tend` is idempotent and is the way to fix the buffer. Do not edit `buffer.md` by hand.
- Exit code 1 if a date is not `YYYY-MM-DD`, if `--depends` is not 8 hex characters, or if the text or description is empty.

### lint

Validates vault files against the schemas.

**When to use it**

- Before committing, to check nothing is malformed.
- After hand-editing a note's frontmatter.
- To check one file you just wrote.

**Usage**

`lint [<path> ...]`

| Argument | Meaning |
|---|---|
| `paths` | Files to validate. With none, walks the vault. |

**Options**

| Option | Effect |
|---|---|
| `--schemas <dir>` | Schemas directory. |
| `--quiet` | Exit code only; suppress per-violation output. |

**Notes**

- Read-only. It never changes a file.
- Exit 0 if clean, 1 if there are violations. Violations print as `<path>:<line>: <message>`.
- Exit code 2 signals a failure to run rather than a violation.

### commit

Reviews uncommitted vault changes, then stages and commits them.

**When to use it**

- End of a working session, before you walk away.
- After a `buffer flush` or a `tasks` ingest rewrote files.
- To read exactly what changed before writing a message.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `review` | Show everything changed since the last commit. Read-only. | `commit review --max-file-lines 50` |
| `save` | Stage every change in the vault and commit it | `commit save --message "Flush buffer and log SGB hours"` |

**Options**

| Option | Effect |
|---|---|
| `review --max-file-lines <n>` | Max diff lines shown per file. Default 150. |
| `review --max-lines <n>` | Max lines of output overall. Default 3000. |
| `save --message <text>` | Required. Commit subject. Single line. |
| `save --body <text>` | Commit body. May span multiple lines. |
| `save --dry-run` | Report what would be staged and committed; change nothing. |

**Notes**

- `save` can only add a commit. It never amends, rebases, resets, checks out or pushes.
- Run `review` first, then write `--message` from what you read.
- Exit code 1 if `--message` is empty or spans more than one line, if `ADULTING_HOME` is not a directory, if it is not the root of its git repository, or if the git call fails.

## Everyday procedures

### 1. Set up a new billable project

1. `threads new --name SGB --kind project --category professional --currency ZAR --rate 2500` — create the thread with billing defaults.
2. `threads show Projects/SGB` — confirm the fields landed.
3. `people new --name "Igor Petrov" --category professional` — create anyone you will assign work to.
4. `lint` — check the new files validate.
5. `commit save --message "Add Projects/SGB thread"` — record it in git.

### 2. Capture a meeting and turn its actions into tracked tasks

1. `notes new` — create the meeting note and write it up. Interactive; TTY only.
2. Write `ACTION:` lines in the body for each commitment, with `(Assignee)` where it applies.
3. `tasks --dry-run` — see what would be ingested.
4. `tasks` — rewrite each `ACTION:` line into a `TASK:` anchor in the source file.
5. `tasks list --thread Projects/SGB` — confirm the new tasks.
6. `lint` — check the note still validates.

### 3. Quick-capture through the day, then file it

1. `buffer add "chase the SARS letter"` — capture when you have no time to pick a thread.
2. `buffer add-text Projects/SGB "Join semantics still unresolved"` — file an observation against a thread.
3. `buffer list` — see everything queued, with line numbers.
4. `buffer rm 1` — remove the UNKNOWN entry.
5. `buffer add-action Processes/Tax "File the return" --due 2026-09-30 --priority H` — re-add it properly.
6. `buffer tend` — regroup and validate; fix anything reported.
7. `buffer flush` — write the entries into `logs/` and clear the buffer.
8. `tasks` — ingest the new ACTION lines into anchors.

### 4. Work the task list

1. `tasks next` — the top 5 by priority, due date and entry date.
2. `tasks list --overdue` — what is late.
3. `tasks show abcd1234` — the detail of one anchor.
4. `tasks set-due abcd1234 2026-10-01` — move a due date.
5. `tasks set-assignee abcd1234 "Igor Petrov"` — hand it over.
6. `tasks done abcd1234` — mark it complete; the end date is stamped.

### 5. Log a session of work

1. `hours log Projects/SGB "DORA metric validation" -m 180` — record the duration under an invoice-ready label.
2. `buffer add-text Projects/SGB "Validated the SQL detection patterns; join semantics unresolved"` — record what actually happened.
3. `buffer flush` — write that into today's log.
4. `hours list Projects/SGB --since 2026-09-01` — confirm the entry.

### 6. Bill a client for a month's work

1. `hours report --thread Projects/SGB --since 2026-08-01 --until 2026-08-31` — totals for the month.
2. `hours list Projects/SGB --since 2026-08-01 --until 2026-08-31` — the line items.
3. `hours edit a1b2c3d4 --description "DORA metric validation"` — fix any label that would read badly on an invoice.
4. `threads show Projects/SGB` — check `client_name` and the other client fields are set.
5. `payments statement --thread Projects/SGB --as-of 2026-09-01 --pdf ~/Downloads/sgb-statement.pdf` — render the statement of account.

### 7. Record a payment

1. `payments log Projects/SGB 15000 -d 2026-09-01 -a "FNB current" -n "Aug invoice"` — record the receipt.
2. `payments list Projects/SGB --since 2026-09-01` — confirm it.
3. `payments statement --thread Projects/SGB` — check billed against received.
4. `payments edit a1b2c3d4 --amount 16000` — correct the amount if it was wrong.

### 8. Check the vault and commit it

1. `buffer tend` — make sure nothing is stuck in the buffer.
2. `lint` — validate every file; fix any `<path>:<line>:` violations reported.
3. `commit review` — read everything that changed.
4. `commit save --dry-run --message "Weekly vault update"` — see what would be staged.
5. `commit save --message "Weekly vault update" --body "Flushed buffer, logged SGB hours, recorded August payment."` — commit.

## Data formats

`lint` enforces every schema below.

### `hours_file`

Billable and unbillable time for one thread, one file per thread, at `hours/{Projects,Processes,Topics}/<Thread>.md`. The body carries exactly one ` ```simple-time-tracker ` fenced block containing JSON `{"entries": [...]}`.

Frontmatter:

| Field | Required | Meaning |
|---|---|---|
| `thread` | Yes | Wikilink to the thread; must resolve to an existing thread file. |
| `currency` | No | Three-letter uppercase ISO code. Absent means the file is not billable. |

Entry object:

| Field | Required | Meaning |
|---|---|---|
| `name` | Yes | The description — what was done. An invoice line item. |
| `startTime` | Yes | ISO 8601 UTC start. |
| `endTime` | Yes | ISO 8601 UTC end; must not precede `startTime`. |
| `id` | Yes | 8 hex characters, unique across the whole vault. |
| `rate` | Yes | Per-hour charge. `0` means unbillable and is an ordinary value. |
| `currency` | No | ISO 4217 code. Absent or null means unbilled. |

Duration is derived from `endTime` minus `startTime`; there is no duration field. Rate and currency are stored per entry so changing a thread's defaults never re-prices history. The plugin's `subEntries` and `collapsed` keys are valid but unused. JSON is pretty-printed at indent 2.

### `log`

One thread's activity for one day, written by `buffer flush`, at `logs/<Kind>/<Name>/<YYYY-MM-DD>.md`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | Yes | Wikilink to `Projects/`, `Processes/` or `Topics/`. |
| `date` | Yes | The day, `YYYY-MM-DD`. |
| `type` | Yes | Always `Log`. |

Body lines: `REF: [[X]] ...` points at another vault file; `TEXT: ...` is a free-text observation; `ACTION: ...` is an open action item; `TASK: ...` and `DONE: ...` are anchored items. The day is the resolution; sub-day timestamps are not preserved. `tasks` ingest treats logs and notes identically.

### `note_correspondence`

A note recording email, message or letter exchanges. Lives in `notes/`, filename `YYYY-MM-DD-HH-MM-SS.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | Yes | What the correspondence is about. |
| `type` | Yes | `Correspondence`. |
| `threads` | Yes | List of thread wikilinks; each must resolve. |
| `timestamp` | Yes | When it happened, `YYYY-MM-DD-HH-MM-SS`. |
| `people` | No | List. Entries may be `[[people/X]]` wikilinks, which must resolve, or plain strings. |

Body keywords: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:`, `!:`.

### `note_meeting`

A note recording a meeting. Lives in `notes/`, filename `YYYY-MM-DD-HH-MM-SS.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | Yes | What the meeting was about. |
| `type` | Yes | `Meeting`. |
| `threads` | Yes | List of thread wikilinks; each must resolve. |
| `timestamp` | Yes | When the meeting happened, `YYYY-MM-DD-HH-MM-SS`. |
| `counterparty` | No | The other party. |
| `location` | No | Where it took place. |
| `people` | No | List. Entries may be `[[people/X]]` wikilinks, which must resolve, or plain strings. |

Body keywords: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:`, `!:`.

### `note_simple`

A note with no type-specific fields, for Workshop, Report, Log, Research or Recipe. Lives in `notes/`, filename `YYYY-MM-DD-HH-MM-SS.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | Yes | What the note is about. |
| `type` | Yes | One of Workshop, Report, Log, Research, Recipe. |
| `threads` | Yes | List of thread wikilinks; each must resolve. |
| `timestamp` | Yes | When it happened, `YYYY-MM-DD-HH-MM-SS`. |
| `people` | No | List of wikilinks or plain strings. |

Body keywords: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:`, `!:`.

### `payments_file`

Money received against one thread, one file per thread, at `payments/{Projects,Processes,Topics}/<Thread>.md`. The body carries exactly one ` ```adulting-payments ` fenced block containing JSON `{"payments": [...]}`.

Frontmatter:

| Field | Required | Meaning |
|---|---|---|
| `thread` | Yes | Wikilink to the thread; must resolve. |
| `currency` | Yes | Three-letter uppercase ISO code. |

Payment object:

| Field | Required | Meaning |
|---|---|---|
| `id` | Yes | 8 hex characters, unique across the whole vault. |
| `received` | Yes | ISO 8601 UTC date the money landed. |
| `amount` | Yes | Must be greater than zero. |
| `currency` | Yes | ISO 4217 code. |
| `account` | No | Which account the money landed in. |
| `note` | No | Free text. |

Ids share one namespace with `hours` entry ids; `lint` checks uniqueness across both. Amounts are computed with decimal arithmetic, never floats. A refund is not a negative payment. JSON is pretty-printed at indent 2.

### `person`

A contact you track, one file per person, in `people/`. People are link targets for `note.people` and task assignees. They cannot be the value of a note's thread.

| Field | Required | Meaning |
|---|---|---|
| `status` | Yes | `open`, `paused` or `closed`. |
| `category` | Yes | `professional`, `personal` or `voluntary`. |
| `started` | Yes | Date you started tracking them, `YYYY-MM-DD`. |
| `ended` | No | Required when `status` is `closed`. |
| `cadences` | No | List of `{key, frequency, description}` objects. |

The body is free-form.

### `task_anchor`

A single `TASK:` or `DONE:` line inside a note or log. This is the vault's source of truth for task state; there is no backend. Written by `tasks` ingest and mutated only by `tasks` subcommands.

| Field | Required | Meaning |
|---|---|---|
| `kind` | Yes | `TASK` or `DONE`. |
| `priority` | No | `H`, `M` or `L`, written as a visible `[#X]` token. |
| `assignee` | No | Person name in parentheses; must resolve to `people/<name>.md`. |
| `body` | Yes | The description. |
| `uuid` | Yes | 8 hex characters, unique across the vault. |
| `entry` | Yes | The ingest date. |
| `end` | No | Completion date. Required when `kind` is `DONE`, and must not precede `entry`. |
| `due` | No | Due date. |
| `scheduled` | No | Scheduled date. |
| `depends` | No | Comma-separated 8-char uuids; each must resolve to another anchor. The graph must be acyclic. |

Example lines:

```
TASK: [#H] (Riaz Arbi) Send quarterly report <!--abcd1234 entry:2026-05-27 due:2026-05-29-->
TASK: Pick up dry cleaning <!--ef567890 entry:2026-05-27-->
DONE: [#M] (Charlie) Review the contract <!--abc12340 entry:2026-05-24 end:2026-05-27-->
```

Attribute order in the comment is fixed: `entry`, `end`, `due`, `scheduled`, `depends`. Priority lives only in the visible token. Obsidian hides the comment in preview.

### `thread`

A project, process or topic, one file per thread, in `threads/`.

| Field | Required | Meaning |
|---|---|---|
| `status` | Yes | `open`, `paused` or `closed`. |
| `kind` | Yes | `project`, `process` or `topic`. |
| `category` | Yes | `professional`, `personal` or `voluntary`. |
| `started` | Yes | Start date, `YYYY-MM-DD`. |
| `ended` | No | Required when `status` is `closed`. |
| `cadences` | No | List of `{key, frequency, description}` objects. |
| `currency` | No | Three-letter uppercase ISO code; default currency for `hours`. |
| `rate` | No | Default hourly rate for `hours`. |
| `client_name` | No | Party billed on a statement. Required to render one. |
| `client_address` | No | Pipe-separated address, e.g. `Unit 301\|2 Park Road\|Cape Town`. |
| `client_vat` | No | Client VAT number. |
| `client_email` | No | Client email address. |

Per-cadence fields: `key` (unique within the thread, used as a tag), `frequency` (interval in days), `description`. A cadence is satisfied when a body entry tagged `#<key>` is added.

`hours log` refuses to write without a currency. `rate` falls back to `.adulting/config.yaml`'s `time.rate`, then to 2500. Both are resolved at write time and stored on each entry. Supplier and banking details are vault-wide and live in `.adulting/config.yaml` under `billing:`. The body holds dated bullets; out-of-order dates are tolerated.

### `thread_entry`

A single dated bullet at the top level of a thread file's body, in the form `- YYYY-MM-DD — text`.

| Field | Required | Meaning |
|---|---|---|
| `date` | Yes | The entry date, `YYYY-MM-DD`. |
| `text` | Yes | What happened. Must not be empty. |

Indented sub-bullets are continuation detail and are not separately validated.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `buffer tend` reports violations and `flush` refuses to run | UNKNOWN entries are intentionally invalid and block the flush | `buffer list`, then `buffer rm <line>` and re-add with `add-text`, `add-ref` or `add-action` |
| `buffer add-action` exits 1 with a date complaint | `--due` or `--scheduled` is not `YYYY-MM-DD` | Re-run with the full ISO date |
| `buffer add-action` exits 1 on `--depends` | The value is not exactly 8 hex characters | Pass an 8-char uuid prefix; repeat the flag for several |
| `tasks` exits 1: uuid prefix is ambiguous | The prefix matches more than one anchor | Pass more characters of the uuid, found with `tasks list` or `tasks show` |
| `tasks` exits 1: no task found with that prefix | The uuid does not exist in any note or log | Run `tasks` to ingest pending ACTION lines, then `tasks list` |
| `tasks set-assignee` exits 1: person does not resolve | There is no `people/<person>.md` | `people new --name "<person>" --category professional` |
| `tasks` exits 1: a task cannot depend on itself | `add-depends` was given the task's own uuid | Pass a different task's uuid |
| `search` exits 1: could not resolve thread | The `--thread` value does not match a thread file | `threads list --all` to find the exact `Kind/Name` |
| An hours entry has no currency and shows under `unbilled` | Neither `-c` nor a thread `currency` was available at write time | `hours edit <id> -c <ISO>`, or set `--currency` on the thread for future entries |
| `lint` prints `<path>:<line>: <message>` and exits 1 | A file breaks its schema | Fix the named field on the named line; re-run `lint <path>` |
| `commit save` exits 1: message must be a single line | `--message` contained a newline | Keep `--message` to one line and put detail in `--body` |
| `commit save` exits 1: ADULTING_HOME is not the root of its git repository | The vault directory is not itself the repo root | Point `ADULTING_HOME` at the repo root, or initialise the repo there |
| `notes pdf`, `minutes` or `agenda` fails to render | `pandoc` or the LaTeX engine is missing | Install `pandoc` and `xelatex` |

## Quick reference

| Command | Does |
|---|---|
| `tasks` | Rewrite every ACTION line in notes and logs into a TASK anchor |
| `tasks add <thread> <text>` | Buffer-append a structured ACTION |
| `tasks done <uuid>` | Mark a task complete and stamp the end date |
| `tasks set-description <uuid> <text>` | Rewrite the task body |
| `tasks set-assignee <uuid> <person>` | Change the assignee |
| `tasks set-due <uuid> <date>` | Set the due date |
| `tasks set-scheduled <uuid> <date>` | Set the scheduled date |
| `tasks set-priority <uuid> <H\|M\|L>` | Set the priority |
| `tasks add-depends <uuid> <dep-uuid>` | Add a dependency |
| `tasks rm-depends <uuid> <dep-uuid>` | Remove a dependency |
| `tasks list` | List pending tasks |
| `tasks next` | Top 5 pending tasks |
| `tasks show <uuid>` | Detail of one task |
| `notes new` | Create a note (interactive) |
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
| `search notes` | Find notes by thread, type, date or text |
| `search logs` | Find daily logs by thread, date or text |
| `search activity` | Rank threads by activity in a window |
| `search overview <thread>` | The whole picture of one thread |
| `threads list` | List thread files |
| `threads show <thread>` | Show one thread file |
| `threads new` | Create a thread file |
| `threads delete <thread>` | Permanently delete a thread file |
| `people list` | List person files |
| `people show <person>` | Show one person file |
| `people new` | Create a person file |
| `people delete <person>` | Permanently delete a person file |
| `hours log <thread> <description>` | Append a time entry |
| `hours list` | List time entries |
| `hours report` | Totals by thread and currency |
| `hours show <id>` | Show one time entry |
| `hours edit <id>` | Change one field of a time entry |
| `hours rm <id>` | Delete a time entry |
| `payments log <thread> <amount>` | Record a receipt |
| `payments list` | List payments |
| `payments statement` | Billed vs received, by thread and currency |
| `payments show <id>` | Show one payment |
| `payments edit <id>` | Change one field of a payment |
| `payments rm <id>` | Delete a payment |
| `buffer add <text>` | Append an UNKNOWN entry |
| `buffer suggest <text>` | Propose a structured entry for raw text |
| `buffer add-text <thread> <text>` | Append a TEXT entry |
| `buffer add-ref <thread> <target>` | Append a REF entry |
| `buffer add-action <thread> <text>` | Append an ACTION entry |
| `buffer list` | Show the buffer with line numbers |
| `buffer rm <line-number>` | Remove one buffer line |
| `buffer tend` | Regroup and validate the buffer |
| `buffer flush` | Write the buffer into logs and clear it |
| `lint` | Validate vault files against the schemas |
| `commit review` | Show everything changed since the last commit |
| `commit save --message <text>` | Stage every change and commit it |
