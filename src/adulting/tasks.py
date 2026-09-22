"""Bridge ACTION: lines from notes/logs into anchored TASK: lines, and
expose source-line mutations as subcommands. Source notes ARE the store;
there is no backend.

No-arg invocation (used as a pre-pass by `notes`):
  Walk notes/ + logs/, find every ACTION: line, validate it (thread
  resolves, assignee resolves, attrs well-formed), and rewrite each in
  place to a `TASK: [#X] (Assignee) <body> <!--<uuid8> entry:YYYY-MM-DD
  ...-->` anchor. The uuid8 is freshly generated and checked against
  the existing vault for uniqueness.

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
import os
import re
import sys
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from adulting import vault as V
from adulting.helpjson import emit_helpjson_if_requested
from adulting.vault import vault_home



ACTION_RE = re.compile(
    r'^ACTION:\s*(?:\(([^)]+)\)\s*)?(.+?)(?:\s*<!--(.*?)-->)?\s*$'
)
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
    notes_dir = vault_home() / 'notes'
    logs_dir = vault_home() / 'logs'
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


def read_source(path):
    """A note or log's text, or None if it cannot be read as UTF-8."""
    try:
        return path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None


def walk_anchors():
    """Yield every parsed Anchor in the vault."""
    for path in discover_source_files():
        text = read_source(path)
        if text is None:
            continue
        for i, line in enumerate(text.split('\n')):
            a = parse_anchor(line, path, i)
            if a:
                yield a


def find_anchor(uuid_prefix):
    """Resolve a uuid prefix to a single anchor. Dies on not-found or
    ambiguous. Prefix matches against the 8-char uuid stored in the
    anchor — any prefix length is accepted (1..8)."""
    p = uuid_prefix.lower()
    hits = [a for a in walk_anchors() if a.uuid.startswith(p)]
    if not hits:
        V.die(f"no task found with uuid prefix {uuid_prefix!r}")
    if len(hits) > 1:
        joined = ', '.join(f"{a.uuid} ({a.path.name}:{a.line_no + 1})"
                           for a in hits)
        V.die(f"uuid prefix {uuid_prefix!r} is ambiguous: {joined}")
    return hits[0]


def write_anchor(anchor, new_line):
    """Rewrite a single line in the anchor's source file. Atomic via
    tmp + os.replace."""
    lines = anchor.path.read_text(encoding='utf-8').split('\n')
    lines[anchor.line_no] = new_line
    tmp = anchor.path.with_suffix(anchor.path.suffix + '.tmp')
    tmp.write_text('\n'.join(lines), encoding='utf-8')
    os.replace(tmp, anchor.path)


def mutate_anchor(anchor, **changes):
    """Apply field updates to an Anchor, rewrite its source line, and
    return the updated Anchor."""
    new = replace(anchor, **changes)
    write_anchor(anchor, format_anchor(new))
    return new


# ---------- helpers ----------

def today_iso():
    return date.today().isoformat()


def validate_date(s):
    if not V.DATE_RE.match(s):
        raise ValueError(f"date must be YYYY-MM-DD, got {s!r}")
    return s


def validate_priority(s):
    if s not in ('H', 'M', 'L'):
        raise ValueError(f"priority must be H, M, or L; got {s!r}")
    return s


# ---------- frontmatter parsing (used for thread cache) ----------

def build_threads_cache():
    """Walk all source files once, return {source_relpath: [threads]}."""
    cache = {}
    for f in discover_source_files():
        text = read_source(f)
        if text is None:
            continue
        rel = str(f.relative_to(vault_home()).with_suffix(''))
        cache[rel] = V.note_threads(V.parse_frontmatter_doc(text)[0])
    return cache


def threads_for(anchor, cache):
    rel = str(anchor.path.relative_to(vault_home()).with_suffix(''))
    return cache.get(rel, [])


# ---------- ingest ----------

def find_action_lines(text):
    """Yield (line_no, raw_line, assignee, body, attr_block) for each
    ACTION: in a source file's text."""
    for i, line in enumerate(text.split('\n')):
        m = ACTION_RE.match(line)
        if m:
            assignee = (m.group(1) or '').strip()
            body = m.group(2).strip()
            attr_block = (m.group(3) or '').strip()
            yield i, line, assignee, body, attr_block


def cmd_default(args):
    return ingest(args.dry_run, args.quiet)


def ingest(dry_run=False, quiet=False):
    """No subcommand: walk notes/logs and ingest each ACTION: line."""
    existing = {a.uuid for a in walk_anchors()}
    plan = []
    unreadable = []
    for path in discover_source_files():
        text = read_source(path)
        if text is None:
            unreadable.append((str(path), ["file is not valid UTF-8; skipped"]))
            continue
        threads = V.note_threads(V.parse_frontmatter_doc(text)[0])
        for i, raw_line, assignee, body, attr_block in find_action_lines(text):
            errors = []
            if not body:
                errors.append("missing description")
            if not threads:
                errors.append("note has no threads:")
            else:
                for t in threads:
                    if not V.is_thread(t):
                        errors.append(f"thread {t!r} does not resolve")
            if assignee and not V.person_exists(assignee):
                errors.append(
                    f"assignee {assignee!r} does not resolve to "
                    f"people/{assignee}.md")
            attrs, attr_errs = V.parse_action_attrs(attr_block.split())
            errors.extend(attr_errs)
            plan.append((path, i, assignee, body, attrs, errors))

    if not plan and not unreadable:
        if not quiet:
            print("Ingested: 0.  Failed: 0.")
        return 0

    succeeded = 0
    failed = list(unreadable)
    for path, i, assignee, body, attrs, errors in plan:
        prefix = f"{path}:{i + 1}"
        if errors:
            failed.append((prefix, errors))
            continue
        u = V.new_id(existing)
        existing.add(u)
        anchor = Anchor(
            kind='TASK',
            priority=attrs.get('priority'),
            assignee=assignee or None,
            body=body,
            uuid=u,
            entry=today_iso(),
            due=attrs.get('due'),
            scheduled=attrs.get('scheduled'),
            depends=tuple(attrs.get('depends', [])),
        )
        new_line = format_anchor(anchor)
        if dry_run:
            if not quiet:
                print(f"would: {new_line}")
            continue
        lines = path.read_text(encoding='utf-8').split('\n')
        lines[i] = new_line
        tmp = path.with_suffix(path.suffix + '.tmp')
        tmp.write_text('\n'.join(lines), encoding='utf-8')
        os.replace(tmp, path)
        succeeded += 1
        if not quiet:
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
    if not quiet:
        if succeeded or failed:
            print(f"Ingested: {succeeded}.  Failed: {len(failed)}.")
    return 1 if failed else 0


# ---------- subcommand: add (delegates to buffer add-action) ----------

def cmd_add(args):
    """`tasks add` is `buffer add-action` under another name: the ACTION is
    buffered, and becomes a task on the next flush and ingest."""
    from adulting import buffer
    return buffer.buffer_action(args.thread, args.text, args.due,
                                args.scheduled, args.priority, args.depends)


# ---------- subcommand: done ----------

def cmd_done(args):
    anchor = find_anchor(args.uuid)
    if anchor.kind == 'DONE':
        print(f"{anchor.uuid} already done")
        return 0
    today = today_iso()
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
    try:
        validate_date(date_str)
    except ValueError as e:
        V.die(str(e))
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
    try:
        prio = validate_priority(args.priority)
    except ValueError as e:
        V.die(str(e))
    anchor = find_anchor(args.uuid)
    mutate_anchor(anchor, priority=prio)
    print(f"updated: {anchor.uuid}  priority={prio}")
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
    prefix = args.dep_uuid.lower()
    listed = [d for d in anchor.depends if d.startswith(prefix)]
    if len(listed) > 1:
        V.die(f"uuid prefix {args.dep_uuid!r} is ambiguous: {', '.join(listed)}")
    if listed:
        mutate_anchor(anchor, depends=tuple(d for d in anchor.depends if d != listed[0]))
        print(f"{anchor.uuid} no longer depends on {listed[0]}")
        return 0
    dep = find_anchor(args.dep_uuid)
    new_deps = tuple(d for d in anchor.depends if d != dep.uuid)
    if new_deps == anchor.depends:
        print(f"{anchor.uuid} did not depend on {dep.uuid}")
        return 0
    mutate_anchor(anchor, depends=new_deps)
    print(f"{anchor.uuid} no longer depends on {dep.uuid}")
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


def cmd_list(args):
    anchors = [a for a in walk_anchors() if a.kind == 'TASK']
    if args.priority:
        anchors = [a for a in anchors if a.priority == args.priority]
    if args.assignee:
        anchors = [a for a in anchors if a.assignee == args.assignee]
    if args.overdue:
        today = today_iso()
        anchors = [a for a in anchors if a.due and a.due < today]
    cache = build_threads_cache()
    if args.thread:
        anchors = [a for a in anchors if args.thread in threads_for(a, cache)]
    anchors.sort(key=lambda a: (_thread_sort_key(threads_for(a, cache)),
                                _sort_key(a)))
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
    print(f"source:      "
          f"{anchor.path.relative_to(vault_home())}:{anchor.line_no + 1}")
    print(f"body:        {anchor.body}")
    print(f"entry:       {anchor.entry}")
    print(f"end:         {anchor.end or '-'}")
    print(f"due:         {anchor.due or '-'}")
    print(f"scheduled:   {anchor.scheduled or '-'}")
    print(f"depends:     "
          f"{', '.join(anchor.depends) if anchor.depends else '-'}")
    return 0


# ---------- main ----------

def main():
    parser = argparse.ArgumentParser(
        description="Bridge ACTION lines into source TASK anchors; "
                    "expose anchor mutations as subcommands.")
    parser.add_argument('--dry-run', action='store_true',
                        help="(default invocation only) Show what would "
                             "be ingested without writing.")
    parser.add_argument('--quiet', action='store_true',
                        help="(default invocation only) Suppress per-action "
                             "output.")
    sub = parser.add_subparsers(dest='subcommand')

    p_add = sub.add_parser('add',
        help="Buffer-append a structured ACTION (delegates to `buffer add-action`).")
    p_add.add_argument('thread', help="Thread label like 'Projects/SGB'.")
    p_add.add_argument('text',
        help="'(Assignee) description' or just 'description'.")
    p_add.add_argument('--due', help='YYYY-MM-DD due date.')
    p_add.add_argument('--scheduled', help='YYYY-MM-DD scheduled date.')
    p_add.add_argument('--priority', choices=['H', 'M', 'L'], help="H, M or L.")
    p_add.add_argument('--depends', action='append', default=[],
        help="A task's 8-character uuid, from `tasks list`; repeatable.")
    p_add.set_defaults(func=cmd_add)

    p_done = sub.add_parser('done',
        help="Mark a task complete; rewrites source TASK->DONE and stamps end.")
    p_done.add_argument('uuid', help="The task's uuid, from `tasks list`; any unique prefix will do.")
    p_done.set_defaults(func=cmd_done)

    p_sd = sub.add_parser('set-description', help="Rewrite source body.")
    p_sd.add_argument('uuid', help="The task's uuid, from `tasks list`; any unique prefix will do.")
    p_sd.add_argument('text', help="The new description.")
    p_sd.set_defaults(func=cmd_set_description)

    p_sa = sub.add_parser('set-assignee', help="Rewrite the (Assignee) prefix.")
    p_sa.add_argument('uuid', help="The task's uuid, from `tasks list`; any unique prefix will do.")
    p_sa.add_argument('person', help="A person with a file in people/; `people/` before the name is allowed.")
    p_sa.set_defaults(func=cmd_set_assignee)

    p_sdue = sub.add_parser('set-due', help="Set due date (YYYY-MM-DD).")
    p_sdue.add_argument('uuid', help="The task's uuid, from `tasks list`; any unique prefix will do.")
    p_sdue.add_argument('date', help="YYYY-MM-DD.")
    p_sdue.set_defaults(func=cmd_set_due)

    p_ssch = sub.add_parser('set-scheduled', help="Set scheduled date.")
    p_ssch.add_argument('uuid', help="The task's uuid, from `tasks list`; any unique prefix will do.")
    p_ssch.add_argument('date', help="YYYY-MM-DD.")
    p_ssch.set_defaults(func=cmd_set_scheduled)

    p_sp = sub.add_parser('set-priority',
        help="Set priority H|M|L; writes [#X] in the visible portion.")
    p_sp.add_argument('uuid', help="The task's uuid, from `tasks list`; any unique prefix will do.")
    p_sp.add_argument('priority', help="H, M or L.")
    p_sp.set_defaults(func=cmd_set_priority)

    p_ad = sub.add_parser('add-depends', help="Add a depends entry.")
    p_ad.add_argument('uuid', help="The task's uuid, from `tasks list`; any unique prefix will do.")
    p_ad.add_argument('dep_uuid', metavar='dep-uuid',
        help="The uuid of the task this one waits on; any unique prefix will do.")
    p_ad.set_defaults(func=cmd_add_depends)

    p_rd = sub.add_parser('rm-depends', help="Remove a depends entry.")
    p_rd.add_argument('uuid', help="The task's uuid, from `tasks list`; any unique prefix will do.")
    p_rd.add_argument('dep_uuid', metavar='dep-uuid',
        help="The dependency to remove; any prefix that picks out one of this task's dependencies.")
    p_rd.set_defaults(func=cmd_rm_depends)

    p_list = sub.add_parser('list', help="List pending tasks (formatted).")
    p_list.add_argument('--priority', choices=['H', 'M', 'L'],
        help="Filter to a single priority.")
    p_list.add_argument('--thread',
        help="Filter to tasks whose source note carries this thread "
             "(e.g. Processes/SGB).")
    p_list.add_argument('--assignee',
        help="Filter to tasks assigned to this person.")
    p_list.add_argument('--overdue', action='store_true',
        help="Show only tasks whose due date is before today.")
    p_list.set_defaults(func=cmd_list)

    p_next = sub.add_parser('next',
        help="Top 5 pending tasks by (priority, due, entry).")
    p_next.set_defaults(func=cmd_next)

    p_show = sub.add_parser('show', help="Detail view of one anchor.")
    p_show.add_argument('uuid', help="The task's uuid, from `tasks list`; any unique prefix will do.")
    p_show.set_defaults(func=cmd_show)

    emit_helpjson_if_requested(parser)
    args = parser.parse_args()

    if args.subcommand is None:
        return cmd_default(args)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
