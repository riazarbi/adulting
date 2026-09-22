"""Unit tests for adulting.buffer. conftest points ADULTING_HOME at tmp_path/vault."""

import re

import pytest

from adulting import buffer as B


def test_parse_action_attrs():
    attrs, errors = B.parse_action_attrs(
        ["due:2026-09-20", "priority:H", "depends:aaaaaaaa", "depends:bbbbbbbb",
         "scheduled:2026-09-15", ""])
    assert attrs == {"depends": ["aaaaaaaa", "bbbbbbbb"], "due": "2026-09-20",
                     "priority": "H", "scheduled": "2026-09-15"}
    assert errors == []
    _, errors = B.parse_action_attrs(["due:soon", "priority:X", "depends:XYZ", "foo", "bar:1"])
    assert errors == ["due must be YYYY-MM-DD; got 'soon'",
                      "priority must be H, M, or L; got 'X'",
                      "depends must be 8 hex chars; got 'XYZ'",
                      "unknown attr token 'foo'",
                      "unknown attr 'bar'"]


def test_format_action_attrs_is_deterministic():
    assert B.format_action_attrs({"scheduled": "2026-09-15", "priority": "L", "due": "2026-09-20",
                                  "depends": ["bbbbbbbb", "aaaaaaaa"]}) == \
        "depends:aaaaaaaa depends:bbbbbbbb due:2026-09-20 priority:L scheduled:2026-09-15"
    assert B.format_action_attrs({"depends": []}) == ""


def test_attrs_round_trip():
    text = "depends:aaaaaaaa due:2026-09-20 priority:M"
    attrs, _ = B.parse_action_attrs(text.split())
    assert B.format_action_attrs(attrs) == text


def test_stamp():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", B.stamp())
    assert B.stamp("2026-08-04").startswith("2026-08-04T")
    with pytest.raises(SystemExit):
        B.stamp("4 Aug")


def test_parse_buffer_entries_classifies_lines():
    lines = [
        "- [[Projects/SGB]] ACTION: (Riaz) Do it <!--2026-09-10T15:00:00 due:2026-09-20-->",
        "",
        "<!-- UNKNOWN ENTRIES BELOW: separator -->",
        "- UNKNOWN: raw <!--2026-09-09T08:00:00-->",
        "garbage",
        "<!-- some other comment -->",
    ]
    entries, unknowns, unparsed = B.parse_buffer_entries(lines)
    assert [(e["line_no"], e["thread"], e["type"], e["body"], e["date"], e["attr_tokens"])
            for e in entries] == [(1, "Projects/SGB", "ACTION", "(Riaz) Do it", "2026-09-10",
                                   ["due:2026-09-20"])]
    assert [(u["line_no"], u["body"]) for u in unknowns] == [(4, "raw")]
    assert unparsed == [(5, "garbage"), (6, "<!-- some other comment -->")]


def test_regroup_lines_orders_groups_then_unknowns_then_unparsed():
    lines = ["- [[Topics/B]] TEXT: b <!--2026-09-10T09:00:00-->",
             "- UNKNOWN: u2 <!--2026-09-12T08:00:00-->",
             "- [[Projects/A]] TEXT: a2 <!--2026-09-11T09:00:00-->",
             "junk",
             "- [[Projects/A]] TEXT: a1-late <!--2026-09-10T18:00:00-->",
             "- [[Projects/A]] TEXT: a1-early <!--2026-09-10T07:00:00-->",
             "- UNKNOWN: u1 <!--2026-09-09T08:00:00-->"]
    out = B.regroup_lines(*B.parse_buffer_entries(lines))
    assert [l.split(": ", 1)[-1].split(" <!")[0] if l.startswith("-") else l for l in out] == [
        "a1-early", "a1-late", "a2", "b", "",
        "<!-- UNKNOWN ENTRIES BELOW: convert via `buffer rm <n>` + the matching `buffer add-*`. tend will fail until cleared. -->",
        "u1", "u2", "",
        "<!-- UNPARSED ENTRIES BELOW: tend cannot regroup these. Fix or remove via `buffer rm`. -->",
        "junk"]


@pytest.fixture
def home():
    h = B.vault_home()
    for rel in ("threads/Projects/SGB.md", "people/Riaz Arbi.md", "notes/n.md",
                "hours/Projects/SGB.md"):
        (h / rel).parent.mkdir(parents=True, exist_ok=True)
        (h / rel).write_text("x")
    return h


def test_resolvers(home):
    assert B.canonical_thread("[[Projects/SGB]]", "unused") == "Projects/SGB"
    assert B.assignee_resolves("") and B.assignee_resolves("Riaz Arbi")
    assert not B.assignee_resolves("Ghost")
    assert B.ref_target_resolves("notes/n") == home / "notes/n.md"
    assert B.ref_target_resolves("Projects/SGB") == home / "threads/Projects/SGB.md"
    assert B.ref_target_resolves("hours/Projects/SGB") == home / "hours/Projects/SGB.md"
    for bad in ("", "notes/nope", "assets/x"):
        assert B.ref_target_resolves(bad) is None, bad


def entry(line):
    [e], _, _ = B.parse_buffer_entries([line])
    return e


def test_validate_entry(home):
    ok = "- [[Projects/SGB]] ACTION: (Riaz Arbi) Do <!--2026-09-10T15:00:00 priority:H-->"
    assert list(B.validate_entry(entry(ok))) == []
    assert list(B.validate_entry(entry(
        "- [[Projects/SGB]] ACTION: (Ghost) Do <!--2026-09-99T15:00:00-->"))) == [
        "timestamp '2026-09-99T15:00:00' is not YYYY-MM-DDTHH:MM:SS",
        "ACTION assignee 'Ghost' does not resolve to people/Ghost.md"]
    assert list(B.validate_entry(entry(
        "- [[Projects/SGB]] REF: [[notes/n]] x <!--2026-09-10T15:00:00 due:2026-09-20-->"))) == [
        "REF entries do not accept attrs; got 'due:2026-09-20'"]


def test_read_append_write_buffer(home):
    assert B.read_buffer() == []
    B.write_buffer(["a", "", ""])
    B.append_line("b")
    assert B.buffer_file().read_text() == "a\nb\n"
    B.write_buffer([])
    assert B.buffer_file().read_text() == ""


def test_format_suggestion_quotes_for_the_shell():
    assert B._shquote("Projects/SGB") == "Projects/SGB"
    assert B._shquote("it's here") == "'it'\\''s here'"
    assert B.format_suggestion({"subcmd": "add-action", "thread": "Projects/SGB",
                                "body": "Draft scope", "due": "2026-09-30",
                                "scheduled": None, "priority": "H"}) == \
        "buffer add-action Projects/SGB 'Draft scope' --due 2026-09-30 --priority H"
    assert B.format_suggestion({"subcmd": "add-text", "thread": "Topics/X", "body": "hi"}) == \
        "buffer add-text Topics/X hi"
