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
    # (command, argv, exit code, last line of stderr). "{hours}", "{payments}"
    # and "{home}" are filled in with a record id and the vault's path.
    ("hours", ["rm", "{hours}"], 1, "hours: error: refusing to delete {hours} without -y"),
    ("payments", ["rm", "{payments}"], 1, "payments: error: refusing to delete {payments} without -y"),
    ("people", ["delete", "Riaz Arbi"], 1,
     "people: error: refusing to delete people/Riaz Arbi.md without -y"),
    ("people", ["delete", "../threads/Projects/SGB", "-y"], 1,
     "people: error: name '../threads/Projects/SGB' cannot contain '/' or start with '.'"),
    ("threads", ["delete", "SGB"], 1,
     "threads: error: refusing to delete threads/Projects/SGB.md without -y"),
    ("notes", ["delete", "2026-09-10-14-30-00"], 1,
     "notes: error: refusing to delete notes/2026-09-10-14-30-00.md without -y"),
    # A missing argument is argparse's to report, so one row pins its
    # wording and the rest only require the refusal.
    ("hours", ["log"], 2, "hours log: error: the following arguments are required: thread"),
    ("payments", ["log"], 2, None),
    ("people", ["new", "--category", "personal"], 2, None),
    ("threads", ["new", "--kind", "project", "--category", "professional"], 2, None),
    ("notes", ["new", "--type", "Log", "--topic", "x"], 2, None),
    ("buffer", ["add-action"], 2, None),
    ("tasks", ["add"], 2, None),
    ("commit", ["save"], 2, None),
]


@pytest.mark.parametrize("cli, argv, code, message", REFUSALS,
                         ids=[" ".join([c, *a]) for c, a, _, _ in REFUSALS])
def test_refuses_on_a_terminal_without_asking(one_of_each, cli, argv, code, message):
    fill = {"hours": ids(one_of_each, "hours")[0], "payments": ids(one_of_each, "payments")[0],
            "home": one_of_each.home}
    buffer = one_of_each.home / "buffer.md"
    buffer.unlink(missing_ok=True)   # hours and payments log REFs there
    before = one_of_each.snapshot()
    r = one_of_each.run_on_a_terminal(*[a.format(**fill) for a in argv], cli=cli)
    assert (r.returncode, r.stdout) == (code, "")
    last = r.stderr.splitlines()[-1]
    if message:
        assert last == message.format(**fill)
    else:
        assert last.startswith(f"{cli} {argv[0]}: error: ") and "?" not in last
    assert one_of_each.snapshot() == before


def test_buffer_rm_deletes_the_line_without_asking(one_of_each):
    """`buffer rm` takes no -y: the line number is the confirmation. It must
    not start asking on a terminal either."""
    first = one_of_each.lines("buffer.md")[0]
    r = one_of_each.run_on_a_terminal("rm", "1", cli="buffer")
    assert (r.returncode, r.stdout, r.stderr) == (0, f"removed line 1: {first}\n", "")
    assert first not in one_of_each.read("buffer.md")


@pytest.mark.parametrize("cli, argv, printed", [
    ("hours", ["edit", "{id}", "-m", "45"], r"logged {id}  Projects/SGB  .* 0h 45m @ 100 ZAR = 75 ZAR\n"),
    ("payments", ["edit", "{id}", "--amount", "120"], r"received {id}  Projects/SGB  .* 120 ZAR\n"),
])
def test_edit_changes_the_record_without_asking(one_of_each, cli, argv, printed):
    rid = ids(one_of_each, cli)[0]
    r = one_of_each.run_on_a_terminal(*[a.format(id=rid) for a in argv], cli=cli)
    assert (r.returncode, r.stderr) == (0, "")
    assert re.fullmatch(printed.format(id=rid), r.stdout)



@pytest.mark.parametrize("argv, first", [
    (["notes"], "2026-09-10-14-30-00.md"),
    (["stream"], "0h 30m work"),
])
def test_search_completes_on_a_terminal(one_of_each, argv, first):
    """Read-only commands must not wait for anything either, and must print
    their answer rather than an empty one."""
    before = one_of_each.snapshot()
    r = one_of_each.run_on_a_terminal(*argv, cli="search")
    assert (r.returncode, r.stderr) == (0, "")
    assert first in r.stdout
    assert one_of_each.snapshot() == before


def test_no_command_reads_stdin():
    """A cheap early warning: nothing in the package calls input() or reads
    sys.stdin. It is only a text search, and `os.read(0, ...)` would get
    past it; the terminal tests above are what actually protect the
    no-prompts rule."""
    readers = re.compile(r"\binput\(|sys\.stdin|getpass")
    hits = [f"{p.name}:{n}: {line.strip()}"
            for p in sorted(SRC.glob("*.py"))
            for n, line in enumerate(p.read_text().split("\n"), start=1)
            if readers.search(line)]
    assert hits == []
