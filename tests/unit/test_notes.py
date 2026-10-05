"""Unit tests for adulting.notes. conftest points ADULTING_HOME at tmp_path/vault."""

import re

import pytest

from adulting import notes as N


@pytest.fixture
def notes_dir():
    """A thread's notes folder; notes live in their first thread's folder."""
    d = N.V.thread_folder("Projects/SGB") / "notes"
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_note_path(notes_dir):
    (notes_dir / "2026-09-10-14-30-00.md").write_text("x")
    assert N.note_path(" 2026-09-10-14-30-00 ") == notes_dir / "2026-09-10-14-30-00.md"
    assert N.note_path("2026-09-10-14-30-00.md") == notes_dir / "2026-09-10-14-30-00.md"
    for bad in ("", "nope", "../people/x", "notes/2026-09-10-14-30-00"):
        with pytest.raises(SystemExit):
            N.note_path(bad)


def test_note_info_reads_lists_scalars_and_quotes(notes_dir):
    p = notes_dir / "2026-09-11-09-00-00.md"
    p.write_text('---\ntopic: "Quoted, topic"\ntype: Report\nthreads:\n  - "[[Topics/Zeta]]"\n'
                 "  - Projects/Plain\ntimestamp: 2026-09-12-08-00-00\n---\nbody\n")
    assert N.note_info(p) == {
        "stem": "2026-09-11-09-00-00", "path": str(p), "timestamp": "2026-09-12-08-00-00",
        "date": "2026-09-12", "type": "Report", "threads": ["Topics/Zeta", "Projects/Plain"],
        "topic": "Quoted, topic"}
    q = notes_dir / "2026-09-12-00-00-00.md"
    q.write_text("no frontmatter\n")
    assert N.note_info(q)["threads"] == [] and N.note_info(q)["date"] == ""


def test_sort_key_falls_back_to_the_stem():
    good = {"timestamp": "2026-09-12-08-00-00", "stem": "2026-01-01-00-00-00"}
    bad = {"timestamp": "yesterday", "stem": "2026-09-11-00-00-00"}
    assert N.sort_key(good) == ("2026-09-12-08-00-00", "2026-01-01-00-00-00")
    assert N.sort_key(bad) == ("2026-09-11-00-00-00", "2026-09-11-00-00-00")


def test_all_notes_skips_dot_files_and_handles_a_missing_dir(notes_dir, tmp_path, monkeypatch):
    (notes_dir / ".hidden.md").write_text("---\ntopic: x\n---\n")
    (notes_dir / "2026-09-10-14-30-00.md").write_text("---\ntopic: x\n---\n")
    assert [n["stem"] for n in N.all_notes()] == ["2026-09-10-14-30-00"]
    monkeypatch.setenv("ADULTING_HOME", str(tmp_path / "empty"))
    assert N.all_notes() == []


def test_ingest_actions_turns_an_action_into_a_task_anchor_quietly(notes_dir, capsys):
    threads = N.V.vault_home() / "threads" / "Projects"
    threads.mkdir(parents=True, exist_ok=True)
    (threads / "SGB.md").write_text("---\nstatus: open\n---\n")
    note = notes_dir / "2026-09-10-14-30-00.md"
    note.write_text('---\nthreads:\n  - "[[Projects/SGB]]"\n---\n\nACTION: do it\n')
    N.ingest_actions()
    assert re.search(r"^TASK: do it <!--[0-9a-f]{8} entry:", note.read_text(), re.M)
    assert capsys.readouterr() == ("", "")


def test_ingest_actions_leaves_a_failing_action_and_stays_silent_without_a_terminal(notes_dir, capsys):
    """capsys stands in for a pipe: not a terminal. The terminal case is in
    tests/cli/test_notes_cli.py, on a real pseudo-terminal."""
    note = notes_dir / "2026-09-10-14-30-00.md"
    note.write_text("---\ntopic: x\n---\n\nACTION: no threads\n")
    N.ingest_actions()
    assert note.read_text() == "---\ntopic: x\n---\n\nACTION: no threads\n"
    assert capsys.readouterr() == ("", "")


# ---------- new ----------

def test_quote_escapes_only_double_quotes():
    assert N.quote('Q3 "review": a\\b') == '"Q3 \\"review\\": a\\b"'


def test_people_entry_links_known_people():
    people = N.V.vault_home() / "people"
    people.mkdir(parents=True, exist_ok=True)
    (people / "Riaz Arbi.md").write_text("x")
    assert N.people_entry("Riaz Arbi") == '"[[people/Riaz Arbi]]"'
    assert N.people_entry('Bern "B"') == '"Bern \\"B\\""'


def test_note_text_for_a_log_and_a_meeting():
    assert N.note_text("2026-09-17-10-00-00", "Log", "Daily", ["Topics/Zeta"]) == (
        '---\ntopic: Daily\ntype: Log\nthreads:\n  - "[[Topics/Zeta]]"\n'
        'timestamp: 2026-09-17-10-00-00\naliases: ["Daily"]\n---\n\n# Content\n\n')
    meeting = N.note_text("2026-09-17-10-00-00", "Meeting", "Kickoff",
                          ["Projects/SGB", "Topics/Zeta"], ["Someone"], "ACME", "")
    # Someone has no people/ file, so they are a plain name, not a wikilink.
    assert meeting == (
        '---\ntopic: Kickoff\ntype: Meeting\nthreads:\n  - "[[Projects/SGB]]"\n  - "[[Topics/Zeta]]"\n'
        'timestamp: 2026-09-17-10-00-00\naliases: ["Kickoff"]\ncounterparty: ACME\nlocation: \n'
        'people:\n  - "Someone"\n---\n\n# Content\n\n')
