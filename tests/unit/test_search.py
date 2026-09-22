"""Unit tests for adulting.search.

Record readers run against a small real vault under tmp_path; conftest has
already pointed ADULTING_HOME there.
"""

from datetime import date, timedelta

import pytest

from adulting import search as S


# ---------- pure helpers ----------

def test_event_date_prefers_frontmatter_then_filename():
    assert S.event_date("2026-08-27-16-30-00", "2026-08-22-09-00-00") == "2026-08-27"
    assert S.event_date('"2026-08-27"', "x") == "2026-08-27"
    assert S.event_date("bad", "2026-08-22-09-00-00") == "2026-08-22"
    assert S.event_date(None, "no-date") == ""


def test_snippet():
    body = "alpha\n\n  beta   gamma"
    assert S.snippet(body, "BETA") == "alpha beta gamma"
    assert S.snippet(body, "missing") == ""
    long = "x " * 100 + "needle " + "y " * 100
    piece = S.snippet(long, "needle", width=30)
    assert piece.startswith("…") and piece.endswith("…") and "needle" in piece


def test_minutes_between_tolerates_bad_records():
    e = {"startTime": "2026-08-26T09:00:00.000Z", "endTime": "2026-08-26T10:45:00.000Z"}
    assert S.minutes_between(e) == 105
    assert S.minutes_between({"startTime": "nope"}) == 0


def test_fmt_hours_and_window_default():
    assert S.fmt_hours(0) == "-"
    assert S.fmt_hours(90) == "1h 30m"
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    assert S.window_default(None, None) == (week_ago, None)
    assert S.window_default("2026-01-01", "2026-02-01") == ("2026-01-01", "2026-02-01")


def record(**over):
    r = {"threads": ["Processes/SGB"], "type": "Meeting", "date": "2026-08-27",
         "topic": "Agenda", "body": "roof survey", "path": "/v/a.md"}
    r.update(over)
    return r


def test_apply_filters_and_newest_first_order():
    rows = [record(), record(date="2026-08-28", path="/v/b.md", type="Report"),
            record(date="", path="/v/c.md"),
            record(threads=["Projects/Alpha"], path="/v/d.md")]
    assert [r["path"] for r in S.apply_filters(rows, thread="Processes/SGB")] == \
        ["/v/b.md", "/v/a.md", "/v/c.md"]
    assert [r["path"] for r in S.apply_filters(rows, type_="report")] == ["/v/b.md"]
    # An undated record never survives a date bound.
    assert "/v/c.md" not in [r["path"] for r in S.apply_filters(rows, since="2000-01-01")]
    assert [r["path"] for r in S.apply_filters(rows, until="2026-08-27")] == \
        ["/v/d.md", "/v/a.md"]
    assert len(S.apply_filters(rows, text="SURVEY")) == 4
    assert S.apply_filters(rows, text="agenda roof") == []



# ---------- against a real vault ----------

@pytest.fixture
def search_home():
    h = S.V.vault_home()
    for rel, text in {
        "threads/Processes/SGB.md": "---\nstatus: open\nstarted: 2026-01-05\n---\n",
        "people/Riaz Arbi.md": "---\nstatus: open\nstarted: bad\n---\n",
        "notes/2026-08-22-09-00-00.md":
            '---\ntopic: Agenda\ntype: Meeting\nthreads:\n  - "[[Processes/SGB]]"\n'
            "timestamp: 2026-08-27-16-30-00\n---\n\nTASK: Chase <!--aaaa1111 entry:2026-08-27-->\n",
        "notes/2026-08-23-09-00-00.md": "no frontmatter\n",
        "logs/Processes/SGB/2026-08-28.md":
            "---\ndate: 2026-08-28\ntype: Log\n---\n\nTEXT: one\nREF: [[hours/Processes/SGB]] x\nACTION: two\n",
        "buffer.md": "- [[Processes/SGB]] TEXT: Pending <!--2026-08-30T10:05:00-->\n"
                     "- [[Processes/SGB]] REF: [[hours/Processes/SGB]] 1h <!--2026-08-30T10:06:00-->\n"
                     "not a buffer line\n",
    }.items():
        (h / rel).parent.mkdir(parents=True, exist_ok=True)
        (h / rel).write_text(text, encoding="utf-8")
    return h


def test_note_records_skip_files_without_frontmatter(search_home):
    notes = S.note_records()
    assert [(n["date"], n["topic"], n["threads"]) for n in notes] == [
        ("2026-08-27", "Agenda", ["Processes/SGB"])]


def test_log_records_recover_the_thread_from_the_path(search_home):
    [log] = S.log_records()
    assert log["threads"] == ["Processes/SGB"]
    assert log["entries"] == 3
    assert log["date"] == "2026-08-28"


def test_stream_documents_drop_self_refs(search_home):
    events = [(e["kind"], e["summary"]) for e in S.stream_documents()]
    assert events == [("note", "Agenda"), ("log", "one"), ("task", "Chase")]


def test_stream_entities_need_a_valid_started_date(search_home):
    assert [(e["kind"], e["summary"]) for e in S.stream_entities()] == [
        ("thread", "thread opened: Processes/SGB")]


def test_stream_pending_parses_and_drops_self_refs(search_home):
    [e] = S.stream_pending()
    assert (e["kind"], e["date"], e["time"], e["summary"]) == (
        "pending", "2026-08-30", "10:05", "TEXT: Pending")
    assert e["path"] == str(search_home / "buffer.md")


def test_resolve_thread_arg(search_home):
    assert S.resolve_thread_arg(None) is None
    assert S.resolve_thread_arg("sgb") == "Processes/SGB"
    with pytest.raises(SystemExit):
        S.resolve_thread_arg("Nope")
