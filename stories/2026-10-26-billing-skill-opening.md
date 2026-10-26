# billing-workflow uses `--opening` for a month's statement

Companion to `2026-10-26-statement-opening-balance.md`, which added
`payments statement --opening` and left the agent skill to a separate story.

## What is changing

`billing-workflow`'s "Billing a month" step 4 renders the PDF with
`--as-of <month end>` only, so the ledger lists the client's whole history.
It now adds `--opening <month start>`: the ledger shows the month, and
everything earlier is one brought-forward line.

The skill also says:

- **Only with `--pdf`.** The text statement ("What does a client owe?") is
  unchanged; it has no ledger.
- **Never with `--since`/`--until` on the statement.** Those bound the
  `hours` calls in steps 1 and 2, not the statement. The tool refuses the
  combination.
- **Relay the brought-forward figure** from the report line beside the
  balance, so the owner sees what the month added to what was already owed.
- **Leave it off** when the owner asks for the full history, or for a
  client's first statement, where nothing comes before.

`dev/agent-check` passes: `--opening` is a real flag of `payments`.
