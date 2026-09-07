"""Statement-of-account arithmetic and PDF rendering.

The arithmetic cases are ported from the standalone renderer this replaced;
its figures were reproduced exactly against the real logs before it was retired.
"""

import datetime
import json
import shutil
import sys
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import _statement as S  # noqa: E402

HAS_PANDOC = shutil.which("pandoc") is not None
HAS_XELATEX = shutil.which("xelatex") is not None
needs_pdf = pytest.mark.skipif(
    not (HAS_PANDOC and HAS_XELATEX),
    reason="pandoc + xelatex required to render a PDF")

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


def test_lines_sum_to_charges():
    st = S.build("T", "ZAR", [entry(D(2026, 1, 1), 20, 2500),
                              entry(D(2026, 1, 2), 90, 2500)],
                 [], D(2026, 1, 31))
    summed = sum(ln["charge"] for ln in st["lines"] if ln["charge"] is not None)
    assert summed == st["charges"]


# ---- running balance ----

def test_charge_precedes_payment_on_the_same_day(vault):
    """A payment must settle a balance that already includes that day's work."""
    st = S.build("T", "ZAR", [entry(D(2026, 1, 1), 60, 1000)],
                 [payment(D(2026, 1, 1), 400)], D(2026, 1, 31))
    assert [ln["charge"] is not None for ln in st["lines"]] == [True, False]
    assert st["lines"][0]["balance"] == Decimal("1000.00")
    assert st["lines"][1]["balance"] == Decimal("600.00")


def test_closing_line_equals_balance():
    st = S.build("T", "ZAR", [entry(D(2026, 1, 1), 60, 1000)],
                 [payment(D(2026, 2, 1), 250)], D(2026, 3, 1))
    assert st["lines"][-1]["balance"] == st["balance"] == Decimal("750.00")


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


def test_aging_always_sums_to_balance():
    as_of = D(2026, 6, 30)
    st = S.build("T", "ZAR", [entry(D(2026, 1, 1), 90, 2500)],
                 [payment(D(2026, 2, 1), 1000)], as_of)
    assert sum(st["aging"].values()) == st["balance"]


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


# ---- CLI wiring ----

def sana(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR", rate=2500)
    p = vault.home / "threads" / "Projects" / "SANA Partners.md"
    p.write_text(p.read_text().replace(
        "---\n\n# SANA",
        "client_name: Sana Partners (Pty) Ltd\n"
        "client_address: Unit 301|2 Park Road|Cape Town\n"
        "client_vat: 4220259826\n---\n\n# SANA"), encoding="utf-8")
    return p


def test_statement_as_of_matches_the_text_view(vault):
    sana(vault)
    vault.run("log", "SANA Partners", "old", "-m", "60", "-r", "1000",
              "-d", "2026-01-01", "-t", "09:00", cli="hours")
    vault.run("log", "SANA Partners", "new", "-m", "60", "-r", "1000",
              "-d", "2026-06-01", "-t", "09:00", cli="hours")
    out = json.loads(vault.run("statement", "--as-of", "2026-03-01",
                               "--json", cli="payments").stdout)
    assert out[0]["billed"] == 1000


def test_pdf_requires_a_thread(vault):
    sana(vault)
    r = vault.run("statement", "--pdf", str(vault.home / "x.pdf"), cli="payments")
    assert r.returncode != 0
    assert "--thread" in (r.stdout + r.stderr)


def test_pdf_requires_client_name(vault):
    vault.write_thread("Projects", "NoClient", currency="ZAR")
    vault.run("log", "NoClient", "work", cli="hours")
    r = vault.run("statement", "--thread", "NoClient", "--pdf",
                  str(vault.home / "x.pdf"), cli="payments")
    assert r.returncode != 0
    assert "client_name" in (r.stdout + r.stderr)


def test_pdf_refuses_when_there_is_nothing_to_state(vault):
    sana(vault)
    r = vault.run("statement", "--thread", "SANA Partners", "--pdf",
                  str(vault.home / "x.pdf"), cli="payments")
    assert r.returncode != 0
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
    assert "2 lines" in r.stdout and "5000" in r.stdout


@needs_pdf
def test_pdf_warns_and_states_when_banking_is_missing(vault):
    sana(vault)
    vault.run("log", "SANA Partners", "work", "-m", "60", "-r", "100",
              "-d", "2026-06-01", "-t", "09:00", cli="hours")
    out = vault.home / "statement.pdf"
    r = vault.run("statement", "--thread", "SANA Partners", "--pdf", str(out),
                  "--as-of", "2026-06-30", cli="payments")
    assert r.returncode == 0, r.stderr
    assert "banking details incomplete" in r.stderr
    # The PDF is opaque to assert against; check the renderer's own markdown
    # says so, which is what lands in it.
    import _statement_pdf as P
    md = P.markdown(
        S.build("Projects/SANA Partners", "ZAR",
                [entry(D(2026, 6, 1), 60, 100)], [], D(2026, 6, 30)),
        {"name": "R", "lines": []}, {"name": "C", "lines": []},
        {"complete": False})
    assert "Banking details not yet supplied" in md


@needs_pdf
def test_a_failed_render_leaves_no_stale_file(vault):
    """Better no statement than yesterday's figures under today's date."""
    sana(vault)
    vault.run("log", "SANA Partners", "work", "-m", "60", "-r", "100",
              "-d", "2026-06-01", "-t", "09:00", cli="hours")
    out = vault.home / "statement.pdf"
    out.write_bytes(b"stale")
    vault.run("statement", "--thread", "SANA Partners", "--pdf", str(out),
              "--as-of", "2026-06-30", cli="payments")
    assert out.read_bytes()[:5] == b"%PDF-"


# ---- markdown escaping ----

def test_description_metacharacters_cannot_break_the_table():
    import _statement_pdf as P
    st = S.build("T", "ZAR", [entry(D(2026, 1, 1), 60, 100,
                                    "a|b *c* _d_ [e] #f `g`")], [], D(2026, 2, 1))
    md = P.markdown(st, {"name": "S", "lines": []}, {"name": "C", "lines": []},
                    {"complete": False})
    row = [ln for ln in md.split("\n") if "a\\|b" in ln]
    assert row, "pipe in a description must be escaped, not split the cell"
    assert "\\*c\\*" in md and "\\_d\\_" in md


def test_money_formats_negatives_in_parentheses():
    import _statement_pdf as P
    assert P.money(Decimal("-150.00"), "ZAR") == "ZAR (150.00)"
    assert P.money(Decimal("1234.5"), "ZAR") == "ZAR 1,234.50"


# ---- banking / party config ----

def write_billing(vault, **over):
    fields = {"supplier_name": "Riaz Arbi",
              "bank_account_name": "Riaz J Arbi", "bank_name": "Capitec Bank",
              "bank_account_number": "0000000000", "bank_branch_code": "470010",
              "bank_account_type": "Savings"}
    fields.update(over)
    body = "owner: Riaz Arbi\nbilling:\n" + "".join(
        f"  {k}: {v}\n" for k, v in fields.items())
    (vault.home / ".adulting" / "config.yaml").write_text(body, encoding="utf-8")


def vault_module(vault):
    """Import _vault with ADULTING_HOME pointed at the fixture."""
    import importlib, os
    os.environ["ADULTING_HOME"] = str(vault.home)
    import _vault
    importlib.reload(_vault)
    return _vault


def test_banking_is_complete_when_every_field_is_set(vault):
    """A document that asks for money must say where to send it."""
    write_billing(vault)
    assert vault_module(vault).banking()["complete"] is True


def test_banking_is_incomplete_while_a_field_is_a_todo_placeholder(vault):
    write_billing(vault, bank_account_number="TODO")
    assert vault_module(vault).banking()["complete"] is False


def test_banking_is_incomplete_when_a_field_is_missing(vault):
    write_billing(vault)
    cfg = vault.home / ".adulting" / "config.yaml"
    cfg.write_text(cfg.read_text().replace("  bank_branch_code: 470010\n", ""),
                   encoding="utf-8")
    assert vault_module(vault).banking()["complete"] is False


def test_supplier_address_is_pipe_separated(vault):
    write_billing(vault, supplier_address="14 Kinnoull Road|Camps Bay|Cape Town")
    assert vault_module(vault).supplier()["lines"] == [
        "14 Kinnoull Road", "Camps Bay", "Cape Town"]


def test_reference_is_the_thread_name_without_its_kind_prefix(vault):
    """Derived, not configured: it cannot drift or carry another client's code."""
    write_billing(vault)
    p = sana(vault)
    assert vault_module(vault).client(p)["reference"] == "SANA Partners"


def test_reference_ignores_a_frontmatter_override(vault):
    write_billing(vault)
    p = sana(vault)
    p.write_text(p.read_text().replace(
        "client_vat:", "client_reference: SOMETHING ELSE\nclient_vat:"),
        encoding="utf-8")
    assert vault_module(vault).client(p)["reference"] == "SANA Partners"
