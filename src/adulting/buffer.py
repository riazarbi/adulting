"""Operate on the buffer queue at ~/vault/buffer.md.

The buffer is the staging area for captured items. Four line types:
    ACTION:  action item that becomes a TASK anchor after flush
    TEXT:    free-text observation
    REF:     reference to another file in the vault
    UNKNOWN: raw quick-capture; must be converted before tend will pass

Single line format (no multi-line entries; one capture per line):

    - [[<Kind>/<Name>]] ACTION: [(<Person>)] <body> <!--<TS> [<attr> ...]-->
    - [[<Kind>/<Name>]] TEXT:   <body>                                <!--<TS>-->
    - [[<Kind>/<Name>]] REF:    [[<target>]] <summary>                <!--<TS>-->
    - UNKNOWN: <body>                                                 <!--<TS>-->

where TS is `YYYY-MM-DDTHH:MM:SS` and the thread is a resolvable
wikilink to threads/<Kind>/<Name>.md. Attrs (ACTION only) carry what
ingest puts on the TASK anchor it creates:

    due:YYYY-MM-DD     scheduled:YYYY-MM-DD
    priority:H|M|L     depends:<uuid8>

UNKNOWN entries have no thread and carry the input string verbatim.
They are intentionally invalid: `tend` reports them as violations so
they block `flush` until they're removed and re-added via the matching
`buffer add-*` command. This lets you capture something quickly when
you don't have time to pick a thread or shape.

Subcommands:
    add        <text>                    (UNKNOWN; convert later)
    add-text   <thread> <text>
    add-ref    <thread> <target> [<summary>]
    add-action <thread> <text>          (also reachable as `tasks add`)
      every add-* takes [--date YYYY-MM-DD]
    list       [<grep>] [--json]
    rm         <line-number>
    tend                                 (regroup + validate; idempotent)
    flush                                (tend, then write logs/, clear buffer)

Operators (human or agent) interact only via these commands. Direct
edits to buffer.md are discouraged — `tend` is the way to fix things,
and individual entries are added/removed via the API.
"""

import json
import re
import sys
from datetime import datetime

from adulting import vault as V


def buffer_file():
    return V.vault_home() / 'buffer.md'

WIKILINK_BODY_RE = re.compile(r'^\[\[([^\]]+)\]\]\s*(.*)$')

# Buffer line shape: thread wikilink, type tag, body, timestamp comment.
# The comment carries the timestamp and (for ACTION lines) optional attrs.
BUFFER_LINE_RE = re.compile(
    r'^-\s+\[\[([^\]]+)\]\]\s+(ACTION|TEXT|REF):\s+(.+?)\s+<!--(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})((?:\s+\S+)*)-->\s*$'
)

# UNKNOWN entries have no thread; just a body and a timestamp.
UNKNOWN_LINE_RE = re.compile(
    r'^-\s+UNKNOWN:\s+(.+?)\s+<!--(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})-->\s*$'
)


# ---------- helpers ----------

def now_ts():
    return datetime.now().strftime('%Y-%m-%dT%H:%M:%S')


def add_date_flag(parser):
    """--date, on every `add-*`: what it does is true of any entry."""
    parser.add_argument('--date', metavar='YYYY-MM-DD',
                        help="File under this day instead of today. Use the "
                             "date the thing happened, not the date you are "
                             "recording it.")


def stamp(date=None):
    """Buffer timestamp, optionally filed under a different day.

    `flush` groups entries by the date portion of this stamp, so a record
    about last Tuesday belongs in last Tuesday's log, not in the log for the
    day somebody got round to flushing. The clock time is kept as-is: it
    orders entries within the day and is not otherwise load-bearing.
    """
    if not date:
        return now_ts()
    if not V.DATE_RE.match(date):
        raise ValueError(f"--date must be YYYY-MM-DD; got {date!r}")
    return f"{date}T{datetime.now().strftime('%H:%M:%S')}"


def canonical_thread(arg):
    """The canonical `Kind/Name` for a thread given as a name, `Kind/Name` or
    wikilink. Raises ValueError if it does not resolve."""
    kind, name, _ = V.find_thread(arg.strip())
    return V.thread_ref(kind, name)


def format_action_attrs(attrs):
    """Render an attrs dict as a deterministic space-separated string.
    Alphabetical key order; empty depends list omitted."""
    out = []
    if attrs.get('depends'):
        for d in sorted(attrs['depends']):
            out.append(f"depends:{d}")
    if attrs.get('due'):
        out.append(f"due:{attrs['due']}")
    if attrs.get('priority'):
        out.append(f"priority:{attrs['priority']}")
    if attrs.get('scheduled'):
        out.append(f"scheduled:{attrs['scheduled']}")
    return ' '.join(out)


def ref_target_resolves(target):
    """The file a REF target names, spelt exactly, or None. A target is a
    thread (`<Kind>/Name`) or any file under notes/, logs/, people/, hours/
    or payments/, without its `.md`."""
    target = target.strip()
    if target.startswith(('Projects/', 'Processes/', 'Topics/')):
        return V.vault_file(f"threads/{target}.md")
    if target.startswith(('people/', 'notes/', 'logs/', 'hours/', 'payments/')):
        return V.vault_file(f"{target}.md")
    return None


def read_buffer():
    if not buffer_file().exists():
        return []
    return buffer_file().read_text(encoding='utf-8').split('\n')


def write_buffer(lines):
    text = '\n'.join(lines)
    if text and not text.endswith('\n'):
        text += '\n'
    buffer_file().write_text(text, encoding='utf-8')


def append_line(line):
    lines = read_buffer()
    # Drop trailing empty lines for a tight append.
    while lines and lines[-1] == '':
        lines.pop()
    lines.append(line)
    write_buffer(lines)


# ---------- adding entries ----------
#
# Each buffer_* function checks its input, appends one line and returns it.
# A bad input raises ValueError and nothing is written. Only the cmd_*
# functions print or stop the program, so other commands can call these.

def buffered(add, *args):
    """Run an add function for a command: print the line it buffered, or
    stop with its error."""
    try:
        line = add(*args)
    except ValueError as e:
        V.die(str(e))
    print(f"buffered: {line}")
    return 0


def cmd_add(args):
    return buffered(buffer_unknown, args.text, args.date)


def cmd_add_text(args):
    return buffered(buffer_text, args.thread, args.text, args.date)


def cmd_add_ref(args):
    return buffered(buffer_ref, args.thread, args.target, args.summary, args.date)


def cmd_add_action(args):
    return buffered(buffer_action, args.thread, args.text, args.due, args.scheduled,
                    args.priority, args.depends, args.date)


def buffer_unknown(text, date=None):
    text = text.strip()
    if not text:
        raise ValueError("text is empty")
    line = f"- UNKNOWN: {text} <!--{stamp(date)}-->"
    append_line(line)
    return line


def buffer_text(thread, text, date=None):
    thread = canonical_thread(thread)
    text = text.strip()
    if not text:
        raise ValueError("text is empty")
    line = f"- [[{thread}]] TEXT: {text} <!--{stamp(date)}-->"
    append_line(line)
    return line


def buffer_ref(thread, target, summary, date=None):
    thread = canonical_thread(thread)
    target = target.strip()
    summary = (summary or '').strip()
    if not ref_target_resolves(target):
        raise ValueError(f"ref target {target!r} does not resolve to a vault file "
                         f"(expected notes/X, logs/X, people/X, hours/X, payments/X, or <Kind>/X)")
    body = f"[[{target}]]" + (f" {summary}" if summary else "")
    line = f"- [[{thread}]] REF: {body} <!--{stamp(date)}-->"
    append_line(line)
    return line


def buffer_action(thread, text, due=None, scheduled=None, priority=None,
                  depends=None, date=None):
    thread = canonical_thread(thread)
    text = text.strip()
    if not text:
        raise ValueError("description is empty")
    assignee, body = V.split_assignee(text)
    if assignee:
        if not body:
            raise ValueError("description after assignee is empty")
        if not V.person_exists(assignee):
            raise ValueError(f"assignee {assignee!r} does not resolve to people/{assignee}.md "
                             f"(create the person file first)")
    body_text = f"({assignee}) {body}" if assignee else text

    # The same rules the ACTION's attributes meet when they are ingested.
    tokens = [f"{k}:{v}" for k, v in (('due', due), ('scheduled', scheduled),
                                       ('priority', priority)) if v]
    tokens += [f"depends:{d}" for d in depends or []]
    attrs, errors = V.parse_action_attrs(tokens)
    if errors:
        raise ValueError(errors[0])

    attr_str = format_action_attrs(attrs)
    comment = stamp(date) + (f" {attr_str}" if attr_str else "")
    line = f"- [[{thread}]] ACTION: {body_text} <!--{comment}-->"
    append_line(line)
    return line


def add_ref(thread, target, summary, date=None):
    """Append a REF entry on behalf of another command, and return it.

    Best-effort: a record that was written must not be undone or reported as
    failed because the buffer could not be, so any failure returns None and
    prints nothing. `hours` and `payments` need that silence: a warning on
    stderr would cost the caller its stdout.
    """
    try:
        return buffer_ref(thread, target, summary, date)
    except (ValueError, OSError):
        return None


# ---------- subcommand: list ----------

def cmd_list(args):
    lines = read_buffer()
    pattern = (args.filter or '').lower()
    shown = [{'line_no': i, 'text': line}
             for i, line in enumerate(lines, start=1)
             if line.strip() and (not pattern or pattern in line.lower())]
    if args.json:
        print(json.dumps(shown, indent=2))
        return 0
    for row in shown:
        print(f"{row['line_no']:4}  {row['text']}")
    if not shown:
        print("(buffer empty)" if not pattern else "(no matching entries)")
    return 0


# ---------- subcommand: rm ----------

def cmd_rm(args):
    try:
        ln = int(args.line_number)
    except ValueError:
        V.die(f"line number must be an integer; got {args.line_number!r}")
    lines = read_buffer()
    if ln < 1 or ln > len(lines):
        V.die(f"line {ln} out of range (buffer has {len(lines)} lines)")
    removed = lines[ln - 1]
    if not removed.strip():
        V.die(f"line {ln} is empty")
    del lines[ln - 1]
    write_buffer(lines)
    print(f"removed line {ln}: {removed}")
    return 0


# ---------- parsing for tend / flush ----------

def parse_buffer_entries(lines):
    """Walk buffer lines, classify each. Returns:
        entries:  parseable structured entries (ACTION/TEXT/REF).
        unknowns: list of {line_no, body, ts, raw} for UNKNOWN entries.
        unparsed: list of (line_no, raw) for non-empty lines that don't
                  match any known shape.
    Separator comment lines for UNKNOWN/UNPARSED sections are skipped.
    """
    entries = []
    unknowns = []
    unparsed = []
    for i, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        # Skip HTML comment marker lines used as separators in the file.
        if line.lstrip().startswith('<!--') and line.rstrip().endswith('-->') \
           and ('UNPARSED' in line or 'UNKNOWN ENTRIES' in line):
            continue
        m = BUFFER_LINE_RE.match(line)
        if m:
            thread, type_, body, ts, attr_block = m.groups()
            attr_tokens = (attr_block or '').split()
            entries.append({
                'line_no': i,
                'thread': thread,
                'type': type_,
                'body': body.strip(),
                'ts': ts,
                'date': ts[:10],
                'attr_tokens': attr_tokens,
                'raw': line,
            })
            continue
        mu = UNKNOWN_LINE_RE.match(line)
        if mu:
            body, ts = mu.groups()
            unknowns.append({
                'line_no': i,
                'body': body.strip(),
                'ts': ts,
                'raw': line,
            })
            continue
        unparsed.append((i, line))
    return entries, unknowns, unparsed


def validate_entry(e):
    """Yield violation messages for one parseable entry."""
    if not V.is_thread(e['thread']):
        yield f"thread {e['thread']!r} does not resolve"

    try:
        datetime.strptime(e['ts'], '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        yield f"timestamp {e['ts']!r} is not YYYY-MM-DDTHH:MM:SS"

    if e['type'] == 'ACTION':
        body = e['body']
        assignee, rest = V.split_assignee(body)
        if assignee:
            if not rest:
                yield "ACTION description after assignee is empty"
            if not V.person_exists(assignee):
                yield f"ACTION assignee {assignee!r} does not resolve to people/{assignee}.md"
        elif not body:
            yield "ACTION description is empty"
        _attrs, attr_errors = V.parse_action_attrs(e.get('attr_tokens', []))
        for err in attr_errors:
            yield f"ACTION {err}"
    elif e['type'] in ('TEXT', 'REF') and e.get('attr_tokens'):
        yield f"{e['type']} entries do not accept attrs; got {' '.join(e['attr_tokens'])!r}"

    if e['type'] == 'REF':
        wm = WIKILINK_BODY_RE.match(e['body'])
        if not wm:
            yield "REF body must start with a [[wikilink]]"
            return
        target = wm.group(1).strip()
        if not ref_target_resolves(target):
            yield f"REF target {target!r} does not resolve to a vault file"

    elif e['type'] == 'TEXT':
        if not e['body']:
            yield "TEXT body is empty"


def regroup_lines(entries, unknowns, unparsed):
    """Rewrite the buffer in canonical order:
        - Structured entries grouped by (thread, date), sorted by timestamp.
        - UNKNOWN entries in their own section at the bottom, sorted by ts.
        - Unparsed lines after that with their own separator comment.
    Returns the new list of buffer lines.
    """
    by_group = {}
    for e in entries:
        key = (e['thread'], e['date'])
        by_group.setdefault(key, []).append(e)
    out = []
    for key in sorted(by_group.keys()):
        group = sorted(by_group[key], key=lambda e: e['ts'])
        for e in group:
            out.append(e['raw'])
    if unknowns:
        out.append('')
        out.append('<!-- UNKNOWN ENTRIES BELOW: convert via `buffer rm <n>` + the matching `buffer add-*`. tend will fail until cleared. -->')
        for u in sorted(unknowns, key=lambda u: u['ts']):
            out.append(u['raw'])
    if unparsed:
        out.append('')
        out.append('<!-- UNPARSED ENTRIES BELOW: tend cannot regroup these. Fix or remove via `buffer rm`. -->')
        for _ln, raw in unparsed:
            out.append(raw)
    return out


# ---------- subcommand: tend ----------

def cmd_tend(args):
    new_lines, violations = tend(read_buffer())
    write_buffer(new_lines)
    if violations:
        report_violations(violations)
        return 1
    if not args.quiet:
        entries, _, _ = parse_buffer_entries(new_lines)
        groups = {(e['thread'], e['date']) for e in entries}
        print(f"buffer tended: {len(entries)} entries, {len(groups)} group(s).")
    return 0


def tend(lines):
    """Regroup the buffer's lines and check them. Returns (new_lines,
    violations); each violation is (line number in new_lines, message, line).
    Clean means no violations: no invalid entry, UNKNOWN entry or unparsed
    line remains."""
    entries, unknowns, unparsed = parse_buffer_entries(lines)
    new_lines = regroup_lines(entries, unknowns, unparsed)

    # Re-parse so line numbers refer to the regrouped lines.
    entries, unknowns, unparsed = parse_buffer_entries(new_lines)
    violations = []
    for e in entries:
        for v in validate_entry(e):
            violations.append((e['line_no'], v, e['raw']))
    for u in unknowns:
        violations.append((u['line_no'],
                           "UNKNOWN entry must be converted to TEXT, REF, or ACTION before tend can pass",
                           u['raw']))
    for ln, raw in unparsed:
        violations.append((ln, "line does not match buffer entry shape", raw))
    return new_lines, violations


def report_violations(violations):
    print(f"buffer has {len(violations)} violation(s):", file=sys.stderr)
    for ln, msg, raw in violations:
        print(f"  buffer.md:{ln}: {msg}", file=sys.stderr)
        print(f"    line: {raw}", file=sys.stderr)
        print(f"    fix: edit via `buffer rm {ln}` and re-add via the matching `buffer add-*`", file=sys.stderr)


# ---------- subcommand: flush ----------

def cmd_flush(args):
    """Tend, then if clean, write each (thread, date) group to
    logs/<thread>/<date>.md (append if exists) and clear the buffer.

    If tend finds a problem, nothing is written and the buffer is left as
    tend left it. Past that point it is not atomic: the log files are
    written one at a time and the buffer is cleared last, so a crash part
    way through can leave an entry both in a log and still in the buffer."""
    lines, violations = tend(read_buffer())
    write_buffer(lines)
    if violations:
        report_violations(violations)
        return 1

    entries, _unknowns, _unparsed = parse_buffer_entries(lines)
    if not entries:
        if not args.quiet:
            print("buffer is empty; nothing to flush.")
        return 0

    by_group = {}
    for e in entries:
        by_group.setdefault((e['thread'], e['date']), []).append(e)

    written_files = []
    for (thread, date), group in sorted(by_group.items()):
        kind, name = thread.split('/', 1)
        log_dir = V.vault_home() / 'logs' / kind / name
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{date}.md"

        body_lines = []
        for e in sorted(group, key=lambda e: e['ts']):
            line = f"{e['type']}: {e['body']}"
            # ACTION attrs ride along into the log line so ingest can put
            # them on the TASK anchor it creates. TS is dropped — the file's `date:`
            # frontmatter carries day-level resolution; sub-day order is lost.
            if e['type'] == 'ACTION' and e.get('attr_tokens'):
                line += f" <!--{' '.join(e['attr_tokens'])}-->"
            body_lines.append(line)

        if log_path.exists():
            existing = log_path.read_text(encoding='utf-8')
            if not existing.endswith('\n'):
                existing += '\n'
            log_path.write_text(existing + '\n'.join(body_lines) + '\n', encoding='utf-8')
        else:
            header = (
                f"---\n"
                f"thread: \"[[{thread}]]\"\n"
                f"date: {date}\n"
                f"type: Log\n"
                f"---\n"
                f"\n"
                f"# Daily log — {thread} — {date}\n"
                f"\n"
            )
            log_path.write_text(header + '\n'.join(body_lines) + '\n', encoding='utf-8')

        written_files.append((log_path, len(group)))

    write_buffer([])

    if not args.quiet:
        for path, n in written_files:
            rel = path.relative_to(V.vault_home())
            print(f"flushed {n} entr{'y' if n == 1 else 'ies'} -> {rel}")
        print(f"flushed {len(entries)} entries into {len(written_files)} log file(s); buffer cleared.")
        # Flush now so these lines come out ahead of anything the ingest
        # below writes to stderr: stdout is block-buffered when piped.
        sys.stdout.flush()

    # Ingest so any ACTION lines just written to logs/ become task anchors
    # immediately. Its output is passed through, not silenced, so the
    # operator or agent can read the new uuid prefixes off the summary lines.
    # The buffer is already cleared, so a failure here must not fail the
    # flush: the entries are safe in the logs and `tasks` can be re-run.
    from adulting import tasks  # here, not at the top: tasks imports buffer
    try:
        ingested, failed = tasks.ingest()
    except OSError as e:
        V.warn(f"flushed, but the task ingest failed: {e}")
        return 0
    tasks.report_ingest(ingested, failed, dry_run=False, quiet=False)
    return 0


# ---------- main ----------

def main():
    parser = V.command_parser(
        'buffer', "Buffer queue operations: capture, regroup, validate, flush.")
    parser.add_argument('--quiet', action='store_true', help="Suppress info output.")
    sub = parser.add_subparsers(dest='subcommand')

    p = sub.add_parser('add', help="Append an UNKNOWN entry (raw quick-capture; fails tend until converted).")
    p.add_argument('text', help="The raw text to capture.")
    add_date_flag(p)
    p.set_defaults(func=cmd_add)

    p = sub.add_parser('add-text', help="Append a TEXT entry.")
    p.add_argument('thread', help="Thread name, 'Kind/Name', or wikilink.")
    p.add_argument('text', help="The observation to record.")
    add_date_flag(p)
    p.set_defaults(func=cmd_add_text)

    p = sub.add_parser('add-ref', help="Append a REF entry.")
    add_date_flag(p)
    p.add_argument('thread', help="Thread name, 'Kind/Name', or wikilink.")
    p.add_argument('target', help="Wikilink target: notes/<stem>, logs/<path>, people/<name>, "
                         "hours/<Kind>/<Thread>, payments/<Kind>/<Thread>, "
                         "or <Kind>/<Thread>.")
    p.add_argument('summary', nargs='?', default='', help="Optional words shown after the link.")
    p.set_defaults(func=cmd_add_ref)

    p = sub.add_parser('add-action', help="Append an ACTION entry. Also reachable as `tasks add`.")
    p.add_argument('thread', help="Thread name, 'Kind/Name', or wikilink.")
    p.add_argument('text', help="'(Assignee) description' or just 'description'.")
    p.add_argument('--due', help='YYYY-MM-DD due date applied on flush+ingest.')
    p.add_argument('--scheduled', help='YYYY-MM-DD scheduled date.')
    p.add_argument('--priority', help="H, M or L.")
    p.add_argument('--depends', action='append', default=[],
                      help="A task's 8-character uuid, from `tasks list`; repeatable.")
    add_date_flag(p)
    p.set_defaults(func=cmd_add_action)

    p = sub.add_parser('list', help="Show buffer with line numbers.")
    p.add_argument('filter', nargs='?', default='', help="Only lines containing this text, ignoring case.")
    p.add_argument('--json', action='store_true', help='JSON output.')
    p.set_defaults(func=cmd_list)

    p = sub.add_parser('rm', help="Remove a single line by line number.")
    p.add_argument('line_number', metavar='line-number', help="The line's number, from `buffer list`.")
    p.set_defaults(func=cmd_rm)

    p = sub.add_parser('tend', help="Regroup by (thread, date) and validate.")
    p.set_defaults(func=cmd_tend)

    p = sub.add_parser('flush', help="Tend, then write to logs/ and clear buffer.")
    p.set_defaults(func=cmd_flush)

    args = V.parse_command(parser)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
