---
name: buffer-workflow
description: Logs a non-action inbox capture — an observation, status update, half-formed thought, or reference to another vault entry — to the buffer staging queue. Activate when an inbox message is NOT an action item, e.g. "met Jordan for a hike, talked Northwind succession". For action items use task-workflow instead; for a number he tracks ("weighed 82.4", "had a drink") use stats-workflow.
---

# Skill: buffer workflow

For anything the owner wants recorded that isn't an action item.

The buffer is a staging queue. Entries accumulate, `buffer tend`
regroups them by thread and date, and `buffer flush` writes them
into per-thread daily logs. You only ever append — the `buffer` tool
description covers the subcommands.

Use `add-text` for an observation, `add-ref` when he links one vault
entry to another. **Never call `add-action` here** — action items
belong to `task-workflow`, which drives it via `tasks add`.

**A tracked number is not an observation.** Check the capture against
`stats list`. "Weighed 82.4" or "had a drink last night" that matches a
declared stat is a `stats log`, following `stats-workflow` — not an
`add-text`. A message with both a number and a remark ("weighed 82.4,
feeling heavy after the weekend") is two entries, proposed together.

A number with no declared stat stays an `add-text`, in his words. Say
there is no stat for it and offer to declare one; never declare it as
part of the capture.

## Steps

1. **Resolve the thread** against `threads list`. If the message
   doesn't clearly belong to one, ask. Don't guess.
2. **Shape the body** per the rules below. If he is describing an
   earlier day, pass `--date` so it files under that day's log.
3. **Propose**, ending in `OK?`.
4. **On confirm**, append it. Reply `Logged.`

You do not flush. The owner flushes when they're ready, or the daily job
does.

## Rules

**Preserve his voice.** Don't fix grammar, expand abbreviations or
improve the phrasing. Capture what he said; only shape the
references.

**Wikilink people in the body.** Resolve each name against
`people list` and write it `[[people/Jordan Blake]]`. If a name
doesn't resolve, ask whether to create the person or drop the link —
never invent one.

**Leave the thread out of the body.** It's a separate argument
already; don't also write `[[Processes/Northwind]]` into the text.

**One entry per thought.** A message carrying three observations
across two threads becomes three entries, proposed together and
confirmed once.

## Examples

> Met Jordan for a hike, talked Northwind succession

→ thread `Processes/Northwind`, body
`Hike with [[people/Jordan Blake]] — talked succession planning.`

> Fabrikam DORA: Ivan is helping us scope a metrics pipeline

→ thread `Projects/Fabrikam DORA`, body
`[[people/Ivan Petrov]] is helping scope a DORA metrics pipeline.`
