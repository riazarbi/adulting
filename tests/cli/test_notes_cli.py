"""Tests for the non-interactive `notes` commands (refactor unit 10).

The old bash `notes` chose a note through a numbered picker, so these tests
cannot run against it. What they keep from it was checked by driving that
picker on the same fixtures: `cat` prints the file verbatim, `copy` appends
` COPY` to every `topic:` line and keeps the rest, and every subcommand
ingests ACTION lines first.

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


def notes(vault, *argv):
    return subprocess.run([command_path("notes", vault.env), *argv], capture_output=True,
                          text=True, env=vault.env, input="")


def write(vault, rel, text):
    p = vault.home / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


@pytest.fixture
def v(vault):
    write(vault, "threads/Projects/SGB.md", "---\nstatus: open\n---\n")
    write(vault, "threads/Topics/Zeta.md", "---\nstatus: open\n---\n")
    write(vault, "notes/2026-09-10-14-30-00.md", KICKOFF)
    # Written on the 11th about something that happened on the 12th.
    write(vault, "notes/2026-09-11-09-00-00.md",
          '---\ntopic: "Quoted, topic"\ntype: Report\nthreads:\n  - "[[Topics/Zeta]]"\n'
          "timestamp: 2026-09-12-08-00-00\n---\n\nbody\n")
    write(vault, "notes/2026-09-12-07-00-00.md",
          '---\ntopic: Same day earlier\ntype: Log\nthread: "[[Projects/SGB]]"\n'
          "timestamp: 2026-09-12-07-00-00\n---\n\nbody\n")
    return vault


# ---------- list ----------

def test_list_is_ordered_by_timestamp_not_filename(v):
    r = notes(v, "list")
    assert (r.returncode, r.stderr) == (0, "")
    assert r.stdout == (
        "2026-09-10-14-30-00  2026-09-10  Meeting  Projects/SGB, Topics/Zeta  Kickoff\n"
        "2026-09-12-07-00-00  2026-09-12  Log      Projects/SGB               Same day earlier\n"
        "2026-09-11-09-00-00  2026-09-12  Report   Topics/Zeta                Quoted, topic\n")


def test_list_filter_and_empty_messages(v, vault):
    assert notes(v, "list", "ZETA").stdout.count("\n") == 2
    assert notes(v, "list", "report").stdout.startswith("2026-09-11-09-00-00")
    assert notes(v, "list", "nothing matches").stdout == "(no matches)\n"
    for f in (vault.home / "notes").iterdir():
        f.unlink()
    assert notes(vault, "list").stdout == "(no notes)\n"


def test_list_json(v):
    rows = json.loads(notes(v, "list", "--json").stdout)
    assert rows[1] == {
        "stem": "2026-09-12-07-00-00", "path": str(v.home / "notes" / "2026-09-12-07-00-00.md"),
        "timestamp": "2026-09-12-07-00-00", "date": "2026-09-12", "type": "Log",
        "threads": ["Projects/SGB"], "topic": "Same day earlier"}


def test_a_note_without_a_timestamp_sorts_by_its_stem(v):
    write(v, "notes/2026-09-11-12-00-00.md", "---\ntopic: Untimed\n---\n")
    stems = [r["stem"] for r in json.loads(notes(v, "list", "--json").stdout)]
    assert stems == ["2026-09-10-14-30-00", "2026-09-11-12-00-00",
                     "2026-09-12-07-00-00", "2026-09-11-09-00-00"]
    assert "2026-09-11-12-00-00  -           -" in notes(v, "list").stdout


# ---------- cat, last ----------

def test_cat_prints_the_note_after_ingesting_its_actions(v):
    r = notes(v, "cat", "2026-09-10-14-30-00")
    assert r.returncode == 0
    assert r.stdout == v.read("notes/2026-09-10-14-30-00.md")
    assert re.search(r"^TASK: ingest me <!--[0-9a-f]{8} entry:", r.stdout, re.M)


def test_cat_accepts_a_trailing_md(v):
    assert notes(v, "cat", "2026-09-12-07-00-00.md").stdout.startswith("---\ntopic: Same day")


@pytest.mark.parametrize("stem, message", [
    ("2026-01-01-00-00-00", "notes: no note '2026-01-01-00-00-00' in {notes}\n"),
    ("notes/2026-09-10-14-30-00", "notes: give a note stem like 2026-09-10-14-30-00, "
                                  "got 'notes/2026-09-10-14-30-00'\n"),
    ("", "notes: give a note stem like 2026-09-10-14-30-00, got ''\n"),
])
def test_bad_stems(v, stem, message):
    r = notes(v, "cat", stem)
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == message.format(notes=v.home / "notes")


def test_last_prints_the_newest_note_by_timestamp(v):
    r = notes(v, "last")
    assert (r.returncode, r.stdout) == (0, f"{v.home / 'notes' / '2026-09-11-09-00-00.md'}\n")


def test_last_with_no_notes(vault):
    r = notes(vault, "last")
    assert (r.returncode, r.stderr) == (1, f"notes: no notes in {vault.home / 'notes'}\n")


# ---------- copy, delete ----------

def test_copy_keeps_everything_but_marks_topic_lines(v):
    r = notes(v, "copy", "2026-09-10-14-30-00")
    m = re.fullmatch(r"Copied 2026-09-10-14-30-00\.md to (\d{4}(?:-\d{2}){5})\.md\n", r.stdout)
    assert m, r.stdout
    original = v.read("notes/2026-09-10-14-30-00.md")
    copy = v.read(f"notes/{m.group(1)}.md")
    assert copy == original.replace("topic: Kickoff\n", "topic: Kickoff COPY\n").replace(
        "topic: in the body\n", "topic: in the body COPY\n")
    assert "timestamp: 2026-09-10-14-30-00" in copy


def test_delete_needs_yes(v):
    path = v.home / "notes" / "2026-09-12-07-00-00.md"
    r = notes(v, "delete", "2026-09-12-07-00-00")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == f"notes: refusing to delete {path} without -y\n"
    assert path.exists()
    r = notes(v, "delete", "2026-09-12-07-00-00", "-y")
    assert (r.returncode, r.stdout) == (0, f"deleted: {path}\n")
    assert not path.exists()


# ---------- the ingest pre-pass ----------

def break_an_action(vault):
    write(vault, "notes/2026-09-13-09-00-00.md",
          "---\ntopic: broken\ntimestamp: 2026-09-13-09-00-00\n---\n\nACTION: (Ghost) nobody\n")


def test_a_failed_ingest_is_silent_when_stderr_is_not_a_terminal(v):
    """The agent harness drops stdout whenever stderr is non-empty, so a
    warning here would cost it the note."""
    break_an_action(v)
    r = notes(v, "cat", "2026-09-12-07-00-00")
    assert (r.returncode, r.stderr) == (0, "")
    assert r.stdout == v.read("notes/2026-09-12-07-00-00.md")
    assert "ACTION: (Ghost) nobody" in v.read("notes/2026-09-13-09-00-00.md")


def test_a_failed_ingest_warns_once_on_a_terminal(v):
    break_an_action(v)
    parent, child = pty.openpty()
    try:
        r = subprocess.run([command_path("notes", v.env), "cat", "2026-09-12-07-00-00"],
                           stdout=subprocess.PIPE, stderr=child, stdin=subprocess.DEVNULL,
                           text=True, env=v.env, timeout=30)
        # Read while the child end is still open: closing it first can
        # discard what the process wrote to the terminal.
        ready, _, _ = select.select([parent], [], [], 5)
        warning = os.read(parent, 4096).decode() if ready else ""
    finally:
        os.close(child)
        os.close(parent)
    assert r.returncode == 0
    assert r.stdout == v.read("notes/2026-09-12-07-00-00.md")
    assert warning.replace("\r\n", "\n") == (
        "notes: warning: some ACTION lines were not ingested; run `tasks` to see why\n")


def test_ingest_runs_before_list_too(v):
    notes(v, "list")
    assert "ACTION: ingest me" not in v.read("notes/2026-09-10-14-30-00.md")


def test_help_json(vault):
    manifest = json.loads(notes(vault, "--help-json").stdout)
    assert [s["name"] for s in manifest["subcommands"]] == [
        "new", "list", "cat", "last", "copy", "delete", "pdf", "minutes", "agenda"]


def test_help_json_does_not_ingest(v):
    notes(v, "--help-json")
    assert "ACTION: ingest me" in v.read("notes/2026-09-10-14-30-00.md")
