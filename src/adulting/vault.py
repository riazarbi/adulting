"""What every command shares: the vault's location, errors, config,
frontmatter, thread and person lookup, ACTION attributes, record files,
time and money.

Record files: `hours` and `payments` store records the same way, one
markdown file per thread under a top-level directory that mirrors
`threads/{Projects,Processes,Topics}/`, with the records as pretty-printed
JSON inside a fenced code block. Only the fence name and the record shape
differ.
"""

import argparse
import difflib
import json
import os
import re
import sys
import uuid as _uuid
from datetime import datetime, timezone
from collections import namedtuple
from decimal import Decimal

from adulting import helpjson
from pathlib import Path


def vault_home():
    """The vault directory. Read on every call, not at import, so tests
    can point it somewhere else."""
    return Path(os.environ.get('ADULTING_HOME', os.path.expanduser('~/vault')))


# ---------- errors ----------

_program = None


class HelpJsonAction(argparse.Action):
    """`--help-json`: print this parser's manifest and stop.

    An action rather than a flag the command reads afterwards, for two
    reasons. Argparse decides what is a flag and what is data, so after `--`
    or as another flag's value the word stays data and the command writes the
    record. And the action is handed the parser it was parsed by, so a
    subcommand prints its own manifest.
    """

    def __init__(self, option_strings, dest, **options):
        super().__init__(option_strings, dest, nargs=0,
                         default=argparse.SUPPRESS, **options)

    def __call__(self, parser, namespace, values, option_string=None):
        # `prog` is "tasks" at the top level and "tasks list" below it; the
        # manifest names the subcommand as the tree above it does.
        print(json.dumps(helpjson.parser_to_dict(parser, name=parser.prog.split()[-1]),
                         indent=2))
        parser.exit(0)


def add_help_json(parser):
    parser.add_argument('--help-json', action=HelpJsonAction,
                        help="Print this command's arguments as JSON, and exit.")


def command_parser(prog, description, **options):
    """The argument parser for a command. Its name is also the one errors
    and warnings start with, however the command was started."""
    global _program
    _program = prog
    parser = argparse.ArgumentParser(prog=prog, description=description, **options)
    add_help_json(parser)
    return parser


class Subcommands:
    """A command's subcommand table. Every subcommand answers `--help-json`
    too, so `tasks list --help-json` describes `list`."""

    def __init__(self, parser, dest='subcommand'):
        self._sub = parser.add_subparsers(dest=dest)

    def add_parser(self, name, **options):
        # A subcommand's one-line help is its description too, so asking the
        # subcommand itself — `tasks list --help-json`, `tasks list --help` —
        # says what it does, as the whole-command manifest already did.
        options.setdefault('description', options.get('help', ''))
        parser = self._sub.add_parser(name, **options)
        add_help_json(parser)
        return parser


def parse_command(parser, subcommand_required=True):
    """A command's arguments: check the vault, and require a subcommand
    unless told otherwise. `--help-json` has already printed and exited by
    the time this is reached."""
    args = parser.parse_args()
    require_vault()
    if subcommand_required and getattr(args, 'subcommand', '') is None:
        parser.error('the following arguments are required: subcommand')
    return args


def program():
    """The running command's name: the one its parser was given, else the
    one argparse would find."""
    return _program or os.path.basename(sys.argv[0])


def die(msg, code=1):
    """Stop with `<command>: error: <msg>` on stderr. argparse reports usage
    errors in the same shape, so every error from every command looks alike.
    Nothing else may reach stderr on success: the agent harness discards
    stdout whenever stderr is non-empty."""
    print(f"{program()}: error: {msg}", file=sys.stderr)
    sys.exit(code)


def require_vault():
    """Stop unless the vault exists and is a directory. Every command checks
    this first, so a mistyped ADULTING_HOME is reported rather than read as
    an empty vault, or silently started as a new one."""
    home = vault_home()
    if not home.is_dir():
        die(f"ADULTING_HOME is not a directory: {home}")


def warn(msg):
    """`<command>: warning: <msg>` on stderr, and carry on."""
    print(f"{program()}: warning: {msg}", file=sys.stderr)


def tell_a_human(msg):
    """Warn, but only when a person is there to read it.

    The agent harness discards stdout whenever stderr is non-empty, so a
    command whose stdout is the answer cannot warn into a pipe without
    throwing the answer away. On a terminal there is no such cost, and a
    person should be told that a file was skipped.
    """
    if sys.stderr.isatty():
        warn(msg)


def make_dir(path):
    """Create a folder the user named, and its parents, or stop saying why not."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        die(f"cannot create {path}: {e.strerror}")


KIND_DIRS = {'project': 'Projects', 'process': 'Processes', 'topic': 'Topics'}

CLOSE = '```'
ISO = '%Y-%m-%dT%H:%M:%S.000Z'

# The fences of the two record stores; the stores themselves are built below,
# once the reading and writing they use exists.
HOURS_FENCE = '```simple-time-tracker'
PAYMENTS_FENCE = '```adulting-payments'


# ---------- command-line flags ----------

def iso_date(value):
    """An argparse type: a real date written YYYY-MM-DD, kept as text."""
    try:
        datetime.strptime(value, '%Y-%m-%d')
    except ValueError as e:
        raise argparse.ArgumentTypeError(
            f"expected a date as YYYY-MM-DD, got {value!r}") from e
    return value


def add_window_flags(parser):
    """--since, --until and --json, worded the same for every command."""
    parser.add_argument('--since', metavar='YYYY-MM-DD', type=iso_date, help='On or after this date.')
    parser.add_argument('--until', metavar='YYYY-MM-DD', type=iso_date, help='On or before this date.')
    parser.add_argument('--json', action='store_true', help='JSON output.')


# ---------- config ----------

def read_config():
    """.adulting/config.yaml, read with the frontmatter parser: top-level
    scalars, and sections of two-space-indented scalars such as
        hours:
          rate: 2500
    """
    config = vault_home() / '.adulting' / 'config.yaml'
    if not config.exists():
        return {}
    return parse_block(read_or_die(config).split('\n'))


def config_default(section, key, fallback):
    """A whole-number default from config.yaml, or `fallback` when the file
    does not set one. A value that cannot be read is an error."""
    val = read_config().get(section, {}).get(key)
    if val is None:
        return fallback
    return as_int(val, f"{section}.{key} in .adulting/config.yaml")


# ---------- frontmatter ----------

KEY_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*$')


def unquote(value):
    return value.strip().strip('"').strip("'")


def parse_block(lines):
    """The small YAML subset the vault uses, from frontmatter or config.yaml.

    Values are strings with their quotes removed. A bare `key:` is an empty
    string, unless indented lines follow it: `  - item` lines make it a list,
    and a list item that is itself `k: v` starts a mapping that deeper
    `k: v` lines continue (a `cadences:` entry); plain `  k: v` lines make it
    a mapping (a config section). Blank lines and `#` comments are skipped.
    """
    out = {}
    key = None      # the top-level key indented lines belong to
    item = None     # the mapping list item being filled in
    for line in lines:
        text = line.strip()
        if not text or text.startswith('#'):
            continue
        if not line[0].isspace():
            m = KEY_RE.match(text)
            key, item = (m.group(1), None) if m else (None, None)
            if m:
                out[key] = unquote(m.group(2))
            continue
        if key is None:
            continue
        if text.startswith('- '):
            value = text[2:].strip()
            # A bare `key:` parsed to '' above; the first indented line under
            # it says what it really is, so '' is the "not decided yet"
            # sentinel and is replaced here by a list, or below by a mapping.
            if out[key] == '':
                out[key] = []
            if not isinstance(out[key], list):
                continue
            m = KEY_RE.match(value) if value[:1] not in ('"', "'") else None
            item = {m.group(1): unquote(m.group(2))} if m else None
            out[key].append(item if m else unquote(value))
            continue
        m = KEY_RE.match(text)
        if not m:
            continue
        if item is not None:
            item[m.group(1)] = unquote(m.group(2))
        else:
            if out[key] == '':
                out[key] = {}
            if isinstance(out[key], dict):
                out[key][m.group(1)] = unquote(m.group(2))
    return out


def read_utf8(path, errors='strict'):
    """A vault file's text, or None when it cannot be read as UTF-8.

    Every command walks files it did not write — a stray binary, a
    sync-conflict copy, something saved in another encoding. A walker skips
    those and carries on; `lint` is the command that reports them.

    This is the only place the vault is read, so there is one answer to a
    file that cannot be.
    """
    try:
        return path.read_text(encoding='utf-8', errors=errors)
    except (OSError, UnicodeDecodeError):
        return None


def read_or_die(path, errors='strict'):
    """A file's text, or stop saying which file is unreadable.

    For a file the user named: skipping it silently would answer a question
    about *that* file by pretending it does not exist.
    """
    text = read_utf8(path, errors)
    if text is None:
        die(f"{path} is not valid UTF-8")
    return text


def parse_frontmatter_doc(text):
    """Return (frontmatter, body) for any vault file. The frontmatter is the
    block between a first-line `---` and the next `---`, read by
    parse_block; the body is the text after it. With no closing `---`, every
    line is read and the whole text is the body. Wikilinks are left as
    written — call unwiki() on them."""
    lines = text.split('\n')
    if not lines or lines[0].strip() != '---':
        return {}, text
    end = next((i for i, line in enumerate(lines[1:], start=1) if line.strip() == '---'), None)
    if end is None:
        return parse_block(lines[1:]), text
    return parse_block(lines[1:end]), '\n'.join(lines[end + 1:])


def unwiki(s):
    m = re.match(r'^\[\[([^\]]+)\]\]$', (s or '').strip())
    return m.group(1) if m else (s or '').strip()


def note_threads(fm):
    """The thread refs in a note's or log's frontmatter: notes carry a
    `threads:` list, logs a singular `thread:`. Wikilinks are unwrapped."""
    raw = fm.get('threads') or fm.get('thread') or []
    if isinstance(raw, str):
        raw = [raw]
    return [unwiki(t) for t in raw if unwiki(t)]


def fuzzy_score(query, name):
    """Score a name against a query (lowercase compare). Higher = better.
    Heuristic ladder: exact > startswith > initials-equal > substring >
    initials-startswith > difflib ratio (capped below the heuristic floor).
    Used by `threads list` and `people list`."""
    q = query.lower()
    n = name.lower()
    if q == n:
        return 1.0
    if n.startswith(q):
        return 0.9
    initials = ''.join(w[0] for w in re.findall(r'\w+', name)).lower()
    if initials == q:
        return 0.85
    if q in n:
        return 0.7
    if initials.startswith(q):
        return 0.6
    return difflib.SequenceMatcher(None, q, n).ratio() * 0.5


# ---------- thread and person files ----------

CATEGORIES = ['professional', 'personal', 'voluntary']


def today():
    return datetime.now().strftime('%Y-%m-%d')


def file_summary(path):
    """What `threads list` and `people list` show of a file, or None when the
    file cannot be read — a listing skips it rather than ending there."""
    text = read_utf8(path)
    if text is None:
        return None
    fm = parse_frontmatter_doc(text)[0]
    return {'path': str(path.relative_to(vault_home())),
            'status': fm.get('status', ''), 'category': fm.get('category', ''),
            'started': fm.get('started', ''), 'ended': fm.get('ended', '')}


def file_json(path, **identity):
    """What `threads show --json` and `people show --json` print: who it is,
    where it is, and all of its frontmatter."""
    fm = parse_frontmatter_doc(read_or_die(path))[0]
    return json.dumps({**identity, 'path': str(path.relative_to(vault_home())), **fm}, indent=2)


def rel(path):
    """A vault file, as every command names it: relative to the vault.

    One format everywhere, so the same file reads the same whichever command
    mentions it. A path outside the vault — `lint` can be pointed at one —
    keeps its own name, since it has nothing to be relative to.
    """
    path = Path(path)
    home = vault_home().resolve()
    full = path.resolve()
    return str(full.relative_to(home)) if full.is_relative_to(home) else str(path)


def where(path, line_no):
    """A place in the vault, as `path:line`."""
    return f"{rel(path)}:{line_no + 1}"


def print_summary_list(rows, args, column, noun):
    """`threads list` and `people list` are one listing over different files:
    open ones unless --all, ranked by the query, printed as a column with the
    status and category beside it, or as JSON."""
    if not args.all:
        rows = [r for r in rows if r['status'] == 'open']
    if args.query:
        rows = rank_by_query(rows, args.query, 'name', column)
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    if not rows:
        print("(no matches)" if args.query else f"(no {noun})")
        return 0
    width = max(len(r[column]) for r in rows)
    print(f"{column.upper():<{width}}  {'STATUS':<8}  CATEGORY")
    for r in rows:
        print(f"{r[column]:<{width}}  {r['status']:<8}  {r['category']}")
    return 0


def rank_by_query(rows, query, *keys):
    """The rows that look like `query`, best first. Each row scores its best
    match over the given keys; a score of 0.3 or less is no match."""
    scored = [(max(fuzzy_score(query, r[k]) for k in keys), r) for r in rows]
    scored = [(s, r) for s, r in scored if s > 0.3]
    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored]


# ---------- thread resolution ----------

def discover_threads():
    for kind, subdir in KIND_DIRS.items():
        d = vault_home() / 'threads' / subdir
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if f.suffix == '.md' and not f.name.startswith('.'):
                yield kind, f.stem, f


def resolve_thread(arg):
    """Resolve 'SGB' / 'Projects/SGB' / '[[Projects/SGB]]' to (kind, name, path).

    Returns None if not found; raises ValueError on ambiguity. Matching is
    exact: relying on the filesystem would make results differ between macOS
    (case-insensitive) and Linux, so every command matches the same way.
    """
    arg = unwiki(arg)
    threads = list(discover_threads())
    if '/' in arg:
        kind_dir, name = arg.split('/', 1)
        cands = [(k, n, p) for k, n, p in threads
                 if KIND_DIRS[k] == kind_dir and n.strip() == name.strip()]
    else:
        cands = [(k, n, p) for k, n, p in threads if n.strip() == arg.strip()]
    if not cands:
        return None
    if len(cands) > 1:
        where = ', '.join(f"{KIND_DIRS[k]}/{n}" for k, n, _ in cands)
        raise ValueError(f"ambiguous thread {arg!r}; matches: {where}")
    return cands[0]


def thread_ref(kind, name):
    return f"{KIND_DIRS[kind]}/{name}"


def is_plain_name(name):
    """True if `name` can become <name>.md inside its folder: no `/`, which
    would reach outside it, and no leading `.`, which would hide the file."""
    return '/' not in name and not name.startswith('.')


def is_thread(ref):
    """True if `ref` is exactly the `Kind/Name` of a thread file. Checked
    against the files in threads/, not by asking the filesystem, so case
    matters on macOS as it does on Linux."""
    return any(thread_ref(kind, name) == ref for kind, name, _ in discover_threads())


def thread_meta(path):
    """(currency, rate) from a thread file's frontmatter; either may be None.
    A rate that is not a whole number is an error, not a missing rate."""
    fm, _ = parse_frontmatter_doc(read_or_die(path))
    rate = fm.get('rate')
    if rate in (None, ''):
        return fm.get('currency') or None, None
    return fm.get('currency') or None, as_int(rate, f"rate in {path.relative_to(vault_home())}")


def find_thread(thread_arg):
    """(kind, name, path) for a thread given as a name, `Kind/Name` or
    wikilink. Raises ValueError if it names no thread, or threads of two
    kinds."""
    match = resolve_thread(thread_arg)
    if not match:
        raise ValueError(f"thread {thread_arg!r} does not resolve to a thread file")
    return match


def resolve_target(thread_arg):
    """find_thread for a command: stop with the error if there is one."""
    try:
        return find_thread(thread_arg)
    except ValueError as e:
        die(str(e))


def resolve_currency(tpath, ref, flag):
    """Thread currency, or the flag, or a hard error. Never guessed."""
    currency = flag or thread_meta(tpath)[0]
    if not currency:
        die(f"thread {ref!r} has no currency\n"
            f"  set `currency: ZAR` in {tpath.relative_to(vault_home())}, "
            f"or pass --currency")
    return check_currency(currency)


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
    fm, _ = parse_frontmatter_doc(read_or_die(tpath))
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

class Store:
    """One kind of record file, and everything that reads or writes one.

    `hours` and `payments` keep their records the same way — JSON inside a
    fenced block, one file per thread — and differ only in the six values
    below, so the reading and writing is written once, here.

    `stamp` is the field that dates a record and `noun` is what one record is
    called in a message, which together give every message about a record the
    same shape: "no entry with id 'x'", "received of payment 'x'".
    """

    def __init__(self, subdir, fence, key, heading, noun, stamp):
        self.subdir = subdir      # hours/ or payments/, under the vault
        self.fence = fence        # the opening fence of the JSON block
        self.key = key            # the key the records sit under in that JSON
        self.heading = heading    # appended to the title of a new file
        self.noun = noun          # one record, in a message
        self.stamp = stamp        # the field that dates a record

    def path(self, kind, name):
        return vault_home() / self.subdir / KIND_DIRS[kind] / f"{name}.md"

    def stamp_name(self, record):
        """How a record's timestamp is named in an error."""
        return f"{self.stamp} of {self.noun} {record.get('id')!r}"

    def day_of(self, record):
        """The local day the record falls on, as YYYY-MM-DD. Local, not UTC:
        evening work belongs to the day it was done, not the next one."""
        return local(record[self.stamp], self.stamp_name(record)).strftime('%Y-%m-%d')

    def sort_key(self, record):
        """Files are kept in time order, undated records first."""
        return record.get(self.stamp) or ''

    def read(self, path):
        return read_records(path, self)

    def save(self, path, records, ref, currency):
        write_records(path, records, self, ref, currency)

    def load_all(self):
        """(path, thread_ref, record) for every record in the store."""
        return load_all(self)

    def find(self, record_id):
        """(path, thread_ref, records, record), or stop. `records` is every
        record in its file, so an edit can be saved with the rest."""
        found = find_record(self, record_id)
        if not found:
            die(f"no {self.noun} with id {record_id!r}")
        return found

    def collect(self, thread=None, since=None, until=None):
        """Every dated record, narrowed to one thread and a date window."""
        want = None
        if thread:
            kind, name, _ = resolve_target(thread)
            want = thread_ref(kind, name)
        for path, ref, r in self.load_all():
            if want and ref != want:
                continue
            if not r.get(self.stamp):
                continue
            if not in_window(self.day_of(r), since, until):
                continue
            yield path, ref, r

    def cmd_rm(self, args):
        """`hours rm` and `payments rm` are the same command."""
        path, ref, records, target = self.find(args.id)
        if not args.yes:
            die(f"refusing to delete {args.id} without -y")
        # The file exists, so its frontmatter — currency included — is kept.
        self.save(path, [r for r in records if r is not target], ref, None)
        print(f"deleted {args.id}")
        return 0


HOURS = Store('hours', HOURS_FENCE, 'entries', ' — hours', 'entry', 'startTime')
PAYMENTS = Store('payments', PAYMENTS_FENCE, 'payments', ' — payments',
                 'payment', 'received')
STORES = (HOURS, PAYMENTS)


def as_output(row):
    """A row as `--json` and `show` print it: the amount as a plain number.
    Rows keep the Decimal until this point, so text output rounds exactly."""
    return {**row, 'amount': float(row['amount'])}


def find_block(lines, fence):
    """(fence_idx, closing_idx) of the first matching block, else None."""
    for i, line in enumerate(lines):
        if line.rstrip() == fence:
            for j in range(i + 1, len(lines)):
                if lines[j].rstrip() == CLOSE:
                    return i, j
            return None
    return None


def read_records(path, store):
    """The records in a file, or none at all: a file that cannot be read has
    no records to show, and `lint` reports it."""
    text = read_utf8(path)
    if text is None:
        return []
    lines = text.split('\n')
    blk = find_block(lines, store.fence)
    if blk is None:
        return []
    raw = '\n'.join(lines[blk[0] + 1:blk[1]]).strip()
    if not raw:
        return []
    try:
        return json.loads(raw).get(store.key, []) or []
    except json.JSONDecodeError as e:
        die(f"malformed JSON in {path}: {e}")


def write_records(path, records, store, ref, currency):
    """Splice records into the file's block, creating the file if needed.

    JSON is pretty-printed rather than written on one line, so appends produce
    readable, mergeable git diffs in a vault synced by git.
    """
    records = sorted(records, key=store.sort_key)
    payload = json.dumps({store.key: records}, indent=2,
                         ensure_ascii=False).split('\n')
    if path.exists():
        # Rewriting a file means reading all of it first; a file that cannot
        # be read is an error, never something to overwrite.
        lines = read_or_die(path).split('\n')
        blk = find_block(lines, store.fence)
        if blk is None:
            die(f"{path} has no {store.fence} block")
        out = lines[:blk[0] + 1] + payload + lines[blk[1]:]
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        title = f"# {path.stem}{store.heading}"
        # currency is omitted for a file that only ever holds unbilled time:
        # money is an overlay on hours, not a precondition for recording them.
        head = ['---', f'thread: "[[{ref}]]"']
        if currency:
            head.append(f'currency: {currency}')
        out = (head + ['---', '', title, '', store.fence] + payload + [CLOSE, ''])
    path.write_text('\n'.join(out), encoding='utf-8')


def record_files(subdir):
    d = vault_home() / subdir
    if not d.is_dir():
        return
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if not x.startswith('.')]
        for f in sorted(files):
            if f.endswith('.md') and not f.startswith('.'):
                yield Path(root) / f


def find_record(store, record_id):
    """(path, thread_ref, records, record) for the record with this id, or
    None. `records` is every record in its file and `record` is the one in
    that list, so an edit to it can be saved with the rest."""
    for path in record_files(store.subdir):
        records = read_records(path, store)
        for r in records:
            if r.get('id') == record_id:
                fm, _ = parse_frontmatter_doc(read_or_die(path))
                return path, unwiki(fm.get('thread', '')) or path.stem, records, r
    return None


def load_all(store):
    """Yield (path, thread_ref, record) for every record in a store."""
    for path in record_files(store.subdir):
        text = read_utf8(path)
        if text is None:
            continue
        fm, _ = parse_frontmatter_doc(text)
        ref = unwiki(fm.get('thread', '')) or path.stem
        for r in read_records(path, store):
            yield path, ref, r


def all_ids():
    """Every record id in the vault, across all tools — ids never collide."""
    ids = set()
    for store in STORES:
        for _, _, r in store.load_all():
            if r.get('id'):
                ids.add(r['id'])
    return ids


def random_id():
    return _uuid.uuid4().hex[:8]


def new_id(existing, draw=random_id):
    """An 8-hex-digit id not in `existing`, drawing again until one is free.
    `draw` makes the ids; a test gives its own to force a collision."""
    while True:
        u = draw()
        if u not in existing:
            return u


# ---------- actions ----------

DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
UUID8_RE = re.compile(r'^[a-f0-9]{8}$')


def vault_file(rel):
    """The path of the vault file `rel` (e.g. 'people/Riaz Arbi.md') if it
    exists with exactly that spelling, else None. Each part is looked up in
    its folder's listing rather than by asking the filesystem, so case
    matters on macOS as it does on Linux, and `..` cannot leave the vault."""
    path = vault_home()
    for part in rel.split('/'):
        if part in ('', '.', '..') or not path.is_dir() or part not in os.listdir(path):
            return None
        path = path / part
    return path if path.is_file() else None


def person_exists(name):
    """True if people/<name>.md exists, spelt exactly so. No name means
    nobody is assigned, which is fine."""
    if not name:
        return True
    return vault_file(f"people/{name}.md") is not None


PRIORITIES = ('H', 'M', 'L')

ASSIGNEE_PREFIX_RE = re.compile(r'^\((?P<assignee>[^)]*)\)\s*(?P<rest>.*)$')
ACTION_RE = re.compile(r'^ACTION:\s*(?P<rest>.*)$')
ATTRS_TAIL_RE = re.compile(r'\s*<!--(?P<attrs>[^>]*)-->\s*$')

Action = namedtuple('Action', 'assignee body attrs errors')


def split_assignee(text):
    """('Riaz Arbi', 'Draft it') for '(Riaz Arbi) Draft it', else ('', text)."""
    m = ASSIGNEE_PREFIX_RE.match(text.strip())
    if not m:
        return '', text.strip()
    return m.group('assignee').strip(), m.group('rest').strip()


def parse_action(line):
    """An `ACTION:` line as (assignee, body, attrs, errors), or None if the
    line is not one. The trailing `<!--attrs-->` is taken off first, so an
    ACTION with attributes and no text keeps its attributes and is simply an
    action with no description. `tasks`, `buffer` and `lint` all read an
    action this way, so they agree about every line."""
    m = ACTION_RE.match(line)
    if not m:
        return None
    rest = m.group('rest').strip()
    tail = ATTRS_TAIL_RE.search(rest)
    tokens = tail.group('attrs').split() if tail else []
    if tail:
        rest = rest[:tail.start()].strip()
    assignee, body = split_assignee(rest)
    attrs, errors = parse_action_attrs(tokens)
    return Action(assignee, body, attrs, errors)


def check_priority(value):
    """A priority as typed, or stop. One rule and one message wherever a
    priority is given: on a flag, on a `priority:` attribute, or to
    `tasks set-priority`."""
    if value not in PRIORITIES:
        die(f"priority must be H, M, or L; got {value!r}")
    return value


def parse_action_attrs(tokens):
    """Parse `due:... scheduled:... priority:... depends:...` tokens from an
    ACTION's attr comment. Returns (attrs, errors): a bad value is reported
    and left out of attrs. A leading buffer timestamp token is skipped."""
    attrs = {'depends': []}
    errors = []
    for tok in tokens:
        if ':' not in tok:
            errors.append(f"unknown attr token {tok!r}")
            continue
        key, _, val = tok.partition(':')
        if key in ('due', 'scheduled'):
            if DATE_RE.match(val):
                attrs[key] = val
            else:
                errors.append(f"{key} must be YYYY-MM-DD; got {val!r}")
        elif key == 'priority':
            if val in PRIORITIES:
                attrs[key] = val
            else:
                errors.append(f"priority must be H, M, or L; got {val!r}")
        elif key == 'depends':
            if UUID8_RE.match(val):
                attrs['depends'].append(val)
            else:
                errors.append(f"depends must be 8 hex chars; got {val!r}")
        elif re.match(r'^\d{4}-\d{2}-\d{2}T', tok):
            continue
        else:
            errors.append(f"unknown attr {key!r}")
    return attrs, errors


# ---------- time ----------

def to_iso(dt):
    """Aware or naive-local datetime -> ISO 8601 UTC with milliseconds."""
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt.astimezone(timezone.utc).strftime(ISO)


def from_iso(s):
    return datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)


def as_time(value, what):
    """A stored timestamp as an aware datetime, or stop. Every walker reads
    times this way, so a malformed one is reported the same everywhere
    instead of crashing one command and being skipped by another."""
    try:
        return from_iso(str(value))
    except (TypeError, ValueError):
        die(f"{what} must be ISO 8601 UTC; got {value!r}")


def local(value, what='timestamp'):
    """A stored timestamp in local time, or stop. `what` names the field, so
    the message points at the record that needs fixing."""
    return as_time(value, what).astimezone()


def minutes_of(e):
    """Whole minutes between an entry's startTime and endTime; 0 if either
    is missing. A time that cannot be read stops the command."""
    if not e.get('startTime') or not e.get('endTime'):
        return 0
    start = as_time(e['startTime'], f"startTime of entry {e.get('id')!r}")
    end = as_time(e['endTime'], f"endTime of entry {e.get('id')!r}")
    return int((end - start).total_seconds() // 60)


def in_window(day, since, until):
    """True if the YYYY-MM-DD `day` falls within since..until. Either bound
    may be empty, meaning open-ended."""
    return (not since or day >= since) and (not until or day <= until)


def is_currency_code(code):
    return bool(re.match(r'^[A-Z]{3}$', code))


def check_currency(raw):
    """A currency as typed, upper-cased, or stop: it must be a 3-letter ISO
    code such as ZAR."""
    code = raw.strip().upper()
    if not is_currency_code(code):
        die(f"currency {code!r} is not a 3-letter ISO code")
    return code


def when_from_flags(date_s, time_s):
    now = datetime.now()
    try:
        d = datetime.strptime(date_s, '%Y-%m-%d').date() if date_s else now.date()
    except ValueError:
        die(f"bad --date {date_s!r}; expected YYYY-MM-DD")
    try:
        t = datetime.strptime(time_s, '%H:%M').time() if time_s else now.time()
    except ValueError:
        die(f"bad --time {time_s!r}; expected HH:MM")
    return datetime.combine(d, t).replace(second=0, microsecond=0)


# ---------- money ----------

def dec(x):
    """JSON number -> Decimal, via str so float artefacts never enter."""
    return Decimal(str(x))


def as_int(value, what):
    """`value` as a whole number, or stop. Money is never guessed: a rate
    that cannot be read is an error wherever it is used, not a silent zero."""
    if isinstance(value, bool) or not isinstance(value, int):
        text = str(value)
        if not re.fullmatch(r'-?\d+', text.strip()):
            die(f"{what} must be a whole number; got {value!r}")
        return int(text)
    return value


def as_money(value, what):
    """`value` as a Decimal amount, or stop."""
    try:
        return dec(value)
    except (ArithmeticError, TypeError, ValueError):
        die(f"{what} must be a number; got {value!r}")


CENT = Decimal('0.01')


def cents(x):
    """A JSON number as Decimal, rounded to the cent. Receipts are rounded
    before they are summed, as charges are, so totals agree with the lines."""
    return dec(x).quantize(CENT)


def fmt_money(amount, currency):
    """Money as text. A currency-less amount is unbilled time, not zero money."""
    if not currency:
        return 'unbilled'
    q = Decimal(amount).quantize(CENT)
    whole = format(q, 'f').rstrip('0').rstrip('.')
    return f"{whole or '0'} {currency}"


def fmt_duration(mins):
    return f"{mins // 60}h {mins % 60}m"
