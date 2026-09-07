"""Render a statement of account to PDF via pandoc + xelatex.

Same toolchain `notes pdf` uses, so this adds no dependency: the repo already
requires pandoc and a LaTeX engine, and nothing here needs a pip install.

Layout only -- every figure arrives precomputed from `_statement.build`.

A note on the table separator rows below: pandoc only gives a pipe table
full-width relative columns (`\linewidth * \real{...}`) when the source row is
wider than its `--columns` threshold, which defaults to 72. A short separator
row yields a natural-width `tabular` that renders squashed and centred instead.
So the separator rows are deliberately padded past 72 characters, and their
relative lengths are the column proportions -- they are the layout, not noise.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

import _vault as V

CENT = Decimal('0.01')


def money(amount, currency):
    """Thousands-separated, always two decimals: this is a money document."""
    q = Decimal(amount).quantize(CENT)
    neg = q < 0
    body = f"{abs(q):,.2f}"
    return f"{currency} ({body})" if neg else f"{currency} {body}"


def esc(text):
    """Escape the pandoc-markdown metacharacters that show up in descriptions.

    Descriptions are free text written months ago; a stray `*` or `_` silently
    italicising half an invoice line is the failure this prevents. Pipes must
    go too -- they would split a table cell.
    """
    out = str(text or '')
    for ch in ('\\', '|', '*', '_', '[', ']', '<', '>', '#', '`', '~', '^'):
        out = out.replace(ch, '\\' + ch)
    return out.replace('\n', ' ')


def party_lines(party):
    rows = [esc(party.get('name', ''))]
    rows += [esc(x) for x in party.get('lines', [])]
    for label, key in (('VAT', 'vat'), ('Tel', 'phone'), ('Email', 'email')):
        if party.get(key):
            rows.append(f"{label}: {esc(party[key])}")
    return [r for r in rows if r]


def grid_table(headers, columns, width=44):
    """A pandoc grid table -- the only markdown table form whose cells may hold
    more than one line, which an address needs.

    Lines within a cell get a trailing backslash: pandoc otherwise soft-wraps
    them into one paragraph and the address runs together on a single line.
    """
    rule = '+' + '+'.join('-' * (width + 2) for _ in headers) + '+'
    head = '+' + '+'.join('=' * (width + 2) for _ in headers) + '+'
    out = [rule, '| ' + ' | '.join(h.ljust(width) for h in headers) + ' |', head]
    for i in range(max(len(c) for c in columns)):
        cells = []
        for col in columns:
            text = col[i] if i < len(col) else ''
            if text and i < len(col) - 1:
                text += '\\'
            cells.append(text.ljust(width))
        out.append('| ' + ' | '.join(cells) + ' |')
    out.append(rule)
    return out


def markdown(st, supplier, client, bank):
    """The statement as a pandoc markdown document."""
    ccy = st['currency']
    as_of = st['as_of'].strftime('%Y-%m-%d')
    out = []

    out.append('---')
    out.append('toc: false')
    out.append('mainfont: Arial')
    out.append('fontsize: 10pt')
    out.append('header-includes:')
    out.append('  - \\usepackage{geometry}')
    out.append('  - \\usepackage{longtable}')
    out.append('geometry:')
    out.append('- top=20mm')
    out.append('- bottom=20mm')
    out.append('- left=15mm')
    out.append('- right=15mm')
    out.append('- heightrounded')
    out.append('---')
    out.append('')

    out.append('# Statement of Account')
    out.append('')

    # Parties.
    out += grid_table(['From', 'To'],
                      [party_lines(supplier), party_lines(client)])
    out.append('')
    out.append(f"**Account:** {esc(st['thread'])}  ")
    out.append(f"**As at:** {as_of}")
    out.append('')

    # Summary.
    out.append('## Summary')
    out.append('')
    out.append('| | |')
    out.append('|:--------------------------------------------------'
               '|-----------------------------:|')
    out.append(f"| Hours billed | {st['hours_billable']:.2f} |")
    if st['minutes_written_off']:
        out.append(f"| Hours written off | {st['hours_written_off']:.2f} |")
    out.append(f"| Charges | {money(st['charges'], ccy)} |")
    out.append(f"| Payments received | {money(st['payments'], ccy)} |")
    out.append(f"| **Balance due** | **{money(st['balance'], ccy)}** |")
    out.append('')

    # Ledger.
    out.append('## Account activity')
    out.append('')
    # Pandoc sizes pipe-table columns in proportion to the dashes below, so
    # these lengths are the layout: Date must not wrap mid-value.
    out.append('| Date | Description | Hours | Rate | Charge | Payment | Balance |')
    out.append('|:-------------|:-----------------------------------|--------:'
               '|----------:|------------:|------------:|------------:|')
    for ln in st['lines']:
        hours = f"{ln['hours']:.2f}" if ln['hours'] is not None else ''
        rate = f"{ln['rate']:,.2f}" if ln['rate'] is not None else ''
        charge = f"{ln['charge']:,.2f}" if ln['charge'] is not None else ''
        pay = f"{ln['payment']:,.2f}" if ln['payment'] is not None else ''
        out.append(f"| {ln['on'].strftime('%Y-%m-%d')} | {esc(ln['description'])} | "
                   f"{hours} | {rate} | {charge} | {pay} | {ln['balance']:,.2f} |")
    out.append(f"| | **Balance due** | **{st['hours_total']:.2f}** | | "
               f"**{st['charges']:,.2f}** | **{st['payments']:,.2f}** | "
               f"**{st['balance']:,.2f}** |")
    out.append('')
    out.append(f"All amounts in {ccy}.")
    out.append('')

    # Aging.
    out.append('## Aging')
    out.append('')
    out.append('| Current | 30 days | 60 days | 90+ days | Total |')
    out.append('|------------------:|------------------:|------------------:'
               '|------------------:|------------------:|')
    a = st['aging']
    out.append(f"| {a['current']:,.2f} | {a['30']:,.2f} | {a['60']:,.2f} | "
               f"{a['90+']:,.2f} | **{st['balance']:,.2f}** |")
    out.append('')

    # Banking.
    out.append('## Payment')
    out.append('')
    if bank['complete']:
        out.append('| | |')
        out.append('|:----------------------------'
                   '|:-------------------------------------------------|')
        out.append(f"| Account name | {esc(bank['bank_account_name'])} |")
        out.append(f"| Bank | {esc(bank['bank_name'])} |")
        out.append(f"| Account number | {esc(bank['bank_account_number'])} |")
        out.append(f"| Branch code | {esc(bank['bank_branch_code'])} |")
        out.append(f"| Account type | {esc(bank['bank_account_type'])} |")
        if client.get('reference'):
            out.append(f"| Reference | {esc(client['reference'])} |")
    else:
        out.append('Banking details not yet supplied.')
    out.append('')
    return '\n'.join(out) + '\n'


def render(st, out_path, tool='payments'):
    """Write the PDF. Renders in a temp dir so no scratch files leak into CWD."""
    if not shutil.which('pandoc'):
        sys.exit(f"{tool}: pandoc not found on PATH (needed for --pdf)")

    supplier = V.supplier()
    client_party = V.client(st['thread_path'])
    bank = V.banking()

    if not client_party['name']:
        sys.exit(f"{tool}: thread {st['thread']!r} has no client_name\n"
                 f"  set `client_name:` in threads/{st['thread']}.md")

    doc = markdown(st, supplier, client_party, bank)
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as workdir:
        src = Path(workdir) / 'statement.md'
        src.write_text(doc, encoding='utf-8')
        # Removed before rendering, not overwritten: a failed render leaves no
        # file rather than yesterday's figures under today's date.
        out_path.unlink(missing_ok=True)
        proc = subprocess.run(
            ['pandoc', str(src), '-s', '-o', str(out_path),
             '--pdf-engine=xelatex',
             '-V', f"title-meta=Statement of Account — {st['thread']}",
             '-V', f"author-meta={supplier['name']}"],
            capture_output=True, text=True, cwd=workdir)
    if proc.returncode != 0:
        sys.stdout.flush()
        sys.exit(f"{tool}: pandoc failed\n{proc.stderr.strip()}")
    if not out_path.exists():
        sys.exit(f"{tool}: pandoc reported success but wrote no file")
    return out_path, bank
