# Changelog

Dated entries, newest first. Each header is a unit of work; bullets capture the detail.

## 2026-05-18 - Task backend goes embedded; `ADULTING_HOME` becomes configurable

The task-storage backend is no longer a global system dependency. A private copy of the binary lives inside `ADULTING_HOME` with its own data dir and rcfile, isolated from any other install on the machine. User-facing surfaces (help, skills, docs) stop naming the backend so users and AI agents stop reaching for it directly.

- **`ADULTING_HOME` env var honored across all tools** (default `~/.adulting`). Six Python tools (`tasks`, `buffer`, `threads`, `people`, `lint`) and three bash scripts (`notes`, `notes_pdf`, `notes_minutes`) read it on every invocation; the path was previously hardcoded in nine places (including a literal `/Users/riaz/.adulting/config.yaml` in two of the bash scripts).
- **`tasks install` subcommand** (one-shot setup): copies a backend binary from `PATH` (e.g. one installed via `brew install task`) into `<ADULTING_HOME>/bin/task`, writes a minimal `<ADULTING_HOME>/taskrc` (`data.location` + `confirmation=no`), creates `<ADULTING_HOME>/task-data/`, and applies the `source` UDA. Flags: `--from-path` (override the source binary), `--migrate` (also copy `~/.task/*` into the new data dir; backs up any pre-existing contents; source is left in place), `--force` (overwrite an existing embedded install).
- **`tasks` routes every subprocess call through the embedded binary** with `env={TASKDATA, TASKRC}` set, via new `task_cmd(*args)` / `task_env()` helpers. Old `task_in_path()` / `shutil.which('task')` paths replaced by `task_installed()` (checks for `<ADULTING_HOME>/bin/task`). Behavioral effect: the embedded instance is fully isolated — a different `task` install on the same machine (if any) operates on different state.
- **User-facing strings sanitized**: `tasks --help` no longer mentions taskwarrior by name; `set-priority` / `set-due` / `done` / etc. success lines now print `backend: <uuid8> …`; sync output prints `desc->backend:` / `status->backend:` instead of `->tw:`; `tasks rebuild` warnings say "backend record" / "backend status"; module docstrings updated. Internal code comments retain `tw` shorthand for maintainer context.
- **Docs purged of taskwarrior mentions**: `README.md` (dependency list, body-keyword table, `tasks` section, data-store tree), `INTEGRATIONS.md` (whole "Taskwarrior" section removed — it's no longer an external integration), `agent/skills/footguns.md` (the "Never call `task` directly" rule deleted — there's nothing to call), `agent/skills/task-workflow.md`, `.claude/skills/bugfix/SKILL.md`, all four `schemas/*.md` (action-line meaning updated). `CHANGELOG.md` left as history.
- **README adds a "One-time setup" section** pointing first-time users at `tasks install`.

### Operational events (data migration against `~/.adulting/`, not in this repo)

- Backed up `~/.task/` to `~/.task.backup-20260518-151613/` before any change.
- Ran `./tasks install --migrate` against the live data. New artifacts under `~/.adulting/`: `bin/task` (46MB binary copied from `/opt/homebrew/Cellar/task/3.4.2/bin/task`), `task-data/taskchampion.sqlite3` (1.2MB, full migration of 59 tasks), `taskrc`. Verified end-to-end: `tasks list`, `tasks next`, `tasks set-priority` (then cleared), `tasks --dry-run`.
- Verified isolation: a write through the embedded backend did not mutate `~/.task/` (and vice versa during the test window).
- Deleted `~/.task/` after migration verified.
- `brew uninstall tasksh task` to remove the system binary and the interactive shell wrapper that depended on it. `task` is no longer on `PATH`.
- `~/.task.backup-20260518-151613/` retained as a recovery snapshot.

## 2026-05-08 - Skills and prompt move into the repo; `agent-build` deploys all three

The hand-authored agent content (one prompt file, four skill files) was previously developed in a sandbox `.adulting/` copy inside the repo, then manually copied to live. Now those sources live alongside the project as `agent/prompt/*.md` and `agent/skills/*.md` (version-controlled), and `agent-build` deploys them to the target alongside the generated `tools/*.json`.

- **`agent/prompt/00-role.md`** + **`agent/skills/{buffer-workflow,task-workflow,create-person,footguns}.md`** moved into the repo proper.
- **`agent-build`** extended with `sync_authored()` — for each `*.md` in `agent/prompt/` and `agent/skills/`, write to `<target>/prompt/` and `<target>/skills/`. Files in the target without a corresponding source (e.g. preexisting third-party skills like `evaluate-tools/`) are left alone — no `--delete` semantics.
- **`--check` mode** now covers tools, prompts, and skills; non-zero exit on any drift.
- **Sandbox `.adulting/` removed** from the repo. Was always untracked; the canonical sources now live in `agent/`.
- **`.gitignore` added** for `__pycache__/`, `*.pyc`, `.DS_Store`.

`agent-build --target ~/.adulting/.agent` is now a one-shot deploy: regenerates tool defs from the binaries' `--help-json`, copies prompt + skills verbatim, leaves runtime state (context/cache/livecontext/mailbox) untouched.

## 2026-05-08 - List outputs surface the resolvable name

`threads list` and `people list` previously split the resolvable identifier across two columns (kind + name for threads, just bare name for people), forcing the caller to reconstruct `Kind/Name` or `people/Name` mentally before passing to other commands. Now the list outputs show the resolvable form directly.

- **`threads list`**: `KIND` and `NAME` columns replaced by a single `THREAD` column showing `Kind/Name` (e.g. `Projects/AXA DORA`, `Processes/SGB`, `Topics/Relationships`). Same width budget; less visual clutter.
- **`people list`**: `NAME` column replaced by `PERSON` showing `people/<Full Name>` (the wikilink-resolvable form used in note frontmatter and buffer body references).
- **Fuzzy match** (positional `<query>` arg) now scores against both the bare name and the resolvable form, taking the better of the two. So `AFT` and `Processes/Arbi Family Trust` both resolve; `bern` and `people/Bern Sellmeyer` both resolve.
- **Input flexibility on the receiving side**: `people show / delete` and `tasks set-assignee` strip a leading `people/` prefix from their arg, so callers can copy values directly from `people list` output without having to translate.
- **JSON output** (`--json`) retains the original `kind`, `name` fields for backward compat and adds the new `thread` (or `person`) field with the resolvable form.

## 2026-05-08 - Agent surface: `agent-build`, `--help-json`, auto-ingest on flush

The agent's tool surface is now generated from the binaries themselves, not hand-maintained. Each binary self-describes via `--help-json`; a build script reads those manifests and writes terse tool definitions into `<adulting-home>/.agent/tools/`. Workflow guidance, footguns, and worked examples live in skills (hand-authored markdown). Three layers, each with a clear role: tool descriptions for discovery, skills for judgment, `<tool> --help` for syntax.

- **`_argparse_helpjson.py`**: ~60-line shared module. Walks an argparse parser tree (including subparsers, args, flags, choices) and emits a structured JSON manifest. Each Python tool calls `emit_helpjson_if_requested(parser)` ahead of `parse_args`. `notes` (bash dispatcher) hand-rolls a `--help-json` case branch — small one-time cost.
- **`agent-build`**: introspects the six binaries (`tasks`, `buffer`, `notes`, `threads`, `people`, `lint`), generates `<target>/.agent/tools/<binary>.json` with `command` (absolute path resolved via `which`), terse `description` (subcommand list with one-liners + pointer to `<tool> --help`), and per-tool overrides (`lint` is `read_only: true`). `--target <dir>` sets the output location (default `~/.adulting/.agent`); `--check` mode for CI exits non-zero on drift.
- **Tool argv contract**: `args` is a JSON array of strings — one element per argv entry. Spaces, quotes, apostrophes pass through verbatim with no shell quoting. The runtime change to support this lives in [`riazarbi/agent`](https://github.com/riazarbi/agent); our codebase aligned alongside.

- **`tasks` ingest output now includes the new uuid prefix**: `ingested: <uuid8>  <path>:<line>  <description>`. Lets callers (esp. the agent) parse the new uuid off the flush summary without a follow-up `tasks list`.
- **`buffer flush` now auto-ingests** after writing logs. Action items go from buffered → tw task in one step instead of three. The buffer-as-staging-area semantics still apply for TEXT/REF entries (they don't ingest; they just become log lines). Output is passed through (not silenced) so uuid prefixes appear inline. `notes <subcommand>` continues to invoke `tasks --quiet` as a pre-pass.

- **`threads list` / `people list` filters**: positional `<query>` arg ranks results by similarity to filename (heuristic ladder: exact > startswith > initials-equal > substring > initials-startswith > difflib ratio, threshold 0.3). `--all` flag includes paused/closed entries; default lists only `status: open`. `AFT` resolves to `Arbi Family Trust`, `BS` to `Bern Sellmeyer`, `fam` to FAMCO and Arbi Family Trust, etc.

Agent migration completes the loop: old `task_*.{sh,json}` and `buffer_append.{sh,json}` retired in favour of the six generated tool defs. Workflow knowledge moved out of the always-loaded prompt and into on-demand skills (`task-workflow.md`, `buffer-workflow.md`, `create-person.md`, `footguns.md`); `00-role.md` slimmed down to classification + confirm flow + name/thread resolution + the canonical six-tool list.

## 2026-05-08 - CLI consistency: subcommand style across all top-level tools

Hard-cut rename. Convention now:

1. Top-level: every tool uses subcommands. No primary verb is a `--flag`.
2. Subcommands are single-token, hyphenated for multi-word (`add-text`, `set-description`).
3. Within a subcommand: required args are positional; optional metadata is flagged.
4. Shared global flags (`--quiet`, `--dry-run`) come before the subcommand.

Renames:

| Before                    | After                  |
|---------------------------|------------------------|
| `notes --new`             | `notes new`            |
| `notes --pdf`             | `notes pdf`            |
| `notes --minutes`         | `notes minutes`        |
| `notes --agenda`          | `notes agenda`         |
| `notes --edit` / `--nano` / `--cat` / `--copy` / `--strip` / `--delete` / `--last` | `notes edit` / `nano` / `cat` / `copy` / `strip` / `delete` / `last` |
| `threads --list`          | `threads list`         |
| `threads --show <X>`      | `threads show <X>`     |
| `threads --new`           | `threads new`          |
| `threads --delete <X>`    | `threads delete <X>`   |
| `people --list/--show/--new/--delete` | `people list/show/new/delete` |

`tasks` and `buffer` already followed the new convention; no changes there.

README, INTEGRATIONS.md, and the help text in `notes` updated. No backward-compat shim — old `--flag` invocations now hit the help fallback.

## 2026-05-08 - Multi-threaded notes; capture-time attrs on ACTION

Notes now belong to many threads instead of one. Threads behave like tags: a list of wikilinks in the note's `threads:` frontmatter, each entry resolved against `threads/<Kind>/<Name>.md`. The 1:1 link between a task and its origin is the `source:` UDA (relative path of the note); thread membership is **derived at query time** by reading the source note's `threads:` list. taskwarrior's `project:` is no longer set by ingest.

- **Schemas**: `note_meeting`, `note_correspondence`, `note_simple` swap singular `thread:` (string + regex) → `threads:` (list with per-element regex). `note_simple` also gains `Recipe` as an allowed type.
- **`lint`**: per-list-element constraint application — scalar constraints in a schema's Fields table are now applied to each list entry when the field type is `list`. Schema-declared regex on `threads:` fires alongside the existing wikilink-resolution check.
- **Notes backfill**: 50 existing notes converted from `thread: "[[X]]"` (one line) to `threads:\n  - "[[X]]"` (list with one entry).
- **`tasks` ingest**: stops passing `project:` to `task add`. Validates each entry of the note's `threads:` list. Source UDA carries the relative path (e.g. `notes/2026-05-07-09-15-22` or `logs/Processes/SGB/2026-05-07`), preserving the 1:1 link.
- **`tasks list` / `next` / `show`**: derive `threads:` from the source note via a per-invocation cache. Multi-thread tasks display as `Thread1 +N`. `tasks list --thread <T>` filters on the derived set.
- **taskwarrior backfill**: 273 pending tasks had `project:` cleared; 30 legacy bare-stem `source:` values prefixed with `notes/`. Effect: third-party `task project:X` filters no longer work — query via `tasks list --thread X` instead. (Documented in INTEGRATIONS.md.)
- **Capture-time attrs on ACTION**: `buffer add-action` accepts `--due YYYY-MM-DD`, `--scheduled YYYY-MM-DD`, `--priority H|M|L`, `--depends <uuid8>` (repeatable). Attrs ride along in the buffer line's HTML comment, survive flush into the log line, and are applied to the new tw task at ingest time. Rewrite to `TASK:` strips the attrs comment (engine-plane attrs live in tw from then on). Buffer line shape: `<!--TS [attr:val ...]-->`.
- **`tasks add` delegates** to `buffer add-action`. One canonical write path. Same flag set.
- **`notes_new`**: thread picker is now multi-pick (numeric list with `(done)` sentinel). Emits `threads:` as a list. Buffers one REF entry per chosen thread on creation.
- **`_uuid` bug fix**: ingest's UUID resolution switched from `task <id> _uuid` (a report that filters out `+SCHEDULED` tasks) to `task <id> export` (parses JSON; works regardless of state).
- **Recipe note type** added for procedural notes (cooking, server provisioning, how-to guides). Same shape as Workshop/Report/Log/Research.

Note: validation has always been running on threads; the regex was just hidden in lint Python code rather than declared in the schema. Both layers are now visible: schema declares per-element regex, lint code declares cross-file resolution.

## 2026-05-07 - Buffer ritual: `buffer tend` / `buffer flush` → `logs/`

The buffer is now a structured queue with three line types (ACTION, TEXT, REF), each anchored to a resolvable thread, all manipulated via API only (`buffer add-text` / `add-ref` / `add-action` / `list` / `rm` / `tend` / `flush`). Direct edits to `buffer.md` discouraged.

- **`buffer` script** added. Subcommands enforce validation at write time: thread must resolve to `threads/<Kind>/<Name>.md`; assignees to `people/<Name>.md`; REF targets to a vault file.
- **`buffer tend`** regroups by `(thread, date)`, sorts by timestamp, surfaces violations with line numbers + suggested fix commands. Idempotent — run repeatedly until clean.
- **`buffer flush`** tends, then writes each `(thread, date)` group into `logs/<Kind>/<Name>/<YYYY-MM-DD>.md`. Existing log files are appended to. Buffer is cleared on success. All-or-nothing per flush — violations leave the buffer untouched.
- **`schemas/log.md`** added; `lint` extended to walk `logs/` recursively. Log files have `thread`/`date`/`type:Log` frontmatter and ACTION/TASK/DONE/TEXT/REF lines. ACTION lines in logs are picked up by `tasks` ingest exactly like ACTION lines in notes.
- **`tasks ingest` and `tasks sync` now scan both `notes/` and `logs/`.** New convention: `source:` UDA on tw tasks is the relative path from `~/.adulting/` without `.md` (e.g., `notes/2026-05-07-09-15-22` or `logs/Projects/SGB/2026-05-07`). Existing tasks keep their legacy bare-stem form; new ingests use the new format.
- **`notes_new` hook**: every new note creation now appends a REF entry to the buffer so the note shows up in its thread's daily log.
- **Agent tool `buffer_append` migrated** to call `buffer add-text <thread> <text>`. Takes thread as first positional arg. Updated `.agent/prompt/10-buffer.md` to match.

Older free-text buffer entries dropped (none had actionable residue). The legacy `## TIMESTAMP` heading format is no longer recognized.

Outstanding: the agent's `task_*` tools (`task_add`, `task_done`, `task_modify`, `task_list`, `task_next`, `task_log`) still call taskwarrior directly. Full migration to the `tasks <subcommand>` surface deferred — needs a design conversation about how to attach `due:` / `priority:` at capture time when the task's UUID doesn't exist yet (the action item lives as a buffer line; the tw task only exists post-flush).

## 2026-05-07 - Topic-searchable notes via `aliases:`

- `notes_new`: emits `aliases: ["<topic>"]` alongside `topic:` for every new note. Quoted to survive special characters in topics (colons, brackets).
- One-shot backfill: 50 existing notes had `aliases: [<topic>]` inserted after the `topic:` line. No notes had a pre-existing `aliases:` field, so nothing was skipped.
- Lint untouched (`aliases` is not in any `## Fields` table; lint ignores unknown fields). Still 106 files / 0 violations.

Effect: Obsidian's Quick Switcher (Cmd-O) now matches notes by topic. Typing "sgb" finds `2024-04-29-09-03-15.md` because its alias is "SGB Onboarding". Filenames stay timestamp-only — schemas, parsers, and wikilinks are unchanged.

## 2026-05-07 - Orphan TASK lines anchored, all lint violations cleared

- 2 orphan `TASK:` lines in `2026-04-21-07-32-57.md` (the FAMCO meeting note) anchored to their taskwarrior matches (`d2b9a3fc`, `edf1c1c4`). Source `<!--<uuid8>-->` comments added; `source:2026-04-21-07-32-57` UDA set on both tw tasks. The bidirectional sync in `tasks` then pushed the (post-edit) source descriptions to taskwarrior on the next run, aligning both sides.
- 7 stale `[[John Lewis Experimentation]]` wikilink references rewrote to `[[Projects/John Lewis Experimentation]]` (Obsidian's rename refactor had produced shortest-path wikilinks, which our schema's path-qualified regex rejects).
- 8 closed person/thread files had `ended: 2026-05-07` added (the schema requires `ended:` whenever `status: closed`).
- Lint: 106 files, 0 violations. **Vault is fully clean for the first time since the refactor began.**

New top-level `INTEGRATIONS.md` documents the external applications this codebase works with (taskwarrior, Obsidian, pandoc/xelatex) and the configuration each one needs for the integration to work. Going forward, **CHANGELOG tracks changes to this codebase's source; INTEGRATIONS.md tracks the configuration of external tools we depend on.** Previous CHANGELOG entries that mention external config (Obsidian app.json / types.json edits, taskwarrior UDA setup) won't be retroactively split — the historical record stays as-is, the convention applies forward.

## 2026-05-06 - Agent prompts realigned to current data model

`~/.adulting/.agent/` (operational, outside this repo) updated to match the post-refactor layout. Mechanical find-and-replace plus one schema adjustment:

- `prompt/00-role.md`: people path `~/.adulting/threads/People/` → `~/.adulting/people/`. Threads path expanded to `~/.adulting/threads/{Projects,Processes,Topics}/` with a note that the kind subdirectory is implicit in taskwarrior's `project:` value.
- `prompt/10-buffer.md`: wikilink format updated. `[[People/<Name>]]` → `[[people/<Name>]]` (lowercase to match the directory). `[[Threads/<filename>]]` → `[[Projects/<name>]]` / `[[Processes/<name>]]` / `[[Topics/<name>]]`.
- `prompt/20-tasks.md`: same path updates (assignee resolution against `~/.adulting/people/`, project resolution against the kind-subdirectories).
- `skills/create_person.md`: file path and template updated. Dropped `kind: relationship` from the frontmatter template — the `person.md` schema doesn't include a `kind:` field (kind is reserved for thread files). Added a clarifying note pointing at the schema.

Tools (`tools/*.{json,sh}`) untouched. They wrap taskwarrior CLI directly and were already correct; the path conventions live in the prompts.

## 2026-05-06 - Source as canonical store: TASK/DONE in notes, bidirectional sync, drop export

- `tasks`:
  - **UUID anchor moves to an HTML comment at end-of-line.** Format is now `TASK: <body> <!--<uuid8>-->`. The comment is stripped by Obsidian's reading view and by pandoc, so the rendered text is just `TASK: <body>` — no UUID clutter in the viewer. Source-view and any script reading raw text still see the anchor. The earlier transitional `TASK:<uuid8> <body>` form (UUID as a bare prefix) is gone; everything migrated.
  - **New `DONE:` keyword** as the completed-state counterpart to `TASK:`. Source can carry status directly: `TASK:` (open) and `DONE:` (completed) are the two states the source tracks. taskwarrior's other states (waiting / recurring / deleted) stay tw-internal — they're not surfaced in source.
  - **`cmd_sync_descriptions` replaced by `cmd_sync`** — bidirectional. Description drift: source wins (push body to tw). Status drift: **completed-state-wins** — if either side is done, both converge to done. The user can mark something done by editing source `TASK:` → `DONE:` (next sync runs `task <uuid> done`) OR by `task <id> done` in CLI (next sync flips source `TASK:` → `DONE:`). Reverting a done state requires explicit action on both sides; sync won't unilaterally undo a completion.
  - **`cmd_export` removed** along with all its helpers (`write_view`, `fmt_task_line`, `thread_kind_for_project`, `fmt_tw_date`, `read_owner`, `ACTIONS_DIR`). Per-project / per-person aggregation now lives in taskwarrior CLI (`task project:X list`, `task description.contains:"Chris" list`); per-thread browsing falls out of Obsidian's backlinks panel against the thread file. The source `TASK:`/`DONE:` lines are the canonical store; `~/.adulting/actions/` directory deleted.
  - Imports trimmed (`defaultdict`, `datetime`, `timezone` — all dead after export removal). Net reduction of ~85 lines in the script.
  - `parse_task_line(line)` returns `(state, uuid_prefix, body)` — the single parser used by sync. State is `'open'` or `'done'`; non-anchored lines return `None` (skipped silently).

- `notes_minutes`, `notes_pdf` (action items table extractor):
  - Regex extended to recognise `DONE:` alongside `ACTION:`/`TASK:`. Closed and open items now both surface in the rendered minutes table.
  - HTML comment stripping: `re.sub(r'\s*<!--[^>]*-->\s*', ' ', text)` runs on each line's body before deduping, so the embedded UUID anchors don't leak into rendered descriptions.

### Operational events (data, not in this repo)

- 219 TASK lines migrated from `TASK:<uuid8> <body>` to `TASK: <body> <!--<uuid8>-->` (the transitional bare-prefix form is dead).
- 34 of 36 previously-stragglers got their `source:` UDA + UUID anchor via a smarter backfill that matched on `(project, body-with-assignee-stripped)`. Sync then auto-pushed the post-rewrite assignee names ((SMT)→(Chris Storey), (Bern Ralph)→(Bern Sellmeyer), etc.) from source to taskwarrior. 2 stragglers remain in `2026-04-21-07-32-57.md` (body text edited in source after migration; manual fix needed).
- 191 source TASK lines flipped to `DONE:` for tasks already in `status: completed` in taskwarrior. After this one-shot, source state mirrors taskwarrior state.
- `~/.adulting/actions/` directory deleted; lint count unchanged (it never walked there).

## 2026-05-06 - Taskwarrior export: per-thread / per-person markdown views, source UDA backfill

- `tasks`:
  - New `ensure_uda()` configures taskwarrior's `source` UDA on first run (`task config uda.source.type string` + `uda.source.label "Source note"`, both via `rc.confirmation:no`). Idempotent; checks `task _config` for the UDA before setting. Silent no-op if `task` isn't on PATH.
  - Ingest now passes `source:<note_stem>` to `task add` so every task created via this bridge knows the note it came from.
  - New `cmd_export()` wipes and regenerates `~/.adulting/actions/` from `task export` JSON. Per-project view at `actions/{Projects,Processes,Topics}/<name>.md` (mirrors threads layout); per-assignee view at `actions/People/<Name>.md`. Tasks without `project:` are skipped silently; tasks whose `project:` doesn't match an existing thread file are also skipped silently. Tasks without an `(Assignee)` description prefix are routed to the owner's person view (owner read from `~/.adulting/config.yaml`). Same task appears in both its project view and its assignee view.
  - View format: comment marker on line 1 (`<!-- generated by `tasks` on <isoZ>; do not edit -->`), then `# Actions: [[<thread or person link>]]`, then `## Open` / `## Waiting` / `## Done` sections (only sections with content). Bullets are plain `- ` (no checkbox — section header conveys status; checkboxes would invite hand-edits). No frontmatter on generated files. Lint already skipped the `actions/` subtree (its `discover_files` only walks `notes`, `threads`, `people`).
  - `fmt_task_line(t, omit)` — symmetric formatter. `omit='person'` (used in project views) shows the assignee wikilink and elides the project; `omit='project'` (person views) shows the thread wikilink and elides the person. The dimension that matches the file is always implicit.
  - `fmt_tw_date()` — converts taskwarrior's compact `YYYYMMDDTHHMMSSZ` to `YYYY-MM-DD`. Tolerant of already-dashed input.
  - `datetime.now(timezone.utc)` replaces deprecated `datetime.utcnow()` in the file-header timestamp.
  - Auto-runs on every `tasks` invocation (so the silent `tasks --quiet` from `notes` keeps the views fresh as a side effect of normal note flow). `--dry-run` skips both ingest and export.

### Operational events (data, not in this repo)

- One-shot backfill of `source:` UDA on the 191 SGB tasks ingested earlier. Match strategy: walk every `TASK:` line in source notes, look up by `(project, full_description)` against `task export`, set `source:<note_stem>` on exact-1 matches via `task <uuid> modify`. 185/191 backfilled; 6 missed (drift between source `TASK:` lines and taskwarrior task descriptions, introduced when multi-person assignees were rewritten in source-only earlier). The 6 miss show up in the export views without a `[[notes/...]]` source link; otherwise unaffected.
- 24 view files generated under `~/.adulting/actions/` on first export (12 project / process / topic, 12 person). Wholly regenerated each run.

## 2026-05-06 - Render pipeline overhaul: ACTION/TASK lifecycle, owner-aware action table, EXPORT_DIR

- `notes`:
  - `DOWNLOADS_DIR` renamed to `EXPORT_DIR` throughout (declaration, export, help text). Default value `$HOME/Downloads` unchanged.
  - New `extract_people_list` awk function reads the `people:` YAML list-of-scalars from a note's frontmatter, unwraps `[[people/Name]]` wikilinks, emits one entry per stdout line. Exported alongside `extract_meta` via `export -f` so the renderer helpers can call it without re-defining.
  - The pre-action `actions --update` hook is replaced with `tasks --quiet 2>/dev/null || true`. Taskwarrior is now the source of truth for action state, managed via the `tasks` bridge; the `--actions` subcommand is removed.
  - `Start:` / `End:` timestamp appends in `--last` / `--edit` / `--nano` removed. Time tracking is no longer part of the workflow.
  - Help text rewritten: action keywords listed as `ACTION:` / `TASK:` (replacing the old markdown-checkbox convention `- [ ]` / `- [x]`); export destination described as `$EXPORT_DIR (default ~/Downloads)`.

- `notes_new`: dropped the `# Timesheet` section template and the `Start:` / `End:` timestamp appends. New notes now end with `# Content` plus an open editor.

- `notes_minutes`, `notes_pdf`, `notes_agenda` (shared changes):
  - `DOWNLOADS_DIR` → `EXPORT_DIR`.
  - Removed the per-file `extract_meta` definition; helpers rely on the version exported by `notes`. Each gains an env-var guard (`: "${NOTES_DIR:?...}"`, `: "${EXPORT_DIR:?...}"`) and a function-presence check (`type extract_meta >/dev/null 2>&1 || exit`) so direct invocation fails loudly.
  - The `Print:` timestamp append at start-of-render is gone (parallel to time-tracking removal in `notes_new`).
  - Title page rendering switched from `attendees:` / `participants:` (single semicolon-separated string fields) to the new `people:` YAML list, populated via `extract_people_list`. Heading is "Attendees" by default, "Participants" for Correspondence type.
  - Pandoc invocation now uses `--from=markdown+lists_without_preceding_blankline`. Earlier `gfm`-based variants were dropped — `gfm` doesn't accept `raw_tex` so `\newpage` rendered as literal text. Pandoc's default `markdown` already enables `raw_tex` + `yaml_metadata_block`; the added extension gives Obsidian/CommonMark-style list rendering (lists right after a paragraph) without losing LaTeX passthrough.

- `notes_minutes`, `notes_pdf` (action items table):
  - **Status** column dropped from the rendered table. With the new ACTION/TASK lifecycle the source doesn't track open/done state — taskwarrior does — so a status column would be misleading.
  - Legacy `grep '- \[[ x]\]' | sed ... | sort | uniq` pipeline replaced with an inline Python extractor that recognises both `- [ ] / - [x]` (legacy, with optional 5-char key and `(Assignee)`) and `ACTION: / TASK:` (new, with optional `(Assignee)`). De-duplication via a `seen` set; `LEGACY` / `NEW` `re.compile` patterns.
  - Empty assignees substitute with the vault `owner`, read from `~/.adulting/config.yaml` via a small awk one-liner. PDFs are for distribution; the owner needs to appear by name on actions they own.

### Operational events (data migrations against `~/.adulting/`, not in this repo)

- `~/.adulting/config.yaml` created with `owner: Riaz Arbi`. Bootstrap pattern; future constants extend the same file. `people/Riaz Arbi.md` created so the owner has a person file.
- 191 closed `- [x]` action items in SGB notes ingested into taskwarrior via `task log project:SGB end:<date>` (end-date drawn from `actions_log.json`); source rewritten to `TASK: ...` form.
- 32 multi-person / organisational TASK assignees resolved in source (multi-person → first name; `SGB`/`All` → Ralph van Niekerk; `SMT` → Chris Storey; `FINCO` → Tamaryn Cox; `Alice` → Chris Storey).
- 246 plain-string entries in notes' `people:` lists resolved to `[[people/<name>]]` wikilinks. 19 new person files created across two waves — (a) auto-resolution against existing files / first-name shorthands, (b) user-directed via a `~/.adulting/REVIEW.md` workflow.
- SGB and FAMCO threads recategorised from `professional` to `voluntary` (school governance / parent committee — unpaid external commitments).
- Lint clean: 104 files, 0 violations.
