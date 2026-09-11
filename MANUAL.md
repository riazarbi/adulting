# adulting — Operators Manual

## Before you start

Your data lives in one directory: `~/vault/` by default. Set `ADULTING_HOME` to point the tools somewhere else.

```
~/vault/
├── .adulting/config.yaml   # vault-wide config
├── notes/                  # markdown notes
├── threads/{Projects,Processes,Topics}/
├── people/                 # person files
├── logs/<Kind>/<Name>/<date>.md
├── hours/{Projects,Processes,Topics}/
├── payments/{Projects,Processes,Topics}/
└── buffer.md               # quick-capture inbox
```

External programs you need:

| Program | Needed by |
|---|---|
| `bash`, `python3`, `awk`, `sed`, `grep` | everything |
| `pandoc` and `xelatex` | `notes pdf`, `notes minutes`, `notes agenda` |
| `open` (macOS) or `xdg-open` (Linux) | opening notes in Obsidian |

Everything is plain text on disk. You can read it, `grep` it, diff it and back it up yourself. No database, no import step.

## How the pieces fit

| Object | What it is | Where it lives |
|---|---|---|
| Note | A persisted document: meeting, correspondence, report, research. | `notes/` |
| Thread | An organising lens — a project, process or topic. | `threads/{Projects,Processes,Topics}/` |
| Person | A contact you track; a link target, never a thread. | `people/` |
| Log | One day of one thread's activity, one line per record. | `logs/<Kind>/<Name>/<date>.md` |
| Time entry | A session of work on a thread, billable or not. | `hours/<Kind>/<Thread>.md` |
| Payment | Money received against a thread. | `payments/<Kind>/<Thread>.md` |
| Action / task | A commitment, written as a line inside a note or log. | `notes/`, `logs/` |
| Buffer entry | A staged capture, not yet filed. | `buffer.md` |

Relationships that matter:

- A note names one or more threads in its `threads` frontmatter list, and may name people.
- A time entry and a payment each belong to exactly one thread; their file path mirrors the thread's.
- A task lives as a `TASK:` or `DONE:` line inside its source note or log. That line is the store — there is no backend.
- A task may name an assignee, who must be a person file. A task may depend on other tasks by uuid.
- `buffer flush` writes buffer entries into the per-thread daily logs and clears the buffer.
- `notes new`, `hours log` and `payments log` each drop a `REF:` into the buffer, filed under the day the thing happened, so the thread's log is a full chronology.
- A thread carrying a `currency` is billable; `hours` costs its entries and `payments statement` reconciles them.

## Command reference

### `tasks`

Turns `ACTION:` lines in notes and logs into anchored `TASK:` lines, and edits those anchors.

**When to use it**

- You wrote `ACTION:` lines in a note and want them tracked.
- You finished something and need to mark it done.
- You want to see what to work on next.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| *(none)* | Ingest every `ACTION:` line in `notes/` and `logs/`, rewriting each in place as a `TASK:` anchor. | `tasks` |
| `add` | Buffer-append a structured ACTION. | `tasks add Projects/SGB "(Riaz Arbi) Draft the scope note" --priority H` |
| `done` | Flip the source `TASK:` to `DONE:` and stamp `end:` with today. | `tasks done abcd1234` |
| `set-description` | Rewrite the task body. | `tasks set-description abcd1234 "Draft and circulate the scope note"` |
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
| `--dry-run` | Default invocation only. Show what would be ingested; write nothing. |
| `--quiet` | Default invocation only. Suppress per-action output. |
| `add --due <YYYY-MM-DD>` | Due date. |
| `add --scheduled <YYYY-MM-DD>` | Scheduled date. |
| `add --priority H\|M\|L` | Priority. |
| `add --depends <uuid8>` | 8-char uuid prefix; repeatable. |
| `list --priority H\|M\|L` | Filter to one priority. |
| `list --thread <Kind/Name>` | Filter to tasks whose source note carries this thread. |
| `list --assignee <person>` | Filter to one assignee. |
| `list --overdue` | Only tasks due before today. |

**Notes**

- The bare `tasks` invocation rewrites source notes and logs in place. Use `--dry-run` first if unsure.
- `tasks add` does not create a task directly. It appends an ACTION to the buffer; the task appears after `buffer flush` and the next `tasks` ingest.
- Do not write `TASK:` lines by hand. `tasks` owns them.
- Exit code 1: no task matches the uuid prefix, the prefix is ambiguous, the description is empty, the assignee does not resolve to `people/<name>.md`, or a task would depend on itself.

### `notes`

Creates, edits, renders and deletes notes.

**When to use it**

- You are about to hold a meeting and want a record for it.
- You want to reopen the note you just wrote.
- You need a PDF, minutes or an agenda from a note.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Create a new note and open it. Default when no subcommand is given. | `notes new` |
| `copy` | Pick a note, copy its contents to a new timestamp. | `notes copy` |
| `strip` | Pick a note, copy it and remove the body — a template. | `notes strip` |
| `edit` | Pick a note, open in the default editor. | `notes edit SGB` |
| `nano` | Pick a note, open in nano. | `notes nano` |
| `last` | Open the most recently-created note. | `notes last` |
| `delete` | Pick a note and permanently delete it. | `notes delete` |
| `cat` | Pick a note and print it to stdout. | `notes cat SGB` |
| `pdf` | Pick a note, render to PDF and markdown. | `notes pdf` |
| `minutes` | Pick a note, render minutes: TOC plus AGREED/RESOLVED/ACTION summary. | `notes minutes` |
| `agenda` | Pick a note, render a meeting agenda. | `notes agenda` |

**Options**

| Option | Effect |
|---|---|
| `<filter>` | Optional second argument. Filters the picker list, case-insensitive. |

**Notes**

- **Every subcommand except `last` is interactive.** It opens a picker and reads a selection from stdin. An agent must never call them. `last` is the only subcommand usable without a TTY.
- `delete` is permanent.
- Rendered output goes to `$EXPORT_DIR`, default `~/Downloads`.
- Body keywords you can write: `ACTION:` (ingested by `tasks`), `AGREED:`, `RESOLVED:`, `!:` (callout surfaced in `notes pdf`). Do not write `TASK:` by hand.

### `search`

Finds notes and logs, and summarises what happened on a thread.

**When to use it**

- You remember a phrase but not which note holds it.
- You are picking up a thread after weeks away.
- You want everything that touched a thread, in one chronology.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `notes` | Find notes by thread, type, date or text. | `search notes --thread Projects/SGB --type Meeting` |
| `logs` | Find daily logs by thread, date or text. | `search logs --text "join semantics" --since 2026-08-01` |
| `activity` | Rank threads by what happened in a window. | `search activity --since 2026-08-01` |
| `overview` | The whole picture of one thread. | `search overview Projects/SGB` |
| `stream` | Every dated record, merged into one chronology. | `search stream --thread Projects/SGB --kind note,log,hours` |

**Options**

| Option | Effect |
|---|---|
| `--thread <thread>` | Thread name, `Kind/Name`, or wikilink. On `activity`, limits to one thread. |
| `--type <type>` | `notes` only. Note type, e.g. `Meeting`. Case-insensitive. |
| `--text <string>` | Case-insensitive literal match. |
| `--kind <list>` | `stream` only. Comma-separated: `note, log, task, done, hours, payment, thread, person, pending`. Default all. |
| `--today` | `stream` only. Shorthand for `--since` and `--until` today. |
| `--reverse` | `stream` only. Oldest first. |
| `--limit <n>` | Max results. Default 20 on `notes`/`logs`, 5 on `overview`, 100 on `stream`. `0` for all. |
| `--since <YYYY-MM-DD>` | On or after this date. |
| `--until <YYYY-MM-DD>` | On or before this date. |
| `--json` | JSON output. Available on every subcommand. |

**Notes**

- `search` returns pointers, never bodies: a path plus metadata. Open the file yourself to read it.
- Paths are emitted absolute, resolved against `ADULTING_HOME`. Hand them straight to a reader.
- Dates are event dates from a note's frontmatter `timestamp`, not the filename. The filename is used only when the frontmatter date is missing or malformed.
- `search` indexes notes and logs, not hours. Detail written into an hours description cannot be found by `--text`.
- Exit code 1: the thread does not resolve, or `--kind` names an unknown kind.

### `threads`

Creates, lists, shows and deletes thread files.

**When to use it**

- You are starting a new project and need somewhere to hang it.
- You need a client's rate and currency set up before logging time.
- You forget the exact thread name and want to search for it.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | List thread files, open by default. | `threads list SGB` |
| `show` | Show a single thread file. | `threads show Projects/SGB` |
| `new` | Create a thread file. | `threads new --name SGB --kind project --category professional --currency ZAR --rate 2500` |
| `delete` | Permanently delete a thread file. | `threads delete Projects/SGB -y` |

**Options**

| Option | Effect |
|---|---|
| `list <query>` | Optional fuzzy search; ranks results by similarity. |
| `list --all` | Include paused and closed threads. |
| `new --name <name>` | Thread name; skips the prompt. |
| `new --kind project\|process\|topic` | Kind; skips the prompt. |
| `new --category professional\|personal\|voluntary` | Category; skips the prompt. |
| `new --currency <ISO>` | Default currency for `hours`, 3-letter ISO. |
| `new --rate <n>` | Default hourly rate for `hours`. Needs `--currency`. |
| `delete -y` | Skip confirmation. |
| `--json` | JSON output on `list` and `show`. |

**Notes**

- `threads new` prompts interactively for any field you do not pass. Pass `--name`, `--kind` and `--category` to run it without a TTY.
- `threads delete` is permanent. Without `-y` it asks for confirmation, so an agent must pass `-y`.

### `people`

Creates, lists, shows and deletes person files.

**When to use it**

- Someone new joins a project and you want to assign tasks to them.
- You need the exact spelling of a name before setting an assignee.
- A contact is no longer active and you want them out of the default list.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | List person files, open by default. | `people list Arbi` |
| `show` | Show a single person file. | `people show "Riaz Arbi"` |
| `new` | Create a person file. | `people new --name "Riaz Arbi" --category professional` |
| `delete` | Permanently delete a person file. | `people delete "Riaz Arbi" -y` |

**Options**

| Option | Effect |
|---|---|
| `list <query>` | Optional fuzzy search; ranks results by similarity. |
| `list --all` | Include closed people. |
| `new --name <name>` | Full name; skips the prompt. |
| `new --category professional\|personal\|voluntary` | Category; skips the prompt. |
| `delete -y` | Skip confirmation. |
| `--json` | JSON output on `list` and `show`. |

**Notes**

- `people new` prompts interactively for any field you do not pass. Pass `--name` and `--category` to run it without a TTY.
- A person's filename without `.md` is the name `tasks set-assignee` must resolve.

### `hours`

Records time worked against a thread, billable or not.

**When to use it**

- You finished a block of client work and want it on the invoice.
- You want to track unbillable time — reading, exercise, admin — in the same place.
- You need month totals before billing.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Append an entry. | `hours log Projects/SGB "DORA metric validation" -m 180 -d 2026-09-10` |
| `list` | List entries. | `hours list Projects/SGB --since 2026-09-01` |
| `report` | Totals by thread and currency, with unbilled time totalled separately. | `hours report --since 2026-09-01 --until 2026-09-30` |
| `show` | Show one entry. | `hours show a1b2c3d4` |
| `edit` | Change one field of an entry. | `hours edit a1b2c3d4 -m 120` |
| `rm` | Delete an entry. | `hours rm a1b2c3d4 -y` |

**Options**

| Option | Effect |
|---|---|
| `-m, --minutes <n>` | Duration. Default 60. |
| `-r, --rate <n>` | Hourly rate; `0` is unbillable. |
| `-c, --currency <ISO>` | ISO code; defaults to the thread's. Without either, the entry is unbilled. |
| `-d, --date <YYYY-MM-DD>` | Default today. |
| `-t, --time <HH:MM>` | Default now. |
| `log --all` | Interactive mode only: list paused and closed threads too. |
| `edit --description <text>` | Rewrite the entry description. |
| `list/report --since`, `--until` | Inclusive date bounds. |
| `report --thread <thread>` | Limit to one thread. |
| `rm -y` | Skip confirmation. |
| `--json` | JSON output on `list`, `report`, `show`. |

**Notes**

- `hours log` with no thread is interactive. Always pass a thread and description when running without a TTY.
- The description is an invoice line item and is not indexed by `search`. Write the detail in a log line instead.
- `rate` and `currency` are stored on each entry at write time. Changing a thread's defaults never re-prices logged work.
- Every logged entry drops a `REF:` into the buffer, filed under the work's date. This is best-effort: the entry is recorded even if the buffer cannot be written.

### `payments`

Records money received against a thread.

**When to use it**

- A client invoice has been paid.
- You want to know what is billed but not yet received.
- You need a statement of account to send.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Record a receipt. | `payments log Projects/SGB 45000 -d 2026-09-08 -a "FNB Business"` |
| `list` | List payments. | `payments list Projects/SGB --since 2026-01-01` |
| `statement` | Billed vs received, by thread and currency. | `payments statement --thread Projects/SGB` |
| `show` | Show one payment. | `payments show b7c8d9e0` |
| `edit` | Change one field of a payment. | `payments edit b7c8d9e0 --amount 46000` |
| `rm` | Delete a payment. | `payments rm b7c8d9e0 -y` |

**Options**

| Option | Effect |
|---|---|
| `-c, --currency <ISO>` | ISO code; defaults to the thread's. |
| `-d, --date <YYYY-MM-DD>` | Date received. Default today. |
| `-t, --time <HH:MM>` | Default now. |
| `-a, --account <name>` | Which account the money landed in. |
| `-n, --note <text>` | Free-text note. |
| `log --all` | Interactive mode only: list paused and closed threads too. |
| `edit --amount <n>` | Change the amount. |
| `statement --thread <thread>` | Limit to one thread. |
| `statement --as-of <YYYY-MM-DD>` | Statement date; drives aging. Default today. |
| `statement --pdf <path>` | Render a PDF to this path. Requires `--thread`. |
| `list/statement --since`, `--until` | Date bounds. |
| `rm -y` | Skip confirmation. |
| `--json` | JSON output on `list`, `statement`, `show`. |

**Notes**

- `payments log` with no thread is interactive. Always pass a thread and amount when running without a TTY.
- Money received must always name a currency. `payments statement` ignores unbilled hours.
- Amounts must be positive. A refund is not a negative payment.
- Statement PDFs use the thread's `client_*` fields; only `client_name` is required to render one.
- Every payment drops a `REF:` into the buffer, filed under the receipt date. Best-effort.

### `buffer`

Stages captured items, then files them into the daily logs.

**When to use it**

- You have a thought mid-meeting and no time to file it.
- You want to check what is queued before it lands in the logs.
- It is end of day and you want the buffer written out.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `add` | Append an UNKNOWN entry — raw quick-capture. | `buffer add "chase SGB about the auth wall"` |
| `suggest` | Propose a structured `add-*` for raw text; prompt to accept. | `buffer suggest "chase SGB about the auth wall" -y` |
| `add-text` | Append a TEXT entry. | `buffer add-text Projects/SGB "Auth wall still unresolved"` |
| `add-ref` | Append a REF entry. | `buffer add-ref Projects/SGB notes/2026-09-10-14-30-00 "Kickoff meeting"` |
| `add-action` | Append an ACTION entry. Also reachable as `tasks add`. | `buffer add-action Projects/SGB "(Riaz Arbi) Draft scope" --due 2026-09-20` |
| `list` | Show the buffer with line numbers. | `buffer list SGB` |
| `rm` | Remove a single line by line number. | `buffer rm 3` |
| `tend` | Regroup by thread and date, and validate. Idempotent. | `buffer tend` |
| `flush` | Tend, then write to `logs/` and clear the buffer. | `buffer flush` |

**Options**

| Option | Effect |
|---|---|
| `--quiet` | Suppress info output. Global. |
| `suggest -y` | Auto-accept the suggestion without prompting. |
| `add-ref --date <YYYY-MM-DD>` | File under this day instead of today. Use the date the thing happened. |
| `add-action --due <YYYY-MM-DD>` | Due date, applied on flush and ingest. |
| `add-action --scheduled <YYYY-MM-DD>` | Scheduled date. |
| `add-action --priority H\|M\|L` | Priority. |
| `add-action --depends <uuid8>` | 8-char uuid prefix; repeatable. |
| `list <filter>` | Filter the listing. |

**Notes**

- `buffer flush` clears `buffer.md`. Run `buffer tend` first if you want to check it passes.
- UNKNOWN entries are intentionally invalid. `tend` reports them as violations and they block `flush` until you `rm` them and re-add via the matching `add-*` command.
- `buffer suggest` prompts unless you pass `-y`. An agent must pass `-y`.
- Do not edit `buffer.md` directly. Use `tend` to fix things and the `add-*` / `rm` commands for individual entries.
- Exit code 1: empty text or description, a `--date` or `--due` that is not `YYYY-MM-DD`, or a `--depends` that is not 8 hex chars.

### `lint`

Validates vault files against the schemas.

**When to use it**

- Before committing, to check nothing is malformed.
- After hand-editing a note or thread.
- To check one file you just changed.

**Usage**

`lint [<path> ...]`

| Argument | Meaning |
|---|---|
| `paths` | Files to validate. Default: walk the whole vault. |

Examples:

```
lint
lint ~/vault/notes/2026-09-10-14-30-00.md
```

**Options**

| Option | Effect |
|---|---|
| `--schemas <dir>` | Use a different schemas directory. |
| `--quiet` | Exit code only; suppress per-violation output. |

**Notes**

- Read-only. It never changes a file.
- Violations print as `<path>:<line>: <message>`.
- Exit 0 is clean, 1 means violations were found, 2 is a tool-level failure.

### `commit`

Reviews uncommitted vault changes, then stages and commits them.

**When to use it**

- End of a working session, to record what changed.
- Before a flush or a bulk edit, to see the current diff.
- To check what would be committed without committing it.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `review` | Show everything that changed since the last commit. Read-only. | `commit review` |
| `save` | Stage every change in the vault and commit it. | `commit save --message "Log SGB kickoff and September hours"` |

**Options**

| Option | Effect |
|---|---|
| `review --max-file-lines <n>` | Max diff lines shown per file. Default 150. |
| `review --max-lines <n>` | Max lines of output overall. Default 3000. |
| `save --message <text>` | Commit subject. Required. Single line. |
| `save --body <text>` | Commit body. May span multiple lines. |
| `save --dry-run` | Report what would be staged and committed; change nothing. |

**Notes**

- `save` can only add a commit. It never amends, rebases, resets, checks out or pushes. The only mutating git calls are `git add` and `git commit`.
- Run `review` first and write the message from what you actually see.
- Exit code 1: `--message` is empty or spans more than one line, `ADULTING_HOME` is not a directory, `ADULTING_HOME` is not the root of its git repository, or a git call fails.

## Everyday procedures

### 1. Set up a new billable project

1. `people new --name "Igor Novak" --category professional` — create the person file for the client contact.
2. `threads new --name "AXA DORA" --kind project --category professional --currency ZAR --rate 2500` — create the thread with billing defaults.
3. `threads show Projects/"AXA DORA"` — confirm the fields landed.
4. `lint` — check the new files validate.

### 2. Capture a meeting and turn its actions into tracked tasks

1. `notes new` — create the meeting note and open it. **Interactive; TTY only.**
2. Write the body, using `ACTION:` lines for commitments and `AGREED:` / `RESOLVED:` for decisions.
3. `tasks --dry-run` — see which ACTION lines would be ingested.
4. `tasks` — rewrite each ACTION in place as a `TASK:` anchor with a uuid.
5. `tasks list --thread Projects/"AXA DORA"` — confirm the new tasks.
6. `notes minutes` — render minutes with the AGREED/RESOLVED/ACTION summary. **Interactive; TTY only.**

### 3. Quick-capture through the day, then file it

1. `buffer add "chase Igor about the join semantics"` — capture with no thread when you have no time to pick one.
2. `buffer add-text Projects/"AXA DORA" "Join semantics on multi-repo commits still unresolved"` — capture something you can already place.
3. `buffer list` — see what is queued, with line numbers.
4. `buffer tend` — regroup and validate; UNKNOWN entries report as violations.
5. `buffer rm 1` — remove the UNKNOWN line.
6. `buffer add-action Projects/"AXA DORA" "(Igor Novak) Resolve join semantics" --due 2026-09-20` — re-add it with a shape.
7. `buffer flush` — write the entries into the daily logs and clear the buffer.
8. `tasks` — ingest the new ACTION lines from the logs into task anchors.

### 4. Work the task list

1. `tasks next` — the top 5 pending tasks by priority, due and entry.
2. `tasks list --overdue` — anything already past its due date.
3. `tasks show abcd1234` — full detail on one anchor.
4. `tasks set-due abcd1234 2026-09-25` — push the date out.
5. `tasks set-priority abcd1234 H` — raise the priority.
6. `tasks done abcd1234` — flip it to `DONE:` and stamp today as `end:`.

### 5. Log a session of work

1. `hours log Projects/"AXA DORA" "DORA metric validation" -m 180` — record three hours under a short label.
2. `buffer add-text Projects/"AXA DORA" "Validated the SQL detection patterns; join semantics unresolved"` — put the detail where `search` can find it.
3. `buffer flush` — file the log line and the `REF:` the hours entry dropped.
4. `hours list Projects/"AXA DORA" --since 2026-09-01` — check the entries.

### 6. Bill a client for a month's work

1. `hours report --thread Projects/"AXA DORA" --since 2026-09-01 --until 2026-09-30` — totals by currency, unbilled time separate.
2. `hours list Projects/"AXA DORA" --since 2026-09-01 --until 2026-09-30` — read the line items you will invoice.
3. `hours edit a1b2c3d4 --description "DORA metric validation and sign-off"` — fix any line item that reads badly.
4. `payments statement --thread Projects/"AXA DORA" --pdf ~/Downloads/axa-statement.pdf` — render the statement of account.

### 7. Record a payment

1. `payments statement --thread Projects/"AXA DORA"` — see what is billed and what is outstanding.
2. `payments log Projects/"AXA DORA" 45000 -d 2026-09-08 -a "FNB Business" -n "Invoice 2026-014"` — record the receipt.
3. `buffer flush` — file the `REF:` into the thread's log for that day.
4. `payments statement --thread Projects/"AXA DORA"` — confirm the balance moved.

### 8. Check the vault and commit it

1. `buffer tend` — make sure nothing is queued in a broken state.
2. `lint` — validate every file against the schemas; exit 0 means clean.
3. `commit review` — read everything that changed since the last commit.
4. `commit save --dry-run --message "Log AXA DORA September work"` — see what would be staged.
5. `commit save --message "Log AXA DORA September work" --body "Kickoff note, 18h logged, invoice 2026-014 received."` — stage and commit.

## Data formats

`lint` enforces every schema below.

### `hours_file`

Billable and unbillable time for one thread, one file per thread, at `hours/{Projects,Processes,Topics}/<Thread>.md`. The body carries exactly one ` ```simple-time-tracker ` fence containing JSON `{"entries": [...]}`.

Frontmatter:

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to the thread; must resolve to an existing thread file. |
| `currency` | no | Three-letter uppercase ISO code. Absent means the file is not billable. |

Entry object:

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | The description of what was done. The only field the Obsidian plugin renders; an invoice line item. |
| `startTime` | yes | ISO 8601 UTC with milliseconds. |
| `endTime` | yes | Same form; must be at or after `startTime`. |
| `id` | yes | 8 hex chars, unique across the whole vault. |
| `rate` | yes | Per-hour charge. `0` means unbillable and is an ordinary value. |
| `currency` | no | ISO 4217. Absent or null means unbilled. |

Duration is derived from `endTime - startTime`; there is no duration field. `rate` and `currency` are stored per entry so changing thread defaults never re-prices history. The plugin's `subEntries` and `collapsed` keys are valid but unused.

### `log`

A per-thread per-day record of activity, written by `buffer flush`, at `logs/<Kind>/<Name>/<YYYY-MM-DD>.md`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to `Projects/`, `Processes/` or `Topics/`. |
| `date` | yes | The day, `YYYY-MM-DD`. |
| `type` | yes | Always `Log`. |

Body lines: `REF:` a pointer to another vault file, `TEXT:` a free-text observation, `ACTION:` an open item, `TASK:` an ingested item, `DONE:` a completed item. `tasks` ingest treats logs and notes identically. The day is the resolution; sub-day timestamps are not preserved.

### `note_correspondence`

A note recording email, message or letter exchanges. Lives in `notes/`, filename `YYYY-MM-DD-HH-MM-SS.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the correspondence is about. |
| `type` | yes | Always `Correspondence`. |
| `threads` | yes | List of thread wikilinks; each must resolve to a thread file. |
| `timestamp` | yes | When it happened, `YYYY-MM-DD-HH-MM-SS`. |
| `people` | no | List of `[[people/X]]` wikilinks (validated to resolve) or plain strings. |

Body keywords: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:`, `!:`.

### `note_meeting`

A note recording a meeting with one or more counterparties. Lives in `notes/`, filename `YYYY-MM-DD-HH-MM-SS.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the meeting was about. |
| `type` | yes | Always `Meeting`. |
| `threads` | yes | List of thread wikilinks; each must resolve. |
| `timestamp` | yes | When the meeting happened, `YYYY-MM-DD-HH-MM-SS`. |
| `counterparty` | no | The other party. |
| `location` | no | Where it was held. |
| `people` | no | List of `[[people/X]]` wikilinks or plain strings for untracked attendees. |

Body keywords: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:`, `!:`.

### `note_simple`

A note for the bare-shape types, with no type-specific fields. Lives in `notes/`, filename `YYYY-MM-DD-HH-MM-SS.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about. |
| `type` | yes | One of `Workshop`, `Report`, `Log`, `Research`, `Recipe`. |
| `threads` | yes | List of thread wikilinks; each must resolve. |
| `timestamp` | yes | When it happened, `YYYY-MM-DD-HH-MM-SS`. |
| `people` | no | List of wikilinks or plain strings. |

Body keywords: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:`, `!:`.

### `payments_file`

Money received against one thread, one file per thread, at `payments/{Projects,Processes,Topics}/<Thread>.md`. The body carries exactly one ` ```adulting-payments ` fence containing JSON `{"payments": [...]}`.

Frontmatter:

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to the thread; must resolve. |
| `currency` | yes | Three-letter uppercase ISO code. |

Payment object:

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | 8 hex chars, unique across the whole vault. Shares one namespace with `hours` ids. |
| `received` | yes | ISO 8601 UTC with milliseconds — the date the money landed. |
| `amount` | yes | Must be greater than zero. |
| `currency` | yes | ISO 4217. |
| `account` | no | Which account the money landed in. |
| `note` | no | Free text. |

Amounts are stored as JSON numbers but computed with `Decimal`. A refund is not a negative payment.

### `person`

A markdown file for someone you track. Lives in `people/`. People are link targets for `note.people` and task assignees; they cannot be the value of a note's thread.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | Date, `YYYY-MM-DD`. |
| `ended` | no | Date. Required when `status` is `closed`. |
| `cadences` | no | List of `{key, frequency, description}`. |

Body is free-form.

### `task_anchor`

A single `TASK:` or `DONE:` line inside a note or log. The vault's source of truth for task state; written and mutated only by `tasks`.

| Field | Required | Meaning |
|---|---|---|
| `kind` | yes | `TASK` or `DONE`. |
| `priority` | no | `H`, `M` or `L`. Lives in the visible `[#X]` token, never in the attrs comment. |
| `assignee` | no | Must resolve to `people/<name>.md`. |
| `body` | yes | The description. |
| `uuid` | yes | 8 hex chars, unique across the vault. |
| `entry` | yes | The ingest date. |
| `end` | no | The completion date. Required when `kind` is `DONE`; must be at or after `entry`. |
| `due` | no | Due date. |
| `scheduled` | no | Scheduled date. |
| `depends` | no | Comma-separated uuids. Each must resolve to another anchor, and the graph must be acyclic. |

Example lines:

```
TASK: [#H] (Riaz Arbi) Send quarterly report <!--abcd1234 entry:2026-05-27 due:2026-05-29-->
TASK: Pick up dry cleaning <!--ef567890 entry:2026-05-27-->
DONE: [#M] (Charlie) Review the contract <!--abc12340 entry:2026-05-24 end:2026-05-27-->
```

Attrs order in the comment is fixed: `entry`, `end`, `due`, `scheduled`, `depends`. The comment is hidden in Obsidian preview.

### `thread`

A markdown file for one project, process or topic. Lives in `threads/`.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `kind` | yes | `project`, `process` or `topic`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | Date, `YYYY-MM-DD`. |
| `ended` | no | Date. Required when `status` is `closed`. |
| `cadences` | no | List of `{key, frequency, description}`; `frequency` is an interval in days. |
| `currency` | no | Three-letter uppercase ISO code; the default `hours` applies. |
| `rate` | no | Default hourly rate. Falls back to `.adulting/config.yaml` `time.rate`, then 2500. |
| `client_name` | no | The party billed on a statement. Required to render a statement PDF. |
| `client_address` | no | Pipe-separated, e.g. `Unit 301\|2 Park Road\|Cape Town`. |
| `client_vat` | no | Client VAT number. |
| `client_email` | no | Client email. |

Body lines are dated bullets conforming to `thread_entry`, plus optional indented sub-bullets and `#<cadence_key>` tags. Supplier and banking details are vault-wide, in `.adulting/config.yaml` under `billing:`. The payment reference printed on a statement is the thread name without its `Kind/` prefix.

### `thread_entry`

A single dated bullet at the top level of a thread file's body.

| Field | Required | Meaning |
|---|---|---|
| `date` | yes | The entry date, `YYYY-MM-DD`. |
| `text` | yes | What happened; at least one character. |

Indented sub-bullets are continuation detail and are not separately validated. Out-of-order dates are tolerated.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `buffer tend` reports violations and `flush` refuses | UNKNOWN entries are intentionally invalid and block the flush. | `buffer list`, then `buffer rm <line>` and re-add with `buffer add-text`, `add-ref` or `add-action`. |
| `buffer add-action` exits 1 with a date complaint | `--due` or `--date` is not `YYYY-MM-DD`. | Re-run with a full ISO date. |
| `buffer add-action` exits 1 on `--depends` | The value is not 8 hex characters. | Pass the 8-char uuid prefix, e.g. `abcd1234`. |
| `tasks` exits 1 saying the uuid prefix is ambiguous | More than one anchor matches that prefix. | Pass more characters of the uuid; `tasks list` shows them. |
| `tasks set-assignee` exits 1 | The name does not resolve to `people/<name>.md`. | `people list` to get the exact name, or `people new --name <name> --category <cat>`. |
| `tasks add-depends` exits 1 saying a task cannot depend on itself | The uuid and dep uuid resolve to the same anchor. | Pass a different dependency uuid. |
| `search` exits 1 saying it could not resolve a thread | The thread argument does not match a thread file. | `threads list --all <query>` to find the exact `Kind/Name`. |
| `search stream` exits 1 on unknown kinds | `--kind` names something outside the allowed set. | Use `note, log, task, done, hours, payment, thread, person, pending`. |
| An hours entry is written with no currency | Neither `-c` nor a thread `currency` was available. | Set `currency` on the thread, or pass `-c <ISO>` on the entry. |
| Detail you wrote in an hours description cannot be found | `search` indexes notes and logs, not hours. | Put the detail in a log line via `buffer add-text`. |
| `lint` exits 1 | A file violates a schema. | Read the `<path>:<line>: <message>` output and fix the file. |
| `commit save` exits 1 complaining about `ADULTING_HOME` | It is not a directory, or not the root of its git repository. | Point `ADULTING_HOME` at the vault root, which must be the git top level. |
| `commit save` exits 1 on the message | `--message` is empty or spans more than one line. | Use a single-line `--message` and put detail in `--body`. |
| `payments statement --pdf` will not run | `--pdf` requires `--thread`. | Add `--thread <Kind/Name>`. |
| `notes pdf` fails to render | `pandoc` or `xelatex` is missing. | Install pandoc and a LaTeX engine. |

## Quick reference

| Command | Does |
|---|---|
| `tasks` | Ingest ACTION lines into TASK anchors, in place. |
| `tasks add` | Buffer-append a structured ACTION. |
| `tasks done` | Mark a task complete and stamp the end date. |
| `tasks set-description` | Rewrite a task body. |
| `tasks set-assignee` | Change who owns a task. |
| `tasks set-due` | Set a due date. |
| `tasks set-scheduled` | Set a scheduled date. |
| `tasks set-priority` | Set priority H, M or L. |
| `tasks add-depends` | Add a dependency. |
| `tasks rm-depends` | Remove a dependency. |
| `tasks list` | List pending tasks. |
| `tasks next` | Top 5 pending tasks. |
| `tasks show` | Detail view of one task. |
| `notes new` | Create a note (interactive). |
| `notes copy` | Copy a note to a new timestamp (interactive). |
| `notes strip` | Copy a note without its body (interactive). |
| `notes edit` | Open a note in the default editor (interactive). |
| `notes nano` | Open a note in nano (interactive). |
| `notes last` | Open the most recent note. |
| `notes delete` | Permanently delete a note (interactive). |
| `notes cat` | Print a note to stdout (interactive). |
| `notes pdf` | Render a note as PDF and markdown (interactive). |
| `notes minutes` | Render meeting minutes (interactive). |
| `notes agenda` | Render a meeting agenda (interactive). |
| `search notes` | Find notes by thread, type, date or text. |
| `search logs` | Find daily logs by thread, date or text. |
| `search activity` | Rank threads by activity in a window. |
| `search overview` | Whole picture of one thread. |
| `search stream` | Every dated record in one chronology. |
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
| `hours report` | Totals by thread and currency. |
| `hours show` | Show one time entry. |
| `hours edit` | Change one field of a time entry. |
| `hours rm` | Delete a time entry. |
| `payments log` | Record money received. |
| `payments list` | List payments. |
| `payments statement` | Billed vs received, by thread and currency. |
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
| `buffer flush` | Write the buffer to logs and clear it. |
| `lint` | Validate vault files against the schemas. |
| `commit review` | Show everything changed since the last commit. |
| `commit save` | Stage every change and commit it. |
