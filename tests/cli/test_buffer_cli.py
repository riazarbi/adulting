"""Tests for the `buffer` CLI (refactor unit 8).

The first sections characterise behaviour kept from the pre-port script and
were run green against it. The last section specifies the removal of the
`suggest` prompt and was written to fail against the old script.
"""

import re
from datetime import date

import pytest


TS = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"


def buf(vault, *argv, input=""):
    # input="" closes stdin, so any prompt would hit EOF instead of hanging.
    return vault.run(*argv, cli="buffer", input=input)


@pytest.fixture
def buffer_vault(vault):
    vault.write_thread("Projects", "SGB")
    vault.write_thread("Topics", "Wellness")
    vault.write("people/Riaz Arbi.md", "---\nstatus: open\n---\n")
    vault.write("notes/2026-09-10-14-30-00.md", "---\ntopic: x\n---\n")
    return vault


def buffer_text(vault):
    return vault.read("buffer.md")


# ---------- add-* ----------

def test_add_writes_an_unknown_entry(buffer_vault):
    r = buf(buffer_vault, "add", "  chase SGB  ")
    assert re.fullmatch(rf"buffered: - UNKNOWN: chase SGB <!--{TS}-->\n", r.stdout)
    assert buffer_text(buffer_vault) == r.stdout[len("buffered: "):]


def test_add_text_ref_action_line_shapes(buffer_vault):
    lines = [
        buf(buffer_vault, "add-text", "Projects/SGB", "Auth wall unresolved").stdout,
        buf(buffer_vault, "add-ref", "Projects/SGB", "notes/2026-09-10-14-30-00", "Kickoff").stdout,
        buf(buffer_vault, "add-ref", "Topics/Wellness", "Projects/SGB").stdout,
        buf(buffer_vault, "add-action", "Projects/SGB", "(Riaz Arbi) Draft scope", "--due", "2026-09-20",
            "--priority", "H", "--scheduled", "2026-09-15", "--depends", "bbbbbbbb",
            "--depends", "aaaaaaaa").stdout,
        buf(buffer_vault, "add-action", "Projects/SGB", "Plain action").stdout,
    ]
    shapes = [re.sub(TS, "TS", l) for l in lines]
    assert shapes == [
        "buffered: - [[Projects/SGB]] TEXT: Auth wall unresolved <!--TS-->\n",
        "buffered: - [[Projects/SGB]] REF: [[notes/2026-09-10-14-30-00]] Kickoff <!--TS-->\n",
        "buffered: - [[Topics/Wellness]] REF: [[Projects/SGB]] <!--TS-->\n",
        "buffered: - [[Projects/SGB]] ACTION: (Riaz Arbi) Draft scope <!--TS depends:aaaaaaaa "
        "depends:bbbbbbbb due:2026-09-20 priority:H scheduled:2026-09-15-->\n",
        "buffered: - [[Projects/SGB]] ACTION: Plain action <!--TS-->\n",
    ]
    assert len(buffer_text(buffer_vault).splitlines()) == 5


def test_add_ref_date_files_under_that_day_and_keeps_the_clock(buffer_vault):
    r = buf(buffer_vault, "add-ref", "--date", "2026-08-04", "Projects/SGB", "notes/2026-09-10-14-30-00")
    assert re.search(r"<!--2026-08-04T\d{2}:\d{2}:\d{2}-->", r.stdout)


@pytest.mark.parametrize("argv, message", [
    (["add", ""], "buffer: error: text is empty"),
    (["add-text", "Nope", "x"], "buffer: error: thread 'Nope' does not resolve to a thread file"),
    (["add-text", "Projects/SGB", " "], "buffer: error: text is empty"),
    (["add-ref", "People/SGB", "notes/x"], "buffer: error: thread 'People/SGB' does not resolve to a thread file"),
    (["add-ref", "Projects/SGB", "notes/nope"],
     "buffer: error: ref target 'notes/nope' does not resolve to a vault file "
     "(expected notes/X, logs/X, people/X, hours/X, payments/X, or <Kind>/X)"),
    (["add-ref", "Projects/SGB", "notes/2026-09-10-14-30-00", "--date", "10 Sep"],
     "buffer: error: --date must be YYYY-MM-DD; got '10 Sep'"),
    (["add-action", "Projects/SGB", " "], "buffer: error: description is empty"),
    (["add-action", "Projects/SGB", "(Ghost) x"],
     "buffer: error: assignee 'Ghost' does not resolve to people/Ghost.md (create the person file first)"),
    (["add-action", "Projects/SGB", "(Riaz Arbi)  "], "buffer: error: description after assignee is empty"),
    (["add-action", "Projects/SGB", "x", "--due", "Friday"], "buffer: error: due must be YYYY-MM-DD; got 'Friday'"),
    (["add-action", "Projects/SGB", "x", "--scheduled", "1/2/26"],
     "buffer: error: scheduled must be YYYY-MM-DD; got '1/2/26'"),
    (["add-action", "Projects/SGB", "x", "--depends", "XYZ"], "buffer: error: depends must be 8 hex chars; got 'XYZ'"),
])
def test_add_errors_write_nothing(buffer_vault, argv, message):
    r = buf(buffer_vault, *argv)
    assert (r.returncode, r.stdout, r.stderr) == (1, "", message + "\n")
    assert not (buffer_vault.home / "buffer.md").exists()


def test_add_ref_accepts_every_record_kind(buffer_vault):
    buffer_vault.write_person("Igor Novak")
    buffer_vault.write_hours_file("Projects", "SGB")
    buffer_vault.write_payments_file("Projects", "SGB")
    buffer_vault.write("logs/Projects/SGB/2026-09-10.md", "x")
    for target in ("people/Igor Novak", "hours/Projects/SGB", "payments/Projects/SGB",
                   "logs/Projects/SGB/2026-09-10", "Topics/Wellness"):
        assert buf(buffer_vault, "add-ref", "Projects/SGB", target).returncode == 0, target


def test_quiet_does_not_silence_add(buffer_vault):
    # DEFERRED BUG 6: --quiet does not silence the add-* commands.
    r = buf(buffer_vault, "--quiet", "add-text", "Projects/SGB", "still printed")
    assert r.stdout.startswith("buffered: ")


# ---------- list, rm ----------

MESSY = [
    "- [[Topics/Wellness]] TEXT: second day <!--2026-09-11T09:00:00-->",
    "- UNKNOWN: late capture <!--2026-09-12T08:00:00-->",
    "- [[Projects/SGB]] ACTION: (Riaz Arbi) Draft scope <!--2026-09-10T15:00:00 depends:bbbbbbbb due:2026-09-20 priority:H-->",
    "garbage line",
    "- [[Projects/SGB]] TEXT: earlier <!--2026-09-10T09:00:00-->",
    "- UNKNOWN: early capture <!--2026-09-09T08:00:00-->",
    "",
    "- [[Topics/Wellness]] REF: [[notes/2026-09-10-14-30-00]] Kickoff <!--2026-09-11T08:00:00-->",
    "- [[Projects/Gone]] TEXT: orphan <!--2026-09-10T10:00:00-->",
    "- [[Projects/SGB]] TEXT: has attrs <!--2026-09-10T11:00:00 due:2026-09-20-->",
    "- [[Projects/SGB]] ACTION: bad attrs <!--2026-09-10T12:00:00 priority:X due:soon foo-->",
    "- [[Topics/Wellness]] REF: not a link <!--2026-09-11T10:00:00-->",
]


def test_list_numbers_lines_and_skips_blanks(buffer_vault):
    buffer_vault.write("buffer.md", "\n".join(MESSY) + "\n")
    out = buf(buffer_vault, "list").stdout.splitlines()
    assert out[0] == "   1  " + MESSY[0]
    assert out[6] == "   8  " + MESSY[7]
    assert len(out) == 11


def test_list_filter_and_empty_messages(buffer_vault):
    assert buf(buffer_vault, "list").stdout == "(buffer empty)\n"
    buffer_vault.write("buffer.md", "\n".join(MESSY) + "\n")
    assert [l[:4] for l in buf(buffer_vault, "list", "WELLNESS").stdout.splitlines()] == ["   1", "   8", "  12"]
    assert buf(buffer_vault, "list", "zzz").stdout == "(no matching entries)\n"


def test_rm(buffer_vault):
    buffer_vault.write("buffer.md", "\n".join(MESSY) + "\n")
    r = buf(buffer_vault, "rm", "4")
    assert r.stdout == "removed line 4: garbage line\n"
    assert "garbage line" not in buffer_text(buffer_vault)
    before = buffer_text(buffer_vault)
    for argv, message in ((["rm", "abc"], "buffer: error: line number must be an integer; got 'abc'"),
                          (["rm", "0"], "buffer: error: line 0 out of range (buffer has 12 lines)"),
                          (["rm", "6"], "buffer: error: line 6 is empty")):
        r = buf(buffer_vault, *argv)
        assert (r.returncode, r.stdout, r.stderr) == (1, "", message + "\n"), argv
        assert buffer_text(buffer_vault) == before


# ---------- tend ----------

REGROUPED = (
    "- [[Projects/Gone]] TEXT: orphan <!--2026-09-10T10:00:00-->\n"
    "- [[Projects/SGB]] TEXT: earlier <!--2026-09-10T09:00:00-->\n"
    "- [[Projects/SGB]] TEXT: has attrs <!--2026-09-10T11:00:00 due:2026-09-20-->\n"
    "- [[Projects/SGB]] ACTION: bad attrs <!--2026-09-10T12:00:00 priority:X due:soon foo-->\n"
    "- [[Projects/SGB]] ACTION: (Riaz Arbi) Draft scope <!--2026-09-10T15:00:00 depends:bbbbbbbb due:2026-09-20 priority:H-->\n"
    "- [[Topics/Wellness]] REF: [[notes/2026-09-10-14-30-00]] Kickoff <!--2026-09-11T08:00:00-->\n"
    "- [[Topics/Wellness]] TEXT: second day <!--2026-09-11T09:00:00-->\n"
    "- [[Topics/Wellness]] REF: not a link <!--2026-09-11T10:00:00-->\n"
    "\n"
    "<!-- UNKNOWN ENTRIES BELOW: convert via `buffer rm <n>` + the matching `buffer add-*`. tend will fail until cleared. -->\n"
    "- UNKNOWN: early capture <!--2026-09-09T08:00:00-->\n"
    "- UNKNOWN: late capture <!--2026-09-12T08:00:00-->\n"
    "\n"
    "<!-- UNPARSED ENTRIES BELOW: tend cannot regroup these. Fix or remove via `buffer rm`. -->\n"
    "garbage line\n")


def violation(line_no, message, raw):
    return (f"  buffer.md:{line_no}: {message}\n    line: {raw}\n"
            f"    fix: edit via `buffer rm {line_no}` and re-add via the matching `buffer add-*`\n")


def test_tend_regroups_and_reports_every_violation(buffer_vault):
    buffer_vault.write("buffer.md", "\n".join(MESSY) + "\n")
    r = buf(buffer_vault, "tend")
    assert (r.returncode, r.stdout) == (1, "")
    assert buffer_text(buffer_vault) == REGROUPED
    lines = REGROUPED.split("\n")
    assert r.stderr == "buffer has 9 violation(s):\n" + "".join([
        violation(1, "thread 'Projects/Gone' does not resolve", lines[0]),
        violation(3, "TEXT entries do not accept attrs; got 'due:2026-09-20'", lines[2]),
        violation(4, "ACTION priority must be H, M, or L; got 'X'", lines[3]),
        violation(4, "ACTION due must be YYYY-MM-DD; got 'soon'", lines[3]),
        violation(4, "ACTION unknown attr token 'foo'", lines[3]),
        violation(8, "REF body must start with a [[wikilink]]", lines[7]),
        violation(11, "UNKNOWN entry must be converted to TEXT, REF, or ACTION before tend can pass", lines[10]),
        violation(12, "UNKNOWN entry must be converted to TEXT, REF, or ACTION before tend can pass", lines[11]),
        violation(15, "line does not match buffer entry shape", lines[14]),
    ])


def test_tend_is_idempotent(buffer_vault):
    buffer_vault.write("buffer.md", "\n".join(MESSY) + "\n")
    first = buf(buffer_vault, "tend")
    second = buf(buffer_vault, "tend")
    assert buffer_text(buffer_vault) == REGROUPED
    assert first.stderr == second.stderr


def test_tend_reports_unresolvable_ref_targets_and_assignees(buffer_vault):
    buffer_vault.write("buffer.md",
          "- [[Projects/SGB]] REF: [[notes/nope]] x <!--2026-09-10T09:00:00-->\n"
          "- [[Projects/SGB]] ACTION: (Ghost) x <!--2026-09-10T10:00:00-->\n")
    stderr = buf(buffer_vault, "tend").stderr
    assert "REF target 'notes/nope' does not resolve to a vault file" in stderr
    assert "ACTION assignee 'Ghost' does not resolve to people/Ghost.md" in stderr


def test_tend_clean_and_quiet(buffer_vault):
    buffer_vault.write("buffer.md", "- [[Projects/SGB]] TEXT: ok <!--2026-09-10T09:00:00-->\n"
                          "- [[Topics/Wellness]] TEXT: ok <!--2026-09-10T09:00:00-->\n")
    assert buf(buffer_vault, "tend").stdout == "buffer tended: 2 entries, 2 group(s).\n"
    assert buf(buffer_vault, "--quiet", "tend").stdout == ""


def test_tend_creates_an_empty_buffer_file(buffer_vault):
    # DEFERRED BUG 5: tend on a vault with no buffer.md writes an empty one.
    r = buf(buffer_vault, "tend")
    assert (r.returncode, r.stdout) == (0, "buffer tended: 0 entries, 0 group(s).\n")
    assert buffer_text(buffer_vault) == ""


# ---------- flush ----------

CLEAN = (
    "- [[Topics/Wellness]] TEXT: second day <!--2026-09-11T09:00:00-->\n"
    "- [[Projects/SGB]] ACTION: (Riaz Arbi) Draft scope <!--2026-09-10T15:00:00 depends:bbbbbbbb due:2026-09-20 priority:H-->\n"
    "- [[Projects/SGB]] TEXT: earlier <!--2026-09-10T09:00:00-->\n"
    "- [[Topics/Wellness]] REF: [[notes/2026-09-10-14-30-00]] Kickoff <!--2026-09-11T08:00:00-->\n")


def test_flush_writes_logs_clears_the_buffer_and_ingests_actions(buffer_vault):
    buffer_vault.write("buffer.md", CLEAN)
    buffer_vault.write("logs/Topics/Wellness/2026-09-11.md", "---\nthread: x\n---\nexisting no newline")
    r = buf(buffer_vault, "flush")
    assert r.returncode == 0
    out = r.stdout.splitlines()
    assert out[:3] == [
        "flushed 2 entries -> logs/Projects/SGB/2026-09-10.md",
        "flushed 2 entries -> logs/Topics/Wellness/2026-09-11.md",
        "flushed 4 entries into 2 log file(s); buffer cleared.",
    ]
    assert re.match(r"ingested: [0-9a-f]{8}  .*/logs/Projects/SGB/2026-09-10\.md:10  Draft scope$", out[3])
    assert out[4] == "Ingested: 1.  Failed: 0."
    assert buffer_text(buffer_vault) == ""
    sgb = buffer_vault.read("logs/Projects/SGB/2026-09-10.md")
    assert re.fullmatch(
        r'---\nthread: "\[\[Projects/SGB\]\]"\ndate: 2026-09-10\ntype: Log\n---\n\n'
        r"# Daily log — Projects/SGB — 2026-09-10\n\n"
        r"TEXT: earlier\n"
        r"TASK: \[#H\] \(Riaz Arbi\) Draft scope <!--[0-9a-f]{8} entry:\d{4}-\d{2}-\d{2} "
        r"due:2026-09-20 depends:bbbbbbbb-->  \n", sgb)
    assert buffer_vault.read("logs/Topics/Wellness/2026-09-11.md") == (
        "---\nthread: x\n---\nexisting no newline\n"
        "REF: [[notes/2026-09-10-14-30-00]] Kickoff\n"
        "TEXT: second day\n")


def test_flush_keeps_action_attrs_in_the_log_line(buffer_vault):
    """The attrs ride into the log line for `tasks` to apply on ingest; the
    ingested anchor still carries them."""
    buffer_vault.write("buffer.md",
          "- [[Projects/SGB]] ACTION: Draft <!--2026-09-10T15:00:00 due:2026-09-20 priority:H-->\n")
    buf(buffer_vault, "--quiet", "flush")
    assert "due:2026-09-20" in buffer_vault.read("logs/Projects/SGB/2026-09-10.md")


def test_flush_refuses_while_tend_fails_and_writes_nothing(buffer_vault):
    buffer_vault.write("buffer.md", "\n".join(MESSY) + "\n")
    r = buf(buffer_vault, "flush")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr.startswith("buffer has 9 violation(s):\n")
    assert list((buffer_vault.home / "logs").rglob("*.md")) == []
    assert buffer_text(buffer_vault) == REGROUPED


def test_flush_empty_and_quiet(buffer_vault):
    assert buf(buffer_vault, "flush").stdout == "buffer is empty; nothing to flush.\n"
    buffer_vault.write("buffer.md", "- [[Projects/SGB]] TEXT: quiet <!--2026-09-10T09:00:00-->\n")
    r = buf(buffer_vault, "--quiet", "flush")
    # DEFERRED BUG 6: --quiet silences flush but not the task ingest it runs.
    assert r.stdout == "Ingested: 0.  Failed: 0.\n"
    assert "TEXT: quiet" in buffer_vault.read("logs/Projects/SGB/2026-09-10.md")


# ---------- suggest ----------

def test_suggest_with_yes_runs_the_suggestion(buffer_vault):
    r = buf(buffer_vault, "suggest", "Draft the SGB scope note by 2026-09-30", "-y")
    assert r.returncode == 0
    lines = r.stdout.splitlines()
    assert lines[:2] == ["suggested:",
                         "  buffer add-action Projects/SGB 'Draft the SGB scope note' --due 2026-09-30"]
    assert re.fullmatch(rf"buffered: - \[\[Projects/SGB\]\] ACTION: Draft the SGB scope note "
                        rf"<!--{TS} due:2026-09-30-->", lines[2])


def test_suggest_without_a_structured_suggestion_stores_unknown(buffer_vault):
    r = buf(buffer_vault, "suggest", "zzzz qqqq", "-y")
    lines = r.stdout.splitlines()
    assert lines[0] == "no structured suggestion; storing as UNKNOWN."
    assert re.fullmatch(rf"buffered: - UNKNOWN: zzzz qqqq <!--{TS}-->", lines[1])
    assert buf(buffer_vault, "--quiet", "suggest", "zzzz qqqq").stdout.startswith("buffered: - UNKNOWN")


def test_suggest_without_yes_and_without_a_terminal_stores_unknown(buffer_vault):
    r = buf(buffer_vault, "suggest", "Draft the SGB scope note by 2026-09-30")
    lines = r.stdout.splitlines()
    assert lines[1] == "  buffer add-action Projects/SGB 'Draft the SGB scope note' --due 2026-09-30"
    assert "storing as UNKNOWN." in lines[2]
    assert "- UNKNOWN: Draft the SGB scope note by 2026-09-30" in buffer_text(buffer_vault)
    assert "ACTION" not in buffer_text(buffer_vault)


# ---------- no interactivity (fails against the pre-port script) ----------

def test_suggest_never_prompts_even_on_a_terminal(buffer_vault):
    r = buffer_vault.run_on_a_terminal("suggest", "Draft the SGB scope note by 2026-09-30", cli="buffer")
    assert r.returncode == 0
    assert "accept?" not in r.stdout
    assert r.stdout.splitlines()[2] == "not accepted (pass -y to accept); storing as UNKNOWN."
    assert "- UNKNOWN: Draft the SGB scope note by 2026-09-30" in buffer_text(buffer_vault)
    assert "ACTION" not in buffer_text(buffer_vault)


def test_a_failed_ingest_after_flush_warns_and_keeps_the_flush(vault):
    """The buffer is cleared before the ingest runs, so an ingest failure
    must not fail the flush: the entries are safe in the logs, and `tasks`
    can be re-run. Here the ingest fails for real, on a notes folder it
    cannot write to."""
    vault.write_thread("Projects", "SGB")
    vault.write_note("2026-09-10-14-30-00", "ACTION: stuck", threads=["Projects/SGB"])
    vault.run("add-text", "Projects/SGB", "hello", cli="buffer")
    today = date.today().isoformat()
    (vault.home / "notes").chmod(0o555)
    try:
        r = vault.run("flush", cli="buffer")
    finally:
        (vault.home / "notes").chmod(0o755)
    assert (r.returncode, r.stdout) == (0, (
        f"flushed 1 entry -> logs/Projects/SGB/{today}.md\n"
        "flushed 1 entries into 1 log file(s); buffer cleared.\n"))
    assert r.stderr == ("buffer: warning: flushed, but the task ingest failed: [Errno 13] "
                        f"Permission denied: '{vault.home / 'notes' / '2026-09-10-14-30-00.md.tmp'}'\n")
    assert vault.read("buffer.md") == ""
    assert vault.lines(f"logs/Projects/SGB/{today}.md")[-2] == "TEXT: hello"
    assert vault.lines("notes/2026-09-10-14-30-00.md")[-2] == "ACTION: stuck"


@pytest.mark.parametrize("target", ["Projects/sgb", "people/riaz arbi", "notes/../threads/Projects/SGB"])
def test_add_ref_needs_the_exact_name_of_a_vault_file(buffer_vault, target):
    """Checked against the files in the vault, not by asking the filesystem,
    so a wrongly cased target is refused on macOS as on Linux, and `..`
    cannot reach out of the folder it names."""
    before = buffer_vault.snapshot()
    r = buffer_vault.run("add-ref", "Projects/SGB", target, cli="buffer")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == (f"buffer: error: ref target {target!r} does not resolve to a vault file "
                        "(expected notes/X, logs/X, people/X, hours/X, payments/X, or <Kind>/X)\n")
    assert buffer_vault.snapshot() == before
