"""Work with notes in ~/vault/notes/, named by stem.

A note's stem is its filename without `.md`, e.g. `2026-09-10-14-30-00`.
`notes list` shows every stem; the other subcommands take one.

  notes new --type T --topic X --thread K/N [...]   create a note, print its path
  notes list [filter]        stem, date, type, threads and topic of each note
  notes cat <stem>           print a note
  notes last                 print the path of the newest note
  notes copy <stem>          copy a note to a new timestamp
  notes delete <stem> -y     delete a note
  notes pdf <stem>           render to markdown and PDF, print both paths
  notes minutes <stem>       render meeting minutes
  notes agenda <stem>        render a meeting agenda

Renders go to ~/Downloads, or --out DIR, as <stem>.md and <stem>.md.pdf.

Non-interactive: nothing prompts, nothing opens an app, and deleting needs -y.

Every subcommand except `new` first ingests ACTION: lines into tasks, as the
old `notes` did, so a note shows its task anchors. If any ACTION line cannot be
ingested, the command carries on, with a one-line warning when stderr is a
terminal.
"""

import argparse
import contextlib
import io
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from adulting import buffer
from adulting import render
from adulting import tasks
from adulting import vault as V
from adulting.helpjson import emit_helpjson_if_requested

TOOL = 'notes'
TIMESTAMP_RE = re.compile(r'^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}$')
NOTE_TYPES = ['Meeting', 'Correspondence', 'Workshop', 'Report', 'Log', 'Research', 'Recipe']
PEOPLE_TYPES = ('Meeting', 'Correspondence')


def notes_dir():
    return V.vault_home() / 'notes'


def note_path(stem):
    """The file for a stem. A trailing `.md` is tolerated; anything else
    that is not a note in notes/ is an error."""
    name = stem.strip()
    if name.endswith('.md'):
        name = name[:-3]
    if '/' in name or not name:
        sys.exit(f"{TOOL}: give a note stem like 2026-09-10-14-30-00, got {stem!r}")
    path = notes_dir() / f"{name}.md"
    if not path.is_file():
        sys.exit(f"{TOOL}: no note {name!r} in {notes_dir()}")
    return path


def note_info(path):
    """What `list` shows about one note, read from its frontmatter."""
    fm, _ = V.parse_frontmatter_doc(path.read_text(encoding='utf-8'))
    raw = fm.get('threads') or fm.get('thread') or []
    if isinstance(raw, str):
        raw = [raw]
    timestamp = str(fm.get('timestamp') or '')
    return {
        'stem': path.stem,
        'path': str(path),
        'timestamp': timestamp,
        'date': timestamp[:10],
        'type': str(fm.get('type') or ''),
        'threads': [V.unwiki(t) for t in raw if t],
        'topic': str(fm.get('topic') or ''),
    }


def sort_key(info):
    """Oldest first, by the frontmatter timestamp: when the thing happened.
    The stem stands in when the timestamp is missing or malformed."""
    when = info['timestamp'] if TIMESTAMP_RE.match(info['timestamp']) else info['stem']
    return (when, info['stem'])


def all_notes():
    if not notes_dir().is_dir():
        return []
    infos = [note_info(p) for p in notes_dir().glob('*.md') if not p.name.startswith('.')]
    return sorted(infos, key=sort_key)


def ingest_actions():
    """Turn ACTION: lines into task anchors before doing anything else.

    `tasks` prints nothing useful here, so its output is held back. If any
    ACTION line fails to ingest, say so in one line and carry on, but only
    when stderr is a terminal. The agent harness discards stdout whenever
    stderr is non-empty, so a warning there would cost it the note.
    """
    held = io.StringIO()
    try:
        with contextlib.redirect_stdout(held), contextlib.redirect_stderr(held):
            rc = tasks.cmd_default(argparse.Namespace(dry_run=False, quiet=True))
    except (Exception, SystemExit):  # noqa: BLE001 - a failed ingest must not stop notes
        rc = 1
    if rc != 0 and sys.stderr.isatty():
        print(f"{TOOL}: warning: some ACTION lines were not ingested; run `tasks` to see why",
              file=sys.stderr)


# ---------- writing a new note ----------

def quote(text):
    """A double-quoted YAML string. Only `"` is escaped, as the old bash did."""
    return '"' + text.replace('"', '\\"') + '"'


def people_entry(name):
    """A wikilink when the person has a file, else the plain name."""
    if (V.vault_home() / 'people' / f"{name}.md").exists():
        return f'"[[people/{name}]]"'
    return quote(name)


def note_text(stem, note_type, topic, threads, people=(), counterparty='', location=''):
    """The frontmatter and heading of a new note, field for field as the
    old `notes new` wrote them. A Meeting always has a `location:` line."""
    lines = ['---', f'topic: {topic}', f'type: {note_type}', 'threads:']
    lines += [f'  - "[[{thread}]]"' for thread in threads]
    lines += [f'timestamp: {stem}', f'aliases: [{quote(topic)}]']
    if note_type == 'Meeting':
        if counterparty:
            lines.append(f'counterparty: {counterparty}')
        lines.append(f'location: {location}')
    if people:
        lines.append('people:')
        lines += [f'  - {people_entry(person)}' for person in people]
    lines += ['---', '', '# Content', '', '']
    return '\n'.join(lines)


def buffer_ref(thread, stem, topic):
    """Drop a REF into the buffer so the note shows up in the thread's daily
    log. Best-effort; its `buffered:` line is printed, as before."""
    buffer.add_ref(thread, f"notes/{stem}", topic, quiet=False)


# ---------- subcommands ----------

def cmd_new(args):
    topic = args.topic.strip()
    if not topic:
        sys.exit(f"{TOOL}: --topic is empty")
    people = [p.strip() for p in (args.person or []) if p.strip()]
    if args.person and args.type not in PEOPLE_TYPES:
        sys.exit(f"{TOOL}: --person is only for Meeting and Correspondence notes")
    if (args.counterparty is not None or args.location is not None) and args.type != 'Meeting':
        sys.exit(f"{TOOL}: --counterparty and --location are only for Meeting notes")

    threads = []
    for arg in args.thread:
        kind, name, _ = V.resolve_target(TOOL, arg)
        ref = V.thread_ref(kind, name)
        if ref not in threads:
            threads.append(ref)

    stem = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    path = notes_dir() / f"{stem}.md"
    if path.exists():
        sys.exit(f"{TOOL}: {path} already exists; try again in a second")
    notes_dir().mkdir(parents=True, exist_ok=True)
    path.write_text(note_text(stem, args.type, topic, threads, people,
                              (args.counterparty or '').strip(), (args.location or '').strip()),
                    encoding='utf-8')
    for thread in threads:
        buffer_ref(thread, stem, topic)
    print(path)


def cmd_list(args):
    rows = all_notes()
    if args.filter:
        needle = args.filter.lower()
        rows = [r for r in rows if needle in ' '.join(
            [r['stem'], r['date'], r['type'], ', '.join(r['threads']), r['topic']]).lower()]
    if args.json:
        print(json.dumps(rows, indent=2))
        return
    if not rows:
        print("(no matches)" if args.filter else "(no notes)")
        return
    cells = [[r['stem'], r['date'] or '-', r['type'] or '-',
              ', '.join(r['threads']) or '-', r['topic']] for r in rows]
    widths = [max(len(row[i]) for row in cells) for i in range(4)]
    for row in cells:
        print('  '.join(cell.ljust(widths[i]) for i, cell in enumerate(row[:4])) + '  ' + row[4])


def cmd_cat(args):
    sys.stdout.write(note_path(args.stem).read_text(encoding='utf-8'))


def cmd_last(args):
    rows = all_notes()
    if not rows:
        sys.exit(f"{TOOL}: no notes in {notes_dir()}")
    print(rows[-1]['path'])


def cmd_copy(args):
    source = note_path(args.stem)
    stem = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    target = notes_dir() / f"{stem}.md"
    if target.exists():
        sys.exit(f"{TOOL}: {target} already exists; try again in a second")
    # As the old `sed '/^topic:/s/$/ COPY/'` did: every line that starts
    # with `topic:` gets the suffix, body lines included.
    lines = source.read_text(encoding='utf-8').split('\n')
    lines = [line + ' COPY' if line.startswith('topic:') else line for line in lines]
    target.write_text('\n'.join(lines), encoding='utf-8')
    print(f"Copied {source.name} to {target.name}")


def cmd_delete(args):
    path = note_path(args.stem)
    if not args.yes:
        sys.exit(f"{TOOL}: refusing to delete {path} without -y")
    path.unlink()
    print(f"deleted: {path}")


def cmd_render(args):
    """pdf, minutes or agenda: write <stem>.md and <stem>.md.pdf, print both
    paths. The markdown is kept even if pandoc fails."""
    source = note_path(args.stem)
    # Absolute, because pandoc runs from a scratch directory.
    out_dir = (Path(args.out).expanduser() if args.out else Path.home() / 'Downloads').resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    text = source.read_text(**render.ENCODING)
    owner = render.read_owner(V.vault_home() / '.adulting' / 'config.yaml')
    if args.subcommand == 'pdf':
        markdown = render.pdf_markdown(text, owner)
    elif args.subcommand == 'minutes':
        markdown = render.minutes_markdown(text, owner)
    else:
        markdown = render.agenda_markdown(text)

    md_path = out_dir / source.name
    pdf_path = out_dir / f"{source.name}.pdf"
    md_path.write_text(markdown, **render.ENCODING)
    print(md_path)
    # A PDF left over from an earlier render must not pass for this one.
    pdf_path.unlink(missing_ok=True)
    ok, message = render.to_pdf(md_path, pdf_path)
    if not ok:
        sys.stdout.flush()
        sys.exit(f"{TOOL}: PDF render failed: {message}")
    print(pdf_path)


def main():
    parser = argparse.ArgumentParser(
        prog=TOOL, description="Create, list, print, copy and delete notes, named by stem.")
    sub = parser.add_subparsers(dest='subcommand', required=True)

    p = sub.add_parser('new', help="Create a note and print its path.")
    p.add_argument('--type', required=True, choices=NOTE_TYPES, help="Kind of note.")
    p.add_argument('--topic', required=True, help="What the note is about.")
    p.add_argument('--thread', required=True, action='append',
                   help="Thread name, 'Kind/Name' or wikilink; repeatable.")
    p.add_argument('--person', action='append',
                   help="Meeting and Correspondence only: an attendee; repeatable. "
                        "Linked when people/<name>.md exists.")
    p.add_argument('--counterparty', help="Meeting only: the other party.")
    p.add_argument('--location', help="Meeting only: where it was held.")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser('list', help="List notes, oldest first: stem, date, type, threads, topic.")
    p.add_argument('filter', nargs='?', default='',
                   help="Case-insensitive text to match in any column.")
    p.add_argument('--json', action='store_true', help="JSON output.")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser('cat', help="Print a note.")
    p.add_argument('stem', help="Note stem, e.g. 2026-09-10-14-30-00.")
    p.set_defaults(func=cmd_cat)

    p = sub.add_parser('last', help="Print the path of the newest note.")
    p.set_defaults(func=cmd_last)

    p = sub.add_parser('copy', help="Copy a note to a new timestamp; its topic gets ' COPY'.")
    p.add_argument('stem', help="Note stem to copy.")
    p.set_defaults(func=cmd_copy)

    p = sub.add_parser('delete', help="Permanently delete a note.")
    p.add_argument('stem', help="Note stem to delete.")
    p.add_argument('-y', '--yes', action='store_true',
                   help="Required: confirms the permanent delete.")
    p.set_defaults(func=cmd_delete)

    renders = {
        'pdf': "Render a note to markdown and PDF: callouts and an action table.",
        'minutes': "Render meeting minutes: agreements, resolutions, action items.",
        'agenda': "Render a meeting agenda: the note with the outcome sections emptied.",
    }
    for name, help_text in renders.items():
        p = sub.add_parser(name, help=help_text)
        p.add_argument('stem', help="Note stem to render.")
        p.add_argument('--out', metavar='DIR', help="Where to write the files (default ~/Downloads).")
        p.set_defaults(func=cmd_render)

    emit_helpjson_if_requested(parser)
    args = parser.parse_args()
    if args.subcommand != 'new':
        ingest_actions()
    args.func(args)


if __name__ == '__main__':
    main()
