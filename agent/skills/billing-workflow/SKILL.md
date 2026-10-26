---
name: billing-workflow
description: Money owed and money received on a consulting thread — recording a payment, rendering a statement of account, checking what's outstanding, and preparing a month's invoice from logged hours. Activate when the owner reports a receipt ("Northwind paid 15k"), asks what a client owes, or wants to bill a month. For logging time worked, use time-workflow.
---

# Skill: billing workflow

For money. The `payments` and `hours` tool descriptions carry the
subcommands and flags; this is the sequence and the judgement.

## Recording a payment

**Always pass the thread** — `payments log` without one exits with
an argparse error and records nothing.

Amount is positive, always. A refund is not a negative payment; if
the owner describes money going back out, say the tool can't express it
rather than inverting the sign.

Capture `-a` (which account it landed in) and `-n` (a short note,
usually which invoice it settles) whenever he mentions them — they
are what makes a statement readable months later. Pass `-d` if the
money landed on an earlier day than today.

Propose, log on confirm, then run `payments statement --thread ...`
and relay the new outstanding balance. He almost always wants to
know what's left.

## Correcting a payment

`payments edit` fixes an amount, date, account or note. `payments rm`
is blocked for you — a receipt that was recorded wrongly gets
corrected, never erased. If a payment must actually be removed, say
so and leave it for the owner.

## What does a client owe?

`payments statement --thread <Kind/Name>` — billed against received,
with aging. `--as-of` sets the statement date if he wants the
position at a past date rather than today.

Read-only. No confirm.

## Billing a month

Four steps. Propose them together; the first three are read-only.

1. `hours report` for the thread, bounded by `--since` and `--until`
   on the month. Gives the totals per currency.
2. `hours list` over the same range. These entry descriptions are
   the invoice line items.
3. Read those descriptions critically. Any that would embarrass him
   in front of a client, fix with `hours edit --description` — this
   is the one write in the sequence, so flag it in the proposal.
4. `payments statement --thread ... --as-of <month end>` to render
   the statement. Add `--pdf <path>` when he wants a file to send,
   and with it `--opening <month start>`: the ledger then shows the
   month, and everything earlier is one "Balance brought forward"
   line. The balance due is the same either way.

`--opening` is for the PDF only, and never goes with `--since` or
`--until` on the statement; those bound the `hours` calls in steps
1 and 2. Leave it off when he asks for the full history, or for a
client's first statement. When it is on, relay the brought-forward
figure from the output beside the balance, so he sees what the month
added to what was already owed.

`--pdf` requires `--thread`, and the thread needs its `client_*`
fields filled in. If the render fails for a missing `client_name`,
say so plainly — it is fixed on the thread, not here.

## Before a thread can be billed

A billable thread needs `currency` and `rate` set on it, which is
what `hours` reads as defaults. If the owner is starting new client work
and the thread doesn't exist, creating it is a separate intent —
propose it, don't fold it silently into a logging request.

## Never state a number you didn't read

Balances, totals and aging come from the tool's actual output.
Never estimate what a client owes, and never add two currencies
into a single figure.
