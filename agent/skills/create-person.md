# Skill: create person file

Triggered when an action item or buffer entry references a person
who doesn't yet have a `~/vault/people/<Full Name>.md` file.
Capture the salient metadata, propose the compound plan, then create
on confirm.

## Required fields

| Field      | Source                                                       |
|------------|--------------------------------------------------------------|
| Full name  | Used as filename and `# <Full Name>` heading                 |
| Category   | `personal`, `professional`, or `voluntary`                   |

`started` is set automatically by `people new` (today's date).

## Gathering protocol

1. **Infer first.** From the triggering context (task description,
   thread the task is on, prior messages):
   - **Category** — most assignees from task captures are
     `professional` (they appear in a work-thread context). Family
     / friends → `personal`. Volunteer-org contacts → `voluntary`.
   - **Surname** — if only a first name, look at the surrounding
     context (the thread, prior tasks) for a full name.

2. **Bundle missing fields into the proposal.** State your inferences
   in the compound proposal; let Riaz correct via the confirm step.
   Example for a task-add trigger:

   ```
   Going to:
   1. Create person Bern Sellmeyer (professional)
   2. tasks add Processes/SGB "(Bern Sellmeyer) Send Riaz the management accounts" --due 2026-05-15

   OK?
   ```

3. **Don't guess at surnames.** If neither the message nor any
   adjacent thread file gives one, surface the gap in the proposal:
   `(needs surname)` instead of inventing. Riaz fills it in during
   confirm.

## Creation invocation

Use `people new` with flags so it runs non-interactively:

```
people ["new", "--name", "<Full Name>", "--category", "<personal|professional|voluntary>"]
```

This emits:

```markdown
---
status: open
category: <category>
started: <today YYYY-MM-DD>
---

# <Full Name>
```

If Riaz hinted at a periodic check-in cadence ("call her quarterly",
"monthly catch-ups"), `people new` doesn't currently take a cadence
flag. Add the cadence by hand-editing the file post-creation, or
defer (most created-via-task people don't need one).

## After creation

The person file is one step in a compound plan (typically
create → tasks add). Continue with the triggering action — the
whole plan was confirmed once; don't re-confirm.
