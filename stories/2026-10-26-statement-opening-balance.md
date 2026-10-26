# A statement can open on a date, with the earlier account brought forward

## What is changing

`payments statement --pdf` prints every charge and payment the thread has
ever had. A client who has been billed for two years gets a ledger two years
long, when what they want is last month's activity and what they owed going
in.

A new flag, `--opening YYYY-MM-DD`, sets the first day the ledger shows.
Everything before it, charges and payments alike, collapses into one
**Balance brought forward** line at the top:

    payments statement --thread Northwind --opening 2026-08-01 --as-of 2026-08-31 --pdf aug.pdf

| Date | Description | Hours | Rate | Charge | Payment | Balance |
|---|---|--:|--:|--:|--:|--:|
| 2026-07-31 | Balance brought forward | | | | | 12,400.00 |
| 2026-08-04 | Draft scope | 3.00 | 1,200.00 | 3,600.00 | | 16,000.00 |
| 2026-08-15 | Payment received — Current | | | | 12,400.00 | 3,600.00 |
| | **Balance due** | **3.00** | | **3,600.00** | **12,400.00** | **3,600.00** |

## Two kinds of date

The flags do different jobs, and this one is the first of its kind:

| Flag | Kind | Effect on the balance |
|---|---|---|
| `--as-of D` | input cut-off | Records after D do not exist. The balance is the account as it stood on D. |
| `--since` / `--until` | input window | Records outside the window do not exist. The balance is the window's net, not the account's. |
| `--opening D` | view compaction | Every record up to `--as-of` still counts. Only how the ledger *prints* them changes. The balance is the same as without the flag. |

So `--opening` never changes the balance due or the aging. With and without
it, a statement asks the client for the same money.

## Behaviour

- **Boundary.** Records dated on `--opening` are shown. The brought-forward
  line covers everything strictly before it and is dated the day before.
- **The line is always printed** when `--opening` is given, at `0.00` if
  nothing came before. A reader can then tell "nothing owed going in" from
  "the flag was ignored".
- **Summary** becomes: Opening balance, Hours billed, Charges, Payments
  received, Balance due. Hours, charges and payments are the period's. The
  identity `opening + charges − payments = balance due` is asserted
  alongside the existing checks.
- **Totals row** sums the period's hours, charges and payments; its balance
  is the closing balance, as today.
- **Aging** is unchanged: it ages the whole unpaid balance, including what
  was brought forward. It still sums to the balance due.
- **A quiet period still renders.** No activity on or after `--opening` but
  a non-zero brought-forward balance is a valid statement, a reminder. Only
  zero brought forward *and* no lines gives today's "nothing to state".
- **Errors**, in the existing `V.die` style:
  - `--opening` after `--as-of`: `--opening 2026-09-01 is after --as-of 2026-08-31`.
  - `--opening` without `--pdf`, or with `--since`/`--until`: see decisions 2 and 3.

## Where it lands

`statement.build` takes an optional `opening` date and splits the entries
and payments it already has. `running` starts from the brought-forward
balance instead of zero. `statement_pdf.markdown` prints the extra line and
summary row. `payments.py` adds the flag and the checks. README's *Statement
of account* section, the help string, and so `MANUAL.md` and
`dev/tools/payments.json` via `dev/ci generate`.

Tests: balance and aging equal with and without `--opening`; boundary day
shown; zero brought forward printed; quiet period renders; opening after
as-of refused.

Agent skills are out of scope here; if the billing skill should offer
`--opening`, that is a separate story.

## Decisions

Agreed 2026-10-26.

1. **Name:** `--opening`. `--from` pairs with `--to` and reads like
   `--since`, which truncates; *opening balance* is the accounting term for
   the start of a statement period.
2. **Text view:** `--opening` requires `--pdf`, as `--pdf` requires
   `--thread`: `--opening needs --pdf; only the PDF has a ledger to compact`.
3. **With `--since`/`--until`:** refused, since a brought-forward line after
   `--since` would be a partial balance carrying the name of a whole one:
   `--opening cannot be combined with --since or --until; --as-of sets the end`.
