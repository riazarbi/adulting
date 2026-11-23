"""Search the vault's notes and logs, and summarise activity.

Notes and logs are the only vault entities without a filtered query — tasks,
hours, payments, threads and people all have one. This closes that gap.

`search` returns pointers, never bodies: a path plus enough metadata to
decide whether to open it. Retrieval is a separate step, so a broad search
never drags whole documents along with it.

Subcommands:
  notes     find notes by thread, type, date range or text
  logs      find daily logs by thread, date range or text
  activity  rank threads by what happened in a window
  overview  the whole picture of one thread
  person    the whole picture of one person
  stream    every dated record, merged into one chronology

Thread and person are both attributes of a record, never folders: a note
belongs to every thread its frontmatter names, and refers to a person
however `vault.PersonMatcher` finds them. `--thread` and `--person` filter
on them and combine; `overview` and `person` summarise one of each.

Paths are emitted ABSOLUTE, resolved against ADULTING_HOME. They exist to be
handed straight to a reader, and a reader resolves a relative path against
its own working directory — which is not the vault. In the agent's container
the vault is a bind mount at /vault while the process runs in /workspace, so
a vault-relative path silently resolves to nothing.

A file that cannot be read as UTF-8 is skipped rather than searched, so one
unreadable file cannot cost you a result set. It is named on stderr only when
stderr is a terminal; `lint` reports it either way.

Dates are the EVENT date, not the capture date: a note's frontmatter
`timestamp` is when the thing happened, while its filename is when the note
was written. They differ in both directions — an agenda drafted days before
its meeting, a session written up days after. The filename is used only when
the frontmatter date is missing or malformed.
"""

import json
import re
import sys
from collections import defaultdict
from datetime import date, timedelta

from adulting import buffer as B
from adulting import tasks as T
from adulting import vault as V


STREAM_KINDS = ('note', 'log', 'task', 'done', 'dropped', 'hours', 'payment',
                'thread', 'person', 'pending')

# REF lines pointing at these are the record's own pointer back into the
# log. The record is already a stream event read from its own file, so
# counting the REF too would list it twice.
SELF_REF_RE = re.compile(r'^REF:\s*\[\[(?:Projects|Processes|Topics)/[^\]/]+/(?:hours|payments)\]\]')

DEFAULT_LIMIT = 20

PERSON_HELP = ("A declared person: full name, or a unique part of one. Matches "
               "links, assignees, attendees and the full name in text.")
DEFAULT_WINDOW_DAYS = 7

# Body lines that count as a log entry.
ENTRY_RE = re.compile(r'^(REF|TEXT|ACTION|TASK|DONE|DROPPED|STAT):', re.M)
LEADING_DATE_RE = re.compile(r'^(\d{4}-\d{2}-\d{2})')


def event_date(fm_value, fallback_stem):
    """Event date as YYYY-MM-DD. Frontmatter wins; filename is the fallback."""
    for candidate in (str(fm_value or ''), fallback_stem):
        m = LEADING_DATE_RE.match(candidate.strip().strip('"\''))
        if m:
            return m.group(1)
    return ''


def read_or_skip(path):
    """A file's text, or None and a word to anyone watching.

    `search` answers on stdout and a person may be reading it, so a file that
    cannot be read is skipped either way — and said out loud only when stderr
    is a terminal, where saying it costs nothing.
    """
    text = V.read_utf8(path)
    if text is None:
        V.tell_a_human(f"{path} is not valid UTF-8; skipped")
    return text


def note_records():
    """Every parseable note, as a dict. Unparseable files are skipped."""
    out = []
    for path in V.note_files():
        text = read_or_skip(path)
        if text is None:
            continue
        fm, body = V.parse_frontmatter_doc(text)
        if not fm:
            continue   # no frontmatter: not a note this command knows
        out.append({
            'kind': 'note',
            'path': str(path),
            'date': event_date(fm.get('timestamp'), path.stem),
            'type': str(fm.get('type', '') or '').strip(),
            'topic': str(fm.get('topic', '') or '').strip(),
            'threads': V.note_threads(fm),
            'people': _as_list(fm.get('people')),
            'body': body,
        })
    return out


def _as_list(value):
    if not value:
        return []
    return value if isinstance(value, list) else [value]


def log_records():
    out = []
    for path in V.log_files():
        text = read_or_skip(path)
        if text is None:
            continue
        fm, body = V.parse_frontmatter_doc(text)
        if not fm:
            continue
        t = fm.get('thread') or ''
        if isinstance(t, list):
            t = t[0] if t else ''
        # With no thread in the frontmatter, the folder the log is in says.
        ref = V.unwiki(str(t)) or str(t) or V.thread_of(path)
        out.append({
            'kind': 'log',
            'path': str(path),
            'date': event_date(fm.get('date'), path.stem),
            'type': 'Log',
            'topic': '',
            'threads': [ref] if ref else [],
            'entries': len(ENTRY_RE.findall(body)),
            'people': [],
            'body': body,
        })
    return out


# ---- stream event collection ----
#
# Every event carries the date the thing HAPPENED, taken from the record
# itself. Not file mtime, not the moment it was written down. Where a record
# knows the clock time it is kept; four fifths of them do not, which is why
# there is no time column.

def _event(kind, date, thread, summary, path, time='', ref=None):
    """A stream event. `ref` is what `--person` is matched against: the
    line the event came from, or (body, people) for a whole note. It is
    taken off before anything is printed."""
    return {'kind': kind, 'date': date, 'time': time, 'thread': thread,
            'summary': summary, 'path': path, '_ref': ref}


def stream_documents():
    """Notes, log lines, and the task anchors inside both."""
    out = []
    for r in note_records():
        out.append(_event('note', r['date'], ', '.join(r['threads']) or '-',
                          r['topic'] or '(untitled)', r['path'],
                          ref=(r['body'], r['people'])))
    for r in log_records():
        thread = ', '.join(r['threads']) or '-'
        for line in r['body'].splitlines():
            line = line.strip()
            if not line or SELF_REF_RE.match(line):
                continue
            if line.startswith(('TEXT:', 'REF:')):
                out.append(_event('log', r['date'], thread,
                                  line.split(':', 1)[1].strip(), r['path'],
                                  ref=line))
            # A stat value is shown as it was while it was buffered, and
            # keeps its clock time: unlike other log lines it has one.
            stat = V.STAT_LINE_RE.match(line)
            if stat:
                out.append(_event('log', r['date'], thread,
                                  f"STAT: {stat['name']} {stat['value']}", r['path'],
                                  stat['ts'][11:16], ref=line))
    # A task anchor is two events: `entry:` when it was taken on and `end:`
    # when it was finished or dropped, usually on different days.
    for r in note_records() + log_records():
        thread = ', '.join(r['threads']) or '-'
        for line in r['body'].splitlines():
            line = line.strip()
            a = T.parse_anchor(line)
            if not a:
                continue
            body = f"({a.assignee}) {a.body}" if a.assignee else a.body
            out.append(_event('task', a.entry, thread, body, r['path'], ref=line))
            if a.end:
                closed = 'dropped' if a.kind == 'DROPPED' else 'done'
                out.append(_event(closed, a.end, thread, body, r['path'], ref=line))
    return out


def stream_records():
    """Hours and payments, from their own files at their own times."""
    out = []
    for path, ref, e in V.HOURS.load_all():
        if not e.get('startTime'):
            continue
        when = V.local(e['startTime'], V.HOURS.stamp_name(e))
        out.append(_event('hours', when.strftime('%Y-%m-%d'), ref,
                          f"{V.fmt_duration(V.minutes_of(e))} {e.get('name','')}",
                          str(path), when.strftime('%H:%M')))
    for path, ref, p in V.PAYMENTS.load_all():
        if not p.get('received'):
            continue
        when = V.local(p['received'], V.PAYMENTS.stamp_name(p))
        out.append(_event('payment', when.strftime('%Y-%m-%d'), ref,
                          f"{V.fmt_money(V.dec(p.get('amount', 0)), p.get('currency'))} received",
                          str(path), when.strftime('%H:%M')))
    return out


def stream_entities():
    """Threads opened and people added, from their `started:` date."""
    found = [('thread', V.thread_ref(k, n), path) for k, n, path in V.discover_threads()]
    people_dir = V.vault_home() / 'people'
    if people_dir.is_dir():
        found += [('person', path.stem, path) for path in sorted(people_dir.glob('*.md'))
                  if not path.name.startswith('.')]
    out = []
    for kind, name, path in found:
        text = read_or_skip(path)
        if text is None:
            continue
        fm, _ = V.parse_frontmatter_doc(text)
        started = str(fm.get('started') or '')[:10]
        if not LEADING_DATE_RE.match(started):
            continue
        thread = name if kind == 'thread' else '-'
        verb = 'thread opened' if kind == 'thread' else 'person added'
        out.append(_event(kind, started, thread, f"{verb}: {name}", str(path)))
    return out


def stream_pending():
    """Buffer entries that have not been flushed into a log yet.

    They are real activity; omitting them would make the stream briefly
    wrong in exactly the window someone is checking. `search` never flushes
    — it is read-only, and flushing writes logs, clears the buffer and runs
    task ingest.
    """
    buffer_file = V.vault_home() / 'buffer.md'
    if not buffer_file.exists():
        return []
    out = []
    text = read_or_skip(buffer_file)
    if text is None:
        return []
    entries, _, _ = B.parse_buffer_entries(text.splitlines())
    for e in entries:
        thread, tag, body, date, clock = e['thread'], e['type'], e['body'], e['date'], e['ts'][11:16]
        # A buffered REF back at an hours or payments record is that
        # record's own pointer. The record is already a stream event read
        # from its own file, so showing the pointer too would list it twice
        # — the same exclusion applied to flushed log lines.
        if SELF_REF_RE.match(f"{tag}: {body}"):
            continue
        out.append(_event('pending', date, V.unwiki(thread) or thread,
                          f"{tag}: {body}", str(buffer_file), clock,
                          ref=f"{tag}: {body}"))
    return out


def resolve_thread_arg(arg):
    """Accept 'Northwind', 'Processes/Northwind' or a wikilink. Returns the canonical ref."""
    return V.thread_ref(*V.resolve_target(arg)[:2]) if arg else None


def person_matcher(arg):
    """A matcher for the declared person `arg` names, or None for no `--person`."""
    return V.PersonMatcher(V.resolve_person(arg)) if arg else None


def event_via(person, e):
    """How a stream event refers to the person, or None."""
    ref = e['_ref']
    if isinstance(ref, tuple):
        found = person.record(*ref)
        return found[0] if found else None
    return person.line(ref) if ref else None


def apply_filters(records, thread=None, type_=None, since=None, until=None,
                  text=None, person=None):
    """The records that pass every filter given, newest first. With a
    person, each record kept gains `via` and `match`: how it refers to the
    person and the line where it does."""
    out = []
    needle = text.lower() if text else None
    want_type = type_.lower() if type_ else None
    for r in records:
        if thread and thread not in r['threads']:
            continue
        if want_type and r['type'].lower() != want_type:
            continue
        # With a window, an undated record is outside it.
        if (since or until) and not (r['date'] and V.in_window(r['date'], since, until)):
            continue
        if needle:
            hay = f"{r['topic']}\n{r['body']}".lower()
            if needle not in hay:
                continue
        if person:
            found = person.record(r['body'], r['people'])
            if not found:
                continue
            r['via'], r['match'] = found
        out.append(r)
    out.sort(key=lambda r: (r['date'], r['path']), reverse=True)
    return out


def trim(line, width=90):
    """A line, whitespace collapsed, cut to `width`."""
    flat = ' '.join(line.split())
    return flat if len(flat) <= width else flat[:width] + '…'


def snippet(body, needle, width=90):
    """One line of context around the first match, whitespace collapsed."""
    flat = ' '.join(body.split())
    i = flat.lower().find(needle.lower())
    if i < 0:
        return ''
    start = max(0, i - width // 3)
    piece = flat[start:start + width]
    return ('…' if start else '') + piece + ('…' if start + width < len(flat) else '')


def hours_in_window(since=None, until=None):
    """Minutes logged per thread ref within the window."""
    mins = defaultdict(int)
    for _path, ref, rec in V.HOURS.load_all():
        start, end = rec.get('startTime'), rec.get('endTime')
        if not start or not end:
            continue
        # Mirror `hours` exactly: local date for bucketing, ISO delta for
        # duration. Slicing the UTC string instead would misfile evening work.
        d = V.as_time(start, V.HOURS.stamp_name(rec)).astimezone().strftime('%Y-%m-%d')
        minutes = V.minutes_of(rec)
        if not V.in_window(d, since, until):
            continue
        if minutes > 0:
            mins[ref] += minutes
    return mins


def fmt_hours(minutes):
    return V.fmt_duration(minutes) if minutes else '-'


def window_default(since, until):
    if since is None:
        since = (date.today() - timedelta(days=DEFAULT_WINDOW_DAYS)).isoformat()
    return since, until


# ---- output ----

def emit(rows, as_json, render):
    if as_json:
        print(json.dumps(rows, indent=2))
        return
    if not rows:
        print("(no matches)")
        return
    render(rows)


def render_docs(rows):
    width = max(len(r['path']) for r in rows)
    via_w = max(len(r.get('via', '')) for r in rows)
    for r in rows:
        parts = [r['path'].ljust(width), (r['date'] or '?').ljust(10)]
        if via_w:
            parts.append(r['via'].ljust(via_w))
        if r['kind'] == 'note':
            parts += [r['type'] or '-', ', '.join(r['threads']) or '-', r['topic']]
        else:
            parts += [', '.join(r['threads']) or '-', f"{r['entries']} entries"]
        print('  '.join(p for p in parts if p != ''))
        if r.get('snippet'):
            print(f"    {r['snippet']}")


def cmd_notes(args):
    show_docs(note_records(), args, args.type)
    return 0


def cmd_logs(args):
    show_docs(log_records(), args, None)
    return 0


def show_docs(records, args, type_):
    """`notes` and `logs`: filter, cap, add a snippet. The snippet is the
    context around a `--text` match, else the line that names `--person`."""
    rows = apply_filters(records, resolve_thread_arg(args.thread),
                         type_, args.since, args.until, args.text,
                         person_matcher(args.person))
    rows = rows[:args.limit] if args.limit else rows
    for r in rows:
        if args.text:
            r['snippet'] = snippet(r['body'], args.text)
        else:
            r['snippet'] = trim(r['match']) if 'match' in r else ''
        for key in ('body', 'people', 'match'):
            r.pop(key, None)
    emit(rows, args.json, render_docs)


def cmd_activity(args):
    since, until = window_default(args.since, args.until)
    thread = resolve_thread_arg(args.thread)
    person = person_matcher(args.person)
    notes = apply_filters(note_records(), thread, None, since, until, person=person)
    logs = apply_filters(log_records(), thread, None, since, until, person=person)
    if person:
        # A log counts the lines that name the person, not every entry in
        # it; and hours never name anyone, so they are not counted.
        for r in logs:
            r['entries'] = sum(1 for line in r['body'].splitlines()
                               if ENTRY_RE.match(line.strip()) and person.line(line))
        mins = {}
    else:
        mins = hours_in_window(since, until)

    agg = defaultdict(lambda: {'notes': 0, 'logs': 0, 'entries': 0,
                               'minutes': 0, 'last': ''})
    for r in notes:
        for t in r['threads']:
            a = agg[t]
            a['notes'] += 1
            a['last'] = max(a['last'], r['date'])
    for r in logs:
        for t in r['threads']:
            a = agg[t]
            a['logs'] += 1
            a['entries'] += r['entries']
            a['last'] = max(a['last'], r['date'])
    for ref, m in mins.items():
        if thread and ref != thread:
            continue
        agg[ref]['minutes'] += m

    rows = [{'thread': t, **v} for t, v in agg.items()]
    rows.sort(key=lambda r: (r['notes'] + r['logs'], r['minutes'], r['last']),
              reverse=True)

    def render(rs):
        w = max(len(r['thread']) for r in rs)
        print(f"{'THREAD'.ljust(w)}  NOTES  LOGS  ENTRIES     HOURS  LAST")
        for r in rs:
            print(f"{r['thread'].ljust(w)}  {r['notes']:>5}  {r['logs']:>4}  "
                  f"{r['entries']:>7}  {fmt_hours(r['minutes']):>8}  {r['last'] or '-'}")
        print(f"\nwindow: {since} to {until or 'today'}")

    emit(rows, args.json, render)
    return 0


def cmd_overview(args):
    thread = resolve_thread_arg(args.thread)
    notes = apply_filters(note_records(), thread, None, args.since, args.until)
    logs = apply_filters(log_records(), thread, None, args.since, args.until)
    mins = hours_in_window(args.since, args.until).get(thread, 0)

    by_type = defaultdict(int)
    for r in notes:
        by_type[r['type'] or '-'] += 1
    entries = sum(r['entries'] for r in logs)

    anchors = {'open': 0, 'done': 0, 'dropped': 0}
    for r in notes + logs:
        anchors['open'] += len(re.findall(r'^TASK:', r['body'], re.M))
        anchors['done'] += len(re.findall(r'^DONE:', r['body'], re.M))
        anchors['dropped'] += len(re.findall(r'^DROPPED:', r['body'], re.M))

    recent = sorted(notes + logs, key=lambda r: (r['date'], r['path']), reverse=True)
    if args.limit:  # 0 means all, as for every other --limit
        recent = recent[:args.limit]

    data = {
        'thread': thread,
        'notes': len(notes), 'notes_by_type': dict(by_type),
        'logs': len(logs), 'entries': entries,
        'tasks_open': anchors['open'], 'tasks_done': anchors['done'],
        'tasks_dropped': anchors['dropped'],
        'minutes': mins,
        'last': max([r['date'] for r in notes + logs], default=''),
        'recent': [{k: r[k] for k in ('path', 'date', 'type', 'topic')}
                   for r in recent],
    }

    if args.json:
        print(json.dumps(data, indent=2))
        return 0
    print(f"{data['thread']}")
    if args.since or args.until:
        print(f"window: {args.since or 'start'} to {args.until or 'today'}")
    print()
    types = ', '.join(f"{k} {v}" for k, v in sorted(by_type.items())) or '-'
    print(f"  notes      {data['notes']:>4}   ({types})")
    print(f"  logs       {data['logs']:>4}   {entries} entries")
    print(f"  tasks      {data['tasks_open']:>4} open, {data['tasks_done']} done, "
          f"{data['tasks_dropped']} dropped")
    print(f"  hours      {fmt_hours(mins):>4}")
    print(f"  last       {data['last'] or '-'}")
    if recent:
        print("\n  recent:")
        w = max(len(r['path']) for r in recent)
        for r in recent:
            label = r['topic'] or f"{r.get('entries', 0)} entries"
            print(f"    {r['path'].ljust(w)}  {r['date']}  "
                  f"{r['type'] or '-'}  {label}")
    return 0


def cmd_person(args):
    """The whole picture of one person: where they come up, on which
    threads, and the tasks assigned to them. Counts agree with `notes`,
    `logs` and `stream` given the same `--person`."""
    name = V.resolve_person(args.person)
    person = V.PersonMatcher(name)
    notes = apply_filters(note_records(), None, None, args.since, args.until, person=person)
    logs = apply_filters(log_records(), None, None, args.since, args.until, person=person)

    by_type = defaultdict(int)
    for r in notes:
        by_type[r['type'] or '-'] += 1

    # Log lines as `stream` counts them: TEXT and REF, one event each.
    log_lines = sum(1 for r in logs for line in r['body'].splitlines()
                    if line.strip().startswith(('TEXT:', 'REF:'))
                    and not SELF_REF_RE.match(line.strip()) and person.line(line))

    tasks = {'open': 0, 'done': 0, 'dropped': 0}
    for r in notes + logs:
        for line in r['body'].splitlines():
            a = T.parse_anchor(line.strip())
            if a and a.assignee == name:
                tasks[{'TASK': 'open', 'DONE': 'done', 'DROPPED': 'dropped'}[a.kind]] += 1

    threads = defaultdict(lambda: {'count': 0, 'last': ''})
    for r in notes + logs:
        for t in r['threads']:
            threads[t]['count'] += 1
            threads[t]['last'] = max(threads[t]['last'], r['date'])
    thread_rows = sorted(({'thread': t, **v} for t, v in threads.items()),
                         key=lambda t: (t['count'], t['last']), reverse=True)

    docs = notes + logs
    dates = [r['date'] for r in docs if r['date']]
    recent = sorted(docs, key=lambda r: (r['date'], r['path']), reverse=True)
    if args.limit:  # 0 means all, as for every other --limit
        recent = recent[:args.limit]

    data = {
        'person': name,
        'first': min(dates, default=''), 'last': max(dates, default=''),
        'notes': len(notes), 'notes_by_type': dict(by_type),
        'logs': len(logs), 'log_lines': log_lines,
        'tasks_open': tasks['open'], 'tasks_done': tasks['done'],
        'tasks_dropped': tasks['dropped'],
        'threads': thread_rows,
        'recent': [{'path': r['path'], 'date': r['date'], 'type': r['type'],
                    'via': r['via'], 'line': trim(r['match'])} for r in recent],
    }

    if args.json:
        print(json.dumps(data, indent=2))
        return 0
    print(name)
    if args.since or args.until:
        print(f"window: {args.since or 'start'} to {args.until or 'today'}")
    print()
    types = ', '.join(f"{k} {v}" for k, v in sorted(by_type.items())) or '-'
    print(f"  first seen {data['first'] or '-':>10}")
    print(f"  last seen  {data['last'] or '-':>10}")
    print(f"  notes      {data['notes']:>4}   ({types})")
    print(f"  logs       {data['logs']:>4}   {log_lines} lines")
    print(f"  tasks      {tasks['open']:>4} open, {tasks['done']} done, "
          f"{tasks['dropped']} dropped   (assigned)")
    if thread_rows:
        print("\n  threads:")
        w = max(len(t['thread']) for t in thread_rows)
        for t in thread_rows:
            print(f"    {t['thread'].ljust(w)}  {t['count']:>4}  {t['last'] or '-'}")
    if recent:
        print("\n  recent:")
        w = max(len(r['path']) for r in data['recent'])
        vw = max(len(r['via']) for r in data['recent'])
        for r in data['recent']:
            print(f"    {r['path'].ljust(w)}  {r['date'] or '?':<10}  "
                  f"{r['type'] or '-'}  {r['via'].ljust(vw)}  {r['line']}")
    return 0


def cmd_stream(args):
    if args.today:
        args.since = args.until = date.today().isoformat()
    since, until = window_default(args.since, args.until)

    kinds = STREAM_KINDS
    if args.kind:
        kinds = tuple(k.strip() for k in args.kind.split(',') if k.strip())
        bad = [k for k in kinds if k not in STREAM_KINDS]
        if bad:
            V.die(f"unknown kind(s) {', '.join(bad)}; "
                f"choose from {', '.join(STREAM_KINDS)}")

    events = (stream_documents() + stream_records() + stream_entities()
              + stream_pending())

    thread = resolve_thread_arg(args.thread)
    person = person_matcher(args.person)
    needle = args.text.lower() if args.text else None
    rows = []
    for e in events:
        if e['kind'] not in kinds:
            continue
        # An event's thread text joins every thread it belongs to with ', '.
        # Compare whole names: `Processes/Northwind` must not match `Processes/Northwind Extra`.
        if thread and thread not in e['thread'].split(', '):
            continue
        if not e['date'] or not V.in_window(e['date'], since, until):
            continue
        if needle and needle not in f"{e['thread']} {e['summary']}".lower():
            continue
        if person:
            e['via'] = event_via(person, e)
            if not e['via']:
                continue
        rows.append(e)
    for e in events:
        e.pop('_ref', None)

    # Newest first by default: today is where the eye lands. Within a day,
    # timed events in time order, then the date-only ones.
    rows.sort(key=lambda e: (e['date'], e['time'] or '99:99', e['kind']),
              reverse=not args.reverse)

    total = len(rows)
    if args.limit:
        rows = rows[:args.limit]

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    if not rows:
        print("(no events)")
        print(f"\nwindow: {since} to {args.until or 'today'}")
        return 0

    kw = max(len(e['kind']) for e in rows)
    tw = min(max(len(e['thread']) for e in rows), 30)
    vw = max(len(e.get('via') or '') for e in rows)
    day = None
    for e in rows:
        if e['date'] != day:
            day = e['date']
            print(f"\n{day}")
        clock = f"  ({e['time']})" if e['time'] else ''
        via = f"{e['via']:<{vw}}  " if person else ''
        print(f"  {e['kind']:<{kw}}  {e['thread'][:tw]:<{tw}}  "
              f"{via}{e['summary']}{clock}")
    print(f"\n{total} event(s); window {since} to {args.until or 'today'}")
    if total > len(rows):
        print(f"{total - len(rows)} more not shown — raise --limit")
    return 0


def main():
    parser = V.command_parser(
        'search', "Search notes and logs, and summarise thread activity.")
    sub = V.Subcommands(parser)

    p = sub.add_parser('notes', help="Find notes by thread, type, date or text.")
    p.add_argument('--thread', help="Thread name, 'Kind/Name', or wikilink.")
    p.add_argument('--type', help='Note type, e.g. Meeting. Case-insensitive.')
    p.add_argument('--person', help=PERSON_HELP)
    p.add_argument('--text', help='Case-insensitive literal, over topic and body.')
    p.add_argument('--limit', type=int, default=DEFAULT_LIMIT,
                   help=f'Max results (default {DEFAULT_LIMIT}; 0 for all).')
    V.add_window_flags(p)
    p.set_defaults(func=cmd_notes)

    p = sub.add_parser('logs', help="Find daily logs by thread, date or text.")
    p.add_argument('--thread', help="Thread name, 'Kind/Name', or wikilink.")
    p.add_argument('--person', help=PERSON_HELP)
    p.add_argument('--text', help='Case-insensitive literal, over the entry lines.')
    p.add_argument('--limit', type=int, default=DEFAULT_LIMIT,
                   help=f'Max results (default {DEFAULT_LIMIT}; 0 for all).')
    V.add_window_flags(p)
    p.set_defaults(func=cmd_logs)

    p = sub.add_parser('activity',
                       help="Rank threads by what happened in a window.")
    p.add_argument('--thread', help='Limit to one thread.')
    p.add_argument('--person', help=PERSON_HELP + ' Hours are not counted.')
    V.add_window_flags(p)
    p.set_defaults(func=cmd_activity)

    p = sub.add_parser('overview', help="The whole picture of one thread.")
    p.add_argument('thread', help="Thread name, 'Kind/Name', or wikilink.")
    p.add_argument('--limit', type=int, default=5,
                   help='Recent items to list (default 5; 0 for all).')
    V.add_window_flags(p)
    p.set_defaults(func=cmd_overview)

    p = sub.add_parser('person', help="The whole picture of one person.")
    p.add_argument('person', help="A declared person: full name, or a unique part of one.")
    p.add_argument('--limit', type=int, default=5,
                   help='Recent items to list (default 5; 0 for all).')
    V.add_window_flags(p)
    p.set_defaults(func=cmd_person)

    p = sub.add_parser('stream',
                        help="Every dated record, merged into one chronology.")
    p.add_argument('--thread', help="Thread name, 'Kind/Name', or wikilink.")
    p.add_argument('--kind', help=f"Comma-separated: {', '.join(STREAM_KINDS)}. "
                                   f"Default all.")
    p.add_argument('--person', help=PERSON_HELP)
    p.add_argument('--text', help='Case-insensitive literal over thread and summary.')
    p.add_argument('--today', action='store_true',
                    help="Just today. Shorthand for --since and --until today.")
    p.add_argument('--reverse', action='store_true',
                    help='Oldest first (default is newest first).')
    p.add_argument('--limit', type=int, default=100,
                    help='Max events (default 100; 0 for all).')
    V.add_window_flags(p)
    p.set_defaults(func=cmd_stream)

    args = V.parse_command(parser)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
