---
schema: payments_file
scope: file
directory: payments
filename: ^[^.]+\.md$
---

# Payments file

Money received against one thread. One file per thread, at
`~/vault/payments/{Projects,Processes,Topics}/<Thread>.md` — mirroring the
`threads/` layout, the same way `hours/` does.

The body carries exactly one ` ```adulting-payments ` fenced block containing
JSON. Unlike `hours`, there is no external plugin to be compatible with, so the
fence is our own; the structure matches `hours` so both are readable and
greppable in the same way. Written and maintained by the `payments` CLI.

## Fields

| name     | required | type   | constraint       |
|----------|----------|--------|------------------|
| thread   | yes      | string |                  |
| currency | yes      | string | regex=^[A-Z]{3}$ |

## Body

| pattern                   | meaning                                       |
|---------------------------|-----------------------------------------------|
| ` ```adulting-payments `  | opens the payments block — exactly one per file |
| JSON `{"payments": [...]}`| the block's sole content; must parse           |

### Payment object

| name     | required | type   | constraint                                  |
|----------|----------|--------|---------------------------------------------|
| id       | yes      | string | 8 hex chars, unique across the whole vault  |
| received | yes      | string | ISO 8601 UTC, `YYYY-MM-DDTHH:MM:SS.mmmZ`    |
| amount   | yes      | number | must be > 0                                 |
| currency | yes      | string | ISO 4217, `^[A-Z]{3}$`                      |
| account  | no       | string | which account the money landed in           |
| note     | no       | string | free text                                   |

## Notes

- `thread` must be a wikilink to `Projects/X`, `Processes/X`, or `Topics/X`, and
  must resolve. `lint` enforces resolution for any scalar `thread` field, so the
  constraint cell is deliberately empty.
- `id` shares one namespace with `hours` entry ids — an id is never reused
  across the two tools, and `lint` checks uniqueness across both.
- `amount` is stored as a JSON number but is only ever *computed* with
  `decimal.Decimal`. These figures get reconciled against invoices, so float
  drift is not acceptable.
- `received` is the date the money landed, which is the one that matters for a
  statement of account. The legacy CSV also carried a separate "record date";
  it was not worth keeping.
- Amounts must be positive. A refund or write-off is not a negative payment —
  if that need arises it wants its own record type, not a sign flip.
- JSON is pretty-printed at `indent=2`, so appends produce readable, mergeable
  git diffs.
