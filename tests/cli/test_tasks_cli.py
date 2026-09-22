"""The `tasks` command: ingest ACTION lines into TASK anchors, list, next,
show, the anchor mutations, and add."""

import json
import re
from datetime import date

import pytest

UUID = r"[0-9a-f]{8}"


def setup_vault(vault, threads=(("Projects", "SGB"),), people=("Riaz Arbi",)):
    for kind, name in threads:
        vault.write_thread(kind, name)
    for p in people:
        vault.write_person(p)


def seed_note(vault, stem, *anchor_lines, threads=("Projects/SGB",)):
    return vault.write_note(stem, "\n".join(anchor_lines), threads=list(threads))


def anchor_lines(vault, relpath):
    """Every TASK:/DONE: line in the file, in order."""
    return [ln for ln in vault.lines(relpath)
            if ln.startswith("TASK:") or ln.startswith("DONE:")]


def first_anchor(vault, relpath):
    lines = anchor_lines(vault, relpath)
    assert lines, f"no TASK:/DONE: line in {relpath}"
    return lines[0]


@pytest.fixture
def base(vault):
    for t in ("Projects/SGB", "Projects/Alpha", "Topics/zeta"):
        vault.write_thread(*t.split("/"))
    vault.write_person("Riaz Arbi")
    vault.write_person("Charlie")
    return vault


KICKOFF_HEAD = ('---\ntopic: Kickoff\nthreads:\n  - "[[Projects/SGB]]"\n'
                '  - "[[Projects/Alpha]]"\n---\n\n')


@pytest.fixture
def inbox(base):
    """Notes with two good ACTIONs and five that fail for different reasons."""
    base.write("notes/2026-09-10-14-30-00.md", KICKOFF_HEAD +
          "ACTION: (Riaz Arbi) Draft the scope note <!--due:2026-09-20 priority:H depends:aaaa0001-->\n"
          "ACTION: " + "Long description " * 5 + "\n"
          "ACTION: bad attrs <!--due:soon priority:X depends:XYZ colour:red junk 2026-09-10T08:00:00-->\n"
          "ACTION: (Ghost) nobody\n"
          "ACTION:   \n"
          "TASK: [#L] (Charlie) Existing <!--aaaa0001 entry:2026-09-01 due:2026-09-05-->  \n")
    base.write("notes/2026-09-11-09-00-00.md", "---\ntopic: no threads\n---\n\nACTION: orphan\n")
    base.write("notes/2026-09-12-09-00-00.md",
          '---\ntopic: gone\nthreads:\n  - "[[Projects/Gone]]"\n---\n\nACTION: gone thread\n')
    return base


def failures(vault):
    kick = vault.home / "notes" / "2026-09-10-14-30-00.md"
    return ("\n5 action(s) NOT ingested (left as ACTION: in source):\n"
            f"  {kick}:10: due must be YYYY-MM-DD; got 'soon'\n"
            f"  {kick}:10: priority must be H, M, or L; got 'X'\n"
            f"  {kick}:10: depends must be 8 hex chars; got 'XYZ'\n"
            f"  {kick}:10: unknown attr 'colour'\n"
            f"  {kick}:10: unknown attr token 'junk'\n"
            f"  {kick}:11: assignee 'Ghost' does not resolve to people/Ghost.md\n"
            f"  {kick}:12: missing description\n"
            f"  {vault.home / 'notes' / '2026-09-11-09-00-00.md'}:5: note has no threads:\n"
            f"  {vault.home / 'notes' / '2026-09-12-09-00-00.md'}:7: thread 'Projects/Gone' does not resolve\n"
            "\n")


# ---------- ingest ----------

def test_ingest_basic_action(vault):
    setup_vault(vault)
    vault.write_note("2026-05-27-09-15-22",
        "ACTION: Pick up dry cleaning",
        threads=["Projects/SGB"])
    r = vault.run(cli="tasks")
    assert r.returncode == 0, r.stderr
    note = vault.read("notes/2026-05-27-09-15-22.md")
    assert "ACTION:" not in note
    assert re.search(
        r"^TASK: Pick up dry cleaning <!--[a-f0-9]{8} entry:\d{4}-\d{2}-\d{2}-->  $",
        note, re.MULTILINE), note


def test_ingest_appends_markdown_hard_break(vault):
    # Each ingested anchor must end with two trailing spaces (a Markdown
    # hard line break) so pandoc renders consecutive tasks on separate
    # lines in the PDF instead of soft-wrapping them into one paragraph.
    setup_vault(vault)
    vault.write_note("2026-05-27-09-15-22",
        "ACTION: First thing\nACTION: Second thing",
        threads=["Projects/SGB"])
    r = vault.run(cli="tasks")
    assert r.returncode == 0, r.stderr
    lines = anchor_lines(vault, "notes/2026-05-27-09-15-22.md")
    assert len(lines) == 2, lines
    for ln in lines:
        assert ln.endswith("-->  "), repr(ln)


def test_ingest_with_assignee_and_attrs(vault):
    setup_vault(vault)
    vault.write_note("2026-05-27-09-15-22",
        "ACTION: (Riaz Arbi) Send report "
        "<!--2026-05-27T09:15:22 due:2026-05-29 priority:H-->",
        threads=["Projects/SGB"])
    r = vault.run(cli="tasks")
    assert r.returncode == 0, r.stderr
    note = vault.read("notes/2026-05-27-09-15-22.md")
    assert re.search(
        r"^TASK: \[#H\] \(Riaz Arbi\) Send report "
        r"<!--[a-f0-9]{8} entry:\d{4}-\d{2}-\d{2} due:2026-05-29-->  $",
        note, re.MULTILINE), note


def test_ingest_unresolved_assignee_fails(vault):
    setup_vault(vault)  # only Riaz Arbi exists
    vault.write_note("2026-05-27-09-15-22",
        "ACTION: (Ghost) Phantom",
        threads=["Projects/SGB"])
    before = vault.read("notes/2026-05-27-09-15-22.md")
    r = vault.run(cli="tasks")
    path = vault.home / "notes" / "2026-05-27-09-15-22.md"
    assert (r.returncode, r.stdout) == (1, "Ingested: 0.  Failed: 1.\n")
    assert r.stderr == ("\n1 action(s) NOT ingested (left as ACTION: in source):\n"
                        f"  {path}:9: assignee 'Ghost' does not resolve to people/Ghost.md\n\n")
    assert vault.read("notes/2026-05-27-09-15-22.md") == before


def test_ingest_unresolved_thread_fails(vault):
    setup_vault(vault, threads=(("Projects", "SGB"),))
    vault.write_note("2026-05-27-09-15-22",
        "ACTION: Refers to a missing thread",
        threads=["Projects/Nope"])
    before = vault.read("notes/2026-05-27-09-15-22.md")
    r = vault.run(cli="tasks")
    path = vault.home / "notes" / "2026-05-27-09-15-22.md"
    assert (r.returncode, r.stdout) == (1, "Ingested: 0.  Failed: 1.\n")
    assert r.stderr == ("\n1 action(s) NOT ingested (left as ACTION: in source):\n"
                        f"  {path}:9: thread 'Projects/Nope' does not resolve\n\n")
    assert vault.read("notes/2026-05-27-09-15-22.md") == before


def test_ingest_idempotent(vault):
    """Re-running ingest on a vault with no ACTION lines is a no-op."""
    setup_vault(vault)
    vault.write_note("2026-05-27-09-15-22",
        "ACTION: Once",
        threads=["Projects/SGB"])
    vault.run(cli="tasks")
    before = vault.read("notes/2026-05-27-09-15-22.md")
    vault.run(cli="tasks")
    after = vault.read("notes/2026-05-27-09-15-22.md")
    assert before == after


def test_ingest_generates_unique_uuids(vault):
    setup_vault(vault)
    vault.write_note("2026-05-27-09-15-22",
        "ACTION: First\nACTION: Second\nACTION: Third",
        threads=["Projects/SGB"])
    vault.run(cli="tasks")
    note = vault.read("notes/2026-05-27-09-15-22.md")
    uuids = re.findall(r"<!--([a-f0-9]{8}) ", note)
    assert len(uuids) == 3
    assert len(set(uuids)) == 3


def test_dry_run_shows_the_anchors_and_writes_nothing(inbox):
    before = inbox.read("notes/2026-09-10-14-30-00.md")
    r = inbox.run("--dry-run", cli="tasks")
    assert r.returncode == 1
    day = r"\d{4}-\d{2}-\d{2}"
    lines = r.stdout.splitlines()
    assert len(lines) == 3
    assert re.fullmatch(rf"would: TASK: \[#H\] \(Riaz Arbi\) Draft the scope note "
                        rf"<!--{UUID} entry:{day} due:2026-09-20 depends:aaaa0001-->  ", lines[0])
    assert re.fullmatch(rf"would: TASK: (Long description ){{4}}Long description "
                        rf"<!--{UUID} entry:{day}-->  ", lines[1])
    assert lines[2] == "Ingested: 0.  Failed: 5."
    assert r.stderr == failures(inbox)
    assert inbox.read("notes/2026-09-10-14-30-00.md") == before


def test_dry_run_quiet_prints_only_failures(inbox):
    r = inbox.run("--dry-run", "--quiet", cli="tasks")
    assert (r.returncode, r.stdout, r.stderr) == (1, "", failures(inbox))


def test_ingest_rewrites_good_actions_in_place_and_leaves_the_rest(inbox):
    r = inbox.run(cli="tasks")
    kick = inbox.home / "notes" / "2026-09-10-14-30-00.md"
    assert r.returncode == 1
    out = r.stdout.splitlines()
    assert re.fullmatch(rf"ingested: {UUID}  {re.escape(str(kick))}:8  Draft the scope note", out[0])
    assert re.fullmatch(rf"ingested: {UUID}  {re.escape(str(kick))}:9  "
                        r"Long description Long description Long description Long desc\.\.\.", out[1])
    assert out[2] == "Ingested: 2.  Failed: 5."
    assert r.stderr == failures(inbox)
    assert re.fullmatch(
        re.escape(KICKOFF_HEAD)
        + rf"TASK: \[#H\] \(Riaz Arbi\) Draft the scope note <!--{UUID} entry:\d{{4}}-\d{{2}}-\d{{2}} "
          r"due:2026-09-20 depends:aaaa0001-->  \n"
        + rf"TASK: (Long description ){{4}}Long description <!--{UUID} entry:\d{{4}}-\d{{2}}-\d{{2}}-->  \n"
        + re.escape("ACTION: bad attrs <!--due:soon priority:X depends:XYZ colour:red junk 2026-09-10T08:00:00-->\n"
                    "ACTION: (Ghost) nobody\n"
                    "ACTION:   \n"
                    "TASK: [#L] (Charlie) Existing <!--aaaa0001 entry:2026-09-01 due:2026-09-05-->  \n"),
        inbox.read("notes/2026-09-10-14-30-00.md"))


def test_ingest_with_nothing_to_do(base):
    r = base.run(cli="tasks")
    assert (r.returncode, r.stdout, r.stderr) == (0, "Ingested: 0.  Failed: 0.\n", "")
    assert base.run("--quiet", cli="tasks").stdout == ""


# ---------- list, next, show ----------

@pytest.fixture
def board(base):
    base.write("notes/2026-09-10-14-30-00.md", KICKOFF_HEAD +
          "TASK: [#H] (Riaz Arbi) Draft the scope note <!--dddd0001 entry:2026-09-10 due:2026-09-20 depends:aaaa0001-->  \n"
          "TASK: [#L] (Charlie) Existing <!--aaaa0001 entry:2026-09-01 due:2026-09-05-->  \n"
          "DONE: Finished <!--aaaa0002 entry:2026-08-01 end:2026-08-03-->\n")
    base.write("logs/Topics/zeta/2026-09-13.md",
          '---\nthread: "[[Topics/zeta]]"\ndate: 2026-09-13\n---\n\n'
          "TASK: log task <!--bbbb0001 entry:2026-09-13 scheduled:2026-09-30-->\n"
          "TASK: [#M] second log task <!--aaaa0003 entry:2026-09-13-->\n")
    base.write("notes/2026-09-14-09-00-00.md", "---\ntopic: x\n---\n\nTASK: unthreaded <!--cccc0001 entry:2026-09-14-->\n")
    return base


def test_list_table(board):
    assert board.run("list", cli="tasks").stdout == (
        "dddd0001  [#H]  Projects/SGB +1  (Riaz Arbi)  Draft the scope note  due:2026-09-20\n"
        "aaaa0001  [#L]  Projects/SGB +1  (Charlie)    Existing              due:2026-09-05\n"
        "aaaa0003  [#M]  Topics/zeta                   second log task\n"
        "bbbb0001        Topics/zeta                   log task\n"
        "cccc0001        -                             unthreaded\n")


def test_list_filters(board):
    assert board.run("list", "--thread", "Projects/Alpha", cli="tasks").stdout.count("\n") == 2
    assert board.run("list", "--priority", "M", cli="tasks").stdout == \
        "aaaa0003  [#M]  Topics/zeta    second log task\n"
    assert board.run("list", "--assignee", "Charlie", cli="tasks").stdout.startswith("aaaa0001")
    assert board.run("list", "--thread", "Projects/Nope", cli="tasks").stdout == "(no tasks)\n"


def test_list_shows_only_pending(vault):
    setup_vault(vault)
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: pending one <!--abcd1234 entry:2026-05-20-->\n"
        "DONE: completed one <!--ef567890 entry:2026-05-20 end:2026-05-25-->")
    r = vault.run("list", cli="tasks")
    assert (r.returncode, r.stdout, r.stderr) == (0, (
        "abcd1234        Projects/SGB    pending one\n"), "")


def test_list_priority_filter(vault):
    setup_vault(vault)
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: [#H] high prio <!--abcd1234 entry:2026-05-20-->\n"
        "TASK: [#L] low prio <!--ef567890 entry:2026-05-20-->")
    r = vault.run("list", "--priority", "H", cli="tasks")
    assert (r.returncode, r.stdout, r.stderr) == (0, (
        "abcd1234  [#H]  Projects/SGB    high prio\n"), "")


def test_list_assignee_filter(vault):
    setup_vault(vault, people=("Riaz Arbi", "Charlie"))
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: (Riaz Arbi) mine <!--abcd1234 entry:2026-05-20-->\n"
        "TASK: (Charlie) theirs <!--ef567890 entry:2026-05-20-->")
    r = vault.run("list", "--assignee", "Charlie", cli="tasks")
    assert (r.returncode, r.stdout, r.stderr) == (0, (
        "ef567890        Projects/SGB  (Charlie)  theirs\n"), "")


def test_list_overdue_filter(vault):
    setup_vault(vault)
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: overdue <!--abcd1234 entry:2026-05-20 due:2000-01-01-->\n"
        "TASK: future <!--ef567890 entry:2026-05-20 due:2099-01-01-->\n"
        "TASK: no-due <!--beef0000 entry:2026-05-20-->")
    r = vault.run("list", "--overdue", cli="tasks")
    assert (r.returncode, r.stdout, r.stderr) == (0, (
        "abcd1234        Projects/SGB    overdue  due:2000-01-01\n"), "")


def test_list_thread_filter(vault):
    setup_vault(vault, threads=(("Projects", "SGB"), ("Projects", "Other")))
    vault.write_note("2026-05-27-09-15-22",
        "TASK: in SGB <!--abcd1234 entry:2026-05-20-->",
        threads=["Projects/SGB"])
    vault.write_note("2026-05-27-10-30-00",
        "TASK: in Other <!--ef567890 entry:2026-05-20-->",
        threads=["Projects/Other"])
    r = vault.run("list", "--thread", "Projects/SGB", cli="tasks")
    assert (r.returncode, r.stdout, r.stderr) == (0, (
        "abcd1234        Projects/SGB    in SGB\n"), "")


def test_list_sorts_by_thread_alphabetically(vault):
    """Thread order beats priority; priority still orders within a thread."""
    setup_vault(vault, threads=(("Projects", "Zed"), ("Projects", "Alpha")))
    vault.write_note("2026-05-27-09-15-22",
        "TASK: [#H] zed-high <!--abcd1234 entry:2026-05-20-->",
        threads=["Projects/Zed"])
    vault.write_note("2026-05-27-10-30-00",
        "TASK: alpha-none <!--ef567890 entry:2026-05-20-->\n"
        "TASK: [#L] alpha-low <!--ef567891 entry:2026-05-20-->",
        threads=["Projects/Alpha"])
    r = vault.run("list", cli="tasks")
    assert (r.returncode, r.stdout, r.stderr) == (0, (
        "ef567891  [#L]  Projects/Alpha    alpha-low\n"
        "ef567890        Projects/Alpha    alpha-none\n"
        "abcd1234  [#H]  Projects/Zed      zed-high\n"), "")


def test_next_orders_by_priority_due_entry(board):
    assert board.run("next", cli="tasks").stdout == (
        "dddd0001  [#H]  Projects/SGB +1  (Riaz Arbi)  Draft the scope note  due:2026-09-20\n"
        "aaaa0003  [#M]  Topics/zeta                   second log task\n"
        "aaaa0001  [#L]  Projects/SGB +1  (Charlie)    Existing              due:2026-09-05\n"
        "bbbb0001        Topics/zeta                   log task\n"
        "cccc0001        -                             unthreaded\n")


def test_next_shows_the_first_5(vault):
    setup_vault(vault)
    lines = [f"TASK: t{i} <!--abc1{i:04x} entry:2026-05-20-->" for i in range(8)]
    seed_note(vault, "2026-05-27-09-15-22", "\n".join(lines))
    r = vault.run("next", cli="tasks")
    assert r.returncode == 0
    # Eight tasks tie on priority, due and entry, so they keep file order.
    shown = re.findall(r"\babc1[0-9a-f]{4}\b", r.stdout)
    assert shown == [f"abc1{i:04x}" for i in range(5)]


def test_show(board):
    assert board.run("show", "aaaa0001", cli="tasks").stdout == (
        "uuid:        aaaa0001\n"
        "kind:        TASK\n"
        "priority:    L\n"
        "assignee:    Charlie\n"
        "threads:     Projects/SGB, Projects/Alpha\n"
        "source:      notes/2026-09-10-14-30-00.md:9\n"
        "body:        Existing\n"
        "entry:       2026-09-01\n"
        "end:         -\n"
        "due:         2026-09-05\n"
        "scheduled:   -\n"
        "depends:     -\n")
    assert board.run("show", "dddd", cli="tasks").stdout.splitlines()[-1] == "depends:     aaaa0001"
    assert board.run("show", "cccc0001", cli="tasks").stdout.splitlines()[4] == "threads:     -"


def test_uuid_prefix_errors(board):
    # DEFERRED BUG 7: the ambiguous-prefix error names files by basename,
    # not by vault path.
    r = board.run("show", "aaaa", cli="tasks")
    assert (r.returncode, r.stderr) == (1, "tasks: error: uuid prefix 'aaaa' is ambiguous: "
                                           "aaaa0001 (2026-09-10-14-30-00.md:9), "
                                           "aaaa0002 (2026-09-10-14-30-00.md:10), "
                                           "aaaa0003 (2026-09-13.md:7)\n")
    r = board.run("show", "ffff", cli="tasks")
    assert (r.returncode, r.stderr) == (1, "tasks: error: no task found with uuid prefix 'ffff'\n")


# ---------- mutations ----------

def test_mutations_print_and_rewrite_the_line(board):
    steps = [
        (["done", "aaaa0002"], 0, "aaaa0002 already done\n"),
        (["done", "bbbb0001"], 0, "done: bbbb0001  log task\n"),
        (["set-description", "bbbb0001", "renamed log task"], 0, "updated: bbbb0001  body=renamed log task\n"),
        (["set-assignee", "bbbb0001", "people/Charlie"], 0, "updated: bbbb0001  assignee=Charlie\n"),
        (["set-due", "bbbb0001", "2026-10-01"], 0, "updated: bbbb0001  due=2026-10-01\n"),
        (["set-scheduled", "bbbb0001", "2026-09-25"], 0, "updated: bbbb0001  scheduled=2026-09-25\n"),
        (["set-priority", "bbbb0001", "L"], 0, "updated: bbbb0001  priority=L\n"),
        (["add-depends", "aaaa0003", "cccc0001"], 0, "aaaa0003 now depends on cccc0001\n"),
        (["add-depends", "aaaa0003", "cccc"], 0, "aaaa0003 already depends on cccc0001\n"),
        (["add-depends", "aaaa0003", "dddd0001"], 0, "aaaa0003 now depends on dddd0001\n"),
        (["rm-depends", "aaaa0003", "bbbb0001"], 0, "aaaa0003 did not depend on bbbb0001\n"),
        (["rm-depends", "aaaa0003", "cccc0001"], 0, "aaaa0003 no longer depends on cccc0001\n"),
        # Replacing a value already there, not adding a second one.
        (["set-priority", "aaaa0003", "H"], 0, "updated: aaaa0003  priority=H\n"),
        (["set-due", "aaaa0001", "2026-10-10"], 0, "updated: aaaa0001  due=2026-10-10\n"),
    ]
    for argv, rc, out in steps:
        r = board.run(*argv, cli="tasks")
        assert (r.returncode, r.stdout, r.stderr) == (rc, out, ""), argv
    assert board.read("logs/Topics/zeta/2026-09-13.md") == (
        '---\nthread: "[[Topics/zeta]]"\ndate: 2026-09-13\n---\n\n'
        f"DONE: [#L] (Charlie) renamed log task <!--bbbb0001 entry:2026-09-13 end:{date.today().isoformat()} "
        "due:2026-10-01 scheduled:2026-09-25-->  \n"
        "TASK: [#H] second log task <!--aaaa0003 entry:2026-09-13 depends:dddd0001-->  \n")
    assert board.lines("notes/2026-09-10-14-30-00.md")[8] == (
        "TASK: [#L] (Charlie) Existing <!--aaaa0001 entry:2026-09-01 due:2026-10-10-->  ")


@pytest.mark.parametrize("argv, message", [
    (["set-description", "bbbb0001", "  "], "tasks: error: description is empty"),
    (["set-assignee", "bbbb0001", "Ghost"], "tasks: error: person 'Ghost' does not resolve to people/Ghost.md"),
    # DEFERRED BUG 7: the date errors use a comma where every other error
    # uses a semicolon.
    (["set-due", "bbbb0001", "soon"], "tasks: error: date must be YYYY-MM-DD, got 'soon'"),
    (["set-scheduled", "bbbb0001", "30/9"], "tasks: error: date must be YYYY-MM-DD, got '30/9'"),
    (["add-depends", "aaaa0003", "aaaa0003"], "tasks: error: a task cannot depend on itself"),
])
def test_mutation_errors_leave_the_file_alone(board, argv, message):
    before = board.read("logs/Topics/zeta/2026-09-13.md")
    r = board.run(*argv, cli="tasks")
    assert (r.returncode, r.stdout, r.stderr) == (1, "", message + "\n")
    assert board.read("logs/Topics/zeta/2026-09-13.md") == before


def test_done_flips_kind_and_stamps_end(vault):
    setup_vault(vault)
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: Send report <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("done", "abcd1234", cli="tasks")
    assert r.returncode == 0, r.stderr
    assert r.stdout == "done: abcd1234  Send report\n"
    assert first_anchor(vault, "notes/2026-05-27-09-15-22.md") == (
        f"DONE: Send report <!--abcd1234 entry:2026-05-20 end:{date.today().isoformat()}-->  ")


def test_rm_depends_unknown_target_fails(vault):
    """A prefix that is neither one of the task's dependencies nor any task
    is an error, and nothing is written."""
    setup_vault(vault)
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: t <!--abcd1234 entry:2026-05-20-->")
    before = vault.read("notes/2026-05-27-09-15-22.md")
    r = vault.run("rm-depends", "abcd1234", "deadbeef", cli="tasks")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == "tasks: error: no task found with uuid prefix 'deadbeef'\n"
    assert vault.read("notes/2026-05-27-09-15-22.md") == before


def test_set_priority_takes_only_h_m_or_l(board):
    before = board.snapshot()
    r = board.run("set-priority", "bbbb0001", "Z", cli="tasks")
    assert (r.returncode, r.stdout) == (2, "")
    assert r.stderr.splitlines()[-1] == (
        "tasks set-priority: error: argument priority: invalid choice: 'Z' (choose from 'H', 'M', 'L')")
    assert board.snapshot() == before


# ---------- add ----------

def test_add_passes_every_flag_to_the_buffer(base):
    r = base.run("add", "Projects/SGB", "(Charlie) via tasks add", "--due", "2026-10-02",
              "--scheduled", "2026-10-01", "--priority", "M", "--depends", "bbbb0001",
              "--depends", "aaaa0001", cli="tasks")
    assert r.returncode == 0
    line = (r"- \[\[Projects/SGB\]\] ACTION: \(Charlie\) via tasks add "
            r"<!--\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d depends:aaaa0001 depends:bbbb0001 "
            r"due:2026-10-02 priority:M scheduled:2026-10-01-->")
    assert re.fullmatch(f"buffered: {line}\n", r.stdout)
    assert re.fullmatch(f"{line}\n", base.read("buffer.md"))


def test_add_passes_the_buffer_exit_code_through(base):
    r = base.run("add", "Projects/Nope", "x", cli="tasks")
    assert r.returncode == 1
    assert r.stderr == "tasks: error: thread 'Projects/Nope' does not resolve to a thread file\n"


# ---------- end to end ----------

def test_full_lifecycle(vault):
    """ACTION -> ingest -> set-priority -> set-due -> done."""
    setup_vault(vault)
    vault.write_note("2026-05-27-09-15-22",
        "ACTION: (Riaz Arbi) lifecycle test",
        threads=["Projects/SGB"])
    r = vault.run(cli="tasks")
    assert r.returncode == 0
    note = vault.read("notes/2026-05-27-09-15-22.md")
    m = re.search(r"<!--([a-f0-9]{8}) entry:", note)
    assert m, note
    u = m.group(1)

    r = vault.run("set-priority", u, "H", cli="tasks")
    assert r.returncode == 0
    r = vault.run("set-due", u, "2026-06-15", cli="tasks")
    assert r.returncode == 0
    r = vault.run("done", u, cli="tasks")
    assert r.returncode == 0

    note = vault.read("notes/2026-05-27-09-15-22.md")
    assert "DONE: [#H] (Riaz Arbi) lifecycle test" in note
    assert "due:2026-06-15" in note
    assert "end:" in note

    # Migrated file passes lint.
    lint = vault.run(cli="lint")
    assert lint.returncode == 0, lint.stdout


@pytest.mark.parametrize("argv", [["rm-depends", "aaaa0003", ""], ["rm-depends", "aaaa0003", "  "],
                                  ["add-depends", "aaaa0003", ""], ["show", ""]])
def test_an_empty_uuid_prefix_is_refused(board, argv):
    """An empty prefix matches everything: `rm-depends X ""` silently removed
    the task's only dependency."""
    board.run("add-depends", "aaaa0003", "dddd0001", cli="tasks")
    before = board.snapshot()
    r = board.run(*argv, cli="tasks")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == "tasks: error: give a uuid prefix; got an empty one\n"
    assert board.snapshot() == before


def test_rm_depends_refuses_a_prefix_matching_two_dependencies(board):
    board.run("add-depends", "aaaa0003", "aaaa0001", cli="tasks")
    board.run("add-depends", "aaaa0003", "aaaa0002", cli="tasks")
    before = board.snapshot()
    r = board.run("rm-depends", "aaaa0003", "aaaa", cli="tasks")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == "tasks: error: uuid prefix 'aaaa' is ambiguous: aaaa0001, aaaa0002\n"
    assert board.snapshot() == before


def test_ingest_leaves_an_action_under_a_wrongly_cased_thread(vault):
    vault.write_thread("Projects", "SGB")
    note = vault.write_note("2026-09-10-14-30-00", "ACTION: do it", threads=["Projects/sgb"])
    before = note.read_text(encoding="utf-8")
    r = vault.run(cli="tasks")
    assert (r.returncode, r.stdout) == (1, "Ingested: 0.  Failed: 1.\n")
    assert r.stderr == ("\n1 action(s) NOT ingested (left as ACTION: in source):\n"
                        f"  {note}:9: thread 'Projects/sgb' does not resolve\n\n")
    assert note.read_text(encoding="utf-8") == before


def test_rm_depends_removes_a_dependency_whose_task_is_gone(vault):
    """Looking the depended-on task up would fail, so the dependency is
    matched against the task's own list first."""
    vault.write_thread("Projects", "SGB")
    note = vault.write_note("2026-09-10-14-30-00",
                            "TASK: needs gone <!--bbbb0001 entry:2026-09-01 depends:dead0001-->",
                            threads=["Projects/SGB"])
    r = vault.run("rm-depends", "bbbb0001", "dead", cli="tasks")
    assert (r.returncode, r.stdout, r.stderr) == (0, "bbbb0001 no longer depends on dead0001\n", "")
    assert note.read_text(encoding="utf-8").split("\n")[8] == "TASK: needs gone <!--bbbb0001 entry:2026-09-01-->  "


def test_ingest_reports_a_file_that_is_not_utf8_and_carries_on(vault):
    vault.write_thread("Projects", "SGB")
    bad = vault.home / "logs" / "Projects" / "SGB" / "2026-09-12.md"
    bad.parent.mkdir(parents=True)
    bad.write_bytes(b"---\nthread: x\n---\n\xff\xfe bad bytes\nACTION: unreachable\n")
    good = vault.write_note("2026-09-10-14-30-00", "ACTION: do it", threads=["Projects/SGB"])
    r = vault.run(cli="tasks")
    assert r.returncode == 1
    assert re.fullmatch(rf"ingested: [0-9a-f]{{8}}  {re.escape(str(good))}:9  do it\nIngested: 1.  Failed: 1.\n", r.stdout)
    assert r.stderr == ("\n1 action(s) NOT ingested (left as ACTION: in source):\n"
                        f"  {bad}: file is not valid UTF-8; skipped\n\n")
    assert vault.run("list", cli="tasks").returncode == 0


def test_depends_help_says_a_whole_uuid(vault):
    manifest = json.loads(vault.run("--help-json", cli="tasks").stdout)
    [sub] = [s for s in manifest["subcommands"] if s["name"] == "add"]
    [flag] = [f for f in sub["flags"] if f["name"] == "--depends"]
    assert flag["description"] == "A task's 8-character uuid, from `tasks list`; repeatable."
