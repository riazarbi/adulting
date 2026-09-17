# Wellness check-ins, and intentions measured against outcomes

## What is being added

Three check-ins a day, seven days a week. The morning asks what you intend
to do; the midday and evening ask what you actually did, how you are, and
whether the intention held.

Captured each time: energy, how relaxed you feel, steps, and — at midday and
evening — whether you did what you set out to do. Exercise is not captured
here; it is time spent and already belongs in `hours`.

## Do not remove the context clearing

The proposal was to keep the day's conversation so the midday check-in can
see the morning's intentions. Measured, that is the expensive way to do it
and the fragile one.

- The always-on prompt is **~7,300 tokens** before a word is exchanged.
- A five-message exchange logged **12,598 prompt tokens** — roughly **1,000
  tokens per message**.
- Three check-ins plus ad-hoc traffic is 25–40 messages, so **32,000–47,000
  tokens** by evening, on a 4B model. When this model degrades it degrades
  badly: one confused afternoon produced 57 tool calls and a wrong answer.

It is also fragile in a way already demonstrated: a single malformed
assistant message poisoned the context and every subsequent turn failed with
a 400 until the file was deleted. A day's intentions living only in that
directory would have gone with it.

**Intentions belong in the vault, not in the conversation.** The morning
check-in writes them as a record; the midday check-in reads them back with
one tool call. That survives a context wipe, a crash, and a restart — and it
is the same durability argument the whole vault rests on. It also gives the
comparison for free: the record is already structured, so "did I do what I
intended" is a query rather than a memory.

Keep the clear, move it to **02:00 daily** — well clear of a 07:30 morning
check-in, and the accumulated day is discarded once rather than mid-morning.

## The store

A new `checkins/<YYYY>-<MM>.md`, one file per month, JSON inside an
```adulting-checkins fence — the shape `hours` and `payments` already use,
for the same reason: many small dated records that must be queryable.

Not notes: three a day is ~1100 files a year against the vault's current
110, and it would swamp `search notes`. Not log lines: free text cannot be
evaluated over time, which is the point of the exercise.

```json
{
  "id": "3f9a2c81",
  "at": "2026-09-12T07:30:00.000Z",
  "period": "morning",
  "energy": "high",
  "relaxed": "medium",
  "steps": 4200,
  "intent": ["Finish the DORA spec", "Call Bern about the accounts"],
  "intent_met": "partly",
  "note": "slept badly, starting slow"
}
```

Only `id`, `at` and `period` are required. A sparse check-in is valid data —
an empty answer is an answer.

## `checkin` CLI

    checkin log --period morning|midday|evening
                [--energy L] [--relaxed L] [--steps N]
                [--intent TEXT ...] [--intent-met yes|partly|no] [--note TEXT]
    checkin list [--since D] [--until D] [--period P] [--json]
    checkin today                      what has been captured today
    checkin intent                     the most recent unmet intentions
    checkin show ID / edit ID / rm ID
    checkin report [--since D] [--until D]

`checkin intent` is what makes the comparison work: the midday check-in
calls it, gets the morning's intentions, and asks against them.

Like every other record-writing tool, `log` drops a `REF:` into the buffer
against `Processes/Wellness`, filed under the day, so the check-in shows up
in the log and therefore in `search stream`.

## The three jobs, seven days a week

    02:00  clear-context     (moved from 03:05 and 13:05)
    07:30  morning-checkin   intentions, energy, relaxed, sleep
    13:10  midday-checkin    activity so far, intent check, energy, steps
    17:30  evening-checkin   activity since midday, intent check, steps
    21:00  nightly-commit    unchanged

Midday and evening keep `activity-capture` for the work itself — hours and
log lines — and add the wellness questions. The morning is new and does not
touch `activity-capture` at all.

## Open questions

1. **How should energy and relaxation be recorded?** The earlier `tend`
   system prompt said "never introduce numeric ratings, scores, or 1-10
   scales", and that instinct is probably right: a number invites false
   precision about a feeling. `low` / `medium` / `high` is still countable
   over time. But a 3-point scale is coarse, and 5 points would show more
   trend. Which?

2. **Should `steps` be asked at every check-in or only the evening?** Asking
   three times a day gets a partial number twice. Asking once gets the whole
   day but loses the shape of it.

3. **What does the morning ask beyond intentions?** Sleep is the strongest
   confounder for everything else — a low-meaning day and a low-sleep day
   look identical from the inside — but it is another question in a ritual
   that has to stay short to survive.

4. **Should a missed check-in be recorded as missed?** A gap in the data is
   ambiguous: away, busy, or unwell. An explicit "no check-in" would make
   the series honest, but nothing can write it except a job that notices the
   absence.
