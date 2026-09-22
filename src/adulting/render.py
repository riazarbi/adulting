"""Render a note as PDF-ready markdown: `notes pdf`, `notes minutes`, `notes agenda`.

A port of the bash scripts notes_pdf, notes_minutes and notes_agenda. Each
step below names the awk, grep or sed it replaces, and reproduces its output
byte for byte, quirks included, so a note renders exactly as it used to.

Text is read and written with errors='surrogateescape', so a note that is not
valid UTF-8 passes through unchanged, as it did through awk.

The markdown is turned into a PDF by pandoc with xelatex, run from a scratch
directory as before.
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ENCODING = dict(encoding='utf-8', errors='surrogateescape')

# awk's [[:space:]]: ASCII whitespace only, unlike Python's \s.
SPACE = ' \t\n\r\f\v'

# awk /--{10,}/: a hyphen followed by ten or more, anywhere in the line.
DASHES_RE = re.compile(r'-{11}')

HR_DASHES = '-' * 68

# notes_minutes inserts this before `# Content` when a note has no `# Summary`.
MINUTES_SUMMARY = (
    "# Summary\n\n## Minuted Agreements\n\n" + HR_DASHES + "\n\n"
    "## Resolutions\n\n" + HR_DASHES + "\n\n"
    "\\newpage\n## Action Items\n\n" + HR_DASHES + "\n\n"
    "\\newpage\n\n")

LEGACY_ACTION_RE = re.compile(r'^-\s*\[[ x]\]\s*(?:[A-Z0-9]{5}\s+)?(?:\(([^)]+)\)\s+)?(.+?)\s*$')
ACTION_RE = re.compile(r'^(?:ACTION|TASK|DONE):\s*(?:\(([^)]+)\)\s*)?(.+?)\s*$')
COMMENT_RE = re.compile(r'\s*<!--[^>]*-->\s*')


# ---------- reading like awk ----------

def records(text):
    """The lines awk would read: split on newline, no empty record after a
    final newline."""
    lines = text.split('\n')
    if text.endswith('\n'):
        lines.pop()
    return lines if text else []


def joined(lines):
    """What awk's `print` produces for these lines: each ends in a newline."""
    return ''.join(line + '\n' for line in lines)


def frontmatter_lines(lines):
    """The lines between an opening `---` on line 1 and the next `---`.
    Without a `---` first line there is no frontmatter."""
    if not lines or lines[0] != '---':
        return []
    out = []
    for line in lines[1:]:
        if line == '---':
            break
        out.append(line)
    return out


def strip_quotes(s):
    if len(s) >= 2 and s[0] == s[-1] and s[0] in '"\'':
        return s[1:-1]
    return s


# ---------- metadata (the extract_* helpers in the bash `notes`) ----------

def extract_meta(lines, field):
    """extract_meta: the first frontmatter line whose key is `field`, with
    surrounding quotes removed and `\\"`/`\\\\` or `''` unescaped."""
    for line in frontmatter_lines(lines):
        if ':' not in line:
            continue
        key, _, value = line.partition(':')
        if key.strip(SPACE) != field:
            continue
        value = value.strip(SPACE)
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            value = value[1:-1].replace('\\"', '"').replace('\\\\', '\\')
        elif len(value) >= 2 and value[0] == "'" and value[-1] == "'":
            value = value[1:-1].replace("''", "'")
        return value
    return ''


def extract_people(lines):
    """extract_people_list: the items of a frontmatter `people:` list.
    `"[[people/Name]]"` becomes `Name`; other items keep their text."""
    out = []
    in_list = False
    for line in frontmatter_lines(lines):
        if in_list and line[:1] and line[0] not in SPACE:
            in_list = False
        if in_list and re.match(r'^[ \t\n\r\f\v]+- ', line):
            value = strip_quotes(re.sub(r'^[ \t\n\r\f\v]+-[ \t\n\r\f\v]+', '', line).strip(SPACE))
            if value.startswith('[[people/') and value.endswith(']]'):
                value = value[len('[[people/'):-2]
            out.append(value)
            continue
        if re.match(r'^people:[ \t\n\r\f\v]*$', line):
            in_list = True
    return out


def read_owner(config_path):
    """The `owner:` from config.yaml, outer double quotes removed; '' if none."""
    if not config_path.exists():
        return ''
    for line in records(config_path.read_text(**ENCODING)):
        m = re.match(r'^owner:[ \t\n\r\f\v]*', line)
        if m:
            return re.sub(r'^"|"$', '', line[m.end():])
    return ''


# ---------- the metadata header ----------

def header(lines, kind):
    """The pandoc metadata block, the `# <type> Details` heading, location and
    people. `kind` is 'pdf', 'minutes' or 'agenda'."""
    title = extract_meta(lines, 'topic')
    note_type = extract_meta(lines, 'type')
    location = extract_meta(lines, 'location')
    date = extract_meta(lines, 'timestamp')[:10]
    if kind == 'pdf':
        top = [f"title: {title}", f"date: {date} ", "toc: false"]
    elif kind == 'agenda':
        top = ["title: Agenda", f"subtitle: {title}", f"date: {date} ", "toc: false"]
    else:
        top = ["title: Minutes", f"subtitle: {title}", f"date: {date} ", "toc: true", "toc-depth: 2"]
    out = ["---"] + top + [
        "mainfont: Arial",
        "header-includes:",
        "  - \\usepackage{geometry}",
        "geometry:",
        "- top=30mm",
        "- left=20mm",
        "- heightrounded",
        "---",
        "",
        "\\newpage",
        "",
        f"# {note_type} Details",
        "",
    ]
    if location:
        out += [f"**Location**: {location}  ", ""]
    people = [p for p in extract_people(lines) if p]
    if people:
        label = "Participants" if note_type == 'Correspondence' else "Attendees"
        out += [f"**{label}**:  ", ""] + [f"- {p}" for p in people]
    return out


# ---------- body passes ----------

def without_frontmatter(lines):
    """Drop the frontmatter block, as every body awk pass does first."""
    if lines and lines[0] == '---':
        for i, line in enumerate(lines[1:], start=1):
            if line == '---':
                return lines[i + 1:]
        return []
    return lines


def cut_sections(lines, headings, stops):
    """The minutes/agenda body awk: after a line containing one of
    `headings`, skip lines until one with eleven or more hyphens; stop
    entirely at a line containing one of `stops`."""
    out = []
    printing = True
    for line in without_frontmatter(lines):
        matched = next((h for h in headings if h in line), None)
        if matched:
            out.append(line)
            printing = False
            continue
        if DASHES_RE.search(line) and not printing:
            printing = True
        if any(s in line for s in stops):
            break
        if printing:
            out.append(line)
    return out


def fill_sections(lines, inserts):
    """The final awk: after a line containing a heading in `inserts`, print
    that heading's lines, then skip until eleven or more hyphens."""
    out = []
    printing = True
    for line in lines:
        matched = next((h for h in inserts if h in line), None)
        if matched:
            out.append(line)
            out.extend(inserts[matched])
            printing = False
            continue
        if DASHES_RE.search(line) and not printing:
            printing = True
        if printing:
            out.append(line)
    return out


def grep_sed_uniq(lines, needle, prefix):
    """`grep needle | sed 's/prefix//' | uniq`: matching lines, the first
    `prefix` removed from each, adjacent duplicates dropped."""
    out = []
    for line in lines:
        if needle in line:
            line = line.replace(prefix, '', 1)
            if not out or out[-1] != line:
                out.append(line)
    return out


def action_rows(lines, owner):
    """The embedded python in the bash scripts: one table row per distinct
    (assignee, task), from `- [ ]` checkboxes and ACTION/TASK/DONE lines.
    An action with no assignee is given to the owner."""
    rows, seen = [], set()
    for line in lines:
        m = LEGACY_ACTION_RE.match(line) or ACTION_RE.match(line)
        if not m:
            continue
        assignee = (m.group(1) or '').strip() or owner
        task = COMMENT_RE.sub(' ', m.group(2)).strip()
        if (assignee, task) in seen:
            continue
        seen.add((assignee, task))
        rows.append(f"| {assignee} | {task} |")
    return rows


def strip_empty_headers(lines):
    """The agenda's END awk: drop an H3 or deeper heading with no body text
    before the next heading of the same or higher level. H1/H2 always stay;
    sub-headings and horizontal rules do not count as body."""
    def level(s):
        if not re.match(r'^#+[ \t\n\r\f\v]+', s):
            return 0
        return len(s) - len(s.lstrip('#'))

    out = []
    for i, line in enumerate(lines):
        lvl = level(line)
        if lvl <= 2:
            out.append(line)
            continue
        for later in lines[i + 1:]:
            later_lvl = level(later)
            if 0 < later_lvl <= lvl:
                break
            if later_lvl == 0 and later.strip(SPACE) and not is_hr(later):
                out.append(line)
                break
    return out


def is_hr(s):
    t = ''.join(c for c in s if c not in SPACE)
    return len(t) >= 3 and (set(t) == {'-'} or set(t) == {'*'} or set(t) == {'_'})


def pad_rules(lines):
    """pad_note_rules: a blank line above and below every horizontal rule in
    the body. The metadata block between the first two `---` is left alone."""
    out = []
    in_fm = False
    prev_blank = True
    prev_hr = False
    for n, line in enumerate(lines, start=1):
        if n == 1 and line == '---':
            out.append(line)
            in_fm, prev_blank = True, False
            continue
        if in_fm and line == '---':
            out.append(line)
            in_fm, prev_blank = False, True
            continue
        if in_fm:
            out.append(line)
            continue
        hr = is_hr(line)
        if (hr and not prev_blank) or (not hr and prev_hr and line.strip(SPACE)):
            out.append('')
        out.append(line)
        prev_blank = not line.strip(SPACE)
        prev_hr = hr
    return out


# ---------- the three renderers ----------

def pdf_markdown(note_text, owner):
    """notes_pdf: body up to `# Timesheet`, callouts after `# Summary`, the
    action table after `# Action Items`."""
    lines = records(note_text)
    body = []
    for line in without_frontmatter(lines):
        if '# Timesheet' in line:
            break
        body.append(line)
    doc = header(lines, 'pdf') + body
    callouts = [''] + grep_sed_uniq(doc, '!:', '!: ') + ['']
    actions = (['', '| Assignee | Task |', '|----------|--------------------------------------------------|']
               + action_rows(doc, owner) + [''])
    return joined(pad_rules(fill_sections(doc, {'# Summary': callouts, '# Action Items': actions})))


def agenda_markdown(note_text):
    """notes_agenda: the note with Agreements, Resolutions and Action Items
    emptied, cut at `# Timesheet` or `# Acceptance`, empty H3+ dropped."""
    lines = records(note_text)
    body = cut_sections(lines, ('# Minuted Agreements', '# Resolutions', '# Action Items'),
                        ('# Timesheet', '# Acceptance'))
    return joined(pad_rules(header(lines, 'agenda') + strip_empty_headers(body)))


def minutes_markdown(note_text, owner):
    """notes_minutes: a Summary with Agreements, Resolutions and Action Items
    filled from AGREED:, RESOLVED: and ACTION/TASK/DONE lines."""
    if '# Summary' not in note_text:
        # awk `print "<summary>"` adds its own newline before the line itself.
        note_text = joined([MINUTES_SUMMARY + '\n' + line if '# Content' in line else line
                            for line in records(note_text)])
    lines = records(note_text)
    body = cut_sections(lines, ('# Minuted Agreements', '# Resolutions', '# Action Items'),
                        ('# Timesheet',))
    doc = records(joined(header(lines, 'minutes') + body))

    rows = action_rows(doc, owner) or ['| None | None |']
    inserts = {
        '# Minuted Agreements': found_block(grep_sed_uniq(doc, 'AGREED:', 'AGREED: '),
                                            "No minutes agreements were made."),
        '# Resolutions': found_block(grep_sed_uniq(doc, 'RESOLVED:', 'RESOLVED: '),
                                     "No Resolutions were passed."),
        '# Action Items': ['', '| Assignee | Task |',
                           '|----------|--------------------------------------------------|'] + rows + [''],
    }
    return joined(pad_rules(fill_sections(doc, inserts)))


def found_block(found, placeholder):
    """The agreed/resolved lines as the bash built them: a blank line, the
    lines, a blank line. When no line has any text, the placeholder replaces
    the whole block except the final blank line."""
    if any(found):
        return [''] + found + ['']
    return [placeholder, '']


# ---------- pandoc ----------

def to_pdf(md_path, pdf_path):
    """Render with pandoc and xelatex from a scratch directory, as before.
    Returns (ok, message)."""
    if shutil.which('pandoc') is None:
        return False, "pandoc is not installed"
    with tempfile.TemporaryDirectory() as scratch:
        proc = subprocess.run(
            # Absolute paths: pandoc runs from the scratch directory.
            ['pandoc', str(Path(md_path).resolve()), '--from=markdown+lists_without_preceding_blankline',
             '-s', '-o', str(Path(pdf_path).resolve()), '--pdf-engine=xelatex',
             '-V', 'header-includes=\\let\\oldtoc\\tableofcontents'
                   '\\renewcommand{\\tableofcontents}{\\oldtoc\\newpage}',
             '-V', 'header-includes=\\AtBeginEnvironment{quote}{\\itshape}'],
            cwd=scratch, capture_output=True, text=True)
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout).strip()
    return True, ''
