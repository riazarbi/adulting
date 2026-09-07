"""Tests for the `payments` CLI and the statement of account."""

import json


def pay(vault, *argv, **kw):
    return vault.run(*argv, cli="payments", **kw)


def hrs(vault, *argv, **kw):
    return vault.run(*argv, cli="hours", **kw)


# ---- logging ----

def test_log_records_a_payment(vault):
    vault.write_thread("Processes", "Arbi Family Trust", currency="BWP")
    r = pay(vault, "log", "Arbi Family Trust", "47300", "-d", "2023-04-05",
            "-a", "FNB Botswana")
    assert r.returncode == 0, r.stderr
    p = vault.payments("Processes", "Arbi Family Trust")[0]
    assert p["amount"] == 47300
    assert p["currency"] == "BWP"
    assert p["account"] == "FNB Botswana"
    assert len(p["id"]) == 8
    assert p["received"].startswith("2023-04-0")


def test_decimal_amount_is_exact(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    pay(vault, "log", "X", "0.10")
    pay(vault, "log", "X", "0.20")
    out = json.loads(pay(vault, "statement", "--json").stdout)[0]
    assert out["received"] == 0.30      # not 0.30000000000000004


def test_comma_separated_amount_accepted(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    pay(vault, "log", "X", "47,300.50")
    assert vault.payments("Projects", "X")[0]["amount"] == 47300.50


def test_negative_and_zero_amounts_rejected(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    assert pay(vault, "log", "X", "-5").returncode != 0
    assert pay(vault, "log", "X", "0").returncode != 0
    assert pay(vault, "log", "X", "abc").returncode != 0


def test_thread_must_resolve(vault):
    r = pay(vault, "log", "NoSuchThread", "100")
    assert r.returncode != 0
    assert not list((vault.home / "payments").rglob("*.md"))


def test_missing_currency_fails(vault):
    vault.write_thread("Projects", "NoCcy")
    r = pay(vault, "log", "NoCcy", "100")
    assert r.returncode != 0
    assert "currency" in (r.stdout + r.stderr)


def test_interactive_log(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    r = pay(vault, "log", input="1\n1500\n2026-03-01\nFNB\nInvoice 3\n")
    assert r.returncode == 0, r.stderr
    p = vault.payments("Projects", "X")[0]
    assert p["amount"] == 1500
    assert p["account"] == "FNB"
    assert p["note"] == "Invoice 3"


def test_optional_fields_omitted_when_blank(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    pay(vault, "log", "X", "100")
    p = vault.payments("Projects", "X")[0]
    assert "account" not in p and "note" not in p


# ---- statement ----

def test_statement_billed_minus_received(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    hrs(vault, "log", "X", "work", "-m", "120", "-r", "1000")   # 2000 billed
    pay(vault, "log", "X", "750")
    row = json.loads(pay(vault, "statement", "--json").stdout)[0]
    assert row["billed"] == 2000
    assert row["received"] == 750
    assert row["outstanding"] == 1250


def test_statement_agrees_with_hours_report(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    hrs(vault, "log", "X", "a", "-m", "20", "-r", "2500")
    hrs(vault, "log", "X", "b", "-m", "90", "-r", "2500")
    billed_report = json.loads(hrs(vault, "report", "--json").stdout)[0]["amount"]
    billed_stmt = json.loads(pay(vault, "statement", "--json").stdout)[0]["billed"]
    assert billed_report == billed_stmt


def test_statement_never_crosses_currencies(vault):
    vault.write_thread("Projects", "ZA", currency="ZAR")
    vault.write_thread("Processes", "BW", currency="BWP")
    hrs(vault, "log", "ZA", "a", "-m", "60", "-r", "100")
    hrs(vault, "log", "BW", "b", "-m", "60", "-r", "100")
    pay(vault, "log", "ZA", "40")
    text = pay(vault, "statement").stdout
    assert "TOTAL ZAR" in text and "TOTAL BWP" in text
    rows = json.loads(pay(vault, "statement", "--json").stdout)
    assert {r["currency"] for r in rows} == {"ZAR", "BWP"}


def test_statement_shows_billed_thread_with_no_payments(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    hrs(vault, "log", "X", "work", "-m", "60", "-r", "500")
    row = json.loads(pay(vault, "statement", "--json").stdout)[0]
    assert row["billed"] == 500 and row["received"] == 0
    assert row["outstanding"] == 500


def test_statement_shows_payment_with_no_billed_hours(vault):
    """An advance payment must not vanish from the statement."""
    vault.write_thread("Projects", "X", currency="ZAR")
    pay(vault, "log", "X", "1000")
    row = json.loads(pay(vault, "statement", "--json").stdout)[0]
    assert row["billed"] == 0 and row["received"] == 1000
    assert row["outstanding"] == -1000


def test_statement_date_window(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    pay(vault, "log", "X", "100", "-d", "2026-01-01")
    pay(vault, "log", "X", "200", "-d", "2026-06-01")
    row = json.loads(pay(vault, "statement", "--since", "2026-05-01",
                         "--json").stdout)[0]
    assert row["received"] == 200


# ---- edit / rm / show ----

def test_edit_amount_and_note(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    pay(vault, "log", "X", "100")
    pid = vault.payments("Projects", "X")[0]["id"]
    pay(vault, "edit", pid, "--amount", "250.75", "-n", "corrected", "figure")
    shown = json.loads(pay(vault, "show", pid, "--json").stdout)
    assert shown["amount"] == 250.75
    assert shown["note"] == "corrected figure"


def test_rm_removes_payment(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    pay(vault, "log", "X", "100")
    pid = vault.payments("Projects", "X")[0]["id"]
    assert pay(vault, "rm", pid, "-y").returncode == 0
    assert vault.payments("Projects", "X") == []


def test_payments_sorted_by_received(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    pay(vault, "log", "X", "1", "-d", "2026-06-01")
    pay(vault, "log", "X", "2", "-d", "2026-01-01")
    amounts = [p["amount"] for p in vault.payments("Projects", "X")]
    assert amounts == [2, 1]


# ---- ids are unique across both tools ----

def test_ids_do_not_collide_with_hours(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    for i in range(10):
        hrs(vault, "log", "X", f"h{i}")
        pay(vault, "log", "X", str(100 + i))
    ids = ([e["id"] for e in vault.entries("Projects", "X")] +
           [p["id"] for p in vault.payments("Projects", "X")])
    assert len(ids) == 20
    assert len(set(ids)) == 20


# ---- lint ----

def test_valid_payments_file_lints_clean(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    p = vault.write_payments_file("Projects", "X", [{
        "id": "a1b2c3d4", "received": "2026-04-05T07:00:00.000Z",
        "amount": 47300, "currency": "ZAR", "account": "FNB Botswana"}])
    assert vault.run(str(p), cli="lint").returncode == 0


def test_lint_flags_missing_payment_field(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    p = vault.write_payments_file("Projects", "X", [{
        "id": "a1b2c3d4", "received": "2026-04-05T07:00:00.000Z",
        "currency": "ZAR"}])
    r = vault.run(str(p), cli="lint")
    assert r.returncode == 1
    assert "payments[0].amount: missing" in r.stdout


def test_lint_flags_non_positive_amount(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    p = vault.write_payments_file("Projects", "X", [{
        "id": "a1b2c3d4", "received": "2026-04-05T07:00:00.000Z",
        "amount": -5, "currency": "ZAR"}])
    r = vault.run(str(p), cli="lint")
    assert r.returncode == 1
    assert "must be positive" in r.stdout


def test_lint_flags_id_shared_with_an_hours_entry(vault):
    """One id namespace across both tools."""
    vault.write_thread("Projects", "X", currency="ZAR")
    vault.write_hours_file("Projects", "X", [{
        "name": "w", "startTime": "2026-04-05T07:00:00.000Z",
        "endTime": "2026-04-05T08:00:00.000Z", "id": "a1b2c3d4",
        "rate": 100, "currency": "ZAR"}])
    vault.write_payments_file("Projects", "X", [{
        "id": "a1b2c3d4", "received": "2026-04-05T07:00:00.000Z",
        "amount": 100, "currency": "ZAR"}])
    r = vault.run(cli="lint")
    assert r.returncode == 1
    assert "duplicated at" in r.stdout


def test_lint_walks_payments_dir(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    vault.write_payments_file("Projects", "X", [{
        "id": "ZZZZ", "received": "2026-04-05T07:00:00.000Z",
        "amount": 1, "currency": "ZAR"}])
    r = vault.run(cli="lint")
    assert r.returncode == 1
    assert "payments/Projects/X.md" in r.stdout
