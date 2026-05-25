#!/usr/bin/env python3
"""Score the rules suggester against eval-v1.jsonl.

Runs `suggest()` on each case (with today pinned to 2026-05-19 so date
expectations remain stable) and reports per-case + aggregate metrics.

Five dimensions per case:
    shape   — output is well-formed (always true for this suggester)
    subcmd  — predicted subcommand matches expected
    thread  — predicted thread matches expected (or both None for out-of-scope)
    person  — assignee + body-wikilinks match expected
    dates   — due/scheduled match expected (both null if neither expected)

For out-of-scope cases (in_scope=false), "correct" means subcmd==add and
thread is None — i.e. the suggester correctly bailed.
"""

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from _suggester import (suggest, load_threads, load_people, build_thread_index,
                        build_idf, build_thread_lengths)  # noqa: E402

TODAY = date(2026, 5, 19)
EVAL_FILE = HERE / 'eval-v1.jsonl'

WIKILINK_RE = re.compile(r'\[\[people/([^\]]+)\]\]')


def extract_wikilinks(body):
    if not body:
        return set()
    return set(WIKILINK_RE.findall(body))


def score_case(case, prediction):
    dims = {}
    dims['shape'] = isinstance(prediction, dict)
    dims['subcmd'] = prediction['subcmd'] == case['subcmd']
    dims['thread'] = prediction['thread'] == case['thread']

    expected_assignee = case.get('assignee')
    expected_links = extract_wikilinks(case.get('body') or '')
    pred_links = extract_wikilinks(prediction.get('body') or '')
    dims['person'] = (
        prediction.get('assignee') == expected_assignee
        and pred_links == expected_links
    )

    dims['dates'] = (
        prediction.get('due') == case.get('due')
        and prediction.get('scheduled') == case.get('scheduled')
    )

    dims['priority'] = prediction.get('priority') == case.get('priority')

    dims['full_match'] = all(
        dims[k] for k in ('shape', 'subcmd', 'thread', 'person', 'dates', 'priority')
    )
    return dims


def main():
    threads = load_threads()
    people = load_people()
    thread_index = build_thread_index(threads)
    df = build_idf(thread_index)
    lengths = build_thread_lengths(thread_index)
    if not threads:
        print(f"warning: no threads found under {Path(os.environ.get('ADULTING_HOME', '~/vault')).expanduser() / 'threads'} "
              f"(set ADULTING_HOME if vault is elsewhere)", file=sys.stderr)

    cases = [json.loads(line) for line in EVAL_FILE.read_text().splitlines() if line.strip()]

    per_case = []
    for case in cases:
        prediction = suggest(case['raw'], today=TODAY, threads=threads,
                             people=people, thread_index=thread_index, df=df,
                             lengths=lengths)
        dims = score_case(case, prediction)
        per_case.append((case, prediction, dims))

    # Per-case report
    print("=" * 100)
    print(f"{'ID':>3}  {'Scope':<8} {'Full':<5} {'Sub':<4} {'Thr':<4} {'Per':<4} {'Dat':<4} {'Pri':<4}  raw")
    print("-" * 100)
    for case, _pred, dims in per_case:
        scope = 'in' if case['in_scope'] else 'oos'
        line = (
            f"{case['id']:>3}  {scope:<8} "
            f"{'✓' if dims['full_match'] else '✗':<5} "
            f"{'✓' if dims['subcmd'] else '✗':<4} "
            f"{'✓' if dims['thread'] else '✗':<4} "
            f"{'✓' if dims['person'] else '✗':<4} "
            f"{'✓' if dims['dates'] else '✗':<4} "
            f"{'✓' if dims['priority'] else '✗':<4}  "
            f"{case['raw'][:60]}"
        )
        print(line)

    # Aggregates split by in-scope vs out-of-scope
    in_scope = [(c, p, d) for c, p, d in per_case if c['in_scope']]
    oos = [(c, p, d) for c, p, d in per_case if not c['in_scope']]

    def pct(items, key):
        if not items:
            return 0.0
        return 100.0 * sum(1 for _, _, d in items if d[key]) / len(items)

    print("=" * 100)
    print(f"In-scope ({len(in_scope)} cases):")
    print(f"  full match:  {pct(in_scope, 'full_match'):5.1f}%")
    print(f"  subcmd:      {pct(in_scope, 'subcmd'):5.1f}%")
    print(f"  thread:      {pct(in_scope, 'thread'):5.1f}%")
    print(f"  person:      {pct(in_scope, 'person'):5.1f}%")
    print(f"  dates:       {pct(in_scope, 'dates'):5.1f}%")
    print(f"  priority:    {pct(in_scope, 'priority'):5.1f}%")
    print(f"Out-of-scope ({len(oos)} cases):")
    print(f"  correctly bailed (subcmd==add): {pct(oos, 'subcmd'):5.1f}%")
    print(f"  full match:                     {pct(oos, 'full_match'):5.1f}%")

    print("=" * 100)
    print("Pass bar (Stage 1 ship): full ≥70% in-scope, thread ≥80% in-scope, oos ≥80%.")
    full_in = pct(in_scope, 'full_match')
    thread_in = pct(in_scope, 'thread')
    oos_correct = pct(oos, 'subcmd')
    if full_in >= 70 and thread_in >= 80 and oos_correct >= 80:
        print(f"PASS — rules suggester clears the bar ({full_in:.0f}% full / "
              f"{thread_in:.0f}% thread / {oos_correct:.0f}% oos).")
        return 0
    else:
        print(f"BELOW BAR — full={full_in:.0f}% thread={thread_in:.0f}% oos={oos_correct:.0f}%. "
              f"Escalate to Stage 2 (needle) or iterate on rules.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
