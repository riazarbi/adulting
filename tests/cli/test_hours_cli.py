"""The `hours` command: log, list, report, show, edit and rm.

First written from the acceptance criteria in
stories/2026-09-07-hours-time-tracking.md, then extended to pin the exact
text a person reads.
"""

import json
import re
from datetime import datetime, timedelta

import pytest


@pytest.fixture
def hours_vault(vault):
    """ZAR thread with a rate, BWP thread without one, an unbilled topic, and
    vault defaults of 45 minutes and 1800 an hour."""
    vault.env["TZ"] = "Africa/Johannesburg"
    vault.write_thread("Projects", "SANA", currency="ZAR", rate=2500)
    vault.write_thread("Processes", "Trust", currency="BWP")
    vault.write_thread("Topics", "Wellness")
    (vault.home / ".adulting" / "config.yaml").write_text(
        "hours:\n  minutes: 45\n  rate: 1800\n", encoding="utf-8")
    return vault


@pytest.fixture
def logged(hours_vault):
    """Three entries on consecutive days; returns their ids in date order."""
    outputs = [
        hours_vault.run("log", "SANA", "Finance pack review", "-m", "90", "-d", "2026-08-04", "-t", "09:15", cli="hours"),
        hours_vault.run("log", "Trust", "Board prep", "-d", "2026-08-05", "-t", "14:00", cli="hours"),
        hours_vault.run("log", "Wellness", "5k", "run", "-m", "30", "-d", "2026-08-06", "-t", "06:30", cli="hours"),
    ]
    return [re.match(r"logged ([0-9a-f]{8})", r.stdout).group(1) for r in outputs]


# ---------- log ----------

def test_log_lines(hours_vault):
    lines = [
        hours_vault.run("log", "SANA", "Finance pack review", "-m", "90", "-d", "2026-08-04", "-t", "09:15", cli="hours").stdout,
        hours_vault.run("log", "Trust", "Board prep", "-d", "2026-08-05", "-t", "14:00", cli="hours").stdout,
        hours_vault.run("log", "Wellness", "5k", "run", "-m", "30", "-d", "2026-08-06", "-t", "06:30", cli="hours").stdout,
    ]
    shapes = [re.sub(r"^logged [0-9a-f]{8}", "logged ID", line) for line in lines]
    assert shapes == [
        "logged ID  Projects/SANA  2026-08-04 09:15  1h 30m @ 2500 ZAR = 3750 ZAR\n",
        "logged ID  Processes/Trust  2026-08-05 14:00  0h 45m @ 1800 BWP = 1350 BWP\n",
        "logged ID  Topics/Wellness  2026-08-06 06:30  0h 30m unbilled\n",
    ]


@pytest.mark.parametrize("argv, message", [
    (["SANA", ""], "hours: error: empty description\n"),
    (["SANA", "x", "-m", "0"], "hours: error: --minutes must be positive\n"),
    (["SANA", "x", "-d", "4 Aug"], "hours: error: bad --date '4 Aug'; expected YYYY-MM-DD\n"),
    (["SANA", "x", "-t", "9am"], "hours: error: bad --time '9am'; expected HH:MM\n"),
    (["Nope", "x"], "hours: error: thread 'Nope' does not resolve to a thread file\n"),
    (["SANA", "x", "-c", "RANDS"], "hours: error: currency 'RANDS' is not a 3-letter ISO code\n"),
])
def test_log_errors_write_nothing(hours_vault, argv, message):
    r = hours_vault.run("log", *argv, cli="hours")
    assert (r.returncode, r.stdout, r.stderr) == (1, "", message)
    assert list(hours_vault.home.rglob("hours.md")) == []


def test_log_defaults_are_60_minutes_and_2500(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    vault.run("log", "SANA Partners", "default sized", cli="hours")
    e = vault.entries("Projects", "SANA Partners")[0]
    assert e["rate"] == 2500
    r = vault.run("show", e["id"], "--json", cli="hours")
    assert json.loads(r.stdout)["minutes"] == 60


def test_log_uses_thread_rate_over_vault_default(vault):
    vault.write_thread("Projects", "Cheap", currency="ZAR", rate=800)
    vault.run("log", "Cheap", "discounted", cli="hours")
    assert vault.entries("Projects", "Cheap")[0]["rate"] == 800


def test_flag_rate_beats_thread_rate(vault):
    vault.write_thread("Projects", "Cheap", currency="ZAR", rate=800)
    vault.run("log", "Cheap", "override", "-r", "4000", cli="hours")
    assert vault.entries("Projects", "Cheap")[0]["rate"] == 4000


def test_ambiguous_thread_fails(vault):
    vault.write_thread("Projects", "Dup", currency="ZAR")
    vault.write_thread("Processes", "Dup", currency="ZAR")
    r = vault.run("log", "Dup", "x", cli="hours")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == "hours: error: ambiguous thread 'Dup'; matches: Projects/Dup, Processes/Dup\n"
    assert list(vault.home.rglob("hours.md")) == []


def test_qualified_path_disambiguates(vault):
    vault.write_thread("Projects", "Dup", currency="ZAR")
    vault.write_thread("Processes", "Dup", currency="ZAR")
    r = vault.run("log", "Processes/Dup", "x", cli="hours")
    assert r.returncode == 0, r.stderr
    assert len(vault.entries("Processes", "Dup")) == 1


def test_thread_resolution_is_case_sensitive(vault):
    """The Arbi family trust bug: case folding must not come from the FS."""
    vault.write_thread("Processes", "Arbi Family Trust", currency="BWP")
    r = vault.run("log", "Arbi family trust", "x", cli="hours")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == "hours: error: thread 'Arbi family trust' does not resolve to a thread file\n"
    assert list(vault.home.rglob("hours.md")) == []


def test_currency_flag_satisfies_missing_thread_currency(vault):
    vault.write_thread("Projects", "NoCcy")
    r = vault.run("log", "NoCcy", "x", "-c", "gbp", cli="hours")
    assert r.returncode == 0, r.stderr
    assert vault.entries("Projects", "NoCcy")[0]["currency"] == "GBP"


def test_punctuation_heavy_description_roundtrips(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    desc = 'Further decomposition; code review, with "Nick" and [[people/Nick]]'
    r = vault.run("log", "SANA Partners", desc, cli="hours")
    assert r.returncode == 0, r.stderr
    eid = vault.entries("Projects", "SANA Partners")[0]["id"]
    shown = json.loads(vault.run("show", eid, "--json", cli="hours").stdout)
    assert shown["description"] == desc


def test_entries_stay_sorted_by_start(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    vault.run("log", "SANA Partners", "later", "-d", "2026-06-01", "-t", "09:00", cli="hours")
    vault.run("log", "SANA Partners", "earlier", "-d", "2026-01-01", "-t", "09:00", cli="hours")
    names = [e["name"] for e in vault.entries("Projects", "SANA Partners")]
    assert names == ["earlier", "later"]



# ---------- unbilled time: currency is optional, because hours records time and money is an overlay on it ----------

def test_log_without_currency_records_unbilled(vault):
    vault.write_thread("Topics", "Reading")          # no currency, no rate
    r = vault.run("log", "Topics/Reading", "Read two chapters", "-m", "30",
                  cli="hours")
    assert r.returncode == 0, r.stderr
    assert "unbilled" in r.stdout
    e = vault.entries("Topics", "Reading")[0]
    assert e["rate"] == 0
    assert "currency" not in e          # absent, not null


def test_unbilled_hours_file_omits_currency_frontmatter(vault):
    vault.write_thread("Topics", "Reading")
    vault.run("log", "Topics/Reading", "Reading", "-m", "30", cli="hours")
    assert "currency:" not in vault.read("threads/Topics/Reading/hours.md")


def test_rate_without_currency_is_refused(vault):
    """The one incoherent combination: a charge with nothing to charge in."""
    vault.write_thread("Topics", "Reading")
    r = vault.run("log", "Topics/Reading", "Reading", "-m", "30", "-r", "500",
                  cli="hours")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == ("hours: error: --rate needs a currency\n"
                        "  pass --currency, or set `currency:` on the thread; "
                        "omit --rate to log the time as unbilled\n")
    assert list(vault.home.rglob("hours.md")) == []


def test_edit_an_unbilled_entry(vault):
    vault.write_thread("Topics", "Reading")
    vault.run("log", "Topics/Reading", "Reading", "-m", "30", cli="hours")
    eid = vault.entries("Topics", "Reading")[0]["id"]
    before = vault.entries("Topics", "Reading")[0]
    r = vault.run("edit", eid, "-m", "45", cli="hours")
    assert r.returncode == 0, r.stderr
    after = vault.entries("Topics", "Reading")[0]
    assert after["startTime"] == before["startTime"]
    start = datetime.fromisoformat(after["startTime"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(after["endTime"].replace("Z", "+00:00"))
    assert end - start == timedelta(minutes=45)
    assert (after["rate"], "currency" in after) == (0, False)


def test_statement_ignores_unbilled_time(vault):
    """Unbilled time can never be charged for, so it must not reach a
    statement of account."""
    vault.write_thread("Topics", "Reading")
    vault.write_thread("Projects", "SANA", currency="ZAR", rate=2500)
    vault.run("log", "Topics/Reading", "Reading", "-m", "600", cli="hours")
    vault.run("log", "Projects/SANA", "Spec", "-m", "60", cli="hours")
    out = vault.run("statement", cli="payments").stdout
    assert "Projects/SANA" in out
    assert "Topics/Reading" not in out


# ---------- list, report, show ----------

def test_list_table(hours_vault, logged):
    a, b, c = logged
    assert hours_vault.run("list", cli="hours").stdout == (
        "ID        DATE        THREAD               DUR          AMOUNT  DESCRIPTION\n"
        f"{a}  2026-08-04  Projects/SANA     1h 30m        3750 ZAR  Finance pack review\n"
        f"{b}  2026-08-05  Processes/Trust   0h 45m        1350 BWP  Board prep\n"
        f"{c}  2026-08-06  Topics/Wellness   0h 30m        unbilled  5k run\n")


def test_list_filters_and_empty(hours_vault, logged):
    assert hours_vault.run("list", "SANA", "--since", "2026-08-05", cli="hours").stdout == "(no entries)\n"
    rows = json.loads(hours_vault.run("list", "--since", "2026-08-05", "--until", "2026-08-05",
                           "--json", cli="hours").stdout)
    assert [r["description"] for r in rows] == ["Board prep"]
    r = hours_vault.run("list", "Nope", cli="hours")
    assert (r.returncode, r.stderr) == (1, "hours: error: thread 'Nope' does not resolve to a thread file\n")


def test_list_json_row(hours_vault, logged):
    rows = json.loads(hours_vault.run("list", "--json", cli="hours").stdout)
    assert rows[2] == {"id": logged[2], "thread": "Topics/Wellness", "date": "2026-08-06",
                       "time": "06:30", "minutes": 30, "rate": 0, "currency": "",
                       "amount": 0.0, "description": "5k run"}


def test_report_totals_per_currency_with_unbilled_first(hours_vault, logged):
    assert hours_vault.run("report", cli="hours").stdout == (
        "THREAD           ENTRIES    DURATION            AMOUNT\n"
        "Processes/Trust        1      0h 45m          1350 BWP\n"
        "Projects/SANA          1      1h 30m          3750 ZAR\n"
        "Topics/Wellness        1      0h 30m          unbilled\n"
        "\n"
        "TOTAL unbilled                0h 30m          unbilled\n"
        "TOTAL BWP                     0h 45m          1350 BWP\n"
        "TOTAL ZAR                     1h 30m          3750 ZAR\n")


def test_report_filters_and_empty(hours_vault, logged):
    assert hours_vault.run("report", "--thread", "Trust", "--until", "2026-08-05", cli="hours").stdout == (
        "THREAD           ENTRIES    DURATION            AMOUNT\n"
        "Processes/Trust        1      0h 45m          1350 BWP\n"
        "\n"
        "TOTAL BWP                     0h 45m          1350 BWP\n")
    assert hours_vault.run("report", "--since", "2030-01-01", cli="hours").stdout == "(no entries)\n"


def test_rate_zero_counts_hours_but_no_money(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    vault.run("log", "SANA Partners", "unbillable", "-m", "120", "-r", "0", cli="hours")
    b = json.loads(vault.run("report", "--json", cli="hours").stdout)[0]
    assert b["minutes"] == 120
    assert b["hours"] == 2.0
    assert b["amount"] == 0


def test_show_text_and_missing(hours_vault, logged):
    assert hours_vault.run("show", logged[0], cli="hours").stdout == (
        f"id           {logged[0]}\n"
        "thread       Projects/SANA\n"
        "date         2026-08-04\n"
        "time         09:15\n"
        "minutes      90\n"
        "rate         2500\n"
        "currency     ZAR\n"
        "amount       3750.0\n"
        "description  Finance pack review\n")
    r = hours_vault.run("show", "deadbeef", cli="hours")
    assert (r.returncode, r.stderr) == (1, "hours: error: no entry with id 'deadbeef'\n")


# ---------- edit, rm ----------

def stored(vault, entry_id):
    """The entry as it sits in the hours file."""
    for kind in ("Projects", "Processes", "Topics"):
        for f in (vault.home / "threads" / kind).glob("*/hours.md"):
            for e in vault.entries(kind, f.parent.name):
                if e["id"] == entry_id:
                    return e


def test_edit_minutes_and_description(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    vault.run("log", "SANA Partners", "before", "-m", "60", cli="hours")
    eid = vault.entries("Projects", "SANA Partners")[0]["id"]
    vault.run("edit", eid, "-m", "30", "--description", "after", "words", cli="hours")
    shown = json.loads(vault.run("show", eid, "--json", cli="hours").stdout)
    assert shown["minutes"] == 30
    assert shown["description"] == "after words"


def test_edit_moves_the_entry_and_keeps_its_duration(hours_vault, logged):
    r = hours_vault.run("edit", logged[0], "-d", "2026-08-07", "-t", "10:00", "-r", "3000", "-c", "usd", cli="hours")
    assert r.stdout == f"logged {logged[0]}  Projects/SANA  2026-08-07 10:00  1h 30m @ 3000 USD = 4500 USD\n"
    e = stored(hours_vault, logged[0])
    # 10:00 in Johannesburg is 08:00 UTC; the 90 minutes are kept.
    assert (e["startTime"], e["endTime"], e["rate"], e["currency"]) == (
        "2026-08-07T08:00:00.000Z", "2026-08-07T09:30:00.000Z", 3000, "USD")
    # The file keeps its original ZAR frontmatter; the entry carries USD.
    assert "currency: ZAR" in hours_vault.read("threads/Projects/SANA/hours.md")


def test_edit_errors(hours_vault, logged):
    r = hours_vault.run("edit", logged[0], "-c", "rands", cli="hours")
    assert (r.returncode, r.stderr) == (1, "hours: error: currency 'RANDS' is not a 3-letter ISO code\n")
    r = hours_vault.run("edit", logged[0], "-m", "-5", cli="hours")
    assert (r.returncode, r.stderr) == (1, "hours: error: --minutes must be positive\n")


def test_edit_refuses_a_rate_on_unbilled_time_as_log_does(hours_vault, logged):
    unbilled = logged[2]
    before = stored(hours_vault, unbilled)
    r = hours_vault.run("edit", unbilled, "--rate", "900", cli="hours")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == "hours: error: --rate needs a currency; pass --currency as well\n"
    assert stored(hours_vault, unbilled) == before
    r = hours_vault.run("edit", unbilled, "--rate", "900", "-c", "usd", cli="hours")
    assert r.returncode == 0, r.stderr
    assert (stored(hours_vault, unbilled)["rate"], stored(hours_vault, unbilled)["currency"]) == (900, "USD")


@pytest.mark.parametrize("words", [[], ["  "]])
def test_edit_refuses_an_empty_description_as_log_does(hours_vault, logged, words):
    before = stored(hours_vault, logged[0])
    r = hours_vault.run("edit", logged[0], "--description", *words, cli="hours")
    assert (r.returncode, r.stdout, r.stderr) == (1, "", "hours: error: empty description\n")
    assert stored(hours_vault, logged[0]) == before


def test_rm_with_yes(hours_vault, logged):
    r = hours_vault.run("rm", logged[2], "-y", cli="hours")
    assert (r.returncode, r.stdout) == (0, f"deleted {logged[2]}\n")
    assert hours_vault.entries("Topics", "Wellness") == []


def test_rm_without_yes_refuses_even_if_stdin_says_yes(hours_vault, logged):
    r = hours_vault.run("rm", logged[0], input="y\n", cli="hours")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == f"hours: error: refusing to delete {logged[0]} without -y\n"
    assert len(hours_vault.entries("Projects", "SANA")) == 1


# ---------- every record drops a REF into the buffer ----------
#
# So the thread's daily log is a complete chronology. The REF is best-effort
# and silent by design: the agent harness discards a tool's stdout whenever
# stderr is non-empty, so `hours log` cannot warn. A silent failure is only
# catchable here.


def test_log_writes_a_buffer_ref(vault):
    vault.write_thread("Projects", "SANA", currency="ZAR", rate=2500)
    vault.run("log", "Projects/SANA", "Reviewed the finance pack", "-m", "90",
              cli="hours")
    assert re.fullmatch(r"- \[\[Projects/SANA\]\] REF: \[\[Projects/SANA/hours\]\] "
                        r"1h 30m Reviewed the finance pack \([0-9a-f]{8}\) "
                        r"<!--\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d-->\n",
                        vault.read("buffer.md"))


def test_the_ref_survives_a_flush_into_the_log(vault):
    vault.write_thread("Projects", "SANA", currency="ZAR", rate=2500)
    vault.run("log", "Projects/SANA", "Reviewed the finance pack", "-m", "90",
              cli="hours")
    assert vault.run("flush", cli="buffer").returncode == 0
    logs = list((vault.home / "threads" / "Projects" / "SANA" / "logs").glob("*.md"))
    assert logs, "no log file was written"
    assert "REF: [[Projects/SANA/hours]]" in logs[0].read_text()


def test_a_failing_buffer_never_breaks_the_hours_write(vault, monkeypatch):
    """Best-effort means best-effort: the time entry is the record that
    matters and must land even if the buffer cannot be written."""
    (vault.home / "buffer.md").write_text("", encoding="utf-8")
    (vault.home / "buffer.md").chmod(0o444)
    try:
        vault.write_thread("Topics", "Wellness")
        r = vault.run("log", "Topics/Wellness", "5k run", "-m", "30", cli="hours")
        assert r.returncode == 0, r.stderr
        assert vault.entries("Topics", "Wellness")[0]["name"] == "5k run"
    finally:
        (vault.home / "buffer.md").chmod(0o644)


def test_backdated_entry_refs_into_the_right_days_log(vault):
    """A REF must be filed under the day the work happened, not the day the
    buffer was flushed. Without --date a backdated entry landed in today's
    log and the chronology lied."""
    vault.write_thread("Projects", "SANA", currency="ZAR", rate=2500)
    vault.run("log", "Projects/SANA", "Backdated work", "-m", "90",
              "-d", "2026-08-04", cli="hours")
    vault.run("flush", cli="buffer")
    day = vault.log_path("Projects/SANA", "2026-08-04")
    assert day.is_file(), sorted(
        p.name for p in (vault.home / "threads" / "Projects" / "SANA" / "logs").glob("*.md"))
    assert "Backdated work" in day.read_text()


def test_entries_on_different_days_split_across_log_files(vault):
    vault.write_thread("Projects", "SANA", currency="ZAR", rate=2500)
    vault.run("log", "Projects/SANA", "Older", "-m", "60", "-d", "2026-08-01",
              cli="hours")
    vault.run("log", "Projects/SANA", "Newer", "-m", "60", "-d", "2026-08-09",
              cli="hours")
    vault.run("flush", cli="buffer")
    days = sorted(p.stem for p in
                  (vault.home / "threads" / "Projects" / "SANA" / "logs").glob("*.md"))
    assert days == ["2026-08-01", "2026-08-09"], days


@pytest.fixture
def broken(hours_vault):
    """A hand-edited entry with a rate but no currency."""
    hours_vault.write_hours_file("Topics", "Wellness", currency="", entries=[{
        "name": "Run", "id": "bbbb0001", "rate": 900,
        "startTime": "2026-08-06T04:30:00.000Z", "endTime": "2026-08-06T05:00:00.000Z"}])
    return hours_vault


def test_edit_names_what_is_wrong_with_an_entry_it_cannot_keep(broken):
    before = broken.snapshot()
    r = broken.run("edit", "bbbb0001", "-m", "45", cli="hours")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == ("hours: error: entry bbbb0001 has a rate but no currency; "
                        "pass --currency, or --rate 0 to leave it unbilled\n")
    assert broken.snapshot() == before


@pytest.mark.parametrize("fix, rate, currency", [(["-c", "zar"], 900, "ZAR"), (["--rate", "0"], 0, None)])
def test_edit_can_repair_an_entry_with_a_rate_but_no_currency(broken, fix, rate, currency):
    r = broken.run("edit", "bbbb0001", "-m", "45", *fix, cli="hours")
    assert (r.returncode, r.stderr) == (0, "")
    e = stored(broken, "bbbb0001")
    assert (e["rate"], e.get("currency"), e["endTime"]) == (rate, currency, "2026-08-06T05:15:00.000Z")


# ---------- a rate is a whole number, or the command says so ----------

def test_a_thread_rate_that_is_not_a_whole_number_is_refused(vault):
    """It used to be swallowed: the thread billed at the built-in 2500."""
    p = vault.write_thread("Projects", "Acme", currency="ZAR")
    p.write_text(p.read_text().replace("currency: ZAR\n", "currency: ZAR\nrate: 1,000\n"))
    r = vault.run("log", "Acme", "work", "-m", "60", cli="hours")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == (f"hours: error: rate in {p} "
                        "must be a whole number; got '1,000'\n")
    assert list(vault.home.rglob("hours.md")) == []


def test_a_config_rate_that_is_not_a_whole_number_is_refused(vault):
    vault.write_thread("Projects", "Acme", currency="ZAR")
    vault.write(".adulting/config.yaml", "hours:\n  rate: 2,500\n")
    r = vault.run("log", "Acme", "work", "-m", "60", cli="hours")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == ("hours: error: hours.rate in .adulting/config.yaml "
                        "must be a whole number; got '2,500'\n")


@pytest.mark.parametrize("rate, shown", [("abc", "'abc'"), (2.5, "2.5"), (None, "None")])
def test_a_stored_rate_that_is_not_a_whole_number_stops_the_command(vault, rate, shown):
    """No entry is implicitly unbilled: a rate that cannot be read is an
    error wherever it is used, not a silent zero."""
    entry = {"name": "work", "id": "aaaa0001", "currency": "ZAR",
             "startTime": "2026-08-04T07:00:00.000Z", "endTime": "2026-08-04T08:00:00.000Z"}
    if rate is not None:
        entry["rate"] = rate
    vault.write_thread("Projects", "Acme", currency="ZAR")
    vault.write_hours_file("Projects", "Acme", [entry])
    for argv in (["list"], ["report"], ["show", "aaaa0001"]):
        r = vault.run(*argv, cli="hours")
        assert (r.returncode, r.stdout) == (1, ""), argv
        assert r.stderr == f"hours: error: rate of entry 'aaaa0001' must be a whole number; got {shown}\n"
    r = vault.run("statement", cli="payments")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == f"payments: error: rate of entry 'aaaa0001' must be a whole number; got {shown}\n"


def test_an_unbilled_entry_writes_a_buffer_ref_too(vault):
    """The REF is written for every entry, billed or not."""
    vault.write_thread("Topics", "Wellness")
    vault.run("log", "Topics/Wellness", "5k run", "-m", "30", cli="hours")
    assert re.fullmatch(r"- \[\[Topics/Wellness\]\] REF: \[\[Topics/Wellness/hours\]\] "
                        r"0h 30m 5k run \([0-9a-f]{8}\) <!--\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d-->\n",
                        vault.read("buffer.md"))


def test_log_stores_the_interval_it_reports(hours_vault):
    """The start and end as they land in the file, not just the printed line."""
    hours_vault.run("log", "SANA", "Finance pack review", "-m", "90",
                    "-d", "2026-08-04", "-t", "09:15", cli="hours")
    [e] = hours_vault.entries("Projects", "SANA")
    # 09:15 in Johannesburg is 07:15 UTC; 90 minutes later is 08:45.
    assert (e["startTime"], e["endTime"]) == ("2026-08-04T07:15:00.000Z", "2026-08-04T08:45:00.000Z")


def test_report_json_buckets_per_thread_and_currency(hours_vault, logged):
    assert json.loads(hours_vault.run("report", "--json", cli="hours").stdout) == [
        {"thread": "Processes/Trust", "currency": "BWP", "entries": 1, "minutes": 45,
         "hours": 0.75, "amount": 1350.0},
        {"thread": "Projects/SANA", "currency": "ZAR", "entries": 1, "minutes": 90,
         "hours": 1.5, "amount": 3750.0},
        {"thread": "Topics/Wellness", "currency": "", "entries": 1, "minutes": 30,
         "hours": 0.5, "amount": 0.0},
    ]


def test_a_record_is_filed_under_its_local_day_not_its_utc_day(vault):
    """Work logged at 09:00 in Sydney is stored as 23:00 UTC the day before.
    It belongs to the day it was done: that decides which log file it lands
    in and which statement window it falls in. Every other fixture is
    mid-day, where local and UTC agree, so this is the one that can tell.
    """
    sydney = {**vault.env, "TZ": "Australia/Sydney"}
    vault.write_thread("Projects", "SGB", currency="ZAR", rate=1000)
    r = vault.run("log", "Projects/SGB", "early start", "-m", "60",
                  "-d", "2026-06-02", "-t", "09:00", cli="hours", env=sydney)
    assert r.returncode == 0, r.stderr

    [entry] = vault.entries("Projects", "SGB")
    assert entry["startTime"] == "2026-06-01T23:00:00.000Z"

    listed = vault.run("list", "--since", "2026-06-02", "--until", "2026-06-02",
                       cli="hours", env=sydney)
    assert entry["id"] in listed.stdout
    assert listed.stdout.splitlines()[1].split()[1] == "2026-06-02"

    # And the buffer REF, which decides the log file, carries the same day.
    assert "<!--2026-06-02T" in vault.read("buffer.md")
