"""The `tasks` command: ingest ACTION lines into TASK anchors, list, next,
show, the anchor mutations, and add."""

import re
from datetime import date

import pytest

UUID = r"[0-9a-f]{8}"


def tasks(vault, *argv):
    return vault.run(*argv, cli="tasks", input="")


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
    r = tasks(inbox, "--dry-run")
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
    r = tasks(inbox, "--dry-run", "--quiet")
    assert (r.returncode, r.stdout, r.stderr) == (1, "", failures(inbox))


def test_ingest_rewrites_good_actions_in_place_and_leaves_the_rest(inbox):
    r = tasks(inbox)
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
    r = tasks(base)
    assert (r.returncode, r.stdout, r.stderr) == (0, "Ingested: 0.  Failed: 0.\n", "")
    assert tasks(base, "--quiet").stdout == ""


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
    assert tasks(board, "list").stdout == (
        "dddd0001  [#H]  Projects/SGB +1  (Riaz Arbi)  Draft the scope note  due:2026-09-20\n"
        "aaaa0001  [#L]  Projects/SGB +1  (Charlie)    Existing              due:2026-09-05\n"
        "aaaa0003  [#M]  Topics/zeta                   second log task\n"
        "bbbb0001        Topics/zeta                   log task\n"
        "cccc0001        -                             unthreaded\n")


def test_list_filters(board):
    assert tasks(board, "list", "--thread", "Projects/Alpha").stdout.count("\n") == 2
    assert tasks(board, "list", "--priority", "M").stdout == \
        "aaaa0003  [#M]  Topics/zeta    second log task\n"
    assert tasks(board, "list", "--assignee", "Charlie").stdout.startswith("aaaa0001")
    assert tasks(board, "list", "--thread", "Projects/Nope").stdout == "(no tasks)\n"


def test_list_shows_only_pending(vault):
    setup_vault(vault)
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: pending one <!--abcd1234 entry:2026-05-20-->\n"
        "DONE: completed one <!--ef567890 entry:2026-05-20 end:2026-05-25-->")
    r = vault.run("list", cli="tasks")
    assert r.returncode == 0
    assert "pending one" in r.stdout
    assert "completed one" not in r.stdout


def test_list_priority_filter(vault):
    setup_vault(vault)
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: [#H] high prio <!--abcd1234 entry:2026-05-20-->\n"
        "TASK: [#L] low prio <!--ef567890 entry:2026-05-20-->")
    r = vault.run("list", "--priority", "H", cli="tasks")
    assert "high prio" in r.stdout
    assert "low prio" not in r.stdout


def test_list_assignee_filter(vault):
    setup_vault(vault, people=("Riaz Arbi", "Charlie"))
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: (Riaz Arbi) mine <!--abcd1234 entry:2026-05-20-->\n"
        "TASK: (Charlie) theirs <!--ef567890 entry:2026-05-20-->")
    r = vault.run("list", "--assignee", "Charlie", cli="tasks")
    assert "theirs" in r.stdout
    assert "mine" not in r.stdout


def test_list_overdue_filter(vault):
    setup_vault(vault)
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: overdue <!--abcd1234 entry:2026-05-20 due:2000-01-01-->\n"
        "TASK: future <!--ef567890 entry:2026-05-20 due:2099-01-01-->\n"
        "TASK: no-due <!--beef0000 entry:2026-05-20-->")
    r = vault.run("list", "--overdue", cli="tasks")
    assert "overdue" in r.stdout
    assert "future" not in r.stdout
    assert "no-due" not in r.stdout


def test_list_thread_filter(vault):
    setup_vault(vault, threads=(("Projects", "SGB"), ("Projects", "Other")))
    vault.write_note("2026-05-27-09-15-22",
        "TASK: in SGB <!--abcd1234 entry:2026-05-20-->",
        threads=["Projects/SGB"])
    vault.write_note("2026-05-27-10-30-00",
        "TASK: in Other <!--ef567890 entry:2026-05-20-->",
        threads=["Projects/Other"])
    r = vault.run("list", "--thread", "Projects/SGB", cli="tasks")
    assert "in SGB" in r.stdout
    assert "in Other" not in r.stdout


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
    pos_low = r.stdout.find("alpha-low")
    pos_none = r.stdout.find("alpha-none")
    pos_zed = r.stdout.find("zed-high")
    assert 0 <= pos_low < pos_none < pos_zed


def test_next_orders_by_priority_due_entry(board):
    assert tasks(board, "next").stdout == (
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


def test_next_sort_priority_first(vault):
    """H sorts before M sorts before L sorts before none."""
    setup_vault(vault)
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: none <!--abc10000 entry:2026-05-20-->\n"
        "TASK: [#L] low <!--abc10001 entry:2026-05-20-->\n"
        "TASK: [#H] high <!--abc10002 entry:2026-05-20-->\n"
        "TASK: [#M] mid <!--abc10003 entry:2026-05-20-->")
    r = vault.run("next", cli="tasks")
    pos_high = r.stdout.find("high")
    pos_mid = r.stdout.find("mid")
    pos_low = r.stdout.find("low")
    pos_none = r.stdout.find("none")
    assert 0 <= pos_high < pos_mid < pos_low < pos_none


def test_show(board):
    assert tasks(board, "show", "aaaa0001").stdout == (
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
    assert tasks(board, "show", "dddd").stdout.splitlines()[-1] == "depends:     aaaa0001"
    assert tasks(board, "show", "cccc0001").stdout.splitlines()[4] == "threads:     -"


def test_uuid_prefix_errors(board):
    # DEFERRED BUG 7: the ambiguous-prefix error names files by basename,
    # not by vault path.
    r = tasks(board, "show", "aaaa")
    assert (r.returncode, r.stderr) == (1, "tasks: error: uuid prefix 'aaaa' is ambiguous: "
                                           "aaaa0001 (2026-09-10-14-30-00.md:9), "
                                           "aaaa0002 (2026-09-10-14-30-00.md:10), "
                                           "aaaa0003 (2026-09-13.md:7)\n")
    r = tasks(board, "show", "ffff")
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
    ]
    for argv, rc, out in steps:
        r = tasks(board, *argv)
        assert (r.returncode, r.stdout, r.stderr) == (rc, out, ""), argv
    text = board.read("logs/Topics/zeta/2026-09-13.md")
    today = re.search(r"end:(\S+)", text).group(1)
    assert text == (
        '---\nthread: "[[Topics/zeta]]"\ndate: 2026-09-13\n---\n\n'
        f"DONE: [#L] (Charlie) renamed log task <!--bbbb0001 entry:2026-09-13 end:{today} "
        "due:2026-10-01 scheduled:2026-09-25-->  \n"
        "TASK: [#M] second log task <!--aaaa0003 entry:2026-09-13 depends:dddd0001-->  \n")


@pytest.mark.parametrize("argv, message", [
    (["set-description", "bbbb0001", "  "], "tasks: error: description is empty"),
    (["set-assignee", "bbbb0001", "Ghost"], "tasks: error: person 'Ghost' does not resolve to people/Ghost.md"),
    # DEFERRED BUG 7: the date errors use a comma where every other error
    # uses a semicolon.
    (["set-due", "bbbb0001", "soon"], "tasks: error: date must be YYYY-MM-DD, got 'soon'"),
    (["set-scheduled", "bbbb0001", "30/9"], "tasks: error: date must be YYYY-MM-DD, got '30/9'"),
    (["set-priority", "bbbb0001", "Z"], "tasks: error: priority must be H, M, or L; got 'Z'"),
    (["add-depends", "aaaa0003", "aaaa0003"], "tasks: error: a task cannot depend on itself"),
])
def test_mutation_errors_leave_the_file_alone(board, argv, message):
    before = board.read("logs/Topics/zeta/2026-09-13.md")
    r = tasks(board, *argv)
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


def test_done_is_idempotent(vault):
    setup_vault(vault)
    seed_note(vault, "2026-05-27-09-15-22",
        "DONE: Already <!--abcd1234 entry:2026-05-20 end:2026-05-25-->")
    r = vault.run("done", "abcd1234", cli="tasks")
    assert r.returncode == 0
    line = first_anchor(vault, "notes/2026-05-27-09-15-22.md")
    assert "end:2026-05-25" in line  # untouched


def test_set_description_rewrites_body(vault):
    setup_vault(vault)
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: old text <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("set-description", "abcd1234", "new text", cli="tasks")
    assert r.returncode == 0
    line = first_anchor(vault, "notes/2026-05-27-09-15-22.md")
    assert "TASK: new text <!--abcd1234" in line


def test_set_assignee_writes_prefix(vault):
    setup_vault(vault, people=("Riaz Arbi", "Charlie"))
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: shared task <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("set-assignee", "abcd1234", "Charlie", cli="tasks")
    assert r.returncode == 0
    line = first_anchor(vault, "notes/2026-05-27-09-15-22.md")
    assert "TASK: (Charlie) shared task <!--abcd1234" in line


def test_set_due_inserts_attr(vault):
    setup_vault(vault)
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: t <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("set-due", "abcd1234", "2026-06-01", cli="tasks")
    assert r.returncode == 0
    line = first_anchor(vault, "notes/2026-05-27-09-15-22.md")
    assert "due:2026-06-01" in line


def test_set_due_replaces_existing(vault):
    setup_vault(vault)
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: t <!--abcd1234 entry:2026-05-20 due:2026-05-25-->")
    r = vault.run("set-due", "abcd1234", "2026-06-01", cli="tasks")
    assert r.returncode == 0
    line = first_anchor(vault, "notes/2026-05-27-09-15-22.md")
    assert "due:2026-06-01" in line
    assert "due:2026-05-25" not in line


def test_set_scheduled_inserts_attr(vault):
    setup_vault(vault)
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: t <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("set-scheduled", "abcd1234", "2026-06-05", cli="tasks")
    assert r.returncode == 0
    line = first_anchor(vault, "notes/2026-05-27-09-15-22.md")
    assert "scheduled:2026-06-05" in line


def test_set_priority_writes_visible_token(vault):
    setup_vault(vault)
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: t <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("set-priority", "abcd1234", "H", cli="tasks")
    assert r.returncode == 0
    line = first_anchor(vault, "notes/2026-05-27-09-15-22.md")
    assert line.startswith("TASK: [#H] t <!--abcd1234")
    # Priority must NOT leak into attrs blob:
    assert "priority:H" not in line


def test_set_priority_replaces_existing(vault):
    setup_vault(vault)
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: [#H] t <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("set-priority", "abcd1234", "M", cli="tasks")
    assert r.returncode == 0
    line = first_anchor(vault, "notes/2026-05-27-09-15-22.md")
    assert "[#M]" in line and "[#H]" not in line


def test_add_depends_appends(vault):
    setup_vault(vault)
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: dep target <!--beef0000 entry:2026-05-20-->\n"
        "TASK: dependent <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("add-depends", "abcd1234", "beef0000", cli="tasks")
    assert r.returncode == 0
    # The dependent is the second TASK line; index 1.
    line = anchor_lines(vault, "notes/2026-05-27-09-15-22.md")[1]
    assert "depends:beef0000" in line


def test_rm_depends_removes(vault):
    setup_vault(vault)
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: dep <!--beef0000 entry:2026-05-20-->\n"
        "TASK: dependent <!--abcd1234 entry:2026-05-20 depends:beef0000-->")
    r = vault.run("rm-depends", "abcd1234", "beef0000", cli="tasks")
    assert r.returncode == 0
    line = anchor_lines(vault, "notes/2026-05-27-09-15-22.md")[1]
    assert "depends:" not in line


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


# ---------- add ----------

def test_add_passes_every_flag_to_the_buffer(base):
    r = tasks(base, "add", "Projects/SGB", "(Charlie) via tasks add", "--due", "2026-10-02",
              "--scheduled", "2026-10-01", "--priority", "M", "--depends", "bbbb0001",
              "--depends", "aaaa0001")
    assert r.returncode == 0
    line = (r"- \[\[Projects/SGB\]\] ACTION: \(Charlie\) via tasks add "
            r"<!--\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d depends:aaaa0001 depends:bbbb0001 "
            r"due:2026-10-02 priority:M scheduled:2026-10-01-->")
    assert re.fullmatch(f"buffered: {line}\n", r.stdout)
    assert re.fullmatch(f"{line}\n", base.read("buffer.md"))


def test_add_passes_the_buffer_exit_code_through(base):
    r = tasks(base, "add", "Projects/Nope", "x")
    assert r.returncode == 1
    assert r.stderr == "tasks: error: thread 'Projects/Nope' does not resolve to threads/<Kind>/<Name>.md\n"


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
