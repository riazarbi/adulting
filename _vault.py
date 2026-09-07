"""Shared vault primitives for the `hours` and `payments` CLIs.

Both tools store records the same way: one markdown file per thread, under a
top-level directory that mirrors `threads/{Projects,Processes,Topics}/`, with
the records as pretty-printed JSON inside a fenced code block. Only the fence
name and the record shape differ.

Follows the repo's existing shared-module pattern (`_suggester.py`,
`_argparse_helpjson.py`) rather than duplicating ~200 lines across two
self-contained tools, where the block-splice logic would inevitably drift.
"""

import json
import os
import re
import sys
import uuid as _uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

HOME = Path(os.environ.get('ADULTING_HOME', os.path.expanduser('~/vault')))
THREADS_DIR = HOME / 'threads'
CONFIG = HOME / '.adulting' / 'config.yaml'

KIND_DIRS = {'project': 'Projects', 'process': 'Processes', 'topic': 'Topics'}

CLOSE = '```'
ISO = '%Y-%m-%dT%H:%M:%S.000Z'

# Every record-bearing directory, as (subdir, fence). Used for vault-wide id
# uniqueness so an id is never reused across tools.
RECORD_DIRS = [('hours', '```simple-time-tracker'), ('payments', '```adulting-payments')]


# ---------- config ----------

def read_config():
    """Minimal one-level-nested YAML reader for .adulting/config.yaml.

    Understands sections with two-space-indented scalar children:
        hours:
          rate: 2500
          minutes: 60
    """
    cfg = {}
    if not CONFIG.exists():
        return cfg
    section = None
    for line in CONFIG.read_text(encoding='utf-8').split('\n'):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        m = re.match(r'^(\s*)([A-Za-z_][\w-]*):\s*(.*?)\s*$', line)
        if not m:
            continue
        indent, key, val = len(m.group(1)), m.group(2), m.group(3)
        val = val.strip().strip('"').strip("'")
        if indent == 0:
            if val == '':
                section = key
                cfg.setdefault(key, {})
            else:
                section = None
                cfg[key] = val
        elif section:
            cfg[section][key] = val
    return cfg


def config_default(section, key, fallback):
    val = read_config().get(section, {}).get(key)
    if val is None:
        return fallback
    try:
        return int(val)
    except ValueError:
        return fallback


# ---------- frontmatter ----------

def parse_frontmatter(text):
    """Return (dict, index of first body line)."""
    fm = {}
    lines = text.split('\n')
    if not lines or lines[0].strip() != '---':
        return fm, 0
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == '---':
            return fm, i + 1
        m = re.match(r'^([a-z_]+):\s*(.*?)\s*$', line)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return fm, 0


def unwiki(s):
    m = re.match(r'^\[\[([^\]]+)\]\]$', (s or '').strip())
    return m.group(1) if m else (s or '').strip()


# ---------- thread resolution ----------

def discover_threads():
    for kind, subdir in KIND_DIRS.items():
        d = THREADS_DIR / subdir
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if f.suffix == '.md' and not f.name.startswith('.'):
                yield kind, f.stem, f


def _eq(a, b, fold_case):
    a, b = a.strip(), b.strip()
    return a.lower() == b.lower() if fold_case else a == b


def resolve_thread(arg, fold_case=False):
    """Resolve 'SGB' / 'Projects/SGB' / '[[Projects/SGB]]' to (kind, name, path).

    Returns None if not found; raises ValueError on ambiguity. Matching is
    case-sensitive by default: relying on the filesystem would make results
    differ between macOS (case-insensitive) and Linux. `fold_case` opts into
    explicit case-insensitive matching for CSV import.
    """
    arg = unwiki(arg)
    threads = list(discover_threads())
    if '/' in arg:
        kind_dir, name = arg.split('/', 1)
        cands = [(k, n, p) for k, n, p in threads
                 if KIND_DIRS[k] == kind_dir and _eq(n, name, fold_case)]
    else:
        cands = [(k, n, p) for k, n, p in threads if _eq(n, arg, fold_case)]
    if not cands:
        return None
    if len(cands) > 1:
        where = ', '.join(f"{KIND_DIRS[k]}/{n}" for k, n, _ in cands)
        raise ValueError(f"ambiguous thread {arg!r}; matches: {where}")
    return cands[0]


def thread_ref(kind, name):
    return f"{KIND_DIRS[kind]}/{name}"


def thread_meta(path):
    """(currency, rate) from a thread file's frontmatter; either may be None."""
    fm, _ = parse_frontmatter(path.read_text(encoding='utf-8'))
    rate = fm.get('rate')
    try:
        rate = int(rate) if rate not in (None, '') else None
    except ValueError:
        rate = None
    return fm.get('currency') or None, rate


def resolve_target(tool, thread_arg, fold_case=False):
    try:
        match = resolve_thread(thread_arg, fold_case=fold_case)
    except ValueError as e:
        sys.exit(f"{tool}: {e}")
    if not match:
        sys.exit(f"{tool}: thread {thread_arg!r} does not resolve to a thread file")
    return match


def resolve_currency(tool, tpath, ref, flag):
    """Thread currency, or the flag, or a hard error. Never guessed."""
    currency = flag or thread_meta(tpath)[0]
    if not currency:
        sys.exit(f"{tool}: thread {ref!r} has no currency\n"
                 f"  set `currency: ZAR` in {tpath.relative_to(HOME)}, "
                 f"or pass --currency")
    currency = currency.upper()
    if not re.match(r'^[A-Z]{3}$', currency):
        sys.exit(f"{tool}: currency {currency!r} is not a 3-letter ISO code")
    return currency


# ---------- billing parties ----------

# Multi-line addresses are pipe-separated: the frontmatter and config readers
# are single-line only, and teaching them block scalars for this one field
# would not pay for itself.
def lines_of(value):
    return [x.strip() for x in (value or '').split('|') if x.strip()]


def supplier():
    """Who is billing, from .adulting/config.yaml's `billing:` section."""
    b = read_config().get('billing', {})
    return {
        'name': b.get('supplier_name') or read_config().get('owner') or '',
        'lines': lines_of(b.get('supplier_address')),
        'phone': b.get('supplier_phone') or '',
        'email': b.get('supplier_email') or '',
        'vat': b.get('supplier_vat') or '',
    }


BANK_FIELDS = ('bank_account_name', 'bank_name', 'bank_account_number',
               'bank_branch_code', 'bank_account_type')


def banking():
    """Where payment should be sent. Printed verbatim on the statement.

    `complete` is false while any field is missing or still a TODO placeholder;
    a statement then says so rather than printing a half-filled payment table.
    A document that asks for money must say where to send it.
    """
    b = read_config().get('billing', {})
    fields = {k: (b.get(k) or '').strip() for k in BANK_FIELDS}
    fields['complete'] = all(
        v and not v.upper().startswith('TODO') for k, v in fields.items()
        if k in BANK_FIELDS)
    return fields


def client(tpath):
    """Who is being billed, from the thread's frontmatter."""
    fm, _ = parse_frontmatter(tpath.read_text(encoding='utf-8'))
    return {
        'name': fm.get('client_name') or '',
        'lines': lines_of(fm.get('client_address')),
        'vat': fm.get('client_vat') or '',
        'email': fm.get('client_email') or '',
        # What the client quotes when paying: the thread name without its
        # Kind/ prefix. Not configurable -- it is derived, so it can never
        # drift from the thread or collide with another client's.
        'reference': tpath.stem,
    }


# ---------- record files (JSON in a fenced block) ----------

def record_path(subdir, kind, name):
    return HOME / subdir / KIND_DIRS[kind] / f"{name}.md"


def find_block(lines, fence):
    """(fence_idx, closing_idx) of the first matching block, else None."""
    for i, line in enumerate(lines):
        if line.rstrip() == fence:
            for j in range(i + 1, len(lines)):
                if lines[j].rstrip() == CLOSE:
                    return i, j
            return None
    return None


def read_records(path, fence, key='entries'):
    if not path.exists():
        return []
    lines = path.read_text(encoding='utf-8').split('\n')
    blk = find_block(lines, fence)
    if blk is None:
        return []
    raw = '\n'.join(lines[blk[0] + 1:blk[1]]).strip()
    if not raw:
        return []
    try:
        return json.loads(raw).get(key, []) or []
    except json.JSONDecodeError as e:
        sys.exit(f"malformed JSON in {path}: {e}")


def write_records(path, records, fence, ref, currency, key='entries',
                  sort_key=None, heading=''):
    """Splice records into the file's block, creating the file if needed.

    JSON is pretty-printed rather than written on one line, so appends produce
    readable, mergeable git diffs in a vault synced by git.
    """
    if sort_key:
        records = sorted(records, key=sort_key)
    payload = json.dumps({key: records}, indent=2, ensure_ascii=False).split('\n')
    if path.exists():
        lines = path.read_text(encoding='utf-8').split('\n')
        blk = find_block(lines, fence)
        if blk is None:
            sys.exit(f"{path} has no {fence} block")
        out = lines[:blk[0] + 1] + payload + lines[blk[1]:]
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        title = f"# {path.stem}{heading}"
        out = (['---', f'thread: "[[{ref}]]"', f'currency: {currency}', '---',
                '', title, '', fence] + payload + [CLOSE, ''])
    path.write_text('\n'.join(out), encoding='utf-8')


def record_files(subdir):
    d = HOME / subdir
    if not d.is_dir():
        return
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if not x.startswith('.')]
        for f in sorted(files):
            if f.endswith('.md') and not f.startswith('.'):
                yield Path(root) / f


def load_all(subdir, fence, key='entries'):
    """Yield (path, thread_ref, record) for every record in a subdir."""
    for path in record_files(subdir):
        fm, _ = parse_frontmatter(path.read_text(encoding='utf-8'))
        ref = unwiki(fm.get('thread', '')) or path.stem
        for r in read_records(path, fence, key):
            yield path, ref, r


def all_ids():
    """Every record id in the vault, across all tools — ids never collide."""
    ids = set()
    for subdir, fence in RECORD_DIRS:
        for _, _, r in load_all(subdir, fence):
            if r.get('id'):
                ids.add(r['id'])
    return ids


def new_id(existing):
    while True:
        u = _uuid.uuid4().hex[:8]
        if u not in existing:
            return u


# ---------- time ----------

def to_iso(dt):
    """Aware or naive-local datetime -> ISO 8601 UTC with milliseconds."""
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt.astimezone(timezone.utc).strftime(ISO)


def from_iso(s):
    return datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)


def local(s):
    return from_iso(s).astimezone()


def when_from_flags(tool, date_s, time_s):
    now = datetime.now()
    try:
        d = datetime.strptime(date_s, '%Y-%m-%d').date() if date_s else now.date()
    except ValueError:
        sys.exit(f"{tool}: bad --date {date_s!r}; expected YYYY-MM-DD")
    try:
        t = datetime.strptime(time_s, '%H:%M').time() if time_s else now.time()
    except ValueError:
        sys.exit(f"{tool}: bad --time {time_s!r}; expected HH:MM")
    return datetime.combine(d, t).replace(second=0, microsecond=0)


# ---------- money ----------

def dec(x):
    """JSON number -> Decimal, via str so float artefacts never enter."""
    return Decimal(str(x))


def fmt_money(amount, currency):
    q = Decimal(amount).quantize(Decimal('0.01'))
    whole = format(q, 'f').rstrip('0').rstrip('.')
    return f"{whole or '0'} {currency}"


def fmt_duration(mins):
    return f"{mins // 60}h {mins % 60}m"


# ---------- prompts ----------

def prompt(label, default=''):
    suffix = f" [{default}]" if default != '' else ''
    try:
        got = input(f"{label}{suffix}: ").strip()
    except EOFError:
        sys.exit("\naborted")
    return got or str(default)


def pick_thread(tool, include_all=False):
    """Numbered picker, matching the `threads new` interactive style."""
    threads = []
    for kind, name, path in discover_threads():
        fm, _ = parse_frontmatter(path.read_text(encoding='utf-8'))
        if not include_all and fm.get('status', 'open') != 'open':
            continue
        threads.append((kind, name, path))
    if not threads:
        sys.exit(f"{tool}: no threads found")
    print("Thread:")
    for i, (kind, name, _) in enumerate(threads, start=1):
        print(f"  {i}. {thread_ref(kind, name)}")
    choice = prompt("Pick")
    try:
        return threads[int(choice) - 1]
    except (ValueError, IndexError):
        sys.exit(f"{tool}: invalid choice")
