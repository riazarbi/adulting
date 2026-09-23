"""Tests for dev/manual-check, the gate that catches a stale MANUAL.md.

The manual is written by a model and committed; nothing used to compare it
with the code. These pin how it is read, against a manual written here rather
than against the real one, so the tests say the same thing whatever state the
committed manual is in.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CHECK = runpy.run_path(str(REPO / "dev" / "manual-check"))

sections = CHECK["sections"]
claimed_names = CHECK["claimed_names"]
real_names = CHECK["real_names"]
spellings = CHECK["spellings"]

MANUAL = """# Manual

## Command reference

### `tasks`

Does things.

**Subcommands**

| Subcommand | What it does | Example |
|---|---|---|
| `list` | List them. | `tasks list` |
| `suggest` | Guess one. | `tasks suggest` |

**Options**

| Option | Effect |
|---|---|
| `--dry-run` | Write nothing. |
| `list --priority H\\|M\\|L` | Filter. |

### `lint`

Checks things.

**Arguments**

| Argument | Meaning |
|---|---|
| `paths` | Files to validate. |

**Options**

| Option | Effect |
|---|---|
| `--quiet` | Exit code only. |

## Everyday procedures

### 1. Do a thing

`lint everything` is not a subcommand and must not be read as one.
"""


def test_a_section_ends_at_the_next_heading():
    """The last command's section used to swallow every chapter after it, so
    anything named there was read as that command's own."""
    found = sections(MANUAL)
    assert sorted(found) == ["lint", "tasks"]
    assert "Files to validate" in found["lint"]
    assert "Everyday procedures" not in found["lint"]
    assert "everything" not in found["lint"]


def test_only_the_subcommands_table_claims_a_subcommand():
    """A positional argument is documented in a table of its own. Reading it
    as a subcommand reported `lint paths` as a command that does not exist."""
    subs, flags = claimed_names(sections(MANUAL)["lint"])
    assert subs == set()
    assert flags == {"--quiet"}


def test_a_flag_in_a_row_is_found_whatever_the_cell_says_around_it():
    subs, flags = claimed_names(sections(MANUAL)["tasks"])
    assert subs == {"list", "suggest"}
    assert flags == {"--dry-run", "--priority"}


def test_a_flags_spellings_are_one_flag():
    """`-m/--minutes` is one flag written two ways: documenting either one
    documents it, and a message about it says the long form."""
    assert spellings({"name": "-m", "aliases": ["--minutes"]}) == ["--minutes", "-m"]
    manifest = {
        "flags": [{"name": "--help-json"}],
        "subcommands": [
            {"name": "log", "flags": [{"name": "-m", "aliases": ["--minutes"]},
                                      {"name": "--help-json"}]},
            {"name": "list", "flags": [{"name": "-m", "aliases": ["--minutes"]}]},
        ],
    }
    subs, flags = real_names(manifest)
    assert subs == {"log", "list"}
    # --help-json is exempt, and one flag on two subcommands is one flag.
    assert flags == [("--minutes", "-m")]


def test_the_real_manual_is_read_without_error():
    """Whatever the manual currently says, reading it must not blow up: the
    gate has to report drift, not crash on it."""
    found = sections((REPO / "MANUAL.md").read_text(encoding="utf-8"))
    sys.path.insert(0, str(REPO / "dev"))
    from commands import COMMANDS

    assert set(COMMANDS) <= set(found)
    for command in COMMANDS:
        subs, flags = claimed_names(found[command])
        assert isinstance(subs, set) and isinstance(flags, set)
