"""Tests for dev/manual-check, the gate that catches a stale MANUAL.md.

The manual is written by a model and committed; nothing used to compare it
with the code. These pin how it is read, against a manual written here rather
than against the real one, so the tests say the same thing whatever state the
committed manual is in.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load(path):
    """Import a dev script that has no .py suffix, as a module, so a test can
    replace one of its functions."""
    spec = importlib.util.spec_from_loader(
        "manual_check", importlib.machinery.SourceFileLoader("manual_check", str(path)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHECK = load(REPO / "dev" / "manual-check")

# What the CLI's surface is, and what prose may claim about it, is shared by
# the three gates that compare committed text with the code.
sys.path.insert(0, str(REPO / "dev"))
import surface  # noqa: E402

sections = CHECK.sections
claimed_names = CHECK.claimed_names
real_names = surface.real_names
spellings = surface.spellings

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


def test_a_heading_is_found_with_or_without_backticks():
    """How the heading is written is the manual writer's choice, and it
    changed between two generations of the manual. A gate that only knows one
    spelling reports every command as missing and says nothing about drift."""
    plain = MANUAL.replace("### `tasks`", "### tasks").replace("### `lint`", "### lint")
    assert sorted(sections(plain)) == ["lint", "tasks"]
    assert sections(plain)["tasks"] == sections(MANUAL)["tasks"]


def test_the_real_manual_has_a_section_for_every_command():
    found = sections((REPO / "MANUAL.md").read_text(encoding="utf-8"))
    sys.path.insert(0, str(REPO / "dev"))
    from commands import COMMANDS

    assert set(COMMANDS) <= set(found)
    # Each section is the command's own, not the whole rest of the manual.
    assert "Everyday procedures" not in found[COMMANDS[-1]]


# ---------- the comparison itself ----------

TASKS = {
    "name": "tasks",
    "flags": [{"name": "--help-json"}, {"name": "--dry-run"}],
    "subcommands": [
        {"name": "list", "flags": [{"name": "--priority"}, {"name": "--json"}]},
        {"name": "ingest", "flags": []},
    ],
}


def problems(monkeypatch, manifest=TASKS, text=None):
    monkeypatch.setattr(CHECK, "manifest", lambda tool: manifest)
    return CHECK.problems("tasks", sections(MANUAL)["tasks"] if text is None else text)


def test_a_manual_that_matches_the_cli_has_no_problems(monkeypatch):
    """The empty case: without it, a comparison that always reports
    something would still look like it was working."""
    manifest = {
        "name": "tasks",
        "flags": [{"name": "--help-json"}, {"name": "--dry-run"}],
        "subcommands": [{"name": "list", "flags": [{"name": "--priority"}]},
                        {"name": "suggest", "flags": []}],
    }
    assert problems(monkeypatch, manifest) == []


def test_every_kind_of_drift_is_reported(monkeypatch):
    """A subcommand or flag in the manual that the CLI does not have, and one
    the CLI has that the manual does not. Deleting either comparison from
    `problems()` drops lines from this list."""
    assert problems(monkeypatch) == [
        "documents `tasks suggest`, which does not exist",
        "does not document the flag `--json`",
        "does not document the subcommand `ingest`",
    ]


def test_a_flag_is_not_documented_by_a_longer_flag_that_starts_with_it(monkeypatch):
    """`--json` is not documented by `--json-lines`: the manual would name a
    flag that exists while leaving the one it is about undocumented."""
    text = ("**Subcommands**\n\n| Subcommand | What |\n|---|---|\n"
            "| `list` | List them. |\n| `ingest` | Ingest. |\n\n"
            "**Options**\n\n| Option | Effect |\n|---|---|\n"
            "| `--dry-run` | Write nothing. |\n"
            "| `list --priority H` | Filter. |\n"
            "| `list --json-lines` | One object per line. |\n")
    assert problems(monkeypatch, text=text) == [
        "documents the flag `--json-lines`, which does not exist",
        "does not document the flag `--json`",
    ]


def test_main_reports_a_stale_manual_and_exits_1(monkeypatch, tmp_path, capsys):
    """`main` is what `dev/ci` runs: it has to return non-zero and name the
    command whose section is missing."""
    manual = tmp_path / "MANUAL.md"
    manual.write_text("# Manual\n\n### `tasks`\n\nNothing here.\n", encoding="utf-8")
    monkeypatch.setattr(CHECK, "manifest", lambda tool: TASKS)
    monkeypatch.setattr(sys, "argv", ["manual-check", "--manual", str(manual)])
    assert CHECK.main() == 1
    out = capsys.readouterr().out
    assert "notes: no `### `notes`` section in the manual" in out
    assert "tasks: does not document the subcommand `list`" in out
    assert "Regenerate it with `dev/ci manual`" in out


def test_main_is_quiet_and_exits_0_when_nothing_has_drifted(monkeypatch, tmp_path, capsys):
    empty = {"name": "x", "flags": [{"name": "--help-json"}]}
    manual = tmp_path / "MANUAL.md"
    manual.write_text("# Manual\n\n" + "".join(
        f"### `{c}`\n\nNothing to document.\n\n" for c in CHECK.COMMANDS),
        encoding="utf-8")
    monkeypatch.setattr(CHECK, "manifest", lambda tool: empty)
    monkeypatch.setattr(sys, "argv", ["manual-check", "--manual", str(manual)])
    assert CHECK.main() == 0
    assert capsys.readouterr().out == ""


def test_the_generation_stage_checks_what_it_generated():
    """`dev/ci manual` and `dev/ci tools` both run their checker on the
    output. Without that, a generation that dropped a command is reported by
    the next run rather than the one that caused it."""
    ci = (REPO / "dev" / "ci").read_text(encoding="utf-8")
    manual = ci[ci.index("def stage_manual("):ci.index("def stage_tools(")]
    tools = ci[ci.index("def stage_tools("):ci.index("def main(")]
    assert "manual-build" in manual and "manual-check" in manual
    assert "tools-build" in tools and "tools-check" in tools


# ---------- old-layout paths in what the manual is generated from ----------

def test_the_manuals_sources_include_the_code_schemas_and_readme():
    names = {p.relative_to(REPO).as_posix() for p in CHECK.INPUTS}
    assert "src/adulting/buffer.py" in names
    assert "src/adulting/schemas/log.md" in names
    assert "README.md" in names


def test_a_stale_path_in_a_docstring_is_reported_with_its_place(tmp_path):
    # The docstring cmd_flush had until the gate read the sources.
    src = tmp_path / "buffer.py"
    src.write_text('"""Tend, then if clean, write each (thread, date) group to\n'
                   '    logs/<thread>/<date>.md (append if exists) and clear the buffer."""\n')
    assert list(CHECK.stale_input_paths([src])) == [
        (f"{src}:2", "logs/<thread>/<date>.md (append if exists) and clear the buffer.\"\"\"")]


def test_the_committed_sources_name_no_old_layout_path():
    assert list(CHECK.stale_input_paths()) == []
