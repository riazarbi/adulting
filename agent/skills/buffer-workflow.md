# Skill: buffer workflow

Loaded when an inbox message is a non-action capture — observation,
status update, half-formed thought, info to remember, reference to a
file. Anything that's *not* an action item.

The buffer is the staging area at `~/vault/buffer.md`. Entries
land as one structured line each, get grouped on `buffer tend` by
`(thread, date)`, and flush into per-thread per-day Log files at
`logs/<Kind>/<Name>/<date>.md`.

## Three line types

- **TEXT** — a free-text observation. The most common.
  `buffer ["add-text", "<thread>", "<body>"]`
- **REF** — a reference to another file in the vault (a note, thread,
  person). Useful when Riaz says "this links to that" or when an
  existing note becomes relevant to a new thread.
  `buffer ["add-ref", "<thread>", "<target>", "<summary>"]`
- **ACTION** — only via the task workflow (`tasks add`). Don't call
  `buffer add-action` directly from this skill; route action items to
  `task-workflow`.

## Steps

1. **Identify the thread.** Resolve abbreviations against
   `~/vault/threads/{Projects,Processes,Topics}/`. If the message
   doesn't clearly belong to a thread, ask which one — don't guess.
2. **Rewrite the message minimally** per the rules below.
3. **Propose**:
   ```
   Going to log to <thread>:

     <proposed body>

   OK?
   ```
4. On confirm: invoke `buffer ["add-text", "<thread>", "<body>"]`.
   Reply: `Logged.`

## Rules

- **Thread is a positional arg, not embedded in the body.** Don't
  include `[[<thread>]]` in the body text — it's already structural.
- **Names inside the body still get wikilinked.** Use
  `[[people/<First> <Last>]]` (lowercase `people/`) for people. Body
  is plain prose otherwise.
- **Preserve voice.** Don't fix grammar, expand abbreviations, or
  "improve" the entry. Capture his wording; just shape references.
- **One write per confirmed entry.** Multi-thought messages become
  multiple entries (one per `(thread, body)` pair), proposed and
  confirmed together.
- **Don't read the buffer to dedupe or reorganize** — `buffer tend`
  handles that automatically.
- **Don't invent thread paths or person wikilinks** for files that
  don't exist. If a referenced thread or person isn't in the vault,
  follow the no-match procedure in the role prompt — ask Riaz which
  existing one to use. Creating a new thread or person file is a
  separate intent that requires an explicit request; never bundle
  it into a buffer log.

## Examples

- "Met Bern for a hike, talked SGB succession" →
  `buffer ["add-text", "Processes/SGB", "Hike with [[people/Bern Sellmeyer]] — talked succession planning."]`
- "AXA DORA: Rhyd is helping us scope a metrics pipeline" →
  `buffer ["add-text", "Projects/AXA DORA", "[[people/Rhyd Lewis]] is helping scope a DORA metrics pipeline."]`
  (assumes Rhyd Lewis.md exists; if not, see `create-person`)
