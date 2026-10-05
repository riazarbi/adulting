# commit-workflow reads the thread from the path

Companion to `2026-10-05-thread-scoped-vault.md`, which moves notes, logs,
hours and payments into thread folders. This story is the agent-skill side
of that move. It must land with the CLI change: the skill ships in the image,
and the old version describes a layout that no longer exists.

## What changes

The `commit-workflow` skill builds the commit body's **Activity** section
from the files `commit review` lists. It used to need a table of three
rules to find each file's thread:

| Source | Thread from |
|--------|-------------|
| `logs/<Kind>/<Name>/<date>.md` | the path |
| `notes/<timestamp>.md` | `threads:` frontmatter |
| `hours/<Kind>/<Thread>.md` | the path |

Now every one of those files lives in `threads/<Kind>/<Name>/`, so there is
one rule: the two folders after `threads/` are the thread. The table keeps
only where the date and the summary come from.

A note that belongs to several threads is filed under the first. The skill
still lists it under every thread its `threads:` frontmatter names, as
before; only the place to find the first thread has moved.

## What does not change

Everything else in the skill: the subject line, grouping and ordering,
hours files as activity, the Vault changes section, and passing the body
as one argument.

## Verification

- `dev/agent-check` passes. It now also rejects any vault path in the old
  layout (`logs/<Kind>/…`, `notes/<stem>.md`, `hours/<Kind>/…`), which is
  what flagged the three stale rows here.
- No other skill names a vault path in the old layout (same check).
