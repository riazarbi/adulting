"""Characterisation of `hours` output and errors, plus the removal of
interactivity (refactor unit 6).

test_hours_cli.py covers the behaviour from the original story, mostly via
JSON and file contents. These pin the text a person reads. The first sections
were run green against the pre-port script; the last section was written to
fail against it.
"""

import json
import re

import pytest

THREAD = "---\nstatus: open\nkind: {kind}\ncategory: professional\nstarted: 2026-01-01\n{extra}---\n\n# x\n"


def hours(vault, *argv, input=""):
    # input="" closes stdin, so any prompt would hit EOF instead of hanging.
    return vault.run(*argv, cli="hours", input=input)


@pytest.fixture
def v(vault):
    """ZAR thread with a rate, BWP thread without one, an unbilled topic, and
    vault defaults of 45 minutes and 1800 an hour."""
    vault.env["TZ"] = "Africa/Johannesburg"
    for rel, kind, extra in (("Projects/SANA", "project", "currency: ZAR\nrate: 2500\n"),
                             ("Processes/Trust", "process", "currency: BWP\n"),
                             ("Topics/Wellness", "topic", "")):
        p = vault.home / "threads" / f"{rel}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(THREAD.format(kind=kind, extra=extra), encoding="utf-8")
    (vault.home / ".adulting" / "config.yaml").write_text(
        "hours:\n  minutes: 45\n  rate: 1800\n", encoding="utf-8")
    return vault


@pytest.fixture
def logged(v):
    """Three entries on consecutive days; returns their ids in date order."""
    outputs = [
        hours(v, "log", "SANA", "Finance pack review", "-m", "90", "-d", "2026-08-04", "-t", "09:15"),
        hours(v, "log", "Trust", "Board prep", "-d", "2026-08-05", "-t", "14:00"),
        hours(v, "log", "Wellness", "5k", "run", "-m", "30", "-d", "2026-08-06", "-t", "06:30"),
    ]
    return [re.match(r"logged ([0-9a-f]{8})", r.stdout).group(1) for r in outputs]


# ---------- log ----------

def test_log_lines(v):
    lines = [
        hours(v, "log", "SANA", "Finance pack review", "-m", "90", "-d", "2026-08-04", "-t", "09:15").stdout,
        hours(v, "log", "Trust", "Board prep", "-d", "2026-08-05", "-t", "14:00").stdout,
        hours(v, "log", "Wellness", "5k", "run", "-m", "30", "-d", "2026-08-06", "-t", "06:30").stdout,
    ]
    shapes = [re.sub(r"^logged [0-9a-f]{8}", "logged ID", l) for l in lines]
    assert shapes == [
        "logged ID  Projects/SANA  2026-08-04 09:15  1h 30m @ 2500 ZAR = 3750 ZAR\n",
        "logged ID  Processes/Trust  2026-08-05 14:00  0h 45m @ 1800 BWP = 1350 BWP\n",
        "logged ID  Topics/Wellness  2026-08-06 06:30  0h 30m unbilled\n",
    ]


@pytest.mark.parametrize("argv, message", [
    (["SANA", ""], "hours: empty description\n"),
    (["SANA", "x", "-m", "0"], "hours: --minutes must be positive\n"),
    (["SANA", "x", "-d", "4 Aug"], "hours: bad --date '4 Aug'; expected YYYY-MM-DD\n"),
    (["SANA", "x", "-t", "9am"], "hours: bad --time '9am'; expected HH:MM\n"),
    (["Nope", "x"], "hours: thread 'Nope' does not resolve to a thread file\n"),
])
def test_log_errors_write_nothing(v, argv, message):
    r = hours(v, "log", *argv)
    assert (r.returncode, r.stdout, r.stderr) == (1, "", message)
    assert list((v.home / "hours").rglob("*.md")) == []


# ---------- list, report, show ----------

def test_list_table(v, logged):
    a, b, c = logged
    assert hours(v, "list").stdout == (
        "ID        DATE        THREAD               DUR          AMOUNT  DESCRIPTION\n"
        f"{a}  2026-08-04  Projects/SANA     1h 30m        3750 ZAR  Finance pack review\n"
        f"{b}  2026-08-05  Processes/Trust   0h 45m        1350 BWP  Board prep\n"
        f"{c}  2026-08-06  Topics/Wellness   0h 30m        unbilled  5k run\n")


def test_list_filters_and_empty(v, logged):
    assert hours(v, "list", "SANA", "--since", "2026-08-05").stdout == "(no entries)\n"
    rows = json.loads(hours(v, "list", "--since", "2026-08-05", "--until", "2026-08-05",
                           "--json").stdout)
    assert [r["description"] for r in rows] == ["Board prep"]
    r = hours(v, "list", "Nope")
    assert (r.returncode, r.stderr) == (1, "hours: thread 'Nope' does not resolve to a thread file\n")


def test_list_json_row(v, logged):
    rows = json.loads(hours(v, "list", "--json").stdout)
    assert rows[2] == {"id": logged[2], "thread": "Topics/Wellness", "date": "2026-08-06",
                       "time": "06:30", "minutes": 30, "rate": 0, "currency": "",
                       "amount": 0.0, "description": "5k run"}


def test_report_totals_per_currency_with_unbilled_first(v, logged):
    assert hours(v, "report").stdout == (
        "THREAD           ENTRIES    DURATION            AMOUNT\n"
        "Processes/Trust        1      0h 45m          1350 BWP\n"
        "Projects/SANA          1      1h 30m          3750 ZAR\n"
        "Topics/Wellness        1      0h 30m          unbilled\n"
        "\n"
        "TOTAL unbilled                0h 30m          unbilled\n"
        "TOTAL BWP                     0h 45m          1350 BWP\n"
        "TOTAL ZAR                     1h 30m          3750 ZAR\n")


def test_report_filters_and_empty(v, logged):
    assert hours(v, "report", "--thread", "Trust", "--until", "2026-08-05").stdout == (
        "THREAD           ENTRIES    DURATION            AMOUNT\n"
        "Processes/Trust        1      0h 45m          1350 BWP\n"
        "\n"
        "TOTAL BWP                     0h 45m          1350 BWP\n")
    assert hours(v, "report", "--since", "2030-01-01").stdout == "(no entries)\n"


def test_show_text_and_missing(v, logged):
    assert hours(v, "show", logged[0]).stdout == (
        f"id           {logged[0]}\n"
        "thread       Projects/SANA\n"
        "date         2026-08-04\n"
        "time         09:15\n"
        "minutes      90\n"
        "rate         2500\n"
        "currency     ZAR\n"
        "amount       3750.0\n"
        "description  Finance pack review\n")
    r = hours(v, "show", "deadbeef")
    assert (r.returncode, r.stderr) == (1, "hours: no entry with id 'deadbeef'\n")


# ---------- edit, rm ----------

def test_edit_moves_the_entry_and_keeps_its_duration(v, logged):
    r = hours(v, "edit", logged[0], "-d", "2026-08-07", "-t", "10:00", "-r", "3000", "-c", "usd")
    assert r.stdout == f"logged {logged[0]}  Projects/SANA  2026-08-07 10:00  1h 30m @ 3000 USD = 4500 USD\n"
    # The file keeps its original ZAR frontmatter; the entry carries USD.
    assert "currency: ZAR" in v.read("hours/Projects/SANA.md")


def test_edit_errors(v, logged):
    r = hours(v, "edit", logged[0], "-c", "rands")
    assert (r.returncode, r.stderr) == (1, "hours: currency 'RANDS' is not a 3-letter ISO code\n")
    r = hours(v, "edit", logged[0], "-m", "-5")
    assert (r.returncode, r.stderr) == (1, "hours: --minutes must be positive\n")


def test_rm_with_yes(v, logged):
    r = hours(v, "rm", logged[2], "-y")
    assert (r.returncode, r.stdout) == (0, f"deleted {logged[2]}\n")
    assert v.entries("Topics", "Wellness") == []


def test_help_json_lists_subcommands(vault):
    manifest = json.loads(hours(vault, "--help-json").stdout)
    assert [s["name"] for s in manifest["subcommands"]] == [
        "log", "list", "report", "show", "edit", "rm"]


# ---------- no interactivity (fails against the pre-port script) ----------

def test_log_without_a_thread_fails_instead_of_prompting(v):
    r = hours(v, "log", input="1\nTyped description\n60\n\n")
    assert r.returncode == 2
    assert "thread" in r.stderr
    assert list((v.home / "hours").rglob("*.md")) == []


def test_log_all_flag_is_gone(v):
    r = hours(v, "log", "SANA", "x", "--all")
    assert r.returncode == 2
    assert "unrecognized arguments: --all" in r.stderr


def test_rm_without_yes_refuses_even_if_stdin_says_yes(v, logged):
    r = hours(v, "rm", logged[0], input="y\n")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == f"hours: refusing to delete {logged[0]} without -y\n"
    assert len(v.entries("Projects", "SANA")) == 1


def test_help_no_longer_mentions_interactive_mode(vault):
    for argv in (["--help"], ["log", "--help"]):
        assert "interactive" not in hours(vault, *argv).stdout.lower()
