"""Bridge ACTION: lines from notes/logs into anchored TASK: lines, and
expose source-line mutations as subcommands. Source notes ARE the store;
there is no backend.

No-arg invocation (used as a pre-pass by `notes`):
  Walk notes/ + logs/, find every ACTION: line, validate it (thread
  resolves, assignee resolves, attrs well-formed), and rewrite each in
  place to a `TASK: [#X] (Assignee) <body> <!--<uuid8> entry:YYYY-MM-DD
  ...-->` anchor. The uuid8 is freshly generated and checked against
  the existing vault for uniqueness.

  A file that cannot be read as UTF-8 is skipped, not counted as a failed
  action; it is named on stderr when stderr is a terminal, and `lint`
  reports it either way.

Subcommands:
  add <thread> <text>            buffer-append a structured ACTION
  done <uuid>                    flip source TASK->DONE; stamp end:<today>
  set-description <uuid> <text>  rewrite body
  set-assignee <uuid> <person>   rewrite (Assignee) prefix
  set-due <uuid> <YYYY-MM-DD>    set due date
  set-scheduled <uuid> <YYYY-MM-DD>  set scheduled date
  set-priority <uuid> <H|M|L>    set priority (writes [#X] in visible portion)
  add-depends <uuid> <dep>       add a depends entry
  rm-depends <uuid> <dep>        remove a depends entry
  list [--priority H|M|L] [--thread T] [--assignee A] [--overdue]
                                 grouped by thread (A-Z), then priority/due/entry
  next                           top 5 pending by (priority, due, entry)
  show <uuid>                    detail view
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path

from adulting import vault as V


# Mirror of schemas/task_anchor.md `shape`. The two regexes are kept in
# lockstep — if you change one, change the other.
ANCHOR_RE = re.compile(
    r'^(?P<kind>TASK|DONE):\s+'
    r'(?:\[#(?P<priority>[^\]]+)\]\s+)?'
    r'(?:\((?P<assignee>[^)]+)\)\s+)?'
    r'(?P<body>.+?)\s+'
    r'<!--\s*(?P<uuid>[a-f0-9]{8})'
    r'\s+entry:(?P<entry>\d{4}-\d{2}-\d{2})'
    r'(?:\s+end:(?P<end>\d{4}-\d{2}-\d{2}))?'
    r'(?:\s+due:(?P<due>\d{4}-\d{2}-\d{2}))?'
    r'(?:\s+scheduled:(?P<scheduled>\d{4}-\d{2}-\d{2}))?'
    r'(?:\s+depends:(?P<depends>[a-f0-9,]+))?'
    r'\s*-->\s*$'
)

PRIORITY_ORDER = {'H': 0, 'M': 1, 'L': 2}


# ---------- anchor model ----------

# A dataclass needs its fields written `name: type`; these are the only
# annotations in the code base.
@dataclass
class Anchor:
    kind: str               # 'TASK' or 'DONE'
    priority: str | None    # 'H'/'M'/'L' or None
    assignee: str | None
    body: str
    uuid: str               # 8-char hex
    entry: str              # YYYY-MM-DD
    end: str | None = None
    due: str | None = None
    scheduled: str | None = None
    depends: tuple = ()
    path: Path | None = None
    line_no: int | None = None  # 0-indexed within file


def parse_anchor(line, path=None, line_no=None):
    m = ANCHOR_RE.match(line)
    if not m:
        return None
    d = m.groupdict()
    deps_raw = d.get('depends') or ''
    deps = tuple(x for x in deps_raw.split(',') if x)
    return Anchor(
        kind=d['kind'],
        priority=d.get('priority') or None,
        assignee=(d.get('assignee') or None),
        body=d['body'].strip(),
        uuid=d['uuid'],
        entry=d['entry'],
        end=d.get('end') or None,
        due=d.get('due') or None,
        scheduled=d.get('scheduled') or None,
        depends=deps,
        path=path,
        line_no=line_no,
    )


def format_anchor(a):
    head = [f"{a.kind}:"]
    if a.priority:
        head.append(f"[#{a.priority}]")
    if a.assignee:
        head.append(f"({a.assignee})")
    head.append(a.body)
    attrs = [a.uuid, f"entry:{a.entry}"]
    if a.end:
        attrs.append(f"end:{a.end}")
    if a.due:
        attrs.append(f"due:{a.due}")
    if a.scheduled:
        attrs.append(f"scheduled:{a.scheduled}")
    if a.depends:
        attrs.append(f"depends:{','.join(a.depends)}")
    # Trailing two spaces are a Markdown hard line break: without them
    # pandoc soft-wraps consecutive anchor lines into one paragraph and
    # the PDF renders every task on a single line. The parse regexes
    # tolerate trailing whitespace, so this round-trips cleanly.
    return f"{' '.join(head)} <!--{' '.join(attrs)}-->  "


# ---------- walking / locating ----------

def discover_source_files():
    """Yield .md files in notes/ (flat) and logs/ (recursive). Sorted
    for deterministic ordering. Skips dotfiles."""
    notes_dir = V.vault_home() / 'notes'
    logs_dir = V.vault_home() / 'logs'
    if notes_dir.is_dir():
        for f in sorted(notes_dir.iterdir()):
            if f.suffix == '.md' and not f.name.startswith('.'):
                yield f
    if logs_dir.is_dir():
        for root, dirs, files in os.walk(logs_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for fname in sorted(files):
                if fname.endswith('.md') and not fname.startswith('.'):
                    yield Path(root) / fname


def walk_anchors():
    """Yield every parsed Anchor in the vault."""
    for path in discover_source_files():
        text = V.read_utf8(path)
        if text is None:
            continue
        for i, line in enumerate(text.split('\n')):
            a = parse_anchor(line, path, i)
            if a:
                yield a


def prefix_of(raw):
    """A uuid prefix as typed, lower-cased. An empty one would match
    everything, so it is refused."""
    p = raw.strip().lower()
    if not p:
        V.die("give a uuid prefix; got an empty one")
    return p


def find_anchor(uuid_prefix):
    """Resolve a uuid prefix to a single anchor. Dies on not-found or
    ambiguous. Prefix matches against the 8-char uuid stored in the
    anchor — any prefix length is accepted (1..8)."""
    p = prefix_of(uuid_prefix)
    hits = [a for a in walk_anchors() if a.uuid.startswith(p)]
    if not hits:
        V.die(f"no task found with uuid prefix {uuid_prefix!r}")
    if len(hits) > 1:
        joined = ', '.join(f"{a.uuid} ({V.where(a.path, a.line_no)})"
                           for a in hits)
        V.die(f"uuid prefix {uuid_prefix!r} is ambiguous: {joined}")
    return hits[0]


def write_line(path, line_no, new_line):
    """Rewrite a single line of a file. Atomic via tmp + os.replace, so a
    vault being synced never sees a half-written note."""
    lines = V.read_or_die(path).split('\n')
    lines[line_no] = new_line
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text('\n'.join(lines), encoding='utf-8')
    os.replace(tmp, path)


def write_anchor(anchor, new_line):
    """Rewrite the line an anchor came from."""
    write_line(anchor.path, anchor.line_no, new_line)


def mutate_anchor(anchor, **changes):
    """Apply field updates to an Anchor, rewrite its source line, and
    return the updated Anchor."""
    new = replace(anchor, **changes)
    write_anchor(anchor, format_anchor(new))
    return new


# ---------- frontmatter parsing (used for thread cache) ----------

def build_threads_cache():
    """Walk all source files once, return {source_relpath: [threads]}."""
    cache = {}
    for f in discover_source_files():
        text = V.read_utf8(f)
        if text is None:
            continue
        rel = str(f.relative_to(V.vault_home()).with_suffix(''))
        cache[rel] = V.note_threads(V.parse_frontmatter_doc(text)[0])
    return cache


def threads_for(anchor, cache):
    rel = str(anchor.path.relative_to(V.vault_home()).with_suffix(''))
    return cache.get(rel, [])


# ---------- ingest ----------

def find_action_lines(text):
    """Yield (line_no, action) for each `ACTION:` line in a source file."""
    for i, line in enumerate(text.split('\n')):
        action = V.parse_action(line)
        if action:
            yield i, action


def cmd_ingest(args):
    try:
        ingested, failed = ingest(args.dry_run)
    except OSError as e:
        V.die(str(e))
    return report_ingest(ingested, failed, args.dry_run, args.quiet)


def ingest(dry_run=False):
    """Walk notes and logs and turn each valid ACTION: line into a TASK
    anchor in place; with dry_run, write nothing. Returns (ingested, failed):
    ingested is a list of (uuid, "path:line", body, anchor line), failed a
    list of ("path:line", [errors]) for the lines left as ACTION:."""
    existing = {a.uuid for a in walk_anchors()}
    plan = []
    failed = []
    for path in discover_source_files():
        text = V.read_utf8(path)
        if text is None:
            # Not a failed action: the file had no actions in it as far as
            # anyone can tell. It is said once, where warnings go, and the
            # count stays a count of ACTION lines.
            V.tell_a_human(f"{path} is not valid UTF-8; skipped")
            continue
        threads = V.note_threads(V.parse_frontmatter_doc(text)[0])
        for i, action in find_action_lines(text):
            errors = []
            if not action.body:
                errors.append("missing description")
            if not threads:
                errors.append("note has no threads:")
            else:
                for thread in threads:
                    if not V.is_thread(thread):
                        errors.append(f"thread {thread!r} does not resolve")
            if action.assignee and not V.person_exists(action.assignee):
                errors.append(
                    f"assignee {action.assignee!r} does not resolve to "
                    f"people/{action.assignee}.md")
            errors.extend(action.errors)
            plan.append((path, i, action, errors))

    ingested = []
    for path, i, action, errors in plan:
        prefix = V.where(path, i)
        if errors:
            failed.append((prefix, errors))
            continue
        u = V.new_id(existing)
        existing.add(u)
        anchor = Anchor(
            kind='TASK',
            priority=action.attrs.get('priority'),
            assignee=action.assignee or None,
            body=action.body,
            uuid=u,
            entry=V.today(),
            due=action.attrs.get('due'),
            scheduled=action.attrs.get('scheduled'),
            depends=tuple(action.attrs.get('depends', [])),
        )
        new_line = format_anchor(anchor)
        if not dry_run:
            write_line(path, i, new_line)
        ingested.append((u, prefix, action.body, new_line))
    return ingested, failed


def report_ingest(ingested, failed, dry_run, quiet):
    """Print what ingest did, as `tasks` does. Returns 1 if any line failed."""
    if not ingested and not failed:
        if not quiet:
            print("Ingested: 0.  Failed: 0.")
        return 0
    if not quiet:
        for u, prefix, body, new_line in ingested:
            if dry_run:
                print(f"would: {new_line}")
            else:
                short = body[:60] + ('...' if len(body) > 60 else '')
                print(f"ingested: {u}  {prefix}  {short}")
    if failed:
        print(file=sys.stderr)
        print(f"{len(failed)} action(s) NOT ingested (left as ACTION: in "
              f"source):", file=sys.stderr)
        for p, errs in failed:
            for e in errs:
                print(f"  {p}: {e}", file=sys.stderr)
        print(file=sys.stderr)
    succeeded = 0 if dry_run else len(ingested)
    if not quiet and (succeeded or failed):
        print(f"Ingested: {succeeded}.  Failed: {len(failed)}.")
    return 1 if failed else 0


# ---------- subcommand: add (delegates to buffer add-action) ----------

def cmd_add(args):
    """`tasks add` is `buffer add-action` under another name: the ACTION is
    buffered, and becomes a task on the next flush and ingest."""
    from adulting import buffer  # here, not at the top: buffer imports tasks
    return buffer.buffered(buffer.buffer_action, args.thread, args.text, args.due,
                           args.scheduled, args.priority, args.depends)


# ---------- subcommand: done ----------

def cmd_done(args):
    anchor = find_anchor(args.uuid)
    if anchor.kind == 'DONE':
        print(f"{anchor.uuid} already done")
        return 0
    today = V.today()
    new = mutate_anchor(anchor, kind='DONE', end=today)
    print(f"done: {new.uuid}  {new.body[:60]}")
    return 0


# ---------- subcommand: set-description ----------

def cmd_set_description(args):
    anchor = find_anchor(args.uuid)
    new_text = args.text.strip()
    if not new_text:
        V.die("description is empty")
    mutate_anchor(anchor, body=new_text)
    print(f"updated: {anchor.uuid}  body={new_text[:60]}")
    return 0


# ---------- subcommand: set-assignee ----------

def cmd_set_assignee(args):
    anchor = find_anchor(args.uuid)
    person = args.person.strip()
    if person.startswith('people/'):
        person = person[len('people/'):]
    if not V.person_exists(person):
        V.die(f"person {person!r} does not resolve to people/{person}.md")
    mutate_anchor(anchor, assignee=person)
    print(f"updated: {anchor.uuid}  assignee={person}")
    return 0


# ---------- subcommand: set-due / set-scheduled ----------

def _set_date(uuid_prefix, date_str, field_name):
    if not V.DATE_RE.match(date_str):
        V.die(f"date must be YYYY-MM-DD, got {date_str!r}")
    anchor = find_anchor(uuid_prefix)
    mutate_anchor(anchor, **{field_name: date_str})
    print(f"updated: {anchor.uuid}  {field_name}={date_str}")
    return 0


def cmd_set_due(args):
    return _set_date(args.uuid, args.date, 'due')


def cmd_set_scheduled(args):
    return _set_date(args.uuid, args.date, 'scheduled')


# ---------- subcommand: set-priority ----------

def cmd_set_priority(args):
    V.check_priority(args.priority)
    anchor = find_anchor(args.uuid)
    mutate_anchor(anchor, priority=args.priority)
    print(f"updated: {anchor.uuid}  priority={args.priority}")
    return 0


# ---------- subcommand: add-depends / rm-depends ----------

def cmd_add_depends(args):
    anchor = find_anchor(args.uuid)
    dep = find_anchor(args.dep_uuid)
    if dep.uuid == anchor.uuid:
        V.die("a task cannot depend on itself")
    if dep.uuid in anchor.depends:
        print(f"{anchor.uuid} already depends on {dep.uuid}")
        return 0
    new_deps = anchor.depends + (dep.uuid,)
    mutate_anchor(anchor, depends=new_deps)
    print(f"{anchor.uuid} now depends on {dep.uuid}")
    return 0


def cmd_rm_depends(args):
    anchor = find_anchor(args.uuid)
    # Match against the dependencies first: the task depended on may have
    # been deleted, and a dangling dependency must still be removable.
    prefix = prefix_of(args.dep_uuid)
    listed = [d for d in anchor.depends if d.startswith(prefix)]
    if len(listed) > 1:
        V.die(f"uuid prefix {args.dep_uuid!r} is ambiguous: {', '.join(listed)}")
    if listed:
        mutate_anchor(anchor, depends=tuple(d for d in anchor.depends if d != listed[0]))
        print(f"{anchor.uuid} no longer depends on {listed[0]}")
        return 0
    # Not one of its dependencies. If it names a task, say so; if not,
    # find_anchor reports that.
    dep = find_anchor(args.dep_uuid)
    print(f"{anchor.uuid} did not depend on {dep.uuid}")
    return 0


# ---------- subcommand: list / next / show ----------

def _sort_key(a):
    return (
        PRIORITY_ORDER.get(a.priority, 3),
        a.due or '9999-99-99',
        a.entry,
        a.uuid,
    )


def _thread_sort_key(threads):
    """Alphabetical by the thread shown in the table; unthreaded last."""
    if not threads:
        return (1, '')
    return (0, threads[0].casefold())


def _format_threads(threads):
    if not threads:
        return '-'
    if len(threads) == 1:
        return threads[0]
    return f"{threads[0]} +{len(threads) - 1}"


def _print_table(anchors, cache):
    if not anchors:
        print("(no tasks)")
        return
    rows = []
    for a in anchors:
        prio = f"[#{a.priority}]" if a.priority else "    "
        thread_cell = _format_threads(threads_for(a, cache))
        assignee_cell = f"({a.assignee})" if a.assignee else ''
        cells = [a.uuid, prio, thread_cell, assignee_cell, a.body,
                 f"due:{a.due}" if a.due else '']
        rows.append(cells)
    widths = [max(len(r[c]) for r in rows) for c in range(len(rows[0]))]
    for r in rows:
        print('  '.join(c.ljust(widths[i]) for i, c in enumerate(r)).rstrip())


def as_row(anchor, cache):
    """One anchor as `--json` prints it: the fields `show` prints, with
    nothing padded or abbreviated."""
    return {'uuid': anchor.uuid, 'priority': anchor.priority,
            'assignee': anchor.assignee, 'threads': threads_for(anchor, cache),
            'body': anchor.body, 'source': V.where(anchor.path, anchor.line_no),
            'entry': anchor.entry, 'due': anchor.due,
            'scheduled': anchor.scheduled, 'depends': list(anchor.depends),
            'end': anchor.end}


def cmd_list(args):
    if args.priority:
        V.check_priority(args.priority)
    anchors = [a for a in walk_anchors() if a.kind == 'TASK']
    if args.priority:
        anchors = [a for a in anchors if a.priority == args.priority]
    if args.assignee:
        anchors = [a for a in anchors if a.assignee == args.assignee]
    if args.overdue:
        today = V.today()
        anchors = [a for a in anchors if a.due and a.due < today]
    cache = build_threads_cache()
    if args.thread:
        kind, name, _ = V.resolve_target(args.thread)
        want = V.thread_ref(kind, name)
        anchors = [a for a in anchors if want in threads_for(a, cache)]
    anchors.sort(key=lambda a: (_thread_sort_key(threads_for(a, cache)),
                                _sort_key(a)))
    if args.json:
        print(json.dumps([as_row(a, cache) for a in anchors], indent=2))
        return 0
    _print_table(anchors, cache)
    return 0


def cmd_next(args):
    anchors = [a for a in walk_anchors() if a.kind == 'TASK']
    anchors.sort(key=_sort_key)
    _print_table(anchors[:5], build_threads_cache())
    return 0


def cmd_show(args):
    anchor = find_anchor(args.uuid)
    cache = build_threads_cache()
    threads = threads_for(anchor, cache)
    print(f"uuid:        {anchor.uuid}")
    print(f"kind:        {anchor.kind}")
    print(f"priority:    {anchor.priority or '-'}")
    print(f"assignee:    {anchor.assignee or '-'}")
    print(f"threads:     {', '.join(threads) if threads else '-'}")
    print(f"source:      {V.where(anchor.path, anchor.line_no)}")
    print(f"body:        {anchor.body}")
    print(f"entry:       {anchor.entry}")
    print(f"end:         {anchor.end or '-'}")
    print(f"due:         {anchor.due or '-'}")
    print(f"scheduled:   {anchor.scheduled or '-'}")
    print(f"depends:     "
          f"{', '.join(anchor.depends) if anchor.depends else '-'}")
    return 0


# ---------- main ----------

UUID_HELP = "The task's uuid, from `tasks list`; any unique prefix will do."


def add_ingest_flags(parser, on_subcommand=False):
    """The ingest flags, which bare `tasks` and `tasks ingest` both take.

    On the subcommand they default to SUPPRESS, so `tasks --dry-run ingest`
    keeps the flag it was given instead of the subparser's own default
    overwriting it.
    """
    default = {'default': argparse.SUPPRESS} if on_subcommand else {}
    parser.add_argument('--dry-run', action='store_true', **default,
                        help="Show what would be ingested without writing.")
    parser.add_argument('--quiet', action='store_true', **default,
                        help="Suppress per-action output.")


def main():
    parser = V.command_parser(
        'tasks', "Bridge ACTION lines into source TASK anchors; "
                    "expose anchor mutations as subcommands.")
    add_ingest_flags(parser)
    sub = V.Subcommands(parser)

    p = sub.add_parser('ingest',
        help="Turn ACTION: lines into TASK anchors — what bare `tasks` does.")
    add_ingest_flags(p, on_subcommand=True)
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser('add',
        help="Buffer-append a structured ACTION (delegates to `buffer add-action`).")
    p.add_argument('thread', help="Thread label like 'Projects/SGB'.")
    p.add_argument('text',
        help="'(Assignee) description' or just 'description'.")
    p.add_argument('--due', help='YYYY-MM-DD due date.')
    p.add_argument('--scheduled', help='YYYY-MM-DD scheduled date.')
    p.add_argument('--priority', help="H, M or L.")
    p.add_argument('--depends', action='append', default=[],
        # A dependency is stored verbatim, so unlike every other uuid
        # argument this one is not a prefix.
        help="A task's 8-character uuid, from `tasks list`; repeatable.")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser('done',
        help="Mark a task complete; rewrites source TASK->DONE and stamps end.")
    p.add_argument('uuid', help=UUID_HELP)
    p.set_defaults(func=cmd_done)

    p = sub.add_parser('set-description', help="Rewrite source body.")
    p.add_argument('uuid', help=UUID_HELP)
    p.add_argument('text', help="The new description.")
    p.set_defaults(func=cmd_set_description)

    p = sub.add_parser('set-assignee', help="Rewrite the (Assignee) prefix.")
    p.add_argument('uuid', help=UUID_HELP)
    p.add_argument('person', help="A person with a file in people/; `people/` before the name is allowed.")
    p.set_defaults(func=cmd_set_assignee)

    p = sub.add_parser('set-due', help="Set due date (YYYY-MM-DD).")
    p.add_argument('uuid', help=UUID_HELP)
    p.add_argument('date', help="YYYY-MM-DD.")
    p.set_defaults(func=cmd_set_due)

    p = sub.add_parser('set-scheduled', help="Set scheduled date.")
    p.add_argument('uuid', help=UUID_HELP)
    p.add_argument('date', help="YYYY-MM-DD.")
    p.set_defaults(func=cmd_set_scheduled)

    p = sub.add_parser('set-priority',
        help="Set priority H|M|L; writes [#X] in the visible portion.")
    p.add_argument('uuid', help=UUID_HELP)
    p.add_argument('priority', help="H, M or L.")
    p.set_defaults(func=cmd_set_priority)

    p = sub.add_parser('add-depends', help="Add a depends entry.")
    p.add_argument('uuid', help=UUID_HELP)
    p.add_argument('dep_uuid', metavar='dep-uuid',
        help="The uuid of the task this one waits on; any unique prefix will do.")
    p.set_defaults(func=cmd_add_depends)

    p = sub.add_parser('rm-depends', help="Remove a depends entry.")
    p.add_argument('uuid', help=UUID_HELP)
    p.add_argument('dep_uuid', metavar='dep-uuid',
        help="The dependency to remove; any prefix that picks out one of this task's dependencies.")
    p.set_defaults(func=cmd_rm_depends)

    p = sub.add_parser('list', help="List pending tasks (formatted).")
    p.add_argument('--priority', help="Filter to a single priority: H, M or L.")
    p.add_argument('--thread',
        help="Filter to tasks whose source note carries this thread "
             "(e.g. Processes/SGB).")
    p.add_argument('--assignee',
        help="Filter to tasks assigned to this person.")
    p.add_argument('--overdue', action='store_true',
        help="Show only tasks whose due date is before today.")
    p.add_argument('--json', action='store_true', help='JSON output.')
    p.set_defaults(func=cmd_list)

    p = sub.add_parser('next',
        help="Top 5 pending tasks by (priority, due, entry).")
    p.set_defaults(func=cmd_next)

    p = sub.add_parser('show', help="Detail view of one anchor.")
    p.add_argument('uuid', help=UUID_HELP)
    p.set_defaults(func=cmd_show)

    args = V.parse_command(parser, subcommand_required=False)
    # The ingest flags are top-level so that bare `tasks --dry-run` works, and
    # argparse would take them before any subcommand. They do nothing there,
    # and a flag that silently does nothing is worse than one that errors:
    # `tasks --dry-run done <uuid>` used to flip the anchor and say nothing.
    if args.subcommand not in (None, 'ingest'):
        for flag, name in (('dry_run', '--dry-run'), ('quiet', '--quiet')):
            if getattr(args, flag, False):
                parser.error(f"{name} applies to ingest only, "
                             f"not to {args.subcommand!r}")
    if args.subcommand is None:
        return cmd_ingest(args)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
