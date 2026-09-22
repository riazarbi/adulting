"""Tests for the `threads` CLI (refactor unit 5).

Billing fields on `threads new` are covered in test_threads_billing.py. The
first sections here characterise behaviour kept from the pre-port script and
were run green against it. The last section specifies the removal of
interactivity and was written to fail against the old script.
"""

import json
from datetime import date

import pytest

FLAGS = ("--kind", "project", "--category", "professional")


def threads(vault, *argv, input=""):
    # input="" closes stdin, so any prompt would hit EOF instead of hanging.
    return vault.run(*argv, cli="threads", input=input)


@pytest.fixture
def v(vault):
    vault.write_thread("Projects", "SGB", started="2026-01-05")
    vault.write_thread("Processes", "Personal Finance", category="personal")
    vault.write_thread("Topics", "Old Idea", status="closed")
    return vault


# ---------- list ----------

def test_list_shows_open_threads_by_kind_then_name(v):
    r = threads(v, "list")
    assert r.returncode == 0
    assert r.stdout == (
        "THREAD                      STATUS    CATEGORY\n"
        "Projects/SGB                open      professional\n"
        "Processes/Personal Finance  open      personal\n")


def test_list_all_includes_closed(v):
    assert "Topics/Old Idea             closed    professional" in \
        threads(v, "list", "--all").stdout


def test_list_json_fields(v):
    rows = json.loads(threads(v, "list", "--json").stdout)
    assert rows[0] == {
        "kind": "project", "name": "SGB", "thread": "Projects/SGB",
        "path": "threads/Projects/SGB.md", "status": "open",
        "category": "professional", "started": "2026-01-05", "ended": ""}


def test_list_query_ranks_by_similarity(v):
    rows = json.loads(threads(v, "list", "--json", "--all", "pf").stdout)
    assert [r["name"] for r in rows][0] == "Personal Finance"
    rows = json.loads(threads(v, "list", "--json", "processes/per").stdout)
    assert [r["name"] for r in rows] == ["Personal Finance"]


def test_list_empty_messages(v):
    assert threads(v, "list", "zzzzzz").stdout == "(no matches)\n"
    for f in (v.home / "threads").rglob("*.md"):
        f.unlink()
    assert threads(v, "list").stdout == "(no threads)\n"


# ---------- show and resolution ----------

def test_show_prints_the_file(v):
    assert threads(v, "show", "Projects/SGB").stdout == v.read("threads/Projects/SGB.md")


@pytest.mark.parametrize("ref", ["SGB", "Projects/SGB", "[[Projects/SGB]]", "  SGB  "])
def test_show_json_resolves_every_reference_form(v, ref):
    r = threads(v, "show", ref, "--json")
    assert json.loads(r.stdout) == {
        "kind": "project", "name": "SGB", "path": "threads/Projects/SGB.md",
        "status": "open", "category": "professional", "started": "2026-01-05"}


@pytest.mark.parametrize("ref", ["Nope", "Projects/Nope", "People/SGB", "sgb"])
def test_show_not_found(v, ref):
    r = threads(v, "show", ref)
    assert r.returncode == 1
    assert r.stderr == f"not found: {ref}\n"


def test_bare_name_in_two_kinds_is_ambiguous(v):
    v.write_thread("Topics", "SGB")
    r = threads(v, "show", "SGB")
    assert r.returncode == 1
    assert r.stderr == "ambiguous thread 'SGB'; matches: Projects/SGB, Topics/SGB\n"
    assert threads(v, "show", "Topics/SGB").returncode == 0


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


def test_new_refuses_an_existing_thread(v):
    r = threads(v, "new", *FLAGS, "--name", "SGB")
    assert r.returncode == 1
    assert r.stderr.startswith("already exists: ")


def test_new_error_messages(vault):
    r = threads(vault, "new", *FLAGS, "--name", "X", "--currency", "rands")
    assert (r.returncode, r.stderr) == (1, "currency 'RANDS' is not a 3-letter ISO code\n")
    r = threads(vault, "new", *FLAGS, "--name", "X", "--rate", "900")
    assert (r.returncode, r.stderr) == (1, "--rate needs a --currency\n")
    r = threads(vault, "new", "--kind", "people", "--category", "personal", "--name", "X")
    assert r.returncode == 2 and "invalid choice" in r.stderr


# ---------- delete ----------

def test_delete_with_yes(v):
    path = v.home / "threads" / "Topics" / "Old Idea.md"
    r = threads(v, "delete", "[[Topics/Old Idea]]", "-y")
    assert (r.returncode, r.stdout) == (0, f"deleted: {path}\n")
    assert not path.exists()


def test_delete_not_found_and_ambiguous(v):
    assert threads(v, "delete", "Nope", "-y").stderr == "not found: Nope\n"
    v.write_thread("Topics", "SGB")
    r = threads(v, "delete", "SGB", "-y")
    assert r.returncode == 1
    assert "ambiguous" in r.stderr
    assert (v.home / "threads" / "Projects" / "SGB.md").exists()


def test_help_json_lists_subcommands(vault):
    manifest = json.loads(threads(vault, "--help-json").stdout)
    assert [s["name"] for s in manifest["subcommands"]] == ["list", "show", "new", "delete"]


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
        assert (r.returncode, r.stderr) == (1, "empty name\n")
    assert list((vault.home / "threads").rglob("*.md")) == []
    assert threads(vault, "new", *FLAGS, "--name", " Acme ").returncode == 0
    assert (vault.home / "threads" / "Projects" / "Acme.md").exists()


def test_delete_without_yes_refuses_even_if_stdin_says_yes(v):
    path = v.home / "threads" / "Projects" / "SGB.md"
    r = threads(v, "delete", "SGB", input="y\n")
    assert r.returncode == 1
    assert r.stderr == f"refusing to delete {path} without -y\n"
    assert path.exists()


def test_help_no_longer_mentions_prompts(vault):
    r = threads(vault, "new", "--help")
    assert "prompt" not in r.stdout.lower()
