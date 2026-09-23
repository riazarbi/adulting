"""The `notes` commands that pick a note by name: list, cat, last, copy,
delete.

A note is named on the command line; nothing prompts. `cat` prints the file
verbatim, `copy` appends ` COPY` to every `topic:` line and keeps the rest,
and every subcommand ingests ACTION lines first.

`notes` is this package's command.
"""

import json
import os
import pty
import re
import select
import subprocess

import pytest

from harness import command_path

KICKOFF = ('---\ntopic: Kickoff\ntype: Meeting\nthreads:\n  - "[[Projects/SGB]]"\n'
           '  - "[[Topics/Zeta]]"\ntimestamp: 2026-09-10-14-30-00\n---\n\n'
           "# Content\n\ntopic: in the body\nACTION: ingest me\n")


@pytest.fixture
def notes_vault(vault):
    vault.write("threads/Projects/SGB.md", "---\nstatus: open\n---\n")
    vault.write("threads/Topics/Zeta.md", "---\nstatus: open\n---\n")
    vault.write("notes/2026-09-10-14-30-00.md", KICKOFF)
    # Written on the 11th about something that happened on the 12th.
    vault.write("notes/2026-09-11-09-00-00.md",
          '---\ntopic: "Quoted, topic"\ntype: Report\nthreads:\n  - "[[Topics/Zeta]]"\n'
          "timestamp: 2026-09-12-08-00-00\n---\n\nbody\n")
    vault.write("notes/2026-09-12-07-00-00.md",
          '---\ntopic: Same day earlier\ntype: Log\nthread: "[[Projects/SGB]]"\n'
          "timestamp: 2026-09-12-07-00-00\n---\n\nbody\n")
    return vault


# ---------- list ----------

def test_list_is_ordered_by_timestamp_not_filename(notes_vault):
    r = notes_vault.run("list", cli="notes")
    assert (r.returncode, r.stderr) == (0, "")
    assert r.stdout == (
        "2026-09-10-14-30-00  2026-09-10  Meeting  Projects/SGB, Topics/Zeta  Kickoff\n"
        "2026-09-12-07-00-00  2026-09-12  Log      Projects/SGB               Same day earlier\n"
        "2026-09-11-09-00-00  2026-09-12  Report   Topics/Zeta                Quoted, topic\n")


def test_list_filter_and_empty_messages(notes_vault, vault):
    assert notes_vault.run("list", "ZETA", cli="notes").stdout.count("\n") == 2
    assert notes_vault.run("list", "report", cli="notes").stdout.startswith("2026-09-11-09-00-00")
    assert notes_vault.run("list", "nothing matches", cli="notes").stdout == "(no matches)\n"
    for f in (vault.home / "notes").iterdir():
        f.unlink()
    assert vault.run("list", cli="notes").stdout == "(no notes)\n"


def test_list_json(notes_vault):
    rows = json.loads(notes_vault.run("list", "--json", cli="notes").stdout)
    assert rows[1] == {
        "stem": "2026-09-12-07-00-00", "path": str(notes_vault.home / "notes" / "2026-09-12-07-00-00.md"),
        "timestamp": "2026-09-12-07-00-00", "date": "2026-09-12", "type": "Log",
        "threads": ["Projects/SGB"], "topic": "Same day earlier"}


def test_a_note_without_a_timestamp_sorts_by_its_stem(notes_vault):
    notes_vault.write("notes/2026-09-11-12-00-00.md", "---\ntopic: Untimed\n---\n")
    stems = [r["stem"] for r in json.loads(notes_vault.run("list", "--json", cli="notes").stdout)]
    assert stems == ["2026-09-10-14-30-00", "2026-09-11-12-00-00",
                     "2026-09-12-07-00-00", "2026-09-11-09-00-00"]
    assert "2026-09-11-12-00-00  -           -" in notes_vault.run("list", cli="notes").stdout


# ---------- cat, last ----------

def test_cat_prints_the_note_after_ingesting_its_actions(notes_vault):
    r = notes_vault.run("cat", "2026-09-10-14-30-00", cli="notes")
    assert r.returncode == 0
    assert r.stdout == notes_vault.read("notes/2026-09-10-14-30-00.md")
    assert re.search(r"^TASK: ingest me <!--[0-9a-f]{8} entry:", r.stdout, re.M)


def test_cat_accepts_a_trailing_md(notes_vault):
    assert notes_vault.run("cat", "2026-09-12-07-00-00.md", cli="notes").stdout.startswith("---\ntopic: Same day")


@pytest.mark.parametrize("stem, message", [
    ("2026-01-01-00-00-00", "notes: error: no note '2026-01-01-00-00-00' in {notes}\n"),
    ("notes/2026-09-10-14-30-00", "notes: error: give a note stem like 2026-09-10-14-30-00, "
                                  "got 'notes/2026-09-10-14-30-00'\n"),
    ("", "notes: error: give a note stem like 2026-09-10-14-30-00, got ''\n"),
    (".hidden", "notes: error: give a note stem like 2026-09-10-14-30-00, got '.hidden'\n"),
])
def test_bad_stems(notes_vault, stem, message):
    r = notes_vault.run("cat", stem, cli="notes")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == message.format(notes=notes_vault.home / "notes")


def test_last_prints_the_newest_note_by_timestamp(notes_vault):
    r = notes_vault.run("last", cli="notes")
    assert (r.returncode, r.stdout) == (0, f"{notes_vault.home / 'notes' / '2026-09-11-09-00-00.md'}\n")


def test_last_with_no_notes(vault):
    r = vault.run("last", cli="notes")
    assert (r.returncode, r.stderr) == (1, f"notes: error: no notes in {vault.home / 'notes'}\n")


# ---------- copy, delete ----------

def test_copy_marks_every_topic_line_and_keeps_the_timestamp(notes_vault):
    # DEFERRED BUG 4: every line starting with `topic:` gets ` COPY`, body
    # lines included, and the copy keeps the original `timestamp:`.
    r = notes_vault.run("copy", "2026-09-10-14-30-00", cli="notes")
    m = re.fullmatch(r"Copied 2026-09-10-14-30-00\.md to (\d{4}(?:-\d{2}){5})\.md\n", r.stdout)
    assert m, r.stdout
    original = notes_vault.read("notes/2026-09-10-14-30-00.md")
    copy = notes_vault.read(f"notes/{m.group(1)}.md")
    assert copy == original.replace("topic: Kickoff\n", "topic: Kickoff COPY\n").replace(
        "topic: in the body\n", "topic: in the body COPY\n")
    assert "timestamp: 2026-09-10-14-30-00" in copy


def test_delete_needs_yes(notes_vault):
    path = notes_vault.home / "notes" / "2026-09-12-07-00-00.md"
    r = notes_vault.run("delete", "2026-09-12-07-00-00", cli="notes")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == "notes: error: refusing to delete notes/2026-09-12-07-00-00.md without -y\n"
    assert path.exists()
    r = notes_vault.run("delete", "2026-09-12-07-00-00", "-y", cli="notes")
    assert (r.returncode, r.stdout) == (0, "deleted: notes/2026-09-12-07-00-00.md\n")
    assert not path.exists()


# ---------- the ingest pre-pass ----------

def break_an_action(vault):
    vault.write("notes/2026-09-13-09-00-00.md",
          "---\ntopic: broken\ntimestamp: 2026-09-13-09-00-00\n---\n\nACTION: (Ghost) nobody\n")


def test_a_failed_ingest_is_silent_when_stderr_is_not_a_terminal(notes_vault):
    """The agent harness drops stdout whenever stderr is non-empty, so a
    warning here would cost it the note."""
    break_an_action(notes_vault)
    r = notes_vault.run("cat", "2026-09-12-07-00-00", cli="notes")
    assert (r.returncode, r.stderr) == (0, "")
    assert r.stdout == notes_vault.read("notes/2026-09-12-07-00-00.md")
    assert "ACTION: (Ghost) nobody" in notes_vault.read("notes/2026-09-13-09-00-00.md")


def test_a_failed_ingest_warns_once_on_a_terminal(notes_vault):
    break_an_action(notes_vault)
    # stderr, not stdin, is the terminal here, so this runs the command
    # itself rather than through vault.run_on_a_terminal.
    parent, child = pty.openpty()
    try:
        r = subprocess.run([command_path("notes", notes_vault.env), "cat", "2026-09-12-07-00-00"],
                           stdout=subprocess.PIPE, stderr=child, stdin=subprocess.DEVNULL,
                           text=True, env=notes_vault.env, timeout=30)
        # Read while the child end is still open: closing it first can
        # discard what the process wrote to the terminal.
        ready, _, _ = select.select([parent], [], [], 5)
        warning = os.read(parent, 4096).decode() if ready else ""
    finally:
        os.close(child)
        os.close(parent)
    assert r.returncode == 0
    assert r.stdout == notes_vault.read("notes/2026-09-12-07-00-00.md")
    assert warning.replace("\r\n", "\n") == (
        "notes: warning: some ACTION lines were not ingested; run `tasks` to see why\n")


INGESTED = re.compile(r"TASK: ingest me <!--[0-9a-f]{8} entry:\d{4}-\d\d-\d\d-->  ")


@pytest.mark.parametrize("argv", [
    ["list"], ["cat", "2026-09-12-07-00-00"], ["last"], ["copy", "2026-09-12-07-00-00"],
    ["delete", "2026-09-12-07-00-00", "-y"],
    ["minutes", "2026-09-12-07-00-00", "--out", "{out}"],
    ["agenda", "2026-09-12-07-00-00", "--out", "{out}"],
    ["pdf", "2026-09-12-07-00-00", "--out", "{out}"],
], ids=lambda a: a[0])
def test_every_subcommand_but_new_ingests_first(notes_vault, tmp_path, argv):
    """The ACTION in the Kickoff note becomes a TASK, whichever note the
    subcommand is about."""
    notes_vault.run(*[a.format(out=tmp_path / "out") for a in argv], cli="notes")
    assert INGESTED.fullmatch(notes_vault.lines("notes/2026-09-10-14-30-00.md")[-2])


def test_help_json_does_not_ingest(notes_vault):
    notes_vault.run("--help-json", cli="notes")
    assert "ACTION: ingest me" in notes_vault.read("notes/2026-09-10-14-30-00.md")
