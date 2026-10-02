---
name: recall
description: Answers questions about what is in the vault — what happened on a thread, what was decided at a meeting, where something was mentioned, where attention has been going. Activate when Riaz asks a question whose answer lives in his notes and logs rather than in his task list. For "what should I do next" use task-workflow; for hours and money use time-workflow and billing-workflow.
---

# Skill: recall

Questions about what happened. `search` finds the documents; `read_file`
opens the ones you need.

Read-only throughout. No confirm step — answer the question.

## Pick the subcommand from the question

| He asks | You call |
|---|---|
| "the last SGB meeting", "our meetings about X" | `search notes --thread ... --type Meeting` |
| "what happened on SGB recently" | `search logs --thread ...` |
| "where did I mention asbestos" | `search notes --text ...`, then `search logs --text ...` |
| "what have I been busy with", "most active threads" | `search activity` |
| "where are we with SGB", "everything on SGB" | `search overview SGB` |
| "what happened today", "did that get logged" | `search stream --today` |
| "what's happened on SGB lately" | `search stream --thread SGB` |

`--thread` takes a bare name. `SGB` resolves on its own — don't call
`threads list` first.

`search stream` is the one to reach for when he is checking that something
landed. It merges every dated record — notes, log lines, tasks opened and
closed, hours, payments — into one chronology, and marks anything still
sitting in the buffer as `pending`.

## Search, then read

`search` returns pointers, never bodies. To answer a question about
*content* you must open the file:

1. `search notes --thread SGB --type Meeting --limit 1`
2. `read_file` the path it returned, copied exactly — it is absolute
   and already correct
3. Answer from what you read

If a read fails, do not start guessing at path prefixes. Re-run the
search with `--json` to get the path cleanly, and if it still fails
say so rather than hunting the filesystem.

Never answer a content question from the search line alone. A topic is a
title, not a summary — "Camps Bay Primary School Parents Meeting" tells you
nothing about what was decided.

## Read one, not ten

Open the smallest number of files that answers the question, usually one.
If several look relevant, say which you read and offer the rest rather than
opening them all — a meeting note is long and his context is finite.

If the top hit turns out to be the wrong document, say so and try the next
one. Don't silently answer from a file that didn't actually cover it.

## Dates are event dates

`search` orders by when something *happened*, not when the note was
written. An agenda drafted days before its meeting sorts to the meeting
date. The newest result really is the most recent meeting.

## Answering well

Meeting notes carry `AGREED:`, `RESOLVED:` and `!:` lines. For "what was
decided" or "key takeaways", lead with those, then the surrounding context.

Give him the answer, not a research report. Name the source note once so he
can open it himself, format per the role prompt's mobile rules, and stop.

## When nothing matches

Say so plainly and say what you searched. An empty result is a real
answer — it usually means the wording differs, so offer a broader term
rather than asserting the thing never happened.
