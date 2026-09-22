"""The `search` command: notes, logs, activity, overview and stream.

Two vaults: `stocked` for the behaviours that were easy to get wrong while
building it (event date over filename, thread and type together, activity
agreeing with `hours`), and `search_vault` for the exact text a person reads.
"""

import json
import os
from datetime import date, timedelta
from pathlib import Path

import pytest

AGENDA = "notes/2026-08-22-09-00-00.md"
REPORT = "notes/2026-08-25-09-00-00.md"
LOG = "logs/Processes/SGB/2026-08-28.md"


def search(vault, *argv):
    return vault.run(*argv, cli="search")


def path(vault, rel):
    return str(vault.home / rel)


@pytest.fixture
def stocked(vault):
    """A vault with two threads, notes of mixed type, logs, and hours."""
    vault.write_thread("Processes", "SGB")
    vault.write_thread("Projects", "Alpha", currency="ZAR", rate=1000)

    # Captured on the 22nd, but the meeting happened on the 27th. The pair
    # exists so filename order and event order disagree.
    p = vault.write_note("2026-08-22-09-00-00", "Agenda body.",
                         threads=["Processes/SGB"], topic="Agenda",
                         type_="Meeting")
    p.write_text(p.read_text().replace("timestamp: 2026-08-22-09-00-00",
                                       "timestamp: 2026-08-27-16-30-00"))
    vault.write_note("2026-08-25-09-00-00", "A report body.",
                     threads=["Processes/SGB"], topic="Interim report",
                     type_="Report")
    vault.write_note("2026-08-26-09-00-00", "Other thread.",
                     threads=["Projects/Alpha"], topic="Alpha kickoff",
                     type_="Meeting")

    log = vault.home / "logs" / "Processes" / "SGB" / "2026-08-28.md"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text('---\nthread: "[[Processes/SGB]]"\ndate: 2026-08-28\n'
                   'type: Log\n---\n\n# log\n\n'
                   'TEXT: Roof needs an asbestos survey.\n'
                   'TEXT: Second entry.\n', encoding="utf-8")

    vault.write_hours_file("Projects", "Alpha", entries=[{
        "name": "Spec work", "id": "aaaa1111", "rate": 1000, "currency": "ZAR",
        "startTime": "2026-08-26T09:00:00.000Z",
        "endTime": "2026-08-26T11:00:00.000Z"}])
    return vault


@pytest.fixture
def search_vault(vault):
    """Two notes, a log without a thread field, hours, a payment, a buffer."""
    vault.env["TZ"] = "Africa/Johannesburg"  # hours/payments render local time
    vault.write_thread("Processes", "SGB", started="2026-01-05")
    vault.write_thread("Processes", "SGB Extra", started="2026-02-01")
    vault.write_thread("Projects", "Alpha", started="2026-03-01")
    vault.write("people/Riaz Arbi.md",
          "---\nstatus: open\ncategory: personal\nstarted: 2026-01-02\n---\n")
    vault.write("notes/2026-08-22-09-00-00.md",
          '---\ntopic: Agenda\ntype: Meeting\nthreads:\n  - "[[Processes/SGB]]"\n'
          '  - "[[Projects/Alpha]]"\ntimestamp: 2026-08-27-16-30-00\n---\n\n'
          + "word " * 60 + "asbestos survey needed " + "tail " * 40
          + "\nTASK: (Riaz Arbi) Chase it <!--aaaa1111 entry:2026-08-27-->\n")
    # A singular `thread:` and a malformed timestamp: the filename supplies the date.
    vault.write("notes/2026-08-25-09-00-00.md",
          '---\ntopic: Interim report\ntype: Report\nthread: "[[Processes/SGB Extra]]"\n'
          'timestamp: bad\n---\n\nDONE: Filed <!--bbbb2222 entry:2026-08-20 end:2026-08-25-->\n')
    # No `thread:` in the log: it is recovered from logs/<Kind>/<Name>/.
    vault.write("logs/Processes/SGB/2026-08-28.md",
          "---\ndate: 2026-08-28\ntype: Log\n---\n\n"
          "TEXT: Roof needs an asbestos survey.\n"
          "REF: [[hours/Processes/SGB]] 1h 0m Spec (cccc3333)\n"
          "REF: [[notes/2026-08-22-09-00-00]] Agenda\n"
          "ACTION: Ring the council\n")
    vault.write_hours_file("Projects", "Alpha", entries=[{
        "name": "Spec work", "id": "aaaa1111", "rate": 1000, "currency": "ZAR",
        "startTime": "2026-08-26T09:00:00.000Z", "endTime": "2026-08-26T11:30:00.000Z"}])
    vault.write_payments_file("Projects", "Alpha", payments=[{
        "id": "dddd4444", "received": "2026-08-29T08:15:00.000Z",
        "amount": 4500.5, "currency": "ZAR"}])
    vault.write("buffer.md",
          "- [[Processes/SGB]] TEXT: Pending thought <!--2026-08-30T10:05:00-->\n"
          "- [[Projects/Alpha]] REF: [[payments/Projects/Alpha]] 4500.5 ZAR received "
          "(dddd4444) <!--2026-08-29T10:15:00-->\n")
    return vault


def _log_with(vault, kind, name, day, body):
    p = vault.home / "logs" / kind / name / f"{day}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f'---\nthread: "[[{kind}/{name}]]"\ndate: {day}\n'
                 f'type: Log\n---\n\n# log\n\n{body}\n', encoding="utf-8")
    return p


# ---------- notes and logs ----------

def test_notes_table(search_vault):
    r = search(search_vault, "notes")
    assert r.returncode == 0
    assert r.stdout == (
        f"{path(search_vault, AGENDA)}  2026-08-27  Meeting  Processes/SGB, Projects/Alpha  Agenda\n"
        f"{path(search_vault, REPORT)}  2026-08-25  Report  Processes/SGB Extra  Interim report\n")


def test_notes_text_match_shows_a_trimmed_snippet(search_vault):
    r = search(search_vault, "notes", "--text", "ASBESTOS")
    assert r.stdout == (
        f"{path(search_vault, AGENDA)}  2026-08-27  Meeting  Processes/SGB, Projects/Alpha  Agenda\n"
        "    …word word word word word word asbestos survey needed tail tail tail "
        "tail tail tail tail ta…\n")


def test_logs_table_counts_every_entry_kind(search_vault):
    r = search(search_vault, "logs")
    assert r.stdout == f"{path(search_vault, LOG)}  2026-08-28  Processes/SGB  4 entries\n"


def test_logs_text_match(search_vault):
    r = search(search_vault, "logs", "--text", "asbestos")
    assert r.stdout.split("\n")[1] == (
        "    TEXT: Roof needs an asbestos survey. REF: [[hours/Processes/SGB]] "
        "1h 0m Spec (cccc3333) RE…")


def test_thread_resolution_folds_case(search_vault):
    assert search(search_vault, "notes", "--thread", "sgb").stdout == \
        f"{path(search_vault, AGENDA)}  2026-08-27  Meeting  Processes/SGB, Projects/Alpha  Agenda\n"


def test_unresolvable_thread_fails(search_vault):
    r = search(search_vault, "notes", "--thread", "Nope")
    assert r.returncode == 1
    assert r.stdout == ""
    assert r.stderr == "search: error: thread 'Nope' does not resolve to a thread file\n"


def test_thread_and_type_filter_together(stocked):
    r = search(stocked, "notes", "--thread", "Processes/SGB", "--type", "Meeting")
    assert "2026-08-22-09-00-00" in r.stdout
    assert "Interim report" not in r.stdout
    assert "Alpha kickoff" not in r.stdout


def test_thread_accepts_bare_name(stocked):
    """`SGB` must resolve without a `threads list` round-trip first."""
    bare = search(stocked, "notes", "--thread", "SGB")
    full = search(stocked, "notes", "--thread", "Processes/SGB")
    assert bare.returncode == 0
    assert bare.stdout == full.stdout


def test_type_is_case_insensitive(stocked):
    assert search(stocked, "notes", "--type", "meeting").stdout == \
           search(stocked, "notes", "--type", "Meeting").stdout


def test_text_miss_reports_no_matches(stocked):
    r = search(stocked, "logs", "--text", "nothingmatchesthis")
    assert r.returncode == 0
    assert "no matches" in r.stdout


def test_limit_caps_results(stocked):
    r = search(stocked, "notes", "--limit", "1", "--json")
    assert len(json.loads(r.stdout)) == 1


def test_date_range_filters(stocked):
    r = search(stocked, "notes", "--since", "2026-08-27", "--json")
    dates = [x["date"] for x in json.loads(r.stdout)]
    assert dates and all(d >= "2026-08-27" for d in dates)


def test_unparseable_file_is_skipped_not_fatal(stocked):
    (stocked.home / "notes" / "2026-08-29-09-00-00.md").write_text(
        "no frontmatter at all\n", encoding="utf-8")
    r = search(stocked, "notes")
    assert r.returncode == 0
    assert "2026-08-29" not in r.stdout


def test_empty_vault_everywhere(vault):
    for argv, out in ((["notes"], "(no matches)\n"), (["logs"], "(no matches)\n"),
                      (["activity"], "(no matches)\n")):
        r = search(vault, *argv)
        assert (r.returncode, r.stdout) == (0, out), argv


# ---------- activity and overview ----------

def test_activity_table(search_vault):
    r = search(search_vault, "activity", "--since", "2026-01-01")
    assert r.stdout == (
        "THREAD               NOTES  LOGS  ENTRIES     HOURS  LAST\n"
        "Processes/SGB            1     1        4         -  2026-08-28\n"
        "Projects/Alpha           1     0        0    2h 30m  2026-08-27\n"
        "Processes/SGB Extra      1     0        0         -  2026-08-25\n"
        "\n"
        "window: 2026-01-01 to today\n")


def test_activity_defaults_to_the_last_seven_days(search_vault):
    search_vault.write("notes/2020-01-01-00-00-00.md",
          f'---\ntopic: Recent\ntype: Log\nthread: "[[Projects/Alpha]]"\n'
          f"timestamp: {(date.today() - timedelta(days=7)).isoformat()}-09-00-00\n---\n")
    r = search(search_vault, "activity")
    since = (date.today() - timedelta(days=7)).isoformat()
    assert r.stdout.endswith(f"\nwindow: {since} to today\n")
    assert "Projects/Alpha" in r.stdout
    assert "Processes/SGB " not in r.stdout


def test_activity_counts_and_ranks(stocked):
    r = search(stocked, "activity", "--since", "2026-01-01", "--json")
    rows = {x["thread"]: x for x in json.loads(r.stdout)}
    assert rows["Processes/SGB"]["notes"] == 2
    assert rows["Processes/SGB"]["logs"] == 1
    assert rows["Processes/SGB"]["entries"] == 2
    assert rows["Projects/Alpha"]["minutes"] == 120


def test_activity_surfaces_threads_with_only_hours(vault):
    """A thread with time logged but no notes or logs is still activity."""
    vault.write_thread("Projects", "Quiet", currency="ZAR", rate=1000)
    vault.write_hours_file("Projects", "Quiet", entries=[{
        "name": "Work", "id": "bbbb2222", "rate": 1000, "currency": "ZAR",
        "startTime": "2026-08-26T09:00:00.000Z",
        "endTime": "2026-08-26T10:00:00.000Z"}])
    r = search(vault, "activity", "--since", "2026-01-01", "--json")
    rows = {x["thread"]: x for x in json.loads(r.stdout)}
    assert rows["Projects/Quiet"]["minutes"] == 60
    assert rows["Projects/Quiet"]["notes"] == 0


def test_overview_text(search_vault):
    r = search(search_vault, "overview", "SGB")
    assert r.stdout == (
        "Processes/SGB\n"
        "\n"
        "  notes         1   (Meeting 1)\n"
        "  logs          1   4 entries\n"
        "  tasks         1 open, 0 done\n"
        "  hours         -\n"
        "  last       2026-08-28\n"
        "\n"
        "  recent:\n"
        f"    {path(search_vault, LOG)}  2026-08-28  Log  4 entries\n"
        f"    {path(search_vault, AGENDA).ljust(len(path(search_vault, LOG)))}  2026-08-27  Meeting  Agenda\n")


def test_overview_with_a_window_and_limit(search_vault):
    r = search(search_vault, "overview", "Processes/SGB", "--since", "2026-08-01",
               "--until", "2026-08-31", "--limit", "1")
    lines = r.stdout.split("\n")
    assert lines[:2] == ["Processes/SGB", "window: 2026-08-01 to 2026-08-31"]
    assert lines[-3:] == ["  recent:", f"    {path(search_vault, LOG)}  2026-08-28  Log  4 entries", ""]


def test_overview_hours_for_a_billed_thread(search_vault):
    r = search(search_vault, "overview", "Alpha", "--json")
    assert json.loads(r.stdout) == {
        "thread": "Projects/Alpha", "notes": 1, "notes_by_type": {"Meeting": 1},
        "logs": 0, "entries": 0, "tasks_open": 1, "tasks_done": 0, "minutes": 150,
        "last": "2026-08-27",
        "recent": [{"path": path(search_vault, AGENDA), "date": "2026-08-27",
                    "type": "Meeting", "topic": "Agenda"}]}


def test_overview_rolls_up_one_thread(stocked):
    r = search(stocked, "overview", "SGB", "--json")
    d = json.loads(r.stdout)
    assert d["thread"] == "Processes/SGB"
    assert d["notes"] == 2
    assert d["logs"] == 1
    assert d["notes_by_type"] == {"Meeting": 1, "Report": 1}
    assert d["recent"]


# ---------- stream: one chronology, ordered by when things happened ----------

def test_stream_text(search_vault):
    r = search(search_vault, "stream", "--since", "2026-01-01")
    assert r.stdout == (
        "\n2026-08-30\n"
        "  pending  Processes/SGB                  TEXT: Pending thought  (10:05)\n"
        "\n2026-08-29\n"
        "  payment  Projects/Alpha                 4500.5 ZAR received  (10:15)\n"
        "\n2026-08-28\n"
        "  log      Processes/SGB                  Roof needs an asbestos survey.\n"
        "  log      Processes/SGB                  [[notes/2026-08-22-09-00-00]] Agenda\n"
        "\n2026-08-27\n"
        "  task     Processes/SGB, Projects/Alpha  (Riaz Arbi) Chase it\n"
        "  note     Processes/SGB, Projects/Alpha  Agenda\n"
        "\n2026-08-26\n"
        "  hours    Projects/Alpha                 2h 30m Spec work  (11:00)\n"
        "\n2026-08-25\n"
        "  note     Processes/SGB Extra            Interim report\n"
        "  done     Processes/SGB Extra            Filed\n"
        "\n2026-08-20\n"
        "  task     Processes/SGB Extra            Filed\n"
        "\n2026-03-01\n"
        "  thread   Projects/Alpha                 thread opened: Projects/Alpha\n"
        "\n2026-02-01\n"
        "  thread   Processes/SGB Extra            thread opened: Processes/SGB Extra\n"
        "\n2026-01-05\n"
        "  thread   Processes/SGB                  thread opened: Processes/SGB\n"
        "\n2026-01-02\n"
        "  person   -                              person added: Riaz Arbi\n"
        "\n14 event(s); window 2026-01-01 to today\n")


def test_stream_thread_filter_matches_whole_thread_names(search_vault):
    """`--thread Processes/SGB` must not pick up `Processes/SGB Extra`.
    It used to: the filter tested whether the ref appeared inside the
    event's thread text. A multi-thread event still matches each thread."""
    r = search(search_vault, "stream", "--since", "2026-01-01", "--thread", "Processes/SGB",
               "--limit", "3")
    assert r.stdout == (
        "\n2026-08-30\n"
        "  pending  Processes/SGB  TEXT: Pending thought  (10:05)\n"
        "\n2026-08-28\n"
        "  log      Processes/SGB  Roof needs an asbestos survey.\n"
        "  log      Processes/SGB  [[notes/2026-08-22-09-00-00]] Agenda\n"
        "\n6 event(s); window 2026-01-01 to today\n"
        "3 more not shown — raise --limit\n")
    rows = json.loads(search(search_vault, "stream", "--since", "2026-01-01", "--thread",
                             "Processes/SGB", "--json").stdout)
    assert {e["thread"] for e in rows} == {"Processes/SGB", "Processes/SGB, Projects/Alpha"}
    extra = json.loads(search(search_vault, "stream", "--since", "2026-01-01", "--thread",
                              "SGB Extra", "--json").stdout)
    assert {e["thread"] for e in extra} == {"Processes/SGB Extra"}


def test_stream_text_filter_and_reverse(search_vault):
    r = search(search_vault, "stream", "--since", "2026-01-01", "--text", "asbestos", "--reverse")
    assert r.stdout == (
        "\n2026-08-28\n"
        "  log  Processes/SGB  Roof needs an asbestos survey.\n"
        "\n1 event(s); window 2026-01-01 to today\n")


def test_stream_until_bounds_the_window(search_vault):
    r = search(search_vault, "stream", "--since", "2026-08-26", "--until", "2026-08-27",
               "--kind", "hours,note", "--json")
    assert [(e["kind"], e["date"]) for e in json.loads(r.stdout)] == [
        ("note", "2026-08-27"), ("hours", "2026-08-26")]


def test_stream_with_nothing_in_the_default_window(search_vault):
    r = search(search_vault, "stream")
    since = (date.today() - timedelta(days=7)).isoformat()
    assert r.stdout == f"(no events)\n\nwindow: {since} to today\n"


def test_stream_unknown_kind_message(search_vault):
    r = search(search_vault, "stream", "--kind", "note,bogus,nope")
    assert r.returncode == 1
    assert r.stderr == ("search: error: unknown kind(s) bogus, nope; choose from note, log, "
                        "task, done, hours, payment, thread, person, pending\n")


def test_one_anchor_yields_two_events_on_different_days(stocked):
    """A DONE anchor is created on one day and finished on another. Both are
    events, and the completion belongs on the day it happened — not the day
    the file is filed under."""
    _log_with(stocked, "Processes", "SGB", "2026-06-02",
              "DONE: Sew the button <!--e845abea entry:2026-06-02 end:2026-09-10-->")
    rows = json.loads(search(stocked, "stream", "--since", "2026-01-01",
                         "--kind", "task,done", "--json").stdout)
    by_kind = {r["kind"]: r["date"] for r in rows}
    assert by_kind == {"task": "2026-06-02", "done": "2026-09-10"}, rows


def test_hours_appear_once_before_and_after_flush(stocked):
    """hours log writes a REF back into the log. The record is already a
    stream event from its own file, so the REF must not double it —
    pending or flushed."""
    stocked.run("log", "Projects/Alpha", "Unmistakable marker", "-m", "60",
                "-d", "2026-08-26", cli="hours")

    def marked(rows):
        return [r for r in rows if "Unmistakable marker" in r["summary"]]

    before = marked(json.loads(search(stocked, "stream", "--since", "2026-01-01",
                                  "--kind", "hours,pending,log", "--json").stdout))
    stocked.run("flush", cli="buffer")
    after = marked(json.loads(search(stocked, "stream", "--since", "2026-01-01",
                                 "--kind", "hours,pending,log", "--json").stdout))
    assert len(before) == 1, before
    assert len(after) == 1, after
    assert after[0]["kind"] == "hours"


def test_unflushed_buffer_entries_show_as_pending(stocked):
    stocked.run("add-text", "Processes/SGB", "Something worth keeping",
                cli="buffer")
    rows = json.loads(search(stocked, "stream", "--since", "2026-01-01",
                         "--kind", "pending", "--json").stdout)
    assert rows and rows[0]["kind"] == "pending"
    assert "Something worth keeping" in rows[0]["summary"]


def test_today_shorthand_bounds_both_ends(stocked):
    today = date.today().isoformat()
    stocked.run("log", "Projects/Alpha", "Now", "-m", "30", cli="hours")
    rows = json.loads(search(stocked, "stream", "--today", "--json").stdout)
    assert rows, "expected today's entry"
    assert all(r["date"] == today for r in rows), rows


def test_events_carry_a_time_only_when_the_record_does(stocked):
    stocked.run("log", "Projects/Alpha", "Timed", "-m", "30", cli="hours")
    rows = json.loads(search(stocked, "stream", "--since", "2026-01-01", "--json").stdout)
    hours = [r for r in rows if r["kind"] == "hours"]
    notes = [r for r in rows if r["kind"] == "log"]
    assert hours and hours[0]["time"], "an hours entry knows its clock time"
    assert all(not r["time"] for r in notes), "a log line is date-only"


def test_reverse_flips_the_order(stocked):
    _log_with(stocked, "Processes", "SGB", "2026-06-02",
              "TEXT: older thing")
    _log_with(stocked, "Processes", "SGB", "2026-08-30",
              "TEXT: newer thing")
    fwd = json.loads(search(stocked, "stream", "--since", "2026-01-01",
                        "--kind", "log", "--json").stdout)
    rev = json.loads(search(stocked, "stream", "--since", "2026-01-01",
                        "--kind", "log", "--reverse", "--json").stdout)
    assert fwd[0]["date"] > fwd[-1]["date"]
    assert rev[0]["date"] < rev[-1]["date"]


# ---------- the path contract ----------

#
# search exists to hand a path to a reader, and a reader resolves a relative
# path against its own working directory. In the agent's container the vault
# is bind-mounted at /vault while the process runs in /workspace, so a
# vault-relative path silently resolves to nothing. Emitting relative paths
# once cost ~57 tool calls and a wrong answer; these pin the contract.


def test_paths_are_absolute(stocked):
    for argv in (["notes"], ["logs"]):
        rows = json.loads(search(stocked, *argv, "--json").stdout)
        assert rows, argv
        for r in rows:
            assert r["path"].startswith("/"), f"{argv}: {r['path']} is not absolute"


def test_paths_resolve_from_an_unrelated_working_directory(stocked, tmp_path):
    """The real failure: a path that only works if you happen to be standing
    in the vault is not a usable path."""
    elsewhere = tmp_path / "workspace"
    elsewhere.mkdir()
    rows = json.loads(search(stocked, "notes", "--json").stdout)
    cwd = os.getcwd()
    try:
        os.chdir(elsewhere)
        for r in rows:
            assert Path(r["path"]).is_file(), \
                f"{r['path']} does not resolve from {elsewhere}"
    finally:
        os.chdir(cwd)


def test_overview_recent_paths_are_absolute_too(stocked):
    d = json.loads(search(stocked, "overview", "SGB", "--json").stdout)
    assert d["recent"]
    for r in d["recent"]:
        assert r["path"].startswith("/"), r["path"]


# ---------- no prompts ----------

def test_never_prompts_without_a_tty(stocked):
    """Every subcommand must complete with stdin closed. `search` must not
    repeat the `hours log` pattern of going interactive when an argument is
    missing."""
    for argv in (["notes"], ["logs"], ["activity"], ["overview", "SGB"]):
        r = stocked.run(*argv, cli="search", input="")
        assert r.returncode == 0, f"{argv} -> {r.stderr}"
