"""Work with notes in ~/vault/notes/, named by stem.

A note's stem is its filename without `.md`, e.g. `2026-09-10-14-30-00`.
`notes list` shows every stem; the other subcommands take one.

  notes list [filter]        stem, date, type, threads and topic of each note
  notes cat <stem>           print a note
  notes last                 print the path of the newest note
  notes copy <stem>          copy a note to a new timestamp
  notes delete <stem> -y     delete a note

Non-interactive: nothing prompts, nothing opens an app, and deleting needs -y.

Every subcommand first ingests ACTION: lines into tasks, as the old `notes`
did, so a note shows its task anchors. If any ACTION line cannot be
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

from adulting import tasks
from adulting import vault as V
from adulting.helpjson import emit_helpjson_if_requested

TOOL = 'notes'
TIMESTAMP_RE = re.compile(r'^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}$')


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


# ---------- subcommands ----------

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


def main():
    parser = argparse.ArgumentParser(
        prog=TOOL, description="List, print, copy and delete notes, named by stem.")
    sub = parser.add_subparsers(dest='subcommand', required=True)

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

    emit_helpjson_if_requested(parser)
    args = parser.parse_args()
    ingest_actions()
    args.func(args)


if __name__ == '__main__':
    main()
