"""The `lint` command: its surface, and every schema it checks: threads,
people, notes, logs, task anchors, hours files and payments files."""

import pytest


def lint(vault, *argv):
    return vault.run(*argv, cli="lint")


def violations(r):
    """The `<path>:<line>: <message>` lines, without the summary."""
    return [l for l in r.stdout.split("\n") if l and "file(s) checked" not in l]


# ---------- command surface ----------

def test_empty_vault_is_clean_with_a_summary_line(vault):
    r = lint(vault)
    assert r.returncode == 0
    assert r.stdout == "\n0 file(s) checked. 0 violation(s).\n"
    assert r.stderr == ""


def test_violation_format_exit_code_and_count(vault):
    p = vault.write_thread("Projects", "SGB", status="bogus")
    r = lint(vault)
    assert r.returncode == 1
    assert violations(r) == [
        f"{p}:0: status: value 'bogus' not in ['open', 'paused', 'closed']"]
    assert r.stdout.endswith("\n1 file(s) checked. 1 violation(s).\n")


def test_quiet_prints_nothing_but_keeps_the_exit_code(vault):
    vault.write_thread("Projects", "SGB", status="bogus")
    r = lint(vault, "--quiet")
    assert r.returncode == 1
    assert r.stdout == ""


def test_explicit_paths_limit_what_is_checked(vault):
    good = vault.write_thread("Projects", "Good")
    vault.write_thread("Projects", "Bad", status="bogus")
    r = lint(vault, str(good))
    assert r.returncode == 0
    assert r.stdout == "\n1 file(s) checked. 0 violation(s).\n"


def test_a_missing_path_is_a_violation(vault):
    missing = vault.home / "notes" / "nope.md"
    r = lint(vault, str(missing))
    assert r.returncode == 1
    assert violations(r) == [f"{missing}:0: file does not exist"]


def test_an_empty_schemas_dir_is_a_tool_failure(vault, tmp_path):
    empty = tmp_path / "no-schemas"
    empty.mkdir()
    r = lint(vault, "--schemas", str(empty))
    assert r.returncode == 2
    assert r.stderr == f"lint: error: no schemas loaded from {empty}\n"


def test_schemas_flag_uses_another_directory(vault, tmp_path):
    only = tmp_path / "only-person"
    only.mkdir()
    (only / "person.md").write_text(
        "---\nschema: person\nscope: file\ndirectory: people\n"
        "filename: ^[^.]+\\.md$\n---\n\n## Fields\n"
        "| name | required | type | constraint |\n|---|---|---|---|\n"
        "| status | yes | enum | open |\n", encoding="utf-8")
    vault.write_thread("Projects", "SGB")
    vault.write_person("Riaz Arbi", status="closed")
    assert violations(lint(vault, "--schemas", str(only))) == [
        f"{vault.home}/threads/Projects/SGB.md:0: no matching file schema",
        f"{vault.home}/people/Riaz Arbi.md:0: status: value 'closed' not in ['open']",
        f"{vault.home}/people/Riaz Arbi.md:0: ended is required when status is closed",
    ]


def test_walk_skips_dot_directories_dot_files_and_bak_files(vault):
    vault.write("threads/.trash/Projects/Old.md", "garbage")
    vault.write("threads/Projects/.hidden.md", "garbage")
    vault.write("threads/Projects/SGB.md.bak", "garbage")
    vault.write("threads/Projects/notes.txt", "garbage")
    r = lint(vault)
    assert (r.returncode, r.stdout) == (0, "\n0 file(s) checked. 0 violation(s).\n")



# ---------- threads and people ----------

def test_closed_thread_and_person_need_ended(vault):
    t = vault.write_thread("Projects", "SGB", status="closed")
    p = vault.write_person("Riaz Arbi", status="closed")
    assert violations(lint(vault)) == [
        f"{vault.home}/threads/Projects/SGB.md:0: ended is required when status is closed",
        f"{vault.home}/people/Riaz Arbi.md:0: ended is required when status is closed",
    ]


def test_missing_required_field(vault):
    p = vault.write("people/Nobody.md", "---\nstatus: open\ncategory: personal\n---\n")
    assert violations(lint(vault)) == [
        f"{p}:0: missing required field 'started' (per person)"]


def test_regex_constraint(vault):
    p = vault.write_thread("Projects", "SGB", started="1 May")
    assert violations(lint(vault)) == [
        f"{p}:0: started: value '1 May' does not match /\\d{{4}}-\\d{{2}}-\\d{{2}}/"]


def test_cadence_rules(vault):
    p = vault.write("threads/Projects/SGB.md",
              "---\nstatus: open\nkind: project\ncategory: professional\n"
              "started: 2026-01-01\ncadences:\n"
              "  - key: weekly\n    frequency: 7\n    description: Check in\n"
              "  - key: weekly\n    frequency: often\n    description: Again\n"
              "  - key: Bad-Key\n    frequency: 30\n"
              "---\n")
    assert violations(lint(vault)) == [
        f"{p}:0: cadences[1]: duplicate key 'weekly'",
        f"{p}:0: cadences[1]: frequency 'often' must be an integer",
        f"{p}:0: cadences[2]: missing description",
        f"{p}:0: cadences[2]: key 'Bad-Key' must be lowercase_with_underscores",
    ]


def test_a_badly_dated_thread_entry_is_not_checked(vault):
    # DEFERRED BUG 8
    p = vault.write_thread("Projects", "SGB")
    with p.open("a", encoding="utf-8") as f:
        f.write("\n- 2026-01-02 — Kicked off\n  - detail is free-form\n"
                "- 2026-13 — Not a date\n")
    # `- 2026-13 — ...` doesn't match thread_entry's applies_when, so it is
    # not checked at all rather than reported as malformed.
    assert violations(lint(vault)) == []


def test_thread_entry_with_empty_text(vault):
    p = vault.write_thread("Projects", "SGB")
    text = p.read_text(encoding="utf-8") + "\n- 2026-01-02 — \n"
    p.write_text(text, encoding="utf-8")
    line_no = text.split("\n").index("- 2026-01-02 — ") + 1
    assert violations(lint(vault)) == [
        f"{p}:{line_no}: line does not conform to thread_entry shape "
        "/^- (?P<date>\\d{4}-\\d{2}-\\d{2}) — (?P<text>.+)$/"]


# ---------- notes ----------

def test_a_valid_note_is_clean(vault):
    vault.write_thread("Projects", "SGB")
    vault.write_person("Riaz Arbi")
    p = vault.write_note("2026-09-10-14-30-00", "ACTION: (Riaz Arbi) Draft it",
                         threads=["Projects/SGB"], type_="Meeting")
    text = p.read_text().replace("---\n\n", 'people:\n  - "[[people/Riaz Arbi]]"\n'
                                             "  - Someone Untracked\n---\n\n", 1)
    p.write_text(text)
    r = lint(vault)
    assert r.returncode == 0, r.stdout


def test_note_with_an_unmatched_filename_has_no_schema(vault):
    p = vault.write("notes/meeting notes.md", "---\ntopic: x\ntype: Log\n---\n")
    assert violations(lint(vault)) == [f"{p}:0: no matching file schema"]


def test_note_thread_links(vault):
    vault.write_thread("Projects", "SGB")
    p = vault.write_note("2026-09-10-14-30-00", "Body",
                         threads=["Projects/SGB", "Projects/Missing", "people/Riaz Arbi"])
    text = p.read_text().replace("  - [[people/Riaz Arbi]]\n",
                                 "  - [[people/Riaz Arbi]]\n  - plain text\n")
    p.write_text(text)
    # The wrong-kind and plain entries fail twice: once on the field's regex,
    # once on wikilink resolution. A well-formed but missing target fails once.
    assert violations(lint(vault)) == [
        f"{p}:0: threads[2]: value '[[people/Riaz Arbi]]' does not match "
        "/\\[\\[(Projects|Processes|Topics)/[^\\]]+\\]\\]/",
        f"{p}:0: threads[3]: value 'plain text' does not match "
        "/\\[\\[(Projects|Processes|Topics)/[^\\]]+\\]\\]/",
        f"{p}:0: threads: wikilink '[[Projects/Missing]]' does not resolve",
        f"{p}:0: threads: wikilink '[[people/Riaz Arbi]]' must target "
        "Projects/X, Processes/X, or Topics/X",
        f"{p}:0: threads: entry 'plain text' is not a wikilink",
    ]


def test_note_people_links(vault):
    vault.write_thread("Projects", "SGB")
    p = vault.write_note("2026-09-10-14-30-00", "Body", threads=["Projects/SGB"])
    text = p.read_text().replace(
        "---\n\n", 'people:\n  - "[[people/Ghost]]"\n  - "[[Projects/SGB]]"\n'
                   "  - Plain Name\n---\n\n", 1)
    p.write_text(text)
    assert violations(lint(vault)) == [
        f"{p}:0: people: wikilink '[[people/Ghost]]' does not resolve",
        f"{p}:0: people: wikilink '[[Projects/SGB]]' should target 'people/...'",
    ]


def test_action_lines_in_a_note(vault):
    vault.write_thread("Projects", "SGB")
    p = vault.write_note("2026-09-10-14-30-00",
                         "ACTION:   \nACTION: (Ghost) Chase it\n",
                         threads=["Projects/SGB"])
    lines_of = p.read_text().split("\n")
    first = lines_of.index("ACTION:   ") + 1
    assert violations(lint(vault)) == [
        f"{p}:{first}: ACTION: missing description",
        f"{p}:{first + 1}: ACTION: assignee 'Ghost' does not resolve to people/Ghost.md",
    ]


# ---------- logs ----------

def test_log_thread_must_resolve(vault):
    p = vault.write("logs/Projects/Gone/2026-09-10.md",
              '---\nthread: "[[Projects/Gone]]"\ndate: 2026-09-10\ntype: Log\n---\n\n'
              "- TEXT: something\n")
    assert violations(lint(vault)) == [
        f"{p}:0: thread: wikilink '[[Projects/Gone]]' does not resolve"]


def test_log_actions_are_checked_like_notes(vault):
    vault.write_thread("Projects", "SGB")
    p = vault.write("logs/Projects/SGB/2026-09-10.md",
              '---\nthread: "[[Projects/SGB]]"\ndate: 2026-09-10\ntype: Log\n---\n\n'
              "ACTION: (Ghost) Chase it\n")
    assert violations(lint(vault)) == [
        f"{p}:7: ACTION: assignee 'Ghost' does not resolve to people/Ghost.md"]


# ---------- task anchors ----------

def anchor_note(vault, *anchor_lines, stem="2026-05-27-09-15-22"):
    """A note in Projects/SGB holding these lines; the thread and a person
    exist. The first line of the body is line 9."""
    if not (vault.home / "threads" / "Projects" / "SGB.md").exists():
        vault.write_thread("Projects", "SGB")
        vault.write_person("Riaz Arbi")
    return vault.write_note(stem, "\n".join(anchor_lines), threads=["Projects/SGB"])


def lint_file(vault, path):
    """(exit code, every violation line) for linting one file. Anything on
    stderr is kept too, so a crash cannot hide."""
    r = lint(vault, str(path))
    return r.returncode, violations(r) + ([r.stderr] if r.stderr else [])


def _shape_violation(path):
    return f"{path}:9: line does not conform to task_anchor shape /{SHAPE}/"


SHAPE = (r"^(?P<kind>TASK|DONE):\s+(?:\[#(?P<priority>[^\]]+)\]\s+)?(?:\((?P<assignee>[^)]+)\)\s+)?"
         r"(?P<body>.+?)\s+<!--\s*(?P<uuid>[a-f0-9]{8})\s+entry:(?P<entry>\d{4}-\d{2}-\d{2})"
         r"(?:\s+end:(?P<end>\d{4}-\d{2}-\d{2}))?(?:\s+due:(?P<due>\d{4}-\d{2}-\d{2}))?"
         r"(?:\s+scheduled:(?P<scheduled>\d{4}-\d{2}-\d{2}))?(?:\s+depends:(?P<depends>[a-f0-9,]+))?"
         r"\s*-->\s*$")


def test_minimal_task_anchor_validates(vault):
    p = anchor_note(vault,
        "TASK: Pick up dry cleaning <!--ef567890 entry:2026-05-27-->")
    assert lint_file(vault, p) == (0, [])


def test_full_task_anchor_validates(vault):
    p = anchor_note(vault,
        "TASK: Prereq <!--ef567890 entry:2026-05-27-->",
        "TASK: [#H] (Riaz Arbi) Send quarterly report "
        "<!--abcd1234 entry:2026-05-27 due:2026-05-29 "
        "scheduled:2026-05-28 depends:ef567890-->")
    # Use full-vault lint so cross-file checks (depends resolution) fire.
    r = lint(vault)
    assert r.returncode == 0, r.stdout


def test_done_with_end_validates(vault):
    p = anchor_note(vault,
        "DONE: [#M] (Riaz Arbi) Review the contract "
        "<!--abc12340 entry:2026-05-24 end:2026-05-27-->")
    assert lint_file(vault, p) == (0, [])


def test_priority_must_be_HML(vault):
    p = anchor_note(vault,
        "TASK: [#Q] (Riaz Arbi) Bad priority <!--abcd1234 entry:2026-05-27-->")
    assert lint_file(vault, p) == (1, [f"{p}:9: task_anchor.priority: value 'Q' not in ['H', 'M', 'L']"])


def test_uuid_must_be_8_hex(vault):
    p = anchor_note(vault,
        "TASK: Bad uuid <!--ZZZZZZZZ entry:2026-05-27-->")
    assert lint_file(vault, p) == (1, [_shape_violation(p)])


def test_entry_must_be_iso_date(vault):
    p = anchor_note(vault,
        "TASK: Bad entry <!--abcd1234 entry:May-27-2026-->")
    assert lint_file(vault, p) == (1, [_shape_violation(p)])


def test_a_line_that_is_not_a_task_anchor_is_not_checked_as_one(vault):
    """`WIP:` does not match the schema's applies_when, so the line is not
    validated as an anchor at all, and the note is clean."""
    p = anchor_note(vault,
        "WIP: Some line <!--abcd1234 entry:2026-05-27-->")
    assert lint_file(vault, p) == (0, [])


def test_done_without_end_flagged(vault):
    anchor_note(vault,
        "DONE: Bad anchor <!--abcd1234 entry:2026-05-27-->", stem="2026-05-27-09-15-22")
    assert violations(lint(vault)) == [
        f"{vault.home}/notes/2026-05-27-09-15-22.md:9: task_anchor: kind=DONE requires 'end'",
    ]


def test_end_before_entry_flagged(vault):
    anchor_note(vault,
        "DONE: Bad order <!--abcd1234 entry:2026-05-27 end:2026-05-20-->", stem="2026-05-27-09-15-22")
    assert violations(lint(vault)) == [
        f"{vault.home}/notes/2026-05-27-09-15-22.md:9: task_anchor: end '2026-05-20' precedes entry '2026-05-27'",
    ]


def test_assignee_unresolved_flagged(vault):
    anchor_note(vault,
        "TASK: (Ghost) Phantom <!--abcd1234 entry:2026-05-27-->", stem="2026-05-27-09-15-22")
    assert violations(lint(vault)) == [
        f"{vault.home}/notes/2026-05-27-09-15-22.md:9: task_anchor.assignee: 'Ghost' does not resolve to people/Ghost.md",
    ]


def test_assignee_resolved_passes(vault):
    anchor_note(vault,
        "TASK: (Riaz Arbi) Real person <!--abcd1234 entry:2026-05-27-->", stem="2026-05-27-09-15-22")
    r = lint(vault)
    assert r.returncode == 0, r.stdout


def test_duplicate_uuid_across_files_flagged(vault):
    anchor_note(vault,
        "TASK: First <!--abcd1234 entry:2026-05-27-->", stem="2026-05-27-09-15-22")
    anchor_note(vault,
        "TASK: Second <!--abcd1234 entry:2026-05-27-->", stem="2026-05-27-10-30-00")
    assert violations(lint(vault)) == [
        f"{vault.home}/notes/2026-05-27-09-15-22.md:9: task_anchor.uuid: 'abcd1234' duplicated at {vault.home}/notes/2026-05-27-10-30-00.md:9",
        f"{vault.home}/notes/2026-05-27-10-30-00.md:9: task_anchor.uuid: 'abcd1234' duplicated at {vault.home}/notes/2026-05-27-09-15-22.md:9",
    ]


def test_dangling_depends_flagged(vault):
    anchor_note(vault,
        "TASK: Depends on nothing <!--abcd1234 entry:2026-05-27 depends:beef0000-->", stem="2026-05-27-09-15-22")
    assert violations(lint(vault)) == [
        f"{vault.home}/notes/2026-05-27-09-15-22.md:9: task_anchor.depends: 'beef0000' does not resolve to any anchor",
    ]


def test_depends_resolved_passes(vault):
    anchor_note(vault,
        "TASK: First <!--abcd1234 entry:2026-05-27-->",
        "TASK: Second <!--ef567890 entry:2026-05-27 depends:abcd1234-->", stem="2026-05-27-09-15-22")
    r = lint(vault)
    assert r.returncode == 0, r.stdout


def test_depends_self_loop_flagged(vault):
    anchor_note(vault,
        "TASK: Self <!--abcd1234 entry:2026-05-27 depends:abcd1234-->", stem="2026-05-27-09-15-22")
    assert violations(lint(vault)) == [
        f"{vault.home}/notes/2026-05-27-09-15-22.md:9: task_anchor.depends: cycle: abcd1234 -> abcd1234",
    ]


def test_depends_2cycle_flagged(vault):
    anchor_note(vault,
        "TASK: A <!--abcd1234 entry:2026-05-27 depends:ef567890-->",
        "TASK: B <!--ef567890 entry:2026-05-27 depends:abcd1234-->", stem="2026-05-27-09-15-22")
    assert violations(lint(vault)) == [
        f"{vault.home}/notes/2026-05-27-09-15-22.md:9: task_anchor.depends: cycle: abcd1234 -> ef567890 -> abcd1234",
    ]


def test_depends_3cycle_flagged(vault):
    anchor_note(vault,
        "TASK: A <!--abcd1234 entry:2026-05-27 depends:ef567890-->",
        "TASK: B <!--ef567890 entry:2026-05-27 depends:beef0000-->",
        "TASK: C <!--beef0000 entry:2026-05-27 depends:abcd1234-->", stem="2026-05-27-09-15-22")
    assert violations(lint(vault)) == [
        f"{vault.home}/notes/2026-05-27-09-15-22.md:9: task_anchor.depends: cycle: abcd1234 -> ef567890 -> beef0000 -> abcd1234",
    ]


def test_dag_without_cycle_passes(vault):
    anchor_note(vault,
        "TASK: A <!--abcd1234 entry:2026-05-27-->",
        "TASK: B <!--ef567890 entry:2026-05-27 depends:abcd1234-->",
        "TASK: C <!--beef0000 entry:2026-05-27 depends:abcd1234,ef567890-->", stem="2026-05-27-09-15-22")
    r = lint(vault)
    assert r.returncode == 0, r.stdout


def test_multi_depends_one_missing_flagged(vault):
    anchor_note(vault,
        "TASK: A <!--abcd1234 entry:2026-05-27-->",
        "TASK: B <!--ef567890 entry:2026-05-27 depends:abcd1234,dead0000-->", stem="2026-05-27-09-15-22")
    assert violations(lint(vault)) == [
        f"{vault.home}/notes/2026-05-27-09-15-22.md:10: task_anchor.depends: 'dead0000' does not resolve to any anchor",
    ]


# ---------- hours files ----------

HOURS_ENTRY = {
    "name": "Bitemporal table design",
    "startTime": "2026-07-25T07:29:00.000Z",
    "endTime": "2026-07-25T09:29:00.000Z",
    "id": "a1b2c3d4",
    "rate": 2000,
    "currency": "ZAR",
}


def entry(**over):
    e = dict(HOURS_ENTRY)
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
    assert violations(lint(vault, str(p))) == [
        f"{vault.home}/hours/Projects/Ghost.md:0: thread: wikilink '[[Projects/Ghost]]' does not resolve",
    ]


def test_missing_currency_frontmatter_is_allowed(vault):
    """An hours file with no currency holds unbilled time, which is valid:
    `hours` records time and money is an overlay. Previously required."""
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    p = vault.write_hours_file("Projects", "SANA Partners", [entry()])
    p.write_text(p.read_text().replace("currency: ZAR\n", ""), encoding="utf-8")
    r = lint(vault, str(p))
    assert r.returncode == 0, r.stdout


def test_malformed_currency_is_still_flagged(vault):
    """Optional does not mean unchecked: a currency that is present must
    still be a 3-letter ISO code."""
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    p = vault.write_hours_file("Projects", "SANA Partners", [entry()])
    p.write_text(p.read_text().replace("currency: ZAR", "currency: rand"),
                 encoding="utf-8")
    assert violations(lint(vault, str(p))) == [
        f"{vault.home}/hours/Projects/SANA Partners.md:0: currency: value 'rand' does not match /^[A-Z]{{3}}$/",
    ]


def test_unparseable_json_is_flagged(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    p = vault.write_hours_file("Projects", "SANA Partners", [entry()])
    p.write_text(p.read_text().replace('"entries"', '"entries" oops'),
                 encoding="utf-8")
    assert violations(lint(vault, str(p))) == [
        f"{vault.home}/hours/Projects/SANA Partners.md:8: hours_file: tracker JSON does not parse: Expecting ':' delimiter: line 2 column 13 (char 14)",
    ]


def test_missing_block_is_flagged(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    p = vault.write_hours_file("Projects", "SANA Partners", [entry()])
    p.write_text('---\nthread: "[[Projects/SANA Partners]]"\ncurrency: ZAR\n'
                 '---\n\n# nothing here\n', encoding="utf-8")
    assert violations(lint(vault, str(p))) == [
        f"{vault.home}/hours/Projects/SANA Partners.md:0: hours_file: no ```simple-time-tracker block",
    ]


def test_missing_entry_field_is_flagged(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    e = entry()
    del e["rate"]
    p = vault.write_hours_file("Projects", "SANA Partners", [e])
    assert violations(lint(vault, str(p))) == [
        f"{vault.home}/hours/Projects/SANA Partners.md:8: hours_file: entries[0].rate: missing",
    ]


def test_bad_id_shape_is_flagged(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    p = vault.write_hours_file("Projects", "SANA Partners", [entry(id="NOPE")])
    assert violations(lint(vault, str(p))) == [
        f"{vault.home}/hours/Projects/SANA Partners.md:8: hours_file: entries[0].id: 'NOPE' is not 8 hex chars",
    ]


def test_bad_timestamp_is_flagged(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    p = vault.write_hours_file("Projects", "SANA Partners",
                              [entry(startTime="2026-07-25 07:29")])
    assert violations(lint(vault, str(p))) == [
        f"{vault.home}/hours/Projects/SANA Partners.md:8: hours_file: entries[0].startTime: '2026-07-25 07:29' is not ISO 8601 UTC",
    ]


def test_end_before_start_is_flagged(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    p = vault.write_hours_file("Projects", "SANA Partners",
                              [entry(endTime="2026-07-25T06:00:00.000Z")])
    assert violations(lint(vault, str(p))) == [
        f"{vault.home}/hours/Projects/SANA Partners.md:8: hours_file: entries[0]: endTime precedes startTime",
    ]


def test_bad_currency_code_is_flagged(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    p = vault.write_hours_file("Projects", "SANA Partners",
                              [entry(currency="rand")])
    assert violations(lint(vault, str(p))) == [
        f"{vault.home}/hours/Projects/SANA Partners.md:8: hours_file: entries[0].currency: 'rand' is not a 3-letter ISO code",
    ]


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
    assert violations(lint(vault)) == [
        f"{vault.home}/hours/Projects/A.md:8: record id 'a1b2c3d4' duplicated at {vault.home}/hours/Projects/B.md:8",
        f"{vault.home}/hours/Projects/B.md:8: record id 'a1b2c3d4' duplicated at {vault.home}/hours/Projects/A.md:8",
    ]


def test_whole_vault_walk_includes_time_dir(vault):
    vault.write_thread("Projects", "SANA Partners", currency="ZAR")
    vault.write_hours_file("Projects", "SANA Partners", [entry(id="ZZZZ")])
    assert violations(lint(vault)) == [
        f"{vault.home}/hours/Projects/SANA Partners.md:8: hours_file: entries[0].id: 'ZZZZ' is not 8 hex chars",
    ]


def test_thread_may_carry_currency_and_rate(vault):
    p = vault.write_thread("Projects", "SANA Partners", currency="ZAR", rate=2500)
    assert lint(vault, str(p)).returncode == 0


def test_thread_bad_currency_is_flagged(vault):
    p = vault.write_thread("Projects", "SANA Partners", currency="zar")
    assert violations(lint(vault, str(p))) == [
        f"{vault.home}/threads/Projects/SANA Partners.md:0: currency: value 'zar' does not match /^[A-Z]{{3}}$/",
    ]


def test_unbilled_hours_pass_lint(vault):
    vault.write_thread("Topics", "Reading")
    vault.run("log", "Topics/Reading", "Reading", "-m", "30", cli="hours")
    r = lint(vault)
    assert r.returncode == 0, r.stdout + r.stderr


# ---------- payments files ----------

def test_valid_payments_file_lints_clean(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    p = vault.write_payments_file("Projects", "X", [{
        "id": "a1b2c3d4", "received": "2026-04-05T07:00:00.000Z",
        "amount": 47300, "currency": "ZAR", "account": "FNB Botswana"}])
    assert lint(vault, str(p)).returncode == 0


def test_lint_flags_missing_payment_field(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    p = vault.write_payments_file("Projects", "X", [{
        "id": "a1b2c3d4", "received": "2026-04-05T07:00:00.000Z",
        "currency": "ZAR"}])
    assert violations(lint(vault, str(p))) == [
        f"{vault.home}/payments/Projects/X.md:8: payments_file: payments[0].amount: missing",
    ]


def test_lint_flags_non_positive_amount(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    p = vault.write_payments_file("Projects", "X", [{
        "id": "a1b2c3d4", "received": "2026-04-05T07:00:00.000Z",
        "amount": -5, "currency": "ZAR"}])
    assert violations(lint(vault, str(p))) == [
        f"{vault.home}/payments/Projects/X.md:8: payments_file: payments[0].amount: must be positive",
    ]


def test_lint_flags_id_shared_with_an_hours_entry(vault):
    """One id namespace across both tools."""
    vault.write_thread("Projects", "X", currency="ZAR")
    vault.write_hours_file("Projects", "X", [{
        "name": "w", "startTime": "2026-04-05T07:00:00.000Z",
        "endTime": "2026-04-05T08:00:00.000Z", "id": "a1b2c3d4",
        "rate": 100, "currency": "ZAR"}])
    vault.write_payments_file("Projects", "X", [{
        "id": "a1b2c3d4", "received": "2026-04-05T07:00:00.000Z",
        "amount": 100, "currency": "ZAR"}])
    assert violations(lint(vault)) == [
        f"{vault.home}/hours/Projects/X.md:8: record id 'a1b2c3d4' duplicated at {vault.home}/payments/Projects/X.md:8",
        f"{vault.home}/payments/Projects/X.md:8: record id 'a1b2c3d4' duplicated at {vault.home}/hours/Projects/X.md:8",
    ]


def test_lint_walks_payments_dir(vault):
    vault.write_thread("Projects", "X", currency="ZAR")
    vault.write_payments_file("Projects", "X", [{
        "id": "ZZZZ", "received": "2026-04-05T07:00:00.000Z",
        "amount": 1, "currency": "ZAR"}])
    assert violations(lint(vault)) == [
        f"{vault.home}/payments/Projects/X.md:8: payments_file: payments[0].id: 'ZZZZ' is not 8 hex chars",
    ]


@pytest.mark.parametrize("block, expected", [
    # The block-shape messages are pinned for every case in
    # tests/unit/test_lint.py; these check that lint's walk reports them.
    (None, "0: payments_file: no ```adulting-payments block"),
    ('{"payments": ["x"]}', "6: payments_file: payments[0] is not an object"),
])
def test_payments_block_errors(vault, block, expected):
    vault.write_thread("Projects", "SGB", currency="ZAR")
    body = "" if block is None else f"```adulting-payments\n{block}\n```\n"
    p = vault.write("payments/Projects/SGB.md",
              f'---\nthread: "[[Projects/SGB]]"\ncurrency: ZAR\n---\n\n{body}')
    assert violations(lint(vault)) == [f"{p}:{expected}"]


def test_payment_fields_are_each_checked(vault):
    vault.write_thread("Projects", "SGB", currency="ZAR")
    p = vault.write("payments/Projects/SGB.md",
              '---\nthread: "[[Projects/SGB]]"\ncurrency: ZAR\n---\n\n```adulting-payments\n'
              '{"payments": [{"id": "abcd1234", "received": "2026-09-10", "amount": "10", "currency": "zar"}]}\n'
              '```\n')
    assert violations(lint(vault)) == [
        f"{p}:6: payments_file: payments[0].received: '2026-09-10' is not ISO 8601 UTC",
        f"{p}:6: payments_file: payments[0].currency: 'zar' is not a 3-letter ISO code",
        f"{p}:6: payments_file: payments[0].amount: '10' is not a number",
    ]


def test_hours_rate_must_be_an_integer_and_one_block_only(vault):
    vault.write_thread("Projects", "SGB", currency="ZAR")
    p = vault.write_hours_file("Projects", "SGB", entries=[
        {"name": "x", "startTime": "2026-09-10T10:00:00.000Z",
         "endTime": "2026-09-10T11:00:00.000Z", "id": "abcd1234", "rate": 2.5}])
    p.write_text(p.read_text() + "\n```simple-time-tracker\n{}\n```\n")
    assert violations(lint(vault)) == [
        f"{vault.home}/hours/Projects/SGB.md:8: hours_file: more than one tracker block",
        f"{vault.home}/hours/Projects/SGB.md:8: hours_file: entries[0].rate: 2.5 is not an integer",
    ]
