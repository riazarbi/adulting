"""No command ever prompts.

Every command that deletes or creates something runs here with a real
terminal on stdin and "y" already typed on it, but without the flag or value
it needs. A prompt that only appears on a terminal would read that "y" and go
ahead; instead each command must refuse, print nothing to stdout, and leave
the vault exactly as it was.
"""

import json
import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src" / "adulting"


@pytest.fixture
def one_of_each(vault):
    """One thing of every kind, so each delete has something to refuse."""
    vault.write_thread("Projects", "SGB", currency="ZAR", rate=100)
    vault.write_person("Riaz Arbi")
    vault.write_note("2026-09-10-14-30-00", "Body", threads=["Projects/SGB"])
    vault.run("log", "SGB", "work", "-m", "30", cli="hours")
    vault.run("log", "SGB", "100", cli="payments")
    return vault


def ids(vault, cli):
    return [r["id"] for r in json.loads(vault.run("list", "--json", cli=cli).stdout)]


REFUSALS = [
    # (command, argv; "{hours}" / "{payments}" are filled with a record id)
    ("hours", ["rm", "{hours}"]),
    ("payments", ["rm", "{payments}"]),
    ("people", ["delete", "Riaz Arbi"]),
    ("threads", ["delete", "SGB"]),
    ("notes", ["delete", "2026-09-10-14-30-00"]),
    ("hours", ["log"]),
    ("payments", ["log"]),
    ("people", ["new", "--category", "personal"]),
    ("threads", ["new", "--kind", "project", "--category", "professional"]),
    ("notes", ["new", "--type", "Log", "--topic", "x"]),
    ("buffer", ["add-action"]),
    ("tasks", ["add"]),
    ("commit", ["save"]),
]


@pytest.mark.parametrize("cli, argv", REFUSALS, ids=[" ".join([c, *a]) for c, a in REFUSALS])
def test_refuses_on_a_terminal_without_asking(one_of_each, cli, argv):
    record = {"hours": ids(one_of_each, "hours")[0], "payments": ids(one_of_each, "payments")[0]}
    argv = [a.format(**record) for a in argv]
    buffer = one_of_each.home / "buffer.md"
    buffer.unlink(missing_ok=True)   # hours and payments log REFs there
    before = one_of_each.snapshot()
    r = one_of_each.run_on_a_terminal(*argv, cli=cli)
    assert r.returncode in (1, 2), r.stderr
    assert r.stdout == ""
    assert "?" not in r.stderr.split("\n")[-2]   # the last line is an error, not a question
    assert one_of_each.snapshot() == before


def test_suggest_stores_unknown_on_a_terminal_without_asking(one_of_each):
    r = one_of_each.run_on_a_terminal("suggest", "Draft the SGB scope note", cli="buffer")
    assert r.returncode == 0
    assert "not accepted (pass -y to accept); storing as UNKNOWN." in r.stdout.splitlines()
    assert re.fullmatch(r"- UNKNOWN: Draft the SGB scope note <!--[0-9T:-]+-->",
                        one_of_each.lines("buffer.md")[-2])


@pytest.mark.parametrize("argv", [["notes"], ["logs"], ["activity"], ["overview", "SGB"], ["stream"]])
def test_search_completes_on_a_terminal(one_of_each, argv):
    before = one_of_each.snapshot()
    r = one_of_each.run_on_a_terminal(*argv, cli="search")
    assert (r.returncode, r.stderr) == (0, "")
    assert one_of_each.snapshot() == before


def test_no_command_reads_stdin():
    """The cheap guarantee behind the tests above: nothing in the package
    calls input() or reads sys.stdin."""
    readers = re.compile(r"\binput\(|sys\.stdin|getpass")
    hits = [f"{p.name}:{n}: {line.strip()}"
            for p in sorted(SRC.glob("*.py"))
            for n, line in enumerate(p.read_text().split("\n"), start=1)
            if readers.search(line)]
    assert hits == []
