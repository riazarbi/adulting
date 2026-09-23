"""The `payments` command: log, list, show, edit, rm, and the statement of
account as text, JSON and PDF."""

import json
import re
import shutil
import subprocess
from datetime import date
import sys

import pytest

from harness import command_path, without_program

needs_pdf = pytest.mark.skipif(
    not (shutil.which("pandoc") and shutil.which("xelatex")),
    reason="pandoc + xelatex required to render a PDF")


@pytest.fixture
def payments_vault(vault):
    """SANA (ZAR, 10 hours at 2500) and Trust (BWP, 90 minutes at 1000)
    billed in July 2026, and an unbilled topic."""
    vault.env["TZ"] = "Africa/Johannesburg"
    vault.write_thread("Projects", "SANA", currency="ZAR", rate=2500)
    vault.write_thread("Processes", "Trust", currency="BWP", rate=1000)
    vault.write_thread("Topics", "Wellness")
    vault.run("log", "SANA", "Work", "-m", "600", "-d", "2026-07-01", "-t", "09:00", cli="hours")
    vault.run("log", "Trust", "Board", "-m", "90", "-d", "2026-07-02", "-t", "09:00", cli="hours")
    return vault


@pytest.fixture
def paid(payments_vault):
    """Two receipts; returns their ids in date order."""
    outs = [payments_vault.run("log", "SANA", "47,300.50", "-d", "2026-07-10", "-t", "08:00",
                "-a", "FNB Business", "-n", "Invoice", "2026-014", cli="payments"),
            payments_vault.run("log", "Trust", "500", "-d", "2026-07-11", cli="payments")]
    return [re.match(r"received ([0-9a-f]{8})", r.stdout).group(1) for r in outs]


# ---------- log ----------

def test_log_lines(payments_vault):
    a = payments_vault.run("log", "SANA", "47,300.50", "-d", "2026-07-10", "-a", "FNB Business", cli="payments").stdout
    b = payments_vault.run("log", "Trust", "500", "-d", "2026-07-11", cli="payments").stdout
    assert re.sub(r"[0-9a-f]{8}", "ID", a) == "received ID  Projects/SANA  2026-07-10  47300.5 ZAR  FNB Business\n"
    assert re.sub(r"[0-9a-f]{8}", "ID", b) == "received ID  Processes/Trust  2026-07-11  500 BWP\n"


@pytest.mark.parametrize("argv, message", [
    (["SANA", "abc"], "payments: error: 'abc' is not a valid amount\n"),
    (["SANA", "-5"], "payments: error: amount must be positive (got -5)\n"),
    (["SANA", "0"], "payments: error: amount must be positive (got 0)\n"),
    (["SANA"], "payments: error: amount is required\n"),
    (["Wellness", "100"], "payments: error: thread 'Topics/Wellness' has no currency\n"
                          "  set `currency: ZAR` in threads/Topics/Wellness.md, or pass --currency\n"),
    (["SANA", "10", "-d", "11 July"], "payments: error: bad --date '11 July'; expected YYYY-MM-DD\n"),
    (["Nope", "10"], "payments: error: thread 'Nope' does not resolve to a thread file\n"),
])
def test_log_errors_write_nothing(payments_vault, argv, message):
    r = payments_vault.run("log", *argv, cli="payments")
    assert (r.returncode, r.stdout, r.stderr) == (1, "", message)
    assert list((payments_vault.home / "payments").rglob("*.md")) == []


def test_log_records_a_payment(vault):
    vault.env["TZ"] = "Africa/Gaborone"
    vault.write_thread("Processes", "Arbi Family Trust", currency="BWP")
    r = vault.run("log", "Arbi Family Trust", "47300", "-d", "2023-04-05", "-t", "09:30",
            "-a", "FNB Botswana", cli="payments")
    assert r.returncode == 0, r.stderr
    [p] = vault.payments("Processes", "Arbi Family Trust")
    assert re.fullmatch(r"[0-9a-f]{8}", p.pop("id"))
    # 09:30 in Gaborone is 07:30 UTC.
    assert p == {"received": "2023-04-05T07:30:00.000Z", "amount": 47300,
                 "currency": "BWP", "account": "FNB Botswana"}


def test_decimal_amount_is_exact(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    vault.run("log", "X", "0.10", cli="payments")
    vault.run("log", "X", "0.20", cli="payments")
    out = json.loads(vault.run("statement", "--json", cli="payments").stdout)[0]
    assert out["received"] == 0.30      # not 0.30000000000000004


def test_payments_sorted_by_received(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    vault.run("log", "X", "1", "-d", "2026-06-01", cli="payments")
    vault.run("log", "X", "2", "-d", "2026-01-01", cli="payments")
    amounts = [p["amount"] for p in vault.payments("Projects", "X")]
    assert amounts == [2, 1]


def test_payment_writes_a_buffer_ref(vault):
    """Same convention as notes and hours: the receipt shows up in the
    thread's daily log on the next flush."""
    vault.write_thread("Projects", "SANA", currency="ZAR", rate=2500)
    vault.run("log", "Projects/SANA", "15000", "-a", "Business current",
              cli="payments")
    # The target is the directory form, payments/Projects/..., not the
    # frontmatter kind, payments/project/...
    assert re.fullmatch(r"- \[\[Projects/SANA\]\] REF: \[\[payments/Projects/SANA\]\] "
                        r"15000 ZAR received \([0-9a-f]{8}\) <!--\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d-->\n",
                        vault.read("buffer.md"))


def test_log_without_a_thread_fails_instead_of_prompting(payments_vault):
    r = payments_vault.run("log", input="1\n1500\n2026-03-01\nFNB\nInvoice 3\n", cli="payments")
    assert r.returncode == 2
    assert "thread" in r.stderr
    assert list((payments_vault.home / "payments").rglob("*.md")) == []


# ---------- list, show ----------

def test_list_table(payments_vault, paid):
    a, b = paid
    assert payments_vault.run("list", cli="payments").stdout == (
        "ID        RECEIVED    THREAD                     AMOUNT  ACCOUNT       NOTE\n"
        f"{a}  2026-07-10  Projects/SANA         47300.5 ZAR  FNB Business  Invoice 2026-014\n"
        f"{b}  2026-07-11  Processes/Trust           500 BWP                \n")


def test_list_filters_and_empty(payments_vault, paid):
    assert payments_vault.run("list", "Trust", "--since", "2026-07-11", cli="payments").stdout == (
        "ID        RECEIVED    THREAD                     AMOUNT  ACCOUNT  NOTE\n"
        f"{paid[1]}  2026-07-11  Processes/Trust           500 BWP     \n")
    assert payments_vault.run("list", "--until", "2026-01-01", cli="payments").stdout == "(no payments)\n"


def test_list_json_row(payments_vault, paid):
    assert json.loads(payments_vault.run("list", "--json", cli="payments").stdout)[0] == {
        "id": paid[0], "thread": "Projects/SANA", "received": "2026-07-10",
        "amount": 47300.5, "currency": "ZAR", "account": "FNB Business",
        "note": "Invoice 2026-014"}


def test_show_text_and_missing(payments_vault, paid):
    assert payments_vault.run("show", paid[0], cli="payments").stdout == (
        f"id         {paid[0]}\n"
        "thread     Projects/SANA\n"
        "received   2026-07-10\n"
        "amount     47300.5\n"
        "currency   ZAR\n"
        "account    FNB Business\n"
        "note       Invoice 2026-014\n")
    r = payments_vault.run("show", "deadbeef", cli="payments")
    assert (r.returncode, r.stderr) == (1, "payments: error: no payment with id 'deadbeef'\n")


# ---------- edit, rm ----------

def test_edit_several_fields(payments_vault, paid):
    r = payments_vault.run("edit", paid[1], "--amount", "600", "-a", "Capitec", "-n", "top", "up",
            "-d", "2026-07-12", "-t", "10:30", cli="payments")
    assert r.stdout == f"received {paid[1]}  Processes/Trust  2026-07-12  600 BWP  Capitec\n"
    assert json.loads(payments_vault.run("show", paid[1], "--json", cli="payments").stdout)["note"] == "top up"


def received(payments_vault, pid):
    """The stored `received` timestamp, rendered in the test's local zone."""
    return json.loads(payments_vault.run("show", pid, "--json", cli="payments").stdout)["received"], \
        next(p["received"] for p in payments_vault.payments("Projects", "SANA") if p["id"] == pid)


def test_edit_time_alone_keeps_the_date(payments_vault, paid):
    """-t used to be ignored unless -d came with it."""
    r = payments_vault.run("edit", paid[0], "-t", "23:59", cli="payments")
    assert r.stdout == f"received {paid[0]}  Projects/SANA  2026-07-10  47300.5 ZAR  FNB Business\n"
    assert received(payments_vault, paid[0]) == ("2026-07-10", "2026-07-10T21:59:00.000Z")


def test_edit_date_alone_keeps_the_time(payments_vault, paid):
    """-d used to reset the time to the moment of the edit."""
    payments_vault.run("edit", paid[0], "-d", "2026-07-15", cli="payments")
    assert received(payments_vault, paid[0]) == ("2026-07-15", "2026-07-15T06:00:00.000Z")


def test_edit_errors(payments_vault, paid):
    r = payments_vault.run("edit", paid[1], "-c", "pula", cli="payments")
    assert (r.returncode, r.stderr) == (1, "payments: error: currency 'PULA' is not a 3-letter ISO code\n")
    r = payments_vault.run("edit", paid[1], "--amount", "0", cli="payments")
    assert (r.returncode, r.stderr) == (1, "payments: error: amount must be positive (got 0)\n")


def test_rm_with_yes(payments_vault, paid):
    assert payments_vault.run("rm", paid[1], "-y", cli="payments").stdout == f"deleted {paid[1]}\n"
    assert payments_vault.payments("Processes", "Trust") == []


def test_rm_without_yes_refuses_even_if_stdin_says_yes(payments_vault, paid):
    r = payments_vault.run("rm", paid[0], input="y\n", cli="payments")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == f"payments: error: refusing to delete {paid[0]} without -y\n"
    assert len(payments_vault.payments("Projects", "SANA")) == 1


# ---------- statement ----------

STATEMENT = (
    "THREAD                     BILLED          RECEIVED       OUTSTANDING\n"
    "Processes/Trust          1500 BWP           500 BWP          1000 BWP\n"
    "Projects/SANA           25000 ZAR       47300.5 ZAR      -22300.5 ZAR\n"
    "\n"
    "TOTAL BWP                1500 BWP           500 BWP          1000 BWP\n"
    "TOTAL ZAR               25000 ZAR       47300.5 ZAR      -22300.5 ZAR\n")


def test_statement_table(payments_vault, paid):
    assert payments_vault.run("statement", cli="payments").stdout == STATEMENT


def test_statement_as_of_bounds_the_text_view(payments_vault, paid):
    assert payments_vault.run("statement", "--thread", "SANA", "--as-of", "2026-07-05", cli="payments").stdout == (
        "THREAD                   BILLED          RECEIVED       OUTSTANDING\n"
        "Projects/SANA         25000 ZAR             0 ZAR         25000 ZAR\n"
        "\n"
        "TOTAL ZAR             25000 ZAR             0 ZAR         25000 ZAR\n")


def test_statement_rejects_a_malformed_as_of(payments_vault, paid):
    """The text view used to compare a bad --as-of as a string, bound
    nothing, and print the whole statement. It now fails like --pdf does."""
    r = payments_vault.run("statement", "--as-of", "5 July", cli="payments")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == "payments: error: bad --as-of '5 July'; expected YYYY-MM-DD\n"


def test_statement_empty(payments_vault):
    assert payments_vault.run("statement", "--since", "2030-01-01", cli="payments").stdout == "(nothing to report)\n"


def test_statement_billed_minus_received(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    vault.run("log", "X", "work", "-m", "120", "-r", "1000", cli="hours")   # 2000 billed
    vault.run("log", "X", "750", cli="payments")
    row = json.loads(vault.run("statement", "--json", cli="payments").stdout)[0]
    assert row["billed"] == 2000
    assert row["received"] == 750
    assert row["outstanding"] == 1250


def test_statement_shows_billed_thread_with_no_payments(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    vault.run("log", "X", "work", "-m", "60", "-r", "500", cli="hours")
    row = json.loads(vault.run("statement", "--json", cli="payments").stdout)[0]
    assert row["billed"] == 500 and row["received"] == 0
    assert row["outstanding"] == 500


def test_statement_shows_payment_with_no_billed_hours(vault):
    """An advance payment must not vanish from the statement."""
    vault.write_thread("Projects", "X", currency="ZAR")
    vault.run("log", "X", "1000", cli="payments")
    row = json.loads(vault.run("statement", "--json", cli="payments").stdout)[0]
    assert row["billed"] == 0 and row["received"] == 1000
    assert row["outstanding"] == -1000


def test_statement_date_window(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    vault.run("log", "X", "100", "-d", "2026-01-01", cli="payments")
    vault.run("log", "X", "200", "-d", "2026-06-01", cli="payments")
    row = json.loads(vault.run("statement", "--since", "2026-05-01",
                         "--json", cli="payments").stdout)[0]
    assert row["received"] == 200


def test_list_and_statement_round_the_same_amount_the_same_way(payments_vault):
    """Money is kept as Decimal until it is printed. `list` used to go through
    float, so a hand-edited 2.675 showed as 2.67 there and 2.68 in the
    statement."""
    payments_vault.write_payments_file("Projects", "SANA", payments=[{
        "id": "cccc0001", "received": "2026-07-20T08:00:00.000Z",
        "amount": 2.675, "currency": "ZAR"}])
    assert "  2.68 ZAR  " in payments_vault.run("list", cli="payments").stdout
    assert "  2.68 ZAR  " in payments_vault.run("statement", "--thread", "SANA", cli="payments").stdout


def test_hours_report_text_statement_and_pdf_statement_agree_to_the_cent(vault):
    """Each charge is rounded to the cent at the line, so the printed lines
    sum to the printed total. Three 20-minute entries at 2500 are 833.33
    each: 2499.99, not the unrounded 2500.00."""
    vault.write_thread("Projects", "SANA", currency="ZAR", rate=2500)
    for day in ("01", "02", "03"):
        vault.run("log", "SANA", f"work {day}", "-m", "20", "-d", f"2026-07-{day}",
                  "-t", "09:00", cli="hours")
    report = json.loads(vault.run("report", "--json", cli="hours").stdout)
    statement = json.loads(vault.run("statement", "--json", cli="payments").stdout)
    assert [r["amount"] for r in report] == [2499.99]
    assert [r["billed"] for r in statement] == [2499.99]
    code = ("from datetime import date; from adulting import payments as P; "
            "print(P.one_thread_statement('SANA', date(2026, 7, 31))['charges'])")
    pdf = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=vault.env)
    assert pdf.stdout.strip() == "2499.99"


# ---------- statement --pdf ----------

def sana(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR", rate=2500)
    p = vault.home / "threads" / "Projects" / "SANA Partners.md"
    p.write_text(p.read_text().replace(
        "---\n\n# SANA",
        "client_name: Sana Partners (Pty) Ltd\n"
        "client_address: Unit 301|2 Park Road|Cape Town\n"
        "client_vat: 4220259826\n---\n\n# SANA"), encoding="utf-8")
    return p


def test_pdf_requires_a_thread(vault):
    sana(vault)
    r = vault.run("statement", "--pdf", str(vault.home / "x.pdf"), cli="payments")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == "payments: error: --pdf needs --thread; a statement is per client\n"
    assert not (vault.home / "x.pdf").exists()


def test_pdf_requires_client_name(vault):
    vault.write_thread("Projects", "NoClient", currency="ZAR")
    vault.run("log", "NoClient", "work", cli="hours")
    r = vault.run("statement", "--thread", "NoClient", "--pdf",
                  str(vault.home / "x.pdf"), cli="payments")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == ("payments: error: thread 'Projects/NoClient' has no client_name\n"
                        "  set `client_name:` in threads/Projects/NoClient.md\n")
    assert not (vault.home / "x.pdf").exists()


def test_pdf_refuses_when_there_is_nothing_to_state(vault):
    sana(vault)
    r = vault.run("statement", "--thread", "SANA Partners", "--pdf",
                  str(vault.home / "x.pdf"), "--as-of", "2026-06-30", cli="payments")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == "payments: error: nothing to state for 'Projects/SANA Partners' as at 2026-06-30\n"
    assert not (vault.home / "x.pdf").exists()


@needs_pdf
def test_pdf_renders_and_reports(vault):
    sana(vault)
    vault.run("log", "SANA Partners", "Bitemporal design", "-m", "120",
              "-r", "2500", "-d", "2026-06-01", "-t", "09:00", cli="hours")
    vault.run("log", "SANA Partners", "1000", "-d", "2026-06-15", cli="payments")
    out = vault.home / "statement.pdf"
    r = vault.run("statement", "--thread", "SANA Partners", "--as-of",
                  "2026-06-30", "--pdf", str(out), cli="payments")
    assert r.returncode == 0, r.stderr
    assert out.exists() and out.stat().st_size > 1000
    assert out.read_bytes()[:5] == b"%PDF-"
    assert r.stdout == (f"{out}: 2 lines, 2.00 h, charges 5000 ZAR, paid 1000 ZAR, "
                        "balance 4000 ZAR as at 2026-06-30\n")


@needs_pdf
def test_pdf_warns_when_banking_is_missing(vault):
    sana(vault)
    vault.run("log", "SANA Partners", "work", "-m", "60", "-r", "100",
              "-d", "2026-06-01", "-t", "09:00", cli="hours")
    out = vault.home / "statement.pdf"
    r = vault.run("statement", "--thread", "SANA Partners", "--pdf", str(out),
                  "--as-of", "2026-06-30", cli="payments")
    assert r.returncode == 0, r.stderr
    assert r.stderr == ("payments: warning: banking details incomplete in .adulting/config.yaml — "
                        "the statement says so instead of printing a payment table\n")


@needs_pdf
def test_a_failed_render_leaves_no_stale_file(vault):
    """Better no statement than yesterday's figures under today's date. The
    render fails for real: pandoc runs, but there is no xelatex to call."""
    sana(vault)
    vault.run("log", "SANA Partners", "work", "-m", "60", "-r", "100",
              "-d", "2026-06-01", "-t", "09:00", cli="hours")
    out = vault.home / "statement.pdf"
    out.write_bytes(b"stale")
    no_latex = without_program(vault.env, "xelatex")
    r = subprocess.run([command_path("payments", no_latex), "statement", "--thread", "SANA Partners",
                        "--pdf", str(out), "--as-of", "2026-06-30"],
                       capture_output=True, text=True, env=no_latex)
    assert r.returncode == 1
    assert r.stderr.startswith("payments: error: pandoc failed\n")
    assert "xelatex" in r.stderr
    assert not out.exists()


def test_a_pdf_folder_that_cannot_be_made_is_an_error_not_a_traceback(vault):
    sana(vault)
    vault.run("log", "SANA Partners", "work", "-m", "60", "-r", "100",
              "-d", "2026-06-01", "-t", "09:00", cli="hours")
    blocker = vault.home / "a-file"
    blocker.write_text("")
    r = vault.run("statement", "--thread", "SANA Partners", "--pdf", str(blocker / "out" / "s.pdf"),
                  "--as-of", "2026-06-30", cli="payments")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == f"payments: error: cannot create {blocker / 'out'}: Not a directory\n"


def test_a_backdated_payment_refs_into_that_days_log(vault):
    """As for hours: the REF is filed under the day the money arrived, not
    the day the buffer was flushed."""
    vault.write_thread("Projects", "SANA", currency="ZAR")
    vault.run("log", "Projects/SANA", "15000", "-d", "2026-08-04", cli="payments")
    vault.run("flush", cli="buffer")
    logs = sorted(p.name for p in (vault.home / "logs" / "Projects" / "SANA").glob("*.md"))
    assert logs == ["2026-08-04.md"]
    assert re.fullmatch(r"REF: \[\[payments/Projects/SANA\]\] 15000 ZAR received \([0-9a-f]{8}\)",
                        vault.lines("logs/Projects/SANA/2026-08-04.md")[-2])


def test_receipts_are_rounded_to_the_cent_before_they_are_summed(vault):
    """As charges are, so the statement agrees with the receipts `list`
    shows. Two hand-edited receipts of 1.005 list as 1 ZAR each, and used to
    total 2.01 on the statement."""
    vault.write_thread("Projects", "SANA", currency="ZAR", rate=2500)
    vault.run("log", "SANA", "Work", "-m", "60", "-d", "2026-07-01", "-t", "09:00", cli="hours")
    vault.write_payments_file("Projects", "SANA", payments=[
        {"id": "cccc0001", "received": "2026-07-20T08:00:00.000Z", "amount": 1.005, "currency": "ZAR"},
        {"id": "cccc0002", "received": "2026-07-21T08:00:00.000Z", "amount": 1.005, "currency": "ZAR"}])
    assert [line.split()[3] for line in vault.run("list", cli="payments").stdout.splitlines()[1:]] == ["1", "1"]
    assert vault.run("statement", cli="payments").stdout.splitlines()[1].split() == [
        "Projects/SANA", "2500", "ZAR", "2", "ZAR", "2498", "ZAR"]


@needs_pdf
def test_the_pdf_statement_honours_the_window(vault):
    """The window used to reach the text view only, so `--pdf` put a period
    on a client document that was never asked for."""
    sana(vault)
    for day in ("01", "02"):
        vault.run("log", "SANA Partners", f"work {day}", "-m", "60", "-r", "1000",
                  "-d", f"2026-06-{day}", "-t", "09:00", cli="hours")
    vault.run("log", "SANA Partners", "500", "-d", "2026-06-02", cli="payments")
    out = vault.home / "statement.pdf"
    windowed = ["--since", "2026-06-02", "--until", "2026-06-30", "--as-of", "2026-06-30"]

    text = vault.run("statement", "--thread", "SANA Partners", *windowed, "--json", cli="payments")
    assert json.loads(text.stdout) == [{"thread": "Projects/SANA Partners", "currency": "ZAR",
                                        "billed": 1000.0, "received": 500.0, "outstanding": 500.0}]
    r = vault.run("statement", "--thread", "SANA Partners", *windowed, "--pdf", str(out), cli="payments")
    assert r.returncode == 0, r.stderr
    assert r.stdout == (f"{out}: 2 lines, 1.00 h, charges 1000 ZAR, paid 500 ZAR, "
                        "balance 500 ZAR as at 2026-06-30\n")


@needs_pdf
def test_the_pdf_statement_refuses_an_empty_window(vault):
    sana(vault)
    vault.run("log", "SANA Partners", "work", "-m", "60", "-r", "1000",
              "-d", "2026-06-01", "-t", "09:00", cli="hours")
    out = vault.home / "statement.pdf"
    r = vault.run("statement", "--thread", "SANA Partners", "--since", "2030-01-01",
                  "--pdf", str(out), cli="payments")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == ("payments: error: nothing to state for 'Projects/SANA Partners' "
                        f"as at {date.today().isoformat()}\n")
    assert not out.exists()


def test_a_stored_amount_that_is_not_a_number_stops_the_command(vault):
    vault.write_thread("Projects", "Acme", currency="ZAR")
    vault.write_payments_file("Projects", "Acme", payments=[
        {"id": "cccc0001", "received": "2026-07-20T08:00:00.000Z", "amount": "lots", "currency": "ZAR"}])
    for argv in (["list"], ["statement"], ["show", "cccc0001"]):
        r = vault.run(*argv, cli="payments")
        assert (r.returncode, r.stdout) == (1, ""), argv
        assert r.stderr == "payments: error: amount of payment 'cccc0001' must be a number; got 'lots'\n"
