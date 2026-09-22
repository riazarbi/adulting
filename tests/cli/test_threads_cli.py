"""The `threads` command: list, show, new (with billing defaults) and delete.

The first sections characterise behaviour kept from the pre-port script and
were run green against it. The last section specifies the removal of
interactivity and was written to fail against the old script.
"""

import json
import re
from datetime import date

import pytest

FLAGS = ("--kind", "project", "--category", "professional")


def threads(vault, *argv, input=""):
    # input="" closes stdin, so any prompt would hit EOF instead of hanging.
    return vault.run(*argv, cli="threads", input=input)


@pytest.fixture
def threads_vault(vault):
    vault.write_thread("Projects", "SGB", started="2026-01-05")
    vault.write_thread("Processes", "Personal Finance", category="personal")
    vault.write_thread("Topics", "Old Idea", status="closed")
    return vault


# ---------- list ----------

def test_list_shows_open_threads_by_kind_then_name(threads_vault):
    r = threads(threads_vault, "list")
    assert r.returncode == 0
    assert r.stdout == (
        "THREAD                      STATUS    CATEGORY\n"
        "Projects/SGB                open      professional\n"
        "Processes/Personal Finance  open      personal\n")


def test_list_all_includes_closed(threads_vault):
    assert "Topics/Old Idea             closed    professional" in \
        threads(threads_vault, "list", "--all").stdout


def test_list_json_fields(threads_vault):
    rows = json.loads(threads(threads_vault, "list", "--json").stdout)
    assert rows[0] == {
        "kind": "project", "name": "SGB", "thread": "Projects/SGB",
        "path": "threads/Projects/SGB.md", "status": "open",
        "category": "professional", "started": "2026-01-05", "ended": ""}


def test_list_query_ranks_by_similarity(threads_vault):
    rows = json.loads(threads(threads_vault, "list", "--json", "--all", "pf").stdout)
    assert [r["name"] for r in rows][0] == "Personal Finance"
    rows = json.loads(threads(threads_vault, "list", "--json", "processes/per").stdout)
    assert [r["name"] for r in rows] == ["Personal Finance"]


def test_list_empty_messages(threads_vault):
    assert threads(threads_vault, "list", "zzzzzz").stdout == "(no matches)\n"
    for f in (threads_vault.home / "threads").rglob("*.md"):
        f.unlink()
    assert threads(threads_vault, "list").stdout == "(no threads)\n"


# ---------- show and resolution ----------

def test_show_prints_the_file(threads_vault):
    assert threads(threads_vault, "show", "Projects/SGB").stdout == threads_vault.read("threads/Projects/SGB.md")


@pytest.mark.parametrize("ref", ["SGB", "Projects/SGB", "[[Projects/SGB]]", "  SGB  "])
def test_show_json_resolves_every_reference_form(threads_vault, ref):
    r = threads(threads_vault, "show", ref, "--json")
    assert json.loads(r.stdout) == {
        "kind": "project", "name": "SGB", "path": "threads/Projects/SGB.md",
        "status": "open", "category": "professional", "started": "2026-01-05"}


@pytest.mark.parametrize("ref", ["Nope", "Projects/Nope", "People/SGB", "sgb"])
def test_show_not_found(threads_vault, ref):
    r = threads(threads_vault, "show", ref)
    assert r.returncode == 1
    assert r.stderr == f"threads: error: not found: {ref}\n"


def test_bare_name_in_two_kinds_is_ambiguous(threads_vault):
    threads_vault.write_thread("Topics", "SGB")
    r = threads(threads_vault, "show", "SGB")
    assert r.returncode == 1
    assert r.stderr == "threads: error: ambiguous thread 'SGB'; matches: Projects/SGB, Topics/SGB\n"
    assert threads(threads_vault, "show", "Topics/SGB").returncode == 0


# ---------- new ----------

def test_new_writes_the_file(vault):
    r = threads(vault, "new", *FLAGS, "--name", "AXA DORA")
    path = vault.home / "threads" / "Projects" / "AXA DORA.md"
    assert r.returncode == 0
    assert r.stdout == f"created: {path}\n"
    assert path.read_text() == (
        f"---\nstatus: open\nkind: project\ncategory: professional\n"
        f"started: {date.today().isoformat()}\n---\n\n# AXA DORA\n")


def test_new_with_billing_orders_currency_then_rate(vault):
    threads(vault, "new", "--kind", "process", "--category", "voluntary",
            "--name", "Trust", "--currency", "bwp", "--rate", "0")
    assert vault.read("threads/Processes/Trust.md") == (
        f"---\nstatus: open\nkind: process\ncategory: voluntary\n"
        f"started: {date.today().isoformat()}\ncurrency: BWP\nrate: 0\n---\n\n# Trust\n")


def test_new_without_a_rate_writes_none(vault):
    """`hours` then falls back to the vault config, then 2500. The old
    interactive path wrote `rate: 2500` when the prompt was left blank."""
    threads(vault, "new", *FLAGS, "--name", "Acme Corp", "--currency", "zar")
    assert vault.read("threads/Projects/Acme Corp.md") == (
        f"---\nstatus: open\nkind: project\ncategory: professional\n"
        f"started: {date.today().isoformat()}\ncurrency: ZAR\n---\n\n# Acme Corp\n")


def test_a_new_billed_thread_can_be_logged_against_at_once(vault):
    """No hand-edit is needed before `hours log` works."""
    threads(vault, "new", *FLAGS, "--name", "Acme Corp", "--currency", "zar")
    r = vault.run("log", "Acme Corp", "kickoff", cli="hours")
    assert r.returncode == 0, r.stderr
    assert re.fullmatch(r"logged [0-9a-f]{8}  Projects/Acme Corp  \d{4}-\d\d-\d\d \d\d:\d\d  "
                        r"1h 0m @ 2500 ZAR = 2500 ZAR\n", r.stdout)


def test_a_new_thread_passes_lint(vault):
    threads(vault, "new", *FLAGS, "--name", "Acme Corp", "--currency", "zar", "--rate", "900")
    r = vault.run(str(vault.home / "threads" / "Projects" / "Acme Corp.md"), cli="lint")
    assert (r.returncode, r.stdout) == (0, "\n1 file(s) checked. 0 violation(s).\n")


def test_new_refuses_an_existing_thread(threads_vault):
    path = threads_vault.home / "threads" / "Projects" / "SGB.md"
    before = path.read_text()
    r = threads(threads_vault, "new", *FLAGS, "--name", "SGB")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == f"threads: error: already exists: {path}\n"
    assert path.read_text() == before


def test_new_error_messages(vault):
    r = threads(vault, "new", *FLAGS, "--name", "X", "--currency", "rands")
    assert (r.returncode, r.stderr) == (1, "threads: error: currency 'RANDS' is not a 3-letter ISO code\n")
    r = threads(vault, "new", *FLAGS, "--name", "X", "--rate", "900")
    assert (r.returncode, r.stderr) == (1, "threads: error: --rate needs a --currency\n")
    assert not (vault.home / "threads" / "Projects" / "X.md").exists()
    r = threads(vault, "new", "--kind", "people", "--category", "personal", "--name", "X")
    assert r.returncode == 2 and "invalid choice" in r.stderr


# ---------- delete ----------

def test_delete_with_yes(threads_vault):
    path = threads_vault.home / "threads" / "Topics" / "Old Idea.md"
    r = threads(threads_vault, "delete", "[[Topics/Old Idea]]", "-y")
    assert (r.returncode, r.stdout) == (0, f"deleted: {path}\n")
    assert not path.exists()


def test_delete_not_found_and_ambiguous(threads_vault):
    assert threads(threads_vault, "delete", "Nope", "-y").stderr == "threads: error: not found: Nope\n"
    threads_vault.write_thread("Topics", "SGB")
    r = threads(threads_vault, "delete", "SGB", "-y")
    assert r.returncode == 1
    assert "ambiguous" in r.stderr
    assert (threads_vault.home / "threads" / "Projects" / "SGB.md").exists()



# ---------- no interactivity (fails against the pre-port script) ----------

@pytest.mark.parametrize("missing", ["--kind", "--category", "--name"])
def test_new_fails_instead_of_prompting_for_a_missing_field(vault, missing):
    given = {"--kind": "project", "--category": "professional", "--name": "Typed"}
    argv = [x for k, val in given.items() if k != missing for x in (k, val)]
    r = threads(vault, "new", *argv, input="1\n1\nTyped\n\n")
    assert r.returncode == 2
    assert missing in r.stderr
    assert not (vault.home / "threads" / "Projects" / "Typed.md").exists()


def test_new_strips_the_name_and_refuses_a_blank_one(vault):
    for blank in ("", "  "):
        r = threads(vault, "new", *FLAGS, "--name", blank)
        assert (r.returncode, r.stderr) == (1, "threads: error: empty name\n")
    assert list((vault.home / "threads").rglob("*.md")) == []
    assert threads(vault, "new", *FLAGS, "--name", " Acme ").returncode == 0
    assert (vault.home / "threads" / "Projects" / "Acme.md").exists()


def test_delete_without_yes_refuses_even_if_stdin_says_yes(threads_vault):
    path = threads_vault.home / "threads" / "Projects" / "SGB.md"
    r = threads(threads_vault, "delete", "SGB", input="y\n")
    assert r.returncode == 1
    assert r.stderr == f"threads: error: refusing to delete {path} without -y\n"
    assert path.exists()


@pytest.mark.parametrize("name", ["../escaped", "a/b", ".hidden"])
def test_new_refuses_a_name_that_is_not_a_plain_filename(vault, name):
    """The name becomes threads/<Kind>/<name>.md, so a `/` could write
    outside threads/ (or crash), and a leading `.` would make a hidden file."""
    r = threads(vault, "new", *FLAGS, "--name", name)
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == f"threads: error: name {name!r} cannot contain '/' or start with '.'\n"
    assert sorted(p.relative_to(vault.home).as_posix() for p in vault.home.rglob("*.md")) == []
