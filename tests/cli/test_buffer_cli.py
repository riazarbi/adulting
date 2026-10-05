"""The `buffer` command: capture entries, regroup and check them, and flush
them into the daily logs."""

import json
import re
from datetime import date

import pytest


TS = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"


@pytest.fixture
def buffer_vault(vault):
    vault.write_thread("Projects", "SGB")
    vault.write_thread("Topics", "Wellness")
    vault.write("people/Riaz Arbi.md", "---\nstatus: open\n---\n")
    vault.write("threads/Projects/SGB/notes/2026-09-10-14-30-00.md", "---\ntopic: x\n---\n")
    return vault


def buffer_text(vault):
    return vault.read("buffer.md")


# ---------- add-* ----------

def test_add_writes_an_unknown_entry(buffer_vault):
    r = buffer_vault.run("add", "  chase SGB  ", cli="buffer")
    assert re.fullmatch(rf"buffered: - UNKNOWN: chase SGB <!--{TS}-->\n", r.stdout)
    assert buffer_text(buffer_vault) == r.stdout[len("buffered: "):]


def test_add_text_ref_action_line_shapes(buffer_vault):
    lines = [
        buffer_vault.run("add-text", "Projects/SGB", "Auth wall unresolved", cli="buffer").stdout,
        buffer_vault.run("add-ref", "Projects/SGB", "2026-09-10-14-30-00", "Kickoff", cli="buffer").stdout,
        buffer_vault.run("add-ref", "Topics/Wellness", "Projects/SGB", cli="buffer").stdout,
        buffer_vault.run("add-action", "Projects/SGB", "(Riaz Arbi) Draft scope", "--due", "2026-09-20",
            "--priority", "H", "--scheduled", "2026-09-15", "--depends", "bbbbbbbb",
            "--depends", "aaaaaaaa", cli="buffer").stdout,
        buffer_vault.run("add-action", "Projects/SGB", "Plain action", cli="buffer").stdout,
    ]
    shapes = [re.sub(TS, "TS", line) for line in lines]
    assert shapes == [
        "buffered: - [[Projects/SGB]] TEXT: Auth wall unresolved <!--TS-->\n",
        "buffered: - [[Projects/SGB]] REF: [[2026-09-10-14-30-00]] Kickoff <!--TS-->\n",
        "buffered: - [[Topics/Wellness]] REF: [[Projects/SGB]] <!--TS-->\n",
        "buffered: - [[Projects/SGB]] ACTION: (Riaz Arbi) Draft scope <!--TS depends:aaaaaaaa "
        "depends:bbbbbbbb due:2026-09-20 priority:H scheduled:2026-09-15-->\n",
        "buffered: - [[Projects/SGB]] ACTION: Plain action <!--TS-->\n",
    ]
    assert len(buffer_text(buffer_vault).splitlines()) == 5


def test_add_ref_date_files_under_that_day_and_keeps_the_clock(buffer_vault):
    r = buffer_vault.run("add-ref", "--date", "2026-08-04", "Projects/SGB", "2026-09-10-14-30-00", cli="buffer")
    assert re.search(r"<!--2026-08-04T\d{2}:\d{2}:\d{2}-->", r.stdout)


@pytest.mark.parametrize("argv, message", [
    (["add", ""], "buffer: error: text is empty"),
    (["add-text", "Nope", "x"], "buffer: error: thread 'Nope' does not resolve to a thread file"),
    (["add-text", "Projects/SGB", " "], "buffer: error: text is empty"),
    (["add-ref", "People/SGB", "x"], "buffer: error: thread 'People/SGB' does not resolve to a thread file"),
    (["add-ref", "Projects/SGB", "nope"],
     "buffer: error: ref target 'nope' does not resolve to a vault file "
     "(expected <Kind>/<Name>, <Kind>/<Name>/hours, <Kind>/<Name>/payments, <Kind>/<Name>/logs/<date>, a note stem, or people/<Name>)"),
    (["add-ref", "Projects/SGB", "2026-09-10-14-30-00", "--date", "10 Sep"],
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
    r = buffer_vault.run(*argv, cli="buffer")
    assert (r.returncode, r.stdout, r.stderr) == (1, "", message + "\n")
    assert not (buffer_vault.home / "buffer.md").exists()


def test_add_ref_accepts_every_record_kind(buffer_vault):
    buffer_vault.write_person("Igor Novak")
    buffer_vault.write_hours_file("Projects", "SGB")
    buffer_vault.write_payments_file("Projects", "SGB")
    buffer_vault.write("threads/Projects/SGB/logs/2026-09-10.md", "x")
    for target in ("people/Igor Novak", "Projects/SGB/hours", "Projects/SGB/payments",
                   "Projects/SGB/logs/2026-09-10", "Topics/Wellness", "2026-09-10-14-30-00",
                   "Projects/SGB/notes/2026-09-10-14-30-00"):
        assert buffer_vault.run("add-ref", "Projects/SGB", target, cli="buffer").returncode == 0, target


def test_quiet_does_not_silence_add(buffer_vault):
    # DEFERRED BUG 6: --quiet does not silence the add-* commands.
    r = buffer_vault.run("--quiet", "add-text", "Projects/SGB", "still printed", cli="buffer")
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
    "- [[Topics/Wellness]] REF: [[2026-09-10-14-30-00]] Kickoff <!--2026-09-11T08:00:00-->",
    "- [[Projects/Gone]] TEXT: orphan <!--2026-09-10T10:00:00-->",
    "- [[Projects/SGB]] TEXT: has attrs <!--2026-09-10T11:00:00 due:2026-09-20-->",
    "- [[Projects/SGB]] ACTION: bad attrs <!--2026-09-10T12:00:00 priority:X due:soon foo-->",
    "- [[Topics/Wellness]] REF: not a link <!--2026-09-11T10:00:00-->",
]


def test_list_numbers_lines_and_skips_blanks(buffer_vault):
    buffer_vault.write("buffer.md", "\n".join(MESSY) + "\n")
    out = buffer_vault.run("list", cli="buffer").stdout.splitlines()
    assert out[0] == "   1  " + MESSY[0]
    assert out[6] == "   8  " + MESSY[7]
    assert len(out) == 11


def test_list_filter_and_empty_messages(buffer_vault):
    assert buffer_vault.run("list", cli="buffer").stdout == "(buffer empty)\n"
    buffer_vault.write("buffer.md", "\n".join(MESSY) + "\n")
    listed = buffer_vault.run("list", "WELLNESS", cli="buffer").stdout.splitlines()
    assert [line[:4] for line in listed] == ["   1", "   8", "  12"]
    assert buffer_vault.run("list", "zzz", cli="buffer").stdout == "(no matching entries)\n"


def test_rm(buffer_vault):
    buffer_vault.write("buffer.md", "\n".join(MESSY) + "\n")
    r = buffer_vault.run("rm", "4", cli="buffer")
    assert r.stdout == "removed line 4: garbage line\n"
    assert "garbage line" not in buffer_text(buffer_vault)
    before = buffer_text(buffer_vault)
    for argv, message in ((["rm", "abc"], "buffer: error: line number must be an integer; got 'abc'"),
                          (["rm", "0"], "buffer: error: line 0 out of range (buffer has 12 lines)"),
                          (["rm", "6"], "buffer: error: line 6 is empty")):
        r = buffer_vault.run(*argv, cli="buffer")
        assert (r.returncode, r.stdout, r.stderr) == (1, "", message + "\n"), argv
        assert buffer_text(buffer_vault) == before


# ---------- tend ----------

REGROUPED = (
    "- [[Projects/Gone]] TEXT: orphan <!--2026-09-10T10:00:00-->\n"
    "- [[Projects/SGB]] TEXT: earlier <!--2026-09-10T09:00:00-->\n"
    "- [[Projects/SGB]] TEXT: has attrs <!--2026-09-10T11:00:00 due:2026-09-20-->\n"
    "- [[Projects/SGB]] ACTION: bad attrs <!--2026-09-10T12:00:00 priority:X due:soon foo-->\n"
    "- [[Projects/SGB]] ACTION: (Riaz Arbi) Draft scope <!--2026-09-10T15:00:00 depends:bbbbbbbb due:2026-09-20 priority:H-->\n"
    "- [[Topics/Wellness]] REF: [[2026-09-10-14-30-00]] Kickoff <!--2026-09-11T08:00:00-->\n"
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
    r = buffer_vault.run("tend", cli="buffer")
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
    first = buffer_vault.run("tend", cli="buffer")
    second = buffer_vault.run("tend", cli="buffer")
    assert buffer_text(buffer_vault) == REGROUPED
    assert first.stderr == second.stderr


def test_tend_reports_unresolvable_ref_targets_and_assignees(buffer_vault):
    ref = "- [[Projects/SGB]] REF: [[nope]] x <!--2026-09-10T09:00:00-->"
    action = "- [[Projects/SGB]] ACTION: (Ghost) x <!--2026-09-10T10:00:00-->"
    buffer_vault.write("buffer.md", f"{ref}\n{action}\n")
    r = buffer_vault.run("tend", cli="buffer")
    fix = "    fix: edit via `buffer rm {n}` and re-add via the matching `buffer add-*`\n"
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == (
        "buffer has 2 violation(s):\n"
        "  buffer.md:1: REF target 'nope' does not resolve to a vault file\n"
        f"    line: {ref}\n" + fix.format(n=1) +
        "  buffer.md:2: ACTION assignee 'Ghost' does not resolve to people/Ghost.md\n"
        f"    line: {action}\n" + fix.format(n=2))


# ---------- a note stem two notes share ----------
#
# Stems are unique by construction, but a sync conflict or a hand copy can
# give two thread folders the same one. That is a vault problem, reported by
# lint. In the buffer it makes the REF lines naming that stem invalid, and
# nothing else: the rest of the buffer is validated as usual.

DUP = "2026-09-10-14-30-00"


@pytest.fixture
def duplicated(buffer_vault):
    buffer_vault.write(f"threads/Topics/Wellness/notes/{DUP}.md", "---\ntopic: y\n---\n")
    return buffer_vault


def test_add_ref_to_a_shared_stem_is_refused_and_says_why(duplicated):
    r = duplicated.run("add-ref", "Projects/SGB", DUP, cli="buffer")
    assert r.returncode == 1 and r.stdout == ""
    assert f"ref target '{DUP}' is the stem of more than one note" in r.stderr
    assert str(duplicated.note_path(DUP, "Projects/SGB")) in r.stderr
    assert str(duplicated.note_path(DUP, "Topics/Wellness")) in r.stderr
    assert not (duplicated.home / "buffer.md").exists()


def test_tend_rejects_only_the_ref_to_a_shared_stem(duplicated):
    ref = f"- [[Projects/SGB]] REF: [[{DUP}]] x <!--2026-09-10T09:00:00-->"
    text = "- [[Projects/SGB]] TEXT: fine <!--2026-09-10T10:00:00-->"
    bad = "- [[Projects/SGB]] TEXT: also bad <!--2026-09-10T11:00:00--> due:2026-09-11"
    duplicated.write("buffer.md", f"{ref}\n{text}\n{bad}\n")
    r = duplicated.run("tend", cli="buffer")
    assert (r.returncode, r.stdout) == (1, "")
    # Both bad lines are reported, so the rest of the buffer was still read;
    # the good line is not among them.
    assert r.stderr.startswith("buffer has 2 violation(s):\n")
    assert (f"REF target '{DUP}' is the stem of more than one note; "
            "`lint` names them\n") in r.stderr
    assert f"    line: {bad}\n" in r.stderr
    assert f"    line: {text}\n" not in r.stderr
    assert all(line in buffer_text(duplicated) for line in (ref, text, bad))


def test_tend_clean_and_quiet(buffer_vault):
    buffer_vault.write("buffer.md", "- [[Projects/SGB]] TEXT: ok <!--2026-09-10T09:00:00-->\n"
                          "- [[Topics/Wellness]] TEXT: ok <!--2026-09-10T09:00:00-->\n")
    assert buffer_vault.run("tend", cli="buffer").stdout == "buffer tended: 2 entries, 2 group(s).\n"
    assert buffer_vault.run("--quiet", "tend", cli="buffer").stdout == ""


def test_tend_creates_an_empty_buffer_file(buffer_vault):
    # DEFERRED BUG 5: tend on a vault with no buffer.md writes an empty one.
    r = buffer_vault.run("tend", cli="buffer")
    assert (r.returncode, r.stdout) == (0, "buffer tended: 0 entries, 0 group(s).\n")
    assert buffer_text(buffer_vault) == ""


# ---------- flush ----------

CLEAN = (
    "- [[Topics/Wellness]] TEXT: second day <!--2026-09-11T09:00:00-->\n"
    "- [[Projects/SGB]] ACTION: (Riaz Arbi) Draft scope <!--2026-09-10T15:00:00 depends:bbbbbbbb due:2026-09-20 priority:H-->\n"
    "- [[Projects/SGB]] TEXT: earlier <!--2026-09-10T09:00:00-->\n"
    "- [[Topics/Wellness]] REF: [[2026-09-10-14-30-00]] Kickoff <!--2026-09-11T08:00:00-->\n")


def test_flush_writes_logs_clears_the_buffer_and_ingests_actions(buffer_vault):
    buffer_vault.write("buffer.md", CLEAN)
    buffer_vault.write("threads/Topics/Wellness/logs/2026-09-11.md", "---\nthread: x\n---\nexisting no newline")
    r = buffer_vault.run("flush", cli="buffer")
    assert r.returncode == 0
    out = r.stdout.splitlines()
    sgb = buffer_vault.log_path("Projects/SGB", "2026-09-10")
    assert out[:3] == [
        f"flushed 2 entries -> {sgb}",
        f"flushed 2 entries -> {buffer_vault.home}/threads/Topics/Wellness/logs/2026-09-11.md",
        "flushed 4 entries into 2 log file(s); buffer cleared.",
    ]
    assert re.match(rf"ingested: [0-9a-f]{{8}}  {re.escape(str(sgb))}:10  Draft scope$", out[3])
    assert out[4] == "Ingested: 1.  Failed: 0."
    assert buffer_text(buffer_vault) == ""
    sgb = buffer_vault.read("threads/Projects/SGB/logs/2026-09-10.md")
    assert re.fullmatch(
        r'---\nthread: "\[\[Projects/SGB\]\]"\ndate: 2026-09-10\ntype: Log\n---\n\n'
        r"# Daily log — Projects/SGB — 2026-09-10\n\n"
        r"TEXT: earlier\n"
        r"TASK: \[#H\] \(Riaz Arbi\) Draft scope <!--[0-9a-f]{8} entry:\d{4}-\d{2}-\d{2} "
        r"due:2026-09-20 depends:bbbbbbbb-->  \n", sgb)
    assert buffer_vault.read("threads/Topics/Wellness/logs/2026-09-11.md") == (
        "---\nthread: x\n---\nexisting no newline\n"
        "REF: [[2026-09-10-14-30-00]] Kickoff\n"
        "TEXT: second day\n")


def test_flush_refuses_while_tend_fails_and_writes_nothing(buffer_vault):
    buffer_vault.write("buffer.md", "\n".join(MESSY) + "\n")
    r = buffer_vault.run("flush", cli="buffer")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr.startswith("buffer has 9 violation(s):\n")
    assert [p for p in buffer_vault.home.rglob("*.md") if p.parent.name == "logs"] == []
    assert buffer_text(buffer_vault) == REGROUPED


def test_flush_empty_and_quiet(buffer_vault):
    assert buffer_vault.run("flush", cli="buffer").stdout == "buffer is empty; nothing to flush.\n"
    buffer_vault.write("buffer.md", "- [[Projects/SGB]] TEXT: quiet <!--2026-09-10T09:00:00-->\n")
    r = buffer_vault.run("--quiet", "flush", cli="buffer")
    # DEFERRED BUG 6: --quiet silences flush but not the task ingest it runs.
    assert r.stdout == "Ingested: 0.  Failed: 0.\n"
    assert "TEXT: quiet" in buffer_vault.read("threads/Projects/SGB/logs/2026-09-10.md")


# ---------- flush skips an ACTION that is already a task ----------

TASK_LOG = "threads/Projects/SGB/logs/2026-09-01.md"
TASK_LINE = ("TASK: [#H] (Riaz Arbi) Draft scope <!--aaaaaaaa entry:2026-09-01 "
             "due:2026-09-20 scheduled:2026-09-15 depends:bbbbbbbb,cccccccc-->  ")
TWIN = ("- [[Projects/SGB]] ACTION: (Riaz Arbi) Draft scope <!--2026-09-10T15:00:00 "
        "depends:cccccccc depends:bbbbbbbb due:2026-09-20 priority:H scheduled:2026-09-15-->\n")


@pytest.fixture
def tasked(buffer_vault):
    buffer_vault.write(TASK_LOG, f'---\nthread: "[[Projects/SGB]]"\n---\n{TASK_LINE}\n')
    return buffer_vault


def flush_of(vault, *buffer_lines, quiet=False):
    vault.write("buffer.md", "".join(buffer_lines))
    return vault.run(*(["--quiet"] if quiet else []), "flush", cli="buffer")


def test_an_action_that_is_already_an_open_task_is_skipped(tasked):
    """The entry date differs, and depends is given in the other order;
    neither counts."""
    before = tasked.read(TASK_LOG)
    r = flush_of(tasked, TWIN)
    assert (r.returncode, r.stderr) == (0, "")
    assert r.stdout == (
        "flushed 0 entries into 0 log file(s); buffer cleared.\n"
        f"already a task: aaaaaaaa  {tasked.home / TASK_LOG}:4  Draft scope\n"
        "Ingested: 0.  Failed: 0.\n")
    assert not (tasked.home / "threads/Projects/SGB/logs/2026-09-10.md").exists()
    assert tasked.read(TASK_LOG) == before
    assert buffer_text(tasked) == ""


def test_a_skip_is_printed_under_quiet(tasked):
    r = flush_of(tasked, TWIN, quiet=True)
    assert r.stdout == (f"already a task: aaaaaaaa  {tasked.home / TASK_LOG}:4  Draft scope\n"
                        "Ingested: 0.  Failed: 0.\n")


def test_the_rest_of_the_buffer_is_flushed_around_a_skip(tasked):
    r = flush_of(tasked, TWIN, "- [[Projects/SGB]] TEXT: kept <!--2026-09-10T09:00:00-->\n")
    assert r.stdout.splitlines()[:3] == [
        f"flushed 1 entry -> {tasked.home}/threads/Projects/SGB/logs/2026-09-10.md",
        "flushed 1 entries into 1 log file(s); buffer cleared.",
        f"already a task: aaaaaaaa  {tasked.home / TASK_LOG}:4  Draft scope"]
    assert tasked.lines("threads/Projects/SGB/logs/2026-09-10.md")[-2:] == ["TEXT: kept", ""]


@pytest.mark.parametrize("twin", [
    TWIN.replace("Draft scope", "draft scope"),
    TWIN.replace("Draft scope", "Draft  scope"),
    TWIN.replace("(Riaz Arbi) ", ""),
    TWIN.replace(" priority:H", ""),
    TWIN.replace("priority:H", "priority:M"),
    TWIN.replace(" due:2026-09-20", ""),
    TWIN.replace("scheduled:2026-09-15", "scheduled:2026-09-16"),
    TWIN.replace(" depends:cccccccc", ""),
    TWIN.replace("[[Projects/SGB]]", "[[Topics/Wellness]]"),
], ids=["case", "spacing", "assignee", "no priority", "priority", "due", "scheduled",
        "depends", "thread"])
def test_an_action_that_differs_in_anything_compared_becomes_a_task(tasked, twin):
    r = flush_of(tasked, twin)
    assert (r.returncode, r.stderr) == (0, "")
    assert "already" not in r.stdout
    assert "Ingested: 1.  Failed: 0." in r.stdout


@pytest.mark.parametrize("change", [
    lambda v: v.write(TASK_LOG, v.read(TASK_LOG).replace("TASK:", "DONE:").replace(
        "entry:2026-09-01", "entry:2026-09-01 end:2026-09-02")),
    lambda v: v.write(TASK_LOG, v.read(TASK_LOG).replace(
        'thread: "[[Projects/SGB]]"', 'threads:\n  - "[[Projects/SGB]]"\n  - "[[Topics/Wellness]]"')),
    lambda v: (v.home / TASK_LOG).write_bytes(v.read(TASK_LOG).encode() + b"\xff\n"),
], ids=["done twin", "several threads", "unreadable file"])
def test_a_twin_that_does_not_count_does_not_block(tasked, change):
    change(tasked)
    r = flush_of(tasked, TWIN)
    assert r.returncode == 0
    assert "already" not in r.stdout
    assert "Ingested: 1.  Failed: 0." in r.stdout


def test_identical_actions_in_one_flush_collapse_across_days(buffer_vault):
    first = "- [[Projects/SGB]] ACTION: Draft scope <!--2026-09-10T15:00:00 due:2026-09-20-->\n"
    second = first.replace("2026-09-10T15", "2026-09-12T08")
    r = flush_of(buffer_vault, second, first)
    assert (r.returncode, r.stderr) == (0, "")
    out = r.stdout.splitlines()
    log = buffer_vault.home / "threads/Projects/SGB/logs/2026-09-10.md"
    assert out[:3] == [
        f"flushed 1 entry -> {log}",
        "flushed 1 entries into 1 log file(s); buffer cleared.",
        "already buffered: Projects/SGB  Draft scope"]
    assert re.fullmatch(rf"ingested: [0-9a-f]{{8}}  {re.escape(str(log))}:9  Draft scope", out[3])
    assert out[4:] == ["Ingested: 1.  Failed: 0."]
    assert not (buffer_vault.home / "threads/Projects/SGB/logs/2026-09-12.md").exists()


def test_an_unflushed_action_in_a_log_is_not_a_task(buffer_vault):
    buffer_vault.write("threads/Projects/SGB/logs/2026-09-01.md",
                       '---\nthread: "[[Projects/SGB]]"\n---\nACTION: Draft scope\n')
    r = flush_of(buffer_vault, "- [[Projects/SGB]] ACTION: Draft scope <!--2026-09-10T15:00:00-->\n")
    assert "already" not in r.stdout
    assert "Ingested: 2.  Failed: 0." in r.stdout


# ---------- nothing prompts ----------

def test_a_failed_ingest_after_flush_warns_and_keeps_the_flush(vault):
    """The buffer is cleared before the ingest runs, so an ingest failure
    must not fail the flush: the entries are safe in the logs, and `tasks`
    can be re-run. Here the ingest fails for real, on a thread's notes
    folder it cannot write to."""
    vault.write_thread("Projects", "SGB")
    vault.write_note("2026-09-10-14-30-00", "ACTION: stuck", threads=["Projects/SGB"])
    vault.run("add-text", "Projects/SGB", "hello", cli="buffer")
    today = date.today().isoformat()
    notes = vault.home / "threads/Projects/SGB/notes"
    notes.chmod(0o555)
    try:
        r = vault.run("flush", cli="buffer")
    finally:
        notes.chmod(0o755)
    assert (r.returncode, r.stdout) == (0, (
        f"flushed 1 entry -> {vault.home}/threads/Projects/SGB/logs/{today}.md\n"
        "flushed 1 entries into 1 log file(s); buffer cleared.\n"))
    assert r.stderr == ("buffer: warning: flushed, but the task ingest failed: [Errno 13] "
                        f"Permission denied: '{notes / '2026-09-10-14-30-00.md.tmp'}'\n")
    assert vault.read("buffer.md") == ""
    assert vault.lines(f"threads/Projects/SGB/logs/{today}.md")[-2] == "TEXT: hello"
    assert vault.lines("threads/Projects/SGB/notes/2026-09-10-14-30-00.md")[-2] == "ACTION: stuck"


@pytest.mark.parametrize("target", ["Projects/sgb", "people/riaz arbi", "people/../threads/Projects/SGB"])
def test_add_ref_needs_the_exact_name_of_a_vault_file(buffer_vault, target):
    """Checked against the files in the vault, not by asking the filesystem,
    so a wrongly cased target is refused on macOS as on Linux, and `..`
    cannot reach out of the folder it names."""
    before = buffer_vault.snapshot()
    r = buffer_vault.run("add-ref", "Projects/SGB", target, cli="buffer")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == (f"buffer: error: ref target {target!r} does not resolve to a vault file "
                        "(expected <Kind>/<Name>, <Kind>/<Name>/hours, <Kind>/<Name>/payments, <Kind>/<Name>/logs/<date>, a note stem, or people/<Name>)\n")
    assert buffer_vault.snapshot() == before


# ---------- thread names are matched exactly, as `threads` lists them ----------

def test_add_refuses_a_wrongly_cased_thread(vault):
    """macOS ignores case, so asking the filesystem let `Projects/sgb`
    through, and flush wrote a wikilink that breaks on Linux."""
    vault.write_thread("Projects", "SGB")
    r = vault.run("add-text", "Projects/sgb", "wrong case", cli="buffer")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == "buffer: error: thread 'Projects/sgb' does not resolve to a thread file\n"
    assert not (vault.home / "buffer.md").exists()


def test_add_accepts_any_form_and_stores_the_canonical_name(vault):
    vault.write_thread("Projects", "SGB")
    for form in ("SGB", "[[Projects/SGB]]", "Projects/SGB"):
        r = vault.run("add-text", form, f"via {form}", cli="buffer")
        assert r.returncode == 0, r.stderr
    lines = vault.read("buffer.md").splitlines()
    assert [line.split(" TEXT:")[0] for line in lines] == ["- [[Projects/SGB]]"] * 3


def test_tend_flags_a_hand_written_wrongly_cased_thread(vault):
    vault.write_thread("Projects", "SGB")
    line = "- [[Projects/sgb]] TEXT: hand written <!--2026-09-10T09:00:00-->"
    vault.write("buffer.md", line + "\n")
    r = vault.run("tend", cli="buffer")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == ("buffer has 1 violation(s):\n"
                        "  buffer.md:1: thread 'Projects/sgb' does not resolve\n"
                        f"    line: {line}\n"
                        "    fix: edit via `buffer rm 1` and re-add via the matching `buffer add-*`\n")




def test_list_json_is_the_numbered_lines(vault):
    """`buffer list --json` gives the same lines the table shows, numbered,
    so a caller does not have to parse the padding."""
    vault.write_thread("Projects", "SGB")
    vault.run("add-text", "Projects/SGB", "first", cli="buffer")
    vault.run("add-text", "Projects/SGB", "second", cli="buffer")
    rows = json.loads(vault.run("list", "--json", cli="buffer").stdout)
    assert [r["line_no"] for r in rows] == [1, 2]
    assert [r["text"].split("TEXT: ")[1].split(" <!--")[0] for r in rows] == ["first", "second"]
    filtered = json.loads(vault.run("list", "second", "--json", cli="buffer").stdout)
    assert [r["line_no"] for r in filtered] == [2]


def test_date_files_every_add_under_the_day_it_happened(vault):
    """`--date` used to be on add-ref alone, though what it does — file the
    entry under the day the thing happened — is true of every entry."""
    vault.write_thread("Projects", "SGB")
    vault.write_note("2026-09-10-14-30-00", "TEXT: something", threads=["Projects/SGB"])
    vault.run("add-text", "Projects/SGB", "late note", "--date", "2026-09-10", cli="buffer")
    vault.run("add-action", "Projects/SGB", "late action", "--date", "2026-09-10", cli="buffer")
    vault.run("add", "late unknown", "--date", "2026-09-10", cli="buffer")
    vault.run("add-ref", "Projects/SGB", "2026-09-10-14-30-00", "seen",
              "--date", "2026-09-10", cli="buffer")
    stamps = [line.split("<!--")[1][:10] for line in vault.lines("buffer.md") if line.strip()]
    assert stamps == ["2026-09-10"] * 4
    bad = vault.run("add-text", "Projects/SGB", "x", "--date", "10 Sept", cli="buffer")
    assert (bad.returncode, bad.stderr) == (
        1, "buffer: error: --date must be YYYY-MM-DD; got '10 Sept'\n")
