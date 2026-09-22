"""Unit tests for adulting.hours. conftest points ADULTING_HOME at tmp_path/vault."""

import os
import time
from datetime import datetime
from decimal import Decimal

import pytest

from adulting import hours as H


def entry(start="2026-08-04T07:00:00.000Z", end="2026-08-04T08:30:00.000Z", **over):
    e = {"name": "x", "startTime": start, "endTime": end, "id": "abcd1234", "rate": 2500}
    e.update(over)
    return e


def test_money_of_is_a_decimal_rounded_to_the_cent():
    assert H.money_of(entry(end="2026-08-04T07:20:00.000Z", rate=2500)) == Decimal("833.33")
    assert H.money_of(entry(end="2026-08-04T07:40:00.000Z", rate=2500)) == Decimal("1666.67")
    assert H.money_of(entry(rate=0)) == Decimal("0.00")


def test_build_entry_omits_currency_for_unbilled_time():
    when = datetime(2026, 8, 4, 9, 0).astimezone()
    billed = H.build_entry("Work", when, 45, 1800, "ZAR", set())
    assert billed["currency"] == "ZAR" and billed["rate"] == 1800
    assert H.V.minutes_of(billed) == 45
    unbilled = H.build_entry("Run", when, 30, 0, None, set())
    assert "currency" not in unbilled


@pytest.fixture
def billing_threads():
    home = H.V.vault_home()
    t = home / "threads"
    for rel, extra in (("Projects/SANA", "currency: zar\nrate: 2500\n"),
                       ("Processes/Trust", "currency: BWP\n"),
                       ("Topics/Wellness", "")):
        (t / f"{rel}.md").parent.mkdir(parents=True, exist_ok=True)
        (t / f"{rel}.md").write_text(f"---\nstatus: open\n{extra}---\n")
    return t


def test_resolve_rate_cascade(billing_threads):
    assert H.resolve_rate(billing_threads / "Projects/SANA.md", None) == 2500
    assert H.resolve_rate(billing_threads / "Projects/SANA.md", 900) == 900
    assert H.resolve_rate(billing_threads / "Processes/Trust.md", None) == H.DEFAULT_RATE
    (H.V.vault_home() / ".adulting").mkdir(parents=True, exist_ok=True)
    (H.V.vault_home() / ".adulting" / "config.yaml").write_text("hours:\n  rate: 1800\n")
    assert H.resolve_rate(billing_threads / "Processes/Trust.md", None) == 1800


def test_resolve_billing(billing_threads):
    assert H.resolve_billing(billing_threads / "Projects/SANA.md", None, None) == ("ZAR", 2500)
    assert H.resolve_billing(billing_threads / "Topics/Wellness.md", None, None) == (None, 0)
    assert H.resolve_billing(billing_threads / "Topics/Wellness.md", None, 0) == (None, 0)
    assert H.resolve_billing(billing_threads / "Topics/Wellness.md", "gbp", 10) == ("GBP", 10)
    with pytest.raises(SystemExit):
        H.resolve_billing(billing_threads / "Topics/Wellness.md", None, 900)
    with pytest.raises(SystemExit):
        H.resolve_billing(billing_threads / "Topics/Wellness.md", "rands", None)


@pytest.fixture
def utc():
    """Local time is UTC for the test, so local dates equal the stored ones."""
    old = os.environ.get("TZ")
    os.environ["TZ"] = "UTC"
    time.tzset()
    yield
    if old is None:
        del os.environ["TZ"]
    else:
        os.environ["TZ"] = old
    time.tzset()


@pytest.fixture
def appended(billing_threads, utc):
    """Two SANA entries, appended newest first."""
    H.append_entry("project", "SANA", entry(id="aaaa0001"))
    H.append_entry("project", "SANA", entry(start="2026-08-02T07:00:00.000Z",
                                            end="2026-08-02T08:00:00.000Z", id="aaaa0002"))


def test_append_keeps_the_file_sorted_by_start(appended):
    assert [e["id"] for _, _, e in H.collect()] == ["aaaa0002", "aaaa0001"]


def test_collect_filters_by_date(appended):
    assert [e["id"] for _, _, e in H.collect(since="2026-08-03")] == ["aaaa0001"]
    assert [e["id"] for _, _, e in H.collect(until="2026-08-02")] == ["aaaa0002"]


def test_find_entry_returns_its_file_and_thread(appended):
    path, ref, e = H.find_entry("aaaa0001")
    assert (path.name, ref, e["id"]) == ("SANA.md", "Projects/SANA", "aaaa0001")


def test_find_entry_refuses_an_unknown_id(appended, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["hours"])
    with pytest.raises(SystemExit) as exc:
        H.find_entry("deadbeef")
    assert exc.value.code == 1
    assert capsys.readouterr().err == "hours: error: no entry with id 'deadbeef'\n"


def test_as_row_charges_the_entry(appended):
    _, ref, e = H.find_entry("aaaa0001")
    assert H.as_row(ref, e)["amount"] == Decimal("3750.00")
