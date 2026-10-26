"""Statement of account: charges, payments, running balance, aging.

Reads nothing itself — callers hand it entries and payments already collected
from the thread's `hours.md` and `payments.md`. Money is Decimal throughout, never float, and
charges land on whole cents at the line so the printed lines always sum to the
printed total.

Ported from a standalone renderer that read the retired task_logging CSVs. The
arithmetic and its self-checks are that code's; the shape follows this repo —
plain functions over dicts, no annotations, `vault.die` on bad data.
"""

from datetime import timedelta
from decimal import Decimal

from adulting import vault as V

AGING_BUCKETS = ('current', '30', '60', '90+')


# ---------- line construction ----------

def hours_of(minutes):
    """Whole hundredths of an hour at the line, so the printed lines sum to
    the printed total, as they do for money."""
    return (Decimal(minutes) / Decimal(60)).quantize(V.CENT)


def charge_of(minutes, rate):
    """Whole cents at the line, so printed lines sum to the printed total."""
    return (Decimal(minutes) / Decimal(60) * Decimal(rate)).quantize(V.CENT)


def running(entries, payments, opening=Decimal('0.00')):
    """Charges and payments merged into one chronological run of the balance,
    starting from `opening`.

    Entries are dicts with `on` (date), `description`, `minutes`, `rate`;
    payments with `on`, `amount`, `account`.
    """
    events = (
        # Sort key puts a charge before a payment on the same day, so a payment
        # always settles a balance that already includes that day's work.
        [(e['on'], 0, e) for e in entries] +
        [(p['on'], 1, p) for p in payments]
    )
    events.sort(key=lambda ev: (ev[0], ev[1]))

    lines = []
    balance = opening
    for on, kind, event in events:
        if kind == 0:
            amount = charge_of(event['minutes'], event['rate'])
            balance += amount
            lines.append({
                'on': on,
                'description': event['description'],
                'hours': hours_of(event['minutes']),
                'rate': Decimal(event['rate']),
                'charge': amount,
                'payment': None,
                'balance': balance,
            })
        else:
            balance -= Decimal(event['amount'])
            account = event.get('account') or ''
            label = f"Payment received — {account}" if account else "Payment received"
            lines.append({
                'on': on,
                'description': label,
                'hours': None,
                'rate': None,
                'charge': None,
                'payment': Decimal(event['amount']),
                'balance': balance,
            })
    return lines


# ---------- aging ----------

def aging(entries, payments, as_of):
    """Age the unpaid balance by charge date, settling oldest charges first."""
    buckets = {b: Decimal('0.00') for b in AGING_BUCKETS}
    unapplied = sum((Decimal(p['amount']) for p in payments), Decimal('0.00'))

    for entry in sorted(entries, key=lambda e: e['on']):
        outstanding = charge_of(entry['minutes'], entry['rate'])
        applied = min(unapplied, outstanding)
        outstanding -= applied
        unapplied -= applied
        if outstanding == 0:
            continue
        days = (as_of - entry['on']).days
        if days < 30:
            bucket = 'current'
        elif days < 60:
            bucket = '30'
        elif days < 90:
            bucket = '60'
        else:
            bucket = '90+'
        buckets[bucket] += outstanding

    # Paid more than is owed: the excess is an unapplied credit, not an aged
    # debt. It shows as a negative in `current` so the buckets still sum to the
    # balance rather than silently disagreeing with it.
    buckets['current'] -= unapplied
    return buckets


# ---------- assembly ----------

def brought_forward(opening, balance):
    """The one line that stands for everything before `opening`."""
    return {
        'on': opening - timedelta(days=1),
        'description': 'Balance brought forward',
        'hours': None,
        'rate': None,
        'charge': None,
        'payment': None,
        'balance': balance,
        'brought_forward': True,
    }


def build(thread, currency, entries, payments, as_of, opening=None):
    """Assemble the statement. `as_of` is a date; `entries`/`payments` are the
    dicts described in `running`.

    `opening`, a date, compacts the view only: records before it become one
    brought-forward line, and the figures are the period's from there on. The
    balance due and the aging are the same with or without it."""
    # A statement is the account AS IT STOOD on `as_of`: work logged after that
    # date has not happened yet as far as this document is concerned. Without
    # this, `--as-of` ages future charges into `current` and overstates the debt.
    entries = [e for e in entries if e['on'] <= as_of]
    payments = [p for p in payments if p['on'] <= as_of]

    # Aging sees the whole account; only the ledger and its totals are cut.
    all_entries, all_payments = entries, payments
    forward = Decimal('0.00')
    if opening:
        forward = (sum((charge_of(e['minutes'], e['rate']) for e in entries
                        if e['on'] < opening), Decimal('0.00'))
                   - sum((Decimal(p['amount']) for p in payments
                          if p['on'] < opening), Decimal('0.00')))
        entries = [e for e in entries if e['on'] >= opening]
        payments = [p for p in payments if p['on'] >= opening]

    lines = running(entries, payments, forward)
    if opening:
        lines.insert(0, brought_forward(opening, forward))
    charges = sum((charge_of(e['minutes'], e['rate']) for e in entries), Decimal('0.00'))
    paid = sum((Decimal(p['amount']) for p in payments), Decimal('0.00'))
    minutes = sum(e['minutes'] for e in entries)
    billable = sum(e['minutes'] for e in entries if Decimal(e['rate']) > 0)

    statement = {
        'thread': thread,
        'currency': currency,
        'as_of': as_of,
        'opening': opening,
        'lines': lines,
        'brought_forward': forward,
        'charges': charges,
        'payments': paid,
        'balance': forward + charges - paid,
        'minutes_total': minutes,
        'minutes_billable': billable,
        'minutes_written_off': minutes - billable,
        # Rounded per line, as charges are, so the printed column adds up.
        'hours_total': sum((hours_of(e['minutes']) for e in entries), Decimal('0.00')),
        'hours_billable': sum((hours_of(e['minutes']) for e in entries
                               if Decimal(e['rate']) > 0), Decimal('0.00')),
        'hours_written_off': sum((hours_of(e['minutes']) for e in entries
                                  if Decimal(e['rate']) <= 0), Decimal('0.00')),
        'aging': aging(all_entries, all_payments, as_of),
    }
    check(statement)
    return statement


def check(statement):
    """Arithmetic that must hold, asserted where it is cheap to assert.

    These are data-integrity guards, not user errors -- but a wrong statement
    asks a client for the wrong money, so failing loudly beats printing it.
    """
    lines = statement['lines']
    if lines and lines[-1]['balance'] != statement['balance']:
        V.die(f"statement check failed: closing line {lines[-1]['balance']} "
              f"!= balance {statement['balance']}")
    aged = sum(statement['aging'].values(), Decimal('0.00'))
    if aged != statement['balance']:
        V.die(f"statement check failed: aging {aged} != balance {statement['balance']}")
    charged = sum((ln['charge'] or Decimal('0.00') for ln in lines), Decimal('0.00'))
    if charged != statement['charges']:
        V.die(f"statement check failed: lines charge {charged} != charges {statement['charges']}")
    received = sum((ln['payment'] or Decimal('0.00') for ln in lines), Decimal('0.00'))
    if received != statement['payments']:
        V.die(f"statement check failed: lines payment {received} "
              f"!= payments {statement['payments']}")
    worked = sum((ln['hours'] or Decimal('0.00') for ln in lines), Decimal('0.00'))
    if worked != statement['hours_total']:
        V.die(f"statement check failed: lines hours {worked} "
              f"!= hours {statement['hours_total']}")
    forward = statement.get('brought_forward', Decimal('0.00'))
    if forward + statement['charges'] - statement['payments'] != statement['balance']:
        V.die(f"statement check failed: brought forward {forward} + charges "
              f"{statement['charges']} - payments {statement['payments']} "
              f"!= balance {statement['balance']}")
