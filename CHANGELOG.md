# Changelog

Dated entries, newest first. Each header is a unit of work; bullets capture the detail.

## 2026-08-18 - `commit` CLI — review the diff, then stage and commit

The agent had no way to record its own work: the vault syncs by git only, and nothing in the toolset could produce a commit. `commit` closes that with two subcommands used in order — `review` to see what changed since the last commit, `save` to stage it all and commit with a summary of that review. Built so it is structurally incapable of altering history: the only mutating git calls are `git add` and `git commit`, and no caller input reaches git argv anywhere except as the value of `-m`, which git never reinterprets as an option.

- **New `commit` CLI** at the repo root, argparse + `emit_helpjson_if_requested` like every other tool, stdlib only. Resolves the vault the standard way (`ADULTING_HOME`, falling back to `~/vault`) and refuses to run unless that path is the *root* of its git repo — if it were merely a subdirectory, `git add -A` would sweep in files outside the vault.
- **`commit review`** prints three sections: changed paths, the diff of tracked edits (`git diff HEAD`, split per file), and the content of new untracked files. Read-only — verified by asserting `git diff --cached` is empty afterwards.
- **Configurable truncation.** `--max-file-lines` (default 150) and `--max-lines` (default 3000). Both cuts are announced in-band naming the flag that lifts them, so a truncated report never reads as a complete one. The per-file cap is what matters: without it a single 34,986-line ASCII CAD export in `assets/` was 91% of a 38,378-line report and pushed every note and log past the global cap.
- **`commit save --message SUBJECT [--body BODY] [--dry-run]`.** `--message` is a single line — a multi-line value is rejected pointing at `--body`. `--dry-run` reports the paths and message and changes nothing.
- **`git status --porcelain -uall -z`** for every path listing. Without `-uall` git collapses a new directory to `assets/`, so `review` would show one line where `save` commits fifty files; `-z` because note filenames carry spaces and non-ASCII. The `-z` rename form is `XY <new>\0<old>\0` — reversed from the human-readable `R old -> new`.
- **Untracked content via `git diff --no-index -- /dev/null <path>`**, which renders a new file as an add-diff without touching the index. It exits 1 whenever the inputs differ, i.e. always, so a non-zero return is the normal case here rather than an error. Binary files collapse to a one-line notice for free.
- **`-c safe.directory='*'` and `-c core.quotepath=false` on every git invocation**, passed per-command, never written to a config file. The first because the vault is a bind mount git otherwise refuses as "dubious ownership"; the second so non-ASCII note filenames stay readable.
- **stdout/stderr discipline.** All success output on stdout with stderr left completely empty; all errors on stderr with a non-zero exit; subprocess stderr always captured. The agent harness discards stdout whenever stderr is non-empty or the exit code is non-zero. "Nothing to commit" is a success — message on stdout, exit 0.
- **`Dockerfile`: `git` added** to the apt list (~50MB with deps; it was not in the image, so none of this worked until now), plus an explicit `GIT_AUTHOR_NAME`/`GIT_AUTHOR_EMAIL`/`GIT_COMMITTER_NAME`/`GIT_COMMITTER_EMAIL` = `agent <agent@adulting.local>`. The identity must be set explicitly and must cover *both* author and committer: with `HOME=/tmp` there is no gitconfig to read, and git then derives an identity from the container UID and hostname silently, with no error. Setting only `GIT_AUTHOR_*` still leaves the committer auto-derived — confirmed on the host, where an author-only commit recorded `committer=Riaz Arbi <riaz@MacBookPro.lan>`. Needs an image rebuild: `docker compose -f /Users/riaz/vault/docker-compose.yml up -d --build agent`.
- **`agent-build`: `'commit'` added to `TOOLS`.** The tool JSON is generated from `--help-json`, never hand-written; the top-level description spells out the review-then-save order because that description is the only thing the model reads when deciding how to call this. Regenerating writes to `$ADULTING_HOME/.agent/tools/commit.json`, i.e. into the vault, not this repo — a separate step from this change, and it requires `commit` on the host `PATH`.
- **New `tests/test_commit_cli.py`**, 12 tests on a throwaway git repo per test with `ADULTING_HOME` pointed at it. Covers: `--message=--amend` committed as a literal subject that *appends* (commit count up, `HEAD^` unchanged); the space-separated `--message --amend` refused by argparse with nothing staged; `review` read-only and listing both a modified tracked file and a new untracked one; files inside a new directory listed individually; both truncation caps announced; multi-line `--body` round-tripping through `git log -1 --format=%B` with paragraph breaks intact; multi-line `--message` rejected; `save` committing everything; `--dry-run` inert; clean tree exit 0; non-repo `ADULTING_HOME` failing on stderr with empty stdout. Full suite green (75 passed).
- **Not bundled**: no refusal on detached HEAD or a mid-merge/mid-rebase tree — `save` would happily commit either. No `push`, no branch handling, no per-path staging: `save` is all-or-nothing across the vault. `review` does not cap the changed-paths listing itself, only the diff bodies that follow it.

## 2026-06-04 - anchor lines end with a Markdown hard break

Bug fix: ingested `TASK:`/`DONE:` lines ended with `-->` and no trailing whitespace, so pandoc soft-wrapped consecutive anchors into one paragraph and the PDF rendered every task on a single line.

- **`format_anchor` patch**: append two trailing spaces (a Markdown hard line break) to the formatted anchor. `format_anchor` is the single writer, so both ingest and every `tasks` mutation are covered. Round-trips cleanly — `ANCHOR_RE`/`ACTION_RE`, the `schemas/task_anchor.md` `shape` regex, and `lint`'s `TASK_RE` all already tolerate trailing whitespace; `notes_pdf`'s action-table renderer strips the comment with surrounding whitespace, so table cells are unaffected.
- **Regression test** `tests/test_tasks_cli.py::test_ingest_appends_markdown_hard_break`: ingests two actions and asserts each anchor ends with `-->  `. Confirmed failing on the unpatched writer and passing with the fix; the two existing `-->$` assertions were updated to `-->  $`; full suite green (63 passed).
- **Not bundled**: anchors already on disk gain the trailing spaces only on next mutation — there is no reformat/`rebuild` command to backfill old notes.

## 2026-06-03 - `tasks list`/`next` now render the assignee

Bug fix: `tasks next` (and `tasks list`) dropped the assignee from their output. The assignee was parsed and stored on the anchor correctly — `tasks show` printed it — but the shared table renderer never emitted it.

- **`_print_table` patch**: added an `assignee_cell` (`(Name)` when set, blank otherwise) between the thread and body columns, matching the `(assignee)` convention already used by `format_anchor`. Both `list` and `next` route through this one renderer, so both are fixed by the single change. Unassigned tasks leave the column blank; alignment is preserved.
- **Regression test** `tests/test_tasks_cli.py::test_list_renders_assignee`: seeds an assigned and an unassigned task, asserts `(Charlie)` appears in `list` output and the unassigned task still renders. Confirmed failing on the unpatched renderer and passing with the fix; full `tasks` CLI suite green.

## 2026-05-27 - `tasks` source-as-database: taskwarrior backend removed

The taskwarrior sqlite store (`~/vault/.adulting/task-data/taskchampion.sqlite3`) was the canonical engine-plane state. Syncing the vault across machines produced unmergeable binary conflicts. Source notes already carried uuid-anchored `TASK:`/`DONE:` lines as the user-visible state; only six attrs (`entry`, `end`, `due`, `scheduled`, `priority`, `depends`) lived exclusively in the backend. This change lifts those onto the on-disk anchor line and deletes the backend.

PRD/user story: `stories/2026-05-27-tasks-source-as-database.md`.

- **New on-disk anchor shape**, validated by the new `schemas/task_anchor.md` line-scope schema:
  ```
  TASK: [#H] (Assignee) <body> <!--<uuid8> entry:YYYY-MM-DD [end:…] [due:…] [scheduled:…] [depends:<u8>,…]-->
  ```
  Priority lives in the visible `[#X]`, never in attrs. Order is fixed; the writer in `tasks` is the only authority.
- **`schemas/task_anchor.md`** declares every field as a named capture (`kind`, `priority`, `assignee`, `body`, `uuid`, `entry`, `end`, `due`, `scheduled`, `depends`) and reuses the existing scalar constraint DSL — no DSL extension needed.
- **`lint` patch**: per-line conditional rules (`kind=DONE → end required`, `end >= entry`, `assignee → people/<name>.md`) follow the precedent at the prior thread/person hardcode block; new vault-wide pass (uuid uniqueness across the vault, `depends` target resolution, `depends` cycle detection via iterative DFS coloring) runs end-of-run after the file walk.
- **`tasks` rewritten**. All subcommands now read and write the source line directly via a `parse_anchor` / `format_anchor` / `mutate_anchor` triple. The dataclass-based `Anchor` is the single in-memory shape; `walk_anchors()` is the only read path; `find_anchor(prefix)` resolves uuid prefixes via the same walk. File mutations go through `tmp + os.replace` for atomicity. Preserved commands: `add`, `done`, `set-description`, `set-assignee`, `set-due`, `set-scheduled`, `set-priority`, `add-depends`, `rm-depends`, `list`, `next`, `show`, and the default (no-arg) ingest. `list` filter DSL replaced with explicit `--priority` / `--thread` / `--assignee` / `--overdue` flags. `next` sorts by `(priority, due, entry, uuid)` ascending; tw's `urgency` formula is gone (priority weight dominated it anyway).
- **`tasks install`, `tasks migrate-layout`, `tasks rebuild`, `cmd_sync`, `task_cmd`, `task_env`, `tw_modify`, `ensure_uda`, the entire `INTERNAL_DIR / bin` / `TASK_BIN` stanza, the legacy-layout detection, the report-vs-export UUID lookup detour, the noon-shift date hack — all deleted. The `tasks` file shrinks from ~1370 lines to ~530.
- **Migration** ran on the live vault: 308 source anchors rewritten with their tw attrs lifted (4 source anchors had no tw record and got synthesized entry/end; 56 tw records had no source anchor and were logged to `.adulting/migration-orphans.txt`). Source-wins on every field where tw disagreed. Where tw recorded an end date that predated entry (back-dated historical tasks), entry was pulled back to match end so the `end >= entry` invariant holds going forward.
- **`~/vault/.adulting/{bin,task-data,taskrc}` deleted** post-migration (~50 MB freed). The visible `.adulting/` keeps only `config.yaml` and the two migration log files for posterity.
- **New test suite** at `tests/`: 61 tests across smoke, schema, lint cross-vault rules, and per-subcommand functionality (ingest, `done`, every `set-*`, `add`/`rm-depends`, `list` filters, `next` sort order, `show`, full ACTION→TASK→DONE lifecycle, prefix-not-found, prefix-ambiguous, removed subcommands). Runs as subprocess against a temp vault per test via the new `conftest.py` `vault` fixture.
- **Sync model is now git only.** Two machines making concurrent edits to the same TASK line conflict on that line in git — resolvable. Two machines editing different lines/files don't conflict at all.

## 2026-05-25 - `Dockerfile` rewritten for the new distroless agent base

The upstream agent project dropped its bundled llama.cpp backend and switched the container base to `gcr.io/distroless/static-debian12`, taking the image from multi-GB down to ~15 MB. Distroless has no shell and no `apt`, so the prior layering — `FROM agent-offline:local` then `apt-get install python3 taskwarrior` — stops building on first `RUN`. The fix inverts the dependency: pull just the agent binary out of the upstream image and build adulting's runtime on debian-slim, where we control the package set.

- **Multistage `Dockerfile`.** Stage 1 is `FROM agent:local AS agent_bin` (the upstream image tag also renamed from `agent-offline:local`). Stage 2 is `FROM debian:trixie-slim` with `apt-get install python3 taskwarrior ca-certificates`, then `COPY --from=agent_bin /usr/local/bin/agent /usr/local/bin/agent`. `ENTRYPOINT ["/usr/local/bin/agent"]` and `USER 1000:0` carried over, plus the env vars (`AGENT_STATE_DIR=/state`, `HOME=/tmp`) and writable mount-point dirs (`/state`, `/workspace`, chmod 0777) that the upstream distroless image used to provide implicitly.
- **`ca-certificates` added explicitly.** Distroless bakes it in; debian-slim doesn't. Without it the agent's outbound TLS to the LLM API would fail with `x509: certificate signed by unknown authority`.
- **No change to `python3` / `taskwarrior` install** — same package list, same justification (stdlib Python CLIs; `tasks install` copies a Linux `task` binary into `<vault>/.adulting/bin/`).
- **`/opt/adulting` bind-mount unchanged.** The CLI tree still lives on the host and edit-and-rerun continues to work without a rebuild.

### Operational events (compose + upstream image, not in this repo)

- Upstream agent project: `model` + `llama` build stages and every `LLAMA_*` env var removed from `docker/Dockerfile`; runtime base switched to `gcr.io/distroless/static-debian12`; `tini` dropped (Go runtime handles signals as PID 1); image tag default changed from `agent-offline:latest` to `agent:latest`. `docker/entrypoint.sh`, `docs/offline.md`, and `scripts/smoke/docker_offline.sh` deleted. See that repo's changelog for the full entry.
- `/Users/riaz/vault/docker-compose.yml`: `agent-base.image` and `agent` service references retagged `agent-offline:local` → `agent:local`; `env_file: /Users/riaz/vault/.env-agent` added to the `agent` service for `AGENT_API_KEY` / `AGENT_BASE_URL` / `AGENT_MODEL` (mirrors the existing `.env-telegram` pattern, keeps the secret out of the compose file); dead `LLAMA_*` / loopback comments removed.
- `/Users/riaz/vault/.env-agent`: already contained the same `AGENT_API_KEY` / `AGENT_BASE_URL` / `AGENT_MODEL` values as the agent repo's `.env`, with `AGENT_STATE_DIR=/state` and `ADULTING_HOME=/vault` for the container — left unchanged.

## 2026-05-25 - `Dockerfile` — package adulting for the agent container

To let the in-container agent (separate repo; image `agent-offline:local`) drive the vault directly, adulting's CLIs need to be reachable from inside that container with `ADULTING_HOME` pointing at the bind-mounted vault. The new `Dockerfile` here is the layer that gives the upstream agent image those affordances; the rest of the wiring lives in the agent project's compose file and the staging vault's `.agent/` state.

- **New `Dockerfile`** at the repo root, derived `FROM agent-offline:local`. Apt-installs `python3` (CLIs are stdlib-only Python) and `taskwarrior` (so an in-container `tasks install` can copy a working Linux `task` binary into `<vault>/.adulting/bin/`, replacing whatever host-built `task` got rsynced in). Pre-creates `/opt/adulting` as the bind-mount target. Sets `PATH=/opt/adulting:$PATH` and `ADULTING_HOME=/vault`. Drops back to user `1000:0` to match the base image.
- **Bind-mount, not `COPY`.** The repo isn't baked into the image — the agent container mounts the host checkout at `/opt/adulting:ro` at runtime. Edits to a script on the host take effect on the next invocation in the container; no rebuild required.
- **`pandoc` + a LaTeX engine** deliberately omitted. Would add ~1 GB and `notes pdf|minutes|agenda` aren't on the agent's expected paths. Add later if PDF rendering becomes necessary.

### Operational events (compose + vault wiring, not in this repo)

The agent project's compose file (now at `/Users/riaz/vault/docker-compose.yml`, moved from `/Users/riaz/projects/agent/docker-compose.yml`) was updated to consume this Dockerfile:

- New `agent-base` service under a `build` profile that builds `agent-offline:local` from the upstream agent project (so the `FROM` resolves locally). Built once with `docker compose --profile build build agent-base`.
- `agent` service now builds `adulting-agent:local` from this repo's `Dockerfile`, with three bind mounts: `<vault>/.agent:/state` (agent runtime state), `<vault>:/vault` (the obsidian content — `ADULTING_HOME` inside), `~/projects/adulting:/opt/adulting:ro` (the CLI tree). Telegram-bridge and timer services repointed at `<vault>/.agent` and `<vault>/.env`.
- **Tool registrations rewritten.** `<vault>/.agent/tools/{buffer,lint,notes,people,tasks,threads}.json` `"command"` fields changed from the host path `/Users/riaz/bin/adulting/<name>` to bare `<name>`. The agent's shell-tool loader runs `exec.LookPath` at startup and silently drops any tool whose path doesn't resolve — host paths don't exist in the container, so without this fix the tools were never registered with the model. Bare names resolve through container `$PATH`.
- `/Users/riaz/.adulting` rsynced to `/Users/riaz/vault` as a staging copy so the agent can be exercised end-to-end without touching production.

## 2026-05-25 - Default vault root moves from `~/.adulting` to `~/vault`

The vault root was previously a hidden directory (`~/.adulting`), which made it invisible in Finder/most file managers by default and made the "open my vault" muscle memory awkward. The default is now `~/vault`, a plain visible directory. `ADULTING_HOME` continues to override (same env var name, same semantics) — only the fallback changed. The inner hidden `.adulting/` subdir for operational state (introduced 2026-05-19, like `.git`/`.obsidian`) is unchanged.

- **Default fallback in all tools** flipped from `os.path.expanduser('~/.adulting')` to `os.path.expanduser('~/vault')` (Python: `_suggester.py`, `buffer`, `people`, `threads`, `tasks`, `lint`; bash: `notes`, `notes_minutes`, `notes_pdf`). The env-var override pattern is unchanged in every file — `ADULTING_HOME` set in your shell still wins.
- **`agent-build` now honors `ADULTING_HOME`** like every other tool. Previously hardcoded `Path.home() / '.adulting' / '.agent'`, ignoring the env var; now `Path(os.environ.get('ADULTING_HOME', os.path.expanduser('~/vault'))) / '.agent'`. Closes a small consistency gap — "set the var once and all commands respect it" is now actually true.
- **`eval/suggester/score.py`** missing-threads warning resolves its example path through `ADULTING_HOME` instead of hardcoding `~/.adulting/threads`.
- **Docstrings, `--help` text, and inline comments** in the same files updated to quote `~/vault/...` instead of `~/.adulting/...` (e.g. `tasks rebuild`'s backup-path comment, `lint`'s argparse help, the module docstrings on `buffer`/`people`/`threads`).
- **Docs swept**: `README.md`, `INTEGRATIONS.md`, `schemas/*.md` (6 files), `agent/prompt/00-role.md`, `agent/skills/{buffer-workflow,create-person,footguns,task-workflow}.md`, `eval/suggester/eval-v1.md`. Mechanical `~/.adulting/` → `~/vault/` substitution; the inner `.adulting/` subdir references (the operational state dir at `<vault>/.adulting/`) are left intact.
- **README design-goals wording** updated: "Maintain all state under the `~/.adulting/` hidden directory" → "Maintain all state under a single vault directory (default `~/vault/`, override with `ADULTING_HOME`)" — `~/vault` is not hidden, and pinning the default name in the design goal was misleading anyway.
- **`Dockerfile`** unchanged: the in-container `ADULTING_HOME=/vault` was already set; the host path is whatever you bind-mount, so the host-side default is now consistent with the container-side default.
- **`CHANGELOG.md`** unchanged below this entry. The historical `~/.adulting/` references in prior entries are accurate as of when they were written; rewriting history is worse than letting old paths read as "old paths".
- **`.claude/worktrees/python-refactor/**`** unchanged (separate worktree, not part of the main tree).

### Operational events (pending, against `~/.adulting/`, not in this repo)

Code now expects `~/vault`; the actual data is still at `~/.adulting`. Two follow-ups are needed before the new default lights up cleanly:

- `mv ~/.adulting ~/vault` (or set `export ADULTING_HOME=$HOME/.adulting` in your shell rc and leave the data where it is). The `.adulting/` operational subdir inside moves with the rest — no internal restructure required.
- `.claude/settings.local.json` has ~9 hardcoded `/Users/riaz/.adulting/...` permission rules (Read paths, `rm` paths, `agent-build --target` paths). These will stop matching after the data move; update to `/Users/riaz/vault/...` when you do the move, or before if you want to keep auto-approval working during the transition.

## 2026-05-20 - `buffer suggest` — explicit-thread override, month dates, case-insensitive fixes

User testing surfaced two failure modes. The fixable one is now fixed; the other is documented as the rules ceiling.

- **Explicit thread directive.** If the raw text contains a `Kind/Name` reference — trailing `- topics/relationships` or inline `[[Projects/X]]` — the suggester honors it verbatim and skips BM25 ranking entirely (no confidence guard either). The kind is a gate (must be Projects/Processes/Topics, which keeps URL paths like `tech/blogs` from false-matching) but is *not* authoritative for resolution: the NAME is matched against the thread list, so `processes/relationships` correctly resolves to `Topics/Relationships` (users misremember Topic vs Process). The directive and any leading ` - ` separator are stripped from the body. This is the reliable escape hatch for any capture the ranker would otherwise misroute.
- **Month dates.** `parse_dates` now handles `before/by/in/during <month>` → first of that month (`before June` → `2026-06-01`). `before` joins `by` as a `--due` hint (vs `--scheduled`).
- **`have` is now an imperative verb** — "Have a date night…" / "Have lunch with mom" classify as ACTION, not TEXT.
- **Case-insensitivity fixes.** Two downstream steps were silently case-sensitive even though detection wasn't: `detect_assignee` (required a capitalised name) and `build_body`'s wikilink replacement (exact-case match). Lowercase input like `bern called…` or `ralph: sign…` now produces the same structured output as the capitalised form.
- **The rules ceiling, documented.** "Have a date night with Simone before June" (no thread keyword, "Simone" not a known person) still misroutes to SGB. SGB's thread file is ~12× the next-largest thread, making it an unavoidable magnet for keyword-poor inputs — and any ranking knob that suppresses it (frequency cap, higher BM25 `b`) also breaks the legitimate "Symonds → SGB" routing, because SGB is genuinely both the largest thread and the noise sink. Mitigations: the explicit-thread directive above, or rejecting the suggestion (drops to UNKNOWN at no cost). Solving it properly needs semantic understanding ("date night" → Relationships) — i.e. Stage 2 (a local LLM).
- **Eval** extended to 27 cases (cases 26–27 cover explicit-thread routing). Score: 82% full / 82% thread / 100% out-of-scope — still over the Stage 1 ship bar.

## 2026-05-19 - `buffer suggest` — rules-only structured capture from raw text

Closes the loop on UNKNOWN: instead of always parking raw text and tending it later, `buffer suggest "..."` proposes a structured `add-text` / `add-action` / `add-ref` invocation derived from the raw input, prompts to accept or reject, and falls through to UNKNOWN on rejection. Rules only — no LLM dependency, no model artifacts, no network — but reaches 85% full-match accuracy on a hand-curated 25-case eval (100% on out-of-scope rejection, persons, dates, priority). The bar to escalate to a local LLM (cactus/needle) wasn't met; rules are sufficient for the workload.

- **`buffer suggest <text> [-y]`** — runs the rules suggester, prints the proposed command, prompts `accept? [Y/n]`. Accept dispatches to the matching `cmd_add_*` in-process; reject (or non-tty without `--yes`) drops to `buffer add` (UNKNOWN), preserving the raw text for later tending. Empty input rejected at the parser; rejection has zero cost downstream because UNKNOWN already exists as the catch-all.
- **`_suggester.py`** (project root, alongside `_argparse_helpjson.py`) — pure stdlib, no dependencies. Pipeline: tokenize → fuzzy person match (full-name or unambiguous first-name) → date parse (today/tomorrow/weekday/next-week/end-of-week/ISO, with `by <date>` → `--due` and bare date → `--scheduled`) → priority detection (URGENT/ASAP/!!! → H; low/whenever → L) → intent classification (out-of-scope guards first, then REF/TEXT/ACTION by verb position) → BM25 thread ranking with rare-term unique-thread bonus and person-pin boost → body construction (strip date/priority spans, wikilink person references, apply assignee prefix). Confidence guards: bail to UNKNOWN if top thread score < 1.5 or if intent is REF without a resolvable target (REF target resolution is not implemented in v1).
- **Thread ranking** uses BM25 with `k1=1.5`, `b=0.4`. The textbook default `b=0.75` is too aggressive on this vault — historical threads (SGB) have ~20x more content than newer ones (FAMCO), and full-strength length normalization let tiny threads win on rare-term hits. Lower `b` keeps length penalization without inverting it. A `+5` flat bonus is added per query token that appears in exactly one thread (`df == 1`) — captures the "Symonds is uniquely SGB" intuition cheaply.
- **Eval harness** at `eval/suggester/`: `eval-v1.md` (human-readable spec, 20 in-scope + 5 out-of-scope), `eval-v1.jsonl` (machine-readable, scored), `score.py` (per-case + aggregate metrics). Treat as the regression check before tuning the suggester; pass bar is `full ≥70% / thread ≥80% / oos ≥80%`. Current score: 80% / 80% / 100% (single-thread-bonus + BM25 demoted REF-no-target from add-ref to UNKNOWN, dropping subcmd from 100% to 95% — a correctness improvement, not a regression).
- **Remaining failures are intrinsic**: cases like "Call mom tomorrow" → `Topics/Relationships` and "pick up dry cleaning" → `Processes/Toil` have no textual hook the inverted index can grab. Flagged at eval-design time. An LLM wouldn't reliably solve them either because the signal isn't in the input.

## 2026-05-19 - `UNKNOWN` buffer type for shape-later quick capture

Adds a fourth buffer line type for moments when picking a thread or line shape is the wrong cost to pay — the input gets parked as-is and surfaces as a tend violation until it's converted. Lets capture happen at the speed of thought; defers the routing decision to a focused session later.

- **`buffer add <text>`** appends `- UNKNOWN: <text> <!--<TS>-->`. No thread, no body shaping, no attrs — the only structure is the line marker and the timestamp. Empty text is rejected at write time.
- **`tend` flags every UNKNOWN as a violation** (`"UNKNOWN entry must be converted to TEXT, REF, or ACTION before tend can pass"`) and exits 1. UNKNOWN lines are otherwise preserved verbatim — tend does *not* drop or modify them.
- **`flush` is gated by tend**, so any UNKNOWN present blocks the log write, buffer clear, and downstream `tasks` ingest. No partial flushes.
- **Regroup places UNKNOWNs in their own section at the bottom of the buffer**, between the structured entries and any UNPARSED tail: `<!-- UNKNOWN ENTRIES BELOW: convert via 'buffer rm <n>' + the matching 'buffer add-*'. tend will fail until cleared. -->`. UNKNOWNs sort by timestamp. The separator comment is recognised on the next parse and skipped, so tend stays idempotent and the comment is removed once the last UNKNOWN is cleared.
- **Conversion flow**: `buffer rm <n>` then re-add via `buffer add-text|add-ref|add-action …`. Once no UNKNOWNs remain, the next `tend` exits 0 and `flush` proceeds normally.
- **`UNKNOWN_LINE_RE`** added alongside the existing `BUFFER_LINE_RE`; `parse_buffer_entries` now returns `(entries, unknowns, unparsed)`; `regroup_lines` and `cmd_tend` updated for the new signature. `cmd_flush` unchanged in spirit — it still delegates to tend first.

## 2026-05-19 - Operational state moves into `.adulting/` so the Obsidian view stays clean

The vault root used to mix three categories at one level: user content (`notes/`, `threads/`, `people/`, `logs/`, `buffer.md`), tooling state (`bin/`, `task-data/`), and config (`taskrc`, `config.yaml`). Obsidian's sidebar showed all of it, and so did Finder. Following the pattern `.git/` and `.obsidian/` already use in this same directory, tooling state now lives in a hidden subdir.

- **`<ADULTING_HOME>/.adulting/`** is the new home for `bin/task`, `task-data/`, `taskrc`, and `config.yaml`. The visible top level is now only user content + Obsidian artifacts.
- **`tasks` path constants re-rooted** under `INTERNAL_DIR = HOME / '.adulting'`. Four constants change (`TASK_BIN`, `TASK_DATA`, `TASK_RC`, `CONFIG_FILE`); the rest of the file is unchanged. `task_installed()` now checks the new path, and `require_task()` detects the legacy layout and prompts for `tasks migrate-layout` rather than the wrong-looking `tasks install`.
- **`tasks migrate-layout` subcommand** (one-shot): detects old vs new layout; `--dry-run` previews the planned moves. Real run writes a tarball backup at `<ADULTING_HOME>/../<name>.backup-<ts>.tar.gz` *outside* the vault (so a botched migration can't eat its own rollback), then uses `shutil.move` (atomic per-file on the same filesystem) for each of `bin/`, `task-data/`, `taskrc`, `config.yaml`. Regenerates `taskrc` with the new absolute `data.location`. Re-applies the `source` UDA via `ensure_uda()`. Prints a one-line `rm -rf + tar -xzf` rollback at the end. Also deletes the top-level `config/` directory (cruft from an abandoned ask.toml feature).
- **`notes_pdf` and `notes_minutes`** updated to read `${ADULTING_HOME:-…}/.adulting/config.yaml` for the `owner:` lookup.
- **README data-store tree** redrawn to show the hidden subdir; the "One-time setup" section now mentions `tasks migrate-layout` for users upgrading from the previous layout.

What deliberately stays at the root: `.obsidian/` (Obsidian's own), `.git/` / `.gitignore` (the user's VCS of their vault), `.agent/` (external agent runtime), `.claude/` (Claude Code's settings), `.env` (consumed by the external agent runtime, not by this codebase), `.DS_Store` (Finder cruft). And of course every user-content dir.

### Operational events (data migration against `~/.adulting/`, not in this repo)

- Captured `task export` snapshot before any change: 353 records (55 pending, 282 completed, 16 in other statuses).
- Ran `./tasks migrate-layout --dry-run`; reviewed plan.
- Ran for real. Tarball backup `~/.adulting.backup-20260519-084331.tar.gz` (16.9 MB). Moved `bin/`, `task-data/`, `taskrc`, `config.yaml`; regenerated `taskrc`; deleted top-level `config/`.
- Post-migration snapshot: 353 records, same status counts, all uuids preserved. The only field deltas across the two snapshots were `urgency` floats drifting by ~0.001 across 17 records — taskwarrior recomputes urgency relative to "now" at export time, so the two snapshots taken a few seconds apart differ trivially. No real data divergence.
- Round-trip write test: `tasks set-priority` → `tasks show` reflects change → cleared via direct binary call.
- `~/.adulting.backup-20260519-084331.tar.gz` retained as a recovery snapshot; delete once you've trusted the new layout for a few days.

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
