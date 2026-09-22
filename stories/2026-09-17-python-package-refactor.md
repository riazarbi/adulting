# Python-only, pipx-installable adulting

Branch: `refactor2`. Merges to `main` only if the whole refactor succeeds.

**Status (2026-09-22): units 0-13 are done, and so is the review.** Every
command is a module of the `adulting` package, installed with pipx. No bash
remains. The review (`2026-09-22-refactor-review-findings.md`) is worked
through, parts A-E: 705 tests, 96% coverage, `dev/ci` green. CHANGELOG.md
records each part. Still outstanding: regenerate MANUAL.md and dev/tools/
(needs `claude`), the deferred bugs at the end of this file, and the merge
to `main`.

## Goal

1. No bash. Every command is Python, in one package: `src/adulting/`.
2. Installable with `pipx install .`, with dependencies declared in `pyproject.toml`.
3. No interactivity. Every command runs from flags and arguments alone.
   Interactive flows come back later as compositions of these commands.
4. Real tests: unit tests for functions, CLI tests for commands. Nothing mocked.
5. Simple code: an intermediate hobbyist should be able to read it.

## Out of scope

- `notes strip`, `notes nano`, `notes edit`: deleted, not ported.
- New features.
- Changing data on disk. Vault files keep their formats byte for byte.

"Python only" still leaves three external programs: `git` (for `commit`),
and `pandoc` + `xelatex` (for PDFs). No pure-Python replacement is worth
the weight. What goes away: `bash`, `awk`, `sed`, `grep`, `column`, `nl`,
`paste`, `cut`, `sort`, `mktemp`, `nano`, `open`, `xdg-open`.

## Dependencies

Runtime: none. Dev: `pytest`.

Considered and rejected:

| Package | Why not |
|---|---|
| PyYAML | Obsidian's unquoted `- [[Projects/X]]` parses as a nested list, and dates become `date` objects. Silent behaviour changes in every frontmatter read. Revisit after the port if needed. |
| pypandoc | A thin wrapper around the same `pandoc` binary. Adds nothing. |
| rapidfuzz | `difflib` already does the fuzzy `list` ranking. |

## Test harness (done)

Two leak paths existed:

1. **PATH.** Your shell resolves commands from `~/bin/adulting`. `buffer
   flush` calls `tasks`, `tasks add` calls `buffer`, and `notes` calls
   `tasks`, `buffer` and `notes_*`, all by name. The old suite therefore
   tested production code whenever one command called another.
2. **ADULTING_HOME.** Your shell exports `ADULTING_HOME=~/vault`. Any child
   process that doesn't override it writes to production.

What now prevents them:

- `tests/harness.py`: `isolated_env()` sets HOME and ADULTING_HOME to
  directories you choose, and builds a PATH with this repo first
  (`.venv/bin`, then the repo root). It drops any PATH entry that holds
  another copy of the commands. It refuses to use the production vault.
- `tests/conftest.py`: replaces `os.environ` for the whole session, gives
  each test its own HOME and vault, and runs every CLI through
  `command_path()`. That function fails if a command would come from
  outside the repo.
- **Tripwire:** at session end, every adulting-managed file in `~/vault` is
  compared (size and mtime) with a snapshot from session start. Any change
  fails the run and names the files. We checked that it fires, using a
  fake vault.
- `tests/unit/test_harness.py` tests all of the above.

Layout: `tests/unit/` (import and call functions), `tests/cli/` (run
commands as subprocesses), `tests/dev/` (developer tools).

Run: `.venv/bin/python -m pytest`

## Testbed (done)

`dev/testbed` copies real vault content into
`~/projects/adulting-testbed/` (override with `ADULTING_TESTBED`).

- Copied: notes, logs, threads, people, hours, payments, assets,
  .adulting, buffer.md, .gitignore.
- Never copied: `.env-*`, `.agent`, `.obsidian`, `.claude`, `.git`,
  syncthing markers, docker-compose.yml.
- `pristine/` is read-only. `home/vault/` is the working copy, with a fresh
  git repo so `commit` works.
- `baseline/` is the reference implementation, taken from `git archive
  119f90b`. It doesn't come from `~/bin/adulting`, which is one commit
  behind main.

```
dev/testbed reset                   # fresh working vault
dev/testbed run new tasks list      # this checkout
dev/testbed run old tasks list      # reference implementation
dev/testbed diff -p                 # what the run changed
dev/testbed compare search stream   # old vs new: exit, stdout, stderr, files
```

## Ranking: easiest to hardest

Scored on size, interactivity to remove, calls to other commands, external
binaries, existing coverage, and risk of damaging data.

| # | Unit | LOC | Why it sits here | Tests today |
|---|---|---|---|---|
| 0 | Shared modules → package | ~1,500 | `_vault`, `_argparse_helpjson`, `_statement(_pdf)`, `_suggester` move into `src/adulting/`. Mechanical, but everything imports them. | indirect |
| 1 | `commit` | 285 | No prompts, no calls to other commands, git only. | good |
| 2 | `lint` | 788 | Read-only, no prompts. `schemas/` must ship as package data. | good |
| 3 | `search` | 632 | Read-only, no prompts. Needs more coverage for `stream`/`overview`. | thin |
| 4 | `people` | 217 | Remove the name/category prompts and the delete confirm. | none |
| 5 | `threads` | 294 | Same as people, plus currency/rate prompts. | 1 file |
| 6 | `hours` | 441 | Remove the thread picker. Calls `buffer add-ref`. | strong |
| 7 | `payments` | 473 | Same as hours, plus the pandoc statement PDF. | good |
| 8 | `buffer` (+ suggester) | 1,352 | Every capture goes through it. `suggest` prompt. `flush` calls `tasks`. | thin |
| 9 | `tasks` | 733 | Rewrites notes and logs in place (highest data risk). `add` calls `buffer`. | strong |
| 10 | `notes` list/cat/last/copy/delete | ~250 bash | New non-interactive way to pick a note. | none |
| 11 | `notes new` | 142 bash | Frontmatter from flags, YAML quoting, one REF per thread. | none |
| 12 | `notes pdf/agenda/minutes` | ~590 bash | Three awk state machines plus pandoc/xelatex. Hardest to match exactly. | none |
| 13 | Cleanup | — | Calls between commands become function calls. `dev/manual-harvest` runs entry points. `ci.sh` → Python. Dockerfile, README, MANUAL, dev/tools. | — |

Deduplication waits until everything is ported: frontmatter parsers ×5 and
thread resolution ×4. Porting and restructuring in the same step hides
regressions.

For 12, the regression check runs over every note in the testbed. The old
renderer's markdown output is stored once as golden files in the testbed
(never in the repo, because it's private data). The new renderer must
produce the same markdown for every note.

## The loop, per unit

1. **Characterise.** Write CLI tests in `tests/cli/` for current behaviour
   and run them against the old script. They must pass there first.
2. **Specify changes.** For each removed prompt or new flag, write a test
   that fails on the old code.
3. **Port.** `git mv` the script into `src/adulting/<cmd>.py`, add
   `main()` to `[project.scripts]`, and reinstall with
   `uv pip install --offline -e '.[dev]'`. Remove the `sys.path` hack.
   Read `ADULTING_HOME` at call time, not import time, so units can be
   tested.
4. **Unit tests** for the module's functions, in `tests/unit/`.
5. **Gate.** Full suite green, tripwire quiet, `dev/testbed compare` on
   representative commands shows only expected differences.
6. **One commit per unit.**

Calls to commands that aren't ported yet stay subprocesses, resolved on
PATH. When both sides are ported, they become function calls (unit 13).

## Decisions (2026-09-17)

1. **Deletes need `-y`.** `threads delete`, `people delete`, `hours rm` and
   `payments rm` never prompt, and refuse to run without `-y`.
2. **Notes are named by stem.** `notes cat|copy|delete|pdf|minutes|agenda
   <stem>`, e.g. `2026-09-10-14-30-00`. A new `notes list [filter]` replaces
   the numbered picker.
3. **No apps are opened.** `notes new`, `notes last` and the renders print
   the file path instead of opening Obsidian or Preview.
4. **`notes` keeps running `tasks` first.** If that ingest fails, `notes`
   prints a one-line warning to stderr and carries on.
5. **Command names stay** for this refactor. An `adulting <cmd>` umbrella can
   come later.

## Merge consequences

- The agent container bind-mounts this repo and runs the root scripts.
  After merge it needs `pip install /opt/adulting` or similar. Dockerfile
  change in unit 13.
- `~/bin/adulting` stops working as a PATH directory after merge. Switch to
  `pipx install ~/bin/adulting` (or `pipx install -e`).
- Agent tool definitions (`dev/tools/`, vault `.agent/tools`) describe
  interactive notes subcommands. Regenerate after the port.

## Deferred bugs

Each is pinned by a test that asserts today's behaviour and carries a
`# DEFERRED BUG <n>` comment, so `grep -rn 'DEFERRED BUG' tests/` finds them
all, and fixing one means changing that test first. None is a data-loss risk.

1. **A note topic containing a colon or a quote breaks its PDF.** The topic is
   written into the pandoc metadata unquoted, so the YAML will not parse. The
   markdown is still written. Two real notes hit this; both were renamed by
   hand on 2026-09-18. Fix: quote the title and subtitle, which changes the
   rendered markdown for every note.
2. **A `TASK:` line with a priority renders wrongly in minutes and PDFs:**
   `| Riaz Arbi | [#H] (Riaz Arbi) Circulate minutes |`. The `[#H]` stops the
   assignee matching, so the name stays in the task text and the row is
   credited to the vault owner.
3. **`!!` never marks a capture high priority.** The suggester's pattern wraps
   `!!+` in `\b` word boundaries, which never match around punctuation.
   `URGENT` and `ASAP` work.
4. **`notes copy` marks body lines too.** Every line starting with `topic:`
   gets ` COPY`, not only the frontmatter one. It also keeps the original
   `timestamp:`, so the copy sorts at the original's date.
5. **`buffer tend` creates an empty `buffer.md`** when there is none.
6. **`--quiet` is partial in `buffer`.** It does not silence the `add-*`
   commands, and `buffer --quiet flush` still prints the ingest summary.
7. **Cosmetic:** `tasks set-due`/`set-scheduled` punctuate their date error
   differently from every other error, and the ambiguous-uuid error names
   files by basename rather than vault path.
8. **A thread body line like `- 2026-13 — ...` is never checked by `lint`.**
   It does not match `thread_entry`'s `applies_when`, so a malformed date is
   skipped rather than reported.
10. **The PDF replaces a note's own `# Summary` section.** Its callouts go
    after `# Summary` and everything up to the next rule is dropped, so a
    minutes-style Summary loses its `## Minuted Agreements` heading. 2 notes
    in the vault have a Summary.
11. **A non-person link in `people:` is listed as an attendee** as written,
    e.g. `[[Projects/X]]`. No note in the vault has one.

Fixed since the port (2026-09-22), found by the review (A8): minutes inserting
a second Summary before any line containing `# Content`, and `#  Details` for a
note with no type.

Decided 2026-09-22, formerly deferred bug 9: minutes and PDFs list every
action, open and done, with a Status column saying which. Completed actions
used to appear with no way to tell them from open ones.

## Duplication left in place

Review part B moved the shared code into `vault.py`: the vault path, errors,
record fences and minutes, date windows, currency codes, ACTION attributes,
person and thread checks, frontmatter thread lists and the config reader.
What survives is deliberate:

- `search` has its own task-anchor regex, matching anchors as events rather
  than parsing them for mutation as `tasks` does.
- `lint`'s frontmatter parser understands the schema DSL's lists of mappings,
  which no other reader needs; `render`'s `extract_meta` reproduces the old
  scripts' unescaping byte for byte. Both are deliberately separate from
  `vault.parse_frontmatter`.
- `vault.parse_frontmatter` (thread files) and `vault.parse_frontmatter_doc`
  (notes and logs) read differently; merging them risks changing
  `threads show --json`.
- Each command keeps the text of its own error messages; only their shape,
  `<command>: error: <message>`, and the code that prints them are shared.
