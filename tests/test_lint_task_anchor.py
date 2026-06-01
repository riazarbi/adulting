"""Cross-vault and conditional checks for task_anchor lines."""


def _setup(vault, people=("Riaz Arbi",), threads=(("Projects", "SGB"),)):
    for kind, name in threads:
        vault.write_thread(kind, name)
    for p in people:
        vault.write_person(p)


def _note(vault, stem, *anchor_lines):
    return vault.write_note(
        stem, "\n".join(anchor_lines), threads=["Projects/SGB"])


def _lint_vault(vault):
    """Walk the whole vault — needed for cross-file checks to fire."""
    r = vault.run(cli="lint")
    return r


def test_done_without_end_flagged(vault):
    _setup(vault)
    _note(vault, "2026-05-27-09-15-22",
        "DONE: Bad anchor <!--abcd1234 entry:2026-05-27-->")
    r = _lint_vault(vault)
    assert r.returncode == 1
    assert "DONE requires 'end'" in r.stdout, r.stdout


def test_end_before_entry_flagged(vault):
    _setup(vault)
    _note(vault, "2026-05-27-09-15-22",
        "DONE: Bad order <!--abcd1234 entry:2026-05-27 end:2026-05-20-->")
    r = _lint_vault(vault)
    assert r.returncode == 1
    assert "precedes entry" in r.stdout, r.stdout


def test_assignee_unresolved_flagged(vault):
    _setup(vault, people=("Riaz Arbi",))
    _note(vault, "2026-05-27-09-15-22",
        "TASK: (Ghost) Phantom <!--abcd1234 entry:2026-05-27-->")
    r = _lint_vault(vault)
    assert r.returncode == 1
    assert "Ghost" in r.stdout and "does not resolve" in r.stdout, r.stdout


def test_assignee_resolved_passes(vault):
    _setup(vault)
    _note(vault, "2026-05-27-09-15-22",
        "TASK: (Riaz Arbi) Real person <!--abcd1234 entry:2026-05-27-->")
    r = _lint_vault(vault)
    assert r.returncode == 0, r.stdout


def test_duplicate_uuid_across_files_flagged(vault):
    _setup(vault)
    _note(vault, "2026-05-27-09-15-22",
        "TASK: First <!--abcd1234 entry:2026-05-27-->")
    _note(vault, "2026-05-27-10-30-00",
        "TASK: Second <!--abcd1234 entry:2026-05-27-->")
    r = _lint_vault(vault)
    assert r.returncode == 1
    assert "duplicated" in r.stdout, r.stdout


def test_dangling_depends_flagged(vault):
    _setup(vault)
    _note(vault, "2026-05-27-09-15-22",
        "TASK: Depends on nothing <!--abcd1234 entry:2026-05-27 depends:beef0000-->")
    r = _lint_vault(vault)
    assert r.returncode == 1
    assert "does not resolve to any anchor" in r.stdout, r.stdout


def test_depends_resolved_passes(vault):
    _setup(vault)
    _note(vault, "2026-05-27-09-15-22",
        "TASK: First <!--abcd1234 entry:2026-05-27-->",
        "TASK: Second <!--ef567890 entry:2026-05-27 depends:abcd1234-->")
    r = _lint_vault(vault)
    assert r.returncode == 0, r.stdout


def test_depends_self_loop_flagged(vault):
    _setup(vault)
    _note(vault, "2026-05-27-09-15-22",
        "TASK: Self <!--abcd1234 entry:2026-05-27 depends:abcd1234-->")
    r = _lint_vault(vault)
    assert r.returncode == 1
    assert "cycle:" in r.stdout, r.stdout


def test_depends_2cycle_flagged(vault):
    _setup(vault)
    _note(vault, "2026-05-27-09-15-22",
        "TASK: A <!--abcd1234 entry:2026-05-27 depends:ef567890-->",
        "TASK: B <!--ef567890 entry:2026-05-27 depends:abcd1234-->")
    r = _lint_vault(vault)
    assert r.returncode == 1
    assert "cycle:" in r.stdout, r.stdout


def test_depends_3cycle_flagged(vault):
    _setup(vault)
    _note(vault, "2026-05-27-09-15-22",
        "TASK: A <!--abcd1234 entry:2026-05-27 depends:ef567890-->",
        "TASK: B <!--ef567890 entry:2026-05-27 depends:beef0000-->",
        "TASK: C <!--beef0000 entry:2026-05-27 depends:abcd1234-->")
    r = _lint_vault(vault)
    assert r.returncode == 1
    assert "cycle:" in r.stdout, r.stdout


def test_dag_without_cycle_passes(vault):
    _setup(vault)
    _note(vault, "2026-05-27-09-15-22",
        "TASK: A <!--abcd1234 entry:2026-05-27-->",
        "TASK: B <!--ef567890 entry:2026-05-27 depends:abcd1234-->",
        "TASK: C <!--beef0000 entry:2026-05-27 depends:abcd1234,ef567890-->")
    r = _lint_vault(vault)
    assert r.returncode == 0, r.stdout


def test_multi_depends_one_missing_flagged(vault):
    _setup(vault)
    _note(vault, "2026-05-27-09-15-22",
        "TASK: A <!--abcd1234 entry:2026-05-27-->",
        "TASK: B <!--ef567890 entry:2026-05-27 depends:abcd1234,dead0000-->")
    r = _lint_vault(vault)
    assert r.returncode == 1
    assert "dead0000" in r.stdout and "does not resolve" in r.stdout, r.stdout
