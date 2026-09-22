"""Manage people files in ~/vault/people/.

Non-interactive: every value comes from arguments, and deleting needs -y.

People are link targets (`[[people/<name>]]`) for `note.people` and
action `assignee:`. They are not threads — they cannot be the value of
`note.thread`. Skeleton: just create / delete / list / show.
"""

import json
import sys

from adulting import vault as V
from adulting.helpjson import emit_helpjson_if_requested

def people_dir():
    return V.vault_home() / 'people'


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
        f"---\nstatus: open\ncategory: {args.category}\nstarted: {V.today()}\n---\n\n# {name}\n",
        encoding='utf-8',
    )
    print(f"created: {path}")
    return 0


def _resolve_person(arg):
    """Accept either bare name ('Bern Sellmeyer') or wikilink-style
    ('people/Bern Sellmeyer'). Strips the prefix if present. The name
    becomes people/<name>.md, so it must be a plain filename."""
    arg = arg.strip()
    if arg.startswith('people/'):
        arg = arg[len('people/'):]
    if not V.is_plain_name(arg):
        V.die(f"name {arg!r} cannot contain '/' or start with '.'")
    return arg


def cmd_delete(args):
    name = _resolve_person(args.person)
    path = people_dir() / f"{name}.md"
    if not V.person_exists(name):
        V.die(f"not found: {path}")
    if not args.yes:
        V.die(f"refusing to delete {path} without -y")
    path.unlink()
    print(f"deleted: {path}")
    return 0


def cmd_list(args):
    rows = []
    for name, path in discover_people():
        # `person` is the resolvable wikilink form.
        rows.append({'name': name, 'person': f"people/{name}", **V.file_summary(path)})

    if not args.all:
        rows = [r for r in rows if r['status'] == 'open']

    if args.query:
        rows = V.rank_by_query(rows, args.query, 'name', 'person')

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    if not rows:
        print("(no matches)" if args.query else "(no people)")
        return 0
    person_w = max(len(r['person']) for r in rows)
    print(f"{'PERSON':<{person_w}}  {'STATUS':<8}  CATEGORY")
    for r in rows:
        print(f"{r['person']:<{person_w}}  {r['status']:<8}  {r['category']}")
    return 0


def cmd_show(args):
    name = _resolve_person(args.person)
    path = people_dir() / f"{name}.md"
    if not V.person_exists(name):
        V.die(f"not found: {path}")
    if args.json:
        print(V.file_json(path, name=path.stem))
    else:
        sys.stdout.write(path.read_text(encoding='utf-8'))
    return 0


def main():
    parser = V.command_parser('people', "Manage people files.")
    sub = parser.add_subparsers(dest='subcommand', required=True)

    p = sub.add_parser('list', help="List person files (open by default).")
    p.add_argument('query', nargs='?', default=None,
                        help="Optional fuzzy search; ranks results by similarity.")
    p.add_argument('--all', action='store_true',
                        help="Include closed people (default: open only).")
    p.add_argument('--json', action='store_true', help="JSON output.")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser('show', help="Show a single person file.")
    p.add_argument('person', help="Full name (matches filename without .md).")
    p.add_argument('--json', action='store_true', help="JSON output.")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser('new', help="Create a person file.")
    p.add_argument('--name', required=True, help="Full name; becomes the filename.")
    p.add_argument('--category', required=True, choices=V.CATEGORIES,
                       help="Relationship category.")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser('delete', help="Permanently delete a person file.")
    p.add_argument('person', help="Full name.")
    p.add_argument('-y', '--yes', action='store_true',
                          help="Required: confirms the permanent delete.")
    p.set_defaults(func=cmd_delete)

    emit_helpjson_if_requested(parser)
    args = parser.parse_args()
    V.require_vault()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
