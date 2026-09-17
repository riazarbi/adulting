"""Characterisation tests for the `lint` CLI (refactor unit 2).

Written against the pre-port script and run green there first. The hours,
payments and task-anchor checks have their own files; this one covers the
command surface and the file-scope rules for notes, threads, people and logs.
"""

import json

import pytest


def lint(vault, *argv):
    return vault.run(*argv, cli="lint")


def violations(r):
    """The `<path>:<line>: <message>` lines, without the summary."""
    return [l for l in r.stdout.split("\n") if l and "file(s) checked" not in l]


def write(vault, rel, text):
    p = vault.home / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


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
    assert r.stderr == f"no schemas loaded from {empty}\n"


def test_schemas_flag_uses_another_directory(vault, tmp_path):
    only = tmp_path / "only-person"
    only.mkdir()
    (only / "person.md").write_text(
        "---\nschema: person\nscope: file\ndirectory: people\n"
        "filename: ^[^.]+\\.md$\n---\n\n## Fields\n"
        "| name | required | type | constraint |\n|---|---|---|---|\n"
        "| status | yes | enum | open |\n", encoding="utf-8")
    thread = vault.write_thread("Projects", "SGB")
    vault.write_person("Riaz Arbi", status="closed")
    r = lint(vault, "--schemas", str(only))
    assert r.returncode == 1
    lines = violations(r)
    assert f"{thread}:0: no matching file schema" in lines
    assert any("status: value 'closed' not in ['open']" in l for l in lines)


def test_walk_skips_dot_directories_dot_files_and_bak_files(vault):
    write(vault, "threads/.trash/Projects/Old.md", "garbage")
    write(vault, "threads/Projects/.hidden.md", "garbage")
    write(vault, "threads/Projects/SGB.md.bak", "garbage")
    write(vault, "threads/Projects/notes.txt", "garbage")
    r = lint(vault)
    assert r.returncode == 0
    assert "0 file(s) checked" in r.stdout


def test_help_json(vault):
    r = lint(vault, "--help-json")
    manifest = json.loads(r.stdout)
    assert manifest["name"] == "lint"
    assert [f["name"] for f in manifest["flags"]] == ["--schemas", "--quiet"]


# ---------- threads and people ----------

def test_closed_thread_and_person_need_ended(vault):
    t = vault.write_thread("Projects", "SGB", status="closed")
    p = vault.write_person("Riaz Arbi", status="closed")
    lines = violations(lint(vault))
    assert f"{t}:0: ended is required when status is closed" in lines
    assert f"{p}:0: ended is required when status is closed" in lines


def test_missing_required_field(vault):
    p = write(vault, "people/Nobody.md", "---\nstatus: open\ncategory: personal\n---\n")
    assert violations(lint(vault)) == [
        f"{p}:0: missing required field 'started' (per person)"]


def test_regex_constraint(vault):
    p = vault.write_thread("Projects", "SGB", started="1 May")
    assert violations(lint(vault)) == [
        f"{p}:0: started: value '1 May' does not match /\\d{{4}}-\\d{{2}}-\\d{{2}}/"]


def test_cadence_rules(vault):
    p = write(vault, "threads/Projects/SGB.md",
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


def test_only_bullets_that_look_dated_are_checked_as_thread_entries(vault):
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
    p = write(vault, "notes/meeting notes.md", "---\ntopic: x\ntype: Log\n---\n")
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
    p = write(vault, "logs/Projects/Gone/2026-09-10.md",
              '---\nthread: "[[Projects/Gone]]"\ndate: 2026-09-10\ntype: Log\n---\n\n'
              "- TEXT: something\n")
    assert violations(lint(vault)) == [
        f"{p}:0: thread: wikilink '[[Projects/Gone]]' does not resolve"]


def test_log_actions_are_checked_like_notes(vault):
    vault.write_thread("Projects", "SGB")
    p = write(vault, "logs/Projects/SGB/2026-09-10.md",
              '---\nthread: "[[Projects/SGB]]"\ndate: 2026-09-10\ntype: Log\n---\n\n'
              "ACTION: (Ghost) Chase it\n")
    assert violations(lint(vault)) == [
        f"{p}:7: ACTION: assignee 'Ghost' does not resolve to people/Ghost.md"]


# ---------- payments (paths not covered in test_payments_cli) ----------

@pytest.mark.parametrize("block, message", [
    (None, "payments_file: no ```adulting-payments block"),
    ("{not json", "payments_file: JSON does not parse: "),
    ('{"entries": []}', 'payments_file: JSON must be {"payments": [...]}'),
    ('{"payments": ["x"]}', "payments_file: payments[0] is not an object"),
    ('{"payments": [{"id": "abcd1234", "received": "2026-09-10", '
     '"amount": "10", "currency": "zar"}]}',
     "payments_file: payments[0].received: '2026-09-10' is not ISO 8601 UTC"),
])
def test_payments_block_errors(vault, block, message):
    vault.write_thread("Projects", "SGB", currency="ZAR")
    body = "" if block is None else f"```adulting-payments\n{block}\n```\n"
    p = write(vault, "payments/Projects/SGB.md",
              f'---\nthread: "[[Projects/SGB]]"\ncurrency: ZAR\n---\n\n{body}')
    lines = violations(lint(vault))
    assert any(l.startswith(f"{p}:") and message in l for l in lines), lines


def test_payment_amount_type_and_currency(vault):
    vault.write_thread("Projects", "SGB", currency="ZAR")
    vault.write_payments_file("Projects", "SGB", payments=[
        {"id": "abcd1234", "received": "2026-09-10T10:00:00.000Z",
         "amount": "10", "currency": "zar"}])
    lines = violations(lint(vault))
    assert any("payments[0].currency: 'zar' is not a 3-letter ISO code" in l for l in lines)
    assert any("payments[0].amount: '10' is not a number" in l for l in lines)


def test_hours_rate_must_be_an_integer_and_one_block_only(vault):
    vault.write_thread("Projects", "SGB", currency="ZAR")
    p = vault.write_hours_file("Projects", "SGB", entries=[
        {"name": "x", "startTime": "2026-09-10T10:00:00.000Z",
         "endTime": "2026-09-10T11:00:00.000Z", "id": "abcd1234", "rate": 2.5}])
    p.write_text(p.read_text() + "\n```simple-time-tracker\n{}\n```\n")
    lines = violations(lint(vault))
    assert any("hours_file: more than one tracker block" in l for l in lines)
    assert any("entries[0].rate: 2.5 is not an integer" in l for l in lines)
