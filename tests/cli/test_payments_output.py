"""Characterisation of `payments` output and errors, plus the removal of
interactivity (refactor unit 7).

test_payments_cli.py and tests/unit/test_statement.py cover the original
stories, mostly via JSON, files and the PDF. These pin the text a person
reads. The first sections were run green against the pre-port script; the
last section was written to fail against it.
"""

import json
import re

import pytest

THREAD = "---\nstatus: open\nkind: {kind}\ncategory: professional\nstarted: 2026-01-01\n{extra}---\n\n# x\n"


def pay(vault, *argv, input=""):
    # input="" closes stdin, so any prompt would hit EOF instead of hanging.
    return vault.run(*argv, cli="payments", input=input)


@pytest.fixture
def v(vault):
    vault.env["TZ"] = "Africa/Johannesburg"
    for rel, kind, extra in (("Projects/SANA", "project", "currency: ZAR\nrate: 2500\n"),
                             ("Processes/Trust", "process", "currency: BWP\nrate: 1000\n"),
                             ("Topics/Wellness", "topic", "")):
        p = vault.home / "threads" / f"{rel}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(THREAD.format(kind=kind, extra=extra), encoding="utf-8")
    vault.run("log", "SANA", "Work", "-m", "600", "-d", "2026-07-01", "-t", "09:00", cli="hours")
    vault.run("log", "Trust", "Board", "-m", "90", "-d", "2026-07-02", "-t", "09:00", cli="hours")
    return vault


@pytest.fixture
def paid(v):
    """Two receipts; returns their ids in date order."""
    outs = [pay(v, "log", "SANA", "47,300.50", "-d", "2026-07-10", "-t", "08:00",
                "-a", "FNB Business", "-n", "Invoice", "2026-014"),
            pay(v, "log", "Trust", "500", "-d", "2026-07-11")]
    return [re.match(r"received ([0-9a-f]{8})", r.stdout).group(1) for r in outs]


# ---------- log ----------

def test_log_lines(v):
    a = pay(v, "log", "SANA", "47,300.50", "-d", "2026-07-10", "-a", "FNB Business").stdout
    b = pay(v, "log", "Trust", "500", "-d", "2026-07-11").stdout
    assert re.sub(r"[0-9a-f]{8}", "ID", a) == "received ID  Projects/SANA  2026-07-10  47300.5 ZAR  FNB Business\n"
    assert re.sub(r"[0-9a-f]{8}", "ID", b) == "received ID  Processes/Trust  2026-07-11  500 BWP\n"


@pytest.mark.parametrize("argv, message", [
    (["SANA", "abc"], "payments: error: 'abc' is not a valid amount\n"),
    (["SANA", "-5"], "payments: error: amount must be positive (got -5)\n"),
    (["SANA"], "payments: error: amount is required\n"),
    (["Wellness", "100"], "payments: error: thread 'Topics/Wellness' has no currency\n"
                          "  set `currency: ZAR` in threads/Topics/Wellness.md, or pass --currency\n"),
    (["SANA", "10", "-d", "11 July"], "payments: error: bad --date '11 July'; expected YYYY-MM-DD\n"),
    (["Nope", "10"], "payments: error: thread 'Nope' does not resolve to a thread file\n"),
])
def test_log_errors_write_nothing(v, argv, message):
    r = pay(v, "log", *argv)
    assert (r.returncode, r.stdout, r.stderr) == (1, "", message)
    assert list((v.home / "payments").rglob("*.md")) == []


# ---------- list, show ----------

def test_list_table(v, paid):
    a, b = paid
    assert pay(v, "list").stdout == (
        "ID        RECEIVED    THREAD                     AMOUNT  ACCOUNT       NOTE\n"
        f"{a}  2026-07-10  Projects/SANA         47300.5 ZAR  FNB Business  Invoice 2026-014\n"
        f"{b}  2026-07-11  Processes/Trust           500 BWP                \n")


def test_list_filters_and_empty(v, paid):
    assert pay(v, "list", "Trust", "--since", "2026-07-11").stdout == (
        "ID        RECEIVED    THREAD                     AMOUNT  ACCOUNT  NOTE\n"
        f"{paid[1]}  2026-07-11  Processes/Trust           500 BWP     \n")
    assert pay(v, "list", "--until", "2026-01-01").stdout == "(no payments)\n"


def test_list_json_row(v, paid):
    assert json.loads(pay(v, "list", "--json").stdout)[0] == {
        "id": paid[0], "thread": "Projects/SANA", "received": "2026-07-10",
        "amount": 47300.5, "currency": "ZAR", "account": "FNB Business",
        "note": "Invoice 2026-014"}


def test_show_text_and_missing(v, paid):
    assert pay(v, "show", paid[0]).stdout == (
        f"id         {paid[0]}\n"
        "thread     Projects/SANA\n"
        "received   2026-07-10\n"
        "amount     47300.5\n"
        "currency   ZAR\n"
        "account    FNB Business\n"
        "note       Invoice 2026-014\n")
    r = pay(v, "show", "deadbeef")
    assert (r.returncode, r.stderr) == (1, "payments: error: no payment with id 'deadbeef'\n")


# ---------- edit, rm ----------

def test_edit_several_fields(v, paid):
    r = pay(v, "edit", paid[1], "--amount", "600", "-a", "Capitec", "-n", "top", "up",
            "-d", "2026-07-12", "-t", "10:30")
    assert r.stdout == f"received {paid[1]}  Processes/Trust  2026-07-12  600 BWP  Capitec\n"
    assert json.loads(pay(v, "show", paid[1], "--json").stdout)["note"] == "top up"


def received(v, pid):
    """The stored `received` timestamp, rendered in the test's local zone."""
    return json.loads(pay(v, "show", pid, "--json").stdout)["received"], \
        next(p["received"] for p in v.payments("Projects", "SANA") if p["id"] == pid)


def test_edit_time_alone_keeps_the_date(v, paid):
    """-t used to be ignored unless -d came with it."""
    r = pay(v, "edit", paid[0], "-t", "23:59")
    assert r.stdout == f"received {paid[0]}  Projects/SANA  2026-07-10  47300.5 ZAR  FNB Business\n"
    assert received(v, paid[0]) == ("2026-07-10", "2026-07-10T21:59:00.000Z")


def test_edit_date_alone_keeps_the_time(v, paid):
    """-d used to reset the time to the moment of the edit."""
    pay(v, "edit", paid[0], "-d", "2026-07-15")
    assert received(v, paid[0]) == ("2026-07-15", "2026-07-15T06:00:00.000Z")


def test_edit_errors(v, paid):
    r = pay(v, "edit", paid[1], "-c", "pula")
    assert (r.returncode, r.stderr) == (1, "payments: error: currency 'PULA' is not a 3-letter ISO code\n")
    r = pay(v, "edit", paid[1], "--amount", "0")
    assert (r.returncode, r.stderr) == (1, "payments: error: amount must be positive (got 0)\n")


def test_rm_with_yes(v, paid):
    assert pay(v, "rm", paid[1], "-y").stdout == f"deleted {paid[1]}\n"
    assert v.payments("Processes", "Trust") == []


# ---------- statement ----------

STATEMENT = (
    "THREAD                     BILLED          RECEIVED       OUTSTANDING\n"
    "Processes/Trust          1500 BWP           500 BWP          1000 BWP\n"
    "Projects/SANA           25000 ZAR       47300.5 ZAR      -22300.5 ZAR\n"
    "\n"
    "TOTAL BWP                1500 BWP           500 BWP          1000 BWP\n"
    "TOTAL ZAR               25000 ZAR       47300.5 ZAR      -22300.5 ZAR\n")


def test_statement_table(v, paid):
    assert pay(v, "statement").stdout == STATEMENT


def test_statement_as_of_bounds_the_text_view(v, paid):
    assert pay(v, "statement", "--thread", "SANA", "--as-of", "2026-07-05").stdout == (
        "THREAD                   BILLED          RECEIVED       OUTSTANDING\n"
        "Projects/SANA         25000 ZAR             0 ZAR         25000 ZAR\n"
        "\n"
        "TOTAL ZAR             25000 ZAR             0 ZAR         25000 ZAR\n")


def test_statement_rejects_a_malformed_as_of(v, paid):
    """The text view used to compare a bad --as-of as a string, bound
    nothing, and print the whole statement. It now fails like --pdf does."""
    r = pay(v, "statement", "--as-of", "5 July")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == "payments: error: bad --as-of '5 July'; expected YYYY-MM-DD\n"


def test_statement_empty(v):
    assert pay(v, "statement", "--since", "2030-01-01").stdout == "(nothing to report)\n"


def test_help_json_lists_subcommands(vault):
    manifest = json.loads(pay(vault, "--help-json").stdout)
    assert [s["name"] for s in manifest["subcommands"]] == [
        "log", "list", "statement", "show", "edit", "rm"]


# ---------- no interactivity (fails against the pre-port script) ----------

def test_log_without_a_thread_fails_instead_of_prompting(v):
    r = pay(v, "log", input="1\n1500\n2026-03-01\nFNB\nInvoice 3\n")
    assert r.returncode == 2
    assert "thread" in r.stderr
    assert list((v.home / "payments").rglob("*.md")) == []


def test_rm_without_yes_refuses_even_if_stdin_says_yes(v, paid):
    r = pay(v, "rm", paid[0], input="y\n")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == f"payments: error: refusing to delete {paid[0]} without -y\n"
    assert len(v.payments("Projects", "SANA")) == 1


def test_list_and_statement_round_the_same_amount_the_same_way(v):
    """Money is kept as Decimal until it is printed. `list` used to go through
    float, so a hand-edited 2.675 showed as 2.67 there and 2.68 in the
    statement."""
    v.write_payments_file("Projects", "SANA", payments=[{
        "id": "cccc0001", "received": "2026-07-20T08:00:00.000Z",
        "amount": 2.675, "currency": "ZAR"}])
    assert "  2.68 ZAR  " in pay(v, "list").stdout
    assert "  2.68 ZAR  " in pay(v, "statement", "--thread", "SANA").stdout
