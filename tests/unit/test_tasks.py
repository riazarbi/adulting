"""Unit tests for adulting.tasks. conftest points ADULTING_HOME at tmp_path/vault."""

import re

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


def test_parse_action_attrs_tolerates_the_buffer_timestamp():
    attrs, errors = T.parse_action_attrs("2026-09-10T08:00:00 due:2026-09-20 depends:aaaa0001")
    assert attrs == {"depends": ["aaaa0001"], "due": "2026-09-20"}
    assert errors == []
    attrs, errors = T.parse_action_attrs("due:soon priority:H")
    assert attrs == {"depends": [], "priority": "H"}  # bad values are not kept
    assert errors == ["due must be YYYY-MM-DD; got 'soon'"]


def test_parse_frontmatter_threads():
    note = '---\ntopic: x\nthreads:\n  - "[[Projects/SGB]]"\n  - Topics/Plain\ntype: Log\n---\nthreads: body\n'
    assert T.parse_frontmatter_threads(note) == ["Projects/SGB", "Topics/Plain"]
    log = "---\nthread: '[[Topics/zeta]]'\n---\n"
    assert T.parse_frontmatter_threads(log) == ["Topics/zeta"]
    assert T.parse_frontmatter_threads("no frontmatter") == []


def test_sort_keys_and_thread_cell():
    high_late = T.parse_anchor("TASK: [#H] a <!--aaaa0002 entry:2026-05-27 due:2026-06-30-->")
    high_soon = T.parse_anchor("TASK: [#H] b <!--aaaa0003 entry:2026-05-28 due:2026-06-01-->")
    none = T.parse_anchor("TASK: c <!--aaaa0001 entry:2026-05-01-->")
    assert sorted([none, high_late, high_soon], key=T._sort_key) == [high_soon, high_late, none]
    assert T._thread_sort_key([]) == (1, "")
    assert T._thread_sort_key(["projects/b", "A"]) == (0, "projects/b")
    assert T._format_threads([]) == "-"
    assert T._format_threads(["Projects/SGB", "Topics/X", "Topics/Y"]) == "Projects/SGB +2"


def test_validators_and_uuid_generation():
    assert T.validate_date("2026-05-27") == "2026-05-27"
    with pytest.raises(ValueError):
        T.validate_date("27 May")
    with pytest.raises(ValueError):
        T.validate_priority("Z")
    for _ in range(50):
        assert re.fullmatch(r"[0-9a-f]{8}", T.gen_uuid8(set()))


@pytest.fixture
def home():
    h = T.vault_home()
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


def test_walk_anchors_skips_dot_files_and_dirs(home):
    assert [(a.uuid, a.line_no) for a in T.walk_anchors()] == [("aaaa0001", 5), ("aaaa0002", 4)]


def test_find_anchor(home):
    assert T.find_anchor("AAAA0001").body == "one"
    with pytest.raises(SystemExit):
        T.find_anchor("aaaa")
    with pytest.raises(SystemExit):
        T.find_anchor("ffff")


def test_mutate_anchor_rewrites_only_that_line(home):
    a = T.find_anchor("aaaa0001")
    T.mutate_anchor(a, priority="M", due="2026-02-01")
    assert (home / "notes/2026-01-01-00-00-00.md").read_text().split("\n")[4:] == [
        "", "TASK: [#M] one <!--aaaa0001 entry:2026-01-01 due:2026-02-01-->  ", "plain", ""]
    assert not list(home.rglob("*.tmp"))


def test_threads_cache_and_resolvers(home):
    cache = T.build_threads_cache()
    assert cache["notes/2026-01-01-00-00-00"] == ["Projects/SGB"]
    assert T.threads_for(T.find_anchor("aaaa0002"), cache) == ["Projects/SGB"]
    assert T.assignee_resolves(None) and T.assignee_resolves("Riaz Arbi")
    assert not T.assignee_resolves("Ghost")
