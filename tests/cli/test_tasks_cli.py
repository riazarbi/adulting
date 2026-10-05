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
    base.write("threads/Projects/SGB/notes/2026-09-10-14-30-00.md", KICKOFF_HEAD +
          "ACTION: (Riaz Arbi) Draft the scope note <!--due:2026-09-20 priority:H depends:aaaa0001-->\n"
          "ACTION: " + "Long description " * 5 + "\n"
          "ACTION: bad attrs <!--due:soon priority:X depends:XYZ colour:red junk 2026-09-10T08:00:00-->\n"
          "ACTION: (Ghost) nobody\n"
          "ACTION:   \n"
          "TASK: [#L] (Charlie) Existing <!--aaaa0001 entry:2026-09-01 due:2026-09-05-->  \n")
    base.write("threads/Projects/SGB/notes/2026-09-11-09-00-00.md", "---\ntopic: no threads\n---\n\nACTION: orphan\n")
    base.write("threads/Projects/Gone/notes/2026-09-12-09-00-00.md",
          '---\ntopic: gone\nthreads:\n  - "[[Projects/Gone]]"\n---\n\nACTION: gone thread\n')
    return base


def failures(vault):
    kick = vault.note_path("2026-09-10-14-30-00", "Projects/SGB")
    # Files are walked thread folder by thread folder, so the note filed
    # under Projects/Gone comes before the two under Projects/SGB.
    return ("\n5 action(s) NOT ingested (left as ACTION: in source):\n"
            f"  {vault.note_path('2026-09-12-09-00-00', 'Projects/Gone')}:7: "
            "thread 'Projects/Gone' does not resolve\n"
            f"  {kick}:10: due must be YYYY-MM-DD; got 'soon'\n"
            f"  {kick}:10: priority must be H, M, or L; got 'X'\n"
            f"  {kick}:10: depends must be 8 hex chars; got 'XYZ'\n"
            f"  {kick}:10: unknown attr 'colour'\n"
            f"  {kick}:10: unknown attr token 'junk'\n"
            f"  {kick}:11: assignee 'Ghost' does not resolve to people/Ghost.md\n"
            f"  {kick}:12: missing description\n"
            f"  {vault.note_path('2026-09-11-09-00-00', 'Projects/SGB')}:5: note has no threads:\n"
            "\n")


# ---------- ingest ----------

def test_ingest_basic_action(vault):
    setup_vault(vault)
    vault.write_note("2026-05-27-09-15-22",
        "ACTION: Pick up dry cleaning",
        threads=["Projects/SGB"])
    r = vault.run(cli="tasks")
    assert r.returncode == 0, r.stderr
    note = vault.read("threads/Projects/SGB/notes/2026-05-27-09-15-22.md")
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
    lines = anchor_lines(vault, "threads/Projects/SGB/notes/2026-05-27-09-15-22.md")
    assert len(lines) == 2, lines
    for ln in lines:
        assert ln.endswith("-->  "), repr(ln)


def test_ingest_with_assignee_and_attrs(vault):
    """Every attribute an ACTION can carry reaches the anchor: assignee,
    priority, due, scheduled and depends. `scheduled:` used to be the one
    nothing asserted, so it could be dropped with a green suite."""
    setup_vault(vault)
    vault.write_note("2026-05-27-09-15-22",
        "ACTION: (Riaz Arbi) Send report "
        "<!--2026-05-27T09:15:22 due:2026-05-29 scheduled:2026-05-28 "
        "priority:H depends:aaaa0001-->",
        threads=["Projects/SGB"])
    r = vault.run(cli="tasks")
    assert r.returncode == 0, r.stderr
    note = vault.read("threads/Projects/SGB/notes/2026-05-27-09-15-22.md")
    assert re.search(
        r"^TASK: \[#H\] \(Riaz Arbi\) Send report "
        r"<!--[a-f0-9]{8} entry:\d{4}-\d{2}-\d{2} due:2026-05-29 "
        r"scheduled:2026-05-28 depends:aaaa0001-->  $",
        note, re.MULTILINE), note


def test_ingest_unresolved_assignee_fails(vault):
    setup_vault(vault)  # only Riaz Arbi exists
    vault.write_note("2026-05-27-09-15-22",
        "ACTION: (Ghost) Phantom",
        threads=["Projects/SGB"])
    before = vault.read("threads/Projects/SGB/notes/2026-05-27-09-15-22.md")
    r = vault.run(cli="tasks")
    path = vault.note_path("2026-05-27-09-15-22", "Projects/SGB")
    assert (r.returncode, r.stdout) == (1, "Ingested: 0.  Failed: 1.\n")
    assert r.stderr == ("\n1 action(s) NOT ingested (left as ACTION: in source):\n"
                        f"  {path}:9: assignee 'Ghost' does not resolve to people/Ghost.md\n\n")
    assert vault.read("threads/Projects/SGB/notes/2026-05-27-09-15-22.md") == before


def test_ingest_unresolved_thread_fails(vault):
    setup_vault(vault, threads=(("Projects", "SGB"),))
    path = vault.write_note("2026-05-27-09-15-22",
        "ACTION: Refers to a missing thread",
        threads=["Projects/Nope"])
    before = path.read_text(encoding="utf-8")
    r = vault.run(cli="tasks")
    assert (r.returncode, r.stdout) == (1, "Ingested: 0.  Failed: 1.\n")
    assert r.stderr == ("\n1 action(s) NOT ingested (left as ACTION: in source):\n"
                        f"  {path}:9: thread 'Projects/Nope' does not resolve\n\n")
    assert path.read_text(encoding="utf-8") == before


def test_ingest_is_also_a_named_subcommand(inbox):
    """`tasks` with no subcommand ingests, and `tasks ingest` is the same
    command said out loud, so --dry-run and --quiet belong to both. Either
    order of the flag and the subcommand means the same thing."""
    before = inbox.read("threads/Projects/SGB/notes/2026-09-10-14-30-00.md")
    bare = inbox.run("--dry-run", cli="tasks")
    named = inbox.run("ingest", "--dry-run", cli="tasks")
    before_flag = inbox.run("--dry-run", "ingest", cli="tasks")
    for r in (named, before_flag):
        assert r.returncode == bare.returncode
        assert r.stderr == bare.stderr
        assert r.stdout.splitlines()[-1] == "Ingested: 0.  Failed: 5."
    assert inbox.read("threads/Projects/SGB/notes/2026-09-10-14-30-00.md") == before
    quiet = inbox.run("ingest", "--dry-run", "--quiet", cli="tasks")
    assert quiet.stdout == ""


@pytest.mark.parametrize("flag", ["--dry-run", "--quiet"])
def test_the_ingest_flags_are_refused_on_another_subcommand(board, flag):
    """`tasks --dry-run done <uuid>` used to flip the anchor to DONE: on disk
    and say nothing. A flag that quietly does nothing is worse than one that
    errors, so it is refused."""
    before = board.read("threads/Topics/zeta/logs/2026-09-13.md")
    r = board.run(flag, "done", "bbbb0001", cli="tasks")
    assert (r.returncode, r.stdout) == (2, "")
    assert r.stderr.endswith(
        f"tasks: error: {flag} applies to ingest only, not to 'done'\n")
    assert board.read("threads/Topics/zeta/logs/2026-09-13.md") == before


def test_ingest_idempotent(vault):
    """Re-running ingest on a vault with no ACTION lines is a no-op."""
    setup_vault(vault)
    vault.write_note("2026-05-27-09-15-22",
        "ACTION: Once",
        threads=["Projects/SGB"])
    vault.run(cli="tasks")
    before = vault.read("threads/Projects/SGB/notes/2026-05-27-09-15-22.md")
    vault.run(cli="tasks")
    after = vault.read("threads/Projects/SGB/notes/2026-05-27-09-15-22.md")
    assert before == after


def test_ingest_generates_unique_uuids(vault):
    setup_vault(vault)
    vault.write_note("2026-05-27-09-15-22",
        "ACTION: First\nACTION: Second\nACTION: Third",
        threads=["Projects/SGB"])
    vault.run(cli="tasks")
    note = vault.read("threads/Projects/SGB/notes/2026-05-27-09-15-22.md")
    uuids = re.findall(r"<!--([a-f0-9]{8}) ", note)
    assert len(uuids) == 3
    assert len(set(uuids)) == 3


def test_dry_run_shows_the_anchors_and_writes_nothing(inbox):
    before = inbox.read("threads/Projects/SGB/notes/2026-09-10-14-30-00.md")
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
    assert inbox.read("threads/Projects/SGB/notes/2026-09-10-14-30-00.md") == before


def test_dry_run_quiet_prints_only_failures(inbox):
    r = inbox.run("--dry-run", "--quiet", cli="tasks")
    assert (r.returncode, r.stdout, r.stderr) == (1, "", failures(inbox))


def test_ingest_rewrites_good_actions_in_place_and_leaves_the_rest(inbox):
    r = inbox.run(cli="tasks")
    kick = str(inbox.note_path("2026-09-10-14-30-00", "Projects/SGB"))
    assert r.returncode == 1
    out = r.stdout.splitlines()
    assert re.fullmatch(rf"ingested: {UUID}  {re.escape(kick)}:8  Draft the scope note", out[0])
    assert re.fullmatch(rf"ingested: {UUID}  {re.escape(kick)}:9  "
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
        inbox.read("threads/Projects/SGB/notes/2026-09-10-14-30-00.md"))


def test_ingest_with_nothing_to_do(base):
    r = base.run(cli="tasks")
    assert (r.returncode, r.stdout, r.stderr) == (0, "Ingested: 0.  Failed: 0.\n", "")
    assert base.run("--quiet", cli="tasks").stdout == ""


# ---------- list, next, show ----------

@pytest.fixture
def board(base):
    base.write("threads/Projects/SGB/notes/2026-09-10-14-30-00.md", KICKOFF_HEAD +
          "TASK: [#H] (Riaz Arbi) Draft the scope note <!--dddd0001 entry:2026-09-10 due:2026-09-20 depends:aaaa0001-->  \n"
          "TASK: [#L] (Charlie) Existing <!--aaaa0001 entry:2026-09-01 due:2026-09-05-->  \n"
          "DONE: Finished <!--aaaa0002 entry:2026-08-01 end:2026-08-03-->\n")
    base.write("threads/Topics/zeta/logs/2026-09-13.md",
          '---\nthread: "[[Topics/zeta]]"\ndate: 2026-09-13\n---\n\n'
          "TASK: log task <!--bbbb0001 entry:2026-09-13 scheduled:2026-09-30-->\n"
          "TASK: [#M] second log task <!--aaaa0003 entry:2026-09-13-->\n")
    base.write("threads/Projects/SGB/notes/2026-09-14-09-00-00.md", "---\ntopic: x\n---\n\nTASK: unthreaded <!--cccc0001 entry:2026-09-14-->\n")
    return base


def test_list_table(board):
    assert board.run("list", cli="tasks").stdout == (
        "dddd0001  [#H]  Projects/SGB +1  (Riaz Arbi)  Draft the scope note  due:2026-09-20\n"
        "aaaa0001  [#L]  Projects/SGB +1  (Charlie)    Existing              due:2026-09-05\n"
        "aaaa0003  [#M]  Topics/zeta                   second log task\n"
        "bbbb0001        Topics/zeta                   log task\n"
        "cccc0001        -                             unthreaded\n")


@pytest.mark.parametrize("argv, expected", [
    (["--thread", "Projects/Alpha"],
     "dddd0001  [#H]  Projects/SGB +1  (Riaz Arbi)  Draft the scope note  due:2026-09-20\n"
     "aaaa0001  [#L]  Projects/SGB +1  (Charlie)    Existing              due:2026-09-05\n"),
    (["--priority", "M"], "aaaa0003  [#M]  Topics/zeta    second log task\n"),
    (["--assignee", "Charlie"],
     "aaaa0001  [#L]  Projects/SGB +1  (Charlie)  Existing  due:2026-09-05\n"),
    (["--overdue"],
     "dddd0001  [#H]  Projects/SGB +1  (Riaz Arbi)  Draft the scope note  due:2026-09-20\n"
     "aaaa0001  [#L]  Projects/SGB +1  (Charlie)    Existing              due:2026-09-05\n"),
    (["--thread", "Topics/zeta", "--priority", "H"], "(no tasks)\n"),
])
def test_list_filters(board, argv, expected):
    """`list` shows pending tasks only; DONE never appears in any of these."""
    r = board.run("list", *argv, cli="tasks")
    assert (r.returncode, r.stdout, r.stderr) == (0, expected, "")



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
        f"source:      {board.note_path('2026-09-10-14-30-00', 'Projects/SGB')}:9\n"
        "body:        Existing\n"
        "entry:       2026-09-01\n"
        "end:         -\n"
        "due:         2026-09-05\n"
        "scheduled:   -\n"
        "depends:     -\n")
    assert board.run("show", "dddd", cli="tasks").stdout.splitlines()[-1] == "depends:     aaaa0001"
    assert board.run("show", "cccc0001", cli="tasks").stdout.splitlines()[4] == "threads:     -"


def test_list_json_carries_the_fields_show_prints(board):
    """Every other listing command has --json; `tasks list` now does too,
    with the anchor's own fields rather than the padded table."""
    rows = json.loads(board.run("list", "--json", "--priority", "H", cli="tasks").stdout)
    assert rows == [
        {"uuid": "dddd0001", "priority": "H", "assignee": "Riaz Arbi",
         "threads": ["Projects/SGB", "Projects/Alpha"],
         "body": "Draft the scope note",
         "source": f"{board.note_path('2026-09-10-14-30-00', 'Projects/SGB')}:8",
         "entry": "2026-09-10",
         "due": "2026-09-20", "scheduled": None, "depends": ["aaaa0001"],
         "end": None},
    ]


def test_uuid_prefix_errors(board):
    """The ambiguous-prefix error names each file by its vault path, as every
    other line `tasks` prints does (this was deferred bug 7)."""
    note = board.note_path("2026-09-10-14-30-00", "Projects/SGB")
    log = board.log_path("Topics/zeta", "2026-09-13")
    r = board.run("show", "aaaa", cli="tasks")
    assert (r.returncode, r.stderr) == (1, "tasks: error: uuid prefix 'aaaa' is ambiguous: "
                                           f"aaaa0001 ({note}:9), "
                                           f"aaaa0002 ({note}:10), "
                                           f"aaaa0003 ({log}:7)\n")
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
    assert board.read("threads/Topics/zeta/logs/2026-09-13.md") == (
        '---\nthread: "[[Topics/zeta]]"\ndate: 2026-09-13\n---\n\n'
        f"DONE: [#L] (Charlie) renamed log task <!--bbbb0001 entry:2026-09-13 end:{date.today().isoformat()} "
        "due:2026-10-01 scheduled:2026-09-25-->  \n"
        "TASK: [#H] second log task <!--aaaa0003 entry:2026-09-13 depends:dddd0001-->  \n")
    assert board.lines("threads/Projects/SGB/notes/2026-09-10-14-30-00.md")[8] == (
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
    before = board.read("threads/Topics/zeta/logs/2026-09-13.md")
    r = board.run(*argv, cli="tasks")
    assert (r.returncode, r.stdout, r.stderr) == (1, "", message + "\n")
    assert board.read("threads/Topics/zeta/logs/2026-09-13.md") == before


def test_done_flips_kind_and_stamps_end(vault):
    setup_vault(vault)
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: Send report <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("done", "abcd1234", cli="tasks")
    assert r.returncode == 0, r.stderr
    assert r.stdout == "done: abcd1234  Send report\n"
    assert first_anchor(vault, "threads/Projects/SGB/notes/2026-05-27-09-15-22.md") == (
        f"DONE: Send report <!--abcd1234 entry:2026-05-20 end:{date.today().isoformat()}-->  ")


def test_rm_depends_unknown_target_fails(vault):
    """A prefix that is neither one of the task's dependencies nor any task
    is an error, and nothing is written."""
    setup_vault(vault)
    seed_note(vault, "2026-05-27-09-15-22",
        "TASK: t <!--abcd1234 entry:2026-05-20-->")
    before = vault.read("threads/Projects/SGB/notes/2026-05-27-09-15-22.md")
    r = vault.run("rm-depends", "abcd1234", "deadbeef", cli="tasks")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == "tasks: error: no task found with uuid prefix 'deadbeef'\n"
    assert vault.read("threads/Projects/SGB/notes/2026-05-27-09-15-22.md") == before


@pytest.mark.parametrize("argv", [
    ["set-priority", "bbbb0001", "Z"],
    ["list", "--priority", "Z"],
    ["add", "Projects/SGB", "x", "--priority", "Z"],
])
def test_a_priority_is_h_m_or_l_wherever_it_is_given(board, argv):
    """One rule and one message: argparse `choices` would have given a
    different message and a different exit code for the same mistake."""
    before = board.snapshot()
    r = board.run(*argv, cli="tasks")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == "tasks: error: priority must be H, M, or L; got 'Z'\n"
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
    note = vault.read("threads/Projects/SGB/notes/2026-05-27-09-15-22.md")
    m = re.search(r"<!--([a-f0-9]{8}) entry:", note)
    assert m, note
    u = m.group(1)

    r = vault.run("set-priority", u, "H", cli="tasks")
    assert r.returncode == 0
    r = vault.run("set-due", u, "2026-06-15", cli="tasks")
    assert r.returncode == 0
    r = vault.run("done", u, cli="tasks")
    assert r.returncode == 0

    note = vault.read("threads/Projects/SGB/notes/2026-05-27-09-15-22.md")
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
                        f"  {note}:9: thread 'Projects/sgb' "
                        "does not resolve\n\n")
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


def test_list_resolves_a_bare_thread_name_like_every_other_command(board):
    """It compared the raw string to the canonical `Kind/Name`, so a bare
    name printed a plausible empty answer instead of the tasks."""
    bare = board.run("list", "--thread", "SGB", cli="tasks")
    assert (bare.returncode, bare.stderr) == (0, "")
    assert bare.stdout == (
        "dddd0001  [#H]  Projects/SGB +1  (Riaz Arbi)  Draft the scope note  due:2026-09-20\n"
        "aaaa0001  [#L]  Projects/SGB +1  (Charlie)    Existing              due:2026-09-05\n")
    assert bare.stdout == board.run("list", "--thread", "Projects/SGB", cli="tasks").stdout


def test_list_refuses_a_thread_that_does_not_resolve(board):
    before = board.snapshot()
    r = board.run("list", "--thread", "Nope", cli="tasks")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == "tasks: error: thread 'Nope' does not resolve to a thread file\n"
    assert board.snapshot() == before


def test_an_action_with_attributes_but_no_text_is_reported_not_ingested(vault):
    """It used to become a task whose description was the HTML comment,
    with the due date dropped."""
    vault.write_thread("Projects", "SGB")
    note = vault.write_note("2026-09-10-14-30-00", "ACTION: <!--due:2026-01-01-->",
                            threads=["Projects/SGB"])
    before = note.read_text(encoding="utf-8")
    r = vault.run(cli="tasks")
    assert (r.returncode, r.stdout) == (1, "Ingested: 0.  Failed: 1.\n")
    assert r.stderr == ("\n1 action(s) NOT ingested (left as ACTION: in source):\n"
                        f"  {note}:9: missing description\n\n")
    assert note.read_text(encoding="utf-8") == before


def test_a_bare_action_line_is_reported_by_tasks_as_lint_reports_it(vault):
    """`tasks` used to skip it silently while `lint` called it a missing
    description; one parser, one answer."""
    vault.write_thread("Projects", "SGB")
    note = vault.write_note("2026-09-10-14-30-00", "ACTION:", threads=["Projects/SGB"])
    r = vault.run(cli="tasks")
    assert (r.returncode, r.stdout) == (1, "Ingested: 0.  Failed: 1.\n")
    assert r.stderr == ("\n1 action(s) NOT ingested (left as ACTION: in source):\n"
                        f"  {note}:9: missing description\n\n")
    lint = vault.run(cli="lint")
    assert f"{note}:9: ACTION: missing description" in lint.stdout
