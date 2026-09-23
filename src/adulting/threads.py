"""Manage thread files in ~/vault/threads/{Projects,Processes,Topics}/.

Non-interactive: every value comes from arguments, and deleting needs -y.

Skeleton: just create / delete / list / show. The richer reporting tools
(daily review, tail, overdue, report) are intentionally omitted — they'll
be rebuilt when we know what views we actually want from notes data.
"""

import sys

from adulting import vault as V

def threads_dir():
    return V.vault_home() / 'threads'


def cmd_new(args):
    kind = args.kind
    category = args.category
    name = args.name.strip()
    if not name:
        V.die("empty name")
    if not V.is_plain_name(name):
        V.die(f"name {name!r} cannot contain '/' or start with '.'")

    # Billing defaults for `hours`. Optional -- most threads are never billed.
    currency = V.check_currency(args.currency) if args.currency else ''
    rate = args.rate
    if rate is not None and not currency:
        V.die("--rate needs a --currency")

    target_dir = threads_dir() / V.KIND_DIRS[kind]
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{name}.md"
    # Asking the filesystem is right here: on macOS `sgb` would overwrite
    # `SGB`, so a name taken in any case is taken.
    if path.exists():
        V.die(f"already exists: {path}")
    billing = ''
    if currency:
        billing += f"currency: {currency}\n"
    if rate is not None:
        billing += f"rate: {rate}\n"
    path.write_text(
        f"---\nstatus: open\nkind: {kind}\ncategory: {category}\n"
        f"started: {V.today()}\n{billing}---\n\n# {name}\n",
        encoding='utf-8',
    )
    print(f"created: {path}")
    return 0


def cmd_delete(args):
    kind, name, path = V.resolve_target(args.thread)
    if not args.yes:
        V.die(f"refusing to delete {path} without -y")
    path.unlink()
    print(f"deleted: {path}")
    return 0


def cmd_list(args):
    rows = []
    for kind, name, path in V.discover_threads():
        # `thread` is the resolvable Kind/Name form.
        rows.append({'kind': kind, 'name': name, 'thread': V.thread_ref(kind, name),
                     **V.file_summary(path)})

    return V.print_summary_list(rows, args, 'thread', 'threads')


def cmd_show(args):
    kind, name, path = V.resolve_target(args.thread)
    if args.json:
        print(V.file_json(path, kind=kind, name=name))
    else:
        sys.stdout.write(path.read_text(encoding='utf-8'))
    return 0


def main():
    parser = V.command_parser('threads', "Manage thread files.")
    sub = parser.add_subparsers(dest='subcommand')

    p = sub.add_parser('list', help="List thread files (open by default).")
    p.add_argument('query', nargs='?', default=None,
                        help="Optional fuzzy search; ranks results by similarity.")
    p.add_argument('--all', action='store_true',
                        help="Include paused/closed threads (default: open only).")
    p.add_argument('--json', action='store_true', help="JSON output.")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser('show', help="Show a single thread file.")
    p.add_argument('thread', help="Thread name or 'Kind/Name'.")
    p.add_argument('--json', action='store_true', help="JSON output.")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser('new', help="Create a thread file.")
    p.add_argument('--name', required=True, help="Thread name; becomes the filename.")
    p.add_argument('--kind', required=True, choices=list(V.KIND_DIRS),
                       help="Which directory the thread lives in.")
    p.add_argument('--category', required=True, choices=V.CATEGORIES,
                       help="Thread category.")
    p.add_argument('--currency', help="Default currency for `hours` (3-letter ISO). Optional.")
    p.add_argument('--rate', type=int, help="Default hourly rate for `hours`. Needs --currency.")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser('delete', help="Permanently delete a thread file.")
    p.add_argument('thread', help="Thread name or 'Kind/Name'.")
    p.add_argument('-y', '--yes', action='store_true',
                          help="Required: confirms the permanent delete.")
    p.set_defaults(func=cmd_delete)

    args = V.parse_command(parser)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
