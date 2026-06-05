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
