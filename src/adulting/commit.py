"""Review and commit changes to the vault.

Two steps, meant to be used in order: `review` prints everything that has
changed since the last commit so you can write an accurate summary, then
`save` stages it all and commits with that summary as the message.

This tool can only ever add a commit. It never amends, rebases, resets,
checks out, or pushes — the only mutating git calls it makes are
`git add` and `git commit`.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from adulting import vault as V
from adulting.helpjson import emit_helpjson_if_requested
from adulting.vault import vault_home



DEFAULT_MAX_FILE_LINES = 150
DEFAULT_MAX_LINES = 3000

# `git status --porcelain` status codes, for the changed-paths listing.
CODES = {
    'M': 'modified', 'A': 'added', 'D': 'deleted', 'R': 'renamed',
    'C': 'copied', 'T': 'typechange', 'U': 'unmerged', '?': 'untracked',
}


def git(*args, check=True):
    """Run a git command against the vault. Subprocess stderr is always
    captured, never passed through to ours."""
    # The vault is a bind mount inside the agent container, so git otherwise
    # refuses it as "dubious ownership". Passed per-command via -c; never
    # written to a config file. core.quotepath=false keeps non-ASCII note
    # filenames readable instead of \303\251-escaped.
    cmd = ['git', '-C', str(vault_home()),
           '-c', 'safe.directory=*',
           '-c', 'core.quotepath=false']
    r = subprocess.run(cmd + list(args), capture_output=True, text=True)
    if check and r.returncode != 0:
        V.die(f"git {' '.join(args)} failed: {(r.stderr or r.stdout).strip()}")
    return r


def require_repo():
    """The vault must be the root of a git repo. If it were merely a
    subdirectory of one, `git add -A` would sweep in files outside it."""
    home = vault_home()
    if not home.is_dir():
        V.die(f"ADULTING_HOME is not a directory: {home}")
    r = git('rev-parse', '--show-toplevel', check=False)
    if r.returncode != 0:
        V.die(f"not a git repository: {home}")
    top = Path(r.stdout.strip()).resolve()
    if top != home.resolve():
        V.die(f"ADULTING_HOME ({home}) is not the root of its git repository ({top})")


def has_head():
    return git('rev-parse', '--verify', '--quiet', 'HEAD', check=False).returncode == 0


def status_entries():
    """Parse `git status --porcelain -uall -z` into (code, path, orig).

    -uall so files inside a new directory are listed individually rather
    than collapsed to `dir/` — otherwise `review` would show one line
    where `save` commits fifty files. -z because note filenames contain
    spaces and non-ASCII characters.
    """
    fields = git('status', '--porcelain', '-uall', '-z').stdout.split('\0')
    entries = []
    i = 0
    while i < len(fields):
        f = fields[i]
        if not f:
            i += 1
            continue
        x, y, path = f[0], f[1], f[3:]
        orig = None
        if x in ('R', 'C'):
            # In -z format a rename is `XY <new>\0<old>\0` — the reverse
            # of the human-readable `R old -> new`.
            i += 1
            orig = fields[i] if i < len(fields) else None
        entries.append((x if x != ' ' else y, path, orig))
        i += 1
    return entries


def describe(code, path, orig):
    label = CODES.get(code, code)
    if orig:
        return f"  {label:<11} {orig} -> {path}"
    return f"  {label:<11} {path}"


def split_diff(text):
    """Split a combined `git diff` into per-file blocks.

    Returns [(path, [lines])]. Safe to split on a bare `diff --git ` at
    line start: inside a hunk every content line carries a leading
    space/+/- prefix, so it can never be mistaken for a header.
    """
    blocks = []
    current = None
    for line in text.split('\n'):
        if line.startswith('diff --git '):
            if current:
                blocks.append(current)
            # `diff --git a/<path> b/<path>` — take the b-side, which is
            # the post-change name for renames.
            path = line.split(' b/', 1)[1] if ' b/' in line else line
            current = (path, [line])
        elif current:
            current[1].append(line)
    if current:
        blocks.append(current)
    # Trailing newline from the diff leaves one empty line on the last block.
    return [(p, lines[:-1] if lines and lines[-1] == '' else lines)
            for p, lines in blocks]


def cap_block(path, lines, max_file_lines):
    total = len(lines)
    if total <= max_file_lines:
        return lines
    return lines[:max_file_lines] + [
        f"[truncated: {path} — showing {max_file_lines:,} of {total:,} lines; "
        f"re-run with --max-file-lines]"
    ]


def cmd_review(args):
    require_repo()
    entries = status_entries()
    if not entries:
        print("no uncommitted changes; working tree clean")
        return 0

    out = ["Changed paths:"] + [describe(*e) for e in entries]

    tracked = []
    if has_head():
        diff = git('diff', '--no-ext-diff', 'HEAD').stdout
        tracked = [(f, cap_block(f, lines, args.max_file_lines))
                   for f, lines in split_diff(diff)]

    untracked = []
    for code, rel, _ in entries:
        if code != '?':
            continue
        # --no-index renders a new file as an add-diff without staging it.
        # It exits 1 whenever the two inputs differ, i.e. always here, so
        # a non-zero return is the normal case rather than an error.
        r = git('diff', '--no-ext-diff', '--no-index', '--', os.devnull, rel,
                check=False)
        if r.returncode > 1:
            untracked.append((rel, [f"[unreadable: {rel}]"]))
            continue
        blocks = split_diff(r.stdout)
        if not blocks:
            # No diff against /dev/null at all: the new file is empty.
            untracked.append((rel, [f"[new empty file: {rel}]"]))
            continue
        for _, lines in blocks:
            untracked.append((rel, cap_block(rel, lines, args.max_file_lines)))

    # Flattened across both sections so the global cap reports one
    # accurate "not shown" count instead of a per-section one.
    items = ([("Changes to tracked files:", lines) for _, lines in tracked] +
             [("New files:", lines) for _, lines in untracked])
    section = None
    for i, (title, lines) in enumerate(items):
        opening = 0 if title == section else 3  # blank, title, blank
        if len(out) + opening + len(lines) > args.max_lines:
            out += ["", f"[truncated: output hit the {args.max_lines:,}-line cap; "
                        f"{len(items) - i} file(s) not shown; re-run with --max-lines]"]
            break
        if title != section:
            out += ["", title, ""]
            section = title
        out += lines

    print('\n'.join(out))
    return 0


def cmd_save(args):
    require_repo()
    if '\n' in args.message:
        V.die("--message must be a single line; put the detail in --body")
    if not args.message.strip():
        V.die("--message must not be empty")

    entries = status_entries()
    if not entries:
        # Not an error: there was simply nothing to do.
        print("nothing to commit; working tree clean")
        return 0

    if args.dry_run:
        print("dry run — nothing staged, nothing committed.")
        print()
        print(f"Would stage {len(entries)} path(s):")
        for e in entries:
            print(describe(*e))
        print()
        print("Would commit with message:")
        print(f"  {args.message}")
        if args.body:
            print()
            for line in args.body.split('\n'):
                print(f"  {line}")
        return 0

    git('add', '-A')
    # --message and --body only ever reach git as the value of -m. git
    # never reinterprets an option's consumed value as another option, so
    # no caller input can turn into a git flag.
    argv = ['commit', '-m', args.message]
    if args.body:
        argv += ['-m', args.body]
    r = git(*argv, check=False)
    if r.returncode != 0:
        V.die(f"git commit failed: {(r.stderr or r.stdout).strip()}")

    sha = git('rev-parse', '--short', 'HEAD').stdout.strip()
    print(f"committed {sha}: {args.message}")
    print(f"{len(entries)} path(s) staged and committed.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Review uncommitted vault changes, then stage and commit them.\n"
            "\n"
            "Two steps, used in order: run `review` to see everything that has\n"
            "changed since the last commit, write a summary of it, then run\n"
            "`save` with that summary so the git log records what happened.\n"
            "\n"
            "`review` is read-only and truncates long diffs (see its --max-*\n"
            "flags). `save` can only ever add a commit — it never amends,\n"
            "rebases, resets, or pushes."))
    sub = parser.add_subparsers(dest='subcommand', required=True)

    p_review = sub.add_parser(
        'review',
        help="Show everything that changed since the last commit. Read-only.")
    p_review.add_argument('--max-file-lines', type=int, default=DEFAULT_MAX_FILE_LINES,
                          help=f"Max diff lines shown per file (default: {DEFAULT_MAX_FILE_LINES}).")
    p_review.add_argument('--max-lines', type=int, default=DEFAULT_MAX_LINES,
                          help=f"Max lines of output overall (default: {DEFAULT_MAX_LINES}).")
    p_review.set_defaults(func=cmd_review)

    p_save = sub.add_parser(
        'save',
        help="Stage every change in the vault and commit it.")
    p_save.add_argument('--message', required=True,
                        help="Commit subject. Single line; use --body for detail.")
    p_save.add_argument('--body',
                        help="Commit body. May span multiple lines.")
    p_save.add_argument('--dry-run', action='store_true',
                        help="Report what would be staged and committed; change nothing.")
    p_save.set_defaults(func=cmd_save)

    emit_helpjson_if_requested(parser)
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
