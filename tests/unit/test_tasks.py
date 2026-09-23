"""Unit tests for adulting.tasks. conftest points ADULTING_HOME at tmp_path/vault."""

import pytest

from adulting import tasks as T

FULL = ("DONE: [#H] (Riaz Arbi) Send the report "
        "<!--abcd1234 entry:2026-05-27 end:2026-05-29 due:2026-05-29 "
        "scheduled:2026-05-28 depends:ef567890,aaaa0001-->  ")


def test_parse_anchor_reads_every_field():
    a = T.parse_anchor(FULL)
    assert (a.kind, a.priority, a.assignee, a.body, a.uuid) == (
        "DONE", "H", "Riaz Arbi", "Send the report", "abcd1234")
    assert (a.entry, a.end, a.due, a.scheduled, a.depends) == (
        "2026-05-27", "2026-05-29", "2026-05-29", "2026-05-28", ("ef567890", "aaaa0001"))


def test_format_anchor_round_trips_with_a_hard_break():
    assert T.format_anchor(T.parse_anchor(FULL)) == FULL
    bare = "TASK: Pick up dry cleaning <!--ef567890 entry:2026-05-27-->"
    assert T.format_anchor(T.parse_anchor(bare)) == bare + "  "


@pytest.mark.parametrize("line", [
    "TASK: no comment",
    "TASK: bad uuid <!--XYZ entry:2026-05-27-->",
    "TASK: attrs out of order <!--abcd1234 due:2026-05-29 entry:2026-05-27-->",
    "ACTION: not an anchor",
    "  TASK: indented <!--abcd1234 entry:2026-05-27-->",
])
def test_parse_anchor_rejects_other_lines(line):
    assert T.parse_anchor(line) is None




@pytest.fixture
def tasks_home():
    h = T.V.vault_home()
    files = {
        "notes/2026-01-01-00-00-00.md": '---\nthreads:\n  - "[[Projects/SGB]]"\n---\n\n'
                                        "TASK: one <!--aaaa0001 entry:2026-01-01-->\nplain\n",
        "notes/.hidden.md": "TASK: hidden <!--bbbb0001 entry:2026-01-01-->\n",
        "logs/Projects/SGB/2026-01-02.md": '---\nthread: "[[Projects/SGB]]"\n---\n\n'
                                           "DONE: two <!--aaaa0002 entry:2026-01-02 end:2026-01-03-->\n",
        "logs/.trash/2026-01-03.md": "TASK: trashed <!--cccc0001 entry:2026-01-01-->\n",
        "threads/Projects/SGB.md": "x",
        "people/Riaz Arbi.md": "x",
    }
    for rel, text in files.items():
        (h / rel).parent.mkdir(parents=True, exist_ok=True)
        (h / rel).write_text(text)
    return h


def test_walk_anchors_skips_dot_files_and_dirs(tasks_home):
    assert [(a.uuid, a.line_no) for a in T.walk_anchors()] == [("aaaa0001", 5), ("aaaa0002", 4)]


def test_find_anchor(tasks_home):
    assert T.find_anchor("AAAA0001").body == "one"
    with pytest.raises(SystemExit):
        T.find_anchor("aaaa")
    with pytest.raises(SystemExit):
        T.find_anchor("ffff")


def test_mutate_anchor_rewrites_only_that_line(tasks_home):
    a = T.find_anchor("aaaa0001")
    T.mutate_anchor(a, priority="M", due="2026-02-01")
    assert (tasks_home / "notes/2026-01-01-00-00-00.md").read_text().split("\n")[4:] == [
        "", "TASK: [#M] one <!--aaaa0001 entry:2026-01-01 due:2026-02-01-->  ", "plain", ""]
    assert not list(tasks_home.rglob("*.tmp"))


def test_threads_cache_and_resolvers(tasks_home):
    cache = T.build_threads_cache()
    assert cache["notes/2026-01-01-00-00-00"] == ["Projects/SGB"]
    assert T.threads_for(T.find_anchor("aaaa0002"), cache) == ["Projects/SGB"]


def test_ingest_returns_what_it_did_and_prints_nothing(tasks_home, capsys):
    note = tasks_home / "notes" / "2026-01-05-00-00-00.md"
    note.write_text('---\nthreads:\n  - "[[Projects/SGB]]"\n---\n\nACTION: (Riaz Arbi) Draft it\nACTION:  \n')
    ingested, failed = T.ingest()
    [(uuid, where, body, line)] = ingested
    assert (where, body) == ("notes/2026-01-05-00-00-00.md:6", "Draft it")
    assert line == f"TASK: (Riaz Arbi) Draft it <!--{uuid} entry:{T.V.today()}-->  "
    assert failed == [("notes/2026-01-05-00-00-00.md:7", ["missing description"])]
    assert note.read_text().split("\n")[5] == line
    assert capsys.readouterr() == ("", "")


def test_ingest_dry_run_writes_nothing(tasks_home):
    note = tasks_home / "notes" / "2026-01-05-00-00-00.md"
    text = '---\nthreads:\n  - "[[Projects/SGB]]"\n---\n\nACTION: Draft it\n'
    note.write_text(text)
    ingested, failed = T.ingest(dry_run=True)
    assert (len(ingested), failed) == (1, [])
    assert note.read_text() == text
