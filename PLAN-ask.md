# PLAN: `ask` implementation (revised)

Decomposition of [PRD-ask.md](PRD-ask.md) into stories for dispatch.
This revision (the second round) tightens resolver contracts, adds a
slot-schema lint, makes the test suite runnable without env tweaks,
and replaces the prose DoD with byte-exact acceptance rows from PRD
§7.2a.

## Scope decisions (user-confirmed)

| Decision           | Choice                                                                                 |
|--------------------|----------------------------------------------------------------------------------------|
| Phase              | Phase A only. Phase B (needle ML fallback) deferred per PRD §8.8.                      |
| Alpha intent set   | **Buffer-only**: `add-action`, `add-text`, `add-ref`, `list`. Matches PRD §8.8 alpha.  |
| Shared scoring     | Extract `fuzzy_score` from `people:108-125` into `_fuzzy.py` at repo root; refactor `people` to import it. |
| Test framework     | `pytest`. Runnable as plain `pytest tests/` — no `PYTHONPATH` override required.       |
| Adulting-side prereqs (S12) | Deferred. Beta/GA precondition per PRD §8.6; not blocking alpha.              |

## Stories

### S0 — Project plumbing (NEW)

**Deliverable:** `pytest tests/` from the repo root passes with no
environment variables set. `import ask_lib` works from any CWD inside
the repo.

- Add a minimal `pyproject.toml` at the repo root with `[tool.pytest.ini_options]` setting `pythonpath = ["."]` (sufficient for tests to import `ask_lib` and `_fuzzy` from the repo root without packaging).
- Alternative if simpler: add a 1-line `conftest.py` at the repo root that does `sys.path.insert(0, str(Path(__file__).parent))`. Pick whichever lands first; do not do both.
- Declare `dateparser` as a runtime dep in the same `pyproject.toml` (PEP 621 `[project] dependencies`). The installer (PRD §8.3) becomes `pip install -e .` instead of bare `pip install dateparser`.
- Update PRD §8.3 if needed (it currently says `pip install dateparser`).
- Verify: from a fresh shell, `cd /Users/riaz/projects/adulting && pytest tests/` collects and runs all tests without `ModuleNotFoundError`.

**Why this exists:** the first round's tests passed only with `PYTHONPATH=...` — DoD was prose, not a runnable check. S0 closes the meta-gap before S1 starts.

### S1 — Package skeleton & CLI scaffold

**Deliverable:** `adulting ask --help` works; `adulting ask "x"` exits 3 with the stub message from PRD §6.1.

- Create `ask` executable (Python entry, `chmod +x`).
- Create `ask_lib/` package per PRD §8.1: `__init__.py`, `cli.py`, `intents.py`, `resolvers.py`, `composer.py`, `executor.py`, `logger.py`, `types.py`. (No `needle.py` — Phase B deferred.)
- Argparse signature from PRD §4.1: positional `<query>`, flags `--yes/-y`, `--dry-run/-n`, `--no-needle`, `--explain`, `--json`. `--no-needle` is accepted as a no-op in alpha.
- Exit-code constants from PRD §4.1 (0–7).
- First-run config bootstrap: write `~/.adulting/config/ask.toml` from a template if missing (PRD §8.4). Template includes the new `min_match_score = 0.5` key under `[thresholds]`.
- Wire `--help-json` via existing `_argparse_helpjson` helper.
- Downstream modules are stubs that raise `NotImplementedError` (or return sentinel exit 3).

### S2 — Core data model

**Deliverable:** `ask_lib/types.py` with frozen dataclasses imported by everything downstream.

- `Intent`, `Slot`, `SlotKind` enum (PRD §4.2–4.3).
- `Resolution`, `SlotValue`, `Candidate`, `Ambiguity` (PRD §4.4).
- Type hints throughout. No logic.

### S3 — Intent table & classifier

**Deliverable:** `ask_lib/intents.py` returns matched `Intent` + confidence for buffer queries.

- `INTENTS` registry seeded with the **4 buffer rows from PRD §4.2** — verbatim. Slot lists must match PRD §4.2 exactly. **Do not add `--scheduled`** or any other slot not declared in PRD §4.2 (this is the regression from round 1). The slot-schema lint in S3.5 will fail the build if anything drifts.
- Leading-phrase regexes per PRD §4.2.
- `read_only=True` for `buffer.list`; `destructive=False` throughout.
- Classifier (PRD §5.2): `score = matched_length / total_query_length`; `confidence = 1.0 - (second_best_score / best_score)`. Below `intent_confidence_min` → exit 3.

### S3.5 — Slot-schema lint (NEW)

**Deliverable:** `tests/test_slot_schema.py` — passes when every `Intent.slots` is a subset of the underlying utility's argparse surface.

- For each Intent in `INTENTS`, run `<utility> --help-json` via subprocess (every adulting utility supports this) and parse the flag list.
- Assert every `Slot.cli_form` in the Intent (when non-empty) appears in the underlying utility's argparse flags. Positional slots (`cli_form==""`) are unchecked here.
- Asserts the alpha doesn't accidentally introduce flags the utility doesn't accept (this is exactly what produced the round-1 `--scheduled` bug).
- Cheap, mechanical, runs in CI alongside the rest of the suite.

### S4 — Person resolver

**Deliverable:** `ask_lib/resolvers.py:PersonResolver` returns `SlotValue`, `Ambiguity`, or `None` per the **PRD §5.3 return contract**.

- **First**: extract `fuzzy_score` from `people:108-125` into new top-level `_fuzzy.py`; refactor `people` to import it (verify `people list` still works).
- Score query against `{filename_stem, frontmatter.aliases}` for every file in `~/.adulting/people/`.
- Three-way return contract (PRD §5.3, **updated**):
  - `SlotValue` when `best_score >= min_match_score` AND `delta >= person_disambiguate`.
  - `Ambiguity` (top-3) when `best_score >= min_match_score` AND `delta < person_disambiguate`.
  - `None` when no candidate clears `min_match_score`.
- Unit test: with a single-file corpus and a query that fuzz-matches at score < 0.5, the resolver returns `None` (not `Ambiguity`, not `SlotValue`).

### S5 — Thread resolver

**Deliverable:** `ask_lib/resolvers.py:ThreadResolver` returns `SlotValue`, `Ambiguity`, or `None` per the **PRD §5.3 return contract**.

- Open threads by default (PRD F-4): filter on frontmatter `status: open`.
- Score against `{filename_stem, frontmatter.tags, frontmatter.aliases}` using 1-to-3-word query windows + capped recency boost `log(days_since_mtime)` (cap 0.1).
- **Same three-way return contract as S4** — including `None` when nothing clears `min_match_score`. The round-1 regression (a single-thread vault auto-picking a hallucinated 0.18 score because there was no runner-up) MUST be fixed here.
- Unit test (regression): a vault containing only `Processes/SGB.md` queried with `"remind me to send bern an email next tuesday"` returns a `SlotValue` only if the base score on `'sgb'` substring matches the SGB stem (lowercase substring → 0.7+ ✓). The same vault queried with `"do something completely unrelated"` returns `None`, **not** `SlotValue(Processes/SGB)`.

### S6 — Date resolver

**Deliverable:** `ask_lib/resolvers.py:DateResolver` returns `(SlotValue | Ambiguity | None)` and exposes `search_spans()` for the composer.

- Add `dateparser` to deps (declared in S0's `pyproject.toml`).
- `dateparser.search.search_dates(query, settings={'PREFER_DATES_FROM': 'future', 'RELATIVE_BASE': today()})`.
- **Pronoun / connective guard (PRD §5.4, NEW).** After `search_dates` returns, drop any matched span that does NOT contain at least one of:
  - a digit (`\d`), or
  - a weekday name (`monday`–`sunday`, case-insensitive), or
  - a month name (`january`–`december` or `jan`–`dec`), or
  - one of `today`, `tomorrow`, `yesterday`, `am`, `pm`.
  Regression test (verbatim from round-1 defect): `search_spans("remind me to send bern an email next tuesday")` MUST return `[("next tuesday", "2026-05-19")]` (anchor today=2026-05-15), NOT `[("me", "<anything>")]`.
- **Multi-DATE-slot dispatch (PRD §5.4, NEW).** The composer is responsible for assigning spans to slots in `intent.slots` order; the resolver simply returns all surviving spans. The DateResolver MUST NOT duplicate one span across multiple slots.

### S7 — Composer

**Deliverable:** `ask_lib/composer.py` produces the exact command string for preview + execution.

- Body composition (PRD §5.5): subtract leading verb phrase, person spans, thread spans, date spans; trim whitespace and trailing punctuation.
- **Multi-DATE-slot dispatch wiring.** When an Intent has N DATE slots and the DateResolver returned M spans, fill `intent.slots[i]` with `spans[i]` for `i < min(N, M)`. Extra spans are dropped (not stuffed elsewhere); missing slots stay unfilled (optional → flag omitted; required → caller handles).
- Empty residual + required slot → caller prompts.
- Command assembly using exact resolved values (PRD NF-6 — never bypass underlying validation). Slots that are unfilled have their flag omitted entirely; the assembler MUST NOT emit a flag with a blank value.
- Shell-safe rendering in preview; execution will be `shell=False` (handled in S8).

### S8 — Executor & logger

**Deliverable:** `ask_lib/executor.py` and `ask_lib/logger.py`.

- Executor: `subprocess.run(..., shell=False, text=True)` inheriting stdout/stderr. Returns underlying exit code; maps to ask's exit codes per PRD §4.1.
- Logger: stdlib `logging.handlers.RotatingFileHandler`, JSONL format per PRD §4.5, 10 MB / 3 generations (PRD NF-9).
- Log-write failures: warn to stderr, never break the run.

### S9 — Preview, confirm, disambiguation (main pipeline)

**Deliverable:** `ask_lib/cli.py` wires S3–S8 into the PRD §5.1 pipeline; happy paths work end-to-end.

- Read-only intents auto-execute with dimmed `[ask → <cmd>]` line on **stderr** (PRD F-7a).
- Non-read-only: print preview to stdout, prompt `[y/N]:` (default `N`).
- Disambiguation prompts (PRD §1.4 example). Non-interactive modes (`--yes`, `--dry-run`, `--json`, or no TTY) auto-pick the top candidate **only if** the resolver returned an `Ambiguity` (above-floor). If the resolver returned `None`, the pipeline treats the slot as unresolved.
- Destructive refusal (PRD F-12, exit 6) — defensive even though no destructive intents are seeded in alpha.
- `--yes` bypasses confirm; `--dry-run` prints preview to stdout and exits 0.
- `--json` emits `{query, intent, confidence, preview, cmd, exit_code}` on stdout and does NOT execute.

### S10 — Tests & fixture corpus

**Deliverable:** `tests/` runnable via `pytest tests/` (no `PYTHONPATH` override — S0 handles that); covers PRD §7.2b scenarios.

- `tests/fixtures/people/` — `Bern Sellmeyer.md`, `Alice Chen.md`, `Alice Vasquez.md`, `Old Contact.md`. Each with minimal frontmatter (`status: active`, optional `aliases:`).
- `tests/fixtures/threads/Processes/SGB.md` with `status: open`. Plus a closed thread to verify the open-by-default filter.
- Unit tests per resolver (S4, S5, S6). Include the regression tests called out in those stories.
- Intent classifier tests (S3).
- Pipeline integration tests with `subprocess.run` against a fake `$HOME` (`monkeypatch.setenv("HOME", ...)`); the real `buffer` script writes into the fake vault's `buffer.md`.
- **Out of scope here**: the 50-query acceptance corpus (PRD §7.1) — that's a beta release gate, not the alpha build artifact.

### S11 — Acceptance gate (NEW, replaces old S11 reordering)

**Deliverable:** `tests/test_acceptance.py` — one test per row in **PRD §7.2a**, asserting **byte-exact** preview match.

- Fixture: `today()` patched to `date(2026, 5, 15)` (PRD §7.2 anchor). `DateResolver` is constructed in `cli.py` with `relative_base=today()`; the test seam is the same monkeypatch.
- For each §7.2a row: `subprocess.run([ASK, "--dry-run", query], env={"HOME": fake_vault, ...})`, capture stdout, assert `stdout.strip() == expected_preview`.
- Failure prints the actual vs expected and which §7.2a row failed.
- This is the alpha DoD: if `test_acceptance.py` is green, the round-2 work is done. If any row fails, the corresponding implementation story is reopened.

### S12 — Adulting-side prereqs (deferred, was S11)

Tracked, not dispatched:

- `--json` output on remaining `threads`/`people` subcommands.
- `notes new` flag-only / non-interactive variants.
- `tasks *-matching` subcommands (8 per PRD §1.5).

Beta/GA preconditions per PRD §8.6. Re-evaluate after alpha lands.

## Dispatch sequence

Sequential waves with parallel work inside each. The acceptance gate (S11) runs last and gates DoD.

| Wave | Stories                                  | Parallelism                                                   |
|------|------------------------------------------|---------------------------------------------------------------|
| 1    | S0 + S1 + S2                             | One agent (tightly coupled, small)                            |
| 2    | S3, S4, S5, S6, S8                       | Five agents in parallel                                       |
| 3    | S7                                       | One agent (needs S3–S6 outputs)                               |
| 4    | S9, S10, S3.5, S11                       | Four agents in parallel (S11 may fail until S9 lands; that's the gate signal)  |

## Definition of done (alpha) — runnable, not prose

Round 2 replaces round 1's prose DoD with three exact commands. The
alpha is done **if and only if** each command below produces the
expected output.

**1. Plain `pytest` passes from a fresh shell.**

```
$ cd /Users/riaz/projects/adulting && pytest tests/
... all green ...
```

No `PYTHONPATH`, no `pip install dateparser`, no `pip install -e .` (or if needed, those steps belong in S0 and `pyproject.toml` should make `pytest` Just Work after a clean `pip install -e .`).

**2. The five §7.2a rows render byte-exact previews.**

`test_acceptance.py` (S11) runs each row in PRD §7.2a and asserts string equality against the **Expected preview** column. All five must pass.

**3. The v0 reference invocation prompts and executes.**

```
$ HOME=<fake_vault> ask "remind me to send bern an email next tuesday"
buffer add-action Processes/SGB 'send bern an email' --due 2026-05-19
[y/N]: y
# buffer.md gets a new ACTION line
```

(Tested as `B4` / declined-confirm `B6` in §7.2b.)

If any of the above fails, the corresponding story is not done — no partial credit.

## Notes on round-1 defects this PLAN closes

| Round-1 defect                                                    | Closed by                              |
|-------------------------------------------------------------------|----------------------------------------|
| `pytest tests/` errored without `PYTHONPATH`                      | S0 (project plumbing)                  |
| DateResolver picked "me" as a date                                | S6 pronoun/connective guard            |
| ThreadResolver auto-picked weak match when only 1 thread          | S5 absolute floor (PRD §5.3 contract)  |
| `buffer.add-action` slot list grew an unsanctioned `--scheduled`  | S3 (verbatim PRD §4.2) + S3.5 (lint)   |
| PRD §1.4 headline example didn't classify                         | PRD §1.4 rewrite (round-2 PRD edit)    |
| Prose DoD didn't catch any of the above                           | S11 byte-exact acceptance rows         |
