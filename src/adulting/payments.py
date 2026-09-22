"""Money received, per thread, for the adulting vault.

Records live in $ADULTING_HOME/payments/<Kind>/<Thread>.md as JSON inside an
```adulting-payments fence — the same shape `hours` uses, so both are readable,
greppable, and produce clean git diffs.

  payments log <thread> <amount>       record a receipt
  payments list / show / edit / rm
  payments statement                   billed vs received, per thread

Non-interactive: every value comes from arguments, and deleting needs -y.

Unlike `hours`, there is no Obsidian plugin to be compatible with here, so the
fence is our own. Amounts are handled as Decimal throughout: these figures get
reconciled against invoices, and float drift is not acceptable in money.

Every recorded payment also drops a `REF:` into the buffer, so it appears
in the thread's daily log on the next `buffer flush`, as `notes new` and
`hours log` do, filed under the day the money was received. Best-effort: a payment is recorded whether or not the
buffer can be written.
"""

import json
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from adulting.helpjson import emit_helpjson_if_requested
from adulting import buffer as B
from adulting import vault as V
from adulting import statement as S
from adulting import statement_pdf as P

SUBDIR = 'payments'
FENCE = V.PAYMENTS_FENCE
HEADING = ' — payments'
KEY = 'payments'

# `hours` side, for the statement.
HOURS_SUBDIR = 'hours'
HOURS_FENCE = V.HOURS_FENCE


def by_received(p):
    return p.get('received') or ''


# ---------- amounts ----------

def parse_amount(raw):
    """Accept '47300', '47300.50', '47,300.50'. Reject anything else."""
    try:
        amt = Decimal(str(raw).replace(',', '').strip())
    except (InvalidOperation, AttributeError):
        V.die(f"{raw!r} is not a valid amount")
    if amt <= 0:
        V.die(f"amount must be positive (got {amt})")
    return amt


def amount_json(amt):
    """Store as a JSON number, dropping a pointless .00."""
    q = amt.quantize(Decimal('0.01'))
    return int(q) if q == q.to_integral_value() else float(q)


# ---------- records ----------

def build_payment(amount, received, currency, account, note, ids):
    p = {
        'id': V.new_id(ids),
        'received': V.to_iso(received),
        'amount': amount_json(amount),
        'currency': currency,
    }
    if account:
        p['account'] = account
    if note:
        p['note'] = note
    return p


def save(path, records, ref, currency):
    V.write_records(path, records, FENCE, ref, currency, key=KEY,
                    sort_key=by_received, heading=HEADING)


def append_payment(kind, name, payment):
    ref = V.thread_ref(kind, name)
    path = V.record_path(SUBDIR, kind, name)
    save(path, V.read_records(path, FENCE, KEY) + [payment], ref, payment['currency'])
    # A REF in the buffer puts this payment in the thread's daily log on the
    # next flush, filed under the day it was received. Best-effort and
    # silent: see buffer.add_ref. `ref` is already the directory form.
    B.add_ref(ref, f"payments/{ref}",
               f"{V.fmt_money(V.dec(payment['amount']), payment['currency'])} "
               f"received ({payment['id']})",
               date=V.local(payment['received']).strftime('%Y-%m-%d'))
    return path


def report_logged(p, ref):
    when = V.local(p['received']).strftime('%Y-%m-%d')
    acct = f"  {p['account']}" if p.get('account') else ''
    print(f"received {p['id']}  {ref}  {when}  "
          f"{V.fmt_money(V.dec(p['amount']), p['currency'])}{acct}")


# ---------- log ----------

def cmd_log(args):
    if args.amount is None:
        V.die("amount is required")

    kind, name, tpath = V.resolve_target(args.thread)
    ref = V.thread_ref(kind, name)
    currency = V.resolve_currency(tpath, ref, args.currency)
    amount = parse_amount(args.amount)
    received = V.when_from_flags(args.date, args.time)

    p = build_payment(amount, received, currency, args.account,
                      ' '.join(args.note).strip() if args.note else '', V.all_ids())
    append_payment(kind, name, p)
    report_logged(p, ref)
    return 0


# ---------- query ----------

def collect(thread=None, since=None, until=None):
    want = None
    if thread:
        kind, name, _ = V.resolve_target(thread)
        want = V.thread_ref(kind, name)
    for path, ref, p in V.load_all(SUBDIR, FENCE, KEY):
        if want and ref != want:
            continue
        if not p.get('received'):
            continue
        day = V.local(p['received']).strftime('%Y-%m-%d')
        if not V.in_window(day, since, until):
            continue
        yield path, ref, p


def as_row(ref, p):
    return {
        'id': p.get('id', ''),
        'thread': ref,
        'received': V.local(p['received']).strftime('%Y-%m-%d'),
        'amount': V.dec(p.get('amount', 0)),
        'currency': p.get('currency', ''),
        'account': p.get('account', ''),
        'note': p.get('note', ''),
    }


def as_output(row):
    """A row as `--json` and `show` print it: the amount as a plain number.
    Rows keep the Decimal until this point, so text output rounds exactly."""
    return {**row, 'amount': float(row['amount'])}


def cmd_list(args):
    rows = [as_row(ref, p) for _, ref, p in
            collect(args.thread, args.since, args.until)]
    rows.sort(key=lambda r: (r['received'], r['thread']))
    if args.json:
        print(json.dumps([as_output(r) for r in rows], indent=2))
        return 0
    if not rows:
        print("(no payments)")
        return 0
    tw = max(len(r['thread']) for r in rows)
    aw = max(len(r['account']) for r in rows) or 1
    print(f"{'ID':<9} {'RECEIVED':<11} {'THREAD':<{tw}}  {'AMOUNT':>16}  "
          f"{'ACCOUNT':<{aw}}  NOTE")
    for r in rows:
        print(f"{r['id']:<9} {r['received']:<11} {r['thread']:<{tw}}  "
              f"{V.fmt_money(r['amount'], r['currency']):>16}  "
              f"{r['account']:<{aw}}  {r['note']}")
    return 0


def find_payment(pid):
    for path, ref, p in V.load_all(SUBDIR, FENCE, KEY):
        if p.get('id') == pid:
            return path, ref, p
    V.die(f"no payment with id {pid!r}")


def cmd_show(args):
    _, ref, p = find_payment(args.id)
    row = as_output(as_row(ref, p))
    if args.json:
        print(json.dumps(row, indent=2))
        return 0
    for k in ('id', 'thread', 'received', 'amount', 'currency', 'account', 'note'):
        print(f"{k:<10} {row[k]}")
    return 0


def cmd_edit(args):
    path, ref, _ = find_payment(args.id)
    records = V.read_records(path, FENCE, KEY)
    target = next(p for p in records if p.get('id') == args.id)

    if args.amount is not None:
        target['amount'] = amount_json(parse_amount(args.amount))
    if args.currency is not None:
        ccy = args.currency.upper()
        if not V.is_currency_code(ccy):
            V.die(f"currency {ccy!r} is not a 3-letter ISO code")
        target['currency'] = ccy
    if args.account is not None:
        target['account'] = args.account
    if args.note is not None:
        target['note'] = ' '.join(args.note).strip()
    if args.date or args.time:
        # Whichever of date and time is not given keeps its current value,
        # as `hours edit` does.
        was = V.local(target['received'])
        target['received'] = V.to_iso(V.when_from_flags(
            args.date or was.strftime('%Y-%m-%d'),
            args.time or was.strftime('%H:%M')))

    save(path, records, ref, None)  # the file exists; its frontmatter is kept
    report_logged(target, ref)
    return 0


def cmd_rm(args):
    path, ref, _ = find_payment(args.id)
    if not args.yes:
        V.die(f"refusing to delete {args.id} without -y")
    records = [x for x in V.read_records(path, FENCE, KEY) if x.get('id') != args.id]
    save(path, records, ref, None)  # the file exists; its frontmatter is kept
    print(f"deleted {args.id}")
    return 0


# ---------- statement ----------

def billed(thread=None, since=None, until=None):
    """Sum the `hours` side, each entry rounded to the cent as the statement
    and `hours report` do, so all three agree exactly."""
    out = {}
    want = None
    if thread:
        kind, name, _ = V.resolve_target(thread)
        want = V.thread_ref(kind, name)
    for _, ref, e in V.load_all(HOURS_SUBDIR, HOURS_FENCE):
        if want and ref != want:
            continue
        if not e.get('startTime') or not e.get('endTime'):
            continue
        # Unbilled time carries no currency and can never be charged for, so
        # it has no place on a statement of account.
        if not e.get('currency'):
            continue
        day = V.local(e['startTime']).strftime('%Y-%m-%d')
        if not V.in_window(day, since, until):
            continue
        mins = V.minutes_of(e)
        amt = S.charge_of(mins, e.get('rate', 0) or 0)
        out.setdefault((ref, e.get('currency', '')), V.dec(0))
        out[(ref, e.get('currency', ''))] += amt
    return out


def _as_of(raw):
    if not raw:
        return date.today()
    try:
        return datetime.strptime(raw, '%Y-%m-%d').date()
    except ValueError:
        V.die(f"bad --as-of {raw!r}; expected YYYY-MM-DD")


def one_thread_statement(thread_arg, as_of):
    """The statement for one thread, built by `statement.build`."""
    kind, name, tpath = V.resolve_target(thread_arg)
    ref = V.thread_ref(kind, name)
    currency = V.resolve_currency(tpath, ref, None)

    entries = []
    for _, r, e in V.load_all(HOURS_SUBDIR, HOURS_FENCE):
        if r != ref or not e.get('startTime') or not e.get('endTime'):
            continue
        # Only time billed in the statement's currency is charged. Unbilled
        # time has no currency, and time billed in another currency belongs
        # on a statement in that currency, as the text statement has it.
        if e.get('currency') != currency:
            continue
        mins = V.minutes_of(e)
        entries.append({'on': V.local(e['startTime']).date(),
                        'description': e.get('name', ''),
                        'minutes': mins,
                        'rate': e.get('rate', 0) or 0})

    paid = []
    for _, r, pm in V.load_all(SUBDIR, FENCE, KEY):
        if r != ref or not pm.get('received'):
            continue
        paid.append({'on': V.local(pm['received']).date(),
                     'amount': V.cents(pm.get('amount', 0)),
                     'account': pm.get('account', '')})

    st = S.build(ref, currency, entries, paid, as_of)
    st['thread_path'] = tpath
    return st


def cmd_pdf(args):
    """A statement document is per client, so --pdf needs exactly one thread."""
    st = one_thread_statement(args.thread, _as_of(args.as_of))
    if not st['lines']:
        V.die(f"nothing to state for {st['thread']!r} as at {st['as_of']}")
    out, bank = P.render(st, args.pdf)
    if not bank['complete']:
        sys.stdout.flush()
        V.warn("banking details incomplete in .adulting/config.yaml — "
               "the statement says so instead of printing a payment table")
    print(f"{out}: {len(st['lines'])} lines, {st['hours_total']:.2f} h, "
          f"charges {V.fmt_money(st['charges'], st['currency'])}, "
          f"paid {V.fmt_money(st['payments'], st['currency'])}, "
          f"balance {V.fmt_money(st['balance'], st['currency'])} "
          f"as at {st['as_of']}")
    return 0


def cmd_statement(args):
    if args.pdf:
        if not args.thread:
            V.die("--pdf needs --thread; a statement is per client")
        return cmd_pdf(args)
    # --as-of is an upper bound on the text view too, so the two agree.
    # Validate it first: a malformed date compared as a string bounds nothing.
    if args.as_of:
        _as_of(args.as_of)
    until = args.until or (args.as_of if args.as_of else None)
    bill = billed(args.thread, args.since, until)
    recv = {}
    for _, ref, p in collect(args.thread, args.since, until):
        key = (ref, p.get('currency', ''))
        recv.setdefault(key, V.dec(0))
        recv[key] += V.cents(p.get('amount', 0))

    rows = []
    for key in sorted(set(bill) | set(recv)):
        ref, ccy = key
        b, r = bill.get(key, V.dec(0)), recv.get(key, V.dec(0))
        rows.append({'thread': ref, 'currency': ccy,
                     'billed': b, 'received': r, 'outstanding': b - r})

    if args.json:
        print(json.dumps([{**x, 'billed': float(x['billed']),
                           'received': float(x['received']),
                           'outstanding': float(x['outstanding'])}
                          for x in rows], indent=2))
        return 0
    if not rows:
        print("(nothing to report)")
        return 0
    tw = max(len(x['thread']) for x in rows)
    print(f"{'THREAD':<{tw}}  {'BILLED':>16}  {'RECEIVED':>16}  {'OUTSTANDING':>16}")
    for x in rows:
        print(f"{x['thread']:<{tw}}  "
              f"{V.fmt_money(x['billed'], x['currency']):>16}  "
              f"{V.fmt_money(x['received'], x['currency']):>16}  "
              f"{V.fmt_money(x['outstanding'], x['currency']):>16}")
    per_ccy = {}
    for x in rows:
        t = per_ccy.setdefault(x['currency'], {'b': V.dec(0), 'r': V.dec(0)})
        t['b'] += x['billed']
        t['r'] += x['received']
    print()
    for ccy, t in sorted(per_ccy.items()):
        print(f"{'TOTAL ' + ccy:<{tw}}  {V.fmt_money(t['b'], ccy):>16}  "
              f"{V.fmt_money(t['r'], ccy):>16}  "
              f"{V.fmt_money(t['b'] - t['r'], ccy):>16}")
    return 0


# ---------- main ----------

def main():
    parser = V.command_parser(
        'payments', "Record money received against threads.")
    sub = parser.add_subparsers(dest='subcommand', required=True)

    log = sub.add_parser('log', help="Record a receipt.")
    log.add_argument('thread', help="Thread name, 'Kind/Name', or wikilink.")
    log.add_argument('amount', nargs='?', help="Amount received.")
    log.add_argument('-c', '--currency', help="ISO code; defaults to the thread's.")
    log.add_argument('-d', '--date', help="Date received, YYYY-MM-DD (default today).")
    log.add_argument('-t', '--time', help="HH:MM (default now).")
    log.add_argument('-a', '--account', help="Which account it landed in.")
    log.add_argument('-n', '--note', nargs='*', help="Free-text note.")
    log.set_defaults(func=cmd_log)

    ls = sub.add_parser('list', help="List payments.")
    ls.add_argument('thread', nargs='?', help="Only this thread: name, 'Kind/Name', or wikilink.")
    V.add_window_flags(ls)
    ls.set_defaults(func=cmd_list)

    st = sub.add_parser('statement', help="Billed vs received, by thread and currency.")
    st.add_argument('--thread', help="Only this thread: name, 'Kind/Name', or wikilink.")
    V.add_window_flags(st)
    st.add_argument('--as-of', help="Statement date, YYYY-MM-DD; drives aging (default: today).")
    st.add_argument('--pdf', help="Render a PDF to this path. Requires --thread.")
    st.set_defaults(func=cmd_statement)

    sh = sub.add_parser('show', help="Show one payment.")
    sh.add_argument('id', help="The payment's 8-character id, from `payments list`.")
    sh.add_argument('--json', action='store_true', help='JSON output.')
    sh.set_defaults(func=cmd_show)

    ed = sub.add_parser('edit', help="Change one field of a payment.")
    ed.add_argument('id', help="The payment's 8-character id, from `payments list`.")
    ed.add_argument('--amount', help="New amount received.")
    ed.add_argument('-c', '--currency', help="New ISO currency code.")
    ed.add_argument('-d', '--date', help="New date received, YYYY-MM-DD.")
    ed.add_argument('-t', '--time', help="New time received, HH:MM.")
    ed.add_argument('-a', '--account', help="New account it landed in.")
    ed.add_argument('-n', '--note', nargs='*', help="New free-text note.")
    ed.set_defaults(func=cmd_edit)

    rm = sub.add_parser('rm', help="Delete a payment.")
    rm.add_argument('id', help="The payment's 8-character id, from `payments list`.")
    rm.add_argument('-y', '--yes', action='store_true',
                    help="Required: confirms the permanent delete.")
    rm.set_defaults(func=cmd_rm)

    emit_helpjson_if_requested(parser)
    args = parser.parse_args()
    V.require_vault()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
