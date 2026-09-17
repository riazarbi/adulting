"""Unit tests for adulting.notes. conftest points ADULTING_HOME at tmp_path/vault."""

import pytest

from adulting import notes as N


@pytest.fixture
def notes_dir():
    d = N.notes_dir()
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


def test_ingest_actions_is_silent_when_everything_ingests(notes_dir, capsys):
    N.ingest_actions()
    assert capsys.readouterr() == ("", "")


def test_ingest_actions_warns_once_on_failure(notes_dir, capsys):
    (notes_dir / "2026-09-10-14-30-00.md").write_text("---\ntopic: x\n---\n\nACTION: no threads\n")
    N.ingest_actions()
    out, err = capsys.readouterr()
    assert out == ""
    assert err == "notes: warning: some ACTION lines were not ingested; run `tasks` to see why\n"
