"""Smoke test — the vault fixture and CLI runner are wired correctly."""


def test_vault_fixture_creates_skeleton(vault):
    assert (vault.home / "notes").is_dir()
    assert (vault.home / "logs").is_dir()
    assert (vault.home / "threads").is_dir()
    assert (vault.home / "people").is_dir()
    assert (vault.home / ".adulting").is_dir()


def test_write_thread_and_person(vault):
    vault.write_thread("Projects", "SGB")
    vault.write_person("Riaz Arbi")
    assert (vault.home / "threads" / "Projects" / "SGB.md").is_file()
    assert (vault.home / "people" / "Riaz Arbi.md").is_file()


def test_run_lint_no_files_is_clean(vault):
    r = vault.run(cli="lint")
    assert r.returncode == 0, f"stderr: {r.stderr}\nstdout: {r.stdout}"


def test_run_tasks_help(vault):
    r = vault.run("--help", cli="tasks")
    assert r.returncode == 0
    assert "ingest" in r.stdout.lower() or "tasks" in r.stdout.lower()


def test_buffer_ref_targets_accept_hours_and_payments(vault):
    """hours/ and payments/ postdate ref_target_resolves and were missing
    from it, so a REF could not point at a time entry or a receipt."""
    vault.write_thread("Projects", "SANA", currency="ZAR", rate=2500)
    vault.write_hours_file("Projects", "SANA", entries=[])
    vault.write_payments_file("Projects", "SANA", payments=[])
    for target in ("hours/Projects/SANA", "payments/Projects/SANA"):
        r = vault.run("add-ref", "Projects/SANA", target, "x", cli="buffer")
        assert r.returncode == 0, f"{target}: {r.stdout}{r.stderr}"


def test_add_ref_date_is_optional_and_validated(vault):
    vault.write_thread("Projects", "SANA")
    ok = vault.run("add-ref", "Projects/SANA", "Projects/SANA", "x", cli="buffer")
    assert ok.returncode == 0, ok.stderr          # optional
    bad = vault.run("add-ref", "Projects/SANA", "Projects/SANA", "x",
                    "--date", "4 August", cli="buffer")
    assert bad.returncode != 0
    assert "YYYY-MM-DD" in (bad.stdout + bad.stderr)
