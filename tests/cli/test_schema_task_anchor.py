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


def _lint(vault, path):
    """(exit code, every violation line) for linting one file. The summary
    line is dropped; everything else lint prints is kept, so a crash or an
    unexpected violation cannot hide."""
    r = vault.run(str(path), cli="lint")
    lines = [l for l in r.stdout.split("\n") if l and "file(s) checked" not in l]
    return r.returncode, lines + ([r.stderr] if r.stderr else [])


def _shape_violation(path):
    return f"{path}:9: line does not conform to task_anchor shape /{SHAPE}/"


SHAPE = (r"^(?P<kind>TASK|DONE):\s+(?:\[#(?P<priority>[^\]]+)\]\s+)?(?:\((?P<assignee>[^)]+)\)\s+)?"
         r"(?P<body>.+?)\s+<!--\s*(?P<uuid>[a-f0-9]{8})\s+entry:(?P<entry>\d{4}-\d{2}-\d{2})"
         r"(?:\s+end:(?P<end>\d{4}-\d{2}-\d{2}))?(?:\s+due:(?P<due>\d{4}-\d{2}-\d{2}))?"
         r"(?:\s+scheduled:(?P<scheduled>\d{4}-\d{2}-\d{2}))?(?:\s+depends:(?P<depends>[a-f0-9,]+))?"
         r"\s*-->\s*$")


def test_minimal_task_anchor_validates(vault):
    _setup(vault)
    p = _note_with_lines(vault,
        "TASK: Pick up dry cleaning <!--ef567890 entry:2026-05-27-->")
    assert _lint(vault, p) == (0, [])


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
    assert _lint(vault, p) == (0, [])


def test_priority_must_be_HML(vault):
    _setup(vault)
    p = _note_with_lines(vault,
        "TASK: [#Q] (Riaz Arbi) Bad priority <!--abcd1234 entry:2026-05-27-->")
    assert _lint(vault, p) == (1, [f"{p}:9: task_anchor.priority: value 'Q' not in ['H', 'M', 'L']"])


def test_uuid_must_be_8_hex(vault):
    _setup(vault)
    p = _note_with_lines(vault,
        "TASK: Bad uuid <!--ZZZZZZZZ entry:2026-05-27-->")
    assert _lint(vault, p) == (1, [_shape_violation(p)])


def test_entry_must_be_iso_date(vault):
    _setup(vault)
    p = _note_with_lines(vault,
        "TASK: Bad entry <!--abcd1234 entry:May-27-2026-->")
    assert _lint(vault, p) == (1, [_shape_violation(p)])


def test_a_line_that_is_not_a_task_anchor_is_not_checked_as_one(vault):
    """`WIP:` does not match the schema's applies_when, so the line is not
    validated as an anchor at all, and the note is clean."""
    _setup(vault)
    p = _note_with_lines(vault,
        "WIP: Some line <!--abcd1234 entry:2026-05-27-->")
    assert _lint(vault, p) == (0, [])
