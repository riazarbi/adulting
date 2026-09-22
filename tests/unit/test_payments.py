"""Unit tests for adulting.payments. conftest points ADULTING_HOME at tmp_path/vault."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from adulting import payments as P


def test_parse_amount():
    assert P.parse_amount("47,300.50") == Decimal("47300.50")
    assert P.parse_amount(" 12 ") == Decimal("12")
    for bad in ("abc", "0", "-1", None):
        with pytest.raises(SystemExit):
            P.parse_amount(bad)


def test_amount_json_drops_pointless_cents():
    assert P.amount_json(Decimal("45000.00")) == 45000
    assert isinstance(P.amount_json(Decimal("45000.00")), int)
    assert P.amount_json(Decimal("0.105")) == 0.1  # quantized to cents (banker's rounding)
    assert P.amount_json(Decimal("10.5")) == 10.5


def test_build_payment_omits_blank_optional_fields():
    when = datetime(2026, 7, 10, 8, 0).astimezone()
    full = P.build_payment(Decimal("100"), when, "ZAR", "FNB", "Inv 1", set())
    assert (full["account"], full["note"], full["amount"]) == ("FNB", "Inv 1", 100)
    bare = P.build_payment(Decimal("100"), when, "ZAR", "", "", set())
    assert "account" not in bare and "note" not in bare


def test_as_of():
    assert P._as_of(None) == date.today()
    assert P._as_of("2026-06-30") == date(2026, 6, 30)
    with pytest.raises(SystemExit):
        P._as_of("30 June")


@pytest.fixture
def vault_with_records():
    home = P.V.vault_home()
    for rel, extra in (("Projects/SANA", "currency: ZAR\n"), ("Topics/Wellness", "")):
        (home / "threads" / f"{rel}.md").parent.mkdir(parents=True, exist_ok=True)
        (home / "threads" / f"{rel}.md").write_text(f"---\nstatus: open\n{extra}---\n")
    P.V.write_records(home / "hours" / "Projects" / "SANA.md", [
        {"name": "Work", "startTime": "2026-07-01T07:00:00.000Z",
         "endTime": "2026-07-01T07:20:00.000Z", "id": "aaaa0001", "rate": 2500, "currency": "ZAR"},
        {"name": "Later", "startTime": "2026-08-01T07:00:00.000Z",
         "endTime": "2026-08-01T08:00:00.000Z", "id": "aaaa0002", "rate": 1000, "currency": "ZAR"},
    ], P.HOURS_FENCE, "Projects/SANA", "ZAR")
    P.V.write_records(home / "hours" / "Topics" / "Wellness.md", [
        {"name": "Run", "startTime": "2026-07-01T05:00:00.000Z",
         "endTime": "2026-07-01T06:00:00.000Z", "id": "aaaa0003", "rate": 0},
    ], P.HOURS_FENCE, "Topics/Wellness", None)
    P.V.write_records(home / "payments" / "Projects" / "SANA.md", [
        {"id": "bbbb0001", "received": "2026-07-10T08:00:00.000Z", "amount": 500.5,
         "currency": "ZAR", "account": "FNB"},
    ], P.FENCE, "Projects/SANA", "ZAR", key=P.KEY)
    return home


def test_billed_rounds_each_entry_and_skips_unbilled_time(vault_with_records):
    assert P.billed() == {("Projects/SANA", "ZAR"): Decimal("1833.33")}
    assert P.billed(until="2026-07-31") == {("Projects/SANA", "ZAR"): Decimal("833.33")}


def test_collect_and_find_payment(vault_with_records):
    [(_, ref, p)] = list(P.collect("SANA"))
    assert (ref, p["id"]) == ("Projects/SANA", "bbbb0001")
    assert list(P.collect(since="2026-07-11")) == []
    assert P.as_row(ref, p)["amount"] == 500.5
    with pytest.raises(SystemExit):
        P.find_payment("deadbeef")


def test_one_thread_statement(vault_with_records):
    st = P.one_thread_statement("SANA", date(2026, 7, 31))
    assert st["currency"] == "ZAR"
    assert st["payments"] == Decimal("500.50")
    assert st["thread_path"].name == "SANA.md"


def test_the_pdf_statement_charges_only_the_threads_currency(vault_with_records):
    """Unbilled time and time billed in another currency have no place on a
    ZAR statement of account. The PDF used to list both and charge the USD
    entry as ZAR."""
    path = vault_with_records / "hours" / "Projects" / "SANA.md"
    records = P.V.read_records(path, P.HOURS_FENCE) + [
        {"name": "Unbilled reading", "startTime": "2026-07-02T07:00:00.000Z",
         "endTime": "2026-07-02T08:00:00.000Z", "id": "aaaa0004", "rate": 0},
        {"name": "USD work", "startTime": "2026-07-03T07:00:00.000Z",
         "endTime": "2026-07-03T08:00:00.000Z", "id": "aaaa0005", "rate": 100, "currency": "USD"},
    ]
    P.V.write_records(path, records, P.HOURS_FENCE, "Projects/SANA", "ZAR")
    st = P.one_thread_statement("SANA", date(2026, 7, 31))
    assert [line["description"] for line in st["lines"]] == ["Work", "Payment received — FNB"]
    assert st["charges"] == Decimal("833.33")
    assert st["balance"] == Decimal("332.83")
