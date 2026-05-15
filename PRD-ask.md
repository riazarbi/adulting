# PRD: `ask` — natural-language entry point for adulting

## 1. Overview

### 1.1 Problem

The adulting utilities are clean CLIs but require exactness that's at
odds with how a user thinks in the moment of capture:

- Threads must resolve to a real `threads/<Kind>/<Name>.md` file —
  exact path, case-sensitive, no fuzzy match at action time.
- Assignees must resolve to a real `people/<Name>.md` file — exact
  filename, case-sensitive.
- Dates must be `YYYY-MM-DD`. Relative terms like "tomorrow" or
  "friday" are rejected by `tasks`.
- The user has to know which subcommand of which utility corresponds
  to what they're trying to do.

This raises friction for the highest-frequency use case — fast
capture. "Remind me to send Bern an email next Tuesday" is what the
user thinks; `buffer add-action Processes/SGB "send Bern Sellmeyer
an email" --due 2026-05-21` is what the system needs.

### 1.2 Goals

- Convert natural-language queries into adulting CLI invocations.
- Make ambiguity visible via a preview-and-confirm step.
- Stay dependency-light and deterministic where possible.
- Build incrementally — measure where rules fail before adding ML.

### 1.3 Non-goals

- Replace direct CLI use. `ask` is an additional entry point.
- Handle destructive operations (`delete`, `rm`) in v1.
- Reach interactive subcommands without explicit non-interactive
  variants existing first.
- Support multi-action queries ("do X and then Y") in v1.
- Coreference resolution ("tell **him** to...") in v1.
- Become a general-purpose assistant.

### 1.4 User experience

    $ adulting ask "send bern an email next tuesday"
    → buffer add-action Processes/SGB "send Bern Sellmeyer an email" --due 2026-05-21
    [y/N]: y

When the formatter can't decide:

    $ adulting ask "remind alice about the launch friday"
    People matching "alice":
      1. Alice Chen        (Projects/Q3-launch, 3 recent notes)
      2. Alice Vasquez     (Projects/SGB,       0 recent notes)
    Which one? [1/2/q]:

When parsing fails outright:

    $ adulting ask "next steps on the launch"
    Could not classify intent. Try a leading verb like "remind me to",
    "note that", or "show me".

Read-only queries skip the confirmation step. The inferred command is
printed dimmed for transparency, then its output streams through:

    $ adulting ask "what's my next task"
    [ask → tasks next]
    abc12345 H 2026-05-18 Projects/SGB  Review the migration doc

### 1.5 Command coverage

Every adulting subcommand is classified below. The intent table is the
extension point: each row in the table maps to one entry in
`ask_lib/intents.py`. Rolling out coverage = filling in rows; the
resolver, composer, and executor pipeline is utility-agnostic.

Legend for **Status**:
✓ Ready, ⚠ Needs adulting-side change, ✗ Out of scope for v1.

Legend for **Class**: `read` (no state change), `create` (new state),
`modify` (existing state), `destructive` (irreversible), `meta`
(maintenance / not user-facing).

#### `buffer`

| Subcommand    | Example NL                       | Class       | Status | Notes                                                | Phase |
|---------------|----------------------------------|-------------|--------|------------------------------------------------------|-------|
| `add-action`  | "remind me to call alice friday" | create      | ✓      | The v0 reference path.                               | A     |
| `add-text`    | "note that the SGB meeting ran"  | create      | ✓      | Same shape as `add-action`, no due slot.             | A     |
| `add-ref`     | "save this link for SGB ..."     | create      | ✓      | URL extracted by regex.                              | A     |
| `list`        | "what's in my buffer"            | read        | ✓      | Read-only; no confirm.                               | A     |
| `rm`          | "remove buffer line 3"           | destructive | ✗      | Takes a line number; users invoke CLI directly.      | —     |
| `tend`        | "tend the buffer"                | meta        | ✗      | Not user-facing NL; CLI direct.                      | —     |
| `flush`       | "flush the buffer"               | meta        | ✗      | Same.                                                | —     |

#### `tasks`

| Subcommand          | Example NL                              | Class       | Status | Notes                                                                 | Phase |
|---------------------|-----------------------------------------|-------------|--------|-----------------------------------------------------------------------|-------|
| `add`               | "add a task to SGB to review the doc"   | create      | ✓      | Delegates to `buffer add-action` already.                             | A     |
| `done`              | "mark the migration doc task done"      | destructive | ⚠      | Reversible but treated destructive in v1. Needs `done-matching`.      | B     |
| `set-description`   | "rename task X to Y"                    | modify      | ⚠      | Needs `set-description-matching`. Free-form text → Phase B.           | B     |
| `set-assignee`      | "assign the doc review to bern"         | modify      | ⚠      | Needs `set-assignee-matching`.                                        | A     |
| `set-due`           | "due date for the doc review is friday" | modify      | ⚠      | Needs `set-due-matching`.                                             | A     |
| `set-scheduled`     | "schedule the review for next monday"   | modify      | ⚠      | Needs `set-scheduled-matching`.                                       | A     |
| `set-priority`      | "make the doc review high priority"     | modify      | ⚠      | Needs `set-priority-matching`.                                        | A     |
| `add-depends`       | "make task X depend on task Y"          | modify      | ⚠      | Needs two `-matching` resolutions. Hard.                              | B     |
| `rm-depends`        | "remove dependency between X and Y"     | modify      | ⚠      | Same.                                                                 | B     |
| `list`              | "show me my tasks"                      | read        | ✓      | Read-only.                                                            | A     |
| `next`              | "what's my next task"                   | read        | ✓      | Read-only; user's example query.                                      | A     |
| `show`              | "show me the doc review task"           | read        | ⚠      | Needs `show-matching`.                                                | A     |
| `rebuild`           | —                                       | meta        | ✗      | Not user-facing.                                                      | —     |
| (bare)              | —                                       | meta        | ✗      | Ingest pre-pass; not user-facing.                                     | —     |

#### `notes`

| Subcommand | Example NL                                  | Class       | Status | Notes                                                                     | Phase |
|------------|---------------------------------------------|-------------|--------|---------------------------------------------------------------------------|-------|
| `new`      | "start a meeting note for SGB about Q3"     | create      | ⚠      | Needs flag-only `new`. Free-form topic/body → Phase B.                    | B     |
| `last`     | "show my last note"                         | read        | ✓      | Already non-interactive.                                                  | A     |
| `cat`      | "show me the SGB meeting note from monday"  | read        | ⚠      | Needs `cat-matching` (resolve note by content/date).                      | B     |
| `agenda`   | "what's on the agenda for SGB"              | read        | ⚠      | Needs non-interactive variant.                                            | A     |
| `minutes`  | "make minutes from the SGB meeting"         | create      | ⚠      | Needs `minutes-matching`; writes PDF.                                     | B     |
| `pdf`      | "export the SGB note as pdf"                | create      | ⚠      | Needs `pdf-matching`.                                                     | A     |
| `edit`     | "edit the SGB note"                         | modify      | ✗      | Opens editor (multi-step external process); not NL-reachable.             | —     |
| `nano`     | —                                           | modify      | ✗      | Same.                                                                     | —     |
| `copy`     | "copy the SGB template note"                | create      | ⚠      | Needs `copy-matching`.                                                    | A     |
| `strip`    | —                                           | meta        | ✗      | Not user-facing NL.                                                       | —     |
| `delete`   | —                                           | destructive | ✗      | CLI direct.                                                               | —     |

#### `threads`

| Subcommand | Example NL                                | Class       | Status | Notes                                                | Phase |
|------------|-------------------------------------------|-------------|--------|------------------------------------------------------|-------|
| `new`      | "create a new project thread for Q4"      | create      | ✓      | Already supports flag-only.                          | A     |
| `list`     | "what threads do I have"                  | read        | ✓      | Read-only; already `--json`.                         | A     |
| `show`     | "tell me about the SGB project"           | read        | ✓      | Resolver picks the thread; underlying takes exact.    | A     |
| `delete`   | —                                         | destructive | ✗      | CLI direct.                                          | —     |

#### `people`

| Subcommand | Example NL                                | Class       | Status | Notes                                                | Phase |
|------------|-------------------------------------------|-------------|--------|------------------------------------------------------|-------|
| `new`      | "add bern sellmeyer as a contact"         | create      | ✓      | Already supports flag-only.                          | A     |
| `list`     | "who do I know"                           | read        | ✓      | Read-only.                                           | A     |
| `show`     | "tell me about bern"                      | read        | ✓      | Resolver picks the person.                           | A     |
| `delete`   | —                                         | destructive | ✗      | CLI direct.                                          | —     |

#### `lint`

| Subcommand | Example NL                  | Class | Status | Notes                          | Phase |
|------------|-----------------------------|-------|--------|--------------------------------|-------|
| (bare)     | "is anything broken in my vault" | read  | ✓      | Trivial dispatch.              | A     |

#### Summary

- **Total subcommands**: 36 across six utilities.
- **In scope for `ask` (eventually)**: 26.
- **Out of scope** (destructive, meta, editor-launching): 10.
- **Ready as-is**: 11. Most are reads.
- **Needs an adulting-side change**: 15. The changes cluster as:
  - 8 `<verb>-matching` subcommands on `tasks` and `notes`.
  - 4 non-interactive variants on `notes`.
  - 3 minor `--json`/flag additions on existing commands.
- **Phase A reachable**: ~17 once `-matching` variants land on `tasks`.
- **Phase B reachable**: the remainder — free-form text composition,
  multi-slot dependency edits, content-matched notes.

Coverage is bounded but explicit. Every row not marked ✗ has a
concrete path to inclusion; the architecture does not need to change
to add any of them.

## 2. Requirements

### 2.1 Functional requirements

| ID    | Requirement                                                                                                  | Phase |
|-------|--------------------------------------------------------------------------------------------------------------|-------|
| F-1   | Accept a natural-language query as a single positional argument.                                             | A     |
| F-2   | Classify intent against a registered set of (utility, subcommand) pairs.                                     | A     |
| F-3   | Resolve person references against `~/.adulting/people/` using fuzzy scoring.                                 | A     |
| F-4   | Resolve thread references against `~/.adulting/threads/`, restricted to open threads by default.             | A     |
| F-5   | Resolve date references via `dateparser` with `RELATIVE_BASE=today()`, `PREFER_DATES_FROM=future`.           | A     |
| F-6   | Render a preview of the assembled command in shell-copyable form.                                            | A     |
| F-7   | Require explicit user confirmation (default `N`) before execution, **except for intents marked read-only**.  | A     |
| F-7a  | Read-only intents auto-execute. Print the inferred command on a dimmed line for transparency, then output.   | A     |
| F-8   | Execute the resolved command via `subprocess.run` on confirmation (or immediately for read-only).            | A     |
| F-9   | Surface the underlying utility's stdout and stderr verbatim.                                                 | A     |
| F-10  | Surface candidates and prompt the user when person/thread resolution is ambiguous.                           | A     |
| F-11  | Log every invocation (query, preview, confirmation, exit code) to `~/.adulting/ask.log` in JSONL format.     | A     |
| F-12  | Refuse to dispatch destructive operations (`delete`, `rm`) — exit with a clear message.                      | A     |
| F-13  | Provide `--yes` to bypass confirmation (for scripting) and `--dry-run` to preview without executing.         | A     |
| F-14  | Fall back to needle inference when Phase A confidence is below threshold.                                    | B     |
| F-15  | Pre-pend `"Today is YYYY-MM-DD. "` to the query before sending to needle.                                    | B     |
| F-16  | Build the needle tool manifest per-call, embedding Phase A's top candidates as parameter-description enums.  | B     |

### 2.2 Non-functional requirements

| ID     | Requirement                                                                                                    |
|--------|----------------------------------------------------------------------------------------------------------------|
| NF-1   | Phase A: median query-to-preview latency under 1 second on a corpus of 500 people and 200 threads.             |
| NF-2   | Phase B: median latency under 2 seconds on the same corpus.                                                    |
| NF-3   | Phase A has no ML dependencies. Pure Python plus `dateparser`.                                                 |
| NF-4   | Deterministic output for a given (query, corpus) pair in Phase A.                                              |
| NF-5   | Failures are transparent: the preview must show exactly what will run, byte-for-byte.                          |
| NF-6   | `ask` must not bypass the underlying utility's validation. Resolved values are passed in exact form.           |
| NF-7   | No network calls. All inference (Phase B) runs locally.                                                        |
| NF-8   | Works offline, with no external API dependencies.                                                              |
| NF-9   | Log file must not grow unbounded. Rotate at 10 MB, keep 3 generations.                                         |
| NF-10  | Phase B is opt-in via config until measured to be net-positive against Phase A alone.                          |

## 3. Architecture and data handling

### 3.1 Components

    ┌────────────────────────────────────────────────────────────┐
    │  adulting ask "<query>"                                    │
    │                                                            │
    │   ┌──────────────┐    ┌─────────────────┐                  │
    │   │ Tokenizer    │ →  │ Intent classifier│                  │
    │   └──────────────┘    └─────────────────┘                  │
    │                                ↓                           │
    │   ┌────────────────────────────────────────┐               │
    │   │ Resolvers (parallel):                  │               │
    │   │   - PersonResolver  (fuzzy_score)      │               │
    │   │   - ThreadResolver  (fuzzy_score)      │               │
    │   │   - DateResolver    (dateparser)       │               │
    │   └────────────────────────────────────────┘               │
    │                                ↓                           │
    │   ┌──────────────┐    ┌────────────────┐                   │
    │   │ Composer     │ →  │ Preview & confirm│                  │
    │   └──────────────┘    └────────────────┘                   │
    │                                ↓                           │
    │   ┌──────────────┐                                         │
    │   │ Executor     │  → subprocess.run(adulting utility)     │
    │   └──────────────┘                                         │
    │                                                            │
    │   (Phase B: NeedleFallback inserted between classifier     │
    │    and resolvers when classifier confidence < threshold)   │
    └────────────────────────────────────────────────────────────┘

### 3.2 Data sources (read-only)

| Path                              | Used by         | Read pattern                                       |
|-----------------------------------|-----------------|----------------------------------------------------|
| `~/.adulting/people/*.md`         | PersonResolver  | Filenames + frontmatter; cached for one invocation |
| `~/.adulting/threads/<Kind>/*.md` | ThreadResolver  | Filenames + frontmatter (status, mtime)            |
| `~/.adulting/notes/`              | ThreadResolver  | mtimes only, for recency boost (optional v1.1)     |
| `~/.adulting/config/ask.toml`     | All             | Settings (thresholds, Phase B enable)              |

### 3.3 Data sinks

| Path                          | Format | Purpose                                               |
|-------------------------------|--------|-------------------------------------------------------|
| `stdout`                      | Text   | Preview, prompts, executed command output             |
| `stderr`                      | Text   | Errors, disambiguation                                |
| `~/.adulting/ask.log`         | JSONL  | One line per invocation; rotated at 10 MB             |

### 3.4 State

`ask` is stateless across invocations. Every run reads the corpus
fresh. No caching to disk between invocations (the corpus is small
enough that scanning it costs <100ms; cache invalidation isn't worth
the complexity).

### 3.5 Process model

`ask` is a single Python process. The underlying adulting utility is
invoked via `subprocess.run` with `text=True`. The subprocess inherits
stdout/stderr so its output streams through naturally. No shell is
used (`shell=False`) to avoid injection from query content that ends
up in body strings.

## 4. Interfaces

### 4.1 CLI signature

    adulting ask [options] <query>

    Options:
      --yes, -y         Skip confirmation (for scripting)
      --dry-run, -n     Show preview, do not execute, do not prompt
      --no-needle       Disable Phase B fallback for this invocation
      --explain         Print scoring details for resolver candidates
      --json            Emit machine-readable result instead of running

    Exit codes:
      0   Command executed, underlying exit code 0
      1   Command executed, underlying non-zero exit code
      2   User declined the preview
      3   Could not classify intent
      4   Ambiguity unresolved (user quit disambiguation prompt)
      5   Malformed or empty query
      6   Refused (destructive operation)
      7   Internal error in ask itself

### 4.2 Intent table entry

```python
@dataclass(frozen=True)
class Intent:
    name: str                    # "buffer.add-action"
    patterns: list[re.Pattern]   # leading-phrase regexes
    utility: str                 # "buffer"
    subcommand: str              # "add-action"
    slots: list[Slot]            # ordered slot schema
    read_only: bool = False      # if True, skip confirmation (auto-exec)
    destructive: bool = False    # if True, ask refuses outright
```

Adding a new intent is a single record in `ask_lib/intents.py`. The
classifier, resolvers, composer, and executor are utility-agnostic and
do not need modification when intents are added. This is the
extensibility contract for full-coverage rollout.

Example registrations for the user's "what's my next task" query and
the v0 reference path:

```python
INTENTS = [
    Intent(
        name="tasks.next",
        patterns=[re.compile(r"^(what'?s? )?(my )?next task")],
        utility="tasks",
        subcommand="next",
        slots=[],
        read_only=True,
    ),
    Intent(
        name="buffer.add-action",
        patterns=[re.compile(r"^remind me to|^add(?: an?)? action")],
        utility="buffer",
        subcommand="add-action",
        slots=[
            Slot("thread",  SlotKind.THREAD, required=True,  cli_form=""),
            Slot("body",    SlotKind.TEXT,   required=True,  cli_form=""),
            Slot("due",     SlotKind.DATE,   required=False, cli_form="--due"),
            Slot("priority",SlotKind.ENUM,   required=False, cli_form="--priority",
                            enum_values=["H","M","L"]),
        ],
    ),
    # ...
]
```

### 4.3 Slot schema

```python
@dataclass(frozen=True)
class Slot:
    name: str                    # "thread", "assignee", "due", "body"
    kind: SlotKind               # PERSON | THREAD | DATE | TEXT | ENUM
    required: bool
    cli_form: str                # "--due" or "" for positional
    enum_values: list[str] = field(default_factory=list)  # for ENUM only
```

### 4.4 Resolution result

```python
@dataclass
class Resolution:
    intent: Intent | None
    slots: dict[str, SlotValue]      # name → resolved value
    confidence: float                # 0.0–1.0
    ambiguities: list[Ambiguity]     # unresolved choices
    phase: Literal["A", "B"]

@dataclass
class SlotValue:
    value: str                       # the exact string passed to CLI
    source: Literal["query", "default", "needle"]
    candidates: list[Candidate]      # top-K with scores

@dataclass
class Candidate:
    value: str
    score: float
    explanation: str                 # for --explain
```

### 4.5 Log entry (JSONL)

```json
{
  "ts": "2026-05-15T14:32:01Z",
  "query": "send bern an email next tuesday",
  "phase": "A",
  "intent": "buffer.add-action",
  "confidence": 0.87,
  "preview": "buffer add-action Processes/SGB \"send Bern Sellmeyer an email\" --due 2026-05-21",
  "confirmed": true,
  "exit_code": 0,
  "duration_ms": 412
}
```

Failed parses log with `"intent": null` and `"error": "<reason>"`.

### 4.6 Config file

`~/.adulting/config/ask.toml`:

```toml
[thresholds]
intent_confidence_min = 0.6     # below this, fall back to Phase B
person_disambiguate   = 0.15    # max delta between top two for auto-pick
thread_disambiguate   = 0.15

[phase_b]
enabled    = false
model_path = "~/.cache/needle/26m-int8"

[date]
prefer_future  = true
locale         = "en_US"

[log]
path           = "~/.adulting/ask.log"
rotate_mb      = 10
keep_files     = 3
```

## 5. Algorithm / business logic

### 5.1 Phase A pipeline

    parse(query):
        tokens     = tokenize(query.lower())
        intent     = classify_intent(tokens, query)
        if intent is None or intent.destructive:
            return failure(EXIT_3 or EXIT_6)

        slots = {}
        for slot in intent.slots:
            match slot.kind:
                PERSON: slots[slot.name] = resolve_person(query)
                THREAD: slots[slot.name] = resolve_thread(query)
                DATE:   slots[slot.name] = resolve_date(query)
                TEXT:   slots[slot.name] = compose_body(query, slots)
                ENUM:   slots[slot.name] = resolve_enum(query, slot)

        check_required(intent, slots)
        check_ambiguities(slots) -> may prompt user

        cmd = compose_command(intent, slots)
        if intent.read_only:
            print_dim(f"[ask → {cmd}]")
            return execute(cmd)               # no confirmation
        if not user_confirms(cmd): return EXIT_2
        return execute(cmd)

### 5.2 Intent classification

Leading-phrase regex match against the intent table. First match wins.
Score = fraction of the regex matched plus a small bonus for a longer
literal prefix. Confidence = score normalized against the
second-best match.

    score = matched_length / total_query_length
    confidence = 1.0 - (second_best_score / best_score)

If `confidence < intent_confidence_min`:

- Phase A only: return EXIT_3.
- Phase B enabled: invoke needle fallback.

### 5.3 Person/thread resolution

Each candidate file is scored using `fuzzy_score()` from
`people.py:108-125`. Inputs:

- For people: the query text scored against `{filename_stem,
  frontmatter.aliases}`.
- For threads: the query text scored against `{filename_stem,
  frontmatter.tags, frontmatter.aliases}`, with a recency boost
  proportional to `log(days_since_mtime)`.

The top candidate is auto-selected when:

    best_score - second_best_score >= person_disambiguate (or thread_disambiguate)

Otherwise, the resolver returns an `Ambiguity` and the caller surfaces
a numbered prompt.

### 5.4 Date resolution

`dateparser.parse(query, settings={'PREFER_DATES_FROM': 'future',
'RELATIVE_BASE': today()})` is invoked on the whole query. The matched
span (returned via `dateparser.search.search_dates`) is recorded so it
can be stripped from the body.

If multiple date spans are found, the resolver picks the one that best
aligns with the intent's date slot semantics (e.g. `--due` prefers
future, `--scheduled` prefers near-future). If still ambiguous, prompt
the user.

### 5.5 Body composition

    body = original_query
         - matched leading verb phrase
         - matched person spans
         - matched thread spans
         - matched date spans
         - trim whitespace and trailing punctuation

If the residual is empty and the slot is required, prompt the user
("What should the action say?") rather than passing an empty string.

### 5.6 Phase B (needle fallback)

Triggered when `confidence < intent_confidence_min` and
`phase_b.enabled = true`. The fallback:

1. Re-runs the resolvers from Phase A to gather top-5 person and
   thread candidates.
2. Builds a needle tool manifest: one tool per intent in scope,
   parameter descriptions enumerating the Phase A candidates.
3. Calls `needle.generate(query=grounded_query, tools=manifest)`
   where `grounded_query = f"Today is {today()}. {original_query}"`.
4. Parses the emitted `[{name, arguments}, ...]` array.
5. Validates the emitted values against the candidate enums. If
   needle hallucinates a thread/person not in the manifest, exit 4.
6. Returns the validated Resolution with `phase="B"`.

## 6. Error handling

### 6.1 Categorization

| Failure mode                       | Detection                            | Response                                      | Exit |
|------------------------------------|--------------------------------------|-----------------------------------------------|------|
| Empty query                        | `len(query.strip()) == 0`            | Print usage hint                              | 5    |
| Intent unclassified                | confidence < threshold, Phase B off  | "Could not classify intent. Try ..."           | 3    |
| Intent unclassified (Phase B fail) | needle returns empty/invalid output  | "Could not understand query."                  | 3    |
| Destructive intent                 | `intent.destructive == True`         | "ask refuses destructive ops; use CLI directly." | 6    |
| Missing required slot              | `slot.required and not resolved`     | Prompt for slot or exit                       | 5    |
| Ambiguous person/thread            | score delta < threshold              | Prompt user with candidates                   | (4 on quit) |
| Ambiguous date                     | multiple spans, no winner            | Prompt user with candidates                   | (4 on quit) |
| Underlying utility non-zero exit   | `subprocess.returncode != 0`         | Pass stderr through; no retry                 | 1    |
| Needle model not loaded            | `phase_b.enabled` but model missing  | Warn; fall through to Phase A error           | 3    |
| Log write failure                  | `OSError` writing `ask.log`          | Warn to stderr; continue (best-effort)        | (n/a) |
| Internal exception                 | unhandled in ask                     | Print traceback, link to issue                | 7    |

### 6.2 Principles

- **No silent retries.** If the underlying utility fails, surface
  the error and stop. Don't re-invoke needle or re-prompt.
- **No bypass of underlying validation.** If the resolved thread
  doesn't actually exist on disk (race condition or stale corpus),
  the underlying utility's exact-match check is the authority.
- **User declines are not failures.** Exit 2 distinct from exit 1.
- **Preview before any state change.** No CLI is invoked until the
  user confirms (or `--yes` is passed).

## 7. Testing plan and scenarios

### 7.1 Plan

- **Unit tests** for each resolver (person, thread, date, intent).
- **Integration tests** running the full pipeline against a fixture
  corpus (`tests/fixtures/people/`, `tests/fixtures/threads/`) with
  `subprocess` patched to record what would be invoked.
- **Acceptance corpus** of ~50 real queries collected from one week
  of user capture. Each tagged with: expected intent, expected slot
  values. Phase A release gate: ≥80% exact-preview matches.
- **Property tests** for date resolution: random datetime inputs
  through `dateparser` round-trip cleanly.
- **No live model tests in CI.** Needle integration tests run
  locally only, behind a `make test-needle` target.

### 7.2 Scenarios

| #  | Query                                                  | Expected outcome                                                                |
|----|--------------------------------------------------------|---------------------------------------------------------------------------------|
| 1  | `remind me to call alice friday`                       | Preview: `buffer add-action <thread> "call Alice <Last>" --due <date>`; y/N    |
| 2  | `remind alice about the launch friday`                 | Disambiguation prompt: two Alices.                                              |
| 3  | `note that the SGB meeting went well`                  | Preview: `notes new --type meeting --thread Projects/SGB --body "..."`; y/N    |
| 4  | `what's on my plate`                                   | Preview: `tasks list --status pending`; y/N                                     |
| 5  | `yesterday I talked to bern about migration`           | Date past + non-action verb → classify as `notes new`, date in body, not slot   |
| 6  | `delete the launch thread`                             | Exit 6, "ask refuses destructive ops; use `threads delete` directly."           |
| 7  | `next steps on the launch`                             | Exit 3, "Could not classify intent. Try ..."                                    |
| 8  | (empty string)                                         | Exit 5, usage hint.                                                             |
| 9  | `remind me to xyz`                                     | Missing date slot — prompt or accept None? Accept None (optional), exec.        |
| 10 | `remind me to call bern on 2026-02-30`                 | Date invalid; surface dateparser error; exit 5.                                 |
| 11 | `add buffer entry for SGB: review the doc by tuesday`  | Preview: thread = Projects/SGB, due = next Tuesday, body = "review the doc"     |
| 12 | `tell him to call back` (coreference)                  | No person resolves; exit 4 with hint that pronouns are not supported.           |
| 13 | `--yes remind me to drink water at 3pm`                | No confirmation prompt; exec immediately; log records `confirmed: true (--yes)` |
| 14 | `--dry-run` on any happy-path query                    | Preview prints, no execution, no prompt, exit 0.                                |
| 15 | Underlying `buffer` returns exit 1                     | ask exits 1; stderr from buffer is preserved.                                   |

### 7.3 Phase B–specific scenarios

| #   | Query                                                      | Expected outcome                                                                |
|-----|------------------------------------------------------------|---------------------------------------------------------------------------------|
| B1  | Phase A confidence below threshold, Phase B enabled        | Needle invoked, manifest enums populated, valid tool call returned              |
| B2  | Needle emits a thread not in the manifest enum             | Exit 4; "model emitted unknown thread"; do not exec                             |
| B3  | Needle model file missing, Phase B enabled                 | Warn, fall through to Phase A error path                                        |
| B4  | Two-action query, Phase B emits two tool calls             | v1: take first, log second as dropped, warn user. (v2 may support both.)        |

## 8. Integration and run instructions

### 8.1 File layout

`ask` ships as a new top-level entry alongside existing utilities:

    adulting/
      ask                  # new — Python entry point (executable)
      ask_lib/             # new — package
        __init__.py
        cli.py             # argparse + main
        intents.py         # intent table + classifier
        resolvers.py       # person, thread, date
        composer.py        # body composition + command assembly
        executor.py        # subprocess wrapper
        logger.py          # JSONL logger with rotation
        needle.py          # Phase B (lazy-imported)
      buffer
      tasks
      notes
      ...
      tests/
        test_resolvers.py
        test_intents.py
        test_pipeline.py
        fixtures/
          people/
          threads/

### 8.2 Dependencies

Phase A:

- Python ≥3.11 (already required elsewhere in adulting).
- `dateparser` ≥1.2 (new dependency; ~2 MB installed).

Phase B (optional, lazy-imported):

- `needle` Python package from `~/projects/needle` (editable install
  or wheel).
- JAX (transitive via needle).
- A needle model checkpoint at `phase_b.model_path`.

### 8.3 Install

    cd ~/projects/adulting
    pip install dateparser
    chmod +x ask

For Phase B (deferred):

    cd ~/projects/needle && pip install -e .
    mkdir -p ~/.cache/needle && \
      cp -r ~/projects/needle/checkpoints/26m-int8 ~/.cache/needle/

### 8.4 First-run setup

`ask` creates `~/.adulting/config/ask.toml` from a template on first
invocation if missing. The template has `phase_b.enabled = false`,
which means a fresh install runs Phase A only.

### 8.5 Enabling Phase B

1. Install needle (above).
2. Edit `~/.adulting/config/ask.toml`: set `phase_b.enabled = true`
   and `phase_b.model_path` to the checkpoint directory.
3. Run `adulting ask --dry-run "test query"` to confirm the model
   loads without error.

### 8.6 Integration with existing utilities

- `ask` invokes existing utilities via subprocess. No new function
  exports or library API needed in `buffer`, `tasks`, `notes`.
- `ask` does require the following adulting-side changes, tracked
  separately from this PRD:
  - `--json` output on `threads list`, `threads show`, `people list`,
    `people show` (already partial — extend remaining commands).
  - Non-interactive variants on subcommands `ask` should reach (e.g.
    `notes new --type ... --thread ... --topic ... --body ...`).
  - Resolve-by-description subcommands on `tasks` (e.g.
    `tasks done-matching <text>`, `tasks set-due-matching <text>
    <date>`).
- These changes are preconditions per-utility, not blockers for
  shipping `ask` with `buffer` support only.

### 8.7 Migration

No existing users; no migration concerns. The CHANGELOG entry for the
first `ask` release should note Phase A behavior, the new
`dateparser` dependency, and that Phase B is disabled by default.

### 8.8 Rollout

| Stage      | Scope                      | Gate                                                                   |
|------------|----------------------------|------------------------------------------------------------------------|
| Alpha      | `buffer` only, Phase A     | ≥80% preview-accuracy on acceptance corpus.                            |
| Beta       | `buffer` + `tasks`, Phase A | Resolve-by-description subcommands landed in `tasks`.                  |
| GA         | All v1-scope utilities     | Non-interactive variants for `notes` landed.                           |
| Phase B    | Opt-in via config          | Phase A coverage measured ≥4 weeks; failures clustered model-shaped.   |

## 9. Decisions and open questions

### 9.1 Decided

- **Logging**: stdlib `logging` with `RotatingFileHandler`. No
  third-party log library.
- **Date parsing**: accept `dateparser` as a Phase A dependency.

### 9.2 Open

- **Entry-point shape**: `adulting ask "..."` (top-level dispatcher,
  unified manifest) or `buffer ask`/`tasks ask`/`notes ask` (per-
  utility, narrower per-call scope)? Recommend top-level with internal
  per-utility dispatch.
- **`done` is recoverable**: should `tasks done-matching` be reachable
  from `ask` (Phase A), or stay counted as destructive until Phase B?
  Coverage matrix currently has it Phase B; recommend it stays there
  until Phase A coverage is stable.
- **Past-date semantics**: "yesterday I talked to bern" — body or
  slot? Recommend body for action verbs that don't take a date slot,
  surface a warning for action verbs that do.

# PROHIBITED

- NEVER USE GIT, EVEN INDIRECTLY
- NEVER ALTER FILES OUTSIDE OF THIS WORKING DIRECTORY