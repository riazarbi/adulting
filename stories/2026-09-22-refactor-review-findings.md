# Refactor review: what is left before `refactor2` merges

Branch: `refactor2` at `93246e1`. Reviewed 2026-09-22.

**Verdict: not done.** The port itself is complete: no bash is left, `dev/ci`
is green, and 655 tests pass at 96% coverage. But the review found real bugs
that the tests miss, a lot of copy-paste between modules, and about 75 tests
that add nothing. The goals in `2026-09-17-python-package-refactor.md` that
are not met yet:

- goal 4: "Real tests"
- goal 5: "Simple code: an intermediate hobbyist should be able to read it"

Work through the parts in order. Each part should leave `dev/ci` green.

| Part | What | Estimate |
|---|---|---|
| A | Bugs | ~2 hours |
| B | Deduplicate the source | ~half a day |
| C | Consistency and dead code | ~2 hours |
| D | Tests | ~1 day |
| E | Update the story | 15 minutes |

The rule for every bug below: **write the failing test first**, then fix.

---

## A. Bugs (must fix)

### A1. The PDF statement includes unbilled hours and hours in another currency

- **Where:** `payments.py:289-296` (`one_thread_statement`) never checks
  `e.get('currency')`. The text statement's `billed()` (`payments.py:257`)
  does, and the `hours` docstring promises that statements ignore unbilled time.
- **Effect:** the PDF lists unbilled time as lines and counts it as "written
  off". It also charges a USD entry on a ZAR thread as ZAR.
- **Fix:** skip the entry when `e.get('currency') != currency`.
- **Test:** in `tests/unit/test_payments.py`, add an unbilled entry and a
  USD entry to the thread. Then assert the exact `charges`, `balance` and
  `lines` of `one_thread_statement`. The current `test_one_thread_statement`
  never looks at charges, which is why this slipped through.

### A2. The text statement and the PDF can differ by cents

- **Where:** `billed()` (`payments.py:265`) and `hours.money_of` (`hours.py:69`)
  sum unrounded amounts. `statement.charge_of` (`statement.py:24`) rounds each
  line to the cent.
- **Effect:** the comment at `payments.py:243` says the two "agree exactly".
  They don't.
- **Fix:** use `statement.charge_of(minutes, rate)` everywhere.

### A3. Money goes through `float` before it is displayed

- **Where:** `hours.py:206`, `payments.py:157` and `payments.py:180` store
  `float(...)` in the rows. `vault.fmt_money` then turns the value back into
  a Decimal.
- **Fix:** keep Decimal in the rows. Convert to float only in the `--json`
  branch, as `cmd_report` already does.

### A4. A relative `notes pdf|minutes|agenda --out` loses the PDF

- **Where:** `notes.py:241` keeps the path relative. `render.to_pdf`
  (`render.py:373-380`) runs pandoc with `cwd=` a temp directory, so pandoc
  looks for the file inside that directory.
- **Fix:** `Path(args.out).expanduser().resolve()`.
- **Test:** a CLI test that runs from a scratch directory with `--out rel`
  and asserts `rel/<stem>.md.pdf` exists. Every current test passes an
  absolute path.

### A5. Thread names are checked 3 different ways

- **Where:**
  - `buffer.py:110` and `tasks.py:229` each have a `thread_resolves` (the same
    code twice). It uses `Path.exists()`.
  - `threads.py:22-80` has its own copy of `KIND_DIRS`, `discover_threads`
    and `resolve_thread`.
- **Effect:**
  - On macOS, `projects/sgb` passes because the filesystem ignores case. Flush
    then writes `logs/projects/sgb/` under the wrong casing. This is exactly
    what `vault.resolve_thread`'s docstring (`vault.py:190-193`) says it avoids.
  - `notes new --thread SGB` works, but `buffer add-text SGB` fails.
- **Fix:**
  - Delete all three copies and use `vault.resolve_thread` /
    `vault.discover_threads` / `vault.KIND_DIRS`.
  - Store the canonical `Kind/Name` in the buffer, not what the user typed.

### A6. `people new` / `threads new` can write outside their folder

- **Where:** `people.py:53` and `threads.py:100` build `dir / f"{name}.md"`
  straight from `--name`.
- **Effect:** `--name ../x` writes outside `people/` or `threads/`.
  `--name a/b` crashes with a traceback.
- **Fix:** reject names that contain `/` or start with `.`.

### A7. `hours edit` skips the checks that `hours log` makes

- **Where:** `hours.py:291-294`.
- **Effect:** `--rate` is accepted on an entry with no currency, and an empty
  `--description` is accepted.
- **Fix:** run the same two checks after the flags are applied.

### A8. Two render bugs are frozen into golden files but missing from the deferred list

- **Minutes print the Summary twice.** `render.py:336` checks
  `'# Content' in line`, which also matches `## Content notes`. See
  `tests/fixtures/render/no_summary_with_content_twice.minutes.expected.md`.
- **The PDF drops `## Minuted Agreements`.** `fill_sections` substring-matches
  `# Summary` (`render.py:321`) and skips up to the first rule. See
  `tests/fixtures/render/with_summary.pdf.expected.md`.
- **Decide:** fix both now (they are small), or add them to the deferred list
  and label the golden files. Don't leave them unlisted.
- **Also check these golden files by hand.** They came from the old bash, and
  no one has read them. In `meeting_full.minutes.expected.md`:
  - DONE and `[x]` tasks show up as Action Items.
  - `[[Projects/Not A Person]]` is listed as an attendee.

  `#  Details` has a double space in the `no_frontmatter` golden files.

### A9. Smaller bugs

1. **`tasks rm-depends` can't remove a dangling dependency.** `tasks.py:509`
   calls `find_anchor(dep_uuid)`, which dies if the depended-on task was
   deleted. Match the uuid prefix against `anchor.depends` instead.
2. **One unreadable log aborts the whole ingest.** `tasks.py:281` and
   `tasks.py:331-332` read with strict UTF-8 and no `try`. Skip the file and
   count it as failed, like `walk_anchors` does.
3. **`search overview --limit 0` shows 5 items.** `search.py:461` has
   `args.limit or 5`, but every other `--limit` means "0 for all".
4. **Operator precedence at `search.py:377`.** `r['date'] or '?'.ljust(10)`
   pads only the `'?'`. Write `(r['date'] or '?').ljust(10)`.
5. **The `--depends` help text doesn't match the validation.** `buffer.py:728`
   and `tasks.py:631` say "UUID prefix", but `buffer.py:296` requires exactly
   8 hex characters.

---

## B. Deduplicate the source

The story deferred this "until the port is done". The port is done. Move each
item into `vault.py` (or a small new module) and delete the copies:

1. **`vault_home()`.** It is defined 8 times: `commit`, `buffer`, `lint`,
   `people`, `tasks`, `threads`, `suggester` and `vault`. Import
   `vault.vault_home`.
2. **Hours and payments helpers.** The same logic is written out many times:
   - Fence strings: 5 copies (`hours.py:50`, `payments.py:36,42`,
     `search.py:40-41`, `lint.py:480,550`, `vault.py:37`). Add
     `vault.HOURS_FENCE` and `vault.PAYMENTS_FENCE`.
   - Minutes between start and end: 5 copies (`hours.minutes_of`,
     `search.minutes_between`, `search.hours_in_window`, `payments.billed`,
     `payments.one_thread_statement`). Make one `vault.minutes_of(entry)`.
   - The 3-letter currency check: 6 copies. Make one
     `vault.check_currency(tool, raw)`.
   - The since/until day filter: 4 copies. `payments.billed` should reuse
     `hours.collect`. Add `vault.in_window(day, since, until)` for the rest.
3. **ACTION-attribute parsing.** It lives in both `buffer.py` and `tasks.py`,
   and the two copies have already drifted:
   - `parse_action_attrs`: `buffer.py:125` and `tasks.py:291`.
   - `DATE_RE` and `UUID8_RE`.
   - `assignee_resolves`.
   - `ASSIGNEE_PREFIX_RE` is unused in `tasks.py:65`.

   Keep one copy. The story's reason for keeping two ("they read different
   things") does not justify two sets of validation rules.
4. **Ids, frontmatter and small helpers.**
   - **Ids:** `tasks.gen_uuid8` is the same as `vault.new_id`.
   - **Frontmatter:** `vault.py` has two parsers of its own,
     `parse_frontmatter` and `parse_frontmatter_doc`, and they use different
     key regexes. Keep one.
   - **Note threads:** `tasks.parse_frontmatter_threads` and `notes.py:67-78`
     do the same "threads or thread → list → unwiki" steps. Make one
     `vault.note_threads(fm)`.
   - **Owner:** `render.read_owner` duplicates
     `vault.read_config().get('owner')`.
5. **lint copies.**
   - `lint._find_block` is the same as `vault.find_block`.
   - `lint.unwiki` has the same name as `vault.unwiki` but returns `None`
     instead of the input. Rename it or remove it.
   - `validate_hours_block` and `validate_payments_block` are about 90% the
     same. Make one function that takes the fence, key and required fields.
     While there, rename the `'hours_ids'` bucket that payments also use to
     `'record_ids'`.

**Commands still call each other through fake argparse Namespaces**
(`buffer.py:315, 646-662`, `tasks.py:412`, `notes.py:108`, `buffer.py:533`,
`buffer.py:604`). Split each into:

- a plain function, such as `ingest(dry_run, quiet)`, `add_ref(thread, target,
  summary, date)` or `tend(lines) -> (new_lines, violations)`, and
- a thin `cmd_*` wrapper that only handles argparse.

That is what unit 13 said it did.

---

## C. Consistency and dead code

1. **One error style.**
   - Today there are four:
     - `error: msg` in `tasks`, `buffer` and `commit`
     - `tool: msg` in `notes`, `hours`, `payments` and `search`
     - a bare message in `threads` and `people`
     - print-then-exit-2 in `lint`
   - Add `vault.die(tool, msg, code=1)` and use it everywhere.
   - `search.die(msg, code)` currently ignores `code`, and
     `dev/manual-harvest:141-151` relies on that parameter.
2. **One `main()` shape.** Every `cmd_*` returns an int, and `main` returns
   `args.func(args)` under `sys.exit(main())`. Today `tasks` and `buffer` do
   this, while `notes` and `commit` return None.
3. **One argparse style.**
   - Call the parser `parser` everywhere, and use `dest='subcommand'`
     everywhere (search uses `cmd`).
   - Share one helper for `--since`, `--until` and `--json`.
   - Give every argument help text. `hours list/report/edit` and
     `payments list/statement/edit` have bare flags, so MANUAL.md and the
     agent tools get no description for them.
4. **Type hints.** Only `tasks.py` has them. Remove them to match the rest of
   the code.
5. **Delete dead code.**
   - `buffer.dispatch_proposal`'s add-ref branch (`buffer.py:650-654`) can't
     run, and would crash on `args.date` if it did. Also remove its
     `suggester` add-ref paths:
     - `format_suggestion` (`suggester.py:626-629, 639`)
     - `ref_target` / `ref_summary`
     - the add-ref intent in `classify_intent`
   - Unused imports:
     - `difflib` and `re` in `people.py`
     - `difflib` in `threads.py`
     - `os` in `statement_pdf.py`
     - `TASK_RE` in `lint.py`
   - Unused parameters:
     - `ref` in `hours.resolve_billing`
     - `entry` in `hours.cmd_rm`
     - `p` in `payments.cmd_rm`
     - `tool=` in `statement_pdf.render`
   - `if not tok: continue` after `str.split()` (`buffer.py:133`,
     `tasks.py:297`).
   - `helpjson.py`:
     - the `_id` alias machinery (`:63-68, 84-85`), since no command uses
       aliases
     - the no-op ternary at `:30`
   - In `search.py`:
     - `resolve_thread_arg` can be two lines
     - `cmd_notes` and `cmd_logs` are the same function
     - `cmd_stream` re-implements `window_default`
   - The pointless frontmatter reads in `hours`/`payments` edit and rm
     (`hours.py:314, 324`, `payments.py:225, 235`).
   - `hours.buffer_ref` and `payments.buffer_ref`: call `buffer.add_ref`
     directly.
   - `dev/manual-harvest`: every bash branch (`:51-60, 108-117, 156-160, 169,
     176, 187-193`) and `is_python()`.
   - The `TOOLS` list is defined in both `dev/ci:43` and
     `dev/manual-harvest:42`. Keep one.
6. **Stale comments.** Update each one so it describes what the code does now:
   - `buffer.py:4` ("backend task")
   - `buffer.py:559` ("tw task creation")
   - `buffer.py:592` ("invoking the subprocess")
   - `buffer.py:531`: claims flush is atomic, which it isn't
   - `helpjson.py:4` (`_argparse_helpjson`)
   - `payments.py:283` and `statement_pdf.py:6` (`_statement.build`)
   - `suggester.py:190`
   - `vault.py:1-10`: still says the module is only for `hours` and
     `payments`
7. **render.py still describes awk.** Rename the helpers after what they do,
   such as `grep_sed_uniq` → `matching_lines`. Drop the awk wording in
   comments and in test names such as `test_records_and_joined_match_awk`.
   Don't change behaviour unless the golden files are regenerated on purpose.
8. **Small tidy-ups.**
   - Move function-level imports to the top of the file:
     - `json` in `search.py` (3 places)
     - `math` and `argparse` in `suggester.py`
     - `datetime` in `payments._as_of`
   - Replace the `lambda` + `# noqa: E731` in `hours.py:56` and
     `payments.py:44` with a `def`.
   - Semicolons and trailing whitespace at `search.py:418-428`.

---

## D. Tests

### D1. Delete: unfalsifiable tests

Items marked ★ were confirmed by breaking the code and watching the test still
pass.

| Test | Why it can't fail |
|---|---|
| ★ `unit/test_notes.py:52` and `:57` (`test_ingest_actions_is_silent_…`) | Still pass when `ingest_actions` is replaced with `return`. Rewrite them: seed an ACTION line, then assert it became a `TASK:` anchor. Seed an invalid one, then assert the file is unchanged. |
| ★ `unit/test_statement.py:231` `test_a_failed_render_leaves_no_stale_file` | The render never actually fails. Rewrite it with a `pandoc` on PATH that exits 1, then assert a non-zero exit code and that no file exists. |
| ★ `unit/test_commit.py:87` `test_has_head`, `:91` `test_require_repo_accepts_the_repo_root` | Pass when `has_head` is replaced with `return True`, and when `require_repo` is a no-op. Add `has_head()` False on a fresh repo, and a "not a git repo" case. |
| ★ `unit/test_payments.py:79` `test_one_thread_statement` | Passes if every hours entry is dropped. See A1. Also add a hit case for `find_payment`. |
| ★ `unit/test_lint.py:168` `test_find_cycles_reports_each_cycle_once`, `:174` `test_cross_check_tasks` | The results go into a set, so a cycle reported twice goes unnoticed. The dedup in `cross_check_tasks` can be deleted and the tests still pass. Assert the exact list of `(path, line, msg)`. |
| `unit/test_harness.py:73` | The loop body never runs, because there are no root scripts. Delete it. Also trim `harness.COMMANDS` (it still lists `notes_new` etc.), the repo-root PATH entry in `own_bin_dirs`, and the test at `test_harness.py:52`. |
| `unit/test_harness.py:20` | If the command is missing, `which` prints `None`, `Path("None").resolve()` lands inside the repo, and the test passes. Assert that the resolved path is `.venv/bin/<name>`. |
| `unit/test_vault.py:146`, `unit/test_tasks.py:71-72` (the id tests) | Removing the avoid-existing guard can't make them fail. `int(x, 16) >= 0` is always true. Use `re.fullmatch('[0-9a-f]{8}', …)`, and force a retry to test the guard. |
| `cli/test_hours_cli.py:193`, `cli/test_payments_cli.py:159` (the id collision tests) | 8 random hex digits won't collide in 20 draws. Delete them. |
| `cli/test_smoke.py`, all 6 tests | Each either duplicates another test or asserts `"tasks" in out` on help text that always contains "tasks". Delete the file. |
| `cli/test_schema_task_anchor.py:22` `_lint_violations` and the tests using it | Keep only matching lines, so they pass if lint crashes. `test_kind_must_be_TASK_or_DONE` is vacuous. Assert the exit code and the exact violation line. |
| The 5 "help no longer mentions X" tests (`hours_output:192`, `payments_output:210`, `people:173`, `threads:184`, `buffer:364`) | Any help text passes as long as it avoids one word. Delete them. |
| The 5 "removed flag/subcommand exits non-zero" tests (`hours_output:179`, `payments_output:197`, `tasks_cli:514-526`) | argparse rejects every unknown flag or subcommand, so these can't fail. `test_help_json` already pins the subcommand list. Delete them. |

### D2. Delete duplicates (about 50 tests)

`*_cli.py` and `*_output.py` were split by refactor unit, not by any
principle, and they test the same behaviour.

- **Merge each command's tests into one file,** ordered by subcommand, with
  each behaviour asserted once, exactly.
- **Merge the lint tests into one file.** Today they are spread across
  `lint_cli`, `lint_hours_file`, `lint_task_anchor`, `schema_task_anchor`,
  `payments_cli:172-222` and `hours_cli:256`.

Duplicates to delete:

- `test_threads_billing.py`: 7 of 10 tests duplicate `test_threads_cli.py`.
  Move the other 3 into `test_threads_cli.py`.
- `test_hours_cli.py:52, 88, 100, 117, 177, 230, 237`.
- `test_payments_cli.py:37, 43, 50, 56, 91, 141`.
- `test_tasks_cli.py:110, 170, 179, 201, 221, 253, 295, 317, 378, 459`.
- `test_search_cli.py:56, 86, 249, 274`.
- `unit/test_statement.py:159` duplicates `test_payments_output.py:162`.

### D3. Tighten weak assertions

The rule: assert the **exact** stdout/stderr and the **file on disk**, not a
substring or only the exit code.

- **Money expected values copied from the implementation.**
  `unit/test_hours.py:22` and `unit/test_payments.py:65` compute the expected
  value with the same formula as the code. Use literal numbers.
- **Exit code or substring only.** Assert exact stderr in
  `unit/test_statement.py:170, 177, 186, 206`.
- **Stdout checked, file on disk not checked:**
  - `cli/test_tasks_output.py:240`: never reads buffer.md. Assert the exact
    line.
  - `cli/test_buffer_cli.py:156` (`test_rm` error cases): also assert exit
    code 1 and that buffer.md is unchanged.
  - `cli/test_hours_output.py:144`: assert the stored start/end, rate and
    currency.
  - `cli/test_hours_cli.py:247`: assert the edited minutes.
- **Loose tasks checks:**
  - `cli/test_tasks_cli.py:432`: assert `== 5`, not `0 < n <= 5`.
  - `:148`: assert `end` is today.
  - `:336`: assert the error message and that the file is unchanged.
- **Other loose checks:**
  - `cli/test_search_output.py:163`: parse the JSON instead of matching text.
  - `cli/test_commit_cli.py:85, 145, 208`: assert exact output.
  - `cli/test_payments_cli.py:26`: set TZ and pin the date.
  - `cli/test_lint_hours_file.py:53, 160`: assert the exact violation line.
  - `cli/test_people_cli.py:97`: assert the file's contents.
- **Split and simplify:**
  - `unit/test_notes.py:79`: assert the full meeting template, not a
    substring.
  - `unit/test_hours.py:69`: uses TZ, `tzset()` and `monkeypatch.undo()` in a
    `try/finally`, which also undoes the autouse isolation. Use a small `utc`
    fixture and split the five behaviours.

### D4. Tests tied to implementation details

Rewrite these to test behaviour that users see, or delete them:

- **Private helpers:**
  - `unit/test_tasks.py:54`
  - `unit/test_lint.py:163` (`_rotate_to_min`)
  - `unit/test_people.py:6` (`_resolve_person`)
  - `unit/test_buffer.py:129` (`_shquote`, which should just be
    `shlex.quote`)
- **Regexes:**
  - `unit/test_search.py:68` (`test_line_patterns`)
  - `unit/test_suggester.py:80` (`G.PRIORITY_HIGH`)
- **Tuning constants:**
  - `unit/test_suggester.py:113` (weight 11 / 10)
  - `unit/test_vault.py:73` (0.85 / 0.7 / 0.6)

  Assert which result ranks first instead.
- **Harvester source text:** `dev/test_manual_harvest.py:40` splits the
  harvester's source code to find the section list. Also make `:49` assert
  that `operator_tools` isn't empty.

### D5. Missing tests

1. **The no-prompts guarantee.**
   - Every "refuses without `-y`" test runs with stdin as a pipe, so a prompt
     that only appears when stdin is a terminal would get past all of them.
     This applies to `hours_output:185`, `payments_output:203`, `people:151`,
     `threads:176` and `notes:139`.
   - `search_cli:142` checks only the exit code.
   - Move `run_on_a_terminal` into `conftest.py`. Run every rm, delete and new
     command under a pty with a timeout. Assert the files are unchanged and no
     prompt was printed.
2. **The renderers.** `render.header`, `pdf_markdown`, `minutes_markdown` and
   `agenda_markdown` have no unit tests. Only the golden files cover them.
   After A8, add unit tests for the two render bugs and for the `[#H]` action
   row.
3. **Cross-command paths:**
   - the notes ingest pre-pass for `last`, `copy`, `delete` and
     `pdf/minutes/agenda` (only `cat` and `list` are tested)
   - `buffer flush` reporting a failed ingest
   - `payments log -d` putting the REF in that day's log
4. **Missing or non-directory `ADULTING_HOME`.** Only `commit` tests it. Add
   one parametrized test across all 10 commands.
5. **Lint core in isolation.** `validate_file` and the hours/payments block
   validators are covered only through CLI tests. Fine if the lint file merge
   in D2 keeps them exact.

### D6. Deferred-bug pins

The story says every deferred bug "is pinned by a test". That's not true yet:

| Bug | State | Do |
|---|---|---|
| 2 (`[#H]` in minutes) | Only an unlabelled golden file pins it | Add a unit test in `test_render.py` |
| 4 (`notes copy`) | `cli/test_notes_cli.py:128` presents it as intended behaviour | Rename the test and label it |
| 6 (`--quiet` on `add-*`) | `cli/test_buffer_cli.py:118` is unlabelled | Label it |
| 7 (error punctuation) | `cli/test_tasks_output.py:184, 223` pin it, unlabelled | Label them |
| 8 (thread-entry dates) | `cli/test_lint_cli.py:149` frames it as intended | Rename the test and label it |
| — | `cli/test_notes_render.py:73` only passes *because of* bug 1 | Use a fixture that renders cleanly, or label the dependency |

Today the labels read "Quirk, pinned", "Old bug, pinned" and "Bug, pinned".
Use one grep-able marker, `# DEFERRED BUG <n>`, on every pin.

### D7. Harness and fixtures

- `conftest.py`:
  - Remove the unused imports (`sys`, `REPO_ROOT`).
  - Remove `Vault.run(check=…)`, which nothing uses.
  - Environment isolation happens twice: `pytest_configure` and then the
    autouse fixture. Keep one.
- **Test fixture names mean different things in different files.**
  - `home`, `threads`, `small_vault`, `vault_with_records`, `repo` and
    `notes_dir` are each defined per file. `home` alone means two different
    things.
  - Use the conftest `vault` fixture, or give each fixture a distinct name.
- **Helpers redefined per file.**
  - Each CLI file redefines `write`, `THREAD` and its own run wrappers.
  - The notes tests call `subprocess` directly.
  - `commit` has its own `GitVault` and `REPO_ROOT`.
  - Use the conftest helpers.
- `unit/test_statement.py` holds 7 CLI tests and some `vault` tests. Move them
  to `cli/test_payments_cli.py` and `unit/test_vault.py`.
  `test_charge_precedes_payment_on_the_same_day` asks for `vault` and never
  uses it.
- Delete the stale `legacy` parameter of `cli/test_tasks_cli.py:32`
  `_read_anchor_line`, and the untracked, unused `tests/fixtures/threads/Topics/`.
- Replace the 9 `--help-json` subcommand-list tests with one parametrized test.

---

## E. Update the refactor story

In `2026-09-17-python-package-refactor.md`:

- Correct the status line. It says 655 tests; after D it will be about 580.
- Add A8's two render bugs to "Deferred bugs", or remove them from it once
  they're fixed.
- Rewrite "Duplication left in place" to cover only what survives B.

## Done means

- [ ] Every A item has a test that failed before the fix.
- [ ] `grep -rn 'def vault_home' src/` finds one match.
- [ ] Every command prints errors as `<tool>: <msg>`.
- [ ] No test file named `*_output.py`, `test_smoke.py` or `test_threads_billing.py` exists.
- [ ] Every rm, delete and new command has a test run under a pty.
- [ ] `grep -rn 'DEFERRED BUG' tests/` finds a pin for every deferred bug in the story.
- [ ] `dev/ci` is green.

---
---

# Round 2: re-review of the fixes

Branch `refactor2` at `7cfc429`. Reviewed 2026-09-22.

**Verdict: good progress, not finished.**

What is confirmed:

- `dev/ci` is green, with 705 tests passing and 96% coverage.
- Every part A bug is fixed. Undoing any one fix makes its test fail.
- The deliberate-breakage runs (mutation checks) catch 14 of 15 changes.
- The pty tests, the notes pre-pass tests and the vault-directory check all
  work.
- The Status column (`0dcecf6`) was the owner's decision. Keep it.

What is left:

- one bug that can delete the wrong file
- five smaller bugs, two of them introduced by the fixes
- the part B items that were skipped
- about 40 tests that are still weak or duplicated

The developer declined three items: the notes 3-file split, isolating the
environment twice, and keeping old names in `harness.COMMANDS`. **All three
are accepted.** Don't reopen them.

| Part | What | Estimate |
|---|---|---|
| R-A | Bugs | ~1.5 hours |
| R-B | Unfinished deduplication | ~half a day |
| R-C | Consistency | ~1 hour |
| R-D | Tests | ~2 hours |

As before: **write the failing test first**, and keep `dev/ci` green after each
part.

## R-A. Bugs

### R-A1. `people delete` and `people show` accept a path (must fix first)

- **Where:** `people.py:58-73` (`_resolve_person`) never calls
  `V.is_plain_name`. The A6 fix protected `new` only.
- **Reproduced:** `people delete ../threads/Projects/Foo -y` deleted the thread
  file and exited 0.
- **Fix:** in `_resolve_person`, die when `not V.is_plain_name(name)`.
- **Also check:** every other command that builds a path from a user-supplied
  name, such as `threads show/delete` and `notes cat/copy/delete <stem>`.
- **Test:** a CLI test that asserts exit 1, the exact error and that the vault
  is unchanged. Add `people delete ../x -y` to the refusal cases in
  `test_no_prompts.py`.

### R-A2. Two thread checks still test whether the file exists (finishes A5)

- **Where:**
  - `buffer.ref_target_resolves` (`buffer.py:129-146`), used by `add-ref` and
    `tend`
  - `lint.wikilink_exists` (`lint.py:315`)
- **Effect:** on macOS, `buffer add-ref SGB Projects/sgb` is accepted and
  buffers `REF: [[Projects/sgb]]`. lint passes a note with
  `threads: [[Projects/sgb]]`.
- **Fix:** resolve thread targets with `V.resolve_thread` / `V.is_thread`.
  Person checks do the same thing (`vault.py:484`, `notes.py:121`,
  `lint.py:472`). Give them one case-exact helper too.
- **Test:** both cases above, refused or reported.

### R-A3. A failed nested ingest is reported as `failed: 1` and exits 0

- **Where:**
  - `buffer.py:579-582` catches `(Exception, SystemExit)` around
    `tasks.ingest()`.
  - `notes.py:103-107` does the same.
  - `notes new` calls `buffer.add_ref` (`notes.py:146`). A `die` inside it
    prints `notes: error: …`, then the command carries on and exits 0.
- **Root cause:** the plain functions from B still call `V.die` / `sys.exit`.
  The fix is R-B1.
- **Test:** make a `die` fire inside ingest. Assert that the warning quotes the
  real message, not `1`.

### R-A4. The A8 fix narrowed too far

- **Where:** `render.py`, the check for whether the note has a `# Content`
  heading. It now matches `line.strip() == '# Content'` exactly.
- **Effect:** a note with no Summary whose heading is `# Contents` or
  `# Content and notes` now gets no Summary or Action Items block at all. No
  note in the vault has such a heading today.
- **Fix:** match a level-1 heading that starts with `# Content`, and exclude
  `##` headings.
- **Test:** a unit test with `# Contents`.

### R-A5. Smaller bugs

1. **An empty dependency prefix removes a live dependency.** `tasks rm-depends
   X ""`, or any 1-character prefix, silently removes the task's only
   dependency. Require a non-empty prefix. If the prefix matches more than one
   dependency, refuse and say it is ambiguous.
2. **The text statement can be a cent out.** `payments.billed` now rounds
   charges, but receipts are summed unrounded. A hand-edited amount of `2.675`
   shows `received 2.68` but `outstanding 2497.32`. Round receipts the same
   way.
3. **`hours edit` can't fix a broken entry.** An entry that already has a rate
   but no currency can't be edited at all, not even with `-m`. The error also
   names `--rate` when that flag wasn't passed. Check the entry's final state,
   and name the fields that are actually wrong.
4. **`suggester.main` has the old shape.** `suggester.py:595` returns None,
   has no `sys.exit(main())`, and prints a traceback on a bad `--today`.
5. **Errors name `notes.py` under `python -m`.** The `<tool>:` prefix comes from
   `argv[0]`, so under `python -m adulting.notes` errors read
   `notes.py: error:`. Set `prog=` on every parser, as notes already does, and
   have `die` use it.

## R-B. Unfinished deduplication (part B leftovers)

Round 1 asked for these, and they were skipped without saying so. Either do
them, or write down why not under "Duplication left in place" in the
refactor story.

1. **Library functions exit the process.**
   - `buffer_ref`, `buffer_action`, `tasks.ingest` and `tend` print and call
     `V.die`, so callers need `redirect_stdout` and
     `except (Exception, SystemExit)` (`buffer.py:287-294`, `buffer.py:580`,
     `notes.py:103`).
   - Make them raise `ValueError` and return their results. Only `cmd_*`
     prints or calls `die`.
   - `tend(lines) -> (new_lines, violations)` as asked in round 1.
   - This fixes R-A3.
2. **One frontmatter parser.** `vault.parse_frontmatter` (`:137`) and
   `parse_frontmatter_doc` (`:157`) both remain, with different key regexes.
   `read_config` has a third. Keep `parse_frontmatter_doc` and delete the
   rest, including the new `read_frontmatter` wrapper.
3. **One ACTION-attribute validator.** `buffer.buffer_action`
   (`buffer.py:255-268`) still has its own due/scheduled/depends checks, with
   different messages from `V.parse_action_attrs`, and it never checks
   priority. Build the tokens, run `V.parse_action_attrs`, then die on the
   first error.
4. **`V.check_currency(raw)`.** The "is it a 3-letter code, else die" check is
   still written out 5 times: `hours.py:94, 297`, `payments.py:213`,
   `threads.py:44` and `vault.resolve_currency`. The new `is_currency_code`
   covers only half of it.
5. **Other leftovers:**
   - **Walkers over the hours records.** `payments.billed` (`:245-270`)
     should reuse `hours.collect`. That leaves `one_thread_statement` and
     `search.hours_in_window` as the only other walkers.
     `search.apply_filters:286` and `cmd_stream` still write out the date
     window check.
   - **lint block validators.** `validate_hours_block` and
     `validate_payments_block` are still two ~35-line copies. `read_block`
     takes 6 parameters. Make one validator that takes a single `label`.
   - **"Resolve a thread or die"** exists 3 times: `V.resolve_target`,
     `buffer.canonical_thread:100` and `threads.cmd_show:125-130`.
   - **people/threads** still repeat `today()`, `CATEGORIES`, the fuzzy-score
     block (`people:97-106` / `threads:103-112`) and `show --json`.

## R-C. Consistency

1. **Use the shared constants directly.** Several modules copy them into local
   names instead:
   - `FENCE = V.HOURS_FENCE`
   - `payments:36,42`
   - `search:40-41`
   - `lint:478,550`
   - `threads:19 KIND_DIRS`

   Use the `V.` names. Also:
   - `search.DATE_RE` shadows `V.DATE_RE` with a different pattern. Rename it.
   - `search.BUFFER_LINE_RE` and `ANCHOR_RE` duplicate `buffer`/`tasks`.
2. **One naming style.**
   - `vault_home`: 7 modules use `from adulting.vault import vault_home` while
     also using `V.`. Use `V.vault_home()` everywhere.
   - Subparser variables use 4 naming styles (`p`, `p_xx`, `ls/rep/sh`,
     `n/l/a/o`, with `l` triggering E741). Use `p = sub.add_parser(...)`
     everywhere.
3. **Dead code.**
   - `tasks.cmd_rm_depends:450-457`: the `mutate_anchor` branch can never run.
   - `if not tok: continue` moved into `vault.py:494` instead of being deleted.
   - The first `except Exception` in `search.hours_in_window:310-329` can never
     trigger. Delete both handlers.
   - The mkdir in `buffer.write_buffer:156` is unreachable now that
     `require_vault` runs first.
   - `commit.require_repo:54` calls `require_vault` a second time.
   - `resolve_thread_arg` (`search:266`) is still 4 lines.
   - `notes.buffer_ref:143` is a wrapper that adds nothing.
   - `search.cmd_overview` has a `render(_)` closure that is called once.
   - `hours.cmd_edit` / `payments.cmd_edit` throw away the record that
     `find_entry` returned, then search for it again.
4. **Validate or catch, not both.** `tasks.validate_date` /
   `validate_priority` (`tasks:208-218`) raise only to be caught and passed to
   `die`. Die directly. Add `choices=` on `set-priority`.
5. **Comments that tell history.** Replace these with what the code does now:
   - `buffer.ref_target_resolves:130-133` ("were simply missing")
   - `notes:21, 115, 128, 221` ("as the old bash did")
   - `render:3`

Also: `hours list --since x` is accepted silently. Validate `--since` and
`--until` in `add_window_flags`.

## R-D. Tests

### R-D1. Tests that can't fail, or pin a bug without saying so

1. **`unit/test_vault.py:148` `test_new_id_…`.** Deleting the avoid-existing
   guard still passes all 705 tests. Round 1 asked for a forced retry.
2. **`unit/test_render.py:177` `test_pdf_markdown`.** It pins deferred bug 10
   and calls it "as the bash always did". Add `# DEFERRED BUG 10` and reword
   the docstring.
3. **`cli/test_lint_cli.py:130`.** `violations() == []` with no return-code
   check passes even if lint crashes. Assert `(rc, stdout, stderr)`.
4. **`cli/test_no_prompts.py:77` `test_no_command_reads_stdin`.** It greps the
   source, and `os.read(0)` gets past it. Either keep it as a lint rule in
   `dev/ci` and delete it from the tests, or keep it and add a docstring saying
   the pty tests are what actually protect this.
5. **The pty refusal gaps.**
   - Add `buffer rm`, which deletes with no `-y` at all, and
     `hours edit` / `payments edit`.
   - Assert the exact refusal message on stderr, not only that the last line
     has no `?`.

### R-D2. Delete: duplicates

| Delete | Duplicate of |
|---|---|
| `cli/test_search_cli.py:489` `test_never_prompts_without_a_tty` (exit code only) | `test_no_prompts.py:83` |
| `cli/test_thread_names.py:48, 53` | `test_threads_cli.py` `test_show_not_found[sgb]`, `test_bare_name_in_two_kinds_is_ambiguous` |
| `cli/test_buffer_cli.py` `test_suggest_never_prompts_even_on_a_terminal` | `test_no_prompts.py` `test_suggest_stores_unknown_on_a_terminal_without_asking` |
| `cli/test_notes_cli.py:200` `test_new_does_not_ingest` | `test_notes_new.py:149` |
| `cli/test_tasks_cli.py:358` `test_next_sort_priority_first` | `:338` `test_next_orders_by_priority_due_entry` |
| `cli/test_hours_cli.py:74, 275, 296, 409, 430` | `:46, :254, :266, :399` |
| `cli/test_payments_cli.py:96, 177, 270` | `unit/test_payments.py:26`, `:170`, `:316` |
| `cli/test_buffer_cli.py` `test_flush_keeps_action_attrs_in_the_log_line` | `test_flush_writes_logs_…` |
| `notes_render.py:111` (help-json) | the parametrized `--help-json` test |

After that:

- Move what is left of `test_thread_names.py` into `test_threads_cli.py` or
  `test_buffer_cli.py`.
- Move what is left of `test_review_small_bugs.py` into the files for its
  commands (tasks, search, buffer). Name each test after the behaviour it
  checks, not after the review.

### R-D3. Make exact

- **Tasks mutation tests.** `cli/test_tasks_cli.py:461-556` has 10 `set-*`,
  `add-depends` and `rm-depends` tests that check substrings. Fold them into
  the exact, parametrized `test_mutations_print_and_rewrite_the_line` (`:406`).
  Also make `:276-308` exact.
- **Other substring checks:**
  - `search_cli:150, 170, 181, 187`
  - `commit_cli:91, 235, 242, 251`
  - `buffer_cli` `test_tend_reports_unresolvable_ref_targets_and_assignees`
- **"Clean" lint tests.** The 13 tests that check only `returncode == 0`
  should assert `(0, "", "")`.
- **Tests that only exercise argparse.** Either assert what they add (the file
  is unchanged, the exact message) or delete them:
  - `people_cli:106, 112, 128`
  - `notes_new:144`
  - `threads_cli:169`

### R-D4. Test behaviour, not internals

- `unit/test_lint.py:167` (`_find_cycles`) and `unit/test_payments.py:34`
  (`_as_of`) test private helpers. Test through `cross_check_tasks` and
  `payments statement --as-of`.
- `unit/test_statement.py:35, 55, 111` restate invariants that `S.check()`
  already enforces inside `build()`. Delete them, or replace them with one
  test that a broken input makes `build()` raise.
- `unit/test_vault.py:127` computes its expected value with `json.dumps`, the
  same call as the code. Write the expected text out literally.
- Every CLI file still defines its own run wrapper (`hours()`, `pay()`,
  `buf()`, `people()`, `threads()`, and `notes()` twice). Use `vault.run(…,
  cli=…)`.

## Round 2 done means

- [ ] `people delete ../x -y` exits 1 and changes nothing. A test proves it.
- [ ] `grep -rn 'exists()' src/adulting/` finds no check of a thread or
      person name.
- [ ] `grep -rn 'SystemExit' src/adulting/` finds nothing outside `vault.die`.
- [ ] `grep -rn 'def parse_frontmatter\b' src/adulting/vault.py` finds nothing,
      and exactly one frontmatter parser remains in `vault.py`.
- [ ] Deleting the avoid-existing guard in `vault.new_id` fails a test.
- [ ] `tests/cli/` has one file per command, plus `test_no_prompts.py`,
      `test_every_command.py` and the three notes files.
- [ ] Every R-D2 row is deleted, and each deletion was checked against its
      counterpart first.
- [ ] `dev/ci` is green.

---
---

# Round 3: round 2 accepted, and a fresh look at the whole codebase

Branch `refactor2` at `c968b38`. Reviewed 2026-09-23.

## Round 2 is done. Accept it.

Every R-A, R-B, R-C and R-D item is done except one lint test (R3-B6 below).
Checked two ways: undoing each fix brings back the original failure, and 9 of 9
deliberate breakages of the round 2 code were caught by a test.

- **All six departures were right.** In particular `2.675` really doesn't
  reproduce; the bug was two receipts of `1.005`, and that is what was fixed.
  Don't revisit any of the six.
- **No regressions.** `src/` is 110 lines shorter, 737 tests pass, 97%
  coverage, `dev/ci` green.
- **The vault link report is correct.** `notes/2026-05-13-17-28-09.md` links
  `[[people/Ralph Van Niekerk]]`; the file is `Ralph van Niekerk.md`. Fix the
  link, not the code.

This round is a **fresh pass over the whole codebase and test suite**, by
reviewers who had not seen rounds 1 or 2. Almost everything below predates
those rounds. It was never found because it was never looked at.

**Grades: code B+, tests B−.**

| Part | What | Estimate |
|---|---|---|
| R3-A | Bugs, worst first | ~half a day |
| R3-B | The tests' real weakness | ~1 day |
| R3-C | Code quality | ~half a day |
| R3-D | Docs and schemas that lie | ~1 hour |

Same rule as always: **write the failing test first.**

## R3-A. Bugs

### R3-A1. `payments statement --pdf` ignores `--since` and `--until`

- **Where:** `payments.py:314-318` routes to `cmd_pdf`, which calls
  `one_thread_statement(args.thread, _as_of(args.as_of))`. The window flags
  never arrive. `one_thread_statement` (`payments.py:262-293`) re-walks the
  hours records by hand instead of using `H.collect`, which is how the filter
  got lost.
- **Reproduced:**
  - `payments statement --thread Projects/Acme --since 2030-01-01` prints
    `(nothing to report)`.
  - The same command with `--pdf out.pdf` writes `2 lines, charges 2000 ZAR`.
- **Why it matters most:** this puts a period on a client document that the
  operator did not ask for. Everything else in this file is cosmetic next to
  it.
- **Fix:** have `one_thread_statement` take the window and use
  `H.collect(thread, since, until)`, so both views walk the records once, the
  same way. If a windowed PDF is not wanted, refuse the combination instead.
- **Test:** the same thread rendered both ways with and without a window, with
  the line counts and totals asserted.

### R3-A2. `--help-json` anywhere in the arguments hijacks the command and exits 0

- **Where:** `helpjson.py:86-89` scans `sys.argv` before `parse_args`, so it
  sees positional data too. `--` does not stop it.
- **Reproduced:** `buffer add-text -- '--help-json'` prints the manifest, exits
  0, and writes no buffer line. The same goes for
  `commit save --message '--help-json'` and `notes new --topic '--help-json'`.
- **Why it matters:** the caller is told the write succeeded. Silent data loss,
  with a success code, in the tool an agent drives.
- **Fix:** register `--help-json` as a real argparse flag on the top-level
  parser and handle it after `parse_known_args`.
- **Test:** each write command with `--help-json` as data. Assert the record
  lands.

### R3-A3. A malformed `rate:` silently bills at the built-in default

- **Where:** `vault.thread_meta` (`vault.py:335-339`) swallows the `ValueError`
  and returns `rate=None`. `hours.resolve_rate` (`hours.py:66-72`) then falls
  back to 2500.
- **Reproduced:** a thread whose frontmatter says `rate: 1,000` lints clean,
  and `hours log` bills it at 2500.
- **Fix:** `thread_meta` must tell "no rate" from "a rate I could not read",
  and die on the second, as `resolve_currency` already does for a missing
  currency. Money is never guessed anywhere else in this code.
- **And the reason lint missed it:** lint parses each schema's `type` column
  into `schema['fields'][name]['type']` (`lint.py:203`) and **never reads it
  again**. The `int` and `string` types in all ten schemas are decorative.
  Either enforce the column or delete it.

### R3-A4. `lint <relative-path>` invents a violation and exits 1

- **Where:** `lint.py:317`. For a relative argument `home in path.parents` is
  false, so the caller's own prefix survives into the scope check.
- **Reproduced:** from the vault's parent, `lint vault/threads/Projects/Acme.md`
  reports `no matching file schema` and exits 1. The same file by absolute path
  is clean.
- **Fix:** resolve the path in `main` before anything else, then use
  `is_relative_to(home)`.

### R3-A5. Smaller bugs

1. **`tasks list --thread SGB` silently returns nothing.** `tasks.py:503`
   compares the raw string to the canonical `Kind/Name`. Every other
   thread-taking command resolves a bare name through `V.resolve_target` and
   errors when it can't. Failing by printing a plausible empty answer is the
   worst of the options. Use `V.resolve_target`.
2. **`ACTION:` with attributes but no text ingests the HTML comment as the
   task.** `tasks.py:38-39`: the lazy body swallows the comment. `ACTION:
   <!--due:2026-01-01-->` becomes a task whose description is
   `<!--due:2026-01-01-->`, and the `due:` is dropped. Anchor the attribute
   group before the body can take it.
3. **`tasks` and `lint` disagree about a bare `ACTION:` line.** `tasks.py:38`
   uses `(.+?)` and skips it silently; `lint.py:25` uses `(.*?)` and reports
   `missing description`. Whichever is right, one regex.
4. **The PDF ledger's Hours column doesn't add up.** `statement_pdf.py:136,142`
   rounds each line but totals unrounded: three 50-minute entries print `0.83`
   three times under a total of `2.50`. Same class as the round 2 money fix,
   which only covered the money columns.
5. **`search` folds thread-name case; nothing else does.** `search.py:254`
   passes `fold_case=True`, so `search notes --thread acme` resolves while
   `hours list acme` is refused. The `fold_case` docstring cites a CSV import
   that does not exist, and this is its only caller. Drop the parameter and the
   4 functions that thread it through (`vault.py:285, 290, 342, 352`).
6. **`search.hours_in_window` hides bad data.** Its `except Exception`
   (`search.py:302`) makes one command under-report hours on a malformed
   `startTime`, while `hours list`, `payments statement` and `search stream`
   all crash with a raw traceback on the same record. Validate at the read
   boundary, and let every walker behave the same way. The same applies to the
   4 other bare `except Exception` swallows in `search.py` (`:77, 102, 199,
   213`), and to `_safe_load` (`:189-193`), whose stated reason is false —
   `vault.record_files` already returns early for an absent directory.

## R3-B. The tests' real weakness

**Targeted mutations of the round 2 code: 9 of 9 caught. Fresh mutations chosen
independently: 2 of 11 caught.** The suite defends what it was pointed at and
little else. Fix that, in this order.

### R3-B1. The client-facing bank details have no test at all

`statement_pdf.py:164-173` (account name, bank, account number, branch code,
reference) is **never executed by any test**: every PDF test runs with
incomplete banking, so only the "not yet supplied" branch runs. Corrupting the
account number leaves the suite green. `statement_pdf.py:121` ("Hours written
off") is never rendered either. Add a statement test with complete banking and
assert the block's exact text.

### R3-B2. No default is tested anywhere

Every `--limit` and truncation default survives being changed:

| Changed | Nothing failed |
|---|---|
| `search overview --limit` 5 → 2 | yes |
| `search notes/logs` limit 20 → 3 | yes |
| `search stream --limit` 100 → 20 | yes |
| `commit` max file lines 150 → 40 | yes |
| `commit review` stops capping tracked diffs | yes |

The tests pass explicit values everywhere. Add a case per default that proves
the default's effect. `commit review`'s tracked-file cap is not exercised at
all, because the only large file in the fixture is untracked.

### R3-B3. Rounding and aging rest on almost nothing

- Making `charge_of` round **down** instead of half-even fails exactly **one**
  assertion (`unit/test_hours.py:19`). Both "agree to the cent" tests pass. Add
  a case whose half-even and round-down results differ, on each path.
- The aging buckets (`statement.py:88-95`) are only tested at 5, 40, 70 and 200
  days, so moving a boundary fails nothing. Test at 30, 60 and 90.
- `statement.check` verifies charges against lines but not payments against
  lines, so a future caller can reintroduce the round 2 receipts bug in
  silence. Add the assertion.

### R3-B4. The golden fixtures pin output nobody has defended

`tests/fixtures/render/*.expected.md` came from the old bash renderer. They
still contain, unlabelled:

- `| None | None | None |` as the empty action-table row (also asserted as
  correct at `unit/test_render.py:83`)
- `- [[Projects/Not A Person]]` listed as a meeting attendee
- `No minutes agreements were made.` next to `No Resolutions were passed.`
- a trailing space in `date: 2026-09-10 `, and `date:  ` / `subtitle: ` in the
  `no_frontmatter` files

"Matches the old script" has become the definition of correct. For each: fix
the output and regenerate, or put a `KNOWN-WRONG:` note in the fixture and a
line in the deferred list. Deferred bugs 2, 10 and 11 already cover some of it;
the rest is undeclared.

### R3-B5. Put back the coverage that the R-D2 deletions lost

In 4 cases the stronger test of the pair was the one deleted:

1. **No test** now checks that an **unbilled** hours entry still writes a
   buffer `REF:` (`test_hours_cli.py:430`).
2. `buffer suggest` on a **structured** suggestion — the case where an
   "accept?" prompt would appear — is no longer covered; the survivor uses an
   unstructured one.
3. `payments` optional fields blank is now only tested as a pure function, so
   "no account" has no end-to-end cover.
4. Smaller: `threads show Projects/sgb` (qualified, wrong case), the stored
   start/end after `hours log`, `hours report --json` per-currency buckets.

### R3-B6. The "make it exact" pass over-shot in places

Exact assertions on **our** output are right. These pin someone else's:

- `test_commit_cli.py:87, 246, 257` pin **git blob hashes**
  (`index 0000000..5626abf`). They encode no requirement of ours.
- `test_no_prompts.py:47-58`: 8 of 14 rows pin argparse's
  `the following arguments are required: …`. Keep one as a representative.
- `test_tasks_cli.py:455` traded our own `priority must be H, M, or L` message
  for argparse's `invalid choice`. Keep a project-owned message.
- `test_lint_cli.py:589` `test_unbilled_hours_pass_lint` is the R-D3 holdout:
  still `returncode == 0` only. Use `assert_clean()`.

### R3-B7. Delete or fold: tests that cannot fail, or say nothing new

1. `test_search_cli.py:159` `test_type_is_case_insensitive` and `:151`
   `test_thread_accepts_bare_name` compare the command's output to itself.
   **Proven vacuous:** breaking the `--type` filter entirely leaves
   `test_type_is_case_insensitive` passing. Assert the expected row.
2. `lint.py:691` skips `.bak` files, but the `.md` suffix check already
   excludes them. The clause is dead, and 2 tests assert it
   (`test_lint_cli.py:85`, `unit/test_lint.py:149`). Delete all three.
3. `test_depends_help_says_a_whole_uuid` exists **twice**, byte-identical
   (`test_tasks_cli.py:576`, `test_buffer_cli.py:390`), and pins a help
   sentence.
4. The "fails instead of prompting" family is duplicated across
   `test_hours_cli.py:141`, `test_payments_cli.py:108`,
   `test_people_cli.py:129, 136`, `test_threads_cli.py:176`,
   `test_notes_new.py:135`. `test_no_prompts.py` is the one home for this.
5. Parametrisation that inflates the count without adding a fact:
   `test_every_command.py:52` (24 cases for one error string, plus 10 more at
   `:69`), `test_no_prompts.py:104` (5 cases, exit code only),
   `test_search_cli.py:451/475` (both weaker than `:459` between them),
   `test_tasks_cli.py:262-303` (4 rebuilt vaults for what `:245`/`:254`
   already cover, and `:254` counts newlines in a file that elsewhere pins
   whole tables).
6. `unit/test_lint.py:216` derives its expected text by calling `json.loads`
   at runtime, so that clause compares the stdlib to itself.
   `dev/test_manual_harvest.py:60` runs every command twice to prove a
   tautology; move it out of the gate.
7. `unit/test_harness.py:77` asserts no executable sits at the repo root. That
   is a lint rule; move it to `dev/ci`.

### R3-B8. Untested behaviour worth covering

- **The suggester's confidence floor** (`suggester.py:574`), the guard that
  decides when to bail to UNKNOWN. Removing it fails nothing. Also untested:
  the person-name boost, length normalisation (`rank_threads` is only ever
  called with `lengths=None`), and the assignee loop. The 27-case corpus in
  `eval/suggester/` is **not run by `dev/ci`**, so nothing gates suggestion
  quality at all.
- **The `--help-json` manifest's content.** Only flag and subcommand names are
  asserted, yet `dev/tools/` and `MANUAL.md` are generated from the rest.
- `threads.py`, `statement_pdf.py` and `helpjson.py` have **no unit test file**.
- `buffer`'s empty-TEXT and empty-ACTION branches (`buffer.py:589`, `:372`).

### R3-B9. Two structural notes

- **Docstrings still name refactor units** ("refactor unit 8", "fails against
  the pre-port script") in `test_buffer_cli.py:1` and many others. Once this
  merges, that is archaeology. Say what the behaviour is instead.
- **The vault tripwire can red a green suite.** `conftest.py:233` fails the run
  if any managed file in the real `~/vault` changed size or mtime — including
  because Obsidian or a sync client touched it. Worth keeping; worth making the
  message say that is the likely cause.

## R3-C. Code quality

1. **One parser for an `ACTION:` line.** There are four:
   `tasks.py:38-39, 262-277`; `buffer.py:58, 217-247`; `buffer.py:360-377`
   (the same four checks again, as messages); `lint.py:25, 447-457` (a
   different regex, no attributes). R3-A5.2 and R3-A5.3 are direct
   consequences. One `parse_action(line) -> (assignee, body, attrs, errors)`
   in `vault.py` removes about 50 lines and the divergence. **Highest-value
   change in this round after the bugs.**
2. **`hours.py` and `payments.py` still carry verbatim twins.** `as_output` is
   byte-identical including its docstring (`hours.py:195` / `payments.py:157`);
   `cmd_rm` is identical but for a variable name; `collect` and
   `find_entry`/`find_payment` differ only in the subdir, fence and noun.
   `vault.py` already owns the record layer. Finish the job, or give both a
   small record-store value that carries subdir, fence, key, heading and sort
   key — which would also collapse `write_records`' 8 parameters
   (`vault.py:458`).
3. **`suggester.py` is the one module below the "intermediate hobbyist" bar.**
   - `parse_dates` (`:216-301`) is 86 lines, 8 sequential `if matched_date is
     None:` blocks and an escape flag. Six of the 8 are the same 4 lines with a
     different pattern. A list of `(pattern, resolver)` pairs is under 30.
   - It also strips the wrong "by"/"before": detection uses the last 20
     characters, the span comes from the first match in the whole prefix, so
     "before lunch, and again before friday" loses the wrong words.
   - `detect_explicit_thread` (`:460-499`) re-matches a reconstructed pattern
     against a slice purely to recompute an offset.
   - `match_person` (`:163-211`): the docstring promises pairs and returns
     names, `text_words` is dead, and when two people share a first name it
     picks the alphabetically-first and wikilinks them — a silent wrong person,
     against the module's own "prefer to bail than mislead".
   - `rank_threads`' `+5.0` unique-token bonus (`:395`) needs a name.
4. **Duplicated state machines.** `render.cut_sections` and `fill_sections`
   (`render.py:171-208`) are the same machine twice, differing only in "also
   stop at" and "also insert". `tasks.py:301-305` is a literal copy of
   `write_anchor` (`:192-196`) fifty lines below it.
   `buffer.format_suggestion` and `dispatch_proposal` are parallel switches
   whose `add` arms are unreachable (`cmd_suggest` returns first), as is the
   "unknown subcmd" guard. `lint`'s "report each occurrence pointing at the
   others" exists twice (`:555-562`, `:601-606`).
5. **Consistency.**
   - `tasks` prints three path formats: absolute on ingest (`:283`),
     vault-relative in `show` (`:526`), basename in the ambiguity error
     (`:183`). `lint` and `buffer` use vault-relative. Pick it.
   - `tasks --dry-run` and `--quiet` are top-level flags that only work on the
     bare invocation, so the help says "(default invocation only)" twice.
   - `tasks` and `buffer list` are the only listing commands with no `--json`.
   - `--date` exists only on `buffer add-ref`, though `stamp()` is generic.
   - `payments._as_of` is the last date flag not using `V.iso_date`, so its
     message differs from every other one.
   - `CENT = V.CENT` survives at `statement.py:17` and `statement_pdf.py:25` —
     the aliasing R-C1 removed everywhere else.
   - `threads.cmd_list` and `people.cmd_list` are still ~25 near-identical
     lines.
   - The uuid help string appears verbatim 10 times in `tasks.py`.
   - `vault.parse_block` (`:143-187`) is now the single parser but is harder to
     read than the two it replaced. Its `out[key] == ''` sentinel needs a
     comment at least.
6. **`dev/ci` has no linter.** The `# noqa: BLE001` markers and the E741
   concern imply one that never runs. Either wire up ruff and honour the
   markers, or delete them.

## R3-D. Docs and schemas that lie

1. **`schemas/thread.md:38` names the wrong config key.** It says `time.rate`;
   `hours.py:72` reads `hours.rate`, and the README agrees. The schema ships as
   package data and is harvested, so the wrong key is already in
   `MANUAL.md:695`.
2. **`dev/tools-build:70-95` documents interactivity that no longer exists** —
   "interactive capture", "prompts per field", "fail cleanly on EOF",
   "suggest prompts for accept/reject". None of it is true now, and the whole
   paragraph hangs off the `'tasks': {}` entry. This is the file that describes
   the agent's blast radius; it has to be true.
3. `dev/tools-build:44` defines `ALLOWED_FIELDS` and never uses it (a copy of
   `dev/tools-check:38`).
4. `dev/testbed` is the only file using double quotes throughout, and the only
   one that assigns a lambda to a name (`:172`).

## Round 3 done means

- [ ] A windowed `payments statement --pdf` shows the same lines as the text
      view. A test proves it.
- [ ] Every write command accepts `--help-json` as data and writes the record.
- [ ] A thread with `rate: 1,000` is refused, not billed at 2500, and lint says
      so.
- [ ] `lint` on a relative path agrees with `lint` on the absolute one.
- [ ] Changing any `--limit` or truncation default fails a test.
- [ ] Corrupting the statement PDF's bank account number fails a test.
- [ ] `grep -rn 'def parse_action' src/adulting/` finds one function, used by
      `tasks`, `buffer` and `lint`.
- [ ] Every `tests/fixtures/render/*.expected.md` oddity is either fixed or
      labelled `KNOWN-WRONG` and listed in the story.
- [ ] `dev/ci` is green.
