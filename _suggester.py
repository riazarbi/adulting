#!/usr/bin/env python3
"""Rules-only capture suggester.

Takes a raw quick-capture string and proposes a structured `buffer add-*`
command. Stdlib only. Designed to be scored against eval-v1.jsonl before
deciding whether to escalate to an LLM-backed suggester.

Pipeline:
    tokenize → person match → date parse → priority detect → intent classify
        → out-of-scope guard → thread rank → body construct → assemble result

Confidence is implicit: if any required step fails to produce a high-signal
answer, the whole suggestion collapses to UNKNOWN (`add`) rather than
guessing. Rejection is free downstream, so we prefer to bail than mislead.
"""

import json
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

HOME = Path(os.environ.get('ADULTING_HOME', os.path.expanduser('~/vault')))
THREADS_DIR = HOME / 'threads'
PEOPLE_DIR = HOME / 'people'
LOGS_DIR = HOME / 'logs'
NOTES_DIR = HOME / 'notes'

# Tokens that we never want to count as content (too generic to rank threads).
STOPWORDS = {
    'a', 'an', 'and', 'as', 'at', 'be', 'by', 'do', 'for', 'from', 'i', 'if',
    'in', 'is', 'it', 'me', 'my', 'no', 'of', 'on', 'or', 'so', 'the', 'this',
    'to', 'up', 'was', 'we', 'with', 'you', 'your', 'are', 'have', 'had',
    'just', 'about', 'over', 'into', 'out', 'next', 'last', 'today',
    'tomorrow', 'yesterday', 'week', 'month', 'year', 'monday', 'tuesday',
    'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'now', 'then',
    'when', 'where', 'what', 'who', 'why', 'how', 'all', 'any', 'some',
}

IMPERATIVE_VERBS = {
    'add', 'ask', 'book', 'build', 'buy', 'call', 'check', 'create', 'do',
    'drop', 'email', 'finish', 'fit', 'fix', 'forward', 'get', 'have',
    'install', 'investigate', 'make', 'meet', 'pick', 'pay', 'plan',
    'prepare', 'reach', 'read', 'refactor', 'remove', 'reply', 'research',
    'review', 'run', 'schedule', 'send', 'sign', 'start', 'submit', 'take',
    'visit', 'write',
}

PAST_TENSE_MARKERS = {
    'sent', 'called', 'met', 'bought', 'did', 'wrote', 'paid',
    'visited', 'finished', 'asked', 'forwarded', 'reviewed', 'noticed',
    'spoke', 'talked', 'saw', 'heard', 'thought', 'realised', 'realized',
    'had', 'was', 'were',
    # 'read' is intentionally omitted — it's the verb form most often used
    # imperatively in this vault ("Read https://..." = an action item).
}

REF_MARKERS = {'link', 'connects', 'connect', 'relates', 'see-also'}

OUT_OF_SCOPE_PATTERNS = [
    re.compile(r'^\s*(create|make|add)\s+(a\s+)?(new\s+)?(person|people)\b', re.I),
    re.compile(r'^\s*(start|make|create)\s+(a\s+)?(new\s+)?thread\b', re.I),
    re.compile(r'^\s*(show|list|find|search)\b', re.I),
    re.compile(r'^\s*what\b', re.I),
    re.compile(r'^\s*(when|where|who|why|how)\b', re.I),
]

PRIORITY_HIGH = re.compile(r'\b(URGENT|ASAP|!!+)\b', re.I)
PRIORITY_LOW = re.compile(r'\b(low(\s+priority)?|whenever)\b', re.I)

DUE_HINTS = re.compile(r'\b(by|before)\s+', re.I)

WEEKDAY_IDX = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
               'friday': 4, 'saturday': 5, 'sunday': 6}

MONTH_IDX = {'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5,
             'june': 6, 'july': 7, 'august': 8, 'september': 9,
             'october': 10, 'november': 11, 'december': 12}


# ---------- vault loaders ----------

def load_threads():
    threads = []
    if not THREADS_DIR.exists():
        return threads
    for kind_dir in sorted(THREADS_DIR.iterdir()):
        if not kind_dir.is_dir():
            continue
        for f in sorted(kind_dir.glob('*.md')):
            threads.append(f"{kind_dir.name}/{f.stem}")
    return threads


def load_people():
    if not PEOPLE_DIR.exists():
        return []
    return sorted(f.stem for f in PEOPLE_DIR.glob('*.md'))


def _tokenize(text):
    return [w for w in re.findall(r"[A-Za-z0-9']+", text.lower())
            if w not in STOPWORDS and len(w) > 1]


def build_thread_index(threads):
    """Return {thread: {token: count}} from thread file + logs + notes + the
    thread name itself (so e.g. "SANA" matches Projects/SANA Partners even
    when no log mentions it). Heavy weight on the thread name to make
    explicit mentions decisive.
    """
    index = {t: {} for t in threads}

    def bump(thread, tokens, weight=1):
        bucket = index[thread]
        for tok in tokens:
            bucket[tok] = bucket.get(tok, 0) + weight

    for thread in threads:
        name_tokens = _tokenize(thread.split('/', 1)[1])
        bump(thread, name_tokens, weight=10)
        thread_file = THREADS_DIR / f"{thread}.md"
        if thread_file.exists():
            bump(thread, _tokenize(thread_file.read_text(encoding='utf-8', errors='ignore')))
        log_dir = LOGS_DIR / thread
        if log_dir.exists():
            for log in log_dir.glob('*.md'):
                bump(thread, _tokenize(log.read_text(encoding='utf-8', errors='ignore')))

    thread_link_re = re.compile(r'\[\[((?:Projects|Processes|Topics)/[^\]]+)\]\]')
    if NOTES_DIR.exists():
        for note in NOTES_DIR.glob('*.md'):
            try:
                text = note.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            head = text[:1500]
            linked = set(thread_link_re.findall(head))
            if not linked:
                continue
            toks = _tokenize(text)
            for t in linked:
                if t in index:
                    bump(t, toks)
    return index


def build_idf(thread_index):
    """Number of threads each token appears in (document frequency)."""
    df = {}
    for thread, freq in thread_index.items():
        for tok in freq:
            df[tok] = df.get(tok, 0) + 1
    return df


def build_thread_lengths(thread_index):
    """Sum of frequencies per thread (treat as 'document length' for BM25)."""
    return {t: sum(f.values()) for t, f in thread_index.items()}


# ---------- person matching ----------

def match_person(text, people):
    """Return list of (matched_name, span_in_text) pairs.

    Strategy: scan word tokens; for each token, try exact-prefix and
    fuzzy-token match against people's first names and full names. Returns
    matches in order of appearance. Multiple matches possible.
    """
    matches = []
    # Cheap pre-pass: for each person, check if any token of their name
    # appears in the input as a standalone word.
    text_words = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    text_words_lower = [w.lower() for w in text_words]
    for person in people:
        parts = person.split()
        first = parts[0].lower()
        # Full-name substring (e.g. "Eddie van der Weide" appears verbatim).
        if person.lower() in text.lower():
            matches.append((person, text.lower().index(person.lower())))
            continue
        # First-name match.
        if first in text_words_lower:
            idx = text.lower().index(first)
            # Disambiguate when multiple people share first name: prefer
            # the one whose full name shares more tokens with the surrounding
            # text. Caller can rank candidates later.
            matches.append((person, idx))
    # Deduplicate while keeping first-occurrence order, and resolve same-text
    # collisions (e.g. two Berns) by keeping the one with the highest
    # full-name token overlap with the input.
    by_first = {}
    for name, idx in matches:
        first = name.split()[0].lower()
        if first not in by_first:
            by_first[first] = []
        by_first[first].append((name, idx))
    resolved = []
    text_tokens = set(_tokenize(text))
    for first, candidates in by_first.items():
        if len(candidates) == 1:
            resolved.append(candidates[0])
        else:
            scored = []
            for name, idx in candidates:
                surname_tokens = set(_tokenize(' '.join(name.split()[1:])))
                overlap = len(surname_tokens & text_tokens)
                scored.append((overlap, name, idx))
            scored.sort(key=lambda s: (-s[0], s[1]))
            resolved.append((scored[0][1], scored[0][2]))
    resolved.sort(key=lambda x: x[1])
    return [name for name, _ in resolved]


# ---------- date parsing ----------

def parse_dates(text, today):
    """Return {'due': 'YYYY-MM-DD' | None, 'scheduled': 'YYYY-MM-DD' | None,
                'spans': [(start, end), ...]} where spans cover the matched
    date phrases (used to strip them from the body).
    """
    result = {'due': None, 'scheduled': None, 'spans': []}
    matched_date = None
    date_decided = False  # True once a branch sets due/scheduled itself

    iso = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
    if iso:
        matched_date = iso.group(1)
        result['spans'].append((iso.start(), iso.end()))

    if matched_date is None:
        m = re.search(r'\btomorrow\b', text, re.I)
        if m:
            matched_date = (today + timedelta(days=1)).isoformat()
            result['spans'].append((m.start(), m.end()))

    if matched_date is None:
        m = re.search(r'\btoday\b', text, re.I)
        if m:
            matched_date = today.isoformat()
            result['spans'].append((m.start(), m.end()))

    if matched_date is None:
        # "next <weekday>" / bare "<weekday>" -> next occurrence (not today)
        m = re.search(r'\b(?:next\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', text, re.I)
        if m:
            target = WEEKDAY_IDX[m.group(1).lower()]
            days_ahead = (target - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            matched_date = (today + timedelta(days=days_ahead)).isoformat()
            result['spans'].append((m.start(), m.end()))

    if matched_date is None:
        m = re.search(r'\bnext\s+week\b', text, re.I)
        if m:
            days_ahead = (0 - today.weekday()) % 7  # next Monday
            if days_ahead == 0:
                days_ahead = 7
            matched_date = (today + timedelta(days=days_ahead)).isoformat()
            result['spans'].append((m.start(), m.end()))

    if matched_date is None:
        m = re.search(r'\bend\s+of\s+week\b', text, re.I)
        if m:
            days_ahead = (4 - today.weekday()) % 7  # Friday
            if days_ahead == 0:
                days_ahead = 7
            matched_date = (today + timedelta(days=days_ahead)).isoformat()
            result['spans'].append((m.start(), m.end()))

    if matched_date is None:
        # "before/by/in <month>" → first of that month. The preposition is
        # inside the matched span (unlike "by Friday" where "by" sits in the
        # prefix), so due/scheduled is decided here directly.
        m = re.search(r'\b(before|by|end\s+of|in|during)\s+'
                      r'(january|february|march|april|may|june|july|august|'
                      r'september|october|november|december)\b', text, re.I)
        if m:
            month = MONTH_IDX[m.group(2).lower()]
            year = today.year if month > today.month else today.year + 1
            matched_date = date(year, month, 1).isoformat()
            result['spans'].append((m.start(), m.end()))
            if m.group(1).lower() in ('before', 'by', 'end of'):
                result['due'] = matched_date
            else:
                result['scheduled'] = matched_date
            date_decided = True

    if matched_date is not None and not date_decided:
        # Decide due vs scheduled: "by/before <date>" → due, else scheduled.
        # Look at text immediately before the matched span.
        start = result['spans'][0][0]
        prefix = text[:start]
        if DUE_HINTS.search(prefix[-20:]):
            result['due'] = matched_date
            hint = DUE_HINTS.search(prefix)
            if hint:
                result['spans'].insert(0, (hint.start(), hint.end()))
        else:
            result['scheduled'] = matched_date
    return result


# ---------- priority detection ----------

def detect_priority(text):
    if PRIORITY_HIGH.search(text):
        return 'H'
    if PRIORITY_LOW.search(text):
        return 'L'
    return None


# ---------- intent classification ----------

def classify_intent(text):
    """Returns one of: 'add' (UNKNOWN), 'add-text', 'add-ref', 'add-action'.

    Strategy: out-of-scope patterns first (questions, create-person, etc.).
    Then scan the first ~4 words: if a past-tense verb appears, classify as
    TEXT (the input is reporting something that happened). If an imperative
    verb leads or appears early, classify as ACTION. Default by length: short
    sentences are likely capture-style actions; long ones are observations.
    """
    stripped = text.strip()
    for pat in OUT_OF_SCOPE_PATTERNS:
        if pat.search(stripped):
            return 'add'
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", stripped)
    if not words:
        return 'add'
    head = [w.lower() for w in words[:4]]
    if head[0] in REF_MARKERS:
        return 'add-ref'
    # Past-tense anywhere in the first few words wins over a later imperative
    # ("Bern called about the fund" → TEXT, not ACTION).
    if any(w in PAST_TENSE_MARKERS for w in head):
        return 'add-text'
    if head[0] in IMPERATIVE_VERBS:
        return 'add-action'
    if any(w in IMPERATIVE_VERBS for w in head[:2]):
        return 'add-action'
    if len(words) <= 8 and not stripped.endswith('.'):
        return 'add-action'
    return 'add-text'


# ---------- thread ranking ----------

def rank_threads(text, thread_index, df, person_matches=(), lengths=None):
    """BM25 ranking with a person-match boost.

    Length normalization is the key fix: without it, the longest-history
    thread (here, SGB with years of journal content) wins every contest on
    generic tokens because its raw frequencies dominate. BM25 divides by a
    length factor so a rare-term hit in a small thread can outweigh many
    common-term hits in a large one.

    Person-match boost: a matched first name contributes BM25 weight * 3
    (treated as an extra "free" hit) — pins the thread when an unambiguous
    person name appears in the input.
    """
    import math
    tokens = _tokenize(text)
    if not tokens:
        return []
    if lengths is None:
        lengths = build_thread_lengths(thread_index)
    n = max(1, len(thread_index))
    avgdl = sum(lengths.values()) / max(1, len(lengths))
    # b tuned downward (textbook default 0.75) because some threads in this
    # vault are tiny (<2k tokens) vs others enormous (>20k); the default
    # over-rewards the small ones, letting them win on rare-term matches
    # even when the large thread has far more occurrences.
    k1, b = 1.5, 0.4
    scores = {}
    for thread, freq in thread_index.items():
        s = 0.0
        dl = lengths.get(thread, 0)
        norm = 1 - b + b * dl / max(avgdl, 1)
        for tok in tokens:
            if tok in freq:
                idf = math.log(1 + n / df.get(tok, 1))
                tf = freq[tok]
                bm = tf * (k1 + 1) / (tf + k1 * norm)
                s += idf * bm
                # Unique-thread bonus: a token appearing in exactly one
                # thread. Empirically right ~5/6 of the time on this vault
                # (squash→Wellness, zoiper→Homephone, vodacom→Agent,
                # aircon→Syncro EV, dinner→Relationships all correct); the
                # occasional miss (a generic word that happens to appear
                # once, e.g. "night") is accepted — rejection drops to
                # UNKNOWN at no cost.
                if df.get(tok, 0) == 1:
                    s += 5.0
        if person_matches:
            for person in person_matches:
                first = person.split()[0].lower()
                if first in freq:
                    name_idf = math.log(1 + n / max(df.get(first, 1), 1))
                    tf = freq[first]
                    bm = tf * (k1 + 1) / (tf + k1 * norm)
                    s += name_idf * bm * 3.0
        if s > 0:
            scores[thread] = s
    return sorted(scores.items(), key=lambda kv: -kv[1])


# ---------- body construction ----------

def build_body(text, person_matches, date_spans, priority_spans, assignee=None):
    """Remove date/priority phrases, wikilink first-name person references,
    and apply the assignee prefix if one was extracted.
    Returns the cleaned body string.
    """
    body = text
    # Strip spans (date phrases, priority markers) — work from end to start
    # to keep offsets stable.
    spans = sorted(set(date_spans + priority_spans), key=lambda s: -s[0])
    for start, end in spans:
        body = body[:start] + body[end:]
    body = re.sub(r'\s+', ' ', body).strip()
    body = re.sub(r'^[\s\-:,]+', '', body)
    body = re.sub(r'[\s\-:,]+$', '', body)

    # Wikilink references to known people. Prefer full-name match if present;
    # otherwise replace the first-name reference. Case-insensitive matching
    # against the body, but the canonical full name (with original casing)
    # always lives inside the [[people/...]] wikilink.
    for person in person_matches:
        full_pat = re.compile(rf'\b{re.escape(person)}\b', re.IGNORECASE)
        if full_pat.search(body):
            body = full_pat.sub(f'[[people/{person}]]', body, count=1)
            continue
        first = person.split()[0]
        first_pat = re.compile(rf'\b{re.escape(first)}\b', re.IGNORECASE)
        body = first_pat.sub(f'[[people/{person}]]', body, count=1)

    if assignee:
        body = f'({assignee}) {body}'
    return body


def detect_assignee(text):
    """`Name: rest` at start of input → (Name, rest_text). Returns
    (None, text) if no match. Case-insensitive — the actual is-this-a-person
    check happens later via the people directory lookup, so a false prefix
    like "urgent:" just fails to resolve and gets left in the body for
    priority/other detectors to handle.
    """
    m = re.match(r'^\s*([A-Za-z][A-Za-z\-]+(?:\s+[A-Za-z][A-Za-z\-]+)?)\s*:\s+(.+)$', text)
    if not m:
        return None, text
    return m.group(1).strip(), m.group(2).strip()


# ---------- explicit thread directive ----------

def detect_explicit_thread(text, threads):
    """Honor an explicit `Kind/Name` thread the user typed into the input,
    e.g. a trailing `- topics/relationships` or an inline `[[Projects/X]]`.

    Returns (thread, start, end): the resolved thread and the [start, end)
    span of the literal directive (including a `[[`/`]]` wrapper and any
    leading ` - ` separator) so the caller can strip it from the body.
    Returns (None, None, None) if no directive is found.

    The kind (Projects/Processes/Topics) is required — this keeps URL paths
    like `tech/blogs` from false-matching — but it is *not* authoritative
    for resolution: users misremember Topic vs Process, so the NAME part is
    matched against the thread list and the kind is just a gate.
    """
    by_name = {}
    for t in threads:
        by_name.setdefault(t.split('/', 1)[1].lower(), t)
    pat = re.compile(r'(\[\[)?\s*\b(projects|processes|topics)/'
                     r'([A-Za-z0-9][\w ]*)', re.I)
    for m in pat.finditer(text):
        name_field = re.sub(r'\s*\]?\]?\s*$', '', m.group(3))
        words = name_field.lower().split()
        for k in range(len(words), 0, -1):
            cand = ' '.join(words[:k])
            if cand in by_name:
                # End of the directive: end of the k-th word in the name.
                name_start = m.start(3)
                wm = re.match(r'\s*'.join(re.escape(w) for w in name_field.split()[:k]),
                              text[name_start:], re.I)
                end = name_start + (wm.end() if wm else len(name_field))
                tb = re.match(r'\s*\]\]', text[end:])
                if tb:
                    end += tb.end()
                # Extend start backward over a ` - ` / `–` / `[[` separator.
                start = m.start()
                sep = re.search(r'\s*[-–—]\s*$', text[:start])
                if sep:
                    start = sep.start()
                return by_name[cand], start, end
    return None, None, None


# ---------- top-level suggester ----------

def suggest(raw_text, today=None, threads=None, people=None, thread_index=None, df=None, lengths=None):
    if today is None:
        today = date.today()
    if threads is None:
        threads = load_threads()
    if people is None:
        people = load_people()
    if thread_index is None:
        thread_index = build_thread_index(threads)
    if df is None:
        df = build_idf(thread_index)
    if lengths is None:
        lengths = build_thread_lengths(thread_index)

    result = {
        'subcmd': 'add',
        'thread': None,
        'body': raw_text,
        'assignee': None,
        'due': None,
        'scheduled': None,
        'priority': None,
        'ref_target': None,
        'ref_summary': None,
    }

    intent = classify_intent(raw_text)
    if intent == 'add':
        return result

    # Explicit thread directive: if the user typed `Kind/Name` (e.g. a
    # trailing `- topics/relationships`), honor it verbatim and strip it
    # from the working text so it doesn't pollute body or ranking.
    explicit_thread, ex_start, ex_end = detect_explicit_thread(raw_text, threads)
    working_text = raw_text
    if explicit_thread:
        working_text = (raw_text[:ex_start] + ' ' + raw_text[ex_end:]).strip()

    # Assignee extraction (only meaningful for actions).
    assignee = None
    body_text = working_text
    if intent == 'add-action':
        a, rest = detect_assignee(working_text)
        if a:
            # Confirm the assignee resolves to a real person.
            for person in people:
                if person.lower().startswith(a.lower()):
                    assignee = person
                    body_text = rest
                    break

    person_matches = match_person(body_text, people)

    dates = parse_dates(body_text, today)
    priority = detect_priority(body_text)

    priority_spans = []
    for pat in (PRIORITY_HIGH, PRIORITY_LOW):
        for m in pat.finditer(body_text):
            priority_spans.append((m.start(), m.end()))

    if explicit_thread:
        # User told us the thread — no ranking, no confidence guard.
        top_thread = explicit_thread
    else:
        ranked = rank_threads(body_text, thread_index, df, person_matches, lengths)
        if not ranked:
            return result
        top_thread, top_score = ranked[0]
        # Bail to UNKNOWN if top score is weak. BM25 scores are typically
        # 1-10 per matching rare term, so 1.5 is a reasonable floor.
        if top_score < 1.5:
            return result

    body = build_body(body_text, person_matches, dates['spans'], priority_spans, assignee)
    if intent == 'add-ref':
        # REF target resolution is not implemented in v1 — without a target
        # the suggestion can't be a valid `buffer add-ref` call. Demote to
        # UNKNOWN so the user can convert it manually later.
        return result

    result.update({
        'subcmd': intent,
        'thread': top_thread,
        'body': body,
        'assignee': assignee,
        'due': dates['due'],
        'scheduled': dates['scheduled'],
        'priority': priority,
    })
    return result


# ---------- CLI ----------

def main():
    import argparse
    p = argparse.ArgumentParser(description="Rules-only capture suggester.")
    p.add_argument('text', help="Raw capture string.")
    p.add_argument('--today', help="Override today's date (YYYY-MM-DD).")
    args = p.parse_args()
    today = date.fromisoformat(args.today) if args.today else date.today()
    out = suggest(args.text, today=today)
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
