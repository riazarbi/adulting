# Changelog

Dated entries, newest first. Each header is a unit of work; bullets capture the detail.

## 2026-10-05 - Everything that belongs to a thread lives in the thread's folder

Stories: `stories/2026-10-05-thread-scoped-vault.md` (CLI) and
`stories/2026-10-05-commit-workflow-thread-folders.md` (agent skill). The
vault's data partitions by thread, so the layout now does too.

- **Layout:** notes, logs, hours and payments move from four root trees into `threads/<Kind>/<Name>/` beside the thread file: `notes/<stem>.md`, `logs/<date>.md`, `hours.md` and `payments.md`. Thread files, `people/`, `assets/` and `buffer.md` stay where they were, so `[[<Kind>/<Name>]]` links are unchanged.
- **One statement of the layout:** `vault.LAYOUT` drives the path helpers, the schemas' new `path:` field (which replaces `directory:` + `filename:`), and a "Vault layout" table in the manual corpus.
- **Notes in several threads** are filed under the first thread they name; `threads:` stays the authority on membership. A note is still found by its stem alone.
- **REF targets:** `notes new` writes `[[<stem>]]`, `hours log` writes `[[<Kind>/<Name>/hours]]` and `payments log` writes `[[<Kind>/<Name>/payments]]`. The old `notes/…`, `logs/…`, `hours/…` and `payments/…` targets no longer resolve.
- **lint:** reports a file whose thread is not its folder's, a note stem used twice, and anything left in the old root folders.
- **Removed:** `threads delete`. Closing a thread is `status: closed`; removing one is done by hand.
- **Path gate:** `manual-check`, `tools-check` and `agent-check` reject any vault path in the old layout. Before this, no gate looked at paths.
- **`dev/migrate-layout VAULT`** moves a vault and rewrites its links. It refuses the production vault without `--production` and refuses a dirty git vault, never overwrites, and a second run does nothing. `dev/testbed` gained `ADULTING_BASELINE`, `ADULTING_TESTBED` and `layout-compare`.
- **Verified on a copy of the production vault:** 365 files moved and 141 links rewritten. lint reports the same 18 pre-existing violations before and after. Fourteen read commands give the same records old-on-old as new-on-migrated.
- **Tests:** the suite was moved to the new layout, with new tests for the layout, lint rules, REF forms, the gate and the migration. Every piece of the change was undone in turn, and each undo failed a test.
- **Review round 1:** a REF to a note stem two notes share is now one invalid buffer line, not the end of the command. One-line YAML lists (`threads: ["[[A]]"]`) are read as lists by the CLI, lint and the migration alike. `manual-check` now also scans the manual's sources (`src/`, schemas, README) for old-layout paths.
- **Review round 2:** `dev/migrate-layout` checks that every move and rewrite can be made before changing anything; one unwritable file means exit 1 and an untouched vault. The undo is `git reset --hard && git clean -fd`.
- **984 passing, `dev/ci` green.**

## 2026-10-02 - `buffer flush` skips an ACTION that is already an open task

Story: `stories/2026-09-23-idempotent-task-flush.md`. Whoever adds a task
should not have to read the vault first; adding one that is already open now
leaves the vault as it was.

- **Behaviour change:** flush drops a buffered ACTION whose thread, assignee, description, priority, due, scheduled and depends (as a set) all equal an open `TASK:`'s, in a file with exactly that one thread. It writes no log line, so the ingest makes no anchor, and prints `already a task: <uuid>  <abs path:line>  <description>` on stdout. Exit 0, nothing on stderr, printed under `--quiet` as the ingest's lines are.
- **Identical ACTIONs in one flush collapse:** the first after `tend` regroups becomes the task, the rest print `already buffered: <thread>  <description>`. The entry date is not compared, so this holds across `--date`.
- **Not blocking:** a DONE twin, a twin in a note with several threads, a twin in a file that is not valid UTF-8, and an un-ingested `ACTION:` in a log. Bare `tasks`, `tasks ingest` and the `notes` pre-pass are unchanged.
- **Identity is the log line's:** `buffer.log_line` is now the one place an entry becomes a log line, and the check parses that line with `V.parse_action`, so it compares what the ingest would have made of it. `tasks.identity`, `action_identity`, `open_tasks` and `short` hold the rest.
- **The `flush` help names both skip lines, and says flush ingests.** It never said the latter, so the generated tool definition told the agent to run `tasks ingest` after a flush, and the manual listed it as a step.
- **`task-workflow`** relays `Already a task: abcd1234.` when flush prints that line instead of `ingested:`. `footguns`' "Don't dedupe the buffer" stands: the buffer takes duplicates, flush drops them.
- **15 tests** in `tests/cli/test_buffer_cli.py`. Checked by undoing eight parts of the change one at a time (no skipping, no collapse, skips on stderr, `--quiet` hiding them, DONE counting, several threads counting, depends ordered, an unreadable file read anyway); each failed at least one.

## 2026-10-02 - `dev/ci manual` checks what it generated

`dev/ci tools` ran `tools-check` on its output; `dev/ci manual` did not, so a
generation that dropped a command or invented a flag was reported by the next
run rather than the one that caused it.

- `stage_manual` now runs `manual-check` after `manual-build`, and reports the pair, exactly as `stage_tools` does.
- A test pins the symmetry: both stages must name their builder and their checker. Checked by removing the new call and watching it fail.
- **914 passing, `dev/ci` green.**

## 2026-10-02 - the agent skills ship in the image too, and are gated like the tools

The skills carried the same stale picture as the tool definitions did: `hours
log` and `payments log` "going interactive" without a thread, `threads new`
and `people new` "prompting for any field you leave out", and a whole
`footguns` section about interactive traps that have not existed since the
port. The system prompt said there were "Nine vault tools" and that there is
"no `notes` tool".

- **`agent/skills/` in the repo**, shipped as `COPY agent/skills /opt/skills` and installed by the entrypoint beside the tool definitions. The stale passages are rewritten: nothing prompts, a command given too little exits with an argparse error naming what is missing.
- **The system prompt is deliberately not shipped.** Tools and skills are capabilities — one file or folder each, so another image's install side by side — while a prompt is the agent's identity. An overlay agent can be general-purpose and still load these. The owner's call, and the right one.
- **`dev/agent-check`**, in `dev/ci lint`: every `command subcommand` and `--flag` a skill names in a code span exists, nothing claims a command prompts, and each skill has the shape the agent requires (SKILL.md, frontmatter `name` equal to the folder name, a description, no keys outside the spec whitelist — the agent rejects a skill that breaks any of those, silently).
- **`dev/surface.py`** is now the one definition of what the CLI's surface is and what prose may claim about it; `manual-check`, `tools-check` and `agent-check` all read it. The claim detector got sharper in the process: it matches the shapes a claim takes ("goes interactive", "prompts on stdin", "confirmation prompt") rather than the bare words, because the skills talk about the agent's *own* system prompt constantly — and a `without` or `no` earlier in the sentence no longer reads as a denial, which was hiding two of the real claims.
- **The entrypoint installs atomically.** Both tiers start at once and the agent watches those directories, so each file is staged under a dotted name and renamed into place; a skill folder is staged whole and swapped, so a file the new version dropped cannot linger inside it. An unwritable destination is one warning, not one per file.
- **Install-only, by decision:** nothing is deleted, so an overlay that stops being run leaves its files behind to be pruned by hand. Simpler than tracking what was installed.
- **Built and run:** "installed 10 tool definition(s)", "installed 9 skill(s)", a stale `tasks.json` replaced, and a foreign `someone-elses` skill left untouched beside them.
- **Outside this repo:** `~/vault/.agent/prompt/00-role.md` loses the ten-tool inventory and the "no `notes` tool" paragraph — the file's own rule is that the tool descriptions are the interface reference, so that list was a leak against it. `docker-compose.yml` drops `:ro` from the skills mount for both tiers, so they still land in `~/vault/.agent/skills` where they can be read on the host.
- **913 passing, `dev/ci` green.**

## 2026-10-02 - the agent tool definitions ride with the image

The agent seeds its `tools/` directory only if it is missing and never
touches it again, so a long-lived state dir keeps whatever generation of the
definitions was first hand-copied into it. The staging vault's copies were
months stale — they still described commands that prompt on stdin — and
`notes.json` was not there at all, so the agent had no `notes` tool.

- **`COPY dev/tools /opt/tools`**, and `container/entrypoint.sh` installs them into `$AGENT_STATE_DIR/tools` before exec'ing the agent. The definitions and the commands they describe now ship as one artifact and cannot disagree, which is what `dev/ci`'s `tools-check` already enforces inside the repo.
- **Files the image ships are overwritten on every start** — the image is the source of truth, so a hand edit to one of them does not survive a restart. Everything else in the directory is left alone: the agent's own builtins (`read_file`, `rg`, `load_skill`, …) are untouched.
- **A definition naming a command that is not on PATH is reported, not deleted.** The directory is shared with whatever else drops tools into it, and a definition for someone else's binary is not ours to remove. Builtins carry no `command` and are not reported.
- A state directory that cannot be written is a warning, not a refusal to start: a read-only mount should not leave the mailbox unattended.
- The agent watches that directory, so the writes register within its debounce window — no second restart.
- **Run in the container, not just written:** with a deliberately stale `tasks.json` and a hand-made `read_file.json` in the state dir, the entrypoint reports "installed 10 tool definition(s)", the stale copy is replaced by the committed one, the agent's own file survives, and the agent receives its arguments. Six tests drive the script directly on the host with a stub agent, covering each of those cases plus the read-only one.

## 2026-10-02 - the image installs the package instead of mounting it

The container used to find the CLIs by bind-mounting the host repo at
`/opt/adulting` and pointing PYTHONPATH at it, with a shell wrapper per
command running `python3 -m adulting.<name>`. The image is self-contained now.

- **A build stage installs the package into a venv at `/opt/venv`**, which the runtime stage copies in and puts first on PATH. The ten commands inside the container are the package's own console scripts — the same ones the tests run. `pip`, `ensurepip` and `setuptools` stay in the build stage.
- `--copies` gives the venv a real interpreter rather than a symlink into a stage the runtime does not have. `--no-build-isolation` with `PYTHONPATH=/usr/lib/python3/dist-packages` for that one command keeps the build off PyPI: the backend comes from apt's setuptools, which a venv cannot see on its own.
- **`/opt/venv`, not `/opt/adulting`:** a source mount left behind in a compose file would otherwise shadow the install and break every command.
- **The build runs `lint --help-json`** before shipping, so a broken install fails the build rather than the agent's first tool call.
- **Built and run for real** (podman): all ten commands resolve to `/opt/venv/bin`, `lint`, `threads list` and `tasks list` work against a mounted vault, and PYTHONPATH is empty inside the container. 320 MB.
- **`tests/dev/test_container.py` pins the new contract** instead of the old one: the install, the venv on PATH, the build-time smoke run, what the build copies, no PYTHONPATH in the runtime stage, no `/opt/adulting`, no `python3 -m` wrappers, and that pyproject still ships the schemas an installed `lint` needs. Checked by reinstating PYTHONPATH, dropping the smoke run and emptying `package-data` in turn.
- **Outside this repo:** `~/vault/docker-compose.yml` drops the `/opt/adulting:ro` mount from both `agent-shallow` and `agent-deep`. Changing the CLI now needs `up -d --build` rather than a restart.

## 2026-10-02 - the image derives from the published agent

The agent is published to GHCR, so the base no longer has to be built on the
host first.

- **`FROM ghcr.io/riazarbi/agent:latest`**, in place of `agent:local`. The build pulls it; the comment block that told you to build `agent-base` from the staging vault's compose file first — with `/home/riaz` paths — is gone, replaced by the `docker login ghcr.io` line a private package needs and a note that `:latest` moves, with the digest form to pin.
- Nothing else in the image changed: the source still arrives as a runtime bind mount, the ten commands are still wrappers around `python3 -m adulting.<name>`, and `tests/dev/test_container.py` still passes.
- **Outside this repo:** `~/vault/docker-compose.yml` still carries a build-only `agent-base` service to produce `agent:local`, and tells you to build it before `agent-shallow`. Both are now redundant.

## 2026-09-30 - the container's way of running the package is tested

The image bind-mounts the source at runtime and installs nothing, so each
command is a wrapper around `python3 -m adulting.<name>` with PYTHONPATH on
the mounted `src/`. Every other test runs the venv's console scripts, so a
module that lost its `__main__` guard, or that only imports when installed,
would break the container with a green suite.

- **`tests/dev/test_container.py`** reads the Dockerfile as text and runs what it builds — no Docker needed. It pins the wrapper list against `dev/commands.py` (the one list the dev scripts share, previously duplicated in the Dockerfile with nothing comparing them), that the wrappers still run a module rather than a console script, and that all ten commands answer `--help-json` when the source is the only thing on the path.
- `-S` keeps site-packages out of those runs, so the venv's editable install cannot answer for the source. A companion test points PYTHONPATH at an empty directory and asserts the import fails, so the others cannot pass on an installed copy.
- Checked by dropping `commit` from the Dockerfile's list and by removing `lint`'s `__main__` guard; each fails one test.
- The Dockerfile itself needed no change: it was already written for the package (no taskwarrior, no `pipx`, source mounted at runtime), and its claim that `notes pdf|minutes|agenda` still write markdown without pandoc is true — `render.to_pdf` returns "pandoc is not installed" and keeps the file.
- **881 passing, `dev/ci` green.**

## 2026-09-29 - what the manual could not say, and a gate over what the tool definitions claim

Regenerating fixed the agent tool definitions — four of them still described
the pre-port interactive commands — but it could not fix what the manual was
missing, because the harvest only sees help text, docstrings, schemas and the
README, and none of them said these things.

- **A new README section, "Output conventions", carried into the manual** (it is in `dev/manual-harvest`'s `README_SECTIONS`). It states the three facts that hold across every command: paths in output are absolute and why; a file that cannot be read as UTF-8 is skipped by a walker, reported by `lint`, and fatal only when the file was named; and every command *and subcommand* answers `--help-json`.
- The commands say it where it is their own behaviour: `lint`'s docstring names the `file is not valid UTF-8` violation, `tasks`' says a skipped file is not a failed action, `search`'s says one unreadable file cannot cost you a result set.
- **`dev/tools-check` now compares a claim with the truth**, not just the shape: a description that says a command prompts, is interactive, or reads stdin fails the gate. Nothing in this package prompts — `tests/cli/test_no_prompts.py` holds every command to it — and four definitions claimed otherwise for six rounds of review, because nothing read them. A denial next to the word ("Nothing prompts", "rather than prompting") is the wording these should carry and passes.
- Checked by putting the real stale sentence back into `dev/tools/hours.json` and watching the gate name it. `tests/dev/test_tools_check.py` pins both halves against the four sentences that were actually there.
- **868 passing, `dev/ci` green.** The manual needs one more `dev/ci manual` to pick up the new section.

## 2026-09-23 - review round 5, parts R5-B3 and R5-B5: tests that prove what they say

- **R5-B3: every subcommand is checked for `--help-json`, not four samples.** The test reads each command's own manifest and asks all 74 subcommands, so one added tomorrow is covered tomorrow. It also asserts the answer is the *subcommand's* manifest, not the whole command's.
- **R5-B5, the weak tests:**
  - `commit review`'s whole-output cap asserted `len(lines) <= 3000`, which passes for any output including none. It pins the real count now, and changing `DEFAULT_MAX_LINES` fails it.
  - `tasks list --thread SGB` compared its output to `--thread Projects/SGB`, which proves neither. The rows are spelled out; the two forms are still compared, as the point is that they agree.
  - `search`'s path tests asserted `startswith("/")`. They assert the path is resolved and is a file — the thing the contract is about.
  - `notes cat` compared its output to the file it had just printed, which passes however wrong both are. It pins the note's own text, and *then* compares with the file.
  - The `--help-json` manifest test repeated an assertion from forty lines above; it now checks the one thing the other does not — that the manifest survives a JSON round trip.
  - The symlinked-vault test stripped the path prefix before comparing, so it could not see the one thing R5-A3 changed. It compares whole lines, absolute paths included.
- **857 passing, `dev/ci` green.**

## 2026-09-23 - review round 5, part R5-A3: every path a command prints is absolute

Round 3 made `tasks` print vault-relative paths, round 4 extended that to
`lint`, and both were wrong for a reason already in the repo: a reader
resolves a relative path against its own working directory, which is not the
vault. In the agent's container the vault is a bind mount at `/vault` while
the process runs in `/workspace`. Emitting relative paths from `search` once
cost about 57 tool calls and a wrong answer.

- **`vault.full(path)`** builds every path in output: `lint` violations and its "duplicated at" messages, `tasks` ingest failures, `tasks show`'s `source:` and `list --json`, `threads`/`people`/`notes` `created:`/`deleted:`/`already exists:`/`not found:`/`refusing to delete`, `buffer flush`'s log lines, the `path` field of `threads`/`people` `list --json` and `show --json`, and the errors naming a thread file to fix a `rate:` or `currency:` in.
- **`vault.rel(path)` stays for identifiers and for matching** — thread refs, wikilink targets, and `lint`'s schema scope check, which used to re-implement it two screens away (**R5-C2**).
- **The rule is written into the story** (`stories/2026-09-17-python-package-refactor.md`, "The path rule") with the container reason and the note that it has now been decided three times, so the next reader does not re-argue it.
- **Verified on the vault copy:** `lint` prints the same eight violations as before, each named absolutely, and `tasks --dry-run` is unchanged. **851 passing, `dev/ci` green.**

## 2026-09-23 - review round 5, parts R5-A1, R5-A2, R5-C3: one reader for the whole vault

Round 4 fixed `search`'s own walks and the CHANGELOG claimed more than that.
Every other read went straight to `read_text`, so a single unreadable file
still ended `notes list`, `threads list`, `people list`, `hours list`,
`hours report`, `search stream` and `search activity` in a traceback. The
round 4 entry is corrected above.

- **`grep -rn read_text src/adulting/` now finds one line**, inside `vault.read_utf8`. Everything else reads through one of two helpers, and which one says what kind of read it is:
  - **`read_utf8(path)`** — a walker. Returns `None`, and the caller skips the file: `file_summary`, `note_info`, `read_records`, `load_all`, and `search`'s walks. A listing drops the row and keeps the rest.
  - **`read_or_die(path)`** — a file the user named. Stops with `<abs path> is not valid UTF-8`, because skipping it would answer a question about *that* file by pretending it is not there: `notes cat|copy|pdf`, `people show`, `threads show`, the buffer, `config.yaml`, a record file being rewritten, a schema.
- **R5-A2: `search` tells a human and says nothing to a pipe.** `vault.tell_a_human(msg)` warns only when `sys.stderr.isatty()` — the pattern `notes` already used, now shared by `notes`, `search` and `tasks`. The agent harness discards stdout whenever stderr is non-empty, and these commands' stdout is the answer.
- **R5-C3: a file `tasks` cannot read is no longer counted as a failed action.** It printed `Failed: 1` for a file that may have held no ACTION lines at all; it is a warning on a terminal now, and the count stays a count of ACTION lines. The test that pinned the old wording is replaced by one that pins both halves.
- **R5-B2: the `search` skip is tested by its results**, not by the absence of a traceback: the good note and log are in the rows, the unreadable ones are not. Reading them with replacement characters would now fail the test.
- New: one parametrised test puts an unreadable file in each of the six stores and runs every listing against it. `Vault.run_with_stderr_on_a_terminal` is the harness half of the isatty rule.
- **Verified on the vault copy:** six commands print byte-identical output. **851 passing, `dev/ci` green.**

## 2026-09-23 - review round 5, part R5-B1: MANUAL.md regenerated, and the gate that checks it is itself checked

- **The manual is regenerated** (owner ran `dev/ci manual`) and the gate passes. `buffer suggest`, the `notes` picker subcommands (`edit`, `nano`, `strip`), `hours log --all` and `payments log --all` are gone from it; `tasks ingest`, `notes list` and the three `--json` flags are in it.
- **The gate only knew one way to write a heading.** The regenerated manual writes `### tasks`, the previous one `### `tasks``, so every command came back as "no section" and the real comparison never ran. Both spellings are read now — how the heading is written is the manual writer's choice.
- **R5-B4: a flag is matched by name, not by substring.** `--json` was satisfied by `--json-lines`, which would leave the flag it is about undocumented while naming one that exists.
- **R5-B1: the gate is gated.** `problems()` and `main()` never ran in a test, so either comparison could be deleted with a green suite. There are tests for all of it now: the empty case, every kind of drift, the `--json-lines` case, and `main` both ways. Checked by disabling each comparison in turn and watching a test fail.
- `tests/dev/test_manual_check.py` loads the script as a module rather than with `runpy`, so a test can replace `manifest()` and drive the comparison from a stub instead of the real CLI.
- **787 passing, `dev/ci` green — manual gate included.**

## 2026-09-23 - review round 4, part R4-C1: one path format, finished

Round 3 settled on vault-relative paths for the commands that walk the vault
and exempted `lint`, on the grounds that it is the command you point at files.
The exemption was wrong: `lint` and `tasks ingest` print the *same* ACTION
violation, and that is the one place a user sees both formats at once.

- **`vault.rel(path)`** is the one answer: a file inside the vault is named relative to it, a path outside keeps its own name, and `V.where` builds `path:line` on top of it. Every command uses it — `lint`'s violations and the "duplicated at" half of its cross-file messages, and the `created:`/`deleted:`/`already exists:`/`not found:`/`refusing to delete` lines in `threads`, `people` and `notes`.
- **`lint`'s output changed**: `/Users/you/vault/notes/x.md:0: …` is now `notes/x.md:0: …`. Verified on the vault copy — the same eight violations, in the same order, named the way every other command names them.
- The test harness grew `Vault.rel(path)` for the same reason.
- **781 passing.**

## 2026-09-23 - review round 4, part R4-B: three tests that could not fail

Each of these defended a round 3 fix without being able to notice its
removal. Each is now checked by undoing the fix it covers.

- **B1: the windowed PDF only proved `--since`.** `--until 2026-06-30` was past every fixture record, and `--as-of` was the same date — a statement drops anything after `as_of` anyway, so `cmd_pdf` could pass `until=None` and nothing changed. There is now work and a payment on 2026-07-15, with `--as-of 2026-08-31`, so only `--until` excludes them. Dropping either end of the window fails the test.
- **B2: `scheduled:` was the one ACTION attribute nothing asserted** on an ingested anchor. `test_ingest_with_assignee_and_attrs` now carries all five — assignee, priority, due, scheduled, depends — and dropping `scheduled` from the ingest fails it.
- **B3: the local-day rule was undefended.** Every fixture timestamp was mid-day, where the local and UTC days agree, so `Store.day_of` could bucket by UTC and stay green — though it decides which log file a record lands in and which statement window it falls in. A new test logs at 09:00 in Australia/Sydney, which stores `2026-06-01T23:00:00.000Z`, and asserts the entry is filed, listed and REF'd under 2026-06-02.
- **781 passing.**

## 2026-09-23 - review round 4, part R4-A2: a gate that catches a stale MANUAL.md

`dev/tools/*.json` were gated; the manual was not, and it is what an agent
reads. **`dev/manual-check`** closes that: it asks every command for its
`--help-json` manifest — deterministic, no model, no network — and compares
the names the manual uses with the names the CLI has. `dev/ci lint` runs it.

- It checks three things and ignores prose: every subcommand the manual documents exists, every subcommand is documented, and the same both ways for flags (`--help` and `--help-json` are exempt). A section is read to the next heading, subcommand claims are read from the **Subcommands** table only, and a flag's spellings count as one flag.
- **`--help-json` now reports a flag's `aliases`**, so `-m/--minutes` is one flag written two ways rather than one documented and one missing.
- **It is failing, and that is the point.** The committed manual still documents `buffer suggest`, deleted in round 3, and three `notes` subcommands (`edit`, `nano`, `strip`) that have not existed since the port — it still describes `notes` as an interactive picker. It also misses `tasks ingest`, three `--json` flags, and every `notes new` flag, and documents `hours log --all` and `payments log --all`, which do not exist.
- **Regenerating is `dev/ci manual`, which needs `claude`** and is the owner's step. Nothing here can write the manual; this only refuses to let it drift quietly.
- `tests/dev/test_manual_check.py` pins how the manual is read, against a manual written in the test rather than the committed one, so the tests say the same thing whatever state the real manual is in. **780 passing.**

## 2026-09-23 - review round 4, parts R4-A4 and R4-C6: flags that lied about what they do

- **R4-A4: `tasks --dry-run done <uuid>` wrote to disk.** The flag is top-level so that bare `tasks --dry-run` works, and argparse took it before any subcommand, where it did nothing — the anchor flipped to `DONE:` and nothing said otherwise. Round 3 made this worse by removing the "(default invocation only)" caveat from the help. `tasks` now refuses the flag rather than ignoring it: `tasks: error: --dry-run applies to ingest only, not to 'done'`, exit 2, nothing written. `tasks ingest --dry-run`, `tasks --dry-run ingest` and bare `tasks --dry-run` are unaffected.
- **R4-C6: `tasks list --help-json` exited 2.** Making `--help-json` a real flag in round 3 put it on the top-level parser only. It is an argparse **action** now, so it is handed the parser that parsed it and every subcommand answers with its own manifest. Argparse still decides what is data: after `--`, or as another flag's value, `--help-json` is written as the record it looks like.
- **A subcommand's one-line help is now its description**, so `tasks list --help-json` and `tasks list --help` say what the subcommand does. The whole-command manifest is unchanged — it already filled that in from `add_parser(help=…)`.
- `helpjson` decides `takes_value` from `nargs == 0` rather than by naming two argparse classes, so a custom action is described correctly.
- **Verified on the vault copy:** `tasks list`, `tasks --dry-run` and `hours report` print byte-identical output. **775 passing, `dev/ci` green.**

## 2026-09-23 - review round 4, parts R4-A1 and R4-A3: files a walker cannot read, and a vault behind a symlink

Both are collateral from round 3, and both were reproduced before being fixed.

- **R4-A1: a vault reached through a symlink was not checked at all.** `lint` resolved the vault but not the file it was looking at, so every walked path was "outside" the vault, matched no schema, and none of its rules ran — while the summary still said the file was checked. `/tmp` and `/var` are symlinks on macOS and a synced vault is often one, so this was easy to hit. Both sides are resolved now, and a test lints the same vault by both paths and compares.
- **R4-A3: one file that is not UTF-8 ended the whole run with a stack trace.** Removing the blanket `except Exception` in round 3 (correctly) left nothing catching the read in `search` and `lint`. **`vault.read_utf8(path)`** is the one reader now: it returns `None` for a file that cannot be read, `tasks` uses it as before, and `search` skips such a file in its own walks over notes, logs, threads, people and the buffer. (**Corrected 2026-09-23:** that covered `search`'s walkers only. Every other read in the package still went straight to `read_text`, so `notes list`, `threads list`, `people list`, `hours list`, `hours report`, `search stream` and `search activity` still ended in a traceback. See R5-A1 below.)
- **`lint` reports it instead of skipping it**, as `<path>:0: file is not valid UTF-8`. `search` stays silent on purpose: it is read-only and its stdout is data — the agent harness discards stdout whenever stderr is non-empty, so a warning there would cost the caller the search results. `lint` is where the vault's health is reported.
- `Vault.run` in the test harness takes an `env`, for the few tests that reach one vault by two paths.
- **Verified on the vault copy:** `lint`, `search notes` and `search stream` print byte-identical output. **769 passing, `dev/ci` green.**

## 2026-09-23 - review round 3, parts R3-B8 and R3-B9: the untested corners, and tests that say what they test

- **R3-B8: `--help-json`'s content is tested, not just its shape.** `tests/unit/test_helpjson.py` asserts a whole manifest — descriptions, `choices`, `required`, `nargs`, `takes_value`, the `add_parser(help=…)` fallback description and the bare-command case — because `MANUAL.md` and `dev/tools/` are generated from exactly those fields. Blanking one description now fails two tests.
- **`threads.py` has a unit test file**: what `threads new` writes (frontmatter, heading, billing only when given) and the five ways it refuses, including a name already taken in another case. `buffer`'s empty-body branches — `TEXT body is empty`, `ACTION description is empty` and the empty-after-assignee case — are covered in `tests/unit/test_buffer.py`. (`statement_pdf` has no file of its own; its `markdown` and `money` are asserted in `tests/unit/test_statement.py`, which is where the statement it renders is built.)
- Each new test was checked by breaking the code it covers.
- **R3-B9: the test docstrings describe behaviour, not the port.** "refactor unit 4", "characterisation added before the port", "fails against the pre-port script" and "the OLD bash renderer" are gone from six files; the section headers say "nothing prompts". Where the provenance still matters — the render fixtures — it is in `tests/fixtures/render/README.md`.
- **The production-vault tripwire names its likely cause.** It now says Obsidian or a sync client touching the vault is the usual reason, tells you to rerun with the vault closed and sync paused, and only then to treat it as a leaking test.
- **762 passing, `dev/ci` green.**

## 2026-09-23 - review round 3, part R3-D: the docs that lied, and the scripts ruff could not see

- **R3-D1: `schemas/thread.md` named the wrong config key.** It said a thread's `rate` falls back to `.adulting/config.yaml`'s `time.rate`; `hours.py` reads `hours.rate`, and the README always said so. The schema ships as package data and is harvested, so the wrong key had already reached `MANUAL.md`; both are corrected.
- **R3-D4: `dev/testbed` is in the repo's own style** — single quotes like every other file (110 strings, converted by tokenising rather than by hand), and its `read = lambda p: ...` is a `def`.
- **ruff was not seeing the `dev/` scripts at all**, because they have no `.py` suffix and a directory only brings ruff the files it recognises. They are named one by one now, which found two more `l` loop variables in `dev/manual-diff`.
- `dev/testbed`, `dev/manual-diff` and `dev/ci` were each run after the edits. **749 passing, `dev/ci` green.**

## 2026-09-23 - review round 3, part R3-C6: ruff runs (owner decision)

The `# noqa` markers implied a linter that never ran. There is one now, and
it is part of the gate rather than something to remember.

- **`dev/ci lint` runs ruff** over `src`, `dev` and `tests`, configured in `pyproject.toml`: `E`, `F`, `W`, `B` (bugbear), `BLE` (the bare `except Exception:` this code base has argued with) and `RUF100`, which keeps a `# noqa` from outliving the thing it suppressed. `ruff>=0.16` is a dev dependency. Verified by breaking a file and watching the gate fail.
- **Line length is 120**, which is what the code already sits inside; two long lines in `buffer.py` and `hours.py` were wrapped. Tests are exempt from that one rule, because they pin vault lines and command output verbatim and wrapping the strings would change what is pinned.
- **The 19 findings are fixed, not silenced:** four unused imports (three of them left by moving `cmd_list` into `vault`), three unused test variables, two pointless f-strings, six `l` loop variables, one `raise ... from e` in `V.iso_date`, and — the one that was a latent bug — `lint`'s `problem()` closure captured the loop variable `tag` by reference (B023), so a record's message could have named a later record's index. It binds at definition now.
- One stale `# noqa: E402` is gone; the rest are real and are honoured.

## 2026-09-23 - review round 3, parts R3-C4 and R3-C5: one machine each, and the inconsistencies picked

**C4, the duplicated state machines:**

- `render.cut_sections` and `fill_sections` were the same walk twice. There is one `walk_sections(lines, headings, inserts, stops)` now; the two names remain as the two ways it is used, one line each.
- `tasks` ingest held a literal copy of `write_anchor`'s tmp+rename fifty lines below it. Both call `write_line(path, line_no, new_line)`.
- `lint` reported a duplicate uuid and a duplicate record id with the same eight lines twice. `report_duplicates(groups, wording)` is the one copy.

**C5, the consistency list — each item decided rather than left:**

- **One path format in `tasks`.** It printed absolute on ingest, vault-relative in `show` and a bare basename in the ambiguity error. Everything it prints is vault-relative now, through `V.where(path, line_no)`, matching `buffer`. **This closes the second half of deferred bug 7.** `lint` keeps absolute paths on purpose: it is the one command you point at files, and its output is read by editors.
- **`tasks ingest` is a real subcommand**, so `--dry-run` and `--quiet` belong to a command instead of being "(default invocation only)" flags. Bare `tasks` still ingests, and `tasks --dry-run ingest` means what it says (the subparser's copies default to SUPPRESS rather than overwriting the flag).
- **`tasks list --json` and `buffer list --json`** — the last two listings without it. `tasks` prints each anchor's own fields, `buffer` the numbered lines as `{line_no, text}`.
- **`--date` is on every `buffer add-*`**, not just `add-ref`: filing an entry under the day the thing happened is true of any entry, and `stamp()` was always generic.
- **`payments statement --as-of` is an argparse date** like `--since` and `--until`, so a bad one is refused in the same words (exit 2 now, not 1).
- `threads list` and `people list` are one function, `V.print_summary_list`; the `CENT = V.CENT` aliases are gone; the uuid help string is `UUID_HELP`, said once (`--depends` keeps its own wording, because a dependency is stored verbatim and is not a prefix); `parse_block`'s `out[key] == ''` sentinel is explained where it is used.
- **Verified on the vault copy:** `threads list`, `people list`, `tasks list`, `tasks --dry-run`, `payments statement` and `lint` print byte-identical output before and after. `dev/tools/{tasks,buffer}.json` describe the new flags. **749 passing, `dev/ci` green.**

## 2026-09-23 - review round 3, part R3-C2: one record store, not two copies of one

`hours` and `payments` keep their records the same way and differed only in a
fence, a subdir and a noun, so every function that read or wrote a record file
existed twice — `as_output` byte for byte, `cmd_rm` but for a variable name.

- **`vault.Store`** carries the six values that differ (subdir, fence, JSON key, file heading, the noun for messages, the field that dates a record) and owns `path`, `read`, `save`, `load_all`, `find`, `collect` and `cmd_rm`. `V.HOURS` and `V.PAYMENTS` are the two of them; `hours rm` and `payments rm` are now literally the same function.
- Deleted as duplicates: `save`, `collect`, `as_output`, `find_entry`/`find_payment`, `cmd_rm`, `by_start`/`by_received`, `start_name`/`received_name`, and the `SUBDIR`/`HEADING`/`KEY` constants in both modules.
- **`write_records` went from 8 parameters to 5**, and `read_records`, `find_record` and `load_all` take a store instead of a `(subdir, fence, key)` triple, so a caller can no longer pair the wrong fence with the wrong key. `search` and `lint` read the same store values rather than repeating the fences and the `"startTime of entry …"` wording.
- **Verified on the vault copy:** `hours list`, `hours report`, `payments list`, `payments statement`, `search stream` and `lint` print byte-identical output before and after. **745 passing, `dev/ci` green.**

## 2026-09-23 - review round 3, part R3-B (2 of 2): tests that say what they pin, and fewer of them

- **R3-B4: the pinned renderer output says where it is wrong.** `tests/fixtures/render/README.md` explains that the `.expected.md` files were captured from the bash renderers, lists the six known-wrong things they pin, and points at the deferred bugs. **Deferred bugs 12, 13 and 14** are new: an empty action table prints `| None | None | None |`; the minutes summary says `No minutes agreements were made.` beside `No Resolutions were passed.`; headers carry trailing spaces and an empty `subtitle:`/`date:` when a note has no frontmatter. `test_render.py` carries a `# DEFERRED BUG 12` marker.
- **R3-B6: the rule lives with the code, not in a test.** `vault.PRIORITIES` and `vault.check_priority` are the one place that says a priority is `H`, `M` or `L`; `tasks set-priority` and `tasks list --priority` both call it, so an unknown priority is refused instead of silently matching nothing.
- **R3-B7: tests that could not fail are gone or made exact.** The "fails instead of prompting" family repeated in five files is deleted (`test_no_prompts.py` proves it once); the search tests that asserted only an exit code now assert the lines; the per-command list-filter tests are one parametrized test with exact output; `test_depends_help_says_a_whole_uuid` is folded into `test_every_command.py`; `test_commit_cli.py` masks blob hashes through one helper. `tests/dev/test_manual_harvest.py` caches its harvest instead of running the CLI once per test.
- **The repo-root rule moved to `dev/ci` lint**, where the other repo-shape rules are, and out of `test_harness.py`.
- `lint`'s dead `.bak` clause is removed: nothing writes `.bak` files any more.
- **745 passing, `dev/ci` green.** The drop from 772 is the deletions above; coverage of behaviour is unchanged.

## 2026-09-23 - review round 3, part R3-B (1 of 2): the coverage the suite was missing

Fresh mutations of the round 2 code were caught 2 times in 11. These are the holes that let that happen; each new test was checked by breaking the code it covers.

- **R3-B1: the client-facing bank details had no test.** Every PDF test ran with incomplete banking, so only the "not yet supplied" branch ever rendered and corrupting the account number changed nothing. The Payment block's exact rows are asserted now, and so is the "Hours written off" line, which was never rendered either.
- **R3-B2: no default was tested.** `search notes/logs` (20), `search overview` (5), `search stream` (100), `commit review`'s per-file cap (150) and its whole-output cap (3000) each have a test that proves the default's effect; changing any of the five fails one. `commit review`'s tracked-file truncation was never exercised at all, because the fixture's only long file was untracked.
- **R3-B3: rounding and aging rested on almost nothing.** Every rounding assertion now has a `.666…` twin beside its `.333…` case, so rounding down instead of half-even fails: `charge_of`, `hours_of` and a built statement. The aging buckets are tested at their boundaries (0, 29, 30, 59, 60, 89, 90, 200 days), so moving one fails.
- **R3-B5: the coverage lost in the round 2 deletions is back:** an unbilled entry's buffer REF, the stored start and end after `hours log`, `hours report --json` per thread and currency, a payment with no account or note end to end, and `threads show Projects/sgb`.
- **772 passing.**

## 2026-09-23 - the rules suggester is removed (owner decision)

`buffer suggest` proposed a structured entry for raw text. It was not routed to by anything and suggested poorly, so it is gone rather than maintained.

- Removed: `src/adulting/suggester.py`, the `buffer suggest` subcommand and its helpers, `tests/unit/test_suggester.py`, the suggest tests in `test_buffer_cli.py`, `test_no_prompts.py` and `test_every_command.py`, and the `eval/suggester/` corpus.
- `dev/tools/buffer.json` drops the subcommand and its `forbidden_args` block; `dev/tools-build`'s policy no longer names it.
- **R3-D2 and R3-D3 with it:** the policy block described prompts that no longer exist (`hours log` with no thread, `threads new` with fields missing); it now says that no command prompts and points at the terminal tests. `tools-build`'s unused `ALLOWED_FIELDS` copy is gone.
- Nothing else referenced the module. **748 passing, `dev/ci` green.**

## 2026-09-23 - review round 3, part R3-C1: one `ACTION:` parser

There were four: `tasks`' regex, `buffer`'s assignee split, `buffer`'s copy of the same checks in `tend`, and `lint`'s different regex. R3-A5.2 and R3-A5.3 were the consequences.

- **`vault.parse_action(line)`** returns `(assignee, body, attrs, errors)`, taking the trailing `<!--attrs-->` off before reading the body. `vault.split_assignee` is the shared `(Person) text` split. `tasks`, `buffer` and `lint` all use them.
- **R3-A5.2:** `ACTION: <!--due:2026-01-01-->` used to become a task whose description was the comment, with the due date dropped. It is now an action with attributes and no description, and it is reported, not ingested.
- **R3-A5.3:** `tasks` and `lint` agree about a bare `ACTION:` line. `tasks` used to skip it silently; both now call it a missing description.
- **`lint` also reports an ACTION's attribute errors**, which only `tasks` used to check.
- **Verified on the vault copy:** `tasks --dry-run` and `lint` print exactly what they printed before. **786 passing.**

## 2026-09-23 - review round 3, part R3-A: the bugs

Each fix has a test written to fail first. Owner decisions are marked.

- **R3-A1: `payments statement --pdf` ignored `--since`/`--until`.** The text view said `(nothing to report)` while the PDF billed the whole thread. `one_thread_statement` now takes the window and walks the records through `hours.collect` and `payments.collect`, so both views read them the same way.
- **R3-A2: `--help-json` anywhere in the arguments hijacked the command.** It was scanned out of `sys.argv` before parsing, so `buffer add-text -- --help-json` printed the manifest, exited 0 and wrote nothing. It is now a real flag on every command, handled by `vault.parse_command`, so argparse decides what is data: after `--`, or as `--topic=--help-json`, the record is written. The flag is documented in every `--help-json` manifest.
- **R3-A3 (owner decision: ints only, failing loudly at entry and at usage):**
  - `vault.as_int` and `vault.as_money` replace every silent fallback. A thread's `rate: 1,000`, a config `hours.rate: 2,500`, a stored rate that is missing, `2.5` or `'abc'`, and an unreadable payment amount now stop the command naming the record: `rate of entry 'aaaa0001' must be a whole number; got 'abc'`.
  - No entry is implicitly unbilled: `hours.rate_of` and `payments.amount_of` are the only readers.
  - `lint` enforces the schemas' `type` column, which was parsed and never used: a field typed `int` must hold a whole number. The vault copy is clean: same 8 violations as before.
- **R3-A4: `lint <relative-path>` invented a violation.** Paths are resolved before they are checked, so a relative path agrees with the absolute one.
- **R3-A5:**
  - `tasks list --thread SGB` resolves the name like every other command, instead of comparing the raw string and printing a plausible `(no tasks)`.
  - The PDF ledger's Hours column adds up: hours are rounded per line, as charges are, so three 50-minute entries print 0.83 three times under 2.49. `statement.check` now also asserts that the lines' payments and hours sum to their totals.
  - **(owner decision) `search` no longer folds thread-name case:** `search notes --thread acme` is refused, as `hours list acme` always was. `fold_case` and the four functions that threaded it through are gone.
  - Every walker reads a stored time through `vault.as_time`, so a malformed `startTime` stops each command with the same message. `search`'s five `except Exception` swallows and `_safe_load` are gone; `minutes_between` with them.
- **Verified on the vault copy:** hours, payments, search, tasks and lint print exactly what they printed before. **773 passing.**

## 2026-09-22 - review round 2, part R-D: the tests

- **R-D1, tests that could not fail or hid a bug:**
  - `new_id` takes a `draw` function, so a test can force a collision; deleting the avoid-existing guard now fails it.
  - `test_pdf_markdown` carries `# DEFERRED BUG 10`.
  - The deferred-bug-8 lint test asserts the exit code and all output.
  - The static no-stdin test says plainly that the terminal tests are what protect the rule.
  - The terminal refusal tests assert each exact message, and they now also cover `buffer rm` and `hours`/`payments edit`.
- **R-D2, duplicates deleted,** each checked against its counterpart first: 18 across `search`, `buffer`, `notes`, `tasks`, `hours`, `payments`, `threads` and `notes render`.
  - `test_thread_names.py` and `test_review_small_bugs.py` are gone. Their tests moved into the files for their commands and are named for the behaviour they check.
  - `tests/cli/` is one file per command, plus `test_no_prompts.py`, `test_every_command.py` and the three notes files.
- **R-D3, exact:**
  - Ten `tasks` mutation tests fold into the exact, step-by-step one, which gains the replace-an-existing-due and replace-an-existing-priority cases.
  - The `tasks list` filters, `search` notes/logs filters, `commit review` outputs and `buffer tend`'s report assert whole output.
  - The 14 clean lint tests check exit code, stderr and summary.
  - The argparse-only tests assert the exact message and an unchanged vault, or are deleted where argparse's `choices` is the whole behaviour.
- **R-D4, behaviour not internals:**
  - Cycles are tested through `cross_check_tasks`, `--as-of` through `payments statement`.
  - The three statement tests that restated `S.check()` are gone.
  - The pretty-printed JSON test spells out its expected lines.
  - Every per-file run wrapper (`hours()`, `pay()`, `buf()`, …) is gone in favour of `vault.run(…, cli=…)`, which now closes stdin by default.
- **Also:** the suggester's folder checks use `is_dir()`/`is_file()`. `threads new` and `people new` explain why they alone ask the filesystem whether a name is taken. The refactor story's status and "Duplication left in place" are current.
- **737 passing, 97% coverage, `dev/ci` green.**

## 2026-09-22 - review round 2, part R-C: consistency

- **Shared names used directly:**
  - `V.HOURS_FENCE`, `V.PAYMENTS_FENCE` and `V.KIND_DIRS` replace the local copies in `hours`, `payments`, `search` and `threads`. `search.DATE_RE` is renamed `LEADING_DATE_RE`, so it no longer shadows `V.DATE_RE`.
  - `search` parses task anchors with `tasks.parse_anchor` and buffer lines with `buffer.parse_buffer_entries`, instead of its own copies of their regexes. They are stricter, and on the vault copy they match exactly the same lines.
- **One naming style:** `V.vault_home()` everywhere, no module imports `vault_home` on its own, and every subparser is `p = sub.add_parser(...)`.
- **Dead code removed:**
  - The `rm-depends` branch that could not run.
  - The `if not tok` guard in `parse_action_attrs`; `buffer_action` no longer builds empty tokens.
  - `write_buffer`'s mkdir and `require_repo`'s second vault check, both made unreachable by `require_vault`.
  - The single-use closure in `search overview`, and a four-line `resolve_thread_arg` (now one).
  - `hours edit/rm` and `payments edit/rm` used to read the file again to find the record they had just found. The new `vault.find_record` returns the record together with its file's list.
  - The first handler in `search.hours_in_window`, which could not trigger. **Kept:** the second. A hand-edited `startTime` that is not ISO reaches it, and without it `search activity` crashes with a traceback; a new test proves it is reachable.
- **Validate or catch, not both:** `tasks.validate_date` and `validate_priority` are gone. `set-due` and `set-scheduled` stop directly, and `set-priority` takes `choices=H,M,L`, so a bad priority is now an argparse usage error (exit 2).
- **Comments that told history** in `notes` and `render` now say what the code does, and `LEGACY_ACTION_RE` is `CHECKBOX_ACTION_RE`.
- **`--since` and `--until` must be real dates** (`vault.iso_date`). `hours list --since x` used to be accepted, and bounded nothing.
- **Verified on the vault copy:** `search` stream/overview/activity, `tasks`, `hours` and `payments` edit/rm, and the buffer's pending events are identical before and after. **765 passing.**

## 2026-09-22 - review round 2, part R-B: the rest of the deduplication

R-B1 and R-B3 went in with R-A.

- **R-B2: one frontmatter parser.**
  - `vault.parse_block` reads the small YAML subset the vault uses: scalars, block lists, lists of mappings, and one level of nested mapping. `parse_frontmatter_doc` and `read_config` both use it.
  - `parse_frontmatter` and `read_frontmatter` are gone. (`lint`'s own schema parser is separate, as the story records.)
  - **Visible change:** `people show --json` and `threads show --json` now list a file's `cadences` as `{key, frequency, description}` entries; they used to print `"cadences": ""`. That affects 13 people in the vault copy.
  - An empty field is `""` everywhere.
- **R-B4: `vault.check_currency`** replaces five copies of "upper-case it, or stop if it is not a 3-letter ISO code".
- **R-B5:**
  - `payments.billed` walks the hours records through `hours.collect` and `hours.money_of`. `search`'s two remaining hand-written date windows use `vault.in_window`.
  - `lint`'s two ~35-line record-block validators are one `validate_record_block(text, path, label)`, driven by a table of the two kinds. `read_block` takes the label alone.
  - "Resolve a thread or stop" is one `vault.find_thread`, which raises, and `resolve_target`, which dies.
  - **Visible change:** `buffer` and `threads` now say `thread 'X' does not resolve to a thread file` like every other command. They used to say `does not resolve to threads/<Kind>/<Name>.md (expected …)` and `not found: X`.
  - `people` and `threads` share `vault.CATEGORIES`, `today()`, `file_summary`, `file_json` and `rank_by_query`. `tasks.today_iso` became `V.today`.
- **Verified on the vault copy:** thread and person lists and every `show --json`, hours, payments, search, tasks and lint are identical before and after, apart from the two visible changes above. **752 passing.**

## 2026-09-22 - review round 2, part R-A: the bugs (with R-B1 and R-B3)

Each fix has a test written to fail first.

- **R-A1: `people delete` and `people show` accepted a path.** `people delete ../threads/Projects/Foo -y` deleted the thread file. Both now refuse a name with `/` or a leading `.`, as `new` does. `notes` refuses a stem with a leading `.` too. `threads` was safe: it only ever matches files it lists.
- **R-A2: every thread and person check is case-exact.** A new `vault.vault_file(rel)` looks each part up in its folder's listing, so `..` cannot leave the vault either. `buffer add-ref` and `tend`, lint's wikilink and assignee checks, `people delete/show`, `notes new`'s people links and `vault.person_exists` all use it. On macOS, `buffer add-ref SGB Projects/sgb`, a note linking `[[Projects/sgb]]`, and `people delete "riaz arbi"` were all accepted. `threads new` and `people new` still ask the filesystem whether the name is taken, because on macOS `sgb` would overwrite `SGB`.
- **R-A3 and R-B1: library functions no longer exit the process.**
  - `buffer`'s add functions return the line they buffered and raise `ValueError` on bad input. `buffered()` prints or dies for the `cmd_*` functions.
  - `buffer.tend(lines)` returns `(new_lines, violations)` and touches no file.
  - `tasks.ingest(dry_run)` returns `(ingested, failed)`, and `tasks.report_ingest` prints them.
  - `add_ref` is best-effort without redirecting output.
  - Nothing in `src/` catches `SystemExit` or redirects stdout any more.
  - `notes new` prints `buffered:` lines itself, and its `buffer_ref` wrapper is gone.
- **R-B3: one ACTION attribute check.** `buffer add-action` runs its flags through `vault.parse_action_attrs`, so it now checks priority too. Its messages match `tasks`': `due must be YYYY-MM-DD`, where they said `--due must be`.
- **R-A4: the minutes Summary goes before the first level-1 heading starting `# Content`,** so `# Contents` and `# Content and notes` get one. `## Content …` never does, and there is only ever one. All 111 notes in the vault copy use exactly `# Content`, so their renders are unchanged.
- **R-A5:**
  - `tasks` refuses an empty uuid prefix (`rm-depends X ""` removed the only dependency).
  - Receipts are rounded to the cent before they are summed, as charges are. The review's example (2.675) already added up, but two receipts of 1.005 listed as 1 each and totalled 2.01.
  - `hours edit` on an entry with a rate but no currency says what is wrong with the entry, not `--rate`. Such an entry could always be repaired with `-c` or `--rate 0`, and a test now proves it.
  - The suggester's `main` has the usual shape and reports a bad `--today`.
  - Every command's parser is built by `vault.command_parser(prog, …)`, and errors use that name, so `python -m adulting.notes` says `notes:`, not `notes.py:`.
- **Verified on the vault copy:** the `buffer` add/tend/rm/flush, `tasks`, `hours log`, `notes list` and `notes minutes` flows give identical output and vault changes before and after. **753 passing.**

## 2026-09-22 - review fixes, part E: the refactor story is current

- `stories/2026-09-17-python-package-refactor.md`:
  - The status line says the review is done: 705 tests, 96% coverage, `dev/ci` green.
  - "Deferred bugs" explains the `# DEFERRED BUG <n>` markers and credits A8 for the two render bugs fixed.
  - "Duplication left in place" now lists only what survives part B, and why.

## 2026-09-22 - review fixes, part D (2 of 2): the rest of the test review, and two fixes it turned up

- **Behaviour change: every command refuses a vault that is not a directory.** With `ADULTING_HOME` pointing at nothing, reads reported an empty vault, and `buffer add`, `people new` and `threads new` quietly started a new vault there, so a mistyped path went unnoticed. With it pointing at a file, those four crashed with a traceback. Every command now stops with `<command>: error: ADULTING_HOME is not a directory: <path>`, as `commit` already did, via a new `vault.require_vault()`.
- **Behaviour change: `buffer suggest` quotes with `shlex.quote`.** It had its own `_shquote`, as the review suggested replacing. A quote in the text is now written `'it'"'"'s'` instead of `'it'\''s'`; both paste the same.
- **One file per command, finished:**
  - `test_tasks_output.py` merges into `test_tasks_cli.py`, and `test_search_output.py` into `test_search_cli.py`.
  - The ten per-command `--help-json` tests become one parametrized test in the new `test_every_command.py`.
  - The review's duplicates are deleted: ten in `tasks`, four in `search`, one in `commit`.
- **Exact assertions** where the review found loose ones:
  - `tasks`: the ingest failures, `next` showing exactly the first five, `done` stamping today's date, `rm-depends` refusing and writing nothing, and `add` writing the exact buffer line.
  - `buffer rm` errors check the exit code and that the buffer is unchanged.
  - The `commit` outputs, `people new`'s file, the whole meeting template, and `search overview --json`.
- **Implementation details no longer tested directly:**
  - Deleted, with each behaviour covered through the commands: the `tasks` sort keys, `lint._rotate_to_min`, `people._resolve_person` and `search`'s line regexes.
  - Rewritten: the suggester tests assert which thread wins rather than weight numbers, and the fuzzy-score test asserts ranking order rather than thresholds.
  - The manual-harvest test reads the section list from the script instead of splitting its source.
- **New tests:**
  - `test_no_prompts.py` runs every create and delete command with a real terminal on stdin and "y" already typed. Each must refuse, print nothing to stdout, and leave the vault byte-identical. A static check confirms nothing in `src/` reads stdin. Injecting a terminal-only prompt into `people delete` fails both.
  - Whole-output unit tests for `render.header` and all three renderers.
  - The notes ingest pre-pass on every subcommand but `new`, which failed when `last` was made to skip it.
  - `buffer flush` warning after a real ingest failure, on a read-only notes folder.
  - `payments log -d` filing its REF under that day.
  - The vault check for all ten commands.
- **Harness:**
  - `Vault` gains `write`, `run_on_a_terminal`, `snapshot` and a `cwd` for `run`, and loses the unused `check`.
  - A comment explains why isolation happens both per session and per test.
  - Eight per-file `write` helpers, three `THREAD` constants, `commit`'s own `GitVault` and the notes tests' direct subprocess calls give way to the conftest helpers. The one exception is the pty test that needs stderr on the terminal, and a comment says why.
  - Fixtures named `v` or `home` now say what they hold: `buffer_vault`, `notes_vault`, `tasks_home` and so on.
  - The empty, untracked `tests/fixtures/threads/` is gone.
- **705 passing.**

## 2026-09-22 - review fixes, part D (1 of 2): one test file per command, duplicates gone, exact assertions

The review found tests split across files by refactor unit rather than by command, with about 50 duplicates and many assertions that check a substring or only the exit code.

- **One file per command:**
  - `test_hours_output.py` merges into `test_hours_cli.py`, and `test_payments_output.py` into `test_payments_cli.py`, each grouped by subcommand.
  - `test_threads_billing.py` merges into `test_threads_cli.py`.
  - The lint tests from `test_lint_hours_file.py`, `test_lint_task_anchor.py`, `test_schema_task_anchor.py`, `test_payments_cli.py` and `test_hours_cli.py` join `test_lint_cli.py`, one section per schema.
  - The PDF statement tests move from `unit/test_statement.py` to `test_payments_cli.py`, and the billing-party tests to `unit/test_vault.py`.
- **Duplicates deleted** after checking each is covered elsewhere: seven in `hours`, seven in `payments` (including one in `unit/test_statement.py`), seven in `threads`, and the lint block-shape cases that `unit/test_lint.py` pins exactly. Where a "duplicate" covered one case nothing else did, that case moved into the surviving test: `hours log -c RANDS`, and `payments log` with amount 0.
- **Exact assertions:**
  - Every lint test now asserts the exact list of violation lines. That is 29 tests that checked a substring, including the cycle, duplicate-id and task-anchor checks.
  - The PDF statement errors assert the exact message, with `--as-of` pinning the one that named today's date.
  - `payments log` pins the stored record under a fixed timezone.
  - The hours and payments buffer REFs assert the whole line.
  - `hours edit` asserts the stored start, end, rate and currency.
  - The ambiguous and wrongly cased `hours log` cases assert the message and that nothing was written.
- **`unit/test_hours.py`:** the one test that appended, collected, found and priced entries is five tests, sharing a `utc` fixture that no longer undoes the suite's isolation.
- **Fixture names say what they hold:** `hours_vault`, `payments_vault` and `billing_threads` replace the several meanings of `v` and `threads`.
- **Harness fix:** `Vault.write_thread` wrote `kind: processe` for a Processes thread (`"Processes".rstrip('s')`); it now maps each kind directory to its frontmatter value.
- **663 passing** (was 680: the difference is deleted duplicates, less new tests).

## 2026-09-22 - review fixes, part C8: small tidy-ups

- **Imports at the top of the file.** Moved: `json` in `search` (three copies), `math` and `argparse` in `suggester`, `datetime` in `payments._as_of`, `statement_pdf` in `payments`, and `suggester` in `buffer`. The two left inside functions, `buffer` → `tasks` and `tasks` → `buffer`, are there because each module imports the other, and a comment now says so.
- **`hours.BY_START` and `payments.BY_RECEIVED`** were lambdas with a lint exemption; they are now plain functions, `by_start` and `by_received`.
- **`search`:** the statements joined by semicolons in `activity` are one per line, a trailing-whitespace line is gone, and `r['date'] or '?'.ljust(10)` is now `(r['date'] or '?').ljust(10)`. That is the same output, since a date is always ten characters, but it now reads the way it runs. `suggester`'s own `main` names its parser `parser`.
- **Verified on the vault copy:** `search` overview/activity/notes/logs/stream, `payments` statement (with and without `--thread` and `--as-of`) and list, `hours` list and edit, and `buffer suggest -y` give identical output before and after. **680 passing.**

## 2026-09-22 - review fixes, parts C2 and C3: one main() shape, help for every argument

- **Every command has the same `main()`:** it builds a parser named `parser`, with subcommands under `dest='subcommand'`, and ends `return args.func(args)` under `sys.exit(main())`. `notes`, `commit`, `hours`, `payments`, `people`, `search` and `threads` used to drop the result, and `lint` exited from inside `main`. Every `cmd_*` now returns an int: 56 bare or missing returns became `return 0`. Exit codes are unchanged, because None already exited 0.
- **One `--since`/`--until`/`--json` helper, `vault.add_window_flags`,** for `hours list/report`, `payments list/statement` and every `search` subcommand; it replaces `search`'s local `add_range`.
- **Every argument has help text.** 62 had none, mostly in `hours` and `payments` edit/show/rm, the `tasks` set-* commands and the `buffer` add commands. `--help`, the harvested manual and the agent tool definitions all now describe them. Each sentence was checked against the code, e.g. `hours edit -d` keeps the duration and `tasks rm-depends` matches a prefix of this task's dependencies first.
- No behaviour change beyond the help text. **680 passing.** `dev/ci generate` will pick the new help text up into MANUAL.md and dev/tools the next time it runs.

## 2026-09-22 - review fixes, parts C6 and C7: comments that say what the code does

- **Stale comments rewritten.** Covered: `buffer`'s module docstring and flush comments, which still mentioned a task backend, taskwarrior and a subprocess; `payments` and `statement_pdf`, which named the old `_statement` module; a `suggester` comment that promised ranking done elsewhere; and `vault`'s docstring, which said it served only `hours` and `payments`.
- **`buffer flush` no longer claims to be atomic.** Its docstring now says what happens: nothing is written if tend finds a problem, but past that point the logs are written one at a time and the buffer is cleared last.
- **`render.py` describes itself, not the awk it replaced.** `records` → `split_lines`, `joined` → `join_lines`, `grep_sed_uniq` → `matching_lines`, with the awk/grep/sed wording gone from comments and test names. The module docstring keeps one sentence of history, because the output must still match the old scripts byte for byte and the render fixtures pin it. No behaviour change. **680 passing.**

## 2026-09-22 - review fixes, part C5: dead code

- **The `add-ref` suggestion that could never be made.** The suggester recognised REF wording ("see-also …", "link …"), then always gave up because it cannot name a REF target. `buffer` still had code to format and run the suggestion. The wording now goes straight to UNKNOWN, the outcome it always had, and the dead paths are gone: the `add-ref` branches in `buffer.format_suggestion` and `dispatch_proposal`, and the `ref_target`/`ref_summary` fields of a suggestion.
- **Unused names:** `lint.TASK_RE`; the `ref` parameter of `hours.resolve_billing`; the unused record in `hours rm` and `payments rm`.
- **Frontmatter reads that did nothing.** `hours` and `payments` edit and rm read the file's currency to pass to `write_records`, which only uses it when it creates a new file. They act on a file that already exists, so the read is gone.
- **`hours.buffer_ref` and `payments.buffer_ref`** were one-line wrappers; both call `buffer.add_ref` directly.
- **`helpjson`:** the subcommand-alias bookkeeping (no command has aliases) and a no-op expression are gone; every `--help-json` manifest is byte-identical.
- **`search`:** `resolve_thread_arg` lost a catch-all that `resolve_target` already covers; `notes` and `logs` share one function; `stream` uses `window_default` instead of its own copy.
- **`dev/`:** `manual-harvest` loses every branch for bash scripts, none of which remain. The command list, kept in `dev/ci`, `dev/manual-harvest` and `dev/manual-diff`, now lives once in `dev/commands.py`, and a test checks it against the console scripts in `pyproject.toml`. The harvested corpus is unchanged except that it drops the `interpreter` line, now always python3.
- **Verified on the vault copy:** `hours` log/edit/show/rm, `payments` log/edit/rm, `buffer suggest` with and without `-y`, and `search` notes/logs/stream give identical output and identical vault changes before and after. **680 passing.**

## 2026-09-22 - review fixes, part C4: no type hints

- `tasks.py` was the only module with type hints; its functions no longer have them, to match the rest of the code. The `Anchor` dataclass keeps its field annotations, because a dataclass cannot declare fields without them; a comment says so. No behaviour change.

## 2026-09-22 - an output folder that cannot be made is an error, not a traceback

Found while checking the error-message change on the vault copy, and present before this refactor: `payments statement --pdf` into a folder that cannot be created printed a Python traceback. So did `notes pdf|minutes|agenda --out`.

- **`vault.make_dir`** creates the folder or stops with `<command>: error: cannot create <folder>: <reason>`, e.g. `Not a directory`. Only these two commands create a folder the user named, and both now use it.
- **Tests:** one for each command, both failing with the traceback before the fix. **679 passing.**

## 2026-09-22 - review fixes, part C: every error looks the same

Errors came in three shapes, depending on the command: `error: text is empty` (`buffer`, `tasks`, `commit`), `hours: empty description` (`hours`, `payments`, `notes`, `search`), and no prefix at all (`threads`, `people`: `not found: Nope`). Decided 2026-09-22: every message looks the same, behind one shared helper.

- **Every fatal error is now `<command>: error: <message>`**, e.g. `hours: error: empty description`, `threads: error: not found: Nope`. That is the shape argparse already uses for usage errors (`buffer: error: unrecognized arguments`), so all errors now match. Warnings are `<command>: warning: <message>`. That changes the banking-details warning from `payments` (it had no prefix) and the task-ingest warning from `buffer flush` (it had no `warning:`). The message text after the prefix is unchanged, and exit codes are unchanged: 1, or 2 for `lint` with no schemas.
- **One helper, `vault.die(msg)`, with `vault.warn(msg)`.** It takes the command name from `sys.argv[0]` the way argparse does, so shared code such as `vault.read_records` names the right command without being told. The four copies of `die()` and about 60 direct `sys.exit("...")` calls all go through it. The `tool` parameter of `resolve_target`, `resolve_currency`, `when_from_flags` and `statement_pdf.render`, and the `TOOL` constants, existed only to build prefixes; they are gone.
- **The statement's self-checks** now say `statement check failed: …`; they used to be prefixed `statement:`, which named no command. A new test covers all three; none had one before.
- **Tests:** about 90 expected messages updated. New tests cover `die` and `warn`, and the banking warning test asserts the whole line instead of a substring. **677 passing.**
- **Verified on the vault copy:** every successful command's output is identical before and after. The errors differ only by the new prefix.

## 2026-09-22 - review fixes, part B (B6): plain functions, not fake argparse results

Commands called each other by building a fake `argparse.Namespace` to pass to the other's `cmd_*` function, so a reader had to find the argparse setup to learn what a call needed.

- **The work now lives in plain functions with ordinary arguments:** `buffer.buffer_unknown(text)`, `buffer_text(thread, text)`, `buffer_ref(thread, target, summary, date)`, `buffer_action(thread, text, due, scheduled, priority, depends)`, `buffer.tend(quiet)` and `tasks.ingest(dry_run, quiet)`. Each `cmd_*` is now a one-line adapter from the parsed arguments.
- **Callers use them directly:** `buffer flush` (tend, then ingest), `buffer suggest -y`, `buffer.add_ref` (used by `hours`, `payments` and `notes`), `tasks add`, and the pre-pass in `notes`. No `argparse.Namespace(` is left in `src/`.
- **Verified on the vault copy:** the same run of `buffer add`, `add-text`, `add-ref`, `add-action`, `suggest` (with and without `-y`), `tend`, `flush` (with its ingest), `tasks add`, bare `tasks`, `hours log` and `notes new` gives identical output and identical vault changes before and after, ids and clock times masked. **674 passing.**

## 2026-09-22 - review fixes, part B (B5): lint's record blocks

- **One block reader for hours and payments files.** `validate_hours_block` and `validate_payments_block` each carried the same twenty lines: find the block, refuse a second one, parse the JSON, check its shape. `lint.read_block` does that once. The messages are unchanged, down to "tracker JSON" versus plain "JSON".
- **`lint._find_block` is gone**; it duplicated `vault.find_block`.
- **Renames.** `lint.unwiki` becomes `wikilink_target`, since it does not do what `vault.unwiki` does: it returns None for plain text. The id registry `'hours_ids'` becomes `'record_ids'` and `cross_check_hours` becomes `cross_check_record_ids`, since both check payment ids too.
- **Tests:** a new test pins every block-shape message, for both kinds of file. It passes on the code before the change and fails when a message is altered. Four of those messages had no test before. **674 passing.**
- **Verified on the vault copy:** `lint` output is identical before and after (381 files, 7 violations).

## 2026-09-22 - review fixes, part B (B4): one frontmatter thread reader, one config reader

- **`vault.note_threads(fm)`** reads the threads a note (`threads:`) or log (`thread:`) belongs to, wikilinks unwrapped. It replaces three copies, in `notes list`, `search`'s note records, and `tasks`' thread cache; `tasks.parse_frontmatter_threads` is gone.
- **The owner comes from `vault.read_config()`.** `render.read_owner` was a second config reader used only for `owner:`. It differed only on odd configs: it kept single quotes and trailing spaces, and took the first of two `owner:` lines where `read_config` takes the last.
- **Not merged: `parse_frontmatter` and `parse_frontmatter_doc`.** The review suggested it, but they read different things (thread files versus notes and logs), and merging them risks changing `threads show --json`. Left for a separate, measured change if ever wanted.
- **Tests:** the thread reader and owner tests moved to the vault tests. **672 passing.**
- **Verified on the vault copy:** `notes list` (text and JSON), `search activity`/`stream`, `tasks list` and `tasks --dry-run` give identical output before and after. So do all 116 minutes renders, and the text of all 228 PDFs matches.

## 2026-09-22 - review fixes, part B (B3): one ACTION attribute parser

`buffer` and `tasks` each parsed an ACTION's `due:`/`scheduled:`/`priority:`/`depends:` attributes, and each checked people files and dates with its own copy of the same code.

- **`vault.parse_action_attrs(tokens)`** replaces both parsers. It follows `tasks`: a bad value is reported and left out, and a buffer timestamp token is skipped. `buffer` only ever used the error list, so its behaviour is unchanged.
- **`vault.person_exists`, `vault.DATE_RE` and `vault.UUID8_RE`** replace the copies in `buffer` and `tasks`; `lint`'s task-anchor assignee check uses `person_exists` too. `tasks`' unused `ASSIGNEE_PREFIX_RE` is gone, and `tasks.gen_uuid8` gives way to `vault.new_id`, which it duplicated.
- **Tests:** the parser and `person_exists` tests moved to the vault tests. **672 passing.**
- **Verified on the vault copy:** `buffer add-action` (good attributes, a bad date, an unknown assignee), `buffer list`, `buffer flush`, `tasks --dry-run`, `tasks list` and `lint` give identical output before and after, ids and clock times masked.

## 2026-09-22 - review fixes, part B (B1, B2): one copy of the shared helpers

The review's part B lists code that several commands each kept their own copy of. These two steps move the simplest copies into `vault.py`. No output changes.

- **B1: one `vault_home()`.** `commit`, `people`, `buffer`, `threads`, `lint`, `tasks` and the suggester each defined their own; all now import the vault's. Unused imports went with them.
- **B2: shared record helpers.** `vault.HOURS_FENCE` and `vault.PAYMENTS_FENCE` replace five copies of the fence strings. `vault.minutes_of` replaces five copies of the minutes sum, and `vault.in_window` replaces four copies of the since/until check. `vault.is_currency_code` replaces seven copies of the ISO-code regex. Each command keeps its own error message; `search`'s record filter keeps its own date check, which also drops undated records.
- **Tests:** `minutes_of` moved from the hours tests to the vault tests, with new tests for `in_window` and `is_currency_code`.
- **Verified on the vault copy:** hours report and list, payments statement and list, and search activity and stream, with and without date windows, give identical output before and after (1,907 lines). **671 passing.**

## 2026-09-22 - review fixes, parts D1 and D6: tests that can fail, and labelled deferred bugs

The review found tests that pass whatever the code does, and deferred bugs whose tests either were not labelled or presented the bug as intended. This fixes both.

- **Rewritten so they can fail.** Each was checked by breaking the code it covers and watching it fail, then restoring the code.
  - The `notes` ingest unit tests assert that an ACTION became a TASK anchor, and that a failing one was left alone. They used to assert only silence.
  - `commit.has_head` is tested false on a repo with no commits, and `require_repo` refuses a plain directory.
  - `one_thread_statement` asserts exact charges, payments, balance and lines, and `find_payment` has a hit case.
  - The lint cycle and task cross-check tests assert exact lists. A new test covers the one case the cycle de-duplication exists for: a task listing the same dependency twice.
  - Both "a failed render leaves no stale file" tests, for the statement and for notes, now make the render fail for real: pandoc runs with no xelatex on PATH, via a new `harness.without_program`. The statement test used to pass a successful render, and the notes one only failed because of deferred bug 1.
  - The harness tests assert the exact `.venv/bin/<name>` path. A missing command used to resolve `Path("None")` inside the repo and pass. The vacuous root-scripts loop became a check that no executable sits at the repo root.
  - The id tests match `[0-9a-f]{8}` exactly instead of `int(x, 16) >= 0`.
  - The task-anchor schema tests assert lint's exit code and every violation line.
- **Deleted, as tests that could not usefully fail:** `test_smoke.py` (each test duplicated another), the two random-id collision tests, the five "help no longer mentions X" tests, and the five "removed flag is rejected" tests.
- **Every deferred bug is now pinned by a test carrying `# DEFERRED BUG n`:** 1-8, 10 and 11, one grep away. The pins for bugs 4 (`notes copy`) and 8 (badly dated thread entries) were named as if the behaviour were intended; they are renamed.
- Unused imports removed across the tests; `harness.own_bin_dirs` explains why it keeps the repo root (dev/testbed's old implementation). **669 passing.**

## 2026-09-22 - action tables say whether each action is open or done

Minutes and PDF action tables listed completed actions (`DONE:`, `- [x]`) alongside open ones with nothing to tell them apart. That was deferred bug 9 until it was decided: list every action, open and done, and say which.

- **A Status column**, `Open` for `ACTION:`, `TASK:` and `- [ ]`, `Done` for `DONE:` and `- [x]`. The heading row is `| Assignee | Task | Status |`, and the empty minutes row becomes `| None | None | None |`. The same task open and done in one note is listed both ways, so nothing is hidden.
- **Tests:** a unit test covers every action form and the both-ways case, another covers the table in `pdf` and `minutes`, and deferred bug 2's pin gains the column. All three failed before the change. Seven fixture expected files changed, and a script confirmed that every changed line is an action-table line.
- **Verified on the vault copy:** all 348 renders still match the old output except that 109 differ, and in each of those only action-table lines changed. PDF outcomes are unchanged. **686 passing.**

## 2026-09-22 - review fixes, part A: the bugs

A third-party review of the refactor (`stories/2026-09-22-refactor-review-findings.md`) found bugs the tests missed. Every one in its part A was reproduced on a scratch vault first, then fixed with a test written to fail before the fix. All but A4 predate the refactor, which carried them over faithfully.

- **A1: the PDF statement charged unbilled and foreign-currency time.** It listed unbilled time as a line and charged a USD entry on a ZAR thread as ZAR. It now takes only entries in the statement's currency, as the text statement did.
- **A2: the text statement and PDF could differ by cents.** `hours report` and the text statement summed unrounded amounts; the PDF rounds each line. All three now use `statement.charge_of`, so three 20-minute entries at 2500 are 2499.99 everywhere. No figure changes on the vault copy, whose entries are all whole cents.
- **A3: money went through `float` before display.** A hand-edited 2.675 listed as 2.67 while the statement showed 2.68. Rows keep the Decimal; only `--json` and `show` convert, with their output unchanged.
- **A4: a relative `notes pdf --out` lost the PDF.** pandoc runs from a scratch directory; the output directory and both paths handed to pandoc are now absolute. This one was mine, from unit 12.
- **A5: thread names were checked three ways.** `buffer` and `tasks` asked the filesystem, so `Projects/sgb` passed on macOS and flush wrote a wikilink that breaks on Linux. Every command now resolves through `vault.resolve_thread`, stored names are checked with the new `vault.is_thread`, and `threads` drops its own copy of the resolver. `buffer add-*` now accept a bare name and store the canonical `Kind/Name`. `threads`' ambiguity message is now the vault's.
- **A6: `people new` / `threads new` could write outside their folder.** `--name ../x` wrote outside it and `a/b` crashed. Names with `/` or a leading `.` are refused.
- **A7: `hours edit` skipped two checks `hours log` makes.** A rate on unbilled time, and an empty description, are now refused.
- **A8: render bugs frozen in the expected-output files.** Measured against the vault copy first:
  - **Fixed:** a second Summary before any line containing `# Content`, and `#  Details` for a note with no type. No real note triggers either; four expected files change by exactly those lines.
  - **Deferred, with `# DEFERRED BUG` tests and story entries:** completed actions listed as Action Items (42 notes), the PDF replacing a note's own Summary (2 notes), and non-person links as attendees (none). Deferred bug 2, the `[#H]` action row, gets its own pinned test.
- **A9: small bugs.** `tasks rm-depends` can remove a dependency on a deleted task. One non-UTF-8 file no longer aborts the ingest; it is skipped and reported as failed. `search overview --limit 0` means all. The `--depends` help no longer says "prefix". The review's A9.4, `?` date padding, was not a bug: the padding applies exactly when the date is missing.
- **Verified:** `dev/ci` green. All 116 vault-copy notes through all three renderers are still 348 of 348 identical to the old output. Reports, statements, tasks, threads and buffer compare identical on the vault copy apart from the intended changes. **686 passing, 96% coverage.**

## 2026-09-18 - refactor unit 13: commands call each other directly, and the last bash goes

The cleanup unit. Commands no longer run each other as subprocesses, the duplicated readers are gone, `ci.sh` is `dev/ci`, and the Dockerfile and README describe a package rather than a directory of scripts.

- **Direct calls instead of PATH lookups.** `hours`, `payments` and `notes` call a new `buffer.add_ref()`; `tasks add` calls `buffer.cmd_add_action`; `buffer flush` calls `tasks.cmd_default`. `add_ref` holds the best-effort rule in one place: it never raises, and stays silent for `hours` and `payments`, where a warning on stderr would cost the caller its stdout. A failing ingest after a flush now reports itself instead of being lost, and cannot fail the flush: the entries are already in the logs. **The suite runs in half the time** as a result, 96s against 195s.
- **Duplication removed.** `read_frontmatter` and `fuzzy_score` were identical in `threads` and `people`; both now live in `vault`. `tasks` used its own frontmatter thread parser and now uses `vault.parse_frontmatter_doc`, checked against the old one with `tasks list`, `next`, `--overdue`, `--thread` and `search activity` on the vault copy: identical. Their tests moved to `tests/unit/test_vault.py`. What stays duplicated, and why, is recorded in the story.
- **`ci.sh` is now `dev/ci`, in Python.** Same stages, same PASS/FAIL lines, same single corpus harvest shared by both generators. The repo has no bash left. `dev/manual-diff` and the manual prompt refer to it by its new name.
- **Dockerfile.** The image cannot install the package, because the source arrives at runtime as a bind mount, so each command gets a wrapper around `python3 -m adulting.<name>` and `PYTHONPATH` points at the mounted source. Edits on the host still take effect with no rebuild. **taskwarrior is dropped**: no command has shelled out to `task` since tasks became source-of-truth. Verified without Docker by running the same wrappers, `PYTHONPATH` and a system Python against a scratch vault: all ten commands answer `--help-json`, and a note, flush, hours entry and `lint` all behave.
- **pipx verified for real.** `pipx install .` into a scratch `PIPX_HOME`, then `notes new`, `buffer flush`, `tasks list`, `threads list`, `lint` and `notes minutes` against a scratch vault, with nothing installed into the real `~/.local/bin`. The PDF step correctly reported that pandoc was missing from that stripped PATH.
- **README** documents installing with pipx, the editable venv for development, Python 3.11+ with no runtime dependencies, and the command names being generic enough to clash. The design goals no longer claim one file per utility or forbid pip. INTEGRATIONS.md no longer refers to a task backend to set up.
- **The story** (`stories/2026-09-17-python-package-refactor.md`) records the finished state, the eight deferred bugs, each pinned by a test, and the duplication left deliberately in place.
- **Still to do, needing `claude`:** MANUAL.md and `dev/tools/` are generated from the tools themselves and are stale — MANUAL still describes the pickers and prompts. Run `dev/ci generate` to rebuild both. `dev/tools/notes.json` was already rewritten by hand in unit 12 so the gate passes.
- **655 passing, 96% coverage.**

## 2026-09-17 - refactor unit 12: the renderers move to Python and the bash is gone

`notes pdf`, `notes minutes` and `notes agenda` are ported to `src/adulting/render.py`, `notes` becomes this package's command, and the six bash scripts are deleted. The repo has no operator bash left.

- **`notes pdf|minutes|agenda <stem> [--out DIR]`** writes `<stem>.md` and `<stem>.md.pdf` and prints both paths. Renders default to `~/Downloads`, as before; `--out` puts them elsewhere. Nothing opens Preview.
- **`render.py` is a line-by-line port.** Each function names the awk, grep or sed step it replaces: awk's record splitting and `print` newline, `extract_meta`'s quote unescaping, the `people:` list rules, the `--{10,}` section boundary (eleven hyphens or more), `grep | sed | uniq`, the action-table python, the empty-H3 pass and `pad_note_rules`. Files are read and written with `errors='surrogateescape'`, so a note that is not valid UTF-8 survives as it did through awk.
- **Two mistakes caught while porting, before any test ran:** awk's `print` adds a newline after the Summary block that `minutes` inserts, and a real `AGREED:` line reading like the "no agreements" placeholder would have been mistaken for it. Both are covered by tests.
- **Verified against every note in the vault copy: 348 of 348 identical.** All 116 notes through all three renderers, markdown byte for byte, with the same PDF successes and failures. The old outputs were captured by driving the old picker; the old `open` calls were intercepted by a scratch script so nothing launched.
- **Old bugs found, pinned rather than fixed:**
  - **A topic containing a colon or a quote breaks the PDF.** It goes into the pandoc metadata unquoted, so the YAML will not parse. Two real notes are affected: `Recs x Exp: Interference Analysis` and `Principles for Autonomous System Design: OpenClaw Deep Dive`. Six of the 348 renders produce no PDF for this reason, in old and new alike. The markdown is still written.
  - **A `TASK:` line with a priority renders as `| Riaz Arbi | [#H] (Riaz Arbi) Circulate minutes |`.** The `[#H]` stops the assignee matching, so the name stays in the task text and the row is credited to the vault owner.
  - `  -` with nothing after it is not a list item: awk wants a space after the dash.
- **Changed:** a PDF left from an earlier render is removed first, so a failed render cannot leave a stale file looking current. A failed render exits 1 with pandoc's message, where the bash ignored the failure.
- **New `tests/cli/test_notes_render.py`** (24 tests). Six synthetic fixture notes in `tests/fixtures/render/` cover every rule; each `<name>.<kind>.expected.md` beside them is the old bash output, and 18 tests compare the port with those files byte for byte. The rest cover the PDF, the two paths printed, the stale-PDF removal, the `~/Downloads` default, a missing note and `--help-json`.
- **New `tests/unit/test_render.py`** (10 tests) covers the rules one at a time: awk record semantics, quote unescaping, people lists, the owner lookup, horizontal rules and padding, section cutting and filling (ten hyphens are not a boundary, eleven are), `grep | sed | uniq` ordering, action-row dedup and owner fallback, and empty-heading stripping.
- **`notes` is now the package's console script.** Deleted: `notes`, `notes_new`, `notes_pdf`, `notes_minutes`, `notes_agenda`, `notes_strip`. `notes strip`, `edit` and `nano` are gone, as agreed. `ci.sh` no longer has a bash-tools list, and shellcheck now runs on itself only.
- **Agent tools:** every `notes` subcommand used to be blocked because all of them needed a terminal. They no longer do, so the agent may use them; only `delete` stays blocked, as for `threads` and `people`. `dev/tools/notes.json` was rewritten by hand to match, and is regenerated with the rest in the cleanup unit.
- README's notes section now documents the stem-based subcommands. `render.py` coverage 99%, `notes.py` 97%. **656 passing.**

## 2026-09-17 - refactor unit 11: `notes new` from flags

`notes new` joins `src/adulting/notes.py`. Every answer the old prompts asked for is now a flag, and it prints the new note's path instead of opening Obsidian. As in unit 10, it runs as `python -m adulting.notes` until the renderers are ported and `notes` switches to Python.

- **`notes new --type T --topic X --thread T [--thread …] [--person NAME …] [--counterparty X] [--location X]`.** `--type` is one of the seven note types. `--thread` accepts a name, `Kind/Name` or a wikilink, and is repeatable; a repeat is written once. The flags follow the old prompts: `--person` only for Meeting and Correspondence, `--counterparty`/`--location` only for Meeting. Using them elsewhere exits 1 and writes nothing.
- **The note is written exactly as before:**
  - **fields:** topic, type, threads, timestamp, aliases; then for a Meeting, counterparty if given and a `location:` line always, even an empty one; then people.
  - **quoting:** the topic unquoted. In `aliases` and in the names of people without a file, only `"` is escaped.
  - **people:** a person with a file is linked as `[[people/Name]]`.
  - **ending:** `# Content` and a blank line.
- **One buffer REF per thread**, in the order given, with the buffer's output passed through as before. `notes new` still skips the ingest pre-pass.
- **Changed:** an empty `--topic` exits 1 (the old prompt accepted one and wrote a note `lint` rejects). A missing `--type`, `--topic` or `--thread` is a usage error (exit 2) and never falls back to reading stdin. A note already existing at the new timestamp is refused rather than overwritten; the old script overwrote it silently.
- **New `tests/cli/test_notes_new.py`** (23 tests) pins, against output captured by feeding the old prompts on stdin:
  - **each note shape:** a full Meeting (quoting and escaping included), the empty location line, all six other types, and Correspondence people
  - **the rest of `new`:** buffer REF order, thread deduplication, and the note passing `lint`
  - **errors:** five that write nothing, three missing flags, an unknown type, and that `new` does not ingest
- **`tests/unit/test_notes.py`** gains quoting, people linking, and note text for a Log and a Meeting.
- **Verified on the vault copy with real threads and people.** Four notes were created through the old prompts and again through the new flags: a Meeting with quotes, colons, a linked and an unlinked person, counterparty and location; a Meeting with nothing optional; Correspondence with a person; and a two-thread Report. With timestamps masked, all four note files and their buffer REFs were identical. The old script's Obsidian `open` calls were intercepted by a scratch `open` on PATH, used only for that check.
- `tests/cli/test_notes_cli.py`'s `--help-json` expectation now includes `new`. The unit 10 entry below had its passing count corrected to 596. **622 passing.**

## 2026-09-17 - `notes` warns about a failed ingest only on a terminal

Unit 10's ingest pre-pass printed its warning to stderr whenever an ACTION line failed to ingest. The agent harness discards a command's stdout whenever stderr is non-empty, so a single malformed ACTION anywhere in the vault would have made every `notes cat` the agent ran come back empty.

- **The warning now prints only when stderr is a terminal.** Run by hand, you still see it; run by the agent or in a pipe, `notes` stays silent, as the old `2>/dev/null || true` always was.
- **Tests.** One CLI test checks that stderr stays empty when it is a pipe. Another attaches stderr to a real pseudo-terminal (Python's `pty`) and checks for the one-line warning; with the warning disabled, that test fails. The unit test now expects silence.
- The real vault has no failing ACTION lines today, so nothing was affected in the meantime. **596 passing.**

## 2026-09-17 - refactor unit 10: `notes list/cat/last/copy/delete` in Python, named by stem

The first notes subcommands move to `src/adulting/notes.py`, without the numbered picker. A note is named by its stem (`2026-09-10-14-30-00`, with `.md` tolerated), and `notes list` shows the stems.

- **Not yet the `notes` command.** The bash `notes new`, `pdf`, `minutes` and `agenda` only work when launched by the bash `notes` dispatcher, whose exported shell functions they depend on. So the bash `notes` stays on PATH, and the new module runs as `python -m adulting.notes` until those are ported. `notes` switches to Python at the end of unit 12.
- **`notes list [filter] [--json]`** replaces the picker. It shows stem, date, type, threads and topic, oldest first by the frontmatter `timestamp` (the stem when that is missing or malformed), with a case-insensitive filter over every column.
- **`notes cat <stem>`** prints the note, as before.
- **`notes last`** prints the newest note's path instead of opening Obsidian. The old picker sorted on the first ten characters of the timestamp and then on the threads/type/topic text, so on a day with several notes "last" wasn't necessarily the latest. The new one is ordered by full timestamp.
- **`notes copy <stem>`** copies to a new timestamp exactly as before: every line starting with `topic:` gets ` COPY`, body lines included, and the frontmatter `timestamp` is kept. Both are pinned rather than changed. It now refuses to overwrite a note that already has the new timestamp, where the old `cp` would have clobbered it.
- **`notes delete <stem>`** needs `-y` and prints `deleted: <path>`. The old one deleted silently after the picker.
- **Every subcommand still ingests ACTION lines first**, now in-process rather than by shelling out to `tasks`. If any ACTION fails to ingest, it prints `notes: warning: some ACTION lines were not ingested; run \`tasks\` to see why` to stderr and carries on; the old `2>/dev/null || true` hid the failure. `--help-json` does not ingest.
- **Old bug that goes away: the picker could act on the wrong note.** With a filter (`notes cat zeta`) it showed a filtered, renumbered list but selected from the unfiltered one. Choosing `2` from a list of Zeta notes returned an SGB note, and `notes delete <filter>` could have deleted a note that was never on screen.
- **Why the tests were not run against the old script:** its interface was a picker, so tests of the stem interface can't. What the new code keeps from it was checked by driving the old picker with stdin on the same fixtures (`cat` verbatim, `copy`'s ` COPY` lines, the ingest pre-pass), then on real data.
- **New `tests/cli/test_notes_cli.py`** (17 tests) covers:
  - **`list`:** timestamp order over filename order, the filter and its empty messages, the JSON row, and untimestamped notes.
  - **`cat` and `last`:** `cat` after ingest, a trailing `.md`, three bad stems, and `last` including with no notes.
  - **`copy` and `delete`:** `copy` content, and `delete` with and without `-y`.
  - **the ingest pre-pass:** it warns once and carries on, runs before `list`, and `--help-json` skips it.
- **New `tests/unit/test_notes.py`** (6 tests) covers stem resolution, frontmatter reading, the sort fallback, and the silent and failing ingest.
- **Verified on the vault copy.** `list` shows all 116 notes. `cat` output was identical to the old picker's for a 17-note sample spread across the vault. `copy` produced identical files for the oldest, a middle and the newest note. `last` names the note with the newest timestamp.
- `notes.py` coverage 97%. **595 passing.**

## 2026-09-17 - refactor unit 9: `tasks` moves into the package

`tasks` moves to `src/adulting/tasks.py` with a console-script entry point. It has no interactivity, so this is a pure port. It is the highest-risk command for data because it rewrites notes and logs in place, so the verification centres on the lines it writes. With this unit every Python command is packaged. What remains at the repo root is the bash `notes` family.

- **Characterised before the port.** New `tests/cli/test_tasks_output.py` has 19 tests, all green against the old script:
  - **ingest:** exact `--dry-run` output with the file untouched; `--dry-run --quiet`; and a real ingest. That ingest rewrote two good ACTIONs in place, byte for byte around them, and left five failing ones. Those fail on a bad attr set (reported one error per attr), an unknown assignee, an empty body, a note with no threads, and a thread that doesn't resolve, and each gets its exact stderr line. Also: the 60-character summary truncation, the two-space hard break, and the nothing-to-do case.
  - **`list`, `next`, `show`:** the exact table, with multi-thread `+1`, unthreaded `-`, padding and trailing-space stripping; the thread, priority and assignee filters and `(no tasks)`; `next` order; and `show` detail, including threads from a log's singular `thread:`.
  - **uuid prefixes:** the ambiguous and not-found errors.
  - **mutations:** every mutation's output and the exact line it leaves in a log file, including `already done`, `already depends on`, `did not depend on`, and a `people/` prefix on `set-assignee`. Six mutation errors leave the file untouched.
  - **`tasks add`:** passes every flag to `buffer` and returns its exit code. `--help-json` is covered too.
- **Two cosmetic inconsistencies pinned, not fixed:** `set-due`/`set-scheduled` say `date must be YYYY-MM-DD, got …` with a comma where other errors use a semicolon, and the ambiguous-prefix error names files by basename rather than vault path.
- **`ADULTING_HOME` is read per call.** An unused `INTERNAL_DIR` constant is gone. `tasks add` still reaches `buffer` through PATH, and `buffer flush` still reaches `tasks` the same way. Both become direct calls in the cleanup unit, alongside `hours`, `payments` and `notes`.
- **New `tests/unit/test_tasks.py`** (15 tests) covers: anchor parsing of every field; the format round-trip with its hard break; five lines that must not parse (attrs out of order, indented, and others); attr parsing that tolerates the buffer's timestamp and drops bad values; `threads:` lists and a singular `thread:`; priority/due/entry and thread sort keys; the thread cell; validators; and uuid generation. Against a real temp vault it also covers skipping dot-files and dot-dirs, prefix resolution, a mutation rewriting exactly one line with no `.tmp` left behind, and the threads cache.
- **Verified on the vault copy:**
  - **Reads and mutations:** old and new are identical for `list` (plain, `--overdue`, `--priority H`, `--thread "Projects/SANA Partners"`), `next`, `--dry-run` and `--help-json`, and for `show`, `done`, `set-priority`, `set-due` and `set-description` on a real task.
  - **Ingest:** ACTION lines were appended to a real 238-line note and a real AXA DORA log, three good and one with an unknown assignee. Old and new then produced identical stdout, stderr and file changes once the fresh uuids were masked.
- **`ci.sh`** no longer lists root Python scripts; there are none left. `tasks.py` coverage 92% → 99%. **572 passing.**

## 2026-09-17 - refactor unit 8: `buffer` moves into the package; `suggest` stops prompting

`buffer` moves to `src/adulting/buffer.py` with a console-script entry point. It was the least-tested core command: every capture, `tend` and `flush` pass through it, and the suggester behind `buffer suggest` had no tests at all.

- **`buffer suggest` never prompts.** With `-y` it runs the suggestion, as before. Without `-y` it prints the suggested command and stores the raw text as UNKNOWN, with `not accepted (pass -y to accept); storing as UNKNOWN.` That was already the behaviour with no terminal attached, under the message `rejected (no tty, no --yes)`. On a terminal it used to ask `accept? [Y/n]`.
- **`buffer` and `suggester` read `ADULTING_HOME` per call.** `flush` still runs `tasks` from PATH, as before; that becomes a direct call once `tasks` is ported. The `hours` and `payments` REF calls now resolve to the packaged `buffer`.
- **Characterised before the port.** New `tests/cli/test_buffer_cli.py` has 35 tests:
  - **33 kept behaviours, green against the old script.** Covered: every `add-*` line shape, including the fixed attr order and sorted depends; `add-ref --date` filing; all 12 `add-*` errors, none of which writes a buffer; REF targets of every record kind; `list` numbering, filtering and empty messages; `rm` and its errors. For `tend`: the exact regrouped file (groups by thread and date, then UNKNOWN and UNPARSED sections), all nine violation types with the exact stderr, idempotence, and clean and quiet output. For `flush`: the exact log file it creates, appending to an existing log that lacks a trailing newline, attrs carried into the ingested anchor, refusal while `tend` fails, and empty and quiet flushes. For `suggest`: `-y`, no suggestion, and no terminal.
  - **2 changes, failing against the old script first:** `suggest` on a real pseudo-terminal (Python's `pty`, with `y` waiting on stdin) must not prompt, and its help must not mention prompting.
- **Quirks found and pinned, not fixed:**
  - `buffer tend` creates an empty `buffer.md` when there is none.
  - `--quiet` does not silence the `add-*` commands.
  - `buffer --quiet flush` still prints the `tasks` ingest summary, because the `tasks` it runs isn't passed `--quiet`.
  - In the suggester, `!!` never marks high priority: the pattern wraps `!!+` in `\b` word boundaries, which never match around punctuation. URGENT and ASAP work.
- **New `tests/unit/test_buffer.py`** (10 tests) covers attr parsing and its errors, deterministic attr formatting and round-trip, stamps, line classification, regroup order, thread/assignee/REF-target resolution, entry validation, buffer file reads and writes, and shell-quoted suggestions.
- **New `tests/unit/test_suggester.py`** (29 tests) covers the rules pipeline against a pinned today: twelve date phrasings (due vs scheduled, never-today weekdays, past months rolling to next year), priority, eight intent classifications, person matching with surname disambiguation, assignee prefixes, explicit `Kind/Name` directives and their spans, body construction, BM25 ranking on rare terms, the vault loaders and thread index, an end-to-end suggestion, and bailing to UNKNOWN.
- **Verified on the vault copy.** `eval/suggester/score.py` gives identical output for the old and new code against the real vault: 77% full match, 82% thread, 100% out-of-scope, which passes its bar. Old vs new `buffer` was identical for `list`, `list sana`, `tend` and `rm 2`. `flush` differed only in the fresh task uuid from the ingest it triggers, and touched the same files. The `add-*` commands and `suggest -y` differed only in capture timestamps. `suggest` without `-y` and `--help-json` changed only as specified.
- `buffer.py` coverage 55% → 96%, `suggester.py` 0% → 90%; total 82% → 95%. **538 passing.**

## 2026-09-17 - `payments` validates `statement --as-of`; `edit` keeps the date or time you don't change

Two quirks pinned in unit 7, fixed.

- **`payments statement --as-of` is validated in the text view.** A malformed value like `5 July` used to be compared against dates as a string, so it bounded nothing: the whole statement printed with exit 0. It now exits 1 with `payments: bad --as-of '5 July'; expected YYYY-MM-DD`, as `--pdf` already did.
- **`payments edit` keeps whichever of date and time you don't change**, as `hours edit` does. `-t` without `-d` used to be ignored. `-d` without `-t` reset the time to the moment of the edit, which was found while writing the test for the first bug.
- **The two unit 7 tests that pinned the quirks now assert the fixes**, plus one for `-d` alone. All three failed before the change. Valid input behaves as before: on the vault copy, old vs new are identical for `statement --as-of`, `statement --thread … --as-of … --json`, `edit -d … -t …` and `edit -a`. `edit -t` alone now changes the file where the old code changed nothing.
- **464 passing.**

## 2026-09-17 - refactor unit 7: `payments` moves into the package and stops prompting

`payments` moves to `src/adulting/payments.py` with a console-script entry point and loses its interactivity, following `hours`. `vault.prompt` and `vault.pick_thread` had no callers left and are deleted.

- **`payments log` requires a thread.** Without one it exits 2 with argparse's usage error and writes nothing; previously it opened the thread picker and prompted for amount, date, account and note. `log --all` is gone. A thread with no amount still exits 1 with `payments: amount is required`, as before.
- **`payments rm` refuses without `-y`.** It exits 1 with `payments: refusing to delete <id> without -y` and leaves the payment, even if stdin says `y`.
- **The buffer REF finds `buffer` on PATH**, for the same reason as `hours`: the old lookup next to the script would have failed silently inside the package.
- **Characterised before the port.** New `tests/cli/test_payments_output.py` has 24 tests:
  - **20 kept behaviours, green against the old script:** the `log` line with and without an account; six `log` errors, none of which writes a file (including the full no-currency hint); the `list` table, filters, empty output and JSON row; `show` text and a missing id; `edit` of several fields; `edit` errors; `rm -y`; the `statement` table with per-currency totals and a negative outstanding; `--as-of` bounding the text view; the empty statement; and `--help-json`
  - **4 changes, each failing against the old script first:** no picker, `--all` removed, no delete confirmation, and help without "interactive"
- **Two quirks found and pinned, not fixed:**
  - `statement --as-of "5 July"` is not validated in the text view. The bad value is compared as a string and bounds nothing, so the whole statement prints with exit 0. `--pdf` rejects the same value.
  - `edit <id> -t HH:MM` without `-d` silently changes nothing.
- **The one prompt-driven test in `tests/cli/test_payments_cli.py` was removed.** The other 24 pass unchanged, as do the PDF statement tests.
- **New `tests/unit/test_payments.py`** (7 tests) covers amount parsing, JSON amounts dropping `.00`, blank optional fields omitted, `--as-of` parsing, and billed totals being exact Decimals that skip unbilled time. Also collect/find and a single-thread statement against a real temp vault.
- **Verified on the vault copy.** Old vs new were identical for `list` (text and JSON), `statement` (text, `--json`, `--as-of`), `show` (text and JSON), `edit -a` and `rm -y` on a real payment. `statement --thread "SANA Partners" --pdf` gave the same summary line and file. `log` differed only in the fresh id, and touched the same files.
- **Side effect of unit 0, seen here:** the old `statement --pdf` printed a `SyntaxWarning` to stderr (the `\l` in `_statement_pdf.py`'s docstring) whenever Python recompiled it. The agent harness discards stdout when stderr is non-empty, so that could cost the agent the summary line. The new code prints nothing to stderr.
- README's payments table updated. `payments.py` coverage 85% → 97%; total 81% → 82%. **463 passing.**

## 2026-09-17 - refactor unit 6: `hours` moves into the package and stops prompting

`hours` moves to `src/adulting/hours.py` with a console-script entry point and loses its interactivity.

- **`hours log` requires a thread.** Without one it exits 2 with argparse's usage error and writes nothing. Previously it opened a numbered thread picker followed by description, minutes and rate prompts. `log --all`, which only widened that picker, is gone and is now an unrecognised argument.
- **`hours rm` refuses without `-y`.** It exits 1 with `hours: refusing to delete <id> without -y` and leaves the entry, even if stdin says `y`.
- **The buffer REF finds `buffer` on PATH.** It used to look for a `buffer` file next to its own script, which doesn't exist inside the package. The best-effort call would then have failed silently and every `hours log` would have lost its log pointer. An install puts all the commands in one bin directory, and the test harness puts this checkout's commands first. If `buffer` can't be found at all, the REF is skipped, as for any other buffer failure. This becomes a direct function call once `buffer` is ported. The existing REF tests cover it: log, directory-form kind, flush, unbilled, backdated, and split across days.
- **Characterised before the port.** New `tests/cli/test_hours_output.py` has 20 tests:
  - **16 kept behaviours, green against the old script:** the `log` line for billed, config-rated and unbilled entries (with `hours.minutes`/`hours.rate` from config); five `log` errors, none of which writes a file; the `list` table, filters and JSON row; the `report` table, with per-currency totals and `TOTAL unbilled` first; `report` filters and empty output; `show` text and a missing id; `edit` moving date and time while keeping duration, and upper-casing currency; the `edit` errors; `rm -y`; and `--help-json`
  - **4 changes, each failing against the old script first:** no thread picker, `--all` removed, no delete confirmation, and help without "interactive"
- **The two prompt-driven tests in `tests/cli/test_hours_cli.py` were removed**; the no-prompt behaviour they covered is specified above. The other 35 tests pass unchanged.
- **New `tests/unit/test_hours.py`** (6 tests) covers duration, Decimal money, unbilled entries omitting `currency`, the rate cascade (flag, thread, config, default), billing resolution and its two refusals, and append/collect/find against a real temp vault.
- **Verified on the vault copy.** Old vs new were identical for `list` (plain, `--json`, `"SANA Partners" --since`), `report` (plain and `--since … --json`), `show` (text and JSON), `edit -m` and `rm -y` on a real entry. `log` differed only in the fresh entry id, and touched the same files. `--help-json` changed only as specified.
- README's hours table updated. `hours.py` coverage 81% → 98%; total 80% → 81%. **433 passing.**

## 2026-09-17 - refactor unit 5: `threads` moves into the package and stops prompting

`threads` moves to `src/adulting/threads.py` with a console-script entry point and loses its interactivity, following `people`.

- **`threads new` requires `--name`, `--kind` and `--category`.** Missing any of them exits 2 with argparse's usage error, reads nothing from stdin and writes nothing. Previously each missing field opened a prompt, and currency and rate were also prompted unless all three were given.
- **One behaviour removed with the prompts:** giving a currency at the prompt and leaving the rate blank used to write `rate: 2500` into the thread file. With flags, `--currency` without `--rate` writes no rate. Logged hours come out the same: `hours` falls back to `.adulting/config.yaml` `hours.rate`, then 2500, and a test pins that a new billable thread logs at 2500 immediately.
- **`threads delete` refuses without `-y`.** It exits 1 with `refusing to delete <path> without -y` and leaves the file, even if stdin says `y`.
- **Bug fixed: `--name` is now stripped**, as for `people`. `--name "  "` no longer creates `  .md`, and `--name ""` no longer falls through to a prompt.
- **Characterised before the port.** New `tests/cli/test_threads_cli.py` has 28 tests:
  - **22 kept behaviours, green against the old script:** the `list` table in kind-then-name order, `--all`, `--json` fields, fuzzy queries, the empty messages, and `show` as raw text and JSON. Resolution by bare name, `Kind/Name`, wikilink and padded name; case-sensitive misses; an unknown kind directory. The ambiguity error when a bare name exists in two kinds. The exact file `new` writes, with and without billing, plus the duplicate and bad currency/rate/kind errors. `delete -y` by wikilink, not-found and ambiguous deletes, and `--help-json`.
  - **6 changes, each failing against the old script first.**
- **`tests/cli/test_threads_billing.py`:** its 5 prompt-driven tests now use flags, and it gained a test that currency without rate writes no rate. All 10 passed against the old script before the port.
- **New `tests/unit/test_threads.py`** (6 tests) covers thread discovery order and filtering, resolution by path, wikilink and bare name, misses, ambiguity, and frontmatter reading.
- **Verified on the vault copy.** Old vs new were identical for:
  - `list` (plain, `--all --json`, two fuzzy queries)
  - `show` (bare `SGB`, `AXA DORA`, `[[Projects/SANA Partners]] --json`, `Projects/Agent --json`)
  - `delete "Personal Finance" -y`
  - `new` for an unbilled topic and a ZAR project with a rate, and `new` refusing the existing SANA Partners

  `--help-json` changed only as specified.
- **Docs.** README's threads section now documents the required flags and the rate fallback. Found while doing it: MANUAL.md names the fallback key `time.rate`, but the code reads `hours.rate`. MANUAL is regenerated in the cleanup unit.
- Dropped an unused `shutil` import. `threads.py` coverage 48% → 96%; total 78% → 80%. **409 passing.**

## 2026-09-17 - refactor unit 4: `people` moves into the package and stops prompting

`people` moves to `src/adulting/people.py` with a console-script entry point. It is the first command to lose its interactivity, per the refactor decisions: every value comes from arguments, and a delete needs `-y`.

- **`people new` requires `--name` and `--category`.** Missing either exits 2 with argparse's usage error; nothing is read from stdin and no file is written. Previously each missing field opened a prompt.
- **`people delete` refuses without `-y`.** It exits 1 with `refusing to delete <path> without -y` and leaves the file, even if stdin says `y`. Previously it asked for confirmation, and with no terminal attached it crashed with an `EOFError` traceback.
- **Bug fixed: `--name` is now stripped.** Only the prompt path stripped whitespace, so `people new --name "  "` created a file named `  .md`, and `--name ""` fell through to the prompt. A blank name now exits 1 with `empty name`, and `" Igor Novak "` creates `Igor Novak.md`.
- **Characterised before the port.** `people` had no tests. New `tests/cli/test_people_cli.py` has 20 tests:
  - **15 kept behaviours, green against the old script:** the `list` table, `--all`, `--json` fields, fuzzy query ranking, the empty messages, `show` as raw text and JSON (with the `people/` prefix), a missing person, the exact file `new` writes (and that it passes `lint`), creating `people/`, refusing duplicates and unknown categories, `delete -y`, and `--help-json`
  - **5 changes, each failing against the old script first:** no name prompt, no category prompt, no delete confirmation, the blank-name fix, and help text without prompt wording
- **New `tests/unit/test_people.py`** (5 tests) covers the fuzzy-score ladder, wikilink-prefix stripping, frontmatter reading, and person discovery against a real temp vault.
- **Verified on the vault copy.** Old vs new were identical for `list`, `list --all --json`, two fuzzy queries, `show` (raw, and `people/…` with `--json`), `new --name … --category …`, and `delete … -y`. `--help-json` changed only as specified.
- README's people table updated. `people.py` coverage 32% → 99%; total 75% → 78%. **374 passing.**

## 2026-09-17 - `search stream --thread` matches whole thread names

`stream --thread Processes/SGB` also returned every event of `Processes/SGB Extra`. The filter asked whether the resolved ref appeared anywhere inside the event's thread text, which is the event's threads joined with `, `. It now splits that text and compares whole names. An event on several threads still matches each of them.

- **Never triggered in the current vault.** No thread's `Kind/Name` is the start of another's. The one name pair that shares a prefix, `Projects/Agent` and `Topics/Agentic Engineering`, differs in kind, so it never collided. Old vs new `stream` output is identical on the vault copy for the full year, and for `--thread` on SANA Partners, AXA DORA, Agent and Personal Finance.
- **The unit 3 test that pinned the bug now asserts the fix.** `--thread Processes/SGB` returns only SGB events and the multi-thread note. `--thread "SGB Extra"` returns only its own.
- No thread name in the vault contains `, `, the separator the split relies on. **349 passing.**

## 2026-09-17 - refactor unit 3: `search` moves into the package; `vault` reads the vault per call

`search` moves to `src/adulting/search.py` with a console-script entry point. `adulting.vault` stops freezing `ADULTING_HOME` at import. No behaviour change.

- **Characterised before the port.** The existing 23 search tests almost all checked `--json`. New `tests/cli/test_search_output.py` (18 tests), run green against the old script first, pins the text people read:
  - the `notes` and `logs` tables and their match snippets
  - the `activity` table and its default 7-day window
  - the `overview` report, with and without a window and `--limit`
  - the full `stream` chronology: day headers, clock times in local time, the `N more not shown` footer, `--text`, `--reverse`, `--until`, and the empty-window message
  - case-folded thread resolution, the unresolvable-thread and unknown-kind errors, and an empty vault
  - notes dated from their filename when `timestamp` is malformed, and logs that recover their thread from their path
- **Bug found and pinned, not fixed:** `stream --thread` is a substring match. `--thread Processes/SGB` also returns every event of `Processes/SGB Extra`, because the filter asks whether the resolved ref appears inside the event's thread text. It is pinned so the port can't change it silently; fixing it is a separate decision.
- **Also pinned:** within one day, `stream` orders events reverse-alphabetically by kind (`task` before `note` before `done`). This is a side effect of sorting the whole key newest-first.
- **`vault.vault_home()`** replaces the import-time `HOME`, `THREADS_DIR` and `CONFIG` constants. `hours` and `payments`, still scripts, pick this up with their tests unchanged. `tests/unit/test_statement.py` no longer reloads the module to change vaults.
- **New `tests/unit/test_search.py`** (12 tests). Covers event dates, snippets, filters and their newest-first order, the anchor/buffer/self-ref line patterns, and the record readers against a real temp vault: frontmatter-less notes skipped, log thread recovered from the path, self-refs dropped, entities needing a valid `started`, and pending entries. Also thread resolution.
- **Verified on the vault copy.** Old vs new were identical in exit code, stdout, stderr and files touched for `notes` (all, and with `--type`/`--text`), `logs` (all, and `--text`), `activity` (default and since January), `overview` (AXA DORA; Personal Finance windowed), and `stream`. The `stream` runs covered the full year (867 events), `--today`, `--kind hours,payment,pending --json`, and `--thread "SANA Partners" --reverse`. `hours report`, `payments statement` and `--help-json` were checked too.
- `search.py` coverage 84% → 94%; total 72% → 75%. **349 passing.**

## 2026-09-17 - refactor unit 2: `lint` and its schemas move into the package

`lint` moves to `src/adulting/lint.py` with a console-script entry point. `schemas/` moves to `src/adulting/schemas/` and ships as package data, so an installed `lint` finds its schemas without a repo checkout. No behaviour change.

- **Characterised before the port.** New `tests/cli/test_lint_cli.py` (29 tests), run green against the old script first. It covers:
  - **the command surface:** the exact summary line, the `path:line: message` format and exit codes, `--quiet`, explicit paths, a missing path, exit 2 on an empty `--schemas` dir, an alternative `--schemas` dir, the walk skipping dot-dirs, dot-files and `.bak`, and `--help-json`
  - **threads, people and logs:** closed without `ended`, missing required fields, regex constraints, every cadence rule, `thread_entry` lines, and log thread resolution
  - **notes:** thread and people wikilinks, and `ACTION:` description and assignee checks
  - **records:** payments and hours block errors not covered elsewhere
- **Two quirks pinned rather than fixed.** A thread body line like `- 2026-13 — ...` isn't checked at all: it fails `thread_entry`'s `applies_when`, so it is never reported as malformed. A wrong-kind or plain entry in a note's `threads:` is reported twice, once by the field regex and once by wikilink resolution.
- **New `tests/unit/test_lint.py`** (18 tests). It covers the frontmatter parser (scalars, lists, lists of mappings), markdown tables with escaped pipes, and every constraint form. It also pins the prose-becomes-enum trap from 2026-09-07. Further tests: all 10 packaged schemas load, `applies_when`, value and cadence validation, schema matching by directory, filename and type, file discovery, cycle detection, and the vault-wide task and record-id checks.
- **`ADULTING_HOME` is read on every call** (`vault_home()`), as in `commit`.
- **Verified as an installed package.** A wheel built from the tree contains all 10 schemas and the entry point. Installed into a fresh venv, its `lint` validated a scratch vault correctly.
- **Verified on the vault copy.** `lint` and `lint --quiet` produced identical output and exit codes, old vs new: 381 files, 7 violations. `--help-json` and the harvested corpus differ only in the default schemas path shown in `--schemas` help.
- **Tooling:** `dev/manual-harvest` reads schemas from the new location and recognises `vault_home() / '...'` when listing a tool's vault paths. README points at `src/adulting/schemas/`.
- `lint.py` coverage 79% → 96%. **319 passing.**

## 2026-09-17 - refactor unit 1: `commit` is the first packaged command

`commit` moves from a root script to `src/adulting/commit.py` and is installed as a console script (`[project.scripts]`). No behaviour change: `commit` never prompted, so nothing was removed.

- **Characterised before the port.** 12 CLI tests added and run green against the old script first. They cover: a vault that isn't a directory, a vault that is a subdirectory of a repo (refused before `git add -A` can sweep in outside files), an empty message, and the exact `review`, `save` and `--dry-run` output. Also renames shown as `old -> new`, a repo with no commits yet, filenames with spaces and non-ASCII, a real pre-commit hook making `git commit` fail, and `--help-json`.
- **Found dead code.** Current git emits a header even for an empty new file, so `review`'s `[new empty file: ...]` fallback is never reached. The test pins what actually happens. The fallback stays until the cleanup pass.
- **`ADULTING_HOME` is read on every call** (`vault_home()`), not frozen at import, so functions can be unit-tested against a temp repo. The git argv is built per call for the same reason.
- **New `tests/unit/test_commit.py`** (10 tests). Covers `describe`, `split_diff`, `cap_block`, and `status_entries` parsing modified, untracked and renamed paths from a real repo. Also `require_repo` accepting the root and refusing a subdirectory.
- **Verified on the vault copy.** A note was edited, a person file deleted, and a non-ASCII file added in a new directory. Old and new then produced identical `review` output (40 lines), `save --dry-run` output, commit subject and author, and a clean tree afterwards. The only difference was the commit sha. `--help-json` is identical, and the harvested manual corpus differs only in two quoted source lines (`HOME` → `home`).
- **Tooling follows ported commands.** `ci.sh` puts `.venv/bin` and the repo root on PATH and calls each tool by name. `dev/manual-harvest` finds a tool's source and executable in either place, and treats a `.py` module as Python.
- `commit.py` coverage 90% → 96%. **272 passing.**

## 2026-09-17 - refactor unit 0: shared modules move into the `adulting` package

First step of the Python-only refactor (`stories/2026-09-17-python-package-refactor.md`, branch `refactor2`). The five shared modules every command imports now live in `src/adulting/`, so each command can be ported on its own without a `sys.path` hack pointing back at the repo root.

- **Moved and renamed:** `_vault.py` → `vault.py`, `_argparse_helpjson.py` → `helpjson.py`, `_statement.py` → `statement.py`, `_statement_pdf.py` → `statement_pdf.py`, `_suggester.py` → `suggester.py`. Contents unchanged apart from imports and one docstring.
- **Root scripts import `adulting.*`** and their `sys.path.insert` lines are gone. So are the ones in `eval/suggester/score.py` and `tests/unit/test_statement.py`. The scripts now run only under the project venv's Python. `~/bin/adulting` is unaffected.
- **`statement_pdf.py` docstring is a raw string.** Its `\linewidth` raised a `SyntaxWarning` on every import.
- **Verified identical on real data.** `dev/testbed compare` ran 15 commands against the vault copy, old code vs new: `hours report|list`, `payments statement|list`, `search stream|activity|overview`, `tasks list|next|--dry-run`, `threads list --all`, `people list --all`, `buffer list|tend`, `commit review`. Exit code, stdout, stderr and files touched were identical for all of them. `buffer suggest -y` differed only in its capture timestamp.
- **New `tests/unit/test_vault.py`** (22 tests) pins the helpers that don't touch the vault, quirks included: `parse_frontmatter` ignores keys with capitals or digits, and an unclosed block reports no body. The later merge of the five frontmatter parsers can't change them unnoticed.
- **Coverage now reports unimported package files.** `suggester.py` had silently dropped out of the report, making the total read 78%. It is 72%, with `suggester.py` at 0%.
- **`ci.sh`** puts `.venv/bin` first on PATH and syntax-checks `src/adulting/*.py`.
- **250 passing.**

## 2026-09-17 - refactor harness: isolated tests, a vault testbed, coverage in CI

Groundwork for the Python-only refactor. Production code was reaching the test suite, and nothing could safely compare the old implementation with the new one on real data.

- **Two leaks, now closed.** Your shell resolves commands from `~/bin/adulting`, and `buffer flush`, `tasks add` and `notes` call sibling commands by name. The suite therefore ran production code whenever one command called another. Separately, the shell exports `ADULTING_HOME=~/vault`, so any child process that didn't override it wrote to the real vault.
- **New `tests/harness.py`.** `isolated_env()` points HOME and ADULTING_HOME at chosen directories and refuses the production vault. It builds a PATH with this repo first and drops any directory holding another copy of the commands. `command_path()` fails if a command would resolve outside the repo.
- **`tests/conftest.py` isolates the whole session.** `os.environ` is replaced before any test module is imported, so even code that reads the environment at import time can't see production. Every test then gets its own HOME and vault.
- **Tripwire on the production vault.** Every adulting-managed file in `~/vault` is fingerprinted by size and mtime at session start and compared at the end. Any difference fails the run and names the files. Checked against a fake vault that a probe test wrote to.
- **Tests split into `tests/unit/`, `tests/cli/` and `tests/dev/`**, plus 8 harness tests in `tests/unit/test_harness.py`.
- **New `dev/testbed`.** It copies the vault's adulting content to `~/projects/adulting-testbed`. Secrets, `.agent`, `.obsidian`, `.git` and sync markers are never copied. The copy is kept read-only as `pristine/`, with a git-initialised working copy beside it. The reference implementation is extracted with `git archive 119f90b` rather than taken from `~/bin/adulting`, which is a commit behind. `run old|new`, `diff` and `compare` run either implementation against the copy and report what changed.
- **Packaging skeleton:** `pyproject.toml` (setuptools, src layout, no runtime dependencies, `pytest` and `coverage` as dev extras) and an empty `src/adulting/`.
- **`./ci.sh test` reports coverage.** It runs pytest under `coverage run` in the venv, and coverage follows the CLI subprocesses (`patch = ["subprocess"]`), so a command counts as covered whether a test imports it or runs it. A per-file table is printed and an HTML report written to `htmlcov/`. 72% overall. Lowest: `suggester` 0%, `people` 32%, `threads` 48%, `buffer` 55%.
- **Refactor plan** in `stories/2026-09-17-python-package-refactor.md`: ranking, per-command loop, and decisions (deletes need `-y`, notes named by stem, no apps opened, `notes` keeps running `tasks` but warns on failure, command names unchanged).
- **228 passing.**

## 2026-09-17 - `tasks list` groups by thread

`tasks list` ordered purely by priority, due and entry, so one thread's tasks were scattered through the table. It now sorts alphabetically by thread first.

- **Sorts on the thread the table shows** — the first of a task's threads, case-insensitive — so the order matches what you see. Tasks with no thread sort last.
- **Priority, due and entry still order tasks within each thread.**
- **`tasks next` is unchanged.** It answers "what should I do now", which is a question across all threads, so it stays priority-first.
- 1 new test. **220 passing.**

## 2026-09-11 - `search stream` — one chronology of the whole vault

Every store answered its own question and nothing put them side by side: `hours list` showed hours, `tasks list` tasks, `search logs` logs. When a check-in reported four time entries and wrote one, nothing surfaced the gap. `stream` merges every dated record into a single time-ordered view.

- **Nine event kinds** — notes, log lines, tasks opened, tasks completed, hours, payments, threads opened, people added, and unflushed buffer entries as `pending`. Filterable by `--kind`, `--thread`, `--text`, `--since`/`--until`, with `--today` for the verification case and `--reverse` for oldest-first.
- **Effective time throughout.** Each event carries the date the thing happened, taken from the record — never file mtime. A `DONE:` anchor yields **two** events from one line: created at `entry:`, completed at `end:`. That matters because a completion is rewritten in place, so **136 of 167** completed tasks live in a log file filed under a different day than the day they were finished. `due:` and `scheduled:` are intent, not activity, and are not event times.
- **No time column.** 1079 of 1316 events (81%) are date-only — only hours, payments and most notes carry a clock. A dedicated column would have been mostly blank, and filling it with `00:00` would have been a visible lie. The time is appended in parentheses where a record knows it.
- **`hours/` and `payments/` REFs are excluded**, whether flushed or still pending. Those records are already events read from their own files; counting their pointer back into the log would list each one twice. The pending half of that rule was missed at first and found by testing a flush — a test now asserts the record appears exactly once on both sides of one.
- **`notes/` REFs stay in.** A note's REF is its only trace in that thread's log, and the note itself is a separate event at its own date.
- **Reads every source directly rather than tailing logs.** The REF convention makes logs a good human index but not a chronology: a REF exists only after a flush and only for records written since the convention landed, so the vault's 127 existing hours entries have none.
- **1313 events across the whole vault**, 66 in a typical week, 1–15 on a normal day and 32 on one bulk tidy-up. Built in memory, the same order of work `search notes` already does. 9 tests, **219 passing**.
- Immediately useful on real data: the malformed anchors carrying `--due` in their description are visible at a glance, and a 30-completion day reads as one grouped block rather than a wall.

## 2026-09-11 - every record points at itself from the log

`notes new` has always dropped a `REF:` into the buffer so a new note shows up in its thread's daily log. `hours` and `payments` postdate that convention and never adopted it, so a day's log silently omitted the time worked and the money received — the two things most likely to be the whole of a day's activity. The inconsistency was the bug.

- **`hours log` and `payments log` now write a `REF:` too**, best-effort, in the same shape `notes_new` uses. A thread's log for a day is now the chronology of everything that touched it.
- **The CLI writes it, not the agent.** This is the point: over one afternoon the model forgot the accompanying log line twice, in different ways. It cannot forget what `hours log` does itself, and the `activity-capture` skill gets *simpler* — recording *that* the work happened is no longer its job, only the detail beyond the label.
- **`buffer add-ref` rejected the targets outright.** `ref_target_resolves` accepted `notes/`, `logs/`, `people/` and `<Kind>/` — it predates both stores, so a REF could not point at a time entry or a receipt at all. Extended, with the error message and `--help` updated to match.
- **Two bugs hid inside the best-effort swallow.** `--quiet` is a leading flag on `buffer`, not a subcommand flag; and the target was built from `kind` (the frontmatter value, `process`) rather than the directory form (`Processes`), producing an unresolvable `hours/process/SGB`. Both failed silently — entries logged fine, buffer stayed empty, nothing said why. Found only by instrumenting the swallow.
- **The swallow has to stay silent.** The agent harness discards a tool's stdout whenever stderr is non-empty, so `hours log` cannot warn without breaking itself for its main caller. That makes CI the only place this class of failure is catchable, hence 9 new tests — including one asserting the directory form specifically, and one that makes `buffer.md` read-only to prove a failing buffer never costs you the time entry. **208 passing**, up from 201.
- **`buffer add-ref` gains an optional `--date`, and the REF is filed under the day the thing happened.** The first cut used the flush date, so time logged with `-d 2026-09-04` put the entry at 2026-09-04 and its REF in `2026-09-11.md` — the log said the work happened on the day someone got round to recording it. `flush` groups on the date portion of the buffer stamp, so passing the record's own date is enough; the clock time is kept, since it orders entries within a day. Three records dated 09-02, 09-04 and 09-11 now produce three log files, each holding its own.
- **Logs are still not a chronology on their own**, which matters for the planned `search stream`. A REF exists only after a flush and only for records written since this convention landed — the vault's 127 existing hours entries and 4 payments have none. So `stream` reads every source directly and must exclude `hours/` and `payments/` REFs, or each record appears twice.
- **`search activity` now double-counts presence, not arithmetic.** The `HOURS` column is unaffected — it reads `hours/` directly — but `LOGS` and `ENTRIES` rise, because those log lines genuinely exist. Left as-is deliberately: the columns are honest about the logs' contents, and it fixes a real defect along the way, since a thread with time but no writing used to show `LAST -`.

## 2026-09-11 - a named person forces a log line

An hours entry recorded "Call with sisters Nadia and Taz Arbi" and no log line, so the names went nowhere. The mechanical split — a six-word label, leftovers to a log line — permitted the names to be absorbed into the label, leaving nothing over.

- **People cannot live in an hours entry.** A `[[wikilink]]` in an entry's `name` renders but creates no backlink and no graph edge, because Obsidian's metadata cache skips fenced code blocks, and `search` does not index hours either. A name in a label is a name that has gone nowhere.
- The `activity-capture` skill now treats a named person as an unconditional trigger for a log line, with names kept out of the label and wikilinked in the log body, resolved against `people list`. An unresolvable name means loading `create-person`, never inventing one and never quietly dropping it.
- Same root cause as the thread-resolution failure the same day: guidance that *permits* the cheap path rather than *forecloses* it. Both rules are now unconditional.

## 2026-09-11 - half-day activity check-ins, and the notes/logs/hours boundary

Most of a working day leaves no artefact. An email sent, a call taken, a problem chewed over — none of it reaches the vault, so `search activity` reported quiet days that were not quiet. Two weekday check-ins now ask what happened and file the answer, and settling where that answer goes forced the boundary between the three content stores to be written down.

- **Two timer jobs** in `.agent/jobs.yaml`: `midday-checkin` at 13:10 and `evening-checkin` at 17:30, weekdays. Both ask a question and stop; the reply is the input. **13:10 rather than 13:00 is deliberate** — `clear-context` wipes the conversation at 13:05, so a check-in started on the hour would have its own context erased mid-exchange. Starting just after the wipe means it begins clean. The evening job first calls `search activity --since <today>` so it can say what it already has and not make him repeat himself.
- **The prompt wording carries the objective.** "Include anything you spent time on even if nothing came of it: emails, calls, a problem you chewed on." That clause is the point of the exercise; without it the reply lists only things that produced something.
- **New `activity-capture` skill** turns one sentence — "i had a 5k run, fixed the broken alarm, and circulated the sgb minutes" — into records. It splits the reply, resolves threads, **estimates durations and shows them** so they are corrected in one word rather than asked about one at a time, checks `tasks list` for matching pending tasks to close, and proposes the whole batch for a single confirm. Role-prompt classification gains intent 10, with the boundary against intent 4 stated: one finished task closes that task; a list covering a stretch of the day becomes time entries.
- **It does not commit.** The 21:00 `nightly-commit` job does that. Committing per check-in would fragment the history and duplicate an existing job.
- **The boundary, written into the README's conceptual model and thereby into `MANUAL.md`.** Three stores, three questions: a **note** is what was said or decided (heavyweight, a document); a **log line** is what happened on a thread today (lightweight, the general-purpose capture surface that exists so recording something need not mean writing a note); a **time entry** is how long it took.
- **Hours hold a label, not a narrative** — and the deciding argument is mechanical rather than aesthetic: **`search` indexes notes and logs, not hours.** Detail written into an entry's `name` cannot be found again by `search --text`. It is also the only field the Obsidian tracker renders and it appears verbatim on a client's statement of account. So a rich afternoon produces both records: a log line with what actually happened, and a time entry with the duration under a short label. A trivial item — "5k run, 30 minutes" — needs no log line, because manufacturing narrative to fill a slot is the duplication worth avoiding.
- **Considered and rejected: synthesising hours from logs.** Logs carry no duration, so synthesis would have to invent one, and it creates a derived store that can drift from its source.
- **`commit-workflow` gains `hours/` as a third timeline source.** Its Activity timeline read only notes and logs; with a day's work now living in time entries, the nightly commit would have reported it as a file modification under "Vault changes". A changed hours file is always activity.
- **An empirical check first, not an assumption.** A census of all 145 log files: 194 task anchors (73%), 53 `REF:`, 19 `TEXT:`, 0 `ACTION:`. Logs are currently a task substrate. That describes usage, not design intent — `buffer add-text` and `add-ref` exist precisely for the capture role — and reading it as a vacancy was the wrong conclusion, corrected before it reached the tools.

## 2026-09-11 - search returned paths nothing could open

Deployed, `search` cost the agent ~57 tool calls on "what were the key takeaways from the last SGB meeting" and it still failed. Two independent defects compounded, and either alone would have been survivable.

- **`search` emitted vault-relative paths** (`notes/2026-08-31-08-03-32.md`, from `path.relative_to(HOME)`). A reader resolves a relative path against its own working directory, which is not the vault. Paths are now absolute.
- **The container's working directory is an empty, unmounted `/workspace`.** The image sets `WORKDIR /workspace` and nothing is bind-mounted there, so `rg .` reported "No files were searched" and `list_files "."` returned null — the agent could not even discover where the vault was. It guessed `vault/`, `vault/notebooks/`, `/home/riaz/vault` (the *host* path, absent inside the container) and `/`, never `/vault`. `working_dir: /vault` added to the compose service; safe because the agent has no file-writing tool, so nothing can litter the cwd.
- **Neither the prompt nor any skill said where the vault was**, or that `load_skill` exists — `load_skill` was called zero times and the agent tried to `read_file` the skill instead. Both now stated, along with the rule that a failed read is not a cue to guess prefixes.
- **The tests passed against the broken code**, which is the lesson worth keeping. They asserted the filename appeared in the output, never that the path was usable — the wrong contract, tested on a host where the distinction is invisible. Three new tests pin it, one of which `chdir`s to an unrelated empty directory and asserts every returned path still resolves. Confirmed to fail against the old code.

## 2026-09-11 - the harvester silently dropped README subsections

`harvest_readme` split on `#{1,3}`, so a `###` subsection under a harvested `##` heading became a section in its own right, was dropped for not appearing in `README_SECTIONS`, and truncated its parent at that point. The notes/logs/hours boundary was written to the README and never reached the corpus, `MANUAL.md`, or the tool definitions — with nothing downstream to notice.

- Splits on levels 1 and 2 only. Verified surgical: the corpus gains exactly the one intended section, +2106 bytes, nothing else.
- **`tests/test_manual_harvest.py`** — the harvester had no tests at all, despite its output being the sole input to both generated artefacts. Four now: subsections survive, every declared README section is present, every operator tool appears with a non-empty manifest, and two runs are byte-identical (the no-pollution argument rests on that). Confirmed to fail against the old split.

## 2026-09-11 - `hours` records time, billable or not

`hours log` hard-refused any thread without a `currency`, so tracking non-billable time meant attaching a currency to a thread that would never involve money. The tool is called `hours`, not billed-hours: money is an overlay on time, not a precondition for recording it.

- **Currency is now the marker of billability.** A thread carrying one is billed at its rate; a thread without one records `rate: 0` and no currency at all. This shape was forced by a latent trap: `resolve_rate` falls back to `DEFAULT_RATE = 2500`, so a currency-less thread would otherwise have silently billed at 2500/hour.
- **The currency key is omitted, not set to `null`.** Absence is the signal; a null reads as a value somebody forgot to fill in.
- **`--rate` with no currency is the one refused combination** — a charge needs something to express itself in. The no-guessing rule survives exactly where it matters.
- **`resolve_billing` is local to `hours`.** `_vault.resolve_currency` stays strict and untouched, because `payments` must keep it: money *received* always names its currency.
- **`hours report` totals unbilled duration in its own row** rather than folding it into a money bucket or dropping it. **`payments statement` skips unbilled entries entirely** — time that can never be charged for has no place on a statement of account.
- **Three bugs lived in the read paths, not the write path.** `append_entry` and `hours edit` both subscripted `entry['currency']` and raised `KeyError` on an unbilled entry; `statement` bucketed unbilled hours under an empty currency and emitted a spurious row. Found by grepping every `['currency']` subscript across all four tools rather than fixing them as they surfaced.
- **`schemas/hours_file.md`: `currency` optional at both file and entry level.** `lint`'s `ENTRY_FIELDS` is a hardcoded tuple, not read from the schema table, so relaxing the table alone was not enough — `currency` came out of the tuple, and the ISO-code check below it still applies whenever one is present. Optional does not mean unchecked.
- **Two existing tests pinned the old contract and failed, correctly.** `test_missing_currency_fails_with_remediation` and `test_missing_currency_frontmatter_is_flagged` were rewritten to assert the new behaviour rather than deleted, each gaining a companion so the surviving rule is still covered: currency is never guessed *for a charge*, and a currency that is present must still be valid ISO. **194 tests passing**, up from 171.
- **The regeneration caught a stale claim that no test could.** The first rebuilt tool definition still told the agent "A currency is required: `log` refuses to write" — the code had changed but the module docstring, the `-c/--currency` help string and the README's resolution table had not, and those are what the corpus is built from. The generated artefacts propagate whatever the source docs say, so stale prose becomes stale agent instructions. Fixed in all three, then regenerated.

## 2026-09-11 - `search` — notes and logs get a query surface

Every vault entity had a filtered, non-interactive query except the two holding the actual content. 110 notes and 145 log files across 20 threads were reachable only by generic grep, and the agent's `rg` is a single exec with no shell and no pipes, so it cannot intersect two predicates: "notes on SGB" and "notes of type Meeting" were two calls whose results the model had to combine itself. Measured against the real vault, "the last SGB meeting" cost 42 paths plus 80 paths into context, and the shortcut a small model actually takes — thread matches sorted by filename — returned the wrong note for 3 of the 7 threads that have meetings, one out by 13 months.

- **New `search` CLI** — `notes`, `logs`, `activity`, `overview`. Named subcommands rather than one with a `--kind` flag: a small model picks a name more reliably than a mode, and notes and logs genuinely differ in shape.
- **It returns pointers, never bodies.** Path first so the left edge is constant and the string fed to a reader is never pushed around by a long topic; variable-length fields last. Retrieval stays a separate step, so a broad search cannot drag whole documents into context.
- **Ordering is by event date, not capture date** — and this was found by looking at the data, not assumed. A note's filename is when it was written; frontmatter `timestamp` is when the thing happened. They diverge in both directions (an agenda drafted five days before its meeting, a session written up three days after), and **29 of 110 notes differ**. The filename is the fallback only when the frontmatter date is missing or malformed, which is 4 notes today. Honest caveat: this changes no answer to "the last meeting" right now — both keys agree for all 7 threads — but it is the correct key for range queries.
- **`activity` counts hours, not just files.** Notes and logs alone miss a thread worked on but not written about: `Processes/Arbi Family Trust` shows 0 notes and 0 logs against an hour of billable work. Cross-checked entry for entry against `hours report`.
- **`overview` is the whole picture of one thread** — record counts by type, open and done tasks, hours, most recent items — replacing six calls (`threads show`, `tasks list --thread`, `hours report`, `payments statement`, and two searches) with one. It overlaps `threads show` deliberately: that prints the thread *file*, this summarises everything in the vault pointing *at* the thread. Task counts verified against `tasks list --thread`.
- **New `_vault.parse_frontmatter_doc`.** The existing `parse_frontmatter` returns a line index rather than the body and handles only single-line `key: value`, so it cannot read a note's `threads:` block list at all — which is why `tasks` and `lint` each carry their own parser. Added as a *new* function rather than changing the existing one, so the six tools depending on it are untouched.
- **Thread arguments resolve fuzzily** through the same helper `hours` and `payments` use: `SGB` works, with no `threads list` round-trip first. `--limit` defaults to 20 and `activity` defaults to the last 7 days, so the common questions are one call with nothing to compose.
- **13 tests**, pinning event-date ordering, thread-and-type filtering together, bare-name resolution, text reaching log bodies, the hours rollup, unparseable files being skipped rather than fatal, and — explicitly — that every subcommand completes with stdin closed. `search` must never repeat the `hours log` pattern of turning interactive when an argument is absent.
- **Not bundled**: no document bodies, no relevance ranking (recency answers the questions actually asked), no cross-entity search — tasks, hours and payments already have filtered lists of their own.
- **Design recorded** in `stories/2026-09-11-search-vault-retrieval.md`.

## 2026-09-11 - tool definitions declare what they block

`forbidden_args` stopped a call at the agent's loader, but the description still advertised the subcommand, so the model would read "rm ID — delete an entry", try it, and be refused with no idea why. `notes` only looked right by luck: the corpus marked its subcommands interactive, so the model wrote a warning unprompted. Nothing would have hinted at a policy block layered on top.

- **`dev/tools-build` appends a `BLOCKED:` line** to any tool with `forbidden_args`, generated from `POLICY` rather than written by the model, so enforcement and prose come from one source and cannot disagree. `dev/tools-check` verifies they match, and the check was confirmed to fire on an injected mismatch.
- **`--repolicy`** re-applies `POLICY` to existing definitions with no model call, leaving generated descriptions alone. A change to the blast radius should not cost an LLM round-trip; only a change to descriptions should. Idempotent — it strips any prior `BLOCKED` paragraph before re-adding.
- **`notes last` blocked, which blocks all 11 subcommands.** `last` and `edit` open Obsidian via `open`/`xdg-open`, `nano` opens nano, and `pdf`/`minutes`/`agenda` run `open -g` on the rendered PDF. Every subcommand either prompts or launches an application, so the tool is unusable headless in its entirety.
- **`buffer suggest`, `hours rm`, `payments rm` blocked.** `suggest` prompts unless `-y` and nothing routes through it; the two `rm`s destroy records where `edit` is what is almost always wanted.
- **Four interactive paths deliberately left unblocked, with the reason recorded in `POLICY`.** `hours log` / `payments log` with no thread, and `threads new` / `people new` with fields missing, all turn interactive on an argument being *absent* — which `forbidden_args` cannot express, since it matches an argv element. All four are needed non-interactively, so blocking the subcommand would remove the capability. They abort cleanly on EOF, and the descriptions state the requirement instead.
- **`search` registered as `read_only`** with nothing to block.

## 2026-09-08 - agent tool definitions generated from the corpus; `agent-build` deleted

`agent-build` flattened each tool's argparse manifest into a prose blob and threw away almost all of it. The manifest knows `set-due` takes two required positionals; the emitted description said only "Set due date (YYYY-MM-DD)". Every subcommand's arguments and flags were dropped, leaving the agent to guess argv — the root cause of malformed calls. It also carried a hardcoded `TOOLS` list that had never gained `hours` or `payments`, introspected binaries from `$PATH` rather than the repo, and baked the build machine's absolute paths into the output (`lint.json` shipped `/Users/riaz/projects/adulting/schemas`).

- **Deleted and replaced by `dev/tools-build`, `dev/tools-prompt.md`, `dev/tools-check`**, with the artefacts committed at `dev/tools/`. Generation is split by how much judgement each part needs.
- **Descriptions are written by the model.** The agent's loader gives every shell tool one untyped `args: []string` and rejects unknown fields, so a typed parameter schema is impossible and the description is the only channel for teaching the interface. That makes it a writing problem.
- **Safety fields are declared in code, not generated.** `read_only` and `forbidden_args` decide whether an agent can delete a note or hang on a prompt; a generated guess is worse than no guess. A tool with no `POLICY` entry is a hard error, so adding one forces the blast radius to be decided deliberately.
- **`dev/tools-check` runs in the CI gate** — no model call, no network — verifying schema conformance against the loader's `DisallowUnknownFields`, filename/`command` agreement, scope, that each description names every subcommand and flag the tool reports, and that no build-machine path leaked in. All three detectors confirmed to fire on injected faults.
- **`notes --help-json` corrected at source.** Its hand-maintained manifest marked 6 subcommands interactive; in fact every one except `last` opens a picker. Headless they do not fail cleanly — the bash `read` takes EOF, `note_number` is empty, and `sed -n "p"` selects *everything*, so `notes cat` prints the first match and errors on the rest. `agent-build` had been advertising four of those as safe.
- **Everything generator-side lives in `dev/`** because the repo root is on the operator's `PATH`: a `tools-build` at root would be an operator-visible command.

## 2026-09-08 - `notes nano` opened a second, empty file

Found by the shellcheck stage added with `ci.sh`, which flagged `SC2145` on the Linux branch of `nano_note()`.

- The function is called `nano_note $note` with a full path, so `$1` is the file. Both branches appended a literal `note` as a second argument — `nano -"$@" note` on Linux, `nano "$@" note` on Darwin — so **macOS was affected too**: `notes nano` opened the requested note *plus* an empty buffer for a file named `note` in the working directory, and the Linux branch additionally mangled the path with a leading dash.
- Both branches collapse to `nano "$1"`. Proven with a stubbed `nano`: `nano called with: /vault/notes/2026-01-01.md note` became `nano called with: /vault/notes/2026-01-01.md`.

## 2026-09-08 - operators manual generated from the codebase

The README is a project overview written for a reader deciding whether to use these tools. There was nothing written for someone operating them, and nothing an agent could be handed as instructions. `MANUAL.md` is generated, never edited, and regenerated from scratch each time so a previous manual can never shape the next one.

- **`ci.sh`** — the gate is `lint` (python `py_compile`, `bash -n`, shellcheck errors, and a check that every operator tool still answers `--help-json`) plus `test`. Stages run independently and all report before exit, so one run names everything broken rather than the first thing.
- **`dev/manual-harvest`** builds a deterministic corpus from the code: argparse manifests, per-subcommand `--help`, module docstrings, literal exit codes extracted by AST rather than grep, vault paths, environment variables, every schema, and curated README background. Byte-identical across runs, verified.
- **`dev/manual-build`** runs a fresh `claude -p` **from an empty temporary directory with no tools**, passing the corpus as the message. With no repository in scope there is nothing to discover, so no `CLAUDE.md`, memory file or existing `MANUAL.md` can reach the model's context. That, rather than a rule in the prompt, is what makes the no-pollution property hold.
- **`dev/manual-prompt.md`** pins all 35 headings, the table columns, and word budgets, and forbids dates, version numbers and any mention of the generator — operators do not have these tools and must not read about them.
- **`dev/manual-diff`** makes stability measurable: heading tree, the set of documented `tool subcommand` pairs, per-section word drift, and a leakage check for developer-tool names. Byte-diffing two LLM runs tells you nothing; what must be stable is the shape.
- **Stability was the finish signal.** Iteration 1 drifted only where the prompt left free choice (recipe titles, schema subsection granularity). With those pinned, three independent runs produced **35 identical headings and 63 identical documented commands**, at 5841 / 5838 / 5754 words.
- **The manual corrected the README twice**, by preferring the schema as the prompt instructs: the README documented a note's `thread` as a single wikilink where `lint` requires a `threads` list — a shape `lint` actively rejects — and marked meeting `location` required where the schema says optional. Both fixed in the README, along with a missing `Recipe` type and an unlisted `log.md` schema.
- **The corpus is harvested at most once per run.** `--from-json` re-renders markdown from an already-harvested JSON corpus without executing anything, so `MANUAL.md` and the tool definitions are built from byte-identical input as a fact of the run rather than an inference from determinism. Confirmed by instrumenting the harvester: exactly one execution per `ci.sh generate`.

## 2026-09-07 - statement of account rendered to PDF

`payments statement` computed billed-vs-received but could only print a table. A separate project (`ledger/billing`) held an ad-hoc renderer that made a real statement-of-account PDF for one client, marked "remove before delivery", and its handoff asked for it to be migrated here. Two of that handoff's assumptions were already false by the time it arrived: its `parsing.py` read `work.txt`/`payments.txt`, retired hours earlier the same day, and its `reportlab` dependency breaks this repo's stdlib-only design goal. The computation was worth taking; the two ends were not.

- **`_statement.py`** — the ported computation: charges, payments merged into one chronological run of the balance, aging by charge date, and the self-checks. Charges round to whole cents *at the line*, so printed lines always sum to the printed total. `--as-of` filters both sides first: a statement is the account as it stood on that date, and without the filter it ages future charges into `current` and overstates the debt. Payments sort after charges on the same day so a payment settles a balance that already includes that day's work. An overpayment lands as a negative in `current` rather than a phantom aged debt, so the buckets still sum to the balance.
- **Ported in this repo's idiom, not copied.** The source uses `from __future__ import annotations`, frozen dataclasses, full PEP 604 annotations and custom exception classes caught in a `main() -> int`; this repo uses plain functions over dicts, no annotations, `sys.exit`, and `args.func(args)` dispatch. The arithmetic and the comments explaining *why* came across verbatim; the shape did not.
- **Validated against the original as an oracle.** Both were run over the same data on the same day: SANA Partners `36 lines, 79.50 h, charges 151500.00, balance 151500.00`, aging `{current: 80000.00, 30: 36500.00, 60: 17500.00, 90+: 17500.00}` — identical, bucket for bucket. Arbi Family Trust, which exercises the payments path, likewise identical at `79 lines, 101.33 h, charges 162966.67, paid 116067.00, balance 46899.67`. The handoff's reference figures (`35 lines, 78.50 h, R149,000.00`) were simply a stale render, exactly as it warned they might be.
- **`parsing.py` dropped entirely** (~158 lines plus its tests). It read the retired CSVs; the vault is now canonical, and it also holds a hand-triaged row the CSV never had. Replaced by ~20 lines reading `hours/` and `payments/` through `_vault.py`.
- **`reportlab` not adopted.** `pdf.py`'s 391 lines of ReportLab flowables were rewritten as **`_statement_pdf.py`**, generating pandoc markdown rendered by xelatex — the same toolchain `notes pdf`, `notes minutes` and `notes agenda` already use, so the stdlib-only goal holds and nothing new goes in the Dockerfile.
- **Two pandoc layout traps, both found by looking at the rendered PDF rather than trusting it.** Pipe-table cells cannot contain line breaks, so the From/To block collapsed and printed a literal `Riaz Arbi\` — parties moved to a **grid table**, the only markdown table form whose cells hold multiple lines, with a trailing backslash per line because pandoc otherwise soft-wraps an address into one paragraph. And pandoc sizes pipe-table columns in proportion to the dashes in the separator row, so the default widths wrapped `2026-05-11` across two lines mid-value; the separator row is now the layout and is commented as such.
- **Descriptions are escaped before they reach the table.** They are free text written months ago; an unescaped `|` splits a cell and a stray `*` or `_` silently italicises half an invoice line.
- **Party details split by scope**: supplier and banking are vault-wide in `.adulting/config.yaml` under `billing:`; client name, address and VAT live on the thread that bills them. Addresses are pipe-separated — the frontmatter and config readers are single-line only, and teaching them block scalars for one field would not pay for itself.
- **Banking details gate the document, not the render.** While any bank field is missing or still `TODO`, the PDF prints "Banking details not yet supplied" instead of a payment table and the command warns on stderr. A document that asks for money must say where to send it. The real values are the operator's to supply and were deliberately not hunted for.
- **`--pdf` requires `--thread`** — a statement is per client — and refuses a thread with no `client_name` or nothing to state. The output file is unlinked before rendering, not overwritten: a failed render leaves no file rather than yesterday's figures under today's date.
- **`schemas/thread.md`** gains optional `client_name` / `client_address` / `client_vat` / `client_email`. Note again that prose in a constraint cell is parsed as an enum — `pipe-separated lines` became `['pipe-separated lines']` and failed the one thread that had the field, caught by `lint` immediately.
- **Tests: 165 passing**, up from 144. `tests/test_statement.py` covers cent-rounding, lines summing to charges, charge-before-payment ordering, `--as-of` excluding later work *and* later payments, all four aging buckets, oldest-first settlement, aging always summing to the balance, overpayment as negative `current`, rate-0 hours counting but not charging, `--pdf` refusing without `--thread`/`client_name`/content, a real render producing a `%PDF-` file, the stale-file guard, and description metacharacters not breaking a table. PDF tests skip cleanly where pandoc or xelatex is absent.
- **The payment reference is derived, not configured**: the thread name without its `Kind/` prefix (`SANA Partners`, not `Projects/SANA Partners`). It was briefly a single vault-wide value, which would have stamped one client's reference on every other client's statement — a latent wrong-reference bug caught before any statement went out. Deriving it removes the setting entirely, so it cannot drift from the thread or be filled in wrongly.
- **Not bundled**: no invoice numbering, no VAT (the supplier is not registered; the client's VAT number is printed for their records only), no multi-thread or consolidated statements, no emailing. The aging buckets are fixed at current/30/60/90+. `hours` has no `--pdf` of its own — the document is a statement of account, and that lives with `payments`.

## 2026-09-07 - `hours` and `payments` CLIs — consulting time tracking moves into the vault

Time tracking lived outside the vault in a semicolon-delimited CSV written by an iOS Shortcut (`~/Library/Mobile Documents/com~apple~CloudDocs/task_logging/work.txt`, 145 rows, Jun 2022 – Sep 2026) and processed by the separate `worklog` repo. It had silently corrupted itself: three rows whose descriptions contained `;` had shifted every later column, so their parsed `Rate` values were `codereviewwithNick`, `refactorofexistingdagintoextract,phase1andphase2dags`, and `addbusinessintentandcodeintentdoctrinestoeachnodelevelfunction`. `Arbi Family Trust` appeared in five spellings (case + trailing whitespace), splitting its totals. There was no currency column at all, so BWP work for the trust and ZAR work for SANA Partners were indistinguishable and cross-thread totals were meaningless. `Category` was `work` in 145/145 rows and `Status` was `start` in 145/145. Two new CLIs replace it, storing records in the vault where `lint` and git can see them.

- **Format: JSON inside a ` ```simple-time-tracker ` fence.** TOML was rejected on a hard constraint — the repo forbids pip installs and stdlib `tomllib` is *read-only*, so adopting it meant hand-rolling a serializer, which is the exact class of bug being escaped. `json` round-trips in stdlib and escapes delimiters by construction. The shape is Obsidian's Super Simple Time Tracker format, so entries render natively and any tool reading that format can query them; the plugin is **not** installed and is not a dependency.
- **Plugin contract verified against a v1.3.0 clone**, not assumed. `Entry` is `{name, startTime?, endTime?, subEntries?, collapsed?}` (`src/tracker.ts:5-15`); timestamps are ISO 8601 UTC strings with milliseconds, not unix (`tracker.ts:167`, and every `test-vault/` fixture). Extra keys survive a plugin round-trip because `loadTracker` does `JSON.parse(json) as Tracker` — a TypeScript cast, a runtime no-op — and `saveTracker` re-stringifies that same object (`tracker.ts:28`), so `id`/`rate`/`currency` are safe even if the plugin is later installed. The plugin imposes no file structure: it is a code-block processor (`main.ts:27`) and filenames, headings, and frontmatter are invisible to it. Confirmed empirically by running its own `loadAllTrackers`/`getDuration` in node against generated files — parses clean, durations agree with `hours report`, extra keys intact.
- **`name` holds the description, not a label.** It is the only field the plugin renders (`tracker.ts:445` → `572`, `MarkdownRenderer.render`), and these descriptions are invoice line items. A synthetic label there with the description hidden in a side key would have made the table, "Copy as table", and "Copy as CSV" all show a useless column. Thread supplies the category dimension; `name` is what was done. Caveat: a `[[wikilink]]` in a description renders clickable but produces **no backlink or graph edge** — Obsidian's metadata cache skips fenced code blocks.
- **JSON pretty-printed at `indent=2`**, against the plugin's `prettyPrintJson: false` default. The vault is a git repo synced with obsidian-git; a single-line blob makes every append a whole-file change and conflicts unmergeably.
- **New `hours` CLI** — `log`, `list`, `report`, `show`, `edit`, `rm`. `log` with no thread runs an interactive picker matching the `threads new` style. Records live at `hours/<Kind>/<Thread>.md`, mirroring `threads/` so thread → path is a pure function.
- **Defaults cascade flag → thread frontmatter → vault config, and are resolved at write time and stored literally on each record.** Changing a thread's `rate` must never retroactively re-price history, nor a currency change re-denominate it. Confirmed by the data: duration 60 is the mode (93/145) and rate 2500 the mode (34), which are the built-in fallbacks. **Currency is never guessed** — no vault default exists and `hours log` exits non-zero naming the file to edit, because a wrong currency silently corrupts totals, which is one of the defects being fixed.
- **`rate: 0` is an ordinary value, not a sentinel.** 41 of 145 rows are genuinely unbillable work (early Solid Insight, Blog, pre-agreement SANA). Hours count toward duration totals; the money is simply zero. No `billable` flag.
- **Thread resolution is case-sensitive, deliberately.** Three `Arbi family trust` rows resolve on macOS (APFS is case-insensitive) and silently fail on Linux — the platform the `Dockerfile` targets. An importer relying on `Path.exists()` therefore produces a different, quieter result depending on where it runs. The migration folded case *explicitly* and reported every fold.
- **Migration ran once and its tooling was then deleted.** `hours import` classified every row (`CLEAN`/`REPAIRED`/`SUSPECT`/`ORPHAN`/`BLANK`), recovered over-delimited rows with a parse rule that fixes the first five fields and the last (Duration and Rate are numeric-validated at the two ends, so rejoining the middle recovers descriptions containing `;`), and put every `REPAIRED` and `SUSPECT` row through interactive triage rather than guessing. All-or-nothing: nothing was written until the whole file was triaged. Final accounting against the file's 146 data lines — **120 entries migrated, 25 dead-project rows quarantined to `.adulting/hours-import-orphans.txt`, 1 blank line logged**. Verified after the fact: every vault entry has a matching CSV row, there are no duplicates, and all four threads reconcile to the minute (Arbi Family Trust 101h 20m, SANA Partners 79h 30m, Solid Insight 3h 30m, Discover Africa Group 5h 0m). The importer's own summary line undercounted `CLEAN` by one against the file's 146 lines; the rows themselves were all processed. `work.txt` was left untouched and the iOS Shortcut feeding it has been retired.
- **`time/` renamed to `hours/`** so the directory matches the command. The command could not be `time` — that is a zsh/bash reserved word, and `time foo` times a command. Schema renamed `time_file` → `hours_file`, orphan file likewise.
- **`threads new` now collects `currency` and `rate`** (both optional; blank skips, and `--rate` without `--currency` is a hard error rather than a silently ignored flag). Without this, every new billable thread needed a hand-edit of YAML before the first `hours log` would work — hit at exactly the wrong moment. Passing `--kind --category --name` together suppresses all prompting, so existing scripted callers do not start blocking on a new question.
- **New `payments` CLI** — `log`, `list`, `statement`, `show`, `edit`, `rm` — storing money received at `payments/<Kind>/<Thread>.md` in an ` ```adulting-payments ` fence. Its own fence, since no external plugin is involved here. `statement` reads the `hours/` side for billed and the `payments/` side for received and reports the difference per thread and currency, never summing across currencies. Amounts must be positive: a refund is not a negative payment. The legacy `payments.txt` (3 rows) was migrated with three `payments log` calls — three rows did not justify a triage machine.
- **All money arithmetic uses `decimal.Decimal`**, entering via `Decimal(str(x))` so float artefacts never get in. `statement` subtracts one tool's arithmetic from the other's; with floats they would disagree in the last cent. A test asserts `hours report` and `payments statement` produce the same billed figure.
- **New `_vault.py`** extracting the ~200 lines both CLIs share — frontmatter, thread resolution, block splice, config, ISO/local time, money formatting, prompts. Follows the existing `_suggester.py` / `_argparse_helpjson.py` pattern; two copies of the block-splice logic would have drifted. `hours` was refactored onto it with the pre-existing tests passing unchanged, and the real vault verified to report identical totals before and after. Record ids share one namespace across both tools.
- **New `schemas/hours_file.md` and `schemas/payments_file.md`**, plus optional `currency` / `rate` on `schemas/thread.md`. Note that prose in a constraint cell is parsed as an enum by the schema DSL — `wikilink to Projects/X; must resolve` silently became `['must resolve']` and failed every valid file until the cell was emptied.
- **`lint` walks `hours/` and `payments/`** and validates the JSON blocks — a new validator kind, since the existing `scope: file` / `scope: line` DSL does not cover JSON inside a fence, added in the same style as the existing `_task_anchor_per_line` special case. Checks required entry fields, id shape, ISO timestamps, `endTime >= startTime`, ISO-4217 currency, positive amounts, and vault-wide id uniqueness across both tools (following the `cross_check_tasks` precedent). Confirmed to add zero violations to the real vault: 4 before, 4 after, all pre-existing note-timestamp issues.
- **Tests: 144 passing**, up from 92. `tests/conftest.py` gains `write_hours_file` / `write_payments_file` / `entries` / `payments` helpers and `currency`/`rate` on `write_thread`. Covers the delimiter bug that motivated the story (a description containing `;`, `,`, `"` and a wikilink round-tripping byte-identically), the macOS/Linux case-sensitivity trap, currency never being defaulted, `rate: 0` counting hours but no money, cross-currency totals never being summed, ids not colliding across tools, and `0.10 + 0.20 == 0.30`.
- **Not bundled**: no invoice or PDF rendering — `report` and `statement` emit totals, and the rounding rule for invoicing is undecided (`hours report` shows real fractional cents, e.g. 162966.67 BWP, because 20- and 90-minute entries divide unevenly). No running timers: the schema permits a null `endTime` but `hours` never writes one, and every interval is synthesised from a logged start plus a duration, so `endTime` asserts more precision than the capture has. No dataviewjs views — the plugin's API needs the plugin installed, so custom views would have to parse the fence themselves. No `threads set-currency`; thread fields are still edited by hand, consistent with every other field. The 26 quarantined rows are recorded and go no further.

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
