---
name: create-person
description: Creates a new person entry for someone referenced in a task or buffer entry who doesn't yet appear in the people roster. Activate when adding a task or buffer line whose actor or mentioned person can't be resolved against `people list`, and a new person entry needs creating as part of the plan.
---

# Skill: create person entry

Triggered when a task or buffer entry references someone who isn't
in `people list`. This is never a standalone job — it is always one
step of a larger plan, so fold it into that plan's single proposal.

`people new` needs a full name and a category. It sets `started`
itself.

## Infer before asking

**Category** — from the context that raised the name. A person
appearing on a work thread is `professional`. Family and friends are
`personal`. Volunteer-organisation contacts are `voluntary`.

**Surname** — if Riaz gave only a first name, look for the full name
in the thread or in earlier messages. `threads show` often carries
it.

Don't invent a surname. If nothing gives you one, write
`(needs surname)` in the proposal and let Riaz fill it in.

## Propose as one plan

Never confirm the person separately from the thing that needed them:

```
Going to:
1. Create person Bern Sellmeyer (professional)
2. tasks add Processes/SGB "(Bern Sellmeyer) Send Riaz the management accounts" --due 2026-05-15

OK?
```

On confirm, create the person, then continue straight into the rest
of the plan. It was all confirmed once — don't ask again.

## Boundary

Person entries are created only through `people`. You can read vault
files directly, but you cannot write them — and a hand-written
person file would not satisfy the schema `lint` enforces.
