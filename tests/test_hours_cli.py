"""Tests for the `hours` CLI — acceptance criteria from
stories/2026-09-07-hours-time-tracking.md."""

import json


def run(vault, *argv, **kw):
    return vault.run(*argv, cli="hours", **kw)


# ---- 1. logging ----

def test_log_writes_entry_and_prints_id(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    r = run(vault, "log", "SANA Partners", "test", "-m", "90", "-r", "2500")
    assert r.returncode == 0, r.stderr
    entries = vault.entries("Projects", "SANA Partners")
    assert len(entries) == 1
    e = entries[0]
    assert e["name"] == "test"
    assert e["rate"] == 2500
    assert e["currency"] == "ZAR"
    assert len(e["id"]) == 8
    assert e["id"] in r.stdout
    # 90 minutes must be expressed as a start/end interval
    assert e["startTime"].endswith("Z") and e["endTime"].endswith("Z")


def test_log_defaults_are_60_minutes_and_2500(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    run(vault, "log", "SANA Partners", "default sized")
    e = vault.entries("Projects", "SANA Partners")[0]
    assert e["rate"] == 2500
    r = run(vault, "show", e["id"], "--json")
    assert json.loads(r.stdout)["minutes"] == 60


def test_log_uses_thread_rate_over_vault_default(vault):
    vault.write_thread("Projects", "Cheap", currency="ZAR", rate=800)
    run(vault, "log", "Cheap", "discounted")
    assert vault.entries("Projects", "Cheap")[0]["rate"] == 800


def test_flag_rate_beats_thread_rate(vault):
    vault.write_thread("Projects", "Cheap", currency="ZAR", rate=800)
    run(vault, "log", "Cheap", "override", "-r", "4000")
    assert vault.entries("Projects", "Cheap")[0]["rate"] == 4000


# ---- 2. threads must resolve ----

def test_unresolvable_thread_fails_and_writes_nothing(vault):
    r = run(vault, "log", "NoSuchThread", "x")
    assert r.returncode != 0
    assert not (vault.home / "hours" / "Projects").exists() or \
        not list((vault.home / "hours").rglob("*.md"))


def test_ambiguous_thread_fails(vault):
    vault.write_thread("Projects", "Dup", currency="ZAR")
    vault.write_thread("Processes", "Dup", currency="ZAR")
    r = run(vault, "log", "Dup", "x")
    assert r.returncode != 0
    assert "ambiguous" in (r.stdout + r.stderr).lower()


def test_qualified_path_disambiguates(vault):
    vault.write_thread("Projects", "Dup", currency="ZAR")
    vault.write_thread("Processes", "Dup", currency="ZAR")
    r = run(vault, "log", "Processes/Dup", "x")
    assert r.returncode == 0, r.stderr
    assert len(vault.entries("Processes", "Dup")) == 1


def test_thread_resolution_is_case_sensitive(vault):
    """The Arbi family trust bug: case folding must not come from the FS."""
    vault.write_thread("Processes", "Arbi Family Trust", currency="BWP")
    r = run(vault, "log", "Arbi family trust", "x")
    assert r.returncode != 0


# ---- 3. interactive parity ----

def test_interactive_log_matches_noninteractive(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    r = run(vault, "log", input="1\nSecond close\n180\n\n")
    assert r.returncode == 0, r.stderr
    e = vault.entries("Projects", "SANA Partners")[0]
    assert e["name"] == "Second close"
    assert e["rate"] == 2500
    assert json.loads(run(vault, "show", e["id"], "--json").stdout)["minutes"] == 180


def test_interactive_lists_only_open_threads(vault):
    vault.write_thread("Projects", "Open One", currency="ZAR")
    vault.write_thread("Projects", "Shut", status="closed", currency="ZAR")
    r = run(vault, "log", input="1\nx\n\n\n")
    assert "Open One" in r.stdout
    assert "Shut" not in r.stdout


# ---- 4. currency is never guessed ----

def test_missing_currency_fails_with_remediation(vault):
    vault.write_thread("Projects", "NoCcy")
    r = run(vault, "log", "NoCcy", "x")
    assert r.returncode != 0
    out = r.stdout + r.stderr
    assert "currency" in out
    assert "threads/Projects/NoCcy.md" in out


def test_currency_flag_satisfies_missing_thread_currency(vault):
    vault.write_thread("Projects", "NoCcy")
    r = run(vault, "log", "NoCcy", "x", "-c", "gbp")
    assert r.returncode == 0, r.stderr
    assert vault.entries("Projects", "NoCcy")[0]["currency"] == "GBP"


def test_bad_currency_rejected(vault):
    vault.write_thread("Projects", "NoCcy")
    assert run(vault, "log", "NoCcy", "x", "-c", "RANDS").returncode != 0


# ---- 5. the delimiter bug that motivated the story ----

def test_punctuation_heavy_description_roundtrips(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    desc = 'Further decomposition; code review, with "Nick" and [[people/Nick]]'
    r = run(vault, "log", "SANA Partners", desc)
    assert r.returncode == 0, r.stderr
    eid = vault.entries("Projects", "SANA Partners")[0]["id"]
    shown = json.loads(run(vault, "show", eid, "--json").stdout)
    assert shown["description"] == desc


# ---- 6. reporting never crosses currencies ----

def test_report_groups_by_currency(vault):
    vault.write_thread("Projects", "ZA", currency="ZAR")
    vault.write_thread("Processes", "BW", currency="BWP")
    run(vault, "log", "ZA", "a", "-m", "60", "-r", "100")
    run(vault, "log", "BW", "b", "-m", "60", "-r", "100")
    out = json.loads(run(vault, "report", "--json").stdout)
    assert {b["currency"] for b in out} == {"ZAR", "BWP"}
    assert all(b["amount"] == 100 for b in out)
    text = run(vault, "report").stdout
    assert "TOTAL ZAR" in text and "TOTAL BWP" in text


def test_rate_zero_counts_hours_but_no_money(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    run(vault, "log", "SANA Partners", "unbillable", "-m", "120", "-r", "0")
    b = json.loads(run(vault, "report", "--json").stdout)[0]
    assert b["minutes"] == 120
    assert b["hours"] == 2.0
    assert b["amount"] == 0


def test_report_date_window(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    run(vault, "log", "SANA Partners", "old", "-d", "2026-01-01", "-t", "09:00")
    run(vault, "log", "SANA Partners", "new", "-d", "2026-06-01", "-t", "09:00")
    out = json.loads(run(vault, "report", "--since", "2026-05-01", "--json").stdout)
    assert out[0]["entries"] == 1


# ---- edit / rm ----

def test_edit_minutes_and_description(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    run(vault, "log", "SANA Partners", "before", "-m", "60")
    eid = vault.entries("Projects", "SANA Partners")[0]["id"]
    run(vault, "edit", eid, "-m", "30", "--description", "after", "words")
    shown = json.loads(run(vault, "show", eid, "--json").stdout)
    assert shown["minutes"] == 30
    assert shown["description"] == "after words"


def test_rm_removes_entry(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    run(vault, "log", "SANA Partners", "doomed")
    eid = vault.entries("Projects", "SANA Partners")[0]["id"]
    assert run(vault, "rm", eid, "-y").returncode == 0
    assert vault.entries("Projects", "SANA Partners") == []


def test_entries_stay_sorted_by_start(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    run(vault, "log", "SANA Partners", "later", "-d", "2026-06-01", "-t", "09:00")
    run(vault, "log", "SANA Partners", "earlier", "-d", "2026-01-01", "-t", "09:00")
    names = [e["name"] for e in vault.entries("Projects", "SANA Partners")]
    assert names == ["earlier", "later"]


def test_ids_are_unique_across_many_logs(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    for i in range(15):
        run(vault, "log", "SANA Partners", f"entry {i}")
    ids = [e["id"] for e in vault.entries("Projects", "SANA Partners")]
    assert len(set(ids)) == 15
