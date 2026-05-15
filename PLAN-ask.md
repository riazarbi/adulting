# PLAN: `ask` implementation

Decomposition of [PRD-ask.md](PRD-ask.md) into stories for dispatch. Captured here so the postmortem can compare against what shipped.

## Scope decisions (user-confirmed)

| Decision           | Choice                                                                                 |
|--------------------|----------------------------------------------------------------------------------------|
| Phase              | Phase A only. Phase B (needle ML fallback) deferred per PRD §8.8.                      |
| Alpha intent set   | **Buffer-only**: `add-action`, `add-text`, `add-ref`, `list`. Matches PRD §8.8 alpha. |
| Shared scoring     | Extract `fuzzy_score` from `people:108-125` into `_fuzzy.py` at repo root; refactor `people` to import it. |
| Test framework     | `pytest` (first test infrastructure in the repo).                                      |
| Adulting-side prereqs (S11) | Deferred. Beta/GA precondition per PRD §8.6; not blocking alpha.              |

## Stories

### S1 — Package skeleton & CLI scaffold

**Deliverable:** `adulting ask --help` works; `adulting ask "x"` exits 3 with stub message.

- Create `ask` executable (Python entry, `chmod +x`).
- Create `ask_lib/` package per PRD §8.1: `__init__.py`, `cli.py`, `intents.py`, `resolvers.py`, `composer.py`, `executor.py`, `logger.py`. (No `needle.py` — Phase B deferred.)
- Argparse signature from PRD §4.1: positional `<query>`, flags `--yes/-y`, `--dry-run/-n`, `--no-needle`, `--explain`, `--json`.
- Exit-code constants from PRD §4.1 (0–7).
- First-run config bootstrap: write `~/.adulting/config/ask.toml` from a template if missing (PRD §8.4). Template has `phase_b.enabled = false`.
- Wire `--help-json` via existing `_argparse_helpjson` helper.
- Downstream modules are stubs that raise `NotImplementedError` (or return sentinel exit 3).

### S2 — Core data model

**Deliverable:** `ask_lib/types.py` with frozen dataclasses imported by everything downstream.

- `Intent`, `Slot`, `SlotKind` enum (PRD §4.2–4.3).
- `Resolution`, `SlotValue`, `Candidate`, `Ambiguity` (PRD §4.4).
- Type hints throughout. No logic.

### S3 — Intent table & classifier

**Deliverable:** `ask_lib/intents.py` returns matched `Intent` + confidence for buffer queries.

- `INTENTS` registry seeded with **4 buffer rows** from PRD §1.5: `add-action`, `add-text`, `add-ref`, `list`.
- Leading-phrase regexes per PRD §4.2 example.
- Slot schemas per PRD §4.2 example (e.g. `add-action` has `thread`, `body`, `due`, `priority`).
- `read_only=True` for `buffer.list`; `destructive=False` throughout.
- Classifier (PRD §5.2): `score = matched_length / total_query_length`; `confidence = 1.0 - (second_best_score / best_score)`. Below `intent_confidence_min` → exit 3.

### S4 — Person resolver

**Deliverable:** `ask_lib/resolvers.py:PersonResolver` returns top candidate or `Ambiguity`.

- **First**: extract `fuzzy_score` from `people:108-125` into new top-level `_fuzzy.py`; refactor `people` to import it (verify `people list` still works).
- Score query against `{filename_stem, frontmatter.aliases}` for every file in `~/.adulting/people/`.
- Auto-pick when `best_score - second_best_score >= person_disambiguate`; else return `Ambiguity` with top candidates.

### S5 — Thread resolver

**Deliverable:** `ask_lib/resolvers.py:ThreadResolver` returns top candidate or `Ambiguity`.

- Open threads by default (PRD F-4).
- Score against `{filename_stem, frontmatter.tags, frontmatter.aliases}` + recency boost `log(days_since_mtime)`.
- Same delta-threshold contract as S4 (`thread_disambiguate`).

### S6 — Date resolver

**Deliverable:** `ask_lib/resolvers.py:DateResolver` returns `(date_str, matched_span)` or `Ambiguity`.

- Add `dateparser` to deps (PRD §8.2).
- `dateparser.parse(query, settings={'PREFER_DATES_FROM': 'future', 'RELATIVE_BASE': today()})`.
- Use `dateparser.search.search_dates` to record matched spans (composer needs them to strip from body).
- Multiple spans → pick per intent's date-slot semantics; else `Ambiguity`.

### S7 — Composer

**Deliverable:** `ask_lib/composer.py` produces the exact command string for preview + execution.

- Body composition (PRD §5.5): subtract leading verb phrase, person spans, thread spans, date spans; trim whitespace and trailing punctuation.
- Empty residual + required slot → caller prompts.
- Command assembly using exact resolved values (PRD NF-6 — never bypass underlying validation).
- Shell-safe rendering in preview; execution will be `shell=False` (handled in S8).

### S8 — Executor & logger

**Deliverable:** `ask_lib/executor.py` and `ask_lib/logger.py`.

- Executor: `subprocess.run(..., shell=False, text=True)` inheriting stdout/stderr. Returns underlying exit code; maps to ask's exit codes per PRD §4.1.
- Logger: stdlib `logging.handlers.RotatingFileHandler`, JSONL format per PRD §4.5, 10 MB / 3 generations (PRD NF-9).
- Log-write failures: warn to stderr, never break the run.

### S9 — Preview, confirm, disambiguation (main pipeline)

**Deliverable:** `ask_lib/cli.py` wires S3–S8 into the PRD §5.1 pipeline; happy paths work end-to-end.

- Read-only intents auto-execute with dimmed `[ask → <cmd>]` line (PRD F-7a).
- Non-read-only: print preview, prompt `[y/N]:` (default `N`).
- Disambiguation prompts (PRD §1.4 example), exit 4 if user quits.
- Destructive refusal (PRD F-12, exit 6) — defensive even though no destructive intents are seeded in alpha.
- `--yes` bypasses confirm; `--dry-run` prints preview and exits 0.

### S10 — Tests & fixture corpus

**Deliverable:** `tests/` runnable via `pytest`; covers PRD §7.2 scenarios 1–15 applicable to buffer.

- `tests/fixtures/people/` and `tests/fixtures/threads/` — small synthetic vault.
- Unit tests per resolver (S4, S5, S6).
- Intent classifier tests (S3).
- Pipeline integration tests with `subprocess.run` patched to record-not-execute.
- **Out of scope here**: the 50-query acceptance corpus (PRD §7.1) — that's a release gate, not a build artifact.

### S11 — Adulting-side prereqs (deferred)

Tracked, not dispatched:

- `--json` output on remaining `threads`/`people` subcommands.
- `notes new` flag-only / non-interactive variants.
- `tasks *-matching` subcommands (8 per PRD §1.5).

Beta/GA preconditions per PRD §8.6. Re-evaluate after alpha lands.

## Dispatch sequence

Sequential waves with parallel work inside each:

| Wave | Stories                         | Parallelism |
|------|---------------------------------|-------------|
| 1    | S1 + S2                         | One agent (tightly coupled, small) |
| 2    | S3, S4, S5, S6, S8              | Five agents in parallel |
| 3    | S7                              | One agent (needs S3–S6 outputs) |
| 4    | S9, S10                         | Two agents (S10 can start once S2 lands; integration tests need S9) |

## Definition of done (alpha)

- `adulting ask "remind me to send bern an email next tuesday"` produces a preview matching PRD §1.4, prompts, and on `y` runs the underlying `buffer add-action`.
- `adulting ask "what's in my buffer"` auto-executes `buffer list` with dimmed preview.
- `adulting ask "delete the launch thread"` exits 6 with refusal message.
- All PRD §7.2 scenarios applicable to buffer pass via `pytest`.
- `~/.adulting/ask.log` accumulates JSONL entries per PRD §4.5; rotates at 10 MB.
- `dateparser` is the only new runtime dependency.
