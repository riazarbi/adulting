"""Tests for the hours_file schema and its lint validation."""

VALID = {
    "name": "Bitemporal table design",
    "startTime": "2026-07-25T07:29:00.000Z",
    "endTime": "2026-07-25T09:29:00.000Z",
    "id": "a1b2c3d4",
    "rate": 2000,
    "currency": "ZAR",
}


def lint(vault, *paths):
    return vault.run(*paths, cli="lint")


def entry(**over):
    e = dict(VALID)
    e.update(over)
    return e


def test_valid_hours_file_is_clean(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    p = vault.write_hours_file("Projects", "SANA Partners", [entry()])
    r = lint(vault, str(p))
    assert r.returncode == 0, r.stdout


def test_empty_block_is_clean(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    p = vault.write_hours_file("Projects", "SANA Partners", [])
    assert lint(vault, str(p)).returncode == 0


def test_unresolvable_thread_is_flagged(vault):
    p = vault.write_hours_file("Projects", "Ghost", [entry()])
    r = lint(vault, str(p))
    assert r.returncode == 1
    assert "does not resolve" in r.stdout


def test_missing_currency_frontmatter_is_flagged(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    p = vault.write_hours_file("Projects", "SANA Partners", [entry()])
    p.write_text(p.read_text().replace("currency: ZAR\n", ""), encoding="utf-8")
    r = lint(vault, str(p))
    assert r.returncode == 1
    assert "currency" in r.stdout


def test_unparseable_json_is_flagged(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    p = vault.write_hours_file("Projects", "SANA Partners", [entry()])
    p.write_text(p.read_text().replace('"entries"', '"entries" oops'),
                 encoding="utf-8")
    r = lint(vault, str(p))
    assert r.returncode == 1
    assert "does not parse" in r.stdout


def test_missing_block_is_flagged(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    p = vault.write_hours_file("Projects", "SANA Partners", [entry()])
    p.write_text('---\nthread: "[[Projects/SANA Partners]]"\ncurrency: ZAR\n'
                 '---\n\n# nothing here\n', encoding="utf-8")
    r = lint(vault, str(p))
    assert r.returncode == 1
    assert "no ```simple-time-tracker block" in r.stdout


def test_missing_entry_field_is_flagged(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    e = entry()
    del e["rate"]
    p = vault.write_hours_file("Projects", "SANA Partners", [e])
    r = lint(vault, str(p))
    assert r.returncode == 1
    assert "entries[0].rate: missing" in r.stdout


def test_bad_id_shape_is_flagged(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    p = vault.write_hours_file("Projects", "SANA Partners", [entry(id="NOPE")])
    r = lint(vault, str(p))
    assert r.returncode == 1
    assert "not 8 hex chars" in r.stdout


def test_bad_timestamp_is_flagged(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    p = vault.write_hours_file("Projects", "SANA Partners",
                              [entry(startTime="2026-07-25 07:29")])
    r = lint(vault, str(p))
    assert r.returncode == 1
    assert "not ISO 8601 UTC" in r.stdout


def test_end_before_start_is_flagged(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    p = vault.write_hours_file("Projects", "SANA Partners",
                              [entry(endTime="2026-07-25T06:00:00.000Z")])
    r = lint(vault, str(p))
    assert r.returncode == 1
    assert "endTime precedes startTime" in r.stdout


def test_bad_currency_code_is_flagged(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    p = vault.write_hours_file("Projects", "SANA Partners",
                              [entry(currency="rand")])
    r = lint(vault, str(p))
    assert r.returncode == 1
    assert "not a 3-letter ISO code" in r.stdout


def test_rate_zero_is_valid(vault):
    """Unbillable work is ordinary, not an error."""
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    p = vault.write_hours_file("Projects", "SANA Partners", [entry(rate=0)])
    assert lint(vault, str(p)).returncode == 0


def test_duplicate_ids_across_files_are_flagged(vault):
    vault.write_thread("Projects", "A", currency="ZAR")
    vault.write_thread("Projects", "B", currency="ZAR")
    vault.write_hours_file("Projects", "A", [entry()])
    vault.write_hours_file("Projects", "B", [entry()])
    r = vault.run(cli="lint")           # whole-vault walk
    assert r.returncode == 1
    assert "duplicated at" in r.stdout


def test_whole_vault_walk_includes_time_dir(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    vault.write_hours_file("Projects", "SANA Partners", [entry(id="ZZZZ")])
    r = vault.run(cli="lint")
    assert r.returncode == 1
    assert "hours/Projects/SANA Partners.md" in r.stdout


def test_thread_may_carry_currency_and_rate(vault):
    p = vault.write_thread("Projects", "SANA Partners", currency="ZAR", rate=2500)
    assert lint(vault, str(p)).returncode == 0


def test_thread_bad_currency_is_flagged(vault):
    p = vault.write_thread("Projects", "SANA Partners", currency="zar")
    r = lint(vault, str(p))
    assert r.returncode == 1
    assert "currency" in r.stdout
