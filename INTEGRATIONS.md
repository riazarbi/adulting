# External integrations

This codebase relies on three external applications. Each section
documents what we use it for, the configuration the integration
needs, and the steps a fresh install requires.

## Taskwarrior

Used as the canonical task store. The `tasks` script ingests `ACTION:`
lines from notes, syncs description and status changes bidirectionally,
and the `task` CLI is the primary surface for querying / modifying
tasks (`task list`, `task next`, `task <id> done`, etc.).

### Required configuration

In `~/.taskrc`:

```
uda.source.type=string
uda.source.label=Source note
```

Every task created by the `tasks` bridge gets `source:<note_stem>`
populated, anchoring it to the markdown note that produced it. The
bridge calls `ensure_uda()` on every invocation; if the UDA is missing
it sets both keys via `task rc.confirmation:no config ...`. **No manual
setup is required for a fresh install** — running `tasks` once is
enough.

### Default locations

- Data: `~/.task/`
- Config: `~/.taskrc`

Both can be relocated via `TASKDATA` / `TASKRC` env vars. This codebase
does **not** relocate them — taskwarrior state lives outside the vault
on purpose, so other taskwarrior tooling (mobile sync, `tasksh`, etc.)
keeps working unchanged.

### User-editable

The user's own `.taskrc` content (themes, aliases, custom reports,
contexts, hooks, additional UDAs like `reviewed` for `tasksh`) is none
of this codebase's business. Only the `source` UDA is required.

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
