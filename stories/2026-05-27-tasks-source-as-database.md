# tasks — source-as-database

Date: 2026-05-27

## User story

As the operator of an `adulting` vault synced across multiple machines (laptop, desktop, container), I want every piece of task state to live in plain-text source files committed to git, so that vault sync is just git sync — never sqlite-conflict-recovery. The `tasks` CLI I use today should continue to work without behavior change, except for commands that only existed to manage the (now-removed) backend.

## Problem

The taskwarrior backend stores canonical engine-plane state in `~/vault/.adulting/task-data/taskchampion.sqlite3`. Syncing the vault across machines produces unmergeable binary conflicts. Recovery is manual.

The backend's value is small: source notes already carry uuid-anchored `TASK:`/`DONE:` lines as the user-visible state. Only six attrs (`entry`, `end`, `due`, `scheduled`, `priority`, `depends`) live exclusively in the backend.

## Goal

Remove the taskwarrior backend. Move the six attrs onto the on-disk anchor line in a schema-validated shape. Source notes become the sole storage; sync correctness reduces to git correctness.

## Out of scope

- New task-management features (`reopen`, `doctor`, `search`, `rm`, etc.). Strictly preserve current command surface minus install/migrate/rebuild.
- Changing the upstream buffer/notes workflow that *produces* `ACTION:` lines — unchanged.
- Compatibility with logseq/org. We borrow `[#H]` and the state-keyword pattern; we don't aim for interop.

## On-disk shape

```
TASK: [#H] (Assignee) <body> <!--<uuid8> entry:YYYY-MM-DD [end:YYYY-MM-DD] [due:YYYY-MM-DD] [scheduled:YYYY-MM-DD] [depends:<u8>,<u8>...]-->
```

Same shape for `DONE:`. Required: `uuid8`, `entry`. Required iff `kind=DONE`: `end`. Priority is in the visible `[#X]`, never in attrs. Order in the attr block is fixed; the writer is the only authority.

Examples:

```
TASK: [#H] (Riaz) Send quarterly report <!--abcd1234 entry:2026-05-27 due:2026-05-29-->
TASK: Pick up dry cleaning <!--ef567890 entry:2026-05-27-->
DONE: [#M] (Charlie) Review the contract <!--abc12340 entry:2026-05-24 end:2026-05-27-->
```

## Schema & lint

New `schemas/task_anchor.md`, scope=line, one named capture per field. `lint` validates each capture via the existing scalar DSL (`regex=`, `enum`, `min=`).

Cross-vault checks added to `lint` end-of-run (matching the precedent at `lint:372–375`):

- `uuid` unique across the whole vault.
- each `depends` entry resolves to a `task_anchor.uuid` somewhere.
- `depends` graph is acyclic.
- `kind=DONE` requires `end`.
- `end >= entry` (string compare; ISO dates sort lexically).
- `assignee` resolves to `people/<name>.md` (existing wikilink resolution pattern).

## Command changes

| Today | After | Δ |
|---|---|---|
| `tasks` (no args) | same | ingest only — no sync (no second store) |
| `tasks add` | same | unchanged — delegates to `buffer add-action` |
| `tasks done` | same | rewrite source line, append `end:<today>` |
| `tasks set-description` | same | rewrite source body |
| `tasks set-assignee` | same | rewrite `(Assignee)` prefix |
| `tasks set-due` | same | rewrite/insert `due:` |
| `tasks set-scheduled` | same | rewrite/insert `scheduled:` |
| `tasks set-priority` | same | rewrite/insert `[#X]` in visible portion |
| `tasks add-depends` | same | append to `depends:` |
| `tasks rm-depends` | same | remove from `depends:` |
| `tasks list` | same | walk vault; new flags replace tw DSL: `--priority`, `--thread`, `--assignee`, `--overdue` |
| `tasks next` | same | sort by (priority, due, entry) asc; top 5 |
| `tasks show` | same | render parsed anchor |
| `tasks rebuild` | **removed** | no second store to reconcile |
| `tasks install` | **removed** | no backend to install |
| `tasks migrate-layout` | **removed** | obsolete one-shot |

## Acceptance criteria

1. Every `TASK:`/`DONE:` anchor in `~/vault/notes/` and `~/vault/logs/` matches the new schema.
2. `lint` reports zero violations on the migrated vault.
3. All ~308 source-anchored tw records carry their `entry`/`end`/`due`/`scheduled`/`priority`/`depends` onto their source line.
4. The ~68 tw-only records (no source anchor) are logged to `~/vault/.adulting/migration-orphans.txt`; not silently dropped.
5. `~/vault/.adulting/{bin,task-data,taskrc}` removed after migration verifies clean.
6. Every preserved `tasks <subcommand>` works on the new format with output equivalent to today's (modulo sort-tiebreaker indeterminacy).
7. Pytest suite covering each subcommand and the lint rules passes (`pytest tests/`).

## Risks

- **Multi-line/odd-whitespace bodies** break migration regex → log to orphans, continue.
- **tw description != source body** (6 known cases per CHANGELOG): source-wins, log conflicts.
- **Cutting tw before migration validates**: sequencing protects against this — backend deletion is the last step.

## Sequencing

1. `schemas/task_anchor.md` + `lint` patch + tests (no behavior change yet).
2. `migrate-tw-to-source` one-shot script + tests; dry-run, then live on `~/vault`.
3. Rewrite `tasks` to read/write source directly; tests.
4. Delete tw plumbing (`cmd_install`, `cmd_migrate_layout`, `cmd_rebuild`, `cmd_sync`, `task_cmd`, `task_env`, `tw_modify`, `ensure_uda`); delete `~/vault/.adulting/{bin,task-data,taskrc}`; update README/CHANGELOG.

## Inventory (snapshot from `~/vault` at start of work)

- 376 tw records (44 pending, 316 completed, 16 deleted)
- 308 anchored `TASK:`/`DONE:` lines in source
- 0 unmigrated `ACTION:` lines
- ~321 tw records carry the `source` UDA
- attrs in tw: 10 with priority, 26 with due, 16 with scheduled, 1 with depends
- backup at `~/vault.bak` (operator-supplied)
