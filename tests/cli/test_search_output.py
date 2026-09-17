"""Characterisation of `search`'s text output and edge cases (refactor unit 3).

test_search_cli.py mostly checks --json. These pin what a person reads, plus
the thread-resolution and window behaviour. Written and run green against
the pre-port script first.
"""

from datetime import date, timedelta

import pytest

THREAD = "---\nstatus: open\nkind: {kind}\ncategory: professional\nstarted: {started}\n---\n\n# x\n"


def write(vault, rel, text):
    p = vault.home / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


@pytest.fixture
def v(vault):
    """Two notes, a log without a thread field, hours, a payment, a buffer."""
    vault.env["TZ"] = "Africa/Johannesburg"  # hours/payments render local time
    write(vault, "threads/Processes/SGB.md", THREAD.format(kind="process", started="2026-01-05"))
    write(vault, "threads/Processes/SGB Extra.md", THREAD.format(kind="process", started="2026-02-01"))
    write(vault, "threads/Projects/Alpha.md", THREAD.format(kind="project", started="2026-03-01"))
    write(vault, "people/Riaz Arbi.md",
          "---\nstatus: open\ncategory: personal\nstarted: 2026-01-02\n---\n")
    write(vault, "notes/2026-08-22-09-00-00.md",
          '---\ntopic: Agenda\ntype: Meeting\nthreads:\n  - "[[Processes/SGB]]"\n'
          '  - "[[Projects/Alpha]]"\ntimestamp: 2026-08-27-16-30-00\n---\n\n'
          + "word " * 60 + "asbestos survey needed " + "tail " * 40
          + "\nTASK: (Riaz Arbi) Chase it <!--aaaa1111 entry:2026-08-27-->\n")
    # A singular `thread:` and a malformed timestamp: the filename supplies the date.
    write(vault, "notes/2026-08-25-09-00-00.md",
          '---\ntopic: Interim report\ntype: Report\nthread: "[[Processes/SGB Extra]]"\n'
          'timestamp: bad\n---\n\nDONE: Filed <!--bbbb2222 entry:2026-08-20 end:2026-08-25-->\n')
    # No `thread:` in the log: it is recovered from logs/<Kind>/<Name>/.
    write(vault, "logs/Processes/SGB/2026-08-28.md",
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
    write(vault, "buffer.md",
          "- [[Processes/SGB]] TEXT: Pending thought <!--2026-08-30T10:05:00-->\n"
          "- [[Projects/Alpha]] REF: [[payments/Projects/Alpha]] 4500.5 ZAR received "
          "(dddd4444) <!--2026-08-29T10:15:00-->\n")
    return vault


def search(vault, *argv):
    return vault.run(*argv, cli="search")


def path(vault, rel):
    return str(vault.home / rel)


AGENDA = "notes/2026-08-22-09-00-00.md"
REPORT = "notes/2026-08-25-09-00-00.md"
LOG = "logs/Processes/SGB/2026-08-28.md"


# ---------- notes and logs ----------

def test_notes_table(v):
    r = search(v, "notes")
    assert r.returncode == 0
    assert r.stdout == (
        f"{path(v, AGENDA)}  2026-08-27  Meeting  Processes/SGB, Projects/Alpha  Agenda\n"
        f"{path(v, REPORT)}  2026-08-25  Report  Processes/SGB Extra  Interim report\n")


def test_notes_text_match_shows_a_trimmed_snippet(v):
    r = search(v, "notes", "--text", "ASBESTOS")
    assert r.stdout == (
        f"{path(v, AGENDA)}  2026-08-27  Meeting  Processes/SGB, Projects/Alpha  Agenda\n"
        "    …word word word word word word asbestos survey needed tail tail tail "
        "tail tail tail tail ta…\n")


def test_logs_table_counts_every_entry_kind(v):
    r = search(v, "logs")
    assert r.stdout == f"{path(v, LOG)}  2026-08-28  Processes/SGB  4 entries\n"


def test_logs_text_match(v):
    r = search(v, "logs", "--text", "asbestos")
    assert r.stdout.split("\n")[1] == (
        "    TEXT: Roof needs an asbestos survey. REF: [[hours/Processes/SGB]] "
        "1h 0m Spec (cccc3333) RE…")


def test_thread_resolution_folds_case(v):
    assert search(v, "notes", "--thread", "sgb").stdout == \
        f"{path(v, AGENDA)}  2026-08-27  Meeting  Processes/SGB, Projects/Alpha  Agenda\n"


def test_unresolvable_thread_fails(v):
    r = search(v, "notes", "--thread", "Nope")
    assert r.returncode == 1
    assert r.stdout == ""
    assert r.stderr == "search: thread 'Nope' does not resolve to a thread file\n"


# ---------- activity and overview ----------

def test_activity_table(v):
    r = search(v, "activity", "--since", "2026-01-01")
    assert r.stdout == (
        "THREAD               NOTES  LOGS  ENTRIES     HOURS  LAST\n"
        "Processes/SGB            1     1        4         -  2026-08-28\n"
        "Projects/Alpha           1     0        0    2h 30m  2026-08-27\n"
        "Processes/SGB Extra      1     0        0         -  2026-08-25\n"
        "\n"
        "window: 2026-01-01 to today\n")


def test_activity_defaults_to_the_last_seven_days(v):
    write(v, "notes/2020-01-01-00-00-00.md",
          f'---\ntopic: Recent\ntype: Log\nthread: "[[Projects/Alpha]]"\n'
          f"timestamp: {(date.today() - timedelta(days=7)).isoformat()}-09-00-00\n---\n")
    r = search(v, "activity")
    since = (date.today() - timedelta(days=7)).isoformat()
    assert r.stdout.endswith(f"\nwindow: {since} to today\n")
    assert "Projects/Alpha" in r.stdout
    assert "Processes/SGB " not in r.stdout


def test_overview_text(v):
    r = search(v, "overview", "SGB")
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
        f"    {path(v, LOG)}  2026-08-28  Log  4 entries\n"
        f"    {path(v, AGENDA).ljust(len(path(v, LOG)))}  2026-08-27  Meeting  Agenda\n")


def test_overview_with_a_window_and_limit(v):
    r = search(v, "overview", "Processes/SGB", "--since", "2026-08-01",
               "--until", "2026-08-31", "--limit", "1")
    lines = r.stdout.split("\n")
    assert lines[:2] == ["Processes/SGB", "window: 2026-08-01 to 2026-08-31"]
    assert lines[-3:] == ["  recent:", f"    {path(v, LOG)}  2026-08-28  Log  4 entries", ""]


def test_overview_hours_for_a_billed_thread(v):
    r = search(v, "overview", "Alpha", "--json")
    assert '"minutes": 150' in r.stdout


# ---------- stream ----------

def test_stream_text(v):
    r = search(v, "stream", "--since", "2026-01-01")
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


def test_stream_thread_filter_is_a_substring_match(v):
    """Known quirk, pinned so the port keeps it: `--thread Processes/SGB`
    also matches `Processes/SGB Extra`, because the filter tests whether
    the resolved ref appears inside the event's thread text."""
    r = search(v, "stream", "--since", "2026-01-01", "--thread", "Processes/SGB",
               "--limit", "3")
    assert r.stdout == (
        "\n2026-08-30\n"
        "  pending  Processes/SGB  TEXT: Pending thought  (10:05)\n"
        "\n2026-08-28\n"
        "  log      Processes/SGB  Roof needs an asbestos survey.\n"
        "  log      Processes/SGB  [[notes/2026-08-22-09-00-00]] Agenda\n"
        "\n10 event(s); window 2026-01-01 to today\n"
        "7 more not shown — raise --limit\n")
    rows = search(v, "stream", "--since", "2026-01-01", "--thread",
                  "Processes/SGB", "--json").stdout
    assert "Processes/SGB Extra" in rows


def test_stream_text_filter_and_reverse(v):
    r = search(v, "stream", "--since", "2026-01-01", "--text", "asbestos", "--reverse")
    assert r.stdout == (
        "\n2026-08-28\n"
        "  log  Processes/SGB  Roof needs an asbestos survey.\n"
        "\n1 event(s); window 2026-01-01 to today\n")


def test_stream_until_bounds_the_window(v):
    r = search(v, "stream", "--since", "2026-08-26", "--until", "2026-08-27",
               "--kind", "hours,note", "--json")
    import json
    assert [(e["kind"], e["date"]) for e in json.loads(r.stdout)] == [
        ("note", "2026-08-27"), ("hours", "2026-08-26")]


def test_stream_with_nothing_in_the_default_window(v):
    r = search(v, "stream")
    since = (date.today() - timedelta(days=7)).isoformat()
    assert r.stdout == f"(no events)\n\nwindow: {since} to today\n"


def test_stream_unknown_kind_message(v):
    r = search(v, "stream", "--kind", "note,bogus,nope")
    assert r.returncode == 1
    assert r.stderr == ("search: unknown kind(s) bogus, nope; choose from note, log, "
                        "task, done, hours, payment, thread, person, pending\n")


def test_empty_vault_everywhere(vault):
    for argv, out in ((["notes"], "(no matches)\n"), (["logs"], "(no matches)\n"),
                      (["activity"], "(no matches)\n")):
        r = search(vault, *argv)
        assert (r.returncode, r.stdout) == (0, out), argv
