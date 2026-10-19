# External integrations

This codebase relies on a few external applications: Obsidian as the
editor, pandoc and xelatex for PDFs, git for `commit`, and optionally
the agent container. Each section documents what we use it for, the
configuration the integration needs, and the steps a fresh install
requires.

(There is no task backend to configure: a task is a `TASK:` line in the
note or log that carries it. See README.md for the design and MANUAL.md
for usage.)

## Obsidian

Used as the markdown editor and vault browser for `~/vault/`. Notes,
threads, and people files are written/read as plain markdown; Obsidian
provides Properties UI, backlinks, graph view, and Bases queries against
the YAML frontmatter.

### Required `~/vault/.obsidian/app.json`

```json
{
  "newLinkFormat": "absolute",
  "useMarkdownLinks": false
}
```

- **`newLinkFormat: "absolute"`** — Obsidian's rename refactor and
  `[[ ]]` autocomplete produce path-qualified wikilinks
  (`[[Projects/Foo]]`), which is what the schemas' `threads:` / `thread:`
  regexes expect. With the default `"shortest"`, renames produce bare `[[Foo]]`
  and `lint` rejects them.
- **`useMarkdownLinks: false`** — wikilinks rather than markdown links.
  Our parsers and schemas assume `[[wikilink]]` form throughout.

Set both via Obsidian: **Settings → Files & Links → New link format → Absolute path in vault** and **Use [[Wikilinks]] → on**. Or write the JSON directly.

### Recommended `~/vault/.obsidian/types.json`

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
- **Daily Notes** — no integration; a thread's daily record is its
  `logs/<YYYY-MM-DD>.md`, written by `buffer flush`

### Recommended community plugin

- **Super Simple Time Tracker** — renders each thread's `hours.md`.
  `hours` writes its entries in the plugin's ```` ```simple-time-tracker ````
  JSON block, and the plugin round-trips the extra keys (`id`, `rate`,
  `currency`) unharmed. Without the plugin the file is still readable
  JSON.

---

## Pandoc + xelatex

Used by `notes pdf` / `notes minutes` / `notes agenda` to render PDFs of
meeting notes, agendas, and arbitrary notes, and by `payments statement
--pdf` to render a statement of account. The renderers pass all options
inline; no per-user config required beyond having the binaries on
`PATH`. Without them, the notes renders still write their markdown and
report the failure; every other command is unaffected.

### Required

- `pandoc` (any recent version)
- A LaTeX engine providing `xelatex`. On macOS, MacTeX (complete) or
  BasicTeX (smaller, may need to install additional LaTeX packages on
  demand). On Linux, TeX Live.

### Pandoc invocation

The notes renderers use `--from=markdown+lists_without_preceding_blankline`,
which gives Obsidian/CommonMark-style list rendering (a list right
after a paragraph, no blank line required) while still supporting
pandoc's default extensions including `raw_tex` (for `\newpage`) and
`yaml_metadata_block`. No alternative pandoc-flavour or extension list
is supported by the rendering scripts.

---

## git

Used by `commit` to record the vault's changes; it is the vault's only
sync mechanism. `$ADULTING_HOME` must be the root of its own git
repository (`git init ~/vault`). `commit save` only ever adds a commit:
it never amends, rebases, resets, checks out or pushes, so pushing to a
remote is yours to do.

---

## The agent container

`Dockerfile` builds an image that runs the agent from
`ghcr.io/riazarbi/agent` with these commands on its `PATH`.

- The vault is expected at `/vault` (`ADULTING_HOME=/vault`) and the
  agent's state at `/state`; mount both writable for UID 1000.
- On every start, `container/entrypoint.sh` copies the tool definitions
  (`dev/tools/*.json`) and skills (`agent/skills/`) into `/state/tools`
  and `/state/skills`, overwriting the files the image ships and leaving
  everything else alone. A hand edit to a shipped file does not survive
  a restart.
- The system prompt is not shipped; it belongs to whoever runs the agent.
- Commits are authored as `agent <agent@sprite.local>`.
- pandoc and LaTeX are left out of the image, so PDF rendering does not
  work inside it.
- Changing the CLI means rebuilding the image.

---

## Anything else?

If you find yourself wanting to integrate another external tool, add
it to this document. The CHANGELOG is for changes to this codebase's
source; INTEGRATIONS.md is the stable reference for what external apps
the codebase expects and how to configure them.
