"""Tests for the `search` CLI.

The behaviours worth pinning are the ones that were easy to get wrong while
building it: ordering by the event date rather than the filename, filtering
by thread and type together, text search reaching log bodies, and the
activity rollup agreeing with `hours` on duration.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


def sh(vault, *argv):
    return vault.run(*argv, cli="search")


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


def test_orders_by_event_date_not_filename(stocked):
    """The agenda is captured on the 22nd but happens on the 27th, so it
    must sort ahead of the report captured on the 25th."""
    r = sh(stocked, "notes", "--thread", "Processes/SGB")
    assert r.returncode == 0
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    assert "2026-08-22-09-00-00" in lines[0], r.stdout
    assert "2026-08-27" in lines[0]


def test_thread_and_type_filter_together(stocked):
    r = sh(stocked, "notes", "--thread", "Processes/SGB", "--type", "Meeting")
    assert "2026-08-22-09-00-00" in r.stdout
    assert "Interim report" not in r.stdout
    assert "Alpha kickoff" not in r.stdout


def test_thread_accepts_bare_name(stocked):
    """`SGB` must resolve without a `threads list` round-trip first."""
    bare = sh(stocked, "notes", "--thread", "SGB")
    full = sh(stocked, "notes", "--thread", "Processes/SGB")
    assert bare.returncode == 0
    assert bare.stdout == full.stdout


def test_type_is_case_insensitive(stocked):
    assert sh(stocked, "notes", "--type", "meeting").stdout == \
           sh(stocked, "notes", "--type", "Meeting").stdout


def test_text_searches_log_bodies(stocked):
    r = sh(stocked, "logs", "--text", "asbestos")
    assert r.returncode == 0
    assert "2026-08-28.md" in r.stdout
    assert "asbestos" in r.stdout.lower()  # the snippet


def test_text_miss_reports_no_matches(stocked):
    r = sh(stocked, "logs", "--text", "nothingmatchesthis")
    assert r.returncode == 0
    assert "no matches" in r.stdout


def test_limit_caps_results(stocked):
    r = sh(stocked, "notes", "--limit", "1", "--json")
    assert len(json.loads(r.stdout)) == 1


def test_date_range_filters(stocked):
    r = sh(stocked, "notes", "--since", "2026-08-27", "--json")
    dates = [x["date"] for x in json.loads(r.stdout)]
    assert dates and all(d >= "2026-08-27" for d in dates)


def test_activity_counts_and_ranks(stocked):
    r = sh(stocked, "activity", "--since", "2026-01-01", "--json")
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
    r = sh(vault, "activity", "--since", "2026-01-01", "--json")
    rows = {x["thread"]: x for x in json.loads(r.stdout)}
    assert rows["Projects/Quiet"]["minutes"] == 60
    assert rows["Projects/Quiet"]["notes"] == 0


def test_overview_rolls_up_one_thread(stocked):
    r = sh(stocked, "overview", "SGB", "--json")
    d = json.loads(r.stdout)
    assert d["thread"] == "Processes/SGB"
    assert d["notes"] == 2
    assert d["logs"] == 1
    assert d["notes_by_type"] == {"Meeting": 1, "Report": 1}
    assert d["recent"]


def test_never_prompts_without_a_tty(stocked):
    """Every subcommand must complete with stdin closed. `search` must not
    repeat the `hours log` pattern of going interactive when an argument is
    missing."""
    for argv in (["notes"], ["logs"], ["activity"], ["overview", "SGB"]):
        r = stocked.run(*argv, cli="search", input="")
        assert r.returncode == 0, f"{argv} -> {r.stderr}"


def test_unparseable_file_is_skipped_not_fatal(stocked):
    (stocked.home / "notes" / "2026-08-29-09-00-00.md").write_text(
        "no frontmatter at all\n", encoding="utf-8")
    r = sh(stocked, "notes")
    assert r.returncode == 0
    assert "2026-08-29" not in r.stdout


# ---- the path contract ----
#
# search exists to hand a path to a reader, and a reader resolves a relative
# path against its own working directory. In the agent's container the vault
# is bind-mounted at /vault while the process runs in /workspace, so a
# vault-relative path silently resolves to nothing. Emitting relative paths
# once cost ~57 tool calls and a wrong answer; these pin the contract.

def test_paths_are_absolute(stocked):
    for argv in (["notes"], ["logs"]):
        rows = json.loads(sh(stocked, *argv, "--json").stdout)
        assert rows, argv
        for r in rows:
            assert r["path"].startswith("/"), f"{argv}: {r['path']} is not absolute"


def test_paths_resolve_from_an_unrelated_working_directory(stocked, tmp_path):
    """The real failure: a path that only works if you happen to be standing
    in the vault is not a usable path."""
    elsewhere = tmp_path / "workspace"
    elsewhere.mkdir()
    rows = json.loads(sh(stocked, "notes", "--json").stdout)
    cwd = os.getcwd()
    try:
        os.chdir(elsewhere)
        for r in rows:
            assert Path(r["path"]).is_file(), \
                f"{r['path']} does not resolve from {elsewhere}"
    finally:
        os.chdir(cwd)


def test_overview_recent_paths_are_absolute_too(stocked):
    d = json.loads(sh(stocked, "overview", "SGB", "--json").stdout)
    assert d["recent"]
    for r in d["recent"]:
        assert r["path"].startswith("/"), r["path"]
