"""The `stats` command: declare a stat on a thread, log values through the
buffer, and read them back as a series."""

import json
import re
from datetime import date, timedelta

import pytest


TS = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"


@pytest.fixture
def stats_vault(vault):
    vault.write_thread("Processes", "Wellness")
    vault.write_thread("Processes", "Money")
    for argv in (["pushups", "--thread", "Wellness", "--type", "int", "--agg", "sum"],
                 ["steps", "--thread", "Processes/Wellness", "--type", "int", "--agg", "last"],
                 ["pullups", "--thread", "Wellness", "--type", "int", "--agg", "max"],
                 ["spend-zar", "--thread", "[[Processes/Money]]", "--type", "decimal", "--agg", "sum"]):
        r = vault.run("new", *argv, cli="stats")
        assert r.returncode == 0, r.stderr
    return vault


def log(vault, *argv):
    r = vault.run("log", *argv, cli="stats")
    assert (r.returncode, r.stderr) == (0, ""), r.stderr
    return r.stdout


def series(vault, *argv):
    r = vault.run("series", *argv, "--json", cli="stats")
    assert (r.returncode, r.stderr) == (0, ""), r.stderr
    return [(p["period"], p["value"]) for p in json.loads(r.stdout)["periods"]]


# ---------- new ----------

def test_new_writes_a_block_list_into_the_thread_frontmatter(stats_vault):
    assert stats_vault.read("threads/Processes/Wellness.md") == (
        "---\nstatus: open\nkind: process\ncategory: professional\nstarted: 2026-01-01\n"
        "stats:\n"
        "  - name: pushups\n    type: int\n    agg: sum\n"
        "  - name: steps\n    type: int\n    agg: last\n"
        "  - name: pullups\n    type: int\n    agg: max\n"
        "---\n\n# Wellness\n")


def test_new_reports_what_it_declared(vault):
    vault.write_thread("Processes", "Wellness")
    r = vault.run("new", "alcohol", "--thread", "Wellness", "--type", "int", "--agg", "sum", cli="stats")
    assert (r.returncode, r.stdout, r.stderr) == (0, "declared: alcohol on Processes/Wellness (int, sum)\n", "")


def test_new_appends_to_a_stats_list_that_has_other_keys_after_it(vault):
    vault.write("threads/Processes/Wellness.md",
                "---\nstatus: open\nkind: process\ncategory: personal\nstarted: 2026-01-01\n"
                "stats:\n  - name: steps\n    type: int\n    agg: last\ncurrency: ZAR\n---\n\n# Wellness\n")
    r = vault.run("new", "pushups", "--thread", "Wellness", "--type", "int", "--agg", "sum", cli="stats")
    assert r.returncode == 0, r.stderr
    assert vault.read("threads/Processes/Wellness.md") == (
        "---\nstatus: open\nkind: process\ncategory: personal\nstarted: 2026-01-01\n"
        "stats:\n  - name: steps\n    type: int\n    agg: last\n"
        "  - name: pushups\n    type: int\n    agg: sum\ncurrency: ZAR\n---\n\n# Wellness\n")
    assert vault.run(cli="lint").returncode == 0


@pytest.mark.parametrize("argv, message", [
    (["pushups", "--thread", "Money", "--type", "int", "--agg", "sum"],
     "stat 'pushups' is already declared on Processes/Wellness"),
    (["Push-Ups", "--thread", "Money", "--type", "int", "--agg", "sum"],
     "name 'Push-Ups' must be lowercase letters, digits and '-' (e.g. run-km)"),
    (["run km", "--thread", "Money", "--type", "int", "--agg", "sum"],
     "name 'run km' must be lowercase letters, digits and '-' (e.g. run-km)"),
    (["situps", "--thread", "Nowhere", "--type", "int", "--agg", "sum"],
     "thread 'Nowhere' does not resolve to a thread file"),
])
def test_new_refuses(stats_vault, argv, message):
    before = stats_vault.snapshot()
    r = stats_vault.run("new", *argv, cli="stats")
    assert (r.returncode, r.stdout, r.stderr) == (1, "", f"stats: error: {message}\n")
    assert stats_vault.snapshot() == before


def test_new_refuses_a_type_or_agg_it_does_not_know(stats_vault):
    for flag, value in (("--type", "bool"), ("--agg", "avg")):
        argv = {"--type": "int", "--agg": "sum", flag: value}
        r = stats_vault.run("new", "situps", "--thread", "Money", *[x for kv in argv.items() for x in kv],
                            cli="stats")
        assert r.returncode == 2
        assert f"invalid choice: '{value}'" in r.stderr


def test_new_refuses_a_thread_file_without_frontmatter(vault):
    path = vault.write("threads/Processes/Wellness.md", "# Wellness\n")
    r = vault.run("new", "pushups", "--thread", "Wellness", "--type", "int", "--agg", "sum", cli="stats")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == f"stats: error: cannot declare a stat in {path.resolve()}: thread file has no frontmatter\n"
    assert vault.read("threads/Processes/Wellness.md") == "# Wellness\n"


def test_new_refuses_a_stats_list_it_cannot_read(vault):
    """A flush-left item is valid YAML, but the reader drops it. Writing the
    new stat beside it used to lose the old one without a word."""
    text = ("---\nstatus: open\nkind: process\ncategory: personal\nstarted: 2026-01-01\n"
            "stats:\n- name: steps\n  type: int\n  agg: last\n---\n")
    path = vault.write("threads/Processes/Wellness.md", text)
    r = vault.run("new", "pushups", "--thread", "Wellness", "--type", "int", "--agg", "sum", cli="stats")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == (f"stats: error: cannot declare a stat in {path.resolve()}: frontmatter line 7 is not "
                        f"read ('- name: steps'); indent it under its key first (`lint` reports it)\n")
    assert vault.read("threads/Processes/Wellness.md") == text


def test_new_refuses_a_one_line_stats_value(vault):
    path = vault.write("threads/Processes/Wellness.md",
                       "---\nstatus: open\nkind: process\ncategory: personal\nstarted: 2026-01-01\n"
                       "stats: []\n---\n")
    r = vault.run("new", "pushups", "--thread", "Wellness", "--type", "int", "--agg", "sum", cli="stats")
    assert r.returncode == 1
    assert r.stderr == (f"stats: error: cannot declare a stat in {path.resolve()}: "
                        f"its `stats:` is not a block list; edit it by hand\n")


# ---------- list ----------

def test_list_shows_every_declared_stat_by_name(stats_vault):
    r = stats_vault.run("list", cli="stats")
    assert r.stdout == (
        "NAME       THREAD              TYPE     AGG\n"
        "pullups    Processes/Wellness  int      max\n"
        "pushups    Processes/Wellness  int      sum\n"
        "spend-zar  Processes/Money     decimal  sum\n"
        "steps      Processes/Wellness  int      last\n")
    rows = json.loads(stats_vault.run("list", "--json", cli="stats").stdout)
    assert rows[0] == {"name": "pullups", "thread": "Processes/Wellness", "type": "int", "agg": "max"}


def test_list_with_nothing_declared(vault):
    assert vault.run("list", cli="stats").stdout == "(no stats)\n"


# ---------- log ----------

def test_log_buffers_a_stat_line_on_the_stat_thread(stats_vault):
    out = log(stats_vault, "pushups", "25")
    assert re.fullmatch(rf"buffered: - \[\[Processes/Wellness\]\] STAT: pushups 25 <!--{TS}-->\n", out)
    assert stats_vault.read("buffer.md") == out[len("buffered: "):]


def test_log_date_and_time_set_the_timestamp(stats_vault):
    assert "<!--2026-10-05T07:30:00-->" in log(stats_vault, "pushups", "20", "-d", "2026-10-05", "-t", "07:30")
    assert re.search(r"<!--2026-10-04T\d{2}:\d{2}:\d{2}-->", log(stats_vault, "pushups", "20", "-d", "2026-10-04"))
    # Either side of midnight, the day is the one the command ran on.
    days = {date.today().isoformat()}
    out = log(stats_vault, "pushups", "20", "--time", "09:15")
    days.add(date.today().isoformat())
    assert any(f"<!--{d}T09:15:00-->" in out for d in days)


def test_log_accepts_zero_and_negative_values(stats_vault):
    assert "STAT: pushups 0 " in log(stats_vault, "pushups", "0")
    assert "STAT: spend-zar -12.50 " in log(stats_vault, "spend-zar", "-12.50")


@pytest.mark.parametrize("argv, message", [
    (["pushups", "2.5"], "value '2.5' for 'pushups' must be a whole number"),
    (["pushups", "lots"], "value 'lots' for 'pushups' must be a whole number"),
    (["spend-zar", "1e3"], "value '1e3' for 'spend-zar' must be a number"),
    (["pushup", "3"], "stat 'pushup' is not declared (see `stats list`); did you mean pushups, pullups?"),
    (["situps", "3"], "stat 'situps' is not declared (see `stats list`); did you mean steps, pushups?"),
    (["zzz", "3"], "stat 'zzz' is not declared (see `stats list`)"),
])
def test_log_refuses_and_buffers_nothing(stats_vault, argv, message):
    r = stats_vault.run("log", *argv, cli="stats")
    assert (r.returncode, r.stdout, r.stderr) == (1, "", f"stats: error: {message}\n")
    assert not (stats_vault.home / "buffer.md").exists()


def test_log_refuses_a_name_declared_twice(stats_vault):
    stats_vault.write("threads/Processes/Money.md",
                      stats_vault.read("threads/Processes/Money.md").replace(
                          "stats:\n", "stats:\n  - name: steps\n    type: int\n    agg: sum\n"))
    r = stats_vault.run("log", "steps", "5", cli="stats")
    assert r.returncode == 1
    assert r.stderr == ("stats: error: stat 'steps' is declared on more than one thread "
                        "(Processes/Money, Processes/Wellness); `lint` reports it, and one must be renamed\n")


def test_log_names_a_stat_declared_twice_on_one_thread(stats_vault):
    path = stats_vault.home / "threads/Processes/Wellness.md"
    path.write_text(path.read_text().replace("stats:\n", "stats:\n  - name: steps\n    type: int\n    agg: sum\n"))
    r = stats_vault.run("log", "steps", "5", cli="stats")
    assert r.stderr == ("stats: error: stat 'steps' is declared twice on Processes/Wellness; "
                        "`lint` reports it, and one must be removed\n")
    r = stats_vault.run("new", "steps", "--thread", "Money", "--type", "int", "--agg", "sum", cli="stats")
    assert r.stderr == "stats: error: stat 'steps' is already declared on Processes/Wellness\n"


def test_a_mistake_is_removed_with_buffer_rm_before_flush(stats_vault):
    log(stats_vault, "pushups", "250", "-d", "2026-10-05", "-t", "07:00")
    log(stats_vault, "pushups", "25", "-d", "2026-10-05", "-t", "07:01")
    r = stats_vault.run("rm", "1", cli="buffer")
    assert (r.returncode, r.stdout) == (
        0, "removed line 1: - [[Processes/Wellness]] STAT: pushups 250 <!--2026-10-05T07:00:00-->\n")
    assert series(stats_vault, "pushups", "--since", "2026-10-05", "--until", "2026-10-05") == [("2026-10-05", 25)]


def test_log_bad_date_or_time(stats_vault):
    r = stats_vault.run("log", "pushups", "1", "-d", "2026-13-01", cli="stats")
    assert (r.returncode, r.stderr) == (1, "stats: error: bad --date '2026-13-01'; expected YYYY-MM-DD\n")
    r = stats_vault.run("log", "pushups", "1", "-t", "25:00", cli="stats")
    assert (r.returncode, r.stderr) == (1, "stats: error: bad --time '25:00'; expected HH:MM\n")


# ---------- flush ----------

def test_flush_files_stat_lines_in_the_daily_log_with_their_timestamp(stats_vault):
    log(stats_vault, "pushups", "20", "-d", "2026-10-05", "-t", "12:00")
    log(stats_vault, "pushups", "25", "-d", "2026-10-05", "-t", "07:00")
    stats_vault.run("add-text", "Wellness", "Felt strong", "--date", "2026-10-05", cli="buffer")
    r = stats_vault.run("flush", cli="buffer")
    assert r.returncode == 0, r.stderr
    body = stats_vault.read("threads/Processes/Wellness/logs/2026-10-05.md").split("\n\n", 2)[2]
    lines = body.splitlines()
    # The TEXT line carries the wall-clock time (add-text has no -t), so its
    # place among the STAT lines depends on when the test runs.
    assert [ln for ln in lines if ln.startswith("STAT:")] == [
        "STAT: pushups 25 <!--2026-10-05T07:00:00-->",
        "STAT: pushups 20 <!--2026-10-05T12:00:00-->"]
    assert "TEXT: Felt strong" in lines
    assert stats_vault.read("buffer.md") == ""
    assert stats_vault.run(cli="lint").returncode == 0


def test_tend_reports_a_stat_whose_declaration_went_away(stats_vault):
    log(stats_vault, "pushups", "20")
    path = stats_vault.home / "threads/Processes/Wellness.md"
    path.write_text(path.read_text().replace("name: pushups", "name: push-ups"))
    r = stats_vault.run("flush", cli="buffer")
    assert r.returncode == 1
    assert "stat 'pushups' is not declared" in r.stderr
    assert "STAT: pushups 20" in stats_vault.read("buffer.md")


def test_tend_reports_a_stat_buffered_on_the_wrong_thread(stats_vault):
    stats_vault.write("buffer.md", "- [[Processes/Money]] STAT: pushups 20 <!--2026-10-05T07:00:00-->\n")
    r = stats_vault.run("tend", cli="buffer")
    assert r.returncode == 1
    assert "buffer.md:1: stat 'pushups' is declared on Processes/Wellness, not Processes/Money" in r.stderr


def test_tend_reports_attrs_on_a_stat(stats_vault):
    stats_vault.write("buffer.md", "- [[Processes/Wellness]] STAT: pushups 20 <!--2026-10-05T07:00:00 due:x-->\n")
    r = stats_vault.run("tend", cli="buffer")
    assert r.returncode == 1
    assert "STAT entries do not accept attrs; got 'due:x'" in r.stderr


# ---------- series ----------

def test_series_aggregates_each_period_by_the_stat_agg(stats_vault):
    for name, value, day, time in [
            ("pushups", "20", "2026-10-05", "07:00"), ("pushups", "25", "2026-10-05", "12:00"),
            ("pushups", "15", "2026-10-05", "18:00"),
            ("steps", "8900", "2026-10-05", "18:00"), ("steps", "3200", "2026-10-05", "10:00"),
            ("pullups", "8", "2026-10-05", "07:00"), ("pullups", "10", "2026-10-05", "07:05"),
            ("pullups", "7", "2026-10-05", "07:10"),
            ("spend-zar", "120.50", "2026-10-05", "09:00"), ("spend-zar", "2.25", "2026-10-05", "10:00")]:
        log(stats_vault, name, value, "-d", day, "-t", time)
    window = ["--since", "2026-10-05", "--until", "2026-10-05"]
    assert series(stats_vault, "pushups", *window) == [("2026-10-05", 60)]
    assert series(stats_vault, "steps", *window) == [("2026-10-05", 8900)]
    assert series(stats_vault, "pullups", *window) == [("2026-10-05", 10)]
    assert series(stats_vault, "spend-zar", *window) == [("2026-10-05", 122.75)]


def test_series_shows_a_gap_as_a_dash_not_a_zero(stats_vault):
    log(stats_vault, "pushups", "20", "-d", "2026-10-05")
    log(stats_vault, "pushups", "0", "-d", "2026-10-07")
    r = stats_vault.run("series", "pushups", "--since", "2026-10-04", "--until", "2026-10-07", cli="stats")
    assert r.stdout == ("pushups (Processes/Wellness, int, sum) by day\n"
                        "DAY         VALUE\n"
                        "2026-10-04  -\n"
                        "2026-10-05  20\n"
                        "2026-10-06  -\n"
                        "2026-10-07  0\n")
    periods = json.loads(stats_vault.run("series", "pushups", "--since", "2026-10-06", "--until", "2026-10-06",
                                         "--json", cli="stats").stdout)["periods"]
    assert periods == [{"period": "2026-10-06", "value": None, "entries": 0}]


def test_series_reads_the_logs_and_the_unflushed_buffer(stats_vault):
    log(stats_vault, "pushups", "20", "-d", "2026-10-05", "-t", "07:00")
    stats_vault.run("flush", cli="buffer")
    log(stats_vault, "pushups", "25", "-d", "2026-10-05", "-t", "08:00")
    log(stats_vault, "steps", "100", "-d", "2026-10-05")
    assert series(stats_vault, "pushups", "--since", "2026-10-05", "--until", "2026-10-05") == [("2026-10-05", 45)]


def test_series_last_takes_the_latest_across_log_and_buffer(stats_vault):
    log(stats_vault, "steps", "9000", "-d", "2026-10-05", "-t", "20:00")
    stats_vault.run("flush", cli="buffer")
    log(stats_vault, "steps", "4000", "-d", "2026-10-05", "-t", "12:00")
    assert series(stats_vault, "steps", "--since", "2026-10-05", "--until", "2026-10-05") == [("2026-10-05", 9000)]


def test_series_by_week_starts_on_monday_and_by_month(stats_vault):
    for day in ("2026-09-27", "2026-09-28", "2026-10-04", "2026-10-05"):
        log(stats_vault, "pushups", "10", "-d", day)
    window = ["--since", "2026-09-27", "--until", "2026-10-05"]
    assert series(stats_vault, "pushups", "--by", "week", *window) == [
        ("2026-09-21", 10), ("2026-09-28", 20), ("2026-10-05", 10)]
    assert series(stats_vault, "pushups", "--by", "month", *window) == [("2026-09", 20), ("2026-10", 20)]


def test_series_without_a_window_runs_from_the_first_value_to_today(stats_vault):
    start = date.today() - timedelta(days=2)
    log(stats_vault, "pushups", "5", "-d", start.isoformat())
    got = series(stats_vault, "pushups")
    # Run across midnight, the series is one day longer; the start is fixed.
    assert got[:3] == [(start.isoformat(), 5), ((start + timedelta(days=1)).isoformat(), None),
                       ((start + timedelta(days=2)).isoformat(), None)]
    assert got[3:] in ([], [((start + timedelta(days=3)).isoformat(), None)])


def test_series_runs_past_today_to_a_future_dated_value(stats_vault):
    ahead = date.today() + timedelta(days=2)
    log(stats_vault, "pushups", "5", "-d", ahead.isoformat())
    got = series(stats_vault, "pushups", "--since", date.today().isoformat())
    assert got[-1] == (ahead.isoformat(), 5)
    assert [v for _, v in got[:-1]] == [None] * (len(got) - 1)


def test_series_from_a_future_since_with_nothing_logged_is_empty(stats_vault):
    later = (date.today() + timedelta(days=30)).isoformat()
    r = stats_vault.run("series", "pushups", "--since", later, cli="stats")
    assert r.stdout == "pushups (Processes/Wellness, int, sum) by day\n(no entries)\n"


def test_series_by_month_crosses_a_year(stats_vault):
    for day in ("2025-11-30", "2026-01-01", "2026-01-31"):
        log(stats_vault, "pushups", "10", "-d", day)
    assert series(stats_vault, "pushups", "--by", "month", "--since", "2025-11-01", "--until", "2026-02-01") == [
        ("2025-11", 10), ("2025-12", None), ("2026-01", 20), ("2026-02", None)]


def test_series_with_no_values(stats_vault):
    r = stats_vault.run("series", "pushups", cli="stats")
    assert r.stdout == "pushups (Processes/Wellness, int, sum) by day\n(no entries)\n"


def test_an_event_is_counted_per_day_and_per_week(vault):
    """The documented way to record that something happened."""
    vault.write_thread("Processes", "Wellness")
    vault.run("new", "alcohol", "--thread", "Wellness", "--type", "int", "--agg", "sum", cli="stats")
    for day in ("2026-10-05", "2026-10-05", "2026-10-07"):
        log(vault, "alcohol", "1", "-d", day)
    window = ["--since", "2026-10-05", "--until", "2026-10-07"]
    assert series(vault, "alcohol", *window) == [("2026-10-05", 2), ("2026-10-06", None), ("2026-10-07", 1)]
    assert series(vault, "alcohol", "--by", "week", *window) == [("2026-10-05", 3)]


def test_series_stops_on_a_value_that_is_not_the_stat_type(stats_vault):
    path = stats_vault.write("threads/Processes/Wellness/logs/2026-10-05.md",
                             '---\nthread: "[[Processes/Wellness]]"\ndate: 2026-10-05\ntype: Log\n---\n\n'
                             "STAT: pushups 2.5 <!--2026-10-05T07:00:00-->\n")
    r = stats_vault.run("series", "pushups", cli="stats")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == (f"stats: error: {path.resolve()}:7: value '2.5' for 'pushups' must be a whole number; "
                        f"fix the line (`lint` reports it)\n")


def test_series_refuses_an_inverted_window(stats_vault):
    r = stats_vault.run("series", "pushups", "--since", "2026-10-05", "--until", "2026-10-01", cli="stats")
    assert (r.returncode, r.stderr) == (1, "stats: error: --since is after --until\n")


# ---------- help ----------

@pytest.mark.parametrize("argv", [["--help"], ["log", "--help"], ["new", "--help"]])
def test_help_says_how_to_record_an_event(vault, argv):
    out = " ".join(vault.run(*argv, cli="stats").stdout.split())
    assert "declare an int stat and log 1 each time it happens" in out
