"""Manage people files in ~/vault/people/.

Non-interactive: every value comes from arguments, and deleting needs -y.

People are link targets (`[[people/<name>]]`) for `note.people` and
action `assignee:`. They are not threads — they cannot be the value of
`note.thread`. Skeleton: just create / delete / list / show.
"""

import argparse
import difflib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from adulting.helpjson import emit_helpjson_if_requested

CATEGORIES = ['professional', 'personal', 'voluntary']


def vault_home():
    """The vault directory. Read on every call, not at import, so tests
    can point it somewhere else."""
    return Path(os.environ.get('ADULTING_HOME', os.path.expanduser('~/vault')))


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


def read_frontmatter(path):
    fm = {}
    text = path.read_text(encoding='utf-8')
    lines = text.split('\n')
    if not lines or lines[0].strip() != '---':
        return fm
    for line in lines[1:]:
        if line.strip() == '---':
            break
        m = re.match(r'^([a-z_]+):\s*(.*?)\s*$', line)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return fm


def cmd_new(args):
    name = args.name.strip()
    if not name:
        sys.exit("empty name")

    people_dir().mkdir(parents=True, exist_ok=True)
    path = people_dir() / f"{name}.md"
    if path.exists():
        sys.exit(f"already exists: {path}")
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
        sys.exit(f"not found: {path}")
    if not args.yes:
        sys.exit(f"refusing to delete {path} without -y")
    path.unlink()
    print(f"deleted: {path}")


def fuzzy_score(query, name):
    """Score a name against a query (lowercase compare). Higher = better.
    Heuristic ladder: exact > startswith > initials-equal > substring >
    initials-startswith > difflib ratio (capped below the heuristic floor)."""
    q = query.lower()
    n = name.lower()
    if q == n:
        return 1.0
    if n.startswith(q):
        return 0.9
    initials = ''.join(w[0] for w in re.findall(r'\w+', name)).lower()
    if initials == q:
        return 0.85
    if q in n:
        return 0.7
    if initials.startswith(q):
        return 0.6
    return difflib.SequenceMatcher(None, q, n).ratio() * 0.5


def cmd_list(args):
    rows = []
    for name, path in discover_people():
        fm = read_frontmatter(path)
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
            (max(fuzzy_score(args.query, r['name']),
                 fuzzy_score(args.query, r['person'])), r)
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
        sys.exit(f"not found: {path}")
    if args.json:
        fm = read_frontmatter(path)
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
