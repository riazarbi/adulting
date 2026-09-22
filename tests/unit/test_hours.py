"""Unit tests for adulting.hours. conftest points ADULTING_HOME at tmp_path/vault."""

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
def threads():
    home = H.V.vault_home()
    t = home / "threads"
    for rel, extra in (("Projects/SANA", "currency: zar\nrate: 2500\n"),
                       ("Processes/Trust", "currency: BWP\n"),
                       ("Topics/Wellness", "")):
        (t / f"{rel}.md").parent.mkdir(parents=True, exist_ok=True)
        (t / f"{rel}.md").write_text(f"---\nstatus: open\n{extra}---\n")
    return t


def test_resolve_rate_cascade(threads):
    assert H.resolve_rate(threads / "Projects/SANA.md", None) == 2500
    assert H.resolve_rate(threads / "Projects/SANA.md", 900) == 900
    assert H.resolve_rate(threads / "Processes/Trust.md", None) == H.DEFAULT_RATE
    (H.V.vault_home() / ".adulting").mkdir(parents=True, exist_ok=True)
    (H.V.vault_home() / ".adulting" / "config.yaml").write_text("hours:\n  rate: 1800\n")
    assert H.resolve_rate(threads / "Processes/Trust.md", None) == 1800


def test_resolve_billing(threads):
    assert H.resolve_billing(threads / "Projects/SANA.md", None, None) == ("ZAR", 2500)
    assert H.resolve_billing(threads / "Topics/Wellness.md", None, None) == (None, 0)
    assert H.resolve_billing(threads / "Topics/Wellness.md", None, 0) == (None, 0)
    assert H.resolve_billing(threads / "Topics/Wellness.md", "gbp", 10) == ("GBP", 10)
    with pytest.raises(SystemExit):
        H.resolve_billing(threads / "Topics/Wellness.md", None, 900)
    with pytest.raises(SystemExit):
        H.resolve_billing(threads / "Topics/Wellness.md", "rands", None)


def test_append_collect_and_find(threads, monkeypatch):
    monkeypatch.setenv("TZ", "UTC")
    import time
    time.tzset()
    try:
        H.append_entry("project", "SANA", entry(id="aaaa0001"))
        H.append_entry("project", "SANA", entry(start="2026-08-02T07:00:00.000Z",
                                                end="2026-08-02T08:00:00.000Z", id="aaaa0002"))
        ids = [e["id"] for _, _, e in H.collect()]
        assert ids == ["aaaa0002", "aaaa0001"]  # the file is kept sorted by start
        assert [e["id"] for _, _, e in H.collect(since="2026-08-03")] == ["aaaa0001"]
        path, ref, e = H.find_entry("aaaa0001")
        assert (path.name, ref) == ("SANA.md", "Projects/SANA")
        assert H.as_row(ref, e)["amount"] == 3750.0
        with pytest.raises(SystemExit):
            H.find_entry("deadbeef")
    finally:
        monkeypatch.undo()
        time.tzset()
