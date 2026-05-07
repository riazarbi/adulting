# External integrations

This codebase relies on three external applications. Each section
documents what we use it for, the configuration the integration
needs, and the steps a fresh install requires.

## Taskwarrior (internal backend)

Taskwarrior is **not user-facing in this system**. It's the backend that
stores task state; the `tasks` script is the only sanctioned interface
to it. Treat `task` (the binary) the way you'd treat a database driver:
nobody calls it directly.

### What this means in practice

- **Don't run `task add` / `task <id> modify` / `task <id> done`** by
  hand or from any agent tool. Use the `tasks` subcommands:

  | Operation                        | Use                                          |
  |----------------------------------|----------------------------------------------|
  | Capture a new action             | `tasks add <thread> "<text>"` (writes buffer) |
  | Mark complete                    | `tasks done <uuid>`                          |
  | Edit description                 | `tasks set-description <uuid> "<text>"`      |
  | Reassign person                  | `tasks set-assignee <uuid> <person>`         |
  | Set due / scheduled              | `tasks set-due <uuid> YYYY-MM-DD` etc.       |
  | Set priority                     | `tasks set-priority <uuid> H\|M\|L`          |
  | Add / remove dependency          | `tasks add-depends`, `tasks rm-depends`      |
  | List / next / show               | `tasks list`, `tasks next`, `tasks show`     |

- **No new tasks are created by `tasks add` directly.** It buffers a
  conformant ACTION line; tasks are created when buffer entries flush
  to notes and the regular `tasks` ingest pre-pass picks up the ACTION.
  This keeps a single creation path: ACTION-line-in-a-note → ingest.

- The only programmatic access to taskwarrior state for callers
  (humans, scripts, agent tools) is via `tasks` and the markdown source
  notes themselves. Read access via `task list` is fine if you want to
  query interactively; for automation, use `tasks list` so you get
  UUID prefixes in the output.

### Why this matters

`tasks` enforces format and validation at write time:
- Threads must resolve to a real `threads/<Kind>/<Name>.md` file.
- Assignees must resolve to a real `people/<Name>.md` file.
- Dates must be `YYYY-MM-DD`. Relative terms like "tomorrow" / "friday"
  are rejected so the agent can't fudge time arithmetic.
- Priority must be `H`, `M`, or `L`.

Bypassing `tasks` to call `task` directly skips these gates and creates
the source-vs-tw drift this whole architecture is designed to prevent.
The `cmd_sync` source-wins policy specifically assumes nobody else is
mutating task descriptions.

### Required UDA

The bridge needs one taskwarrior UDA configured:

```
uda.source.type=string
uda.source.label=Source note
```

Every task created by ingest gets `source:<note_stem>` populated. The
bridge calls `ensure_uda()` on every invocation, so **no manual setup
is required** — running `tasks` once configures it.

### Default locations

- Data: `~/.task/`
- Config: `~/.taskrc`

Both can be relocated via `TASKDATA` / `TASKRC`. This codebase doesn't
relocate them today — vendoring the taskwarrior binary inside the vault
is a future option that would point these at vault-internal paths.

### User-editable

The user's own `.taskrc` content (themes, custom reports, contexts,
hooks, other UDAs) is none of this codebase's business. Only the
`source` UDA is required.

---

## Obsidian

Used as the markdown editor and vault browser for `~/.adulting/`. Notes,
threads, and people files are written/read as plain markdown; Obsidian
provides Properties UI, backlinks, graph view, and Bases queries against
the YAML frontmatter.

### Required `~/.adulting/.obsidian/app.json`

```json
{
  "newLinkFormat": "absolute",
  "useMarkdownLinks": false
}
```

- **`newLinkFormat: "absolute"`** — Obsidian's rename refactor and
  `[[ ]]` autocomplete produce path-qualified wikilinks
  (`[[Projects/Foo]]`), which is what the note schema's `thread:` regex
  expects. With the default `"shortest"`, renames produce bare `[[Foo]]`
  and `lint` rejects them.
- **`useMarkdownLinks: false`** — wikilinks rather than markdown links.
  Our parsers and schemas assume `[[wikilink]]` form throughout.

Set both via Obsidian: **Settings → Files & Links → New link format → Absolute path in vault** and **Use [[Wikilinks]] → on**. Or write the JSON directly.

### Recommended `~/.adulting/.obsidian/types.json`

```json
{
  "types": {
    "started": "date",
    "ended": "date",
    "people": "multitext",
    "timestamp": "date",
    "aliases": "aliases",
    "cssclasses": "multitext",
    "tags": "tags"
  }
}
```

Sets the right input widget for each frontmatter field in the
Properties panel. Obsidian doesn't have a native enum / select type, so
`status` / `kind` / `category` stay as text — their Properties dropdown
lists existing values found in the vault automatically, which is
adequate.

### Required core plugins

These ship enabled by default in Obsidian; named here for clarity:

- **Properties** — frontmatter UI in the editor
- **Backlinks** — graph navigation; the per-thread / per-person view of
  which notes link to a file
- **File Explorer** — directory tree

### Recommended core plugins

- **Graph** — visualises the wikilink graph; useful for spotting orphan
  notes / unconnected people
- **Bases** — query frontmatter properties (e.g. "all `kind: project`
  threads with `status: open`")
- **Daily Notes** — enabled in your install but no script integration
  yet

---

## Pandoc + xelatex

Used by `notes --pdf` / `--minutes` / `--agenda` to render PDFs of
meeting notes, agendas, and arbitrary notes. The renderer scripts pass
all options inline; no per-user config required beyond having the
binaries on `PATH`.

### Required

- `pandoc` (any recent version)
- A LaTeX engine providing `xelatex`. On macOS, MacTeX (complete) or
  BasicTeX (smaller, may need to install additional LaTeX packages on
  demand). On Linux, TeX Live.

### Pandoc invocation

The renderers use `--from=markdown+lists_without_preceding_blankline`,
which gives Obsidian/CommonMark-style list rendering (a list right
after a paragraph, no blank line required) while still supporting
pandoc's default extensions including `raw_tex` (for `\newpage`) and
`yaml_metadata_block`. No alternative pandoc-flavour or extension list
is supported by the rendering scripts.

---

## Anything else?

If you find yourself wanting to integrate another external tool, add
it to this document. The CHANGELOG is for changes to this codebase's
source; INTEGRATIONS.md is the stable reference for what external apps
the codebase expects and how to configure them.
