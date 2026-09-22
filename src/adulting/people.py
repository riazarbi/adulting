"""Manage people files in ~/vault/people/.

Non-interactive: every value comes from arguments, and deleting needs -y.

People are link targets (`[[people/<name>]]`) for `note.people` and
action `assignee:`. They are not threads — they cannot be the value of
`note.thread`. Skeleton: just create / delete / list / show.
"""

import argparse
import json
import sys
from datetime import datetime

from adulting import vault as V
from adulting.helpjson import emit_helpjson_if_requested
from adulting.vault import vault_home

CATEGORIES = ['professional', 'personal', 'voluntary']




def people_dir():
    return vault_home() / 'people'


def today():
    return datetime.now().strftime('%Y-%m-%d')


def discover_people():
    if not people_dir().is_dir():
        return
    for f in sorted(people_dir().iterdir()):
        if f.suffix == '.md' and not f.name.startswith('.'):
            yield f.stem, f


def cmd_new(args):
    name = args.name.strip()
    if not name:
        V.die("empty name")
    if not V.is_plain_name(name):
        V.die(f"name {name!r} cannot contain '/' or start with '.'")

    people_dir().mkdir(parents=True, exist_ok=True)
    path = people_dir() / f"{name}.md"
    if path.exists():
        V.die(f"already exists: {path}")
    path.write_text(
        f"---\nstatus: open\ncategory: {args.category}\nstarted: {today()}\n---\n\n# {name}\n",
        encoding='utf-8',
    )
    print(f"created: {path}")


def _resolve_person(arg):
    """Accept either bare name ('Bern Sellmeyer') or wikilink-style
    ('people/Bern Sellmeyer'). Strips the prefix if present."""
    arg = arg.strip()
    if arg.startswith('people/'):
        arg = arg[len('people/'):]
    return arg


def cmd_delete(args):
    name = _resolve_person(args.person)
    path = people_dir() / f"{name}.md"
    if not path.exists():
        V.die(f"not found: {path}")
    if not args.yes:
        V.die(f"refusing to delete {path} without -y")
    path.unlink()
    print(f"deleted: {path}")


def cmd_list(args):
    rows = []
    for name, path in discover_people():
        fm = V.read_frontmatter(path)
        rows.append({
            'name': name,
            'person': f"people/{name}",  # resolvable wikilink-form
            'path': str(path.relative_to(vault_home())),
            'status': fm.get('status', ''),
            'category': fm.get('category', ''),
            'started': fm.get('started', ''),
            'ended': fm.get('ended', ''),
        })

    if not args.all:
        rows = [r for r in rows if r['status'] == 'open']

    if args.query:
        # Match against both bare name and people/Name; take the better score.
        scored = [
            (max(V.fuzzy_score(args.query, r['name']),
                 V.fuzzy_score(args.query, r['person'])), r)
            for r in rows
        ]
        scored = [(s, r) for s, r in scored if s > 0.3]
        scored.sort(key=lambda x: -x[0])
        rows = [r for _, r in scored]

    if args.json:
        print(json.dumps(rows, indent=2))
        return
    if not rows:
        print("(no matches)" if args.query else "(no people)")
        return
    person_w = max(len(r['person']) for r in rows)
    print(f"{'PERSON':<{person_w}}  {'STATUS':<8}  CATEGORY")
    for r in rows:
        print(f"{r['person']:<{person_w}}  {r['status']:<8}  {r['category']}")


def cmd_show(args):
    name = _resolve_person(args.person)
    path = people_dir() / f"{name}.md"
    if not path.exists():
        V.die(f"not found: {path}")
    if args.json:
        fm = V.read_frontmatter(path)
        print(json.dumps({
            'name': path.stem,
            'path': str(path.relative_to(vault_home())),
            **fm,
        }, indent=2))
    else:
        sys.stdout.write(path.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description="Manage people files.")
    sub = parser.add_subparsers(dest='subcommand', required=True)

    p_list = sub.add_parser('list', help="List person files (open by default).")
    p_list.add_argument('query', nargs='?', default=None,
                        help="Optional fuzzy search; ranks results by similarity.")
    p_list.add_argument('--all', action='store_true',
                        help="Include closed people (default: open only).")
    p_list.add_argument('--json', action='store_true', help="JSON output.")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser('show', help="Show a single person file.")
    p_show.add_argument('person', help="Full name (matches filename without .md).")
    p_show.add_argument('--json', action='store_true', help="JSON output.")
    p_show.set_defaults(func=cmd_show)

    p_new = sub.add_parser('new', help="Create a person file.")
    p_new.add_argument('--name', required=True, help="Full name; becomes the filename.")
    p_new.add_argument('--category', required=True, choices=CATEGORIES,
                       help="Relationship category.")
    p_new.set_defaults(func=cmd_new)

    p_delete = sub.add_parser('delete', help="Permanently delete a person file.")
    p_delete.add_argument('person', help="Full name.")
    p_delete.add_argument('-y', '--yes', action='store_true',
                          help="Required: confirms the permanent delete.")
    p_delete.set_defaults(func=cmd_delete)

    emit_helpjson_if_requested(parser)
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
