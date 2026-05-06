# Changelog

Dated entries, newest first. Each header is a unit of work; bullets capture the detail.

## 2026-05-06 - Render pipeline overhaul: ACTION/TASK lifecycle, owner-aware action table, EXPORT_DIR

- `notes`:
  - `DOWNLOADS_DIR` renamed to `EXPORT_DIR` throughout (declaration, export, help text). Default value `$HOME/Downloads` unchanged.
  - New `extract_people_list` awk function reads the `people:` YAML list-of-scalars from a note's frontmatter, unwraps `[[people/Name]]` wikilinks, emits one entry per stdout line. Exported alongside `extract_meta` via `export -f` so the renderer helpers can call it without re-defining.
  - The pre-action `actions --update` hook is replaced with `tasks --quiet 2>/dev/null || true`. Taskwarrior is now the source of truth for action state, managed via the `tasks` bridge; the `--actions` subcommand is removed.
  - `Start:` / `End:` timestamp appends in `--last` / `--edit` / `--nano` removed. Time tracking is no longer part of the workflow.
  - Help text rewritten: action keywords listed as `ACTION:` / `TASK:` (replacing the old markdown-checkbox convention `- [ ]` / `- [x]`); export destination described as `$EXPORT_DIR (default ~/Downloads)`.

- `notes_new`: dropped the `# Timesheet` section template and the `Start:` / `End:` timestamp appends. New notes now end with `# Content` plus an open editor.

- `notes_minutes`, `notes_pdf`, `notes_agenda` (shared changes):
  - `DOWNLOADS_DIR` → `EXPORT_DIR`.
  - Removed the per-file `extract_meta` definition; helpers rely on the version exported by `notes`. Each gains an env-var guard (`: "${NOTES_DIR:?...}"`, `: "${EXPORT_DIR:?...}"`) and a function-presence check (`type extract_meta >/dev/null 2>&1 || exit`) so direct invocation fails loudly.
  - The `Print:` timestamp append at start-of-render is gone (parallel to time-tracking removal in `notes_new`).
  - Title page rendering switched from `attendees:` / `participants:` (single semicolon-separated string fields) to the new `people:` YAML list, populated via `extract_people_list`. Heading is "Attendees" by default, "Participants" for Correspondence type.
  - Pandoc invocation now uses `--from=markdown+lists_without_preceding_blankline`. Earlier `gfm`-based variants were dropped — `gfm` doesn't accept `raw_tex` so `\newpage` rendered as literal text. Pandoc's default `markdown` already enables `raw_tex` + `yaml_metadata_block`; the added extension gives Obsidian/CommonMark-style list rendering (lists right after a paragraph) without losing LaTeX passthrough.

- `notes_minutes`, `notes_pdf` (action items table):
  - **Status** column dropped from the rendered table. With the new ACTION/TASK lifecycle the source doesn't track open/done state — taskwarrior does — so a status column would be misleading.
  - Legacy `grep '- \[[ x]\]' | sed ... | sort | uniq` pipeline replaced with an inline Python extractor that recognises both `- [ ] / - [x]` (legacy, with optional 5-char key and `(Assignee)`) and `ACTION: / TASK:` (new, with optional `(Assignee)`). De-duplication via a `seen` set; `LEGACY` / `NEW` `re.compile` patterns.
  - Empty assignees substitute with the vault `owner`, read from `~/.adulting/config.yaml` via a small awk one-liner. PDFs are for distribution; the owner needs to appear by name on actions they own.

### Operational events (data migrations against `~/.adulting/`, not in this repo)

- `~/.adulting/config.yaml` created with `owner: Riaz Arbi`. Bootstrap pattern; future constants extend the same file. `people/Riaz Arbi.md` created so the owner has a person file.
- 191 closed `- [x]` action items in SGB notes ingested into taskwarrior via `task log project:SGB end:<date>` (end-date drawn from `actions_log.json`); source rewritten to `TASK: ...` form.
- 32 multi-person / organisational TASK assignees resolved in source (multi-person → first name; `SGB`/`All` → Ralph van Niekerk; `SMT` → Chris Storey; `FINCO` → Tamaryn Cox; `Alice` → Chris Storey).
- 246 plain-string entries in notes' `people:` lists resolved to `[[people/<name>]]` wikilinks. 19 new person files created across two waves — (a) auto-resolution against existing files / first-name shorthands, (b) user-directed via a `~/.adulting/REVIEW.md` workflow.
- SGB and FAMCO threads recategorised from `professional` to `voluntary` (school governance / parent committee — unpaid external commitments).
- Lint clean: 104 files, 0 violations.
