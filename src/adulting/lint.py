"""Validate adulting files against schemas in schemas/.

Usage:
    lint                        # walk ~/vault/ and validate everything
    lint <path> [<path> ...]    # validate specific files

Exit code 0 if clean, 1 if any violations. Errors print as
<path>:<line>: <message>, the path absolute, as every command prints one.
Pass --quiet for exit-code-only.

Every other command skips a file it cannot read as UTF-8 and carries on.
This is where such a file is reported, as `file is not valid UTF-8`.
"""

import json
import os
import re
import sys
from pathlib import Path

from adulting import vault as V

# The schemas ship inside the package, next to this module.
SCHEMAS_DIR = Path(__file__).resolve().parent / 'schemas'


WIKILINK_RE = re.compile(r'^\[\[([^\]]+)\]\]$')


# ---------- helpers ----------

def unquote(s):
    """Strip surrounding single/double quotes if present, with simple escape handling."""
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1].replace('\\"', '"').replace('\\\\', '\\')
    if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
        return s[1:-1].replace("''", "'")
    return s


def wikilink_target(s):
    """If s is a wikilink string `[[target]]`, return the target. Else None.
    (vault.unwiki returns plain text unchanged; lint needs to tell them apart.)"""
    m = WIKILINK_RE.match(s.strip())
    return m.group(1) if m else None


# ---------- frontmatter parsing ----------

def parse_frontmatter(text):
    """Parse YAML-ish frontmatter. Returns (dict, body_start_line_index).

    Handles:
      - flat scalars `key: value` (with surrounding quotes stripped)
      - list of scalars (each line `  - "value"`)
      - list of mappings (each list item with `  key: val` lines)
    """
    lines = text.split('\n')
    if not lines or lines[0].strip() != '---':
        return {}, 0
    fm = {}
    i = 1
    body_start = 0
    while i < len(lines):
        if lines[i].strip() == '---':
            body_start = i + 1
            break
        m = re.match(r'^([a-z_]+):\s*(.*?)\s*$', lines[i])
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2)
        if val == '':
            children, mode = _read_block_children(lines, i + 1)
            fm[key] = children
            # advance past the block — _read_block_children returns end index
            i = mode
        else:
            fm[key] = unquote(val)
            i += 1
    return fm, body_start


def _read_block_children(lines, start):
    """Read indented block children starting at lines[start]. Returns
    (collected, end_index). collected is either a list of dicts (when items
    have key:value bodies) or a list of strings (when items are scalars)."""
    collected = []
    is_mapping_list = None  # decided by first item
    current_dict = None
    i = start
    while i < len(lines) and lines[i].strip() != '---':
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if not (line.startswith(' ') or line.startswith('\t')):
            break
        stripped = line.lstrip()
        if stripped.startswith('- '):
            rest = stripped[2:].rstrip()
            # Decide list type from first item
            if is_mapping_list is None:
                # Mapping if rest looks like `key: value` (and isn't a quoted string)
                if not rest.startswith('"') and not rest.startswith("'") and re.match(r'^[a-z_][a-z0-9_]*:\s', rest):
                    is_mapping_list = True
                else:
                    is_mapping_list = False
            if is_mapping_list:
                current_dict = {}
                collected.append(current_dict)
                if ':' in rest:
                    ck, _, cv = rest.partition(':')
                    current_dict[ck.strip()] = unquote(cv.strip())
            else:
                collected.append(unquote(rest))
                current_dict = None
        else:
            # Continuation of current mapping list item
            if is_mapping_list and current_dict is not None and ':' in stripped:
                ck, _, cv = stripped.partition(':')
                current_dict[ck.strip()] = unquote(cv.strip())
        i += 1
    return collected, i


# ---------- schema loading ----------

_CELL_SPLIT_RE = re.compile(r'(?<!\\)\|')


def parse_md_table(lines, start_idx):
    """Read consecutive |-prefixed lines as a markdown table. Returns
    (data_rows, end_idx). The header and separator rows are dropped.
    Pipes inside cells can be escaped as \\|."""
    rows = []
    i = start_idx
    while i < len(lines):
        line = lines[i].strip()
        if not line.startswith('|'):
            break
        if re.match(r'^\|[-: |]+\|$', line):
            i += 1
            continue
        cells = _CELL_SPLIT_RE.split(line.strip('|'))
        rows.append([c.replace(r'\|', '|').strip() for c in cells])
        i += 1
    return rows, i


def parse_constraint(text):
    out = {}
    text = text.strip()
    if not text:
        return out
    for part in (p.strip() for p in text.split(';')):
        if not part:
            continue
        if part.startswith('regex='):
            out['regex'] = part[len('regex='):].strip()
        elif part.startswith('min='):
            try:
                out['min_length'] = int(part[len('min='):].strip())
            except ValueError:
                pass
        elif part == 'must_contain_digit':
            out.setdefault('flags', set()).add('must_contain_digit')
        else:
            values = [v.strip().strip('"\'') for v in part.split(',') if v.strip()]
            if values:
                out['enum'] = values
    return out


def parse_schema(path):
    text = V.read_or_die(path)
    fm, body_start = parse_frontmatter(text)
    schema = {
        'name': fm.get('schema'),
        'scope': fm.get('scope', 'file'),
        'applies_when': fm.get('applies_when', ''),
        'filename': fm.get('filename', ''),
        'directory': fm.get('directory', ''),  # optional dir scope
        'shape': fm.get('shape', ''),
        'fields': {},
        'path': str(path),
    }
    lines = text.split('\n')
    i = body_start
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('## ') and line[3:].strip().lower() == 'fields':
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith('|'):
                if lines[j].strip().startswith('## '):
                    break
                j += 1
            rows, end = parse_md_table(lines, j)
            for row in rows[1:] if rows else []:
                if len(row) < 4:
                    continue
                name, required, type_, constraint = row[:4]
                schema['fields'][name] = {
                    'required': required.lower() == 'yes',
                    'type': (type_ or 'string').lower(),
                    'constraint': parse_constraint(constraint),
                }
            i = end
        else:
            i += 1
    return schema


def load_schemas(schemas_dir):
    schemas = {}
    for f in sorted(schemas_dir.iterdir()):
        if f.suffix == '.md':
            s = parse_schema(f)
            if s['name']:
                schemas[s['name']] = s
    return schemas


# ---------- applies_when evaluation ----------

def eval_when(expr, ctx):
    expr = expr.strip()
    if not expr:
        return False
    m = re.match(r'^(\w+)\s*==\s*(.+)$', expr)
    if m:
        return ctx.get(m.group(1)) == m.group(2).strip()
    m = re.match(r'^(\w+)\s+in\s+\[(.+)\]$', expr)
    if m:
        values = [v.strip() for v in m.group(2).split(',')]
        return ctx.get(m.group(1)) in values
    m = re.match(r'^(\w+)\s*=~\s*(.+)$', expr)
    if m:
        text = ctx.get(m.group(1)) or ''
        try:
            return bool(re.search(m.group(2).strip(), text))
        except re.error:
            return False
    return False


# ---------- value validation ----------

def validate_value(name, value, spec):
    if value is None or value == '':
        return
    if isinstance(value, list):
        # Apply scalar constraints per-element. Skips list-of-mappings
        # (those are validated by their own schema, e.g. cadences).
        for i, item in enumerate(value):
            if isinstance(item, str):
                yield from validate_value(f"{name}[{i}]", item, spec)
        return
    if spec.get('type') == 'int' and not re.fullmatch(r'-?\d+', str(value).strip()):
        yield f"{name}: value {value!r} is not a whole number"
    constraint = spec.get('constraint', {})
    enum = constraint.get('enum')
    if enum and value not in enum:
        yield f"{name}: value {value!r} not in {enum}"
    regex = constraint.get('regex')
    if regex and not re.match('^' + regex + '$', value):
        yield f"{name}: value {value!r} does not match /{regex}/"
    min_length = constraint.get('min_length')
    if min_length is not None and len(value) < min_length:
        yield f"{name}: value {value!r} shorter than min={min_length}"
    if 'must_contain_digit' in constraint.get('flags', set()):
        if not any(c.isdigit() for c in value):
            yield f"{name}: value {value!r} must contain a digit"


def validate_cadences(cadences):
    if not isinstance(cadences, list):
        return
    seen = set()
    for idx, cad in enumerate(cadences):
        if not isinstance(cad, dict):
            continue
        prefix = f"cadences[{idx}]"
        for required in ('key', 'frequency', 'description'):
            if not cad.get(required):
                yield f"{prefix}: missing {required}"
        key = cad.get('key', '')
        if key:
            if key in seen:
                yield f"{prefix}: duplicate key {key!r}"
            seen.add(key)
            if not re.match(r'^[a-z_][a-z0-9_]*$', key):
                yield f"{prefix}: key {key!r} must be lowercase_with_underscores"
        freq = cad.get('frequency', '')
        if freq:
            try:
                int(freq)
            except (TypeError, ValueError):
                yield f"{prefix}: frequency {freq!r} must be an integer"


# ---------- cross-file (wikilink resolution) ----------

def wikilink_exists(target):
    """True if a wikilink target like 'Projects/SGB' or 'people/Charlie'
    names a thread or person file, spelt exactly so."""
    target = target.strip()
    if target.startswith(('Projects/', 'Processes/', 'Topics/')):
        return V.vault_file(f"threads/{target}.md") is not None
    if target.startswith('people/'):
        return V.vault_file(f"{target}.md") is not None
    return False


# ---------- file validation ----------

def find_file_schema(path, fm, schemas):
    """Match by filename + applies_when + (new) directory scope."""
    # `V.rel` resolves both sides: ADULTING_HOME is often reached through a
    # symlink (/tmp and /var are symlinks on macOS, and a synced vault is
    # frequently one), and an unresolved file under a resolved home is
    # relative to nothing, which used to match no schema at all.
    rel_str = V.rel(path)
    for s in schemas.values():
        if s['scope'] != 'file':
            continue
        # Directory scope (if set)
        sdir = s.get('directory', '')
        if sdir:
            top = rel_str.split(os.sep, 1)[0]
            if top != sdir:
                continue
        # Filename pattern
        fpattern = s.get('filename')
        if fpattern and not re.search(fpattern, path.name):
            continue
        applies = s.get('applies_when')
        if applies and not eval_when(applies, fm):
            continue
        return s
    return None


def validate_file(path, schemas, registry=None):
    path = Path(path)
    if not path.exists():
        yield (0, "file does not exist")
        return
    text = V.read_utf8(path)
    if text is None:
        # Every other command skips this file quietly; lint is where the
        # vault's health is reported, so here it is a violation.
        yield (0, "file is not valid UTF-8")
        return
    fm, body_start = parse_frontmatter(text)

    schema = find_file_schema(path, fm, schemas)
    if not schema:
        yield (0, "no matching file schema")
        return

    # Required fields.
    for fname, spec in schema['fields'].items():
        if spec['required'] and not fm.get(fname):
            yield (0, f"missing required field {fname!r} (per {schema['name']})")

    # Field values (scalars).
    for fname, value in fm.items():
        spec = schema['fields'].get(fname)
        if spec:
            for err in validate_value(fname, value, spec):
                yield (0, err)

    # Conditional rules.
    if schema['name'] == 'thread' and fm.get('status') == 'closed' and not fm.get('ended'):
        yield (0, "ended is required when status is closed")
    if schema['name'] == 'person' and fm.get('status') == 'closed' and not fm.get('ended'):
        yield (0, "ended is required when status is closed")

    # Cadences.
    if 'cadences' in fm:
        for err in validate_cadences(fm['cadences']):
            yield (0, err)

    # Wikilink resolution: thread field on logs (singular, scalar)
    if 'thread' in fm and isinstance(fm['thread'], str):
        target = wikilink_target(fm['thread'])
        if target and not wikilink_exists(target):
            yield (0, f"thread: wikilink {fm['thread']!r} does not resolve")

    # Wikilink resolution: threads list on notes (multi)
    if 'threads' in fm and isinstance(fm['threads'], list):
        for entry in fm['threads']:
            if not isinstance(entry, str):
                continue
            target = wikilink_target(entry)
            if target is None:
                yield (0, f"threads: entry {entry!r} is not a wikilink")
            elif not target.startswith(('Projects/', 'Processes/', 'Topics/')):
                yield (0, f"threads: wikilink {entry!r} must target Projects/X, Processes/X, or Topics/X")
            elif not wikilink_exists(target):
                yield (0, f"threads: wikilink {entry!r} does not resolve")

    # Wikilink resolution: people list (entries that ARE wikilinks)
    if 'people' in fm and isinstance(fm['people'], list):
        for entry in fm['people']:
            if not isinstance(entry, str):
                continue
            target = wikilink_target(entry)
            if target:
                if not target.startswith('people/'):
                    yield (0, f"people: wikilink {entry!r} should target 'people/...'")
                elif not wikilink_exists(target):
                    yield (0, f"people: wikilink {entry!r} does not resolve")
            # plain strings allowed (untracked attendees)

    # Time files: the body is a JSON tracker block, not line-oriented.
    if schema['name'] in RECORD_KINDS:
        yield from validate_record_block(text, path, schema['name'], registry)
        return

    # Body lines: line schemas (e.g. thread_entry on threads); ACTION/TASK on notes.
    line_schemas = [s for s in schemas.values() if s['scope'] == 'line']
    body_lines = text.split('\n')[body_start:]
    is_note = schema['name'] in ('note_meeting', 'note_correspondence', 'note_simple', 'log')
    for offset, line in enumerate(body_lines):
        line_no = body_start + offset + 1

        # Line schemas (thread_entry etc.)
        for ls in line_schemas:
            if not eval_when(ls.get('applies_when', ''), {'line': line}):
                continue
            shape = ls.get('shape')
            if not shape:
                continue
            m = re.match(shape, line)
            if not m:
                yield (line_no, f"line does not conform to {ls['name']} shape /{shape}/")
                continue
            captures = m.groupdict()
            for fname, spec in ls['fields'].items():
                captured = captures.get(fname) or ''
                if spec['required'] and not captured:
                    yield (line_no, f"{ls['name']}.{fname}: missing")
                elif captured:
                    for err in validate_value(f"{ls['name']}.{fname}", captured, spec):
                        yield (line_no, err)

            # task_anchor: per-line cross-cuts (kind/end/assignee) and
            # register for vault-wide checks (uniqueness, depends, cycles).
            if ls['name'] == 'task_anchor':
                for err in _task_anchor_per_line(captures):
                    yield (line_no, err)
                if registry is not None:
                    _task_anchor_register(registry, captures, path, line_no)

        # ACTION: lines (notes only)
        if is_note:
            action = V.parse_action(line)
            if action:
                if not action.body:
                    yield (line_no, "ACTION: missing description")
                if action.assignee and not V.person_exists(action.assignee):
                    yield (line_no, f"ACTION: assignee {action.assignee!r} does not "
                                    f"resolve to people/{action.assignee}.md")
                for err in action.errors:
                    yield (line_no, f"ACTION: {err}")


# ---------- hours_file and payments_file: the JSON record block ----------

ISO_RE = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$')

# What each kind of record file holds, and the words its messages use.
# currency is optional on an hours entry: absent means unbilled time.
RECORD_KINDS = {
    'hours_file': {'fence': V.HOURS.fence, 'key': V.HOURS.key, 'block': 'tracker',
                   'json': 'tracker JSON', 'fields': ('name', 'startTime', 'endTime', 'id', 'rate'),
                   'times': ('startTime', 'endTime')},
    'payments_file': {'fence': V.PAYMENTS.fence, 'key': V.PAYMENTS.key, 'block': 'payments',
                      'json': 'JSON', 'fields': ('id', 'received', 'amount', 'currency'),
                      'times': ('received',)},
}


def read_block(text, label):
    """The records in a file's JSON block, checked for shape.

    Returns (errors, fence_line, records). `records` is None when there is
    nothing further to check: no block, an empty one, or JSON of the wrong
    shape.
    """
    kind = RECORD_KINDS[label]
    fence, key = kind['fence'], kind['key']
    lines = text.split('\n')
    blk = V.find_block(lines, fence)
    if blk is None:
        return [(0, f"{label}: no {fence} block")], 0, None
    errors = []
    if sum(1 for line in lines if line.rstrip() == fence) > 1:
        errors.append((blk[0] + 1, f"{label}: more than one {kind['block']} block"))

    fence_line = blk[0] + 1
    raw = '\n'.join(lines[blk[0] + 1:blk[1]]).strip()
    if not raw:
        return errors, fence_line, None  # an empty block is a legitimately empty file
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        errors.append((fence_line, f"{label}: {kind['json']} does not parse: {e}"))
        return errors, fence_line, None
    if not isinstance(data, dict) or not isinstance(data.get(key), list):
        errors.append((fence_line, f"{label}: {kind['json']} must be {{\"{key}\": [...]}}"))
        return errors, fence_line, None
    return errors, fence_line, data[key]


def validate_record_block(text, path, label, registry=None):
    """Check each record in an hours or payments file. Every problem is
    reported against the line of the block's opening fence."""
    kind = RECORD_KINDS[label]
    errors, fence_line, records = read_block(text, label)
    yield from errors
    for idx, r in enumerate(records or []):
        # `tag` is bound now, not when `problem` is called, so the message
        # names the record it was made for.
        def problem(message, tag=f"{kind['key']}[{idx}]"):
            return (fence_line, f"{label}: {tag}{message}")

        if not isinstance(r, dict):
            yield problem(" is not an object")
            continue
        for f in kind['fields']:
            if r.get(f) in (None, ''):
                yield problem(f".{f}: missing")
        rid = r.get('id')
        if rid and not re.match(r'^[0-9a-f]{8}$', str(rid)):
            yield problem(f".id: {rid!r} is not 8 hex chars")
        for f in kind['times']:
            v = r.get(f)
            if v and not ISO_RE.match(str(v)):
                yield problem(f".{f}: {v!r} is not ISO 8601 UTC")
        st, en = r.get('startTime'), r.get('endTime')
        if st and en and ISO_RE.match(str(st)) and ISO_RE.match(str(en)) and en < st:
            yield problem(": endTime precedes startTime")
        ccy = r.get('currency')
        if ccy and not V.is_currency_code(str(ccy)):
            yield problem(f".currency: {ccy!r} is not a 3-letter ISO code")
        if label == 'hours_file':
            rate = r.get('rate')
            if rate is not None and not isinstance(rate, int):
                yield problem(f".rate: {rate!r} is not an integer")
        else:
            amt = r.get('amount')
            if amt is not None:
                if not isinstance(amt, (int, float)) or isinstance(amt, bool):
                    yield problem(f".amount: {amt!r} is not a number")
                elif amt <= 0:
                    yield problem(".amount: must be positive")
        if registry is not None and rid:
            registry.setdefault('record_ids', {}).setdefault(str(rid), []).append(
                (path, fence_line))


def report_duplicates(groups, wording):
    """A value that should be unique across the vault, and is not, is
    reported at every place it occurs, each one pointing at the others.
    `groups` maps the value to the (path, line) pairs holding it."""
    for value, hits in groups.items():
        if len(hits) <= 1:
            continue
        for path, ln in hits:
            others = ', '.join(f"{V.full(p)}:{n}" for p, n in hits if (p, n) != (path, ln))
            yield path, ln, f"{wording} {value!r} duplicated at {others}"


def cross_check_record_ids(registry):
    """Hours and payment ids must be unique across the whole vault."""
    yield from report_duplicates(registry.get('record_ids', {}), 'record id')


# ---------- task_anchor: per-line + vault-wide rules ----------

def _task_anchor_per_line(captures):
    """Cross-cuts that need the full capture dict but are scoped to one line."""
    kind = captures.get('kind')
    entry = captures.get('entry')
    end = captures.get('end')
    assignee = captures.get('assignee')

    if kind == 'DONE' and not end:
        yield "task_anchor: kind=DONE requires 'end'"
    if end and entry and end < entry:
        yield f"task_anchor: end {end!r} precedes entry {entry!r}"
    if assignee:
        if not V.person_exists(assignee):
            yield f"task_anchor.assignee: {assignee!r} does not resolve to people/{assignee}.md"


def _task_anchor_register(registry, captures, path, line_no):
    uuid8 = captures.get('uuid')
    if not uuid8:
        return
    registry['by_uuid'].setdefault(uuid8, []).append((path, line_no))
    deps_raw = captures.get('depends') or ''
    if deps_raw:
        deps = [d for d in deps_raw.split(',') if d]
        if deps:
            registry['depends_edges'].append((uuid8, deps, path, line_no))


def cross_check_tasks(registry):
    """Yield (path, line_no, msg) for vault-wide task_anchor rules.
    Runs after every file has been walked so the registry is complete."""
    by_uuid = registry['by_uuid']

    yield from report_duplicates(by_uuid, 'task_anchor.uuid:')

    # Dependency targets must resolve.
    known = set(by_uuid)
    for _src, deps, path, ln in registry['depends_edges']:
        for d in deps:
            if d not in known:
                yield path, ln, f"task_anchor.depends: {d!r} does not resolve to any anchor"

    # Cycle detection via iterative DFS coloring. Self-loops included.
    graph = {}
    for src, deps, _, _ in registry['depends_edges']:
        graph.setdefault(src, []).extend(deps)
    src_locations = {}
    for src, _deps, path, ln in registry['depends_edges']:
        src_locations.setdefault(src, (path, ln))
    seen = set()
    for cycle in _find_cycles(graph):
        canon = tuple(_rotate_to_min(cycle))
        if canon in seen:
            continue
        seen.add(canon)
        first = cycle[0]
        path, ln = src_locations.get(first, (None, 0))
        if path is not None:
            yield path, ln, ("task_anchor.depends: cycle: "
                             + ' -> '.join(list(cycle) + [cycle[0]]))


def _find_cycles(graph):
    """Yield each cycle as a list of uuid8s in traversal order. Uses
    iterative DFS with white/gray/black coloring; on a gray hit, splice
    out the cycle from the path stack."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}
    for node in list(graph):
        if color[node] != WHITE:
            continue
        # (node, iter_over_neighbors); path tracks the current DFS chain.
        stack = [(node, iter(graph.get(node, [])))]
        path = [node]
        color[node] = GRAY
        while stack:
            cur, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                color[cur] = BLACK
                stack.pop()
                path.pop()
                continue
            if nxt not in color:
                # Unknown target — handled by the dangling-depends check;
                # don't traverse into it for cycle detection.
                continue
            c = color[nxt]
            if c == WHITE:
                color[nxt] = GRAY
                path.append(nxt)
                stack.append((nxt, iter(graph.get(nxt, []))))
            elif c == GRAY:
                # Cycle: from where nxt appears in path to the end.
                idx = path.index(nxt)
                yield path[idx:]
            # BLACK: already-finished node; not a cycle through here.


def _rotate_to_min(seq):
    """Canonical rotation so equivalent cycles dedupe. Rotates so the
    lexicographically smallest element comes first."""
    if not seq:
        return seq
    i = min(range(len(seq)), key=lambda k: seq[k])
    return list(seq[i:]) + list(seq[:i])


# ---------- file discovery ----------

def discover_files():
    for sub in ('notes', 'threads', 'people', 'logs', 'hours', 'payments'):
        d = V.vault_home() / sub
        if not d.is_dir():
            continue
        for root, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if not x.startswith('.')]
            for f in sorted(files):
                if f.startswith('.'):
                    continue
                full = Path(root) / f
                if full.suffix == '.md':
                    yield full


# ---------- main ----------

def main():
    parser = V.command_parser('lint', "Validate adulting files against schemas.")
    parser.add_argument('paths', nargs='*',
                        help='Files to validate (default: walk ~/vault/).')
    parser.add_argument('--schemas', default=str(SCHEMAS_DIR),
                        help=f'Schemas directory (default: {SCHEMAS_DIR}).')
    parser.add_argument('--quiet', action='store_true',
                        help='Suppress per-violation output.')
    args = V.parse_command(parser, subcommand_required=False)

    schemas = load_schemas(Path(args.schemas))
    if not schemas:
        V.die(f"no schemas loaded from {args.schemas}", code=2)

    # Resolved, so a path given relative to the caller's directory is
    # checked exactly as the same file given absolutely.
    files = [Path(p).resolve() for p in args.paths] if args.paths else list(discover_files())

    registry = {'by_uuid': {}, 'depends_edges': [], 'record_ids': {}}
    total = 0
    for f in files:
        for line_no, msg in validate_file(f, schemas, registry=registry):
            total += 1
            if not args.quiet:
                print(f"{V.full(f)}:{line_no}: {msg}")

    for path, line_no, msg in cross_check_tasks(registry):
        total += 1
        if not args.quiet:
            print(f"{V.full(path)}:{line_no}: {msg}")

    for path, line_no, msg in cross_check_record_ids(registry):
        total += 1
        if not args.quiet:
            print(f"{V.full(path)}:{line_no}: {msg}")

    if not args.quiet:
        print(f"\n{len(files)} file(s) checked. {total} violation(s).")
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main())
