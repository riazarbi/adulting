"""The `people` command: list, show, new and delete, each driven entirely
by arguments."""

import json
from datetime import date

import pytest


@pytest.fixture
def people_vault(vault):
    vault.write_person("Riaz Arbi", category="professional", started="2026-01-02")
    vault.write_person("Bern Sellmeyer", category="personal")
    vault.write_person("Old Contact", status="closed")
    return vault


# ---------- list ----------

def test_list_shows_open_people_in_a_table(people_vault):
    r = people_vault.run("list", cli="people")
    assert r.returncode == 0
    assert r.stdout == (
        "PERSON                 STATUS    CATEGORY\n"
        "people/Bern Sellmeyer  open      personal\n"
        "people/Riaz Arbi       open      professional\n")


def test_list_all_includes_closed(people_vault):
    assert "people/Old Contact     closed    professional" in people_vault.run("list", "--all", cli="people").stdout


def test_list_json_fields(people_vault):
    rows = json.loads(people_vault.run("list", "--json", cli="people").stdout)
    assert rows[1] == {
        "name": "Riaz Arbi", "person": "people/Riaz Arbi",
        "path": "people/Riaz Arbi.md", "status": "open",
        "category": "professional", "started": "2026-01-02", "ended": ""}


def test_list_query_ranks_by_similarity(people_vault):
    rows = json.loads(people_vault.run("list", "--json", "ra", cli="people").stdout)
    assert [r["name"] for r in rows] == ["Riaz Arbi"]  # initials match
    rows = json.loads(people_vault.run("list", "--json", "people/bern", cli="people").stdout)
    assert [r["name"] for r in rows][0] == "Bern Sellmeyer"


def test_list_empty_messages(vault, people_vault):
    assert people_vault.run("list", "zzzzzz", cli="people").stdout == "(no matches)\n"
    for f in (vault.home / "people").iterdir():
        f.unlink()
    assert vault.run("list", cli="people").stdout == "(no people)\n"


# ---------- show ----------

def test_show_prints_the_file(people_vault):
    r = people_vault.run("show", "Riaz Arbi", cli="people")
    assert r.stdout == (people_vault.home / "people" / "Riaz Arbi.md").read_text()


def test_show_accepts_the_wikilink_form_and_json(people_vault):
    r = people_vault.run("show", "people/Riaz Arbi", "--json", cli="people")
    assert json.loads(r.stdout) == {
        "name": "Riaz Arbi", "path": "people/Riaz Arbi.md", "status": "open",
        "category": "professional", "started": "2026-01-02"}


def test_show_missing_person(people_vault):
    r = people_vault.run("show", "Nobody", cli="people")
    assert r.returncode == 1
    assert r.stderr == "people: error: not found: people/Nobody.md\n"


# ---------- new ----------

def test_new_with_flags_writes_the_file(vault):
    r = vault.run("new", "--name", "Igor Novak", "--category", "professional", cli="people")
    path = vault.home / "people" / "Igor Novak.md"
    assert r.returncode == 0
    assert r.stdout == "created: people/Igor Novak.md\n"
    assert path.read_text() == (
        f"---\nstatus: open\ncategory: professional\nstarted: {date.today().isoformat()}\n"
        "---\n\n# Igor Novak\n")
    assert vault.run(cli="lint").returncode == 0


def test_new_creates_the_people_dir(vault):
    (vault.home / "people").rmdir()
    r = vault.run("new", "--name", "A", "--category", "personal", cli="people")
    path = vault.home / "people" / "A.md"
    assert (r.returncode, r.stdout, r.stderr) == (0, "created: people/A.md\n", "")
    assert path.read_text() == (f"---\nstatus: open\ncategory: personal\n"
                                f"started: {date.today().isoformat()}\n---\n\n# A\n")


def test_new_refuses_an_existing_person(people_vault):
    before = people_vault.snapshot()
    r = people_vault.run("new", "--name", "Riaz Arbi", "--category", "personal", cli="people")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == "people: error: already exists: people/Riaz Arbi.md\n"
    assert people_vault.snapshot() == before


# ---------- delete ----------

def test_delete_with_yes(people_vault):
    path = people_vault.home / "people" / "Old Contact.md"
    r = people_vault.run("delete", "people/Old Contact", "-y", cli="people")
    assert r.returncode == 0
    assert r.stdout == "deleted: people/Old Contact.md\n"
    assert not path.exists()


def test_delete_missing_person(people_vault):
    before = people_vault.snapshot()
    r = people_vault.run("delete", "Nobody", "-y", cli="people")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == "people: error: not found: people/Nobody.md\n"
    assert people_vault.snapshot() == before


# ---------- nothing prompts ----------


def test_delete_without_yes_refuses_even_if_stdin_says_yes(people_vault):
    path = people_vault.home / "people" / "Old Contact.md"
    r = people_vault.run("delete", "Old Contact", input="y\n", cli="people")
    assert r.returncode == 1
    assert r.stderr == "people: error: refusing to delete people/Old Contact.md without -y\n"
    assert path.exists()


def test_new_strips_the_name_and_refuses_a_blank_one(vault):
    """The old flag path skipped the strip the prompt path did, so
    `--name "  "` created a file called `  .md`, and `--name ""` fell
    through to the prompt."""
    for blank in ("", "  "):
        r = vault.run("new", "--name", blank, "--category", "personal", cli="people")
        assert r.returncode == 1
        assert r.stderr == "people: error: empty name\n"
        assert list((vault.home / "people").iterdir()) == []
    r = vault.run("new", "--name", " Igor Novak ", "--category", "personal", cli="people")
    assert r.returncode == 0
    assert (vault.home / "people" / "Igor Novak.md").exists()


@pytest.mark.parametrize("name", ["../escaped", "a/b", ".hidden"])
def test_new_refuses_a_name_that_is_not_a_plain_filename(vault, name):
    """The name becomes people/<name>.md, so a `/` could write outside
    people/ (or crash), and a leading `.` would make a hidden file."""
    r = vault.run("new", "--name", name, "--category", "personal", cli="people")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == f"people: error: name {name!r} cannot contain '/' or start with '.'\n"
    assert sorted(p.relative_to(vault.home).as_posix() for p in vault.home.rglob("*.md")) == []


@pytest.mark.parametrize("command", [["delete", "-y"], ["show"], ["show", "--json"]])
@pytest.mark.parametrize("name", ["../threads/Projects/SGB", "people/../threads/Projects/SGB", ".hidden"])
def test_delete_and_show_refuse_a_name_that_is_not_a_plain_filename(vault, command, name):
    """The name becomes people/<name>.md, so `../` reached outside people/:
    `people delete ../threads/Projects/SGB -y` deleted the thread file."""
    vault.write_thread("Projects", "SGB")
    vault.write("people/.hidden.md", "---\nstatus: open\n---\n")
    before = vault.snapshot()
    r = vault.run(command[0], name, *command[1:], cli="people")
    shown = name[len("people/"):] if name.startswith("people/") else name
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == f"people: error: name {shown!r} cannot contain '/' or start with '.'\n"
    assert vault.snapshot() == before


@pytest.mark.parametrize("command", [["delete", "-y"], ["show"]])
def test_delete_and_show_need_the_exact_name(people_vault, command):
    """On macOS the filesystem ignores case, so `people delete "riaz arbi"`
    used to delete Riaz Arbi.md."""
    before = people_vault.snapshot()
    r = people_vault.run(command[0], "riaz arbi", *command[1:], cli="people")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == "people: error: not found: people/riaz arbi.md\n"
    assert people_vault.snapshot() == before


def test_show_json_lists_a_persons_cadences(vault):
    """They used to come out as "cadences": "", the old scalar-only reader
    dropping the list."""
    vault.write("people/Bern Sellmeyer.md",
                "---\nstatus: open\ncategory: professional\nstarted: 2026-01-01\ncadences:\n"
                "  - key: catch_up\n    frequency: 7\n    description: Catch up at least every week\n"
                "---\n\n# Bern Sellmeyer\n")
    r = vault.run("show", "Bern Sellmeyer", "--json", cli="people")
    assert json.loads(r.stdout) == {
        "name": "Bern Sellmeyer", "path": "people/Bern Sellmeyer.md", "status": "open",
        "category": "professional", "started": "2026-01-01",
        "cadences": [{"key": "catch_up", "frequency": "7", "description": "Catch up at least every week"}]}
