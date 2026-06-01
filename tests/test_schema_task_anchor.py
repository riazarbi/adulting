"""task_anchor schema: shape regex parses canonical forms; lint validates
each field through its existing scalar DSL.

These tests exercise lint as a subprocess against a temp vault — same
path the operator uses. Cross-vault rules (uniqueness, depends, cycles,
end>=entry) are covered in test_lint_task_anchor.py once the patch is in.
"""


def _setup(vault):
    """Common setup: one thread, one person."""
    vault.write_thread("Projects", "SGB")
    vault.write_person("Riaz Arbi")


def _note_with_lines(vault, *anchor_lines):
    return vault.write_note(
        "2026-05-27-09-15-22", "\n".join(anchor_lines),
        threads=["Projects/SGB"])


def _lint_violations(vault, path):
    r = vault.run(str(path), cli="lint")
    return [l for l in r.stdout.split("\n")
            if "task_anchor" in l or ": missing" in l or "does not conform" in l]


def test_minimal_task_anchor_validates(vault):
    _setup(vault)
    p = _note_with_lines(vault,
        "TASK: Pick up dry cleaning <!--ef567890 entry:2026-05-27-->")
    assert _lint_violations(vault, p) == []


def test_full_task_anchor_validates(vault):
    _setup(vault)
    p = _note_with_lines(vault,
        "TASK: Prereq <!--ef567890 entry:2026-05-27-->",
        "TASK: [#H] (Riaz Arbi) Send quarterly report "
        "<!--abcd1234 entry:2026-05-27 due:2026-05-29 "
        "scheduled:2026-05-28 depends:ef567890-->")
    # Use full-vault lint so cross-file checks (depends resolution) fire.
    r = vault.run(cli="lint")
    assert r.returncode == 0, r.stdout


def test_done_with_end_validates(vault):
    _setup(vault)
    p = _note_with_lines(vault,
        "DONE: [#M] (Riaz Arbi) Review the contract "
        "<!--abc12340 entry:2026-05-24 end:2026-05-27-->")
    assert _lint_violations(vault, p) == []


def test_priority_must_be_HML(vault):
    _setup(vault)
    p = _note_with_lines(vault,
        "TASK: [#Q] (Riaz Arbi) Bad priority <!--abcd1234 entry:2026-05-27-->")
    violations = _lint_violations(vault, p)
    assert any("priority" in v and ("'Q'" in v or "Q" in v) for v in violations), violations


def test_uuid_must_be_8_hex(vault):
    _setup(vault)
    p = _note_with_lines(vault,
        "TASK: Bad uuid <!--ZZZZZZZZ entry:2026-05-27-->")
    violations = _lint_violations(vault, p)
    # Either the shape regex fails or the uuid field rejects it.
    assert violations, "expected at least one violation for bad uuid"


def test_entry_must_be_iso_date(vault):
    _setup(vault)
    p = _note_with_lines(vault,
        "TASK: Bad entry <!--abcd1234 entry:May-27-2026-->")
    violations = _lint_violations(vault, p)
    assert violations, "expected violation for non-ISO entry"


def test_kind_must_be_TASK_or_DONE(vault):
    _setup(vault)
    p = _note_with_lines(vault,
        "WIP: Some line <!--abcd1234 entry:2026-05-27-->")
    # Doesn't match applies_when at all -> not validated as task_anchor,
    # so no task_anchor violation expected. Tests that the schema
    # doesn't false-fire on unrelated lines.
    assert _lint_violations(vault, p) == []
