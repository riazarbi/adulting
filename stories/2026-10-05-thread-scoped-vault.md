# Thread-scoped vault layout

Status: built on branch `thread-scoped-vault`; verified on a copy of the vault. The production vault is not migrated yet.

## Decisions (2026-10-05)

- **The thread file stays where it is** (option A): `threads/<Kind>/<Name>.md`
  sits next to a `threads/<Kind>/<Name>/` folder.
- **`people/` stays global.**
- **`buffer.md` stays at the root.**
- **`notes directory.base` is out of scope.** It is unused.
- **Work happens on a copy of the production vault**, never on `~/vault`,
  until the result is verified. See "Working on a copy".
- **Multi-thread notes live under their first listed thread.** Frontmatter
  stays the authority on membership.
- **`threads delete` is removed.** Deleting a thread is a manual job.
- **Archiving is a status change, not a file operation.** Setting
  `status: closed` in the thread's frontmatter is the whole act, and
  `threads list` already hides closed threads by default. Nothing moves.
- **`assets/` stays global.**
- **The path gate is part of this story.**

## The proposal

Today the vault has one top-level tree per kind of record. Four of them
(`logs/`, `hours/`, `payments/`, and implicitly `notes/`) are partitioned by
thread in a different place each:

    threads/Projects/SGB.md
    logs/Projects/SGB/2026-10-05.md
    hours/Projects/SGB.md
    payments/Projects/SGB.md
    notes/2026-10-05-09-00-00.md        (thread only in frontmatter)
    people/Charlie.md
    buffer.md

The proposal is one tree, partitioned by thread, with everything about the
thread underneath it:

    threads/Projects/SGB.md             (the thread file, where it is now)
    threads/Projects/SGB/notes/2026-10-05-09-00-00.md
    threads/Projects/SGB/logs/2026-10-05.md
    threads/Projects/SGB/hours.md
    threads/Projects/SGB/payments.md
    people/Charlie.md                   (see "People")
    buffer.md

## What the live vault says

Measured read-only against `~/vault` on 2026-10-05.

| tree      | files | already per-thread? |
|-----------|------:|---------------------|
| threads   |    25 | yes (one file each) |
| logs      |   208 | yes, `logs/<Kind>/<Name>/` |
| hours     |    17 | yes, `hours/<Kind>/<Name>.md` |
| payments  |     2 | yes, `payments/<Kind>/<Name>.md` |
| notes     |   129 | no, flat; thread in frontmatter |
| people    |    68 | no |

- **Notes partition cleanly.** 128 of 129 notes name exactly one thread. The
  exception is `2026-05-15-08-26-53` ("AI for SDLC Protocol"), which names
  SANA Partners and AXA DORA.
- **People mostly do too, with exceptions.** Of the 53 people referenced
  from a note or log (as `[[people/X]]` or as an assignee), 48 appear in one
  thread only. Bern Sellmeyer appears in 3 threads, three more people in 2,
  and Riaz Arbi in 10. 15 people are referenced from no note or log.
- **Path-qualified links exist and would break.** Logs hold ~67
  `[[hours/<Kind>/<Name>]]`, ~67 `[[notes/<stem>]]`, one `[[logs/…]]`, and
  one `[[payments/…]]`. `hours log`, `payments add` and `notes new` write
  them as `REF:` lines through the buffer. There are 406 `[[people/X]]` links.
- **Obsidian barely depends on the layout.** `notes directory.base` filters
  on `file.inFolder("notes")`, but it is unused. The only community plugin
  is obsidian-git. Note embeds (`![[Pasted image …]]`, ~50) resolve by name
  against the global `assets/` folder, so moving notes does not affect them.

## Technical feasibility

The change is feasible, and smaller than it first looks, for three reasons:

1. **Logs, hours and payments already map from thread to path.** Only the
   prefix moves (`logs/<Kind>/<Name>/` becomes
   `threads/<Kind>/<Name>/logs/`). `Store.path` in `vault.py:601` and the log
   path in `buffer.py:542` are each one line.
2. **Membership is already read from frontmatter, not from the path.**
   `note_threads`, the tasks thread cache, search and lint all ask the
   file's `thread:` / `threads:`, so they keep working wherever the file is.
3. **Task anchors carry their identity in the file.** UUIDs live on the
   `TASK:`/`DONE:` line. `tasks.py:215` keys its cache by relative path,
   but rebuilds that cache on every run, so moving a file loses nothing.

### Where the thread file goes

This is the main design choice. Thread wikilinks (`[[Projects/SGB]]`) are
everywhere: buffer lines, note and log frontmatter, `hours`/`payments`
frontmatter.

- **A. The thread file stays a sibling of its folder.** (recommended)
  `threads/Projects/SGB.md` plus `threads/Projects/SGB/`. Obsidian resolves
  `[[Projects/SGB]]` exactly as it does today, so no thread link changes.
  The cost is that a thread is a file *and* a folder, so moving or archiving
  it takes two steps.
- **B. The thread file goes inside the folder** (`threads/Projects/SGB/SGB.md`,
  the folder-note convention). Obsidian no longer resolves `[[Projects/SGB]]`,
  so every thread link in the vault would need rewriting, and so would the
  `thread_ref` format the CLI emits. Rejected.
- **C. Kind folders at the vault root** (`Projects/SGB.md`,
  `Projects/SGB/…`), with no `threads/` level. Option A without the prefix,
  which makes a thread ref literally its path. That is tidy, but it puts
  three more folders at the root and changes every `threads/` reference.
  Worth a look only if we are moving everything anyway.

### Code blast radius

| module | change |
|---|---|
| `vault.py` | `Store.path`, `record_files` (walk `threads/**/hours.md` etc.), `discover_threads` must ignore the new sub-folders, `vault_file` lookups |
| `notes.py` | `notes_dir`/`note_path`/`all_notes`: notes are found by stem across thread folders, and `new` writes under the first `--thread` |
| `buffer.py` | log path in flush; `ref_target_resolves` prefixes |
| `tasks.py` | `discover_source_files` |
| `search.py` | notes/logs/hours walks, buffer unchanged |
| `lint.py` | `discover_files`; `find_file_schema` scopes schemas by **first path component** (`lint.py:329`), so scoping must move to "position under a thread folder" |
| `threads.py` | `delete` is removed (see "Removing `threads delete`"); `discover_threads` must skip the new sibling folders |
| `hours.py`, `payments.py`, `notes.py` | the `REF:` targets they write |
| schemas | `directory:` and the "Lives at" prose in 7 schema files |
| tests | roughly 300 path literals, plus the `vault` fixture in `conftest.py` |
| MANUAL, `dev/tools/*.json`, `agent/skills/*`, README, docstrings | see "Impact on the generated docs" |

A rough estimate is a few hundred changed lines in `src/`, with most of the
work in tests. Nothing needs a new dependency or a new concept, apart from
the "home thread" rule below.

### Multi-thread notes: the one new rule

A note has one file but may belong to several threads. Proposed rule: **the
note lives under its first listed thread, and frontmatter stays the
authority on membership.** Lint checks that the containing thread is the
first entry in `threads:`. Cross-thread views (search, tasks, `notes list`)
already read frontmatter, so they still show the note under every thread it
names. Browsing the folder of a non-home thread does not show it. That
affects one note today.

If the `threads:` list is later edited so that the home thread changes,
lint flags it. A small `notes move <stem>` (or a `lint --fix`) would
re-home the note. That can wait until it is needed.

### Links: rewrite now, write sturdier ones from now on

- Migrate the ~134 path-qualified REF targets.
- Change `notes new` to write `[[<stem>]]`, a bare stem, instead of
  `[[notes/<stem>]]`. Note stems are timestamps and unique across the vault,
  and Obsidian resolves a bare unique name wherever the file is. Notes could
  then move again without breaking a link.
- Hours and payments files can't use bare links, because every thread has
  an `hours.md`. Their REF target becomes `[[Projects/SGB/hours]]`, which
  Obsidian resolves by path suffix.

### Migration

A one-off script, idempotent, that takes the vault root as an argument
(it never defaults to `~/vault`):
1. Move the notes, logs, hours and payments files.
2. Rewrite REF targets.
3. Run lint.

## Working on a copy

`dev/testbed` already provides this. `create` copies `~/vault`'s content
(no secrets, agent state, `.obsidian` or `.git`) into
`~/projects/adulting-testbed/pristine/`. `reset` restores a working vault
from that copy, and `run new …` runs this checkout's commands against it
with `HOME` and `ADULTING_HOME` isolated, so neither `~/vault` nor `~/bin`
can be reached. The plan:

1. Run `dev/testbed create` once to take a fresh snapshot. The existing one
   predates this story, and `pristine/` must reflect today's vault.
2. Run the migration script against `home/vault/`, then use `dev/testbed
   diff` to review the moves.
3. Run the new commands against the migrated copy: lint clean, and the
   outputs below match the old layout's.
4. Repeat steps 2–3 from `reset` as often as needed. The pristine copy is
   never written to.
5. Only once that passes, run the migration on `~/vault`, as a separate
   step and on your go, with a git commit beforehand and `~/.adulting.bak`
   as the second restore point.

**A testbed limitation.** `compare` runs old against new and diffs the
results. Once the layout changes, every path in the output differs by
design, so a raw `compare` would be all noise. Two options:

- Compare old-on-pristine with new-on-migrated, normalising paths. For each
  moved file, map the old path to the new one and rewrite the old output
  before diffing.
- Compare only path-free output: `--json` totals, task lists by uuid,
  `hours report`, `payments statement`.

I'd add the normalisation. It is small, and it is the only way to show
that `search`, `tasks list` and `notes list` return the same records.

`BASELINE_COMMIT` (`119f90b`) is the pre-package-refactor reference. For
this story the baseline should be `main` at the commit before work starts.

## Impact on the generated docs

This is the part most likely to go wrong without anyone noticing.

### How the docs are produced

    module docstrings ─┐
    argparse help= ────┤
    --help-json ───────┼─> dev/manual-harvest ─> corpus ─┬─> claude ─> MANUAL.md
    schemas/*.md ──────┤                                 └─> claude ─> dev/tools/*.json
    vault_paths() ─────┤
    README.md ─────────┘
    agent/skills/*/SKILL.md   (hand-written, shipped in the image)

The CI gates (`manual-check`, `tools-check`, `agent-check`) compare **names
only**: subcommands, flags, and claims about prompting. **None of them
checks a path.** Every layout statement in MANUAL.md, the tool descriptions
and the skills could stay wrong after this refactor and CI would still pass.

### Where the layout is written down today

| source | what it says | reaches |
|---|---|---|
| `schemas/*.md` (9 files) | "Lives at `~/vault/logs/<Kind>/<Name>/…`", `directory:` frontmatter | corpus → MANUAL, tools; also drives lint |
| module docstrings: `buffer`, `tasks`, `notes`, `hours`, `payments`, `vault`, `threads`, `lint`, `people` | `notes/ + logs/`, `$ADULTING_HOME/hours/…`, `threads/<Kind>/<Name>.md` | corpus → MANUAL, tools |
| argparse help: `buffer add-ref target` (`notes/<stem>, logs/<path>, …`), `buffer flush` ("write to logs/") | the REF target grammar | `--help`, `--help-json`, corpus |
| `vault_paths()` in `dev/manual-harvest` | regex over `vault_home() / '<dir>'` and `$ADULTING_HOME/<dir>` | corpus "vault paths" line per tool |
| README.md | ~28 mentions plus a layout tree (lines 316–348) | corpus (declared sections) → MANUAL |
| MANUAL.md | 29 mentions | generated |
| `dev/tools/{buffer,tasks,notes,lint}.json` | 1 each | generated |
| `agent/skills/commit-workflow` | a table that derives thread from path for `logs/` and `hours/`, and from frontmatter for `notes/` | hand-written; read at runtime by the agent |

### What has to change, and how to make it stay right

1. **`vault_paths()` will silently go blank.** Its regex matches
   `vault_home() / 'notes'`. Once paths are built as `thread_dir(...) /
   'notes'`, it finds nothing, and the corpus says "(none detected)". It
   already misses `lint` (it walks a tuple of directories) and reports
   `hours/` only because of a docstring. **Fix:** declare the layout once in
   `vault.py` (for example a `LAYOUT` mapping such as `'log':
   'threads/<Kind>/<Name>/logs/<YYYY-MM-DD>.md'`) and have both the code and
   the harvester read it. The corpus then carries the layout from a single
   source instead of from regex archaeology.
2. **Schema prose and `directory:`.** Rewrite the "Lives at" lines, and
   replace `directory:` (a first-path-component match) with a pattern that
   lint and the docs share, for example `path: threads/*/*/logs/*.md`. The
   schemas are harvested verbatim, so this one edit fixes both lint and the
   corpus.
3. **Docstrings and help strings.** About 9 modules plus 2 `help=` strings.
   Change these wording-wise in the same commits as the code they describe,
   so that a harvest at any commit is self-consistent.
4. **README.** Redraw the layout tree and fix the "Notes live in…" lines.
   README is authored and harvested, so it is an input to the manual, not
   an output.
5. **Regenerate MANUAL.md and `dev/tools/` with `dev/ci generate`, once, at
   the end**, from one harvest. Then read the diff. Regeneration is
   model-written, so the review is not optional.
6. **`commit-workflow` skill.** After the move, *every* record file's
   thread can be read from its path (`threads/<Kind>/<Name>/…`), including
   notes. The table collapses to one rule, which makes the skill simpler.
   Per the CLI-vs-agent split, this goes in its own story, but the CLI story
   must not merge until that story is ready, or the shipped skill will
   describe a layout that no longer exists.
7. **Close the gap: a path gate.** Add a check (in `surface.py`, run by all
   three gates) that flags any vault-path pattern in MANUAL.md,
   `dev/tools/*.json` or `agent/skills/` that does not match `LAYOUT`. For
   example, `notes/<…>.md` or `hours/<Kind>/` at the start of a path. It is
   cheap, has no model call, and it is the only thing that would have
   caught drift here. It also protects any future layout change.

Order of work: `LAYOUT` and the harvester first, so every later commit
harvests correctly. Then code, schemas, docstrings and README together,
module by module. Then the path gate, which should fail against the old
MANUAL and tools. Then `dev/ci generate` and review. The skill story lands
alongside.

## Benefits to you

1. **A thread is one place.** `ls`, `rg` and Obsidian's file tree show the
   whole of a thread's notes, logs, hours and payments in one folder.
   Today they are spread over four trees, and notes are mixed into a flat
   folder of 129 files.
2. **Scoped work for the agent.** A thread is a single directory, so the
   agent can be pointed at it (or limited to it) to read a thread's full
   history, instead of running search-tool queries or doing a frontmatter
   join. Context stays small and relevant.
3. **Closed threads are easy to skip.** Archiving stays a status change.
   But with one folder per thread, a closed thread's material sits in one
   place that `rg` or the agent can ignore by path, without a frontmatter
   join.
4. **Sharing and handover.** A client's statement, the notes behind it, and
   the logs can be handed over (or zipped, or synced selectively) as one
   folder.
5. **One tree to maintain, not four.** The rule "hours/payments/logs mirror
   `threads/`" goes away, and with it a whole class of orphan and mismatch
   that the mirroring allows.
6. **Manual delete and rename get simpler.** Deleting a thread by hand
   becomes removing `<Name>.md` plus `<Name>/`, not hunting through four
   trees. Today `threads delete` unlinks only the thread file
   (`threads.py:54`) and leaves the thread's logs, hours, payments and notes
   behind as orphans; it is being removed (see below). Rename becomes one
   folder move instead of four, though thread wikilinks still need
   rewriting.

## Costs to you

1. **A one-time migration of the live vault.** About 360 files move and
   ~134 links are rewritten, in one large obsidian-git commit. That breaks
   `git log --follow`-style history only cosmetically, since git detects
   renames.
2. **Every hours and payments file has the same name.** Obsidian tabs and
   search results show `hours.md`, not `SGB.md`. Mitigate with an
   `aliases: ["SGB — hours"]` frontmatter entry; the H1 is already
   `# SGB — hours`.
3. **Cross-thread views walk deeper.** "All notes", `hours report` and
   `payments statement` across threads now walk `threads/**`. This makes no
   noticeable performance difference at this size, but the code is a little
   less direct.
4. **A new rule to remember**, the home thread for multi-thread notes,
   which lint enforces.
5. **Any habit of opening `notes/` to see "everything recent"** has to
   change to `notes list`.
6. **Engineering time.** Mostly in tests and docs. While the move is in
   progress, the CLI and the agent skills must change together (separate
   stories; see below).

## People

The evidence points both ways.

**For per-thread `people/`:** 48 of 53 referenced people live in exactly
one thread. A per-thread `people/` folder would make a client's contacts
part of the thread folder you browse, archive or hand over.

**For global `people/`** (recommended):
- **The people who matter most cross threads.** You appear in 10 threads,
  and the long-lived contacts (Bern, family) are exactly the ones that
  span. Splitting them means either duplicate files that drift apart, or
  choosing an arbitrary home.
- **A person is not a thread's property.** The person schema gives people
  their own `status`, `category` and `cadences`, the same lifecycle a
  thread has. A relationship outlives the project you met them on, so
  archiving a thread should not archive the people in it.
- **Links.** Changing 406 `[[people/X]]` links and assignee resolution
  (`person_exists` → `people/<name>.md`) would require a thread context
  everywhere a person is named. A bare `[[X]]` would also collide as soon
  as one person existed in two threads.
- **15 people are referenced from no thread at all.** Under a per-thread
  layout they would have no home.

**Middle ground:** keep `people/` global, and add a derived view
(`people list --thread SGB`, from note and log references) so that "who is
on this thread" is one command away, without moving files. On handover,
that view lists the people files to include.

## Removing `threads delete`

The subcommand is removed outright, with no deprecation period. It is
named in several places, and each one has to go in the same change, or
a gate fails:

| place | what to do |
|---|---|
| `src/adulting/threads.py` | drop `cmd_delete` and its parser (lines 54–61 and 112–115) |
| `dev/tools-build` `POLICY` | drop `'threads': {'forbidden_args': ['delete']}`. `tools-check` requires every forbidden arg to name a real subcommand, so leaving it makes the gate fail |
| `dev/tools/threads.json` | regenerated; it must no longer declare a `delete` block |
| README.md:135 | remove the row |
| MANUAL.md:208, 722 | regenerated; `manual-check` fails until then, because it requires every documented subcommand to exist |
| tests | delete the `threads delete` cases in `tests/cli/test_threads_cli.py` and any `test_every_command` entry |

Once it is gone, threads has no destructive subcommand at all, so the
tool definition can drop its safety note about deletion.

## Out of scope

- Agent skill updates. Per the CLI-vs-agent split, they get their own story
  once the CLI behaviour is agreed.
- `buffer.md` stays at the root, unchanged.

# Built (2026-10-05)

## Where things ended up

- **`vault.LAYOUT`** is the single statement of the layout. The path helpers
  (`thread_folder`, `thread_of`, `note_files`, `log_files`, `find_note`,
  `Store.path`) follow it. Each schema's `path:` must be one of its values
  (`tests/unit/test_layout.py`), and `dev/manual-harvest` puts it in the
  corpus as an authoritative "Vault layout" table. The regex-based
  `vault_paths()` is gone.
- **Schemas** use `path: threads/<Kind>/<Name>/logs/<YYYY-MM-DD>.md` and so
  on, in place of `directory:` + `filename:`. lint matches a file against
  `path:` with the placeholders expanded (`<Name>` still refuses a `.`, as
  `filename:` did).
- **New lint rules:**
  - A file in a thread folder whose `thread:` (or first `threads:` entry)
    is another thread is reported.
  - A note stem used twice is reported at both places.
  - Files left in the old root folders are reported as `no matching file
    schema; is it where the vault layout puts it?`.
- **REF targets:** `notes new` writes the bare stem.
  - `hours log` and `payments log` write `<Kind>/<Name>/hours` and
    `<Kind>/<Name>/payments`.
  - `buffer add-ref` accepts those forms, plus `<Kind>/<Name>/logs/<date>`,
    a bare stem, and `people/<Name>`. The old `notes/…` and `hours/…` forms
    no longer resolve.
- **New hours and payments files** are titled `# <Name> — hours`, with the
  name taken from the thread, since every such file is now `hours.md` or
  `payments.md`. No `aliases:` was added: Obsidian tabs show the filename
  either way.
- **`threads delete` is removed**, along with its tests, its README row and
  its `forbidden_args` policy entry.
- **The path gate** is `surface.stale_paths`. `manual-check` (whole
  manual), `tools-check` and `agent-check` all run it. It flags a path that
  starts at a retired root (`notes/`, `logs/`, `hours/`, `payments/`):
  - after a vault prefix (`~/vault/`, `$ADULTING_HOME/`, `/vault/`), or
  - when followed by `<`, `{`, a thread kind, or a digit.

  It leaves prose such as "notes/logs" and a thread's own `notes/` alone.
- **`dev/migrate-layout VAULT`** does the move.
  - It refuses the production vault without `--production`, and refuses a
    git vault that has uncommitted changes.
  - It never overwrites a file, and a second run does nothing.
  - It moves a note's attachments (`<stem>-x.png`, linked by relative path)
    along with the note.
  - It writes a `--map` of every move.
- **`dev/testbed`**:
  - `ADULTING_BASELINE` and `ADULTING_TESTBED` choose the baseline commit
    and the testbed location.
  - A package-era baseline gets its own venv.
  - `layout-compare` runs old on the old layout and new on the migrated
    vault, with old's paths mapped to their new places.

## Verification on a copy of the production vault

The testbed is at `~/projects/adulting-testbed-threads`, with the baseline at
`main` (5ea5e84). The previous testbed and its goldens were left untouched.

- **Migration:** moved 135 files from notes/ (133 notes and 2 images that
  one note links by relative path), 211 from logs/, 17 from hours/ and 2
  from payments/. It rewrote 141 links in 91 files. No problems were left.
- **lint:** 456 files and 18 violations, both before and after. They are
  the same 18, already present in the vault: timestamp shapes, two
  unresolved people, three closed threads without `ended`, and two
  sync-conflict copies. Only their order and the wording of the
  no-schema message differ.
- **`layout-compare`, same output:** `threads list --all --json`,
  `people list --all --json`, `notes list --json`, `tasks list`,
  `tasks next`, `hours report`, `payments list --json`,
  `payments statement`, `buffer list`, `search activity`,
  `search notes --thread "AXA DORA" --json`, `search logs --json`.
- **`layout-compare` scope:** read-only commands only. The commands that
  write (`notes new`, `buffer flush`, `hours log`, `payments log` and the
  rest) were checked against the new layout by the test suite alone.
- **`layout-compare`, explained differences:**
  - `hours list --json` has the same records. Ties on date and time used
    to come out in filesystem walk order and now come out in thread order.
  - `search overview SGB` has the same rows. Only the padding differs,
    because column width follows path length.

## Tests

- **Full suite:** 965 passing, before the tests added after the mutation
  run below.
- **Mutation check.** Each piece of the change was undone in turn:
  - filing a note under its first thread;
  - the bare-stem REF;
  - copying a note beside its source;
  - the home-thread lint rule;
  - the duplicate-stem lint rule;
  - walking the legacy folders;
  - the self-REF pattern;
  - thread files only in the stream;
  - folders not being threads;
  - titling a record file by its thread;
  - old REF forms being rejected;
  - the stale-path gate;
  - link rewriting in the migration;
  - attachments moving with their note.

  Each made at least one test fail. Two were missed on the first pass
  (folders and titling), and tests were added for both.
- **Weak checks fixed.** Several "writes nothing" tests globbed the old
  top-level `hours/` and `payments/` folders, and some unreadable-file
  cases wrote to old paths, so they could not fail. They now look at the
  new places.

## Still to do (operator)

1. Review the regenerated `MANUAL.md` and `dev/tools/*.json` diff.
2. Merge with the skill story (`2026-10-05-commit-workflow-thread-folders.md`).
3. Migrate `~/vault`:
   - Commit the vault (obsidian-git), so the working tree is clean.
   - Run `dev/migrate-layout ~/vault --dry-run`. It reports any file it
     could not move and any it could not write; fix those first.
   - Run it with `--production`.
   - Run `lint` and expect the same violations as before.
   - Commit.

   **To undo** before that last commit:
   `git -C ~/vault reset --hard && git -C ~/vault clean -fd`. A bare
   `reset --hard` restores the old paths but leaves the moved copies behind
   as untracked files, and `clean -fd` removes them. `~/.adulting.bak` is
   the second restore point.

# Round 1

Response to the first review. Each fix was checked by undoing it on the
finished tree and running the tests named, which must then fail. The full
suite was used except where a narrower set is given. All undos were made by
a script that restored the file afterwards. Final state: **981 passing**;
syntax, ruff, `--help-json` and the three gates all pass.

## 1. A note stem two notes share

**Decision: reject only the REF lines that name the shared stem.** A
duplicate stem is a vault problem, and `lint` is where it is reported (at
both files). It should not take the whole buffer down with it.

- `buffer add-ref <thread> <stem>` refuses with
  `ref target '<stem>' is the stem of more than one note (<path>, <path>);
  `lint` reports it, and one must be renamed`, and writes nothing.
- `buffer tend` reports that line as a violation:
  `REF target '<stem>' is the stem of more than one note; `lint` names them`.
  It validates every other line as usual and reports their own problems.
- `buffer flush` still refuses while `tend` reports anything. That is the
  existing rule for any invalid line, not something new.
- A command that names one note (`notes cat`, `delete`, `pdf`, `minutes`,
  `agenda`, `copy`) still stops with `note '<stem>' exists more than once:
  <path>, <path>`. Acting on whichever file the walk met first would be a
  guess.

**What changed:**
- `vault.notes_named(stem)` lists every match, and `find_note` uses it.
- `buffer.ref_target_resolves` uses `notes_named` and treats more than one
  match as not resolving. It no longer calls `find_note`, which stopped the
  command.
- The new `buffer.ref_target_problem` words the refusal for `add-ref`.

The reviewer's description was accurate. One correction to its scope: the
old code stopped the command only when the buffer held a REF to the shared
stem, not whenever a duplicate existed. But it then stopped the whole
command with a `find_note` error rather than a violation on the line.

**Tests:**
- `test_a_stem_two_notes_share_is_an_error_naming_both[cat|delete|pdf]` in
  `tests/cli/test_notes_cli.py`.
- `test_add_ref_to_a_shared_stem_is_refused_and_says_why` and
  `test_tend_rejects_only_the_ref_to_a_shared_stem` in
  `tests/cli/test_buffer_cli.py`.

**Undone:**
- Removing `len(found) > 1` in `find_note` fails the three notes tests.
- Letting the buffer resolve a shared stem to its first match fails both
  buffer tests.
- Putting back `return V.find_note(target)` (stop the command) also fails
  both buffer tests.

## 2. An old path in a docstring, and a gate on the manual's sources

**Fix:** `cmd_flush`'s docstring now names
`threads/<Kind>/<Name>/logs/<date>.md`.

**Gate:** `manual-check` now also runs `stale_paths` over what the manual
is generated from: `src/adulting/*.py` (docstrings, help strings and
messages alike), `src/adulting/schemas/*.md` and `README.md`. On a hit it
names the file and line, and says to fix the source rather than
regenerate.

**Checked:**
- With the gate in place and the docstring not yet fixed, `dev/manual-check`
  exited 1 with exactly one hit,
  `src/adulting/buffer.py:539: … 'logs/<thread>/<date>.md (append if exists)
  and clear the buffer.'`. The line had moved from 519 because of item 1.
- After the fix it exits 0.

**Tests** in `tests/dev/test_manual_check.py`:
- the sources list includes the code, the schemas and the README;
- the old `cmd_flush` docstring is reported at its line;
- the committed sources have no hit.

**Undone:**
- Putting the old docstring back fails
  `test_the_committed_sources_name_no_old_layout_path`, along with the two
  existing `main` tests, since `main` now fails.
- Making the gate skip the sources fails
  `test_a_stale_path_in_a_docstring_is_reported_with_its_place`.

## 3. Two docstrings that were wrong

- The comment above `LAYOUT` now points to `tests/unit/test_layout.py`.
- `thread_folders()` no longer claims lint reports a folder with no thread
  file. It now says what happens: lint reports the files in such a folder,
  because their `thread:` does not resolve, and an empty one goes
  unremarked. I checked this against a scratch vault, where a log in
  `threads/Projects/Ghost/` with no `Ghost.md` gives `thread: wikilink
  '[[Projects/Ghost]]' does not resolve`. No lint rule was added, as the
  reviewer suggested.

## 4. The migration reads threads as the commands do

**What I found:** the CLI did not accept a one-line list either.
`parse_block` read `threads: ["[[Projects/A]]", "[[Projects/B]]"]` as one
string. `note_threads` then gave a single "thread" named by the whole
string, and lint's own parser kept it as a string too. Switching the script
to `note_threads` alone would therefore have made it refuse that note,
consistently with the CLI. 106 notes in the vault already write `aliases:`
this way, so one-line lists are real.

**What changed:**
- `vault.flow_list` reads a one-line YAML list:
  - it splits on commas outside quotes;
  - it reads `\"` inside double quotes as `"` (`notes new` writes a topic's
    quotes that way) and `''` inside single quotes as `'`;
  - a value starting with `[[` stays a wikilink scalar, so an unquoted
    `thread: [[Projects/A]]` reads as before.
- `parse_block` and lint's `parse_frontmatter` both use it.
- `dev/migrate-layout` drops its own parser and calls
  `V.note_threads(V.parse_frontmatter_doc(text)[0])`.
- `aliases:` now reads as a list. Nothing in the code reads `aliases`, and
  no schema declares it.

**Tests:**
- `test_a_one_line_threads_list_is_read_as_the_commands_read_it` in
  `tests/dev/test_migrate_layout.py`: a one-line `threads:` note moves to its
  first thread's folder.
- `test_a_one_line_threads_list_is_read_as_a_list` in
  `tests/cli/test_lint_cli.py`: lint is clean when the note is under its
  first thread, and reports the home-thread rule when it is not.
- Four parser tests in `tests/unit/test_vault.py`, including lint and
  `parse_frontmatter_doc` agreeing.

**Undone:**
- Taking flow lists out of `parse_block` fails the migration test and two
  vault tests.
- Taking them out of lint's parser fails the lint test and the agreement
  test.
- Removing the escape handling fails the quoting test.

## 5. What the migration does not do

It does not rewrite ordinary markdown links (`[text](path)`,
`![alt](path)`). A note moves two folders deeper, so a relative link in one
would break. The vault has no such links apart from a note's own
attachments, which move with it. This is now stated in the script's
docstring, with the `grep` to run before migrating a vault that might have
others, and here.

## 6. What `layout-compare` covers

`layout-compare` covered **read-only commands only**. The commands that
write — `notes new`, `notes copy`, `buffer add-*`, `buffer flush`,
`tasks` ingest and mutations, `hours log`, `edit`, `rm`, `payments log` —
were checked against the new layout by the test suite alone, not on the
copy of the vault.

## MANUAL.md

Not regenerated. Nothing the harvester reads changed in this round:
- the tool modules' docstrings, `--help` and `--help-json`;
- the `die()` lines it collects as exit codes;
- the schemas, README.md and `vault.LAYOUT`.

The source changes were all in function docstrings, error messages raised
as `ValueError`, and parsing. `manual-check` and `tools-check` pass against
the committed MANUAL.md and tool definitions.

# Round 2

**The problem:** the migration could fail halfway. On a read-only copy it
moved every file, then stopped with a `PermissionError` traceback while
rewriting links. The vault was left with every file moved and some links
rewritten, which is neither layout.

## 1. Nothing changes unless everything can

`dev/migrate-layout` now plans the whole migration and then checks it
against the filesystem before touching anything (`unwritable()`):
- each move needs its source folder to be writable, and the first existing
  folder on the way to its target;
- each file whose links are rewritten must be writable itself.

If anything fails the check, every such file is reported as `problem:
<path>: … not writable`, followed by `nothing changed: every file must be
writable before any is moved`, and the run exits 1. `--dry-run` reports the
same, so it shows these files before a real run does.

One step still runs after the moves: removing the old root folders once
they are empty. If that fails, it is reported as a problem and leaves an
empty folder behind; it no longer raises.

**Test:** `test_nothing_changes_unless_everything_can` in
`tests/dev/test_migrate_layout.py`, with three cases:
- a read-only log whose links need rewriting;
- a read-only file that does not move but is rewritten (`people/`);
- a read-only `notes/` folder that files must leave.

Each case asserts exit 1, the two messages, no traceback, and the vault
unchanged byte for byte. "Unchanged" means every file's bytes and every
path, folders included, are the same before and after.

**Undone:** with the check disabled (`blocked = []`), all three cases
fail.

**On a real copy:**
- A `cp -Rp` copy of the testbed's read-only `pristine/` exits 1 and
  reports 91 files as not writable, with no traceback. A checksum of every
  path, mode, size and file's contents is identical before and after.
- A writable copy, after `dev/testbed reset`, migrates as before: 135 + 211
  + 17 + 2 files and 141 links, then lint reports the same 18 violations.

## 2. Recovery instructions

`git reset --hard` alone restores the old paths but leaves the moved
copies behind as untracked files. The undo is
`git reset --hard && git clean -fd`. This is now stated in the script's
docstring and in the operator steps above ("Still to do", step 3).

Final state: `tests/dev` passes, and syntax, ruff, `--help-json` and the
three gates pass. Only `dev/migrate-layout` and its tests changed in this
round, so nothing the manual is built from changed.
