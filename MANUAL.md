# adulting — Operators Manual

## Before you start

Your data lives in one directory. The default is `~/vault/`. Set `ADULTING_HOME` to point the tools at a different vault:

```
export ADULTING_HOME=/path/to/vault
```

Everything under it is plain text: markdown files with YAML frontmatter, JSON inside fenced blocks. You can read, grep, diff and back up the vault yourself. Tooling state lives in the hidden `.adulting/` directory, alongside `.obsidian/`.

External programs the tools need:

| Program | Needed by |
|---|---|
| `bash`, `python3`, `awk`, `sed`, `grep` | everything |
| `pandoc` plus a LaTeX engine (`xelatex`) | `notes pdf`, `notes minutes`, `notes agenda` |
| `open` (macOS) or `xdg-open` (Linux) | launching Obsidian to edit notes |

No Python packages are required beyond the standard library.

## How the pieces fit

| Object | What it is | Where it lives |
|---|---|---|
| Note | A document: meeting, correspondence, report, research | `notes/` |
| Thread | The organising lens — a project, process or topic | `threads/{Projects,Processes,Topics}/` |
| Person | A contact you track; a link target, never a thread | `people/` |
| Log | One thread's activity for one day | `logs/<Kind>/<Name>/<YYYY-MM-DD>.md` |
| Time entry | A session of work on a thread, billable or not | `hours/{Projects,Processes,Topics}/` |
| Payment | Money received against a thread | `payments/{Projects,Processes,Topics}/` |
| Action / task | An `ACTION:` line, ingested into a `TASK:` anchor | inside notes and logs |
| Buffer | The quick-capture inbox | `buffer.md` |

Relationships that matter:

- A note names one or more threads in `threads:`, and may name people in `people:`.
- A time entry and a payment each belong to exactly one thread. Their files mirror the `threads/` layout, so thread name gives file path.
- A thread may carry `currency` and `rate`. Those are the defaults `hours` applies. A thread with no currency is not billable.
- A thread may carry `client_*` fields. Those name the party billed on a statement.
- An `ACTION:` line lives in a note or log. `tasks` rewrites it in place into a `TASK:` anchor with an 8-char uuid. Source files are the only store.
- A task's assignee must resolve to a file in `people/`.
- `buffer flush` writes buffer lines into `logs/`. `notes new`, `hours log` and `payments log` each drop a `REF:` into the buffer, so the day's log points at everything that touched the thread.

## Command reference

### `tasks`

Bridges `ACTION:` lines in notes and logs into anchored `TASK:` lines, and mutates those anchors.

**When to use it**

- You wrote `ACTION:` lines in a note and want them tracked.
- You finished something and want it marked done.
- You want to see what to work on next.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| *(none)* | Ingest every `ACTION:` line into a `TASK:` anchor | `tasks` |
| `add` | Buffer-append a structured ACTION | `tasks add Projects/SGB "(Riaz Arbi) Send the draft" --due 2026-06-01` |
| `done` | Flip source `TASK:` to `DONE:`; stamp `end:` | `tasks done abcd1234` |
| `set-description` | Rewrite the body | `tasks set-description abcd1234 "Send the signed draft"` |
| `set-assignee` | Rewrite the `(Assignee)` prefix | `tasks set-assignee abcd1234 "Riaz Arbi"` |
| `set-due` | Set the due date | `tasks set-due abcd1234 2026-06-05` |
| `set-scheduled` | Set the scheduled date | `tasks set-scheduled abcd1234 2026-06-02` |
| `set-priority` | Set priority `H`, `M` or `L` | `tasks set-priority abcd1234 H` |
| `add-depends` | Add a dependency | `tasks add-depends abcd1234 ef567890` |
| `rm-depends` | Remove a dependency | `tasks rm-depends abcd1234 ef567890` |
| `list` | List pending tasks | `tasks list --priority H --overdue` |
| `next` | Top 5 pending by priority, due, entry | `tasks next` |
| `show` | Detail view of one anchor | `tasks show abcd1234` |

**Options**

| Option | Effect |
|---|---|
| `--dry-run` | Default invocation only. Show what would be ingested; write nothing. |
| `--quiet` | Default invocation only. Suppress per-action output. |
| `add --due <YYYY-MM-DD>` | Due date. |
| `add --scheduled <YYYY-MM-DD>` | Scheduled date. |
| `add --priority {H,M,L}` | Priority. |
| `add --depends <uuid8>` | 8-char uuid prefix. Repeatable. |
| `list --priority {H,M,L}` | Filter to one priority. |
| `list --thread <Kind/Name>` | Filter to tasks whose source note carries this thread. |
| `list --assignee <person>` | Filter to one assignee. |
| `list --overdue` | Only tasks due before today. |

**Notes**

- The bare `tasks` invocation rewrites source notes and logs in place. Run `tasks --dry-run` first if you want to see the effect.
- Do not write `TASK:` lines by hand. `tasks` owns them.
- Exit code 1: empty description, a task depending on itself, no task matching the uuid prefix, an ambiguous uuid prefix, or an assignee that does not resolve to `people/<person>.md`.

### `notes`

Creates, renders, edits and deletes notes.

**When to use it**

- You need to write up a meeting.
- You want a PDF, minutes or an agenda from an existing note.
- You want to reopen the note you just wrote.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `new` | Create a note and open it. Default when no subcommand is given. | `notes new` |
| `copy` | Pick a note, copy its contents to a new timestamp | `notes copy` |
| `strip` | Pick a note, copy it and remove the body, for templating | `notes strip` |
| `edit` | Pick a note, open in the default editor | `notes edit` |
| `nano` | Pick a note, open in nano | `notes nano` |
| `last` | Open the most recently created note | `notes last` |
| `delete` | Pick a note and permanently delete it | `notes delete` |
| `cat` | Pick a note and print it to stdout | `notes cat` |
| `pdf` | Pick a note, render PDF plus markdown | `notes pdf` |
| `minutes` | Pick a note, render minutes: TOC plus AGREED/RESOLVED/ACTION summary | `notes minutes` |
| `agenda` | Pick a note, render an agenda | `notes agenda` |

**Options**

| Option | Effect |
|---|---|
| `<filter>` (second positional) | Case-insensitive substring filter on the picker list. |

**Notes**

- Every subcommand except `last` opens an interactive picker and reads a selection from stdin. **An agent must never call them.** Only `notes last` is usable without a TTY.
- `notes delete` permanently deletes the selected file.
- Rendered output goes to `$EXPORT_DIR`, default `~/Downloads`.
- Body keywords you can write: `ACTION:`, `AGREED:`, `RESOLVED:`, `!:`. Do not write `TASK:` by hand.
- `pdf`, `minutes` and `agenda` need `pandoc` and `xelatex`.

### `search`

Finds notes and logs, and summarises thread activity.

**When to use it**

- You remember a phrase but not which note holds it.
- You want everything that happened on a thread last month.
- You want to know which threads were busy in a window.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `notes` | Find notes by thread, type, date or text | `search notes --thread Projects/SGB --type Meeting` |
| `logs` | Find daily logs by thread, date or text | `search logs --text "invoice" --since 2026-05-01` |
| `activity` | Rank threads by what happened in a window | `search activity --since 2026-05-01 --until 2026-05-31` |
| `overview` | The whole picture of one thread | `search overview Projects/SGB` |

**Options**

Global to all four subcommands: `--since <YYYY-MM-DD>`, `--until <YYYY-MM-DD>`, `--json`.

| Option | Effect |
|---|---|
| `--thread <Kind/Name>` | Limit to one thread. Accepts a name, `Kind/Name`, or a wikilink. On `overview` the thread is a positional argument instead. |
| `--type <type>` | `notes` only. Note type, case-insensitive. |
| `--text <string>` | Case-insensitive literal. Over topic and body for `notes`, over entry lines for `logs`. |
| `--limit <n>` | Max results. Default 20 for `notes` and `logs`, 0 for all. Default 5 recent items for `overview`. |
| `--since` / `--until` | Bound the date window. |
| `--json` | JSON output. |

**Notes**

- `search` returns pointers, never bodies. Open the file to read it.
- Paths are emitted absolute, resolved against `ADULTING_HOME`.
- Dates are the event date from a note's `timestamp`, not the capture date in the filename. The filename is used only when the frontmatter date is missing or malformed.
- Hours are not indexed. Detail written into a time entry's description cannot be found with `--text`.
- Exit code 1 when a thread argument cannot be resolved.

### `threads`

Manages thread files.

**When to use it**

- You are starting a new project and need somewhere to hang its notes.
- You need a thread's billing defaults or client details.
- You want to see which threads are open.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | List thread files, open by default | `threads list SGB` |
| `show` | Show a single thread file | `threads show Projects/SGB` |
| `new` | Create a thread file | `threads new --name SGB --kind project --category professional --currency ZAR --rate 2500` |
| `delete` | Permanently delete a thread file | `threads delete Projects/SGB -y` |

**Options**

| Option | Effect |
|---|---|
| `list <query>` | Fuzzy search; ranks results by similarity. |
| `list --all` | Include paused and closed threads. |
| `list --json`, `show --json` | JSON output. |
| `new --name <name>` | Thread name; skips the prompt. |
| `new --kind {project,process,topic}` | Thread kind; skips the prompt. |
| `new --category {professional,personal,voluntary}` | Category; skips the prompt. |
| `new --currency <ISO>` | Default currency for `hours`. Three-letter ISO code. |
| `new --rate <n>` | Default hourly rate for `hours`. Needs `--currency`. |
| `delete -y` | Skip confirmation. |

**Notes**

- `threads new` prompts interactively for any field you do not pass. Pass `--name`, `--kind` and `--category` to run it without a TTY.
- `threads delete` permanently removes the file. Without `-y` it asks for confirmation, which needs a TTY.
- A thread with no `currency` is not billable. Its time is recorded as unbilled.

### `people`

Manages person files.

**When to use it**

- You need an assignee for a task and the person has no file yet.
- You want to link a note to an attendee.
- You want to check who you track.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | List person files, open by default | `people list Arbi` |
| `show` | Show a single person file | `people show "Riaz Arbi"` |
| `new` | Create a person file | `people new --name "Riaz Arbi" --category professional` |
| `delete` | Permanently delete a person file | `people delete "Riaz Arbi" -y` |

**Options**

| Option | Effect |
|---|---|
| `list <query>` | Fuzzy search; ranks results by similarity. |
| `list --all` | Include closed people. |
| `list --json`, `show --json` | JSON output. |
| `new --name <full name>` | Full name; skips the prompt. |
| `new --category {professional,personal,voluntary}` | Category; skips the prompt. |
| `delete -y` | Skip confirmation. |

**Notes**

- `people new` prompts interactively for any field you do not pass.
- A person is a link target, never a thread. `note.thread` cannot name a person.
- `show` and `delete` take the full name, matching the filename without `.md`.

### `hours`

Records time worked against a thread, billable or not.

**When to use it**

- You just finished a block of client work.
- You want a month's totals before invoicing.
- You mistyped a duration and need to correct it.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Append an entry | `hours log Projects/SGB "DORA metric validation" -m 180` |
| `list` | List entries | `hours list Projects/SGB --since 2026-05-01 --until 2026-05-31` |
| `report` | Totals by thread and currency | `hours report --thread Projects/SGB --since 2026-05-01` |
| `show` | Show one entry | `hours show a1b2c3d4` |
| `edit` | Change one field of an entry | `hours edit a1b2c3d4 -m 120` |
| `rm` | Delete an entry | `hours rm a1b2c3d4 -y` |

**Options**

| Option | Effect |
|---|---|
| `-m, --minutes <n>` | Duration. Default 60. |
| `-r, --rate <n>` | Hourly rate. `0` means unbillable. |
| `-c, --currency <ISO>` | ISO code. Defaults to the thread's. Without either, the entry is recorded as unbilled. |
| `-d, --date <YYYY-MM-DD>` | Date of work. Default today. |
| `-t, --time <HH:MM>` | Start time. Default now. |
| `log --all` | Interactive mode only: list paused and closed threads too. |
| `list --since` / `--until` | Inclusive date bounds. |
| `report --thread <Kind/Name>` | Limit the report to one thread. |
| `report --since` / `--until` | Bound the report window. |
| `--json` | JSON output on `list`, `report` and `show`. |
| `edit --description <text>` | Rewrite the entry description. |
| `rm -y` | Skip confirmation. |

**Notes**

- `hours log` with no thread is interactive. Always pass a thread when running without a TTY.
- `rate` and `currency` are resolved at write time and stored on each entry. Changing a thread's defaults never re-prices logged work.
- Time on a thread with no currency totals under an `unbilled` row in `report`, and `payments statement` ignores it.
- The description is an invoice line item, and is not indexed by `search`. Put the narrative in a log line.
- Each logged entry drops a `REF:` into the buffer, filed under the date the work happened. This is best-effort: the entry is recorded whether or not the buffer can be written.
- `hours rm` deletes the entry.

### `payments`

Records money received against a thread and reports billed versus received.

**When to use it**

- A client's transfer has landed.
- You need a statement of account to send.
- You want to know what is still outstanding.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `log` | Record a receipt | `payments log Projects/SGB 15000 -d 2026-06-03 -a "Business Current"` |
| `list` | List payments | `payments list Projects/SGB --since 2026-01-01` |
| `statement` | Billed vs received, by thread and currency | `payments statement --thread Projects/SGB --as-of 2026-06-30` |
| `show` | Show one payment | `payments show 9f8e7d6c` |
| `edit` | Change one field of a payment | `payments edit 9f8e7d6c --amount 16000` |
| `rm` | Delete a payment | `payments rm 9f8e7d6c -y` |

**Options**

| Option | Effect |
|---|---|
| `-c, --currency <ISO>` | ISO code. Defaults to the thread's. |
| `-d, --date <YYYY-MM-DD>` | Date received. Default today. |
| `-t, --time <HH:MM>` | Time received. Default now. |
| `-a, --account <name>` | Which account the money landed in. |
| `-n, --note <text>` | Free-text note. |
| `log --all` | Interactive mode only: list paused and closed threads too. |
| `list --since` / `--until` | Bound the listing. |
| `statement --thread <Kind/Name>` | Limit the statement to one thread. |
| `statement --since` / `--until` | Bound the statement window. |
| `statement --as-of <YYYY-MM-DD>` | Statement date; drives aging. Default today. |
| `statement --pdf <path>` | Render a PDF to this path. Requires `--thread`. |
| `--json` | JSON output on `list`, `statement` and `show`. |
| `edit --amount <n>` | Change the amount. |
| `rm -y` | Skip confirmation. |

**Notes**

- `payments log` with no thread is interactive. Always pass a thread and amount when running without a TTY.
- Money received must always name a currency. There is no unbilled case here.
- Amounts must be positive. There is no negative payment.
- `statement --pdf` renders the thread's `client_name` as the billed party. The payment reference printed is the thread name without its `Kind/` prefix.
- Each payment drops a `REF:` into the buffer, filed under the date received. Best-effort, as with `hours`.

### `buffer`

Stages captured items in `buffer.md` and flushes them into daily logs.

**When to use it**

- You have a thought mid-meeting and no time to file it.
- You want to check what is queued before it lands in logs.
- You are ready to write the day's captures into `logs/`.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `add` | Append an UNKNOWN entry for later conversion | `buffer add "chase the SGB invoice"` |
| `suggest` | Propose a structured `add-*` for raw text | `buffer suggest "chase the SGB invoice" -y` |
| `add-text` | Append a TEXT entry | `buffer add-text Projects/SGB "Join semantics still unresolved"` |
| `add-ref` | Append a REF entry | `buffer add-ref Projects/SGB notes/2026-06-01-14-30-00 "Vendor decision"` |
| `add-action` | Append an ACTION entry | `buffer add-action Projects/SGB "(Riaz Arbi) Send the draft" --priority H` |
| `list` | Show the buffer with line numbers | `buffer list SGB` |
| `rm` | Remove one line by number | `buffer rm 3` |
| `tend` | Regroup by thread and date, then validate | `buffer tend` |
| `flush` | Tend, write to `logs/`, clear the buffer | `buffer flush` |

**Options**

| Option | Effect |
|---|---|
| `--quiet` | Global. Suppress info output. |
| `suggest -y` | Auto-accept the suggestion without prompting. |
| `add-ref --date <YYYY-MM-DD>` | File under this day instead of today. Use the date the thing happened. |
| `add-action --due <YYYY-MM-DD>` | Due date, applied on flush and ingest. |
| `add-action --scheduled <YYYY-MM-DD>` | Scheduled date. |
| `add-action --priority {H,M,L}` | Priority. |
| `add-action --depends <uuid8>` | 8-char uuid prefix. Repeatable. |
| `list <filter>` | Filter the listing. |

**Notes**

- `buffer suggest` prompts for accept or reject. Pass `-y` to run it without a TTY.
- `UNKNOWN` entries are intentionally invalid. `tend` reports them as violations, which blocks `flush` until you remove them and re-add them with the matching `add-*` command.
- `buffer flush` writes to `logs/` and empties `buffer.md`. It is the only buffer command that clears state.
- Do not edit `buffer.md` by hand. Use `tend` to fix grouping and the `add-*`/`rm` commands for individual entries.
- Exit code 1: empty text or description, an empty description after an assignee, a `--date` or `--due` that is not `YYYY-MM-DD`, or a `--depends` that is not 8 hex characters.

### `lint`

Validates vault files against the schemas.

**When to use it**

- Before committing, to catch a malformed note.
- After hand-editing frontmatter.
- To check one file you just wrote.

**Usage**

```
lint [<path> ...]
```

| Argument | Meaning |
|---|---|
| `paths` | Files to validate. With none, walks the whole vault. |

**Options**

| Option | Effect |
|---|---|
| `--schemas <dir>` | Use a different schemas directory. |
| `--quiet` | Suppress per-violation output; exit code only. |

**Notes**

- Violations print as `<path>:<line>: <message>`.
- Exit 0 if clean, 1 if any violations, 2 on a tool-level failure.
- `lint` enforces cross-file rules the schemas cannot express: uuid uniqueness across the vault, assignee and thread resolution, and an acyclic `depends` graph.

### `commit`

Reviews uncommitted vault changes, then stages and commits them.

**When to use it**

- You finished a session of work and want the vault snapshotted.
- You want to see what changed before writing a message.
- You want a dry run of the commit before making it.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `review` | Show everything changed since the last commit. Read-only. | `commit review` |
| `save` | Stage every change and commit it | `commit save --message "Log SGB work and June payment"` |

**Options**

| Option | Effect |
|---|---|
| `review --max-file-lines <n>` | Max diff lines shown per file. Default 150. |
| `review --max-lines <n>` | Max lines of output overall. Default 3000. |
| `save --message <text>` | Required. Commit subject. Single line. |
| `save --body <text>` | Commit body. May span multiple lines. |
| `save --dry-run` | Report what would be staged and committed; change nothing. |

**Notes**

- `commit save` only ever adds a commit. It never amends, rebases, resets, checks out or pushes.
- Run `review` first, then write `--message` from what you saw.
- Exit code 1: `--message` empty or spanning more than one line, `ADULTING_HOME` not a directory, `ADULTING_HOME` not the root of its git repository, or a failing git call.

## Everyday procedures

### 1. Set up a new billable project

1. `threads new --name SGB --kind project --category professional --currency ZAR --rate 2500` — create the thread with billing defaults.
2. `threads show Projects/SGB` — confirm the fields landed.
3. `people new --name "Igor Petrov" --category professional` — create a file for each person you will assign work to.
4. `lint` — check the new files validate.

### 2. Capture a meeting and turn its actions into tracked tasks

1. `notes new` — **interactive.** Create the meeting note and write the body, using `ACTION:` lines for commitments.
2. `tasks --dry-run` — see which `ACTION:` lines will be ingested.
3. `tasks` — rewrite each `ACTION:` into a `TASK:` anchor in the source file.
4. `tasks list --thread Projects/SGB` — confirm the new tasks.
5. `notes minutes` — **interactive.** Render minutes if you need to circulate them.

### 3. Quick-capture through the day, then file it

1. `buffer add "chase the SGB invoice"` — capture raw when you have no time to pick a thread.
2. `buffer list` — review what is queued, with line numbers.
3. `buffer rm 3` — remove the UNKNOWN line you are about to replace.
4. `buffer add-action Projects/SGB "(Riaz Arbi) Chase the invoice" --due 2026-06-10` — re-add it structured.
5. `buffer tend` — regroup and validate; fix anything it reports.
6. `buffer flush` — write the entries into `logs/` and clear the buffer.
7. `tasks` — ingest the new `ACTION:` lines in the logs into anchors.

### 4. Work the task list

1. `tasks next` — the top 5 pending by priority, due date and entry date.
2. `tasks show abcd1234` — read the detail of one anchor.
3. `tasks set-priority abcd1234 H` — raise the priority if it has moved up.
4. `tasks list --overdue` — see what has slipped past its due date.
5. `tasks done abcd1234` — flip it to `DONE:` and stamp today as the end date.

### 5. Log a session of work

1. `hours log Projects/SGB "DORA metric validation" -m 180 -d 2026-06-01` — record the duration under a short invoice-ready label.
2. `buffer add-text Projects/SGB "Join semantics on multi-repo commits still unresolved" ` — record what actually happened, so `search` can find it.
3. `buffer flush` — file the log line and the entry's `REF:` into the thread's daily log.
4. `hours list Projects/SGB --since 2026-06-01` — confirm the entry.

### 6. Bill a client for a month's work

1. `hours report --thread Projects/SGB --since 2026-06-01 --until 2026-06-30` — totals by currency for the month.
2. `hours list Projects/SGB --since 2026-06-01 --until 2026-06-30` — read the line items you are billing.
3. `hours edit a1b2c3d4 --description "DORA metric validation"` — fix any description that will not read well on an invoice.
4. `threads show Projects/SGB` — check `client_name` and the other `client_*` fields are set.
5. `payments statement --thread Projects/SGB --as-of 2026-06-30 --pdf ~/Downloads/sgb-statement.pdf` — render the statement of account.

### 7. Record a payment

1. `payments log Projects/SGB 15000 -d 2026-07-03 -a "Business Current" -n "June invoice"` — record the receipt under the date the money landed.
2. `buffer flush` — file the payment's `REF:` into the thread's daily log.
3. `payments list Projects/SGB --since 2026-07-01` — confirm it.
4. `payments statement --thread Projects/SGB` — check billed against received.

### 8. Check the vault and commit it

1. `buffer tend` — make sure nothing is queued invalid.
2. `lint` — validate every file; fix anything printed as `<path>:<line>: <message>`.
3. `commit review` — read everything that changed since the last commit.
4. `commit save --dry-run --message "June SGB work"` — see what would be staged.
5. `commit save --message "Log June SGB work and record the June payment"` — stage and commit.

## Data formats

`lint` enforces every schema below.

### `hours_file`

Time logged against one thread. One file per thread at `~/vault/hours/{Projects,Processes,Topics}/<Thread>.md`. The body holds exactly one ` ```simple-time-tracker ` fenced block containing JSON `{"entries": [...]}`.

Frontmatter fields:

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to the thread; must resolve to a thread file. |
| `currency` | no | Three-letter ISO code. Absent means the file is not billable. |

Entry object fields:

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | The description — what was done. An invoice line item. |
| `startTime` | yes | ISO 8601 UTC. |
| `endTime` | yes | ISO 8601 UTC; must be at or after `startTime`. |
| `id` | yes | 8 hex chars, unique across the whole vault. |
| `rate` | yes | Per-hour charge. `0` means unbillable and is an ordinary value. |
| `currency` | no | ISO 4217 code. Absent or null means unbilled. |

Duration is derived from `endTime` minus `startTime`; there is no duration field. The plugin's `subEntries` and `collapsed` keys are valid but unused.

### `log`

One thread's activity for one day, written by `buffer flush`. Lives at `~/vault/logs/<Kind>/<Name>/<YYYY-MM-DD>.md`.

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to `Projects/`, `Processes/` or `Topics/`. |
| `date` | yes | The day, `YYYY-MM-DD`. |
| `type` | yes | Always `Log`. |

Body lines: `REF:` a pointer to another vault file, `TEXT:` a free-text observation, `ACTION:` an open item, `TASK:` an ingested item, `DONE:` a completed item. `tasks` ingest treats logs and notes identically.

### `note_correspondence`

A note recording email, message or letter exchanges. Lives in `~/vault/notes/`, filename `YYYY-MM-DD-HH-MM-SS.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about. |
| `type` | yes | `Correspondence`. |
| `threads` | yes | List of thread wikilinks; each must resolve. |
| `timestamp` | yes | When the exchange happened. |
| `people` | no | List of `[[people/X]]` wikilinks or plain strings. |

Body keywords: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:`, `!:`.

### `note_meeting`

A note recording a meeting. Lives in `~/vault/notes/`, filename `YYYY-MM-DD-HH-MM-SS.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the meeting was about. |
| `type` | yes | `Meeting`. |
| `threads` | yes | List of thread wikilinks; each must resolve. |
| `timestamp` | yes | When the meeting happened. |
| `counterparty` | no | Who you met. |
| `location` | no | Where it happened. |
| `people` | no | List of `[[people/X]]` wikilinks or plain strings. |

Body keywords: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:`, `!:`.

### `note_simple`

A note of any bare-shape type. Lives in `~/vault/notes/`, filename `YYYY-MM-DD-HH-MM-SS.md`.

| Field | Required | Meaning |
|---|---|---|
| `topic` | yes | What the note is about. |
| `type` | yes | One of `Workshop`, `Report`, `Log`, `Research`, `Recipe`. |
| `threads` | yes | List of thread wikilinks; each must resolve. |
| `timestamp` | yes | When the thing happened. |
| `people` | no | List of `[[people/X]]` wikilinks or plain strings. |

Body keywords: `ACTION:`, `TASK:`, `AGREED:`, `RESOLVED:`, `!:`.

### `payments_file`

Money received against one thread. One file per thread at `~/vault/payments/{Projects,Processes,Topics}/<Thread>.md`. The body holds exactly one ` ```adulting-payments ` fenced block containing JSON `{"payments": [...]}`.

Frontmatter fields:

| Field | Required | Meaning |
|---|---|---|
| `thread` | yes | Wikilink to the thread; must resolve. |
| `currency` | yes | Three-letter ISO code. |

Payment object fields:

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | 8 hex chars, unique across the whole vault. Shares one namespace with `hours` entry ids. |
| `received` | yes | ISO 8601 UTC; the date the money landed. |
| `amount` | yes | Must be greater than zero. Computed with `Decimal`. |
| `currency` | yes | ISO 4217 code. |
| `account` | no | Which account the money landed in. |
| `note` | no | Free text. |

### `person`

Someone you track. Lives in `~/vault/people/`. People are link targets for `note.people` and task assignees; they can never be a thread.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | Date you started tracking them. |
| `ended` | no | Required when `status` is `closed`. |
| `cadences` | no | List of `{key, frequency, description}`. |

The body is free-form.

### `task_anchor`

A single `TASK:` or `DONE:` line inside a note or log. The vault's source of truth for task state. Written and mutated only by `tasks`.

| Field | Required | Meaning |
|---|---|---|
| `kind` | yes | `TASK` or `DONE`. |
| `priority` | no | `H`, `M` or `L`. Lives in the visible `[#X]` token. |
| `assignee` | no | Must resolve to `people/<name>.md`. |
| `body` | yes | The description. |
| `uuid` | yes | 8 hex chars, unique across the vault. |
| `entry` | yes | The ingest date. |
| `end` | no | The completion date. Required when `kind` is `DONE`; must be on or after `entry`. |
| `due` | no | Due date. |
| `scheduled` | no | Scheduled date. |
| `depends` | no | Comma-separated uuids; each must resolve, and the graph must be acyclic. |

Example:

```
TASK: [#H] (Riaz Arbi) Send quarterly report <!--abcd1234 entry:2026-05-27 due:2026-05-29-->
```

Attr order in the comment is fixed: `entry`, `end`, `due`, `scheduled`, `depends`.

### `thread`

The organising lens for notes, hours and payments. Lives in `~/vault/threads/`.

| Field | Required | Meaning |
|---|---|---|
| `status` | yes | `open`, `paused` or `closed`. |
| `kind` | yes | `project`, `process` or `topic`. |
| `category` | yes | `professional`, `personal` or `voluntary`. |
| `started` | yes | Start date. |
| `ended` | no | Required when `status` is `closed`. |
| `cadences` | no | List of `{key, frequency, description}`; `frequency` is an interval in days. |
| `currency` | no | Default currency for `hours`. Three-letter ISO code. |
| `rate` | no | Default hourly rate for `hours`. |
| `client_name` | no | Party billed on a statement. Required to render one. |
| `client_address` | no | Pipe-separated, e.g. `Unit 301\|2 Park Road\|Cape Town`. |
| `client_vat` | no | Client VAT number. |
| `client_email` | no | Client email. |

`rate` falls back to `.adulting/config.yaml`'s `time.rate`, then to 2500. Supplier and banking details are vault-wide and live in `.adulting/config.yaml` under `billing:`. A cadence is satisfied when a log entry tagged `#<key>` is added to the thread.

### `thread_entry`

A single dated bullet at the top level of a thread file's body. Indented sub-bullets are continuation detail and are not separately validated.

| Field | Required | Meaning |
|---|---|---|
| `date` | yes | The entry date, `YYYY-MM-DD`. |
| `text` | yes | The entry text. |

Example:

```
- 2024-06-01 — Vendor decision finalised [[2024-06-01-14-30-00]].
```

Out-of-order dates are tolerated.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `buffer flush` refuses to run | The buffer holds `UNKNOWN` entries, which `tend` reports as violations | `buffer list`, `buffer rm <line>`, then re-add with `buffer add-text`, `add-ref` or `add-action` |
| `tasks done` exits 1 with "no task found with uuid prefix" | The prefix matches no anchor in the vault | Run `tasks list` to find the real uuid |
| `tasks` exits 1 with "uuid prefix is ambiguous" | The prefix matches more than one anchor | Pass more characters of the uuid |
| `tasks set-assignee` exits 1 on the person | No `people/<person>.md` exists | `people new --name "<person>" --category professional`, then retry |
| `tasks add-depends` exits 1 with "a task cannot depend on itself" | The two uuids are the same anchor | Pass the uuid of the other task |
| `buffer add-action` exits 1 on `--depends` | The value is not 8 hex characters | Pass the 8-char uuid prefix exactly |
| `buffer add-ref --date` or `--due` exits 1 | The date is not `YYYY-MM-DD` | Rewrite the date in full ISO form |
| `search` exits 1 with "could not resolve thread" | The thread argument names no file under `threads/` | `threads list --all` to find the correct `Kind/Name` |
| An `hours` entry shows under `unbilled` in `report` | Neither `-c` nor the thread supplied a currency | `hours edit <id> -c <ISO>`, or set `currency` on the thread for future entries |
| `payments statement --pdf` will not render | `--pdf` requires `--thread`, and the thread needs `client_name` | Add `--thread`, and set `client_name` on the thread file |
| `commit save` exits 1 on `--message` | The message is empty or spans more than one line | Put the subject on one line and the detail in `--body` |
| `commit` exits 1 about `ADULTING_HOME` | The vault is not a directory, or is not the root of its git repository | Point `ADULTING_HOME` at the repository root |
| `lint` exits 1 with violations | A file does not match its schema | Fix the file at the printed `<path>:<line>` |
| `notes pdf` fails to produce output | `pandoc` or `xelatex` is missing | Install pandoc and a LaTeX engine |

## Quick reference

| Command | Does |
|---|---|
| `tasks` | Ingest `ACTION:` lines into `TASK:` anchors |
| `tasks add` | Buffer-append a structured ACTION |
| `tasks done` | Mark a task complete |
| `tasks set-description` | Rewrite a task body |
| `tasks set-assignee` | Change a task's assignee |
| `tasks set-due` | Set a task's due date |
| `tasks set-scheduled` | Set a task's scheduled date |
| `tasks set-priority` | Set a task's priority |
| `tasks add-depends` | Add a task dependency |
| `tasks rm-depends` | Remove a task dependency |
| `tasks list` | List pending tasks |
| `tasks next` | Top 5 pending tasks |
| `tasks show` | Detail of one task anchor |
| `notes new` | Create a note (interactive) |
| `notes copy` | Copy a note to a new timestamp (interactive) |
| `notes strip` | Copy a note without its body (interactive) |
| `notes edit` | Edit a note in the default editor (interactive) |
| `notes nano` | Edit a note in nano (interactive) |
| `notes last` | Open the most recent note |
| `notes delete` | Delete a note (interactive) |
| `notes cat` | Print a note to stdout (interactive) |
| `notes pdf` | Render a note to PDF (interactive) |
| `notes minutes` | Render meeting minutes (interactive) |
| `notes agenda` | Render a meeting agenda (interactive) |
| `search notes` | Find notes |
| `search logs` | Find daily logs |
| `search activity` | Rank threads by activity |
| `search overview` | Summarise one thread |
| `threads list` | List threads |
| `threads show` | Show one thread |
| `threads new` | Create a thread |
| `threads delete` | Delete a thread |
| `people list` | List people |
| `people show` | Show one person |
| `people new` | Create a person |
| `people delete` | Delete a person |
| `hours log` | Record time worked |
| `hours list` | List time entries |
| `hours report` | Totals by thread and currency |
| `hours show` | Show one time entry |
| `hours edit` | Change a time entry field |
| `hours rm` | Delete a time entry |
| `payments log` | Record money received |
| `payments list` | List payments |
| `payments statement` | Billed vs received |
| `payments show` | Show one payment |
| `payments edit` | Change a payment field |
| `payments rm` | Delete a payment |
| `buffer add` | Quick-capture raw text |
| `buffer suggest` | Propose a structured capture |
| `buffer add-text` | Queue a TEXT entry |
| `buffer add-ref` | Queue a REF entry |
| `buffer add-action` | Queue an ACTION entry |
| `buffer list` | Show the buffer |
| `buffer rm` | Remove a buffer line |
| `buffer tend` | Regroup and validate the buffer |
| `buffer flush` | Write the buffer into logs |
| `lint` | Validate files against schemas |
| `commit review` | Show uncommitted vault changes |
| `commit save` | Stage and commit the vault |
