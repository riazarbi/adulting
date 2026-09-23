"""Time tracking for the adulting vault, billable and not.

Entries live in $ADULTING_HOME/hours/<Kind>/<Thread>.md as JSON inside a
```simple-time-tracker fence, so Obsidian's Super Simple Time Tracker plugin
(and anything that reads its format) can render them natively.

  hours log <thread> <description...>   append an entry
  hours list / report / show / edit / rm

Non-interactive: every value comes from arguments, and deleting needs -y.

The entry `name` field holds the description: it is the only field the plugin
renders, and these descriptions are invoice line items. Extra keys (id, rate,
currency) ride alongside; the plugin round-trips unknown keys unharmed because
loadTracker() casts rather than maps.

Money is an overlay on time, not a precondition for recording it. A thread
carrying a `currency` is billable: entries take its rate and are costed. A
thread with no currency is not: its entries are written with rate 0 and no
currency at all, `hours report` totals their duration under an `unbilled`
row, and `payments statement` ignores them. So personal threads -- reading,
exercise, admin -- can be tracked in the same place as client work without
inventing a currency for them.

Rate 0 means unbillable and is an ordinary value -- hours still count.
Asking for a rate with no currency to express it in is the one refused
combination.

Every logged entry also drops a `REF:` into the buffer, so it appears in the
thread's daily log on the next `buffer flush` -- the same thing `notes new`
has always done. The pointer is filed under the day the work happened, not
the day of the flush, so a backdated entry lands in the right day's log. That
keeps the log a complete chronology of the thread rather than one that
silently omits time. Best-effort: if the buffer cannot
be written the entry is still recorded, and nothing is reported, because a
warning on stderr would cost the caller its stdout.
"""

import json
import sys
from datetime import timedelta

from adulting import buffer as B
from adulting import statement as S
from adulting import vault as V

STORE = V.HOURS

DEFAULT_MINUTES = 60
DEFAULT_RATE = 2500


# ---------- entries ----------

def rate_of(e):
    """An entry's rate. Every entry carries one: `hours log` writes 0 for
    unbilled time, so a missing or unreadable rate is an error."""
    return V.as_int(e.get('rate'), f"rate of entry {e.get('id')!r}")


def money_of(e):
    """Decimal, not float: these figures get invoiced. Rounded to the cent
    per entry, as the statement does, so every total is a sum of the lines."""
    return S.charge_of(V.minutes_of(e), rate_of(e))


def resolve_rate(tpath, flag):
    if flag is not None:
        return int(flag)
    thread_rate = V.thread_meta(tpath)[1]
    if thread_rate is not None:
        return thread_rate
    return V.config_default('hours', 'rate', DEFAULT_RATE)


def resolve_billing(tpath, currency_flag, rate_flag):
    """Return (currency, rate). A thread with no currency is not billable.

    `hours` records time; money is an overlay. Where no currency is available
    the entry is unbilled: currency None, rate 0. Asking for a rate without a
    currency is the one incoherent combination, and it is an error rather
    than a guess. This is deliberately NOT V.resolve_currency, which stays
    strict for `payments` — money received must name its currency.
    """
    currency = currency_flag or V.thread_meta(tpath)[0]
    if not currency:
        if rate_flag is not None and int(rate_flag) != 0:
            V.die("--rate needs a currency\n"
                  "  pass --currency, or set `currency:` on the thread; "
                  "omit --rate to log the time as unbilled")
        return None, 0
    return V.check_currency(currency), resolve_rate(tpath, rate_flag)


def build_entry(desc, when, minutes, rate, currency, ids):
    entry = {
        'name': desc,
        'startTime': V.to_iso(when),
        'endTime': V.to_iso(when + timedelta(minutes=minutes)),
        'id': V.new_id(ids),
        'rate': int(rate),
    }
    # Omitted rather than null for unbilled time: the key's absence is the
    # signal, and a null reads as a currency somebody forgot to fill in.
    if currency:
        entry['currency'] = currency
    return entry


def append_entry(kind, name, entry):
    ref = V.thread_ref(kind, name)
    path = STORE.path(kind, name)
    STORE.save(path, STORE.read(path) + [entry], ref, entry.get('currency'))
    # A REF in the buffer puts this entry in the thread's daily log on the
    # next flush, filed under the day the work happened. Best-effort and
    # silent: see buffer.add_ref. `ref` is already the directory form
    # (Processes/SGB); `kind` is the frontmatter form and is not a path.
    B.add_ref(ref, f"hours/{ref}",
               f"{V.fmt_duration(V.minutes_of(entry))} {entry['name']} "
               f"({entry['id']})",
               date=V.local(entry['startTime'], STORE.stamp_name(entry)).strftime('%Y-%m-%d'))
    return path


def report_logged(entry, ref):
    when = V.local(entry['startTime'], STORE.stamp_name(entry)).strftime('%Y-%m-%d %H:%M')
    if entry.get('currency'):
        tail = (f"@ {entry['rate']} {entry['currency']} = "
                f"{V.fmt_money(money_of(entry), entry['currency'])}")
    else:
        tail = "unbilled"
    print(f"logged {entry['id']}  {ref}  {when}  "
          f"{V.fmt_duration(V.minutes_of(entry))} {tail}")


# ---------- log ----------

def cmd_log(args):
    desc = ' '.join(args.description).strip()
    if not desc:
        V.die("empty description")

    kind, name, tpath = V.resolve_target(args.thread)
    ref = V.thread_ref(kind, name)
    currency, rate = resolve_billing(tpath, args.currency, args.rate)
    minutes = args.minutes if args.minutes is not None else V.config_default(
        'hours', 'minutes', DEFAULT_MINUTES)
    if minutes <= 0:
        V.die("--minutes must be positive")

    entry = build_entry(desc, V.when_from_flags(args.date, args.time),
                        minutes, rate, currency, V.all_ids())
    append_entry(kind, name, entry)
    report_logged(entry, ref)
    return 0


# ---------- query ----------

def as_row(ref, e):
    return {
        'id': e.get('id', ''),
        'thread': ref,
        'date': V.local(e['startTime'], STORE.stamp_name(e)).strftime('%Y-%m-%d'),
        'time': V.local(e['startTime'], STORE.stamp_name(e)).strftime('%H:%M'),
        'minutes': V.minutes_of(e),
        'rate': rate_of(e),
        'currency': e.get('currency', ''),
        'amount': money_of(e),
        'description': e.get('name', ''),
    }


def cmd_list(args):
    rows = [as_row(ref, e) for _, ref, e in
            STORE.collect(args.thread, args.since, args.until)]
    rows.sort(key=lambda r: (r['date'], r['time']))
    if args.json:
        print(json.dumps([V.as_output(r) for r in rows], indent=2))
        return 0
    if not rows:
        print("(no entries)")
        return 0
    tw = max(len(r['thread']) for r in rows)
    print(f"{'ID':<9} {'DATE':<11} {'THREAD':<{tw}}  {'DUR':>7}  {'AMOUNT':>14}  DESCRIPTION")
    for r in rows:
        print(f"{r['id']:<9} {r['date']:<11} {r['thread']:<{tw}}  "
              f"{V.fmt_duration(r['minutes']):>7}  "
              f"{V.fmt_money(r['amount'], r['currency']):>14}  {r['description']}")
    return 0


def cmd_report(args):
    buckets = {}
    for _, ref, e in STORE.collect(args.thread, args.since, args.until):
        key = (ref, e.get('currency', ''))
        b = buckets.setdefault(key, {'thread': ref, 'currency': key[1],
                                     'minutes': 0, 'amount': V.dec(0), 'entries': 0})
        b['minutes'] += V.minutes_of(e)
        b['amount'] += money_of(e)
        b['entries'] += 1
    out = sorted(buckets.values(),
                 key=lambda b: (b['thread'], b['currency'] or ''))
    if args.json:
        print(json.dumps([{**b, 'amount': float(b['amount']),
                           'hours': round(b['minutes'] / 60, 2)} for b in out], indent=2))
        return 0
    if not out:
        print("(no entries)")
        return 0
    tw = max(len(b['thread']) for b in out)
    print(f"{'THREAD':<{tw}}  {'ENTRIES':>7}  {'DURATION':>10}  {'AMOUNT':>16}")
    for b in out:
        print(f"{b['thread']:<{tw}}  {b['entries']:>7}  "
              f"{V.fmt_duration(b['minutes']):>10}  "
              f"{V.fmt_money(b['amount'], b['currency']):>16}")
    # Totals are per-currency only: summing across currencies is meaningless.
    per_ccy = {}
    for b in out:
        t = per_ccy.setdefault(b['currency'], {'minutes': 0, 'amount': V.dec(0)})
        t['minutes'] += b['minutes']
        t['amount'] += b['amount']
    print()
    # Unbilled time has no currency to total against, so it gets its own row
    # rather than being folded into a money bucket or dropped.
    for ccy, t in sorted(per_ccy.items(), key=lambda kv: kv[0] or ''):
        label = ('TOTAL ' + ccy) if ccy else 'TOTAL unbilled'
        print(f"{label:<{tw}}  {'':>7}  {V.fmt_duration(t['minutes']):>10}  "
              f"{V.fmt_money(t['amount'], ccy):>16}")
    return 0


def cmd_show(args):
    _, ref, _, e = STORE.find(args.id)
    row = V.as_output(as_row(ref, e))
    if args.json:
        print(json.dumps(row, indent=2))
        return 0
    for k in ('id', 'thread', 'date', 'time', 'minutes', 'rate', 'currency',
              'amount', 'description'):
        print(f"{k:<12} {row[k]}")
    return 0


def cmd_edit(args):
    path, ref, entries, target = STORE.find(args.id)

    if args.description is not None:
        target['name'] = ' '.join(args.description).strip()
        if not target['name']:
            V.die("empty description")
    if args.rate is not None:
        target['rate'] = int(args.rate)
    if args.currency is not None:
        target['currency'] = V.check_currency(args.currency)
    # As in `log`: a rate is money, and money needs a currency. The entry
    # may have been broken before this edit, so say which field is at fault.
    if target.get('rate') and not target.get('currency'):
        if args.rate is not None:
            V.die("--rate needs a currency; pass --currency as well")
        V.die(f"entry {args.id} has a rate but no currency; "
              f"pass --currency, or --rate 0 to leave it unbilled")

    if args.date or args.time:
        start = V.local(target['startTime'], STORE.stamp_name(target))
        mins = V.minutes_of(target)
        when = V.when_from_flags(args.date or start.strftime('%Y-%m-%d'),
                                 args.time or start.strftime('%H:%M'))
        target['startTime'] = V.to_iso(when)
        target['endTime'] = V.to_iso(when + timedelta(minutes=mins))
    if args.minutes is not None:
        if args.minutes <= 0:
            V.die("--minutes must be positive")
        target['endTime'] = V.to_iso(
            V.from_iso(target['startTime']) + timedelta(minutes=args.minutes))

    STORE.save(path, entries, ref, None)  # the file exists; its frontmatter is kept
    report_logged(target, ref)
    return 0


# ---------- main ----------

def main():
    parser = V.command_parser(
        'hours', "Track consulting hours in the adulting vault.")
    sub = parser.add_subparsers(dest='subcommand')

    p = sub.add_parser('log', help="Append an entry.")
    p.add_argument('thread', help="Thread name, 'Kind/Name', or wikilink.")
    p.add_argument('description', nargs='*', help="What was done.")
    p.add_argument('-m', '--minutes', type=int, help="Duration (default 60).")
    p.add_argument('-r', '--rate', type=int, help="Hourly rate; 0 = unbillable.")
    p.add_argument('-c', '--currency',
                     help="ISO code; defaults to the thread's. Without either, "
                          "the entry is recorded as unbilled.")
    p.add_argument('-d', '--date', help="YYYY-MM-DD (default today).")
    p.add_argument('-t', '--time', help="HH:MM (default now).")
    p.set_defaults(func=cmd_log)

    p = sub.add_parser('list', help="List entries.")
    p.add_argument('thread', nargs='?', help="Only this thread: name, 'Kind/Name', or wikilink.")
    V.add_window_flags(p)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser('report',
                         help="Totals by thread and currency, with unbilled "
                              "time totalled separately.")
    p.add_argument('--thread', help="Only this thread: name, 'Kind/Name', or wikilink.")
    V.add_window_flags(p)
    p.set_defaults(func=cmd_report)

    p = sub.add_parser('show', help="Show one entry.")
    p.add_argument('id', help="The entry's 8-character id, from `hours list`.")
    p.add_argument('--json', action='store_true', help='JSON output.')
    p.set_defaults(func=cmd_show)

    p = sub.add_parser('edit', help="Change one field of an entry.")
    p.add_argument('id', help="The entry's 8-character id, from `hours list`.")
    p.add_argument('--description', nargs='*', help="New description.")
    p.add_argument('-m', '--minutes', type=int,
                    help="New duration; the start stays where it is.")
    p.add_argument('-r', '--rate', type=int, help="New hourly rate; needs a currency.")
    p.add_argument('-c', '--currency', help="New ISO currency code.")
    p.add_argument('-d', '--date', help="Move to this day, YYYY-MM-DD; the duration is kept.")
    p.add_argument('-t', '--time', help="Move to this start time, HH:MM; the duration is kept.")
    p.set_defaults(func=cmd_edit)

    p = sub.add_parser('rm', help="Delete an entry.")
    p.add_argument('id', help="The entry's 8-character id, from `hours list`.")
    p.add_argument('-y', '--yes', action='store_true',
                    help="Required: confirms the permanent delete.")
    p.set_defaults(func=STORE.cmd_rm)

    args = V.parse_command(parser)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
