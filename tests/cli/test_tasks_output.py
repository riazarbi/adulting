"""Characterisation of `tasks` output and in-place rewrites (refactor unit 9).

test_tasks_cli.py covers the behaviour from the original story. These pin the
exact text a person reads and the exact lines written back into notes and
logs. `tasks` has no interactivity to remove, so every test here was run
green against the pre-port script.
"""

import json
import re

import pytest

THREAD = "---\nstatus: open\n---\n"
UUID = r"[0-9a-f]{8}"


def tasks(vault, *argv):
    return vault.run(*argv, cli="tasks", input="")


def write(vault, rel, text):
    p = vault.home / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


@pytest.fixture
def base(vault):
    for t in ("Projects/SGB", "Projects/Alpha", "Topics/zeta"):
        write(vault, f"threads/{t}.md", THREAD)
    write(vault, "people/Riaz Arbi.md", THREAD)
    write(vault, "people/Charlie.md", THREAD)
    return vault


KICKOFF_HEAD = ('---\ntopic: Kickoff\nthreads:\n  - "[[Projects/SGB]]"\n'
                '  - "[[Projects/Alpha]]"\n---\n\n')


@pytest.fixture
def inbox(base):
    """Notes with two good ACTIONs and five that fail for different reasons."""
    write(base, "notes/2026-09-10-14-30-00.md", KICKOFF_HEAD +
          "ACTION: (Riaz Arbi) Draft the scope note <!--due:2026-09-20 priority:H depends:aaaa0001-->\n"
          "ACTION: " + "Long description " * 5 + "\n"
          "ACTION: bad attrs <!--due:soon priority:X depends:XYZ colour:red junk 2026-09-10T08:00:00-->\n"
          "ACTION: (Ghost) nobody\n"
          "ACTION:   \n"
          "TASK: [#L] (Charlie) Existing <!--aaaa0001 entry:2026-09-01 due:2026-09-05-->  \n")
    write(base, "notes/2026-09-11-09-00-00.md", "---\ntopic: no threads\n---\n\nACTION: orphan\n")
    write(base, "notes/2026-09-12-09-00-00.md",
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

def test_dry_run_shows_the_anchors_and_writes_nothing(inbox):
    before = inbox.read("notes/2026-09-10-14-30-00.md")
    r = tasks(inbox, "--dry-run")
    assert r.returncode == 1
    date = r"\d{4}-\d{2}-\d{2}"
    lines = r.stdout.splitlines()
    assert len(lines) == 3
    assert re.fullmatch(rf"would: TASK: \[#H\] \(Riaz Arbi\) Draft the scope note "
                        rf"<!--{UUID} entry:{date} due:2026-09-20 depends:aaaa0001-->  ", lines[0])
    assert re.fullmatch(rf"would: TASK: (Long description ){{4}}Long description "
                        rf"<!--{UUID} entry:{date}-->  ", lines[1])
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
    write(base, "notes/2026-09-10-14-30-00.md", KICKOFF_HEAD +
          "TASK: [#H] (Riaz Arbi) Draft the scope note <!--dddd0001 entry:2026-09-10 due:2026-09-20 depends:aaaa0001-->  \n"
          "TASK: [#L] (Charlie) Existing <!--aaaa0001 entry:2026-09-01 due:2026-09-05-->  \n"
          "DONE: Finished <!--aaaa0002 entry:2026-08-01 end:2026-08-03-->\n")
    write(base, "logs/Topics/zeta/2026-09-13.md",
          '---\nthread: "[[Topics/zeta]]"\ndate: 2026-09-13\n---\n\n'
          "TASK: log task <!--bbbb0001 entry:2026-09-13 scheduled:2026-09-30-->\n"
          "TASK: [#M] second log task <!--aaaa0003 entry:2026-09-13-->\n")
    write(base, "notes/2026-09-14-09-00-00.md", "---\ntopic: x\n---\n\nTASK: unthreaded <!--cccc0001 entry:2026-09-14-->\n")
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


def test_next_orders_by_priority_due_entry(board):
    assert tasks(board, "next").stdout == (
        "dddd0001  [#H]  Projects/SGB +1  (Riaz Arbi)  Draft the scope note  due:2026-09-20\n"
        "aaaa0003  [#M]  Topics/zeta                   second log task\n"
        "aaaa0001  [#L]  Projects/SGB +1  (Charlie)    Existing              due:2026-09-05\n"
        "bbbb0001        Topics/zeta                   log task\n"
        "cccc0001        -                             unthreaded\n")


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


# ---------- add ----------

def test_add_passes_every_flag_to_the_buffer(base):
    r = tasks(base, "add", "Projects/SGB", "(Charlie) via tasks add", "--due", "2026-10-02",
              "--scheduled", "2026-10-01", "--priority", "M", "--depends", "bbbb0001",
              "--depends", "aaaa0001")
    assert r.returncode == 0
    assert re.fullmatch(r"buffered: - \[\[Projects/SGB\]\] ACTION: \(Charlie\) via tasks add "
                        r"<!--\S+ depends:aaaa0001 depends:bbbb0001 due:2026-10-02 priority:M "
                        r"scheduled:2026-10-01-->\n", r.stdout)


def test_add_passes_the_buffer_exit_code_through(base):
    r = tasks(base, "add", "Projects/Nope", "x")
    assert r.returncode == 1
    assert r.stderr == "tasks: error: thread 'Projects/Nope' does not resolve to threads/<Kind>/<Name>.md\n"


def test_help_json(vault):
    manifest = json.loads(tasks(vault, "--help-json").stdout)
    assert [f["name"] for f in manifest["flags"]] == ["--dry-run", "--quiet"]
    assert [s["name"] for s in manifest["subcommands"]] == [
        "add", "done", "set-description", "set-assignee", "set-due", "set-scheduled",
        "set-priority", "add-depends", "rm-depends", "list", "next", "show"]
