"""Log numbers against declared stats, and show how they move over time.

A stat is something measured: push-ups, steps, kilometres run, money spent.
It is declared once on a thread, in the thread file's frontmatter:

    stats:
      - name: pushups
        type: int
        agg: sum

`type` is `int` or `decimal`. `agg` says how a series combines the values
that fall in one period: `sum` adds them (push-ups done in sets), `last`
takes the latest (a step count that is a running total), `max` the largest
(a best set). Names are unique across the vault, so `stats log pushups 25`
needs no thread.

An event, something that happens or does not ("I drank alcohol today"), is
an `int` stat logged as `1` each time it happens: under `sum` its series
counts the occurrences, under `max` it says whether it happened at all.

A value is buffered like every other capture, as
    - [[<Kind>/<Name>]] STAT: <name> <value> <!--<TS>-->
and `buffer flush` files it in the thread's daily log as
    STAT: <name> <value> <!--<TS>-->
keeping its timestamp. `series` reads the logs and the unflushed buffer.

Subcommands:
    new     <name> --thread <thread> --type int|decimal --agg sum|last|max
    list    [--json]
    log     <name> <value> [-d YYYY-MM-DD] [-t HH:MM]
    series  <name> [--since] [--until] [--by day|week|month] [--json]

There is no rename and no delete. Changing a declaration is an edit to the
thread's frontmatter; values already logged are not rewritten.

Exit 1, with the reason on stderr and nothing written, when:
    - the name is not declared (`stats log` and `series` suggest close
      matches), or is declared on two threads, or twice on one;
    - the value is not of the stat's type: `int` takes a whole number,
      `decimal` a plain number such as 12.50, never 1e3;
    - `-d/--date` is not YYYY-MM-DD, or `-t/--time` is not HH:MM;
    - `new` gets a bad name, a name already declared, a thread that does not
      resolve, or a thread file whose frontmatter it cannot safely add to;
    - `series` finds a logged value that is not of the stat's type, naming
      the file and line, or `--since` is after `--until`.
Exit 2 is a usage error: a missing argument, or an unknown --type or --agg.
"""

import json
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal

from adulting import buffer as B
from adulting import vault as V

EVENT_HELP = ("To record that something happened (an event, a yes/no), declare an "
              "int stat and log 1 each time it happens: with --agg sum the series "
              "counts occurrences, with --agg max it shows whether it happened at all.")


# ---------- new ----------

def stat_item(name, type_, agg):
    """The frontmatter lines that declare one stat, as `cadences` are
    written: the reader takes a list of mappings in block style only."""
    return [f"  - name: {name}", f"    type: {type_}", f"    agg: {agg}"]


def declare(text, item):
    """`text`, a thread file, with `item` appended to its `stats:` list. A
    `stats:` key is created before the closing `---` when there is none.
    Raises ValueError when the file has no frontmatter, or a `stats:` value
    this cannot append to."""
    lines = text.split('\n')
    if not lines or lines[0].strip() != '---':
        raise ValueError("thread file has no frontmatter")
    end = next((i for i, line in enumerate(lines[1:], start=1) if line.strip() == '---'), None)
    if end is None:
        raise ValueError("thread file's frontmatter is not closed with ---")
    # Writing around a line the reader skips would leave it skipped: a
    # flush-left item under `stats:` stays invisible beside the new one.
    unread = V.unread_lines(lines[1:end])
    if unread:
        i, line = unread[0]
        raise ValueError(f"frontmatter line {i + 2} is not read ({line!r}); "
                         f"indent it under its key first (`lint` reports it)")
    key = next((i for i in range(1, end) if lines[i].split(':', 1)[0] == 'stats'
                and not lines[i][:1].isspace()), None)
    if key is None:
        return '\n'.join(lines[:end] + ['stats:'] + item + lines[end:])
    if lines[key].split(':', 1)[1].strip():
        raise ValueError("its `stats:` is not a block list; edit it by hand")
    # The list runs over the indented lines below the key.
    after = key + 1
    while after < end and (lines[after][:1].isspace() or not lines[after].strip()):
        after += 1
    return '\n'.join(lines[:after] + item + lines[after:])


def cmd_new(args):
    name = args.name.strip()
    if not V.STAT_NAME_RE.match(name):
        V.die(f"name {name!r} must be lowercase letters, digits and '-' (e.g. run-km)")
    kind, tname, path = V.resolve_target(args.thread)
    ref = V.thread_ref(kind, tname)
    taken = V.declared_stats().get(name)
    if taken:
        V.die(f"stat {name!r} is already declared on {', '.join(sorted({s.thread for s in taken}))}")
    try:
        text = declare(V.read_or_die(path), stat_item(name, args.type, args.agg))
    except ValueError as e:
        V.die(f"cannot declare a stat in {V.full(path)}: {e}")
    path.write_text(text, encoding='utf-8')
    print(f"declared: {name} on {ref} ({args.type}, {args.agg})")
    return 0


# ---------- list ----------

def cmd_list(args):
    rows = [{'name': s.name, 'thread': s.thread, 'type': s.type, 'agg': s.agg}
            for found in V.declared_stats().values() for s in found]
    rows.sort(key=lambda r: (r['name'], r['thread']))
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    if not rows:
        print("(no stats)")
        return 0
    width = max(len(r['name']) for r in rows)
    twidth = max(len(r['thread']) for r in rows)
    print(f"{'NAME':<{width}}  {'THREAD':<{twidth}}  {'TYPE':<7}  AGG")
    for r in rows:
        print(f"{r['name']:<{width}}  {r['thread']:<{twidth}}  {r['type']:<7}  {r['agg']}")
    return 0


# ---------- log ----------

def timestamp(date_s, time_s):
    """The entry's YYYY-MM-DDTHH:MM:SS: now, unless --date or --time move it.
    A --date alone keeps the current clock, as `buffer --date` does."""
    if not date_s and not time_s:
        return B.now_ts()
    when = V.when_from_flags(date_s, time_s)
    if not time_s:
        when = datetime.combine(when.date(), datetime.now().time())
    return when.strftime('%Y-%m-%dT%H:%M:%S')


def cmd_log(args):
    ts = timestamp(args.date, args.time)
    return B.buffered(B.buffer_stat, args.name, args.value, ts)


# ---------- series ----------

def entries(stat):
    """[(ts, Decimal value, where)] for every value of `stat`: its thread's
    logs, then the unflushed buffer, in timestamp order. A value that does
    not read as the stat's type stops the command, naming the line."""
    found = []

    def take(ts, value, where):
        problem = V.stat_value_problem(stat, value)
        if problem:
            V.die(f"{where}: {problem}; fix the line (`lint` reports it)")
        found.append((ts, Decimal(value), where))

    logs = V.thread_folder(stat.thread) / 'logs'
    if logs.is_dir():
        for path in sorted(logs.glob('*.md')):
            text = V.read_utf8(path)
            if text is None:
                continue
            for i, line in enumerate(text.split('\n')):
                m = V.STAT_LINE_RE.match(line)
                if m and m['name'] == stat.name:
                    take(m['ts'], m['value'], V.where(path, i))

    buffered, _, _ = B.parse_buffer_entries(B.read_buffer())
    for e in buffered:
        if e['type'] != 'STAT' or e['thread'] != stat.thread:
            continue
        m = V.STAT_BODY_RE.match(e['body'])
        if m and m['name'] == stat.name:
            take(e['ts'], m['value'], f"{V.full(B.buffer_file())}:{e['line_no']}")

    # Stable, so two values with one timestamp keep log-then-buffer order.
    found.sort(key=lambda x: x[0])
    return found


def period_of(day, by):
    """The first day of the period `day` falls in. A week starts on Monday."""
    if by == 'week':
        return day - timedelta(days=day.weekday())
    if by == 'month':
        return day.replace(day=1)
    return day


def next_period(start, by):
    if by == 'week':
        return start + timedelta(days=7)
    if by == 'month':
        return (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return start + timedelta(days=1)


def label(start, by):
    return start.strftime('%Y-%m') if by == 'month' else start.isoformat()


def aggregate(values, agg):
    """One period's values, in timestamp order, as one number."""
    if agg == 'sum':
        return sum(values, Decimal(0))
    if agg == 'max':
        return max(values)
    return values[-1]


def series(stat, since, until, by):
    """[{period, value, entries}], one per period from `since` to `until`.
    A period with nothing logged has value None: a gap, not a zero. With no
    `since`, the series starts at the first value; with no `until`, it ends
    today, or at the last value if that is later."""
    found = [x for x in entries(stat) if V.in_window(x[0][:10], since, until)]
    days = [date.fromisoformat(ts[:10]) for ts, _, _ in found]
    first = date.fromisoformat(since) if since else (days[0] if days else None)
    if first is None:
        return []
    last = date.fromisoformat(until) if until else max([date.today(), *days])
    buckets = {}
    for (_, value, _), day in zip(found, days, strict=True):
        buckets.setdefault(period_of(day, by), []).append(value)
    out = []
    start = period_of(first, by)
    while start <= last:
        values = buckets.get(start, [])
        out.append({'period': label(start, by),
                    'value': aggregate(values, stat.agg) if values else None,
                    'entries': len(values)})
        start = next_period(start, by)
    return out


def as_number(value, stat):
    """A Decimal as the stat's type would write it, for JSON."""
    if value is None:
        return None
    return int(value) if stat.type == 'int' else float(value)


def cmd_series(args):
    if args.since and args.until and args.since > args.until:
        V.die("--since is after --until")
    try:
        stat = V.find_stat(args.name.strip())
    except ValueError as e:
        V.die(str(e))
    rows = series(stat, args.since, args.until, args.by)
    if args.json:
        print(json.dumps({'stat': stat.name, 'thread': stat.thread, 'type': stat.type,
                          'agg': stat.agg, 'by': args.by,
                          'periods': [{**r, 'value': as_number(r['value'], stat)} for r in rows]},
                         indent=2))
        return 0
    print(f"{stat.name} ({stat.thread}, {stat.type}, {stat.agg}) by {args.by}")
    if not rows:
        print("(no entries)")
        return 0
    width = max(len(r['period']) for r in rows)
    print(f"{args.by.upper():<{width}}  VALUE")
    for r in rows:
        value = '-' if r['value'] is None else format(r['value'], 'f')
        print(f"{r['period']:<{width}}  {value}")
    return 0


# ---------- main ----------

def main():
    parser = V.command_parser(
        'stats', "Log numbers against declared stats (push-ups, steps, km run, money "
                 "spent) and show them over time. " + EVENT_HELP)
    sub = V.Subcommands(parser)

    p = sub.add_parser('new', help="Declare a stat on a thread, in the thread file's frontmatter. "
                                   "Names are unique across the vault. " + EVENT_HELP)
    p.add_argument('name', help="Lowercase letters, digits and '-'. Put a unit in the name if "
                                "the name alone is unclear (run-km, spend-zar).")
    p.add_argument('--thread', required=True, help="Thread name, 'Kind/Name', or wikilink.")
    p.add_argument('--type', required=True, choices=V.STAT_TYPES,
                   help="int for whole numbers (counts, steps, events); decimal for the rest.")
    p.add_argument('--agg', required=True, choices=V.STAT_AGGS,
                   help="How `series` combines several values in one period: sum adds them, "
                        "last takes the latest, max the largest.")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser('list', help="List declared stats.")
    p.add_argument('--json', action='store_true', help="JSON output.")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser('log', help="Buffer a value of a declared stat; `buffer flush` files it in "
                                   "the stat's thread's daily log. " + EVENT_HELP)
    p.add_argument('name', help="The stat's name, from `stats list`.")
    p.add_argument('value', help="A whole number for an int stat, a number for a decimal one. "
                                 "1 records that an event happened.")
    p.add_argument('-d', '--date', help="YYYY-MM-DD (default today).")
    p.add_argument('-t', '--time', help="HH:MM (default now).")
    p.set_defaults(func=cmd_log)

    p = sub.add_parser('series', help="Show a stat's value per day, week or month, from its logs "
                                      "and the unflushed buffer. A period with nothing logged "
                                      "shows '-' (null in JSON), not 0.")
    p.add_argument('name', help="The stat's name, from `stats list`.")
    p.add_argument('--by', choices=('day', 'week', 'month'), default='day',
                   help="Period length (default day). A week starts on Monday.")
    V.add_window_flags(p)
    p.set_defaults(func=cmd_series)

    args = V.parse_command(parser)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
