"""Manage thread files in ~/vault/threads/{Projects,Processes,Topics}/.

Non-interactive: every value comes from arguments, and deleting needs -y.

Skeleton: just create / delete / list / show. The richer reporting tools
(daily review, tail, overdue, report) are intentionally omitted — they'll
be rebuilt when we know what views we actually want from notes data.
"""

import argparse
import difflib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from adulting import vault as V
from adulting.helpjson import emit_helpjson_if_requested

KIND_DIRS = V.KIND_DIRS
CATEGORIES = ['professional', 'personal', 'voluntary']


def vault_home():
    """The vault directory. Read on every call, not at import, so tests
    can point it somewhere else."""
    return Path(os.environ.get('ADULTING_HOME', os.path.expanduser('~/vault')))


def threads_dir():
    return vault_home() / 'threads'


def today():
    return datetime.now().strftime('%Y-%m-%d')


def cmd_new(args):
    kind = args.kind
    category = args.category
    name = args.name.strip()
    if not name:
        sys.exit("empty name")
    if not V.is_plain_name(name):
        sys.exit(f"name {name!r} cannot contain '/' or start with '.'")

    # Billing defaults for `hours`. Optional -- most threads are never billed.
    currency = (args.currency or '').strip().upper()
    if currency and not re.match(r'^[A-Z]{3}$', currency):
        sys.exit(f"currency {currency!r} is not a 3-letter ISO code")
    rate = args.rate
    if rate is not None and not currency:
        sys.exit("--rate needs a --currency")

    target_dir = threads_dir() / KIND_DIRS[kind]
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{name}.md"
    if path.exists():
        sys.exit(f"already exists: {path}")
    billing = ''
    if currency:
        billing += f"currency: {currency}\n"
    if rate is not None:
        billing += f"rate: {rate}\n"
    path.write_text(
        f"---\nstatus: open\nkind: {kind}\ncategory: {category}\n"
        f"started: {today()}\n{billing}---\n\n# {name}\n",
        encoding='utf-8',
    )
    print(f"created: {path}")


def cmd_delete(args):
    try:
        match = V.resolve_thread(args.thread)
    except ValueError as e:
        sys.exit(str(e))
    if not match:
        sys.exit(f"not found: {args.thread}")
    kind, name, path = match
    if not args.yes:
        sys.exit(f"refusing to delete {path} without -y")
    path.unlink()
    print(f"deleted: {path}")


def cmd_list(args):
    rows = []
    for kind, name, path in V.discover_threads():
        fm = V.read_frontmatter(path)
        rows.append({
            'kind': kind,
            'name': name,
            'thread': f"{KIND_DIRS[kind]}/{name}",  # resolvable Kind/Name form
            'path': str(path.relative_to(vault_home())),
            'status': fm.get('status', ''),
            'category': fm.get('category', ''),
            'started': fm.get('started', ''),
            'ended': fm.get('ended', ''),
        })

    if not args.all:
        rows = [r for r in rows if r['status'] == 'open']

    if args.query:
        # Match against both bare name and Kind/Name; take the better score.
        scored = [
            (max(V.fuzzy_score(args.query, r['name']),
                 V.fuzzy_score(args.query, r['thread'])), r)
            for r in rows
        ]
        scored = [(s, r) for s, r in scored if s > 0.3]
        scored.sort(key=lambda x: -x[0])
        rows = [r for _, r in scored]

    if args.json:
        print(json.dumps(rows, indent=2))
        return
    if not rows:
        print("(no matches)" if args.query else "(no threads)")
        return
    thread_w = max(len(r['thread']) for r in rows)
    print(f"{'THREAD':<{thread_w}}  {'STATUS':<8}  CATEGORY")
    for r in rows:
        print(f"{r['thread']:<{thread_w}}  {r['status']:<8}  {r['category']}")


def cmd_show(args):
    try:
        match = V.resolve_thread(args.thread)
    except ValueError as e:
        sys.exit(str(e))
    if not match:
        sys.exit(f"not found: {args.thread}")
    kind, name, path = match
    if args.json:
        fm = V.read_frontmatter(path)
        print(json.dumps({
            'kind': kind,
            'name': name,
            'path': str(path.relative_to(vault_home())),
            **fm,
        }, indent=2))
    else:
        sys.stdout.write(path.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description="Manage thread files.")
    sub = parser.add_subparsers(dest='subcommand', required=True)

    p_list = sub.add_parser('list', help="List thread files (open by default).")
    p_list.add_argument('query', nargs='?', default=None,
                        help="Optional fuzzy search; ranks results by similarity.")
    p_list.add_argument('--all', action='store_true',
                        help="Include paused/closed threads (default: open only).")
    p_list.add_argument('--json', action='store_true', help="JSON output.")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser('show', help="Show a single thread file.")
    p_show.add_argument('thread', help="Thread name or 'Kind/Name'.")
    p_show.add_argument('--json', action='store_true', help="JSON output.")
    p_show.set_defaults(func=cmd_show)

    p_new = sub.add_parser('new', help="Create a thread file.")
    p_new.add_argument('--name', required=True, help="Thread name; becomes the filename.")
    p_new.add_argument('--kind', required=True, choices=list(KIND_DIRS),
                       help="Which directory the thread lives in.")
    p_new.add_argument('--category', required=True, choices=CATEGORIES,
                       help="Thread category.")
    p_new.add_argument('--currency', help="Default currency for `hours` (3-letter ISO). Optional.")
    p_new.add_argument('--rate', type=int, help="Default hourly rate for `hours`. Needs --currency.")
    p_new.set_defaults(func=cmd_new)

    p_delete = sub.add_parser('delete', help="Permanently delete a thread file.")
    p_delete.add_argument('thread', help="Thread name or 'Kind/Name'.")
    p_delete.add_argument('-y', '--yes', action='store_true',
                          help="Required: confirms the permanent delete.")
    p_delete.set_defaults(func=cmd_delete)

    emit_helpjson_if_requested(parser)
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
