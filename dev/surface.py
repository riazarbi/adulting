"""What the commands are, and the claims prose must not make about them.

Three gates compare committed text with the real CLI: `manual-check` reads
MANUAL.md, `tools-check` reads the agent tool definitions, `agent-check`
reads the agent skills. They ask the same two questions — does every name
exist, and does anything claim a command prompts — so the answers live here
rather than in three copies that can disagree.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# `--help-json` is a flag on every command and every subcommand, documented
# where the convention is explained rather than once per command.
EXEMPT_FLAGS = {'--help', '-h', '--help-json'}

FLAG_RE = re.compile(r'--[a-z][a-z0-9-]*')

# No command in this package prompts or reads stdin — tests/cli/test_no_prompts.py
# holds every one of them to it. The tool definitions and the agent skills
# both described the pre-port commands for months after that stopped being
# true, because nothing compared the prose with the code.
# The claim is that a *command* asks the operator something, so the shapes
# such a claim takes are matched rather than the bare words: prose about the
# role prompt, an automated prompt, or a "non-interactive run" is talking
# about something else entirely.
PROMPT_RE = re.compile(
    r"""prompts?\s+(for|on|you|the\ user|unless|if|when)   # "prompts on stdin"
      | prompting                                          # "rather than prompting"
      | interactively                                       # "run it interactively"
      | interactive\s+(capture|mode|prompt|trap)            # "interactive capture"
      | (goes|turns|drops\ into|enters|opens)\ (a\ |an\ )?\w*\s*interactive
      | reads\s+(from\s+)?stdin
      | (capture|confirmation)\s+prompt
      | needs\ a\ terminal
      | opens\ an\ application
    """,
    re.I | re.X)
# A denial counts only when it negates the verb directly: "nothing prompts",
# "no command prompts", "never reads stdin", "rather than prompting". A `no`
# or `without` earlier in the sentence usually belongs to a different clause
# — "`payments log` *without one* goes interactive" denies nothing about
# interactivity, and is exactly the claim being hunted — so only a handful of
# words may stand between the denial and the verb.
DENIAL_RE = re.compile(r"\b(not|never|nothing|none|no\ command|no\ adulting\ command|"
                       r"n't|rather\ than|instead\ of)\b"
                       r"(\s+(command|commands|subcommand|does|do|read|reads))?\s*$",
                       re.I | re.X)


# Where files lived before they moved into thread folders. The layout is
# declared once, in vault.LAYOUT, and nothing compares prose with it except
# this: a path that starts at one of these old roots describes a vault that
# no longer exists. Matched only where it is unmistakably a path — after a
# vault prefix (`~/vault/`, `$ADULTING_HOME/`, `/vault/`), or followed by a
# placeholder, a thread kind or a date — so that prose such as "notes/logs"
# and a thread's own `notes/` folder are left alone.
RETIRED_ROOTS = ('notes', 'logs', 'hours', 'payments')
_ROOT = '(?:' + '|'.join(RETIRED_ROOTS) + ')'
STALE_PATH_RE = re.compile(
    rf"""(?:~/vault/|\$ADULTING_HOME/|(?<![\w.])/vault/){_ROOT}\b
       | (?<![\w/.-]){_ROOT}/(?:<|\{{|Projects\b|Processes\b|Topics\b|\d)
    """, re.X)


def stale_paths(text):
    """(line number, line) for every line naming a vault path in the layout
    the vault had before thread folders."""
    for n, line in enumerate(text.splitlines(), start=1):
        if STALE_PATH_RE.search(line):
            yield n, line.strip()


def manifest(tool):
    """The tool's own description of its surface, from the installed command."""
    exe = REPO / '.venv' / 'bin' / tool
    env = dict(os.environ)
    env.pop('ADULTING_HOME', None)
    p = subprocess.run([str(exe), '--help-json'], capture_output=True, text=True,
                       env=env, stdin=subprocess.DEVNULL, timeout=20)
    if p.returncode != 0:
        sys.exit(f"surface: error: {tool} --help-json failed: {p.stderr.strip()}")
    return json.loads(p.stdout)


def spellings(flag):
    """Every way a flag can be written, longest first, so a message about it
    names `--minutes` rather than `-m`."""
    return sorted([flag['name']] + flag.get('aliases', []), key=len, reverse=True)


def real_names(m):
    """(subcommands, flags) the command really has. A flag is the set of its
    spellings: documenting either one documents the flag."""
    subs = {s['name'] for s in m.get('subcommands', [])}
    flags = list(m.get('flags', []))
    for s in m.get('subcommands', []):
        flags += s.get('flags', [])
    spelt = {tuple(spellings(f)) for f in flags}
    return subs, sorted(s for s in spelt if not set(s) & EXEMPT_FLAGS)


def interactivity_claims(description):
    """Sentences claiming the command prompts, or reads from stdin.

    A sentence that denies it — "Nothing prompts", "never reads stdin" — is
    exactly what these should say, so a claim counts only when the word is
    not negated by the words right before it.
    """
    for sentence in re.split(r'(?<=[.;])\s+|\n', description):
        for m in PROMPT_RE.finditer(sentence):
            if not DENIAL_RE.search(sentence[:m.start()]):
                yield sentence.strip()
                break
