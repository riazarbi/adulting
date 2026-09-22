"""Tests for the `people` CLI (refactor unit 4).

The first section characterises behaviour kept from the pre-port script and
was run green against it. The last section specifies the removal of
interactivity and was written to fail against the old script.
"""

import json
from datetime import date

import pytest


def people(vault, *argv, input=""):
    # input="" closes stdin, so any prompt would hit EOF instead of hanging.
    return vault.run(*argv, cli="people", input=input)


@pytest.fixture
def v(vault):
    vault.write_person("Riaz Arbi", category="professional", started="2026-01-02")
    vault.write_person("Bern Sellmeyer", category="personal")
    vault.write_person("Old Contact", status="closed")
    return vault


# ---------- list ----------

def test_list_shows_open_people_in_a_table(v):
    r = people(v, "list")
    assert r.returncode == 0
    assert r.stdout == (
        "PERSON                 STATUS    CATEGORY\n"
        "people/Bern Sellmeyer  open      personal\n"
        "people/Riaz Arbi       open      professional\n")


def test_list_all_includes_closed(v):
    assert "people/Old Contact     closed    professional" in people(v, "list", "--all").stdout


def test_list_json_fields(v):
    rows = json.loads(people(v, "list", "--json").stdout)
    assert rows[1] == {
        "name": "Riaz Arbi", "person": "people/Riaz Arbi",
        "path": "people/Riaz Arbi.md", "status": "open",
        "category": "professional", "started": "2026-01-02", "ended": ""}


def test_list_query_ranks_by_similarity(v):
    rows = json.loads(people(v, "list", "--json", "ra").stdout)
    assert [r["name"] for r in rows] == ["Riaz Arbi"]  # initials match
    rows = json.loads(people(v, "list", "--json", "people/bern").stdout)
    assert [r["name"] for r in rows][0] == "Bern Sellmeyer"


def test_list_empty_messages(vault, v):
    assert people(v, "list", "zzzzzz").stdout == "(no matches)\n"
    for f in (vault.home / "people").iterdir():
        f.unlink()
    assert people(vault, "list").stdout == "(no people)\n"


# ---------- show ----------

def test_show_prints_the_file(v):
    r = people(v, "show", "Riaz Arbi")
    assert r.stdout == (v.home / "people" / "Riaz Arbi.md").read_text()


def test_show_accepts_the_wikilink_form_and_json(v):
    r = people(v, "show", "people/Riaz Arbi", "--json")
    assert json.loads(r.stdout) == {
        "name": "Riaz Arbi", "path": "people/Riaz Arbi.md", "status": "open",
        "category": "professional", "started": "2026-01-02"}


def test_show_missing_person(v):
    r = people(v, "show", "Nobody")
    assert r.returncode == 1
    assert r.stderr == f"not found: {v.home / 'people' / 'Nobody.md'}\n"


# ---------- new ----------

def test_new_with_flags_writes_the_file(vault):
    r = people(vault, "new", "--name", "Igor Novak", "--category", "professional")
    path = vault.home / "people" / "Igor Novak.md"
    assert r.returncode == 0
    assert r.stdout == f"created: {path}\n"
    assert path.read_text() == (
        f"---\nstatus: open\ncategory: professional\nstarted: {date.today().isoformat()}\n"
        "---\n\n# Igor Novak\n")
    assert vault.run(cli="lint").returncode == 0


def test_new_creates_the_people_dir(vault):
    (vault.home / "people").rmdir()
    assert people(vault, "new", "--name", "A", "--category", "personal").returncode == 0


def test_new_refuses_an_existing_person(v):
    r = people(v, "new", "--name", "Riaz Arbi", "--category", "personal")
    assert r.returncode == 1
    assert r.stderr.startswith("already exists: ")


def test_new_rejects_an_unknown_category(vault):
    r = people(vault, "new", "--name", "A", "--category", "family")
    assert r.returncode == 2
    assert "invalid choice" in r.stderr


# ---------- delete ----------

def test_delete_with_yes(v):
    path = v.home / "people" / "Old Contact.md"
    r = people(v, "delete", "people/Old Contact", "-y")
    assert r.returncode == 0
    assert r.stdout == f"deleted: {path}\n"
    assert not path.exists()


def test_delete_missing_person(v):
    r = people(v, "delete", "Nobody", "-y")
    assert r.returncode == 1
    assert r.stderr.startswith("not found: ")


def test_help_json_lists_subcommands(vault):
    manifest = json.loads(people(vault, "--help-json").stdout)
    assert [s["name"] for s in manifest["subcommands"]] == ["list", "show", "new", "delete"]


# ---------- no interactivity (fails against the pre-port script) ----------

def test_new_without_name_fails_instead_of_prompting(vault):
    r = people(vault, "new", "--category", "personal", input="Typed Name\n")
    assert r.returncode == 2
    assert "--name" in r.stderr
    assert list((vault.home / "people").iterdir()) == []


def test_new_without_category_fails_instead_of_prompting(vault):
    r = people(vault, "new", "--name", "Typed Name", input="1\n")
    assert r.returncode == 2
    assert "--category" in r.stderr
    assert list((vault.home / "people").iterdir()) == []


def test_delete_without_yes_refuses_even_if_stdin_says_yes(v):
    path = v.home / "people" / "Old Contact.md"
    r = people(v, "delete", "Old Contact", input="y\n")
    assert r.returncode == 1
    assert r.stderr == f"refusing to delete {path} without -y\n"
    assert path.exists()


def test_new_strips_the_name_and_refuses_a_blank_one(vault):
    """The old flag path skipped the strip the prompt path did, so
    `--name "  "` created a file called `  .md`, and `--name ""` fell
    through to the prompt."""
    for blank in ("", "  "):
        r = people(vault, "new", "--name", blank, "--category", "personal")
        assert r.returncode == 1
        assert r.stderr == "empty name\n"
        assert list((vault.home / "people").iterdir()) == []
    r = people(vault, "new", "--name", " Igor Novak ", "--category", "personal")
    assert r.returncode == 0
    assert (vault.home / "people" / "Igor Novak.md").exists()


def test_help_no_longer_mentions_prompts(vault):
    r = people(vault, "new", "--help")
    assert "prompt" not in r.stdout.lower()


@pytest.mark.parametrize("name", ["../escaped", "a/b", ".hidden"])
def test_new_refuses_a_name_that_is_not_a_plain_filename(vault, name):
    """The name becomes people/<name>.md, so a `/` could write outside
    people/ (or crash), and a leading `.` would make a hidden file."""
    r = people(vault, "new", "--name", name, "--category", "personal")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == f"name {name!r} cannot contain '/' or start with '.'\n"
    assert sorted(p.relative_to(vault.home).as_posix() for p in vault.home.rglob("*.md")) == []
