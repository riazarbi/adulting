"""Statement of account: charges, payments, running balance, aging.

Reads nothing itself — callers hand it entries and payments already collected
from `hours/` and `payments/`. Money is Decimal throughout, never float, and
charges land on whole cents at the line so the printed lines always sum to the
printed total.

Ported from a standalone renderer that read the retired task_logging CSVs. The
arithmetic and its self-checks are that code's; the shape follows this repo —
plain functions over dicts, no annotations, `sys.exit` on bad data.
"""

import sys
from decimal import Decimal

CENT = Decimal('0.01')
AGING_BUCKETS = ('current', '30', '60', '90+')


# ---------- line construction ----------

def charge_of(minutes, rate):
    """Whole cents at the line, so printed lines sum to the printed total."""
    return (Decimal(minutes) / Decimal(60) * Decimal(rate)).quantize(CENT)


def running(entries, payments):
    """Charges and payments merged into one chronological run of the balance.

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
    balance = Decimal('0.00')
    for on, kind, event in events:
        if kind == 0:
            amount = charge_of(event['minutes'], event['rate'])
            balance += amount
            lines.append({
                'on': on,
                'description': event['description'],
                'hours': Decimal(event['minutes']) / Decimal(60),
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

def build(thread, currency, entries, payments, as_of):
    """Assemble the statement. `as_of` is a date; `entries`/`payments` are the
    dicts described in `running`."""
    # A statement is the account AS IT STOOD on `as_of`: work logged after that
    # date has not happened yet as far as this document is concerned. Without
    # this, `--as-of` ages future charges into `current` and overstates the debt.
    entries = [e for e in entries if e['on'] <= as_of]
    payments = [p for p in payments if p['on'] <= as_of]

    lines = running(entries, payments)
    charges = sum((charge_of(e['minutes'], e['rate']) for e in entries), Decimal('0.00'))
    paid = sum((Decimal(p['amount']) for p in payments), Decimal('0.00'))
    minutes = sum(e['minutes'] for e in entries)
    billable = sum(e['minutes'] for e in entries if Decimal(e['rate']) > 0)

    statement = {
        'thread': thread,
        'currency': currency,
        'as_of': as_of,
        'lines': lines,
        'charges': charges,
        'payments': paid,
        'balance': charges - paid,
        'minutes_total': minutes,
        'minutes_billable': billable,
        'minutes_written_off': minutes - billable,
        'hours_total': Decimal(minutes) / Decimal(60),
        'hours_billable': Decimal(billable) / Decimal(60),
        'hours_written_off': Decimal(minutes - billable) / Decimal(60),
        'aging': aging(entries, payments, as_of),
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
        sys.exit(f"statement: closing line {lines[-1]['balance']} "
                 f"!= balance {statement['balance']}")
    aged = sum(statement['aging'].values(), Decimal('0.00'))
    if aged != statement['balance']:
        sys.exit(f"statement: aging {aged} != balance {statement['balance']}")
    charged = sum((ln['charge'] or Decimal('0.00') for ln in lines), Decimal('0.00'))
    if charged != statement['charges']:
        sys.exit(f"statement: lines charge {charged} != charges {statement['charges']}")
