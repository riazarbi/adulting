"""Statement-of-account arithmetic, and the markdown the PDF is made from.

The arithmetic cases are ported from the standalone renderer this replaced;
its figures were reproduced exactly against the real logs before it was retired.
"""

import datetime
from decimal import Decimal

import pytest

from adulting import statement as S
from adulting import statement_pdf as P

D = datetime.date


def entry(on, minutes, rate, description="work"):
    return {"on": on, "minutes": minutes, "rate": rate, "description": description}


def payment(on, amount, account="Bank"):
    return {"on": on, "amount": Decimal(str(amount)), "account": account}


# ---- charge rounding ----


def test_charge_lands_on_whole_cents():
    # 20 minutes at 2500/h is 833.333...; the line must be exact cents so the
    # printed lines sum to the printed total.
    assert S.charge_of(20, 2500) == Decimal("833.33")



# ---- running balance ----


def test_charge_precedes_payment_on_the_same_day():
    """A payment must settle a balance that already includes that day's work."""
    st = S.build("T", "ZAR", [entry(D(2026, 1, 1), 60, 1000)],
                 [payment(D(2026, 1, 1), 400)], D(2026, 1, 31))
    assert [ln["charge"] is not None for ln in st["lines"]] == [True, False]
    assert st["lines"][0]["balance"] == Decimal("1000.00")
    assert st["lines"][1]["balance"] == Decimal("600.00")



def test_payment_description_carries_the_account():
    st = S.build("T", "ZAR", [], [payment(D(2026, 1, 1), 10, "FNB Botswana")],
                 D(2026, 1, 31))
    assert "FNB Botswana" in st["lines"][0]["description"]


# ---- as-of ----


def test_as_of_excludes_later_work():
    """Work logged after the statement date has not happened yet."""
    st = S.build("T", "ZAR", [entry(D(2026, 1, 1), 60, 1000),
                              entry(D(2026, 6, 1), 60, 1000)],
                 [], D(2026, 3, 1))
    assert len(st["lines"]) == 1
    assert st["charges"] == Decimal("1000.00")


def test_as_of_excludes_later_payments():
    st = S.build("T", "ZAR", [entry(D(2026, 1, 1), 60, 1000)],
                 [payment(D(2026, 6, 1), 1000)], D(2026, 3, 1))
    assert st["payments"] == Decimal("0.00")
    assert st["balance"] == Decimal("1000.00")


# ---- aging ----


def test_aging_buckets_by_age():
    as_of = D(2026, 6, 30)
    st = S.build("T", "ZAR", [
        entry(as_of - datetime.timedelta(days=5), 60, 100),     # current
        entry(as_of - datetime.timedelta(days=40), 60, 100),    # 30
        entry(as_of - datetime.timedelta(days=70), 60, 100),    # 60
        entry(as_of - datetime.timedelta(days=200), 60, 100),   # 90+
    ], [], as_of)
    assert st["aging"] == {"current": Decimal("100.00"), "30": Decimal("100.00"),
                           "60": Decimal("100.00"), "90+": Decimal("100.00")}


def test_aging_settles_oldest_charges_first():
    as_of = D(2026, 6, 30)
    st = S.build("T", "ZAR", [
        entry(as_of - datetime.timedelta(days=200), 60, 100),
        entry(as_of - datetime.timedelta(days=5), 60, 100),
    ], [payment(as_of, 100)], as_of)
    assert st["aging"]["90+"] == Decimal("0.00")     # oldest cleared
    assert st["aging"]["current"] == Decimal("100.00")



def test_overpayment_shows_as_negative_current_not_an_aged_debt():
    as_of = D(2026, 6, 30)
    st = S.build("T", "ZAR", [entry(D(2026, 1, 1), 60, 100)],
                 [payment(D(2026, 2, 1), 250)], as_of)
    assert st["balance"] == Decimal("-150.00")
    assert st["aging"]["current"] == Decimal("-150.00")
    assert sum(st["aging"].values()) == st["balance"]


# ---- written-off hours ----


def test_rate_zero_counts_hours_but_not_money():
    st = S.build("T", "ZAR", [entry(D(2026, 1, 1), 120, 0),
                              entry(D(2026, 1, 2), 60, 1000)],
                 [], D(2026, 2, 1))
    assert st["hours_total"] == Decimal(3)
    assert st["hours_billable"] == Decimal(1)
    assert st["hours_written_off"] == Decimal(2)
    assert st["charges"] == Decimal("1000.00")


# ---- markdown escaping ----


def test_description_metacharacters_cannot_break_the_table():
    st = S.build("T", "ZAR", [entry(D(2026, 1, 1), 60, 100,
                                    "a|b *c* _d_ [e] #f `g`")], [], D(2026, 2, 1))
    md = P.markdown(st, {"name": "S", "lines": []}, {"name": "C", "lines": []},
                    {"complete": False})
    row = [ln for ln in md.split("\n") if "a\\|b" in ln]
    assert row, "pipe in a description must be escaped, not split the cell"
    assert "\\*c\\*" in md and "\\_d\\_" in md


def test_money_formats_negatives_in_parentheses():
    assert P.money(Decimal("-150.00"), "ZAR") == "ZAR (150.00)"
    assert P.money(Decimal("1234.5"), "ZAR") == "ZAR 1,234.50"


def test_markdown_says_so_when_banking_details_are_missing():
    st = S.build("Projects/SANA Partners", "ZAR", [entry(D(2026, 6, 1), 60, 100)], [], D(2026, 6, 30))
    md = P.markdown(st, {"name": "R", "lines": []}, {"name": "C", "lines": []}, {"complete": False})
    assert "Banking details not yet supplied" in md


def test_check_refuses_a_statement_that_does_not_add_up(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["payments"])
    d = Decimal
    good = {"lines": [{"balance": d("100.00"), "charge": d("100.00"),
                       "payment": None, "hours": d("1.00")}],
            "balance": d("100.00"), "charges": d("100.00"), "payments": d("0.00"),
            "hours_total": d("1.00"),
            "aging": {"current": d("100.00"), "30": d("0.00"), "60": d("0.00"), "90+": d("0.00")}}
    S.check(good)  # returns without exiting
    for bad, message in (
            ({"balance": d("90.00"), "aging": {"current": d("90.00")}},
             "closing line 100.00 != balance 90.00"),
            ({"aging": {"current": d("50.00")}}, "aging 50.00 != balance 100.00"),
            ({"charges": d("80.00")}, "lines charge 100.00 != charges 80.00")):
        with pytest.raises(SystemExit) as exc:
            S.check({**good, **bad})
        assert exc.value.code == 1
        assert capsys.readouterr().err == f"payments: error: statement check failed: {message}\n"


def test_hours_are_rounded_per_line_so_the_column_adds_up():
    """As charges are. Three 50-minute entries print 0.83 three times, so
    the total is 2.49, not the unrounded 2.50."""
    st = S.build("T", "ZAR", [entry(D(2026, 1, day), 50, 100) for day in (1, 2, 3)],
                 [], D(2026, 1, 31))
    assert [ln["hours"] for ln in st["lines"]] == [Decimal("0.83")] * 3
    assert st["hours_total"] == Decimal("2.49")
    assert st["hours_billable"] == Decimal("2.49")


def test_written_off_hours_are_rounded_the_same_way():
    st = S.build("T", "ZAR", [entry(D(2026, 1, 1), 50, 0), entry(D(2026, 1, 2), 50, 100)],
                 [], D(2026, 1, 31))
    assert (st["hours_total"], st["hours_billable"], st["hours_written_off"]) == (
        Decimal("1.66"), Decimal("0.83"), Decimal("0.83"))


def test_check_refuses_lines_whose_hours_do_not_sum(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["payments"])
    st = S.build("T", "ZAR", [entry(D(2026, 1, 1), 50, 100)], [], D(2026, 1, 31))
    with pytest.raises(SystemExit):
        S.check({**st, "hours_total": Decimal("9.99")})
    assert capsys.readouterr().err == (
        "payments: error: statement check failed: lines hours 0.83 != hours 9.99\n")


def test_check_refuses_payments_that_do_not_sum(monkeypatch, capsys):
    """The round 2 receipts bug in one assertion, so a future caller cannot
    reintroduce it in silence."""
    monkeypatch.setattr("sys.argv", ["payments"])
    st = S.build("T", "ZAR", [], [payment(D(2026, 1, 1), 10)], D(2026, 1, 31))
    with pytest.raises(SystemExit):
        S.check({**st, "payments": Decimal("9.99")})
    assert capsys.readouterr().err == (
        "payments: error: statement check failed: lines payment 10.00 != payments 9.99\n")
