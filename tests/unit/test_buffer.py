"""Unit tests for adulting.buffer. conftest points ADULTING_HOME at tmp_path/vault."""

import re

import pytest

from adulting import buffer as B


def test_format_action_attrs_is_deterministic():
    assert B.format_action_attrs({"scheduled": "2026-09-15", "priority": "L", "due": "2026-09-20",
                                  "depends": ["bbbbbbbb", "aaaaaaaa"]}) == \
        "depends:aaaaaaaa depends:bbbbbbbb due:2026-09-20 priority:L scheduled:2026-09-15"
    assert B.format_action_attrs({"depends": []}) == ""


def test_attrs_round_trip():
    text = "depends:aaaaaaaa due:2026-09-20 priority:M"
    attrs, _ = B.V.parse_action_attrs(text.split())
    assert B.format_action_attrs(attrs) == text


def test_stamp():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", B.stamp())
    assert B.stamp("2026-08-04").startswith("2026-08-04T")
    with pytest.raises(ValueError, match="^--date must be YYYY-MM-DD; got '4 Aug'$"):
        B.stamp("4 Aug")


def test_parse_buffer_entries_classifies_lines():
    lines = [
        "- [[Projects/SQR]] ACTION: (Remy) Do it <!--2026-09-10T15:00:00 due:2026-09-20-->",
        "",
        "<!-- UNKNOWN ENTRIES BELOW: separator -->",
        "- UNKNOWN: raw <!--2026-09-09T08:00:00-->",
        "garbage",
        "<!-- some other comment -->",
    ]
    entries, unknowns, unparsed = B.parse_buffer_entries(lines)
    assert [(e["line_no"], e["thread"], e["type"], e["body"], e["date"], e["attr_tokens"])
            for e in entries] == [(1, "Projects/SQR", "ACTION", "(Remy) Do it", "2026-09-10",
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
    assert [ln.split(": ", 1)[-1].split(" <!")[0] if ln.startswith("-") else ln for ln in out] == [
        "a1-early", "a1-late", "a2", "b", "",
        "<!-- UNKNOWN ENTRIES BELOW: convert via `buffer rm <n>` + the matching `buffer add-*`. tend will fail until cleared. -->",
        "u1", "u2", "",
        "<!-- UNPARSED ENTRIES BELOW: tend cannot regroup these. Fix or remove via `buffer rm`. -->",
        "junk"]


STEM = "2026-09-10-14-30-00"


@pytest.fixture
def buffer_home():
    h = B.V.vault_home()
    for rel in ("threads/Projects/SQR.md", "people/Remy Dorn.md",
                f"threads/Projects/SQR/notes/{STEM}.md", "threads/Projects/SQR/hours.md",
                "threads/Projects/SQR/payments.md", "threads/Projects/SQR/logs/2026-09-10.md"):
        (h / rel).parent.mkdir(parents=True, exist_ok=True)
        (h / rel).write_text("x")
    return h


def test_resolvers(buffer_home):
    assert B.canonical_thread("[[Projects/SQR]]") == "Projects/SQR"
    assert B.ref_target_resolves(STEM) == buffer_home / f"threads/Projects/SQR/notes/{STEM}.md"
    assert B.ref_target_resolves("Projects/SQR") == buffer_home / "threads/Projects/SQR.md"
    assert B.ref_target_resolves("Projects/SQR/hours") == buffer_home / "threads/Projects/SQR/hours.md"
    for bad in ("", "nope", "assets/x"):
        assert B.ref_target_resolves(bad) is None, bad


def test_every_ref_target_form_resolves_and_the_old_forms_do_not(buffer_home):
    """A REF target names a thread, a file in a thread's folder, a note by
    its bare stem, or a person. The pre-thread-folder forms (notes/<stem>,
    hours/<Kind>/<Name>, ...) name folders that no longer exist, and do not
    resolve even if a leftover file is still there."""
    sqr = buffer_home / "threads/Projects/SQR"
    for target, path in (
            ("Projects/SQR", buffer_home / "threads/Projects/SQR.md"),
            ("Projects/SQR/hours", sqr / "hours.md"),
            ("Projects/SQR/payments", sqr / "payments.md"),
            ("Projects/SQR/logs/2026-09-10", sqr / "logs/2026-09-10.md"),
            (f"Projects/SQR/notes/{STEM}", sqr / f"notes/{STEM}.md"),
            (STEM, sqr / f"notes/{STEM}.md"),
            ("people/Remy Dorn", buffer_home / "people/Remy Dorn.md")):
        assert B.ref_target_resolves(target) == path, target
    for rel in (f"notes/{STEM}.md", "hours/Projects/SQR.md", "payments/Projects/SQR.md",
                "logs/Projects/SQR/2026-09-10.md"):
        (buffer_home / rel).parent.mkdir(parents=True, exist_ok=True)
        (buffer_home / rel).write_text("x")
    for old in (f"notes/{STEM}", "hours/Projects/SQR", "payments/Projects/SQR",
                "logs/Projects/SQR/2026-09-10"):
        assert B.ref_target_resolves(old) is None, old


def entry(line):
    [e], _, _ = B.parse_buffer_entries([line])
    return e


def test_validate_entry(buffer_home):
    ok = "- [[Projects/SQR]] ACTION: (Remy Dorn) Do <!--2026-09-10T15:00:00 priority:H-->"
    assert list(B.validate_entry(entry(ok))) == []
    assert list(B.validate_entry(entry(
        "- [[Projects/SQR]] ACTION: (Ghost) Do <!--2026-09-99T15:00:00-->"))) == [
        "timestamp '2026-09-99T15:00:00' is not YYYY-MM-DDTHH:MM:SS",
        "ACTION assignee 'Ghost' does not resolve to people/Ghost.md"]
    assert list(B.validate_entry(entry(
        "- [[Projects/SQR]] REF: [[2026-09-10-14-30-00]] x <!--2026-09-10T15:00:00 due:2026-09-20-->"))) == [
        "REF entries do not accept attrs; got 'due:2026-09-20'"]


def test_read_append_write_buffer(buffer_home):
    assert B.read_buffer() == []
    B.write_buffer(["a", "", ""])
    B.append_line("b")
    assert B.buffer_file().read_text() == "a\nb\n"
    B.write_buffer([])
    assert B.buffer_file().read_text() == ""



# ---------- the add functions are for other commands too ----------

def test_an_add_function_returns_its_line_and_prints_nothing(buffer_home, capsys):
    line = B.buffer_text("SQR", "hello")
    assert re.fullmatch(r"- \[\[Projects/SQR\]\] TEXT: hello <!--[0-9T:-]+-->", line)
    assert (buffer_home / "buffer.md").read_text() == line + "\n"
    assert capsys.readouterr() == ("", "")


def test_a_bad_input_raises_and_writes_nothing(buffer_home, capsys):
    with pytest.raises(ValueError, match="^text is empty$"):
        B.buffer_text("SQR", "  ")
    with pytest.raises(ValueError, match="^priority must be H, M, or L; got 'X'$"):
        B.buffer_action("SQR", "Draft it", priority="X")
    assert not (buffer_home / "buffer.md").exists()
    assert capsys.readouterr() == ("", "")


def test_add_ref_is_best_effort_and_silent(buffer_home, capsys):
    assert B.add_ref("SQR", "missing", "x") is None
    assert B.add_ref("SQR", STEM, "x", "2026-08-04").startswith(
        f"- [[Projects/SQR]] REF: [[{STEM}]] x <!--2026-08-04T")
    assert capsys.readouterr() == ("", "")


def test_tend_returns_the_regrouped_lines_and_writes_nothing(buffer_home):
    lines = ["- [[Topics/B]] TEXT: later <!--2026-09-11T09:00:00-->",
             "- [[Projects/SQR]] TEXT: sooner <!--2026-09-10T09:00:00-->",
             "- UNKNOWN: raw <!--2026-09-10T10:00:00-->"]
    new_lines, violations = B.tend(lines)
    assert new_lines[:2] == [lines[1], lines[0]]
    assert [(v[1], v[2]) for v in violations] == [
        ("thread 'Topics/B' does not resolve", lines[0]),
        ("UNKNOWN entry must be converted to TEXT, REF, or ACTION before tend can pass", lines[2])]
    assert not (buffer_home / "buffer.md").exists()


def test_validate_entry_reports_an_empty_body(vault):
    """A hand-edited buffer can hold an entry with nothing after the type.
    `tend` says so instead of flushing an empty log line."""
    vault.write_thread("Projects", "SQR")
    text = {"thread": "Projects/SQR", "type": "TEXT", "body": "",
            "ts": "2026-09-10T15:00:00", "date": "2026-09-10", "attr_tokens": []}
    assert list(B.validate_entry(text)) == ["TEXT body is empty"]
    action = {**text, "type": "ACTION"}
    assert list(B.validate_entry(action)) == ["ACTION description is empty"]
    named = {**action, "body": "(Remy Dorn)"}
    assert list(B.validate_entry(named)) == [
        "ACTION description after assignee is empty",
        "ACTION assignee 'Remy Dorn' does not resolve to people/Remy Dorn.md",
    ]
