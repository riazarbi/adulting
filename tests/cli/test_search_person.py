"""`search --person` and `search person`: people as a filter dimension.

One vault where each way of referring to someone appears once, so each test
can say which way a record matched. Story: stories/2026-11-23-search-person.md.
"""

import json

import pytest

MEETING = "threads/Processes/SQR/notes/2026-08-27-09-00-00.md"
LETTER = "threads/Projects/Alpha/notes/2026-08-20-09-00-00.md"
REPORT = "threads/Processes/SQR/notes/2026-08-10-09-00-00.md"
LOG = "threads/Processes/SQR/logs/2026-08-28.md"


def path(vault, rel):
    return str(vault.home / rel)


def note(topic, type_, thread, stamp, body, people=()):
    fm = (f"---\ntopic: {topic}\ntype: {type_}\nthreads:\n  - \"[[{thread}]]\"\n"
          f"timestamp: {stamp}\n")
    if people:
        fm += "people:\n" + "".join(f"  - {p}\n" for p in people)
    return fm + "---\n\n" + body + "\n"


@pytest.fixture
def people_vault(vault):
    vault.write_thread("Processes", "SQR")
    vault.write_thread("Projects", "Alpha", currency="ZAR", rate=1000)
    for name in ("Remy Dorn", "Bram Halvorsen"):
        vault.write(f"people/{name}.md",
                    "---\nstatus: open\ncategory: personal\nstarted: 2026-01-02\n---\n")

    # Remy: linked in frontmatter, named in the text and assigned a task;
    # the link is strongest. Bram: a plain attendee and nothing more.
    vault.write(MEETING, note(
        "Kickoff", "Meeting", "Processes/SQR", "2026-08-27-09-00-00",
        "Went through the plan with remy dorn.\n"
        "TASK: (Remy Dorn) Send the pack <!--aaaa1111 entry:2026-08-27-->",
        people=['"[[people/Remy Dorn]]"', "Bram Halvorsen"]))
    # Remy only in the text; Bram only behind an aliased link.
    vault.write(LETTER, note(
        "Fees", "Correspondence", "Projects/Alpha", "2026-08-20-09-00-00",
        "Email from Remy Dorn about fees, copied to [[people/Bram Halvorsen|Bram]]."))
    # Near misses: a longer name, a first name alone, the full name inside
    # a link to something else, and a name nobody declared.
    vault.write(REPORT, note(
        "Survey", "Report", "Processes/SQR", "2026-08-10-09-00-00",
        "Remy Dornfield came round. Bram was out.\n"
        "REF: [[Topics/Remy Dorn Archive]]\n"
        "Una Declared phoned."))
    # Remy named in a TEXT line and assigned a finished task; Bram linked.
    vault.write(LOG,
                '---\nthread: "[[Processes/SQR]]"\ndate: 2026-08-28\ntype: Log\n---\n\n'
                "TEXT: Called Remy Dorn.\n"
                "REF: [[people/Bram Halvorsen]] introduced\n"
                "DONE: (Remy Dorn) File it <!--bbbb2222 entry:2026-08-20 end:2026-08-28-->\n"
                "TEXT: Unrelated.\n")
    vault.write("buffer.md",
                "- [[Processes/SQR]] ACTION: (Remy Dorn) Ring back <!--2026-08-30T10:05:00-->\n")
    vault.write_hours_file("Projects", "Alpha", entries=[{
        "name": "Spec work", "id": "cccc3333", "rate": 1000, "currency": "ZAR",
        "startTime": "2026-08-26T09:00:00.000Z", "endTime": "2026-08-26T11:00:00.000Z"}])
    return vault


def found(vault, *argv):
    r = vault.run(*argv, "--json", cli="search")
    assert (r.returncode, r.stderr) == (0, ""), r.stderr
    return json.loads(r.stdout)


# ---------- the matching rule ----------

def test_each_way_of_referring_to_someone(people_vault):
    v = people_vault
    remy = found(v, "notes", "--person", "Remy Dorn")
    assert [(x["path"], x["via"]) for x in remy] == [
        (path(v, MEETING), "link"), (path(v, LETTER), "text")]
    bram = found(v, "notes", "--person", "Bram Halvorsen")
    assert [(x["path"], x["via"]) for x in bram] == [
        (path(v, MEETING), "attendee"), (path(v, LETTER), "link")]
    logs = found(v, "logs", "--person", "Remy Dorn")
    assert [(x["path"], x["via"]) for x in logs] == [(path(v, LOG), "assignee")]


def test_near_misses_do_not_match(people_vault):
    """A longer name, a first name, the name inside another link: none is Remy."""
    for name in ("Remy Dorn", "Bram Halvorsen"):
        paths = [x["path"] for x in found(people_vault, "notes", "--person", name)]
        assert path(people_vault, REPORT) not in paths, name


def test_aliased_link_is_a_link_not_text(people_vault):
    letter = [x for x in found(people_vault, "notes", "--person", "Bram Halvorsen")
              if x["path"] == path(people_vault, LETTER)]
    assert letter[0]["via"] == "link"


def test_snippet_is_the_line_that_names_the_person(people_vault):
    r = people_vault.run("logs", "--person", "Remy Dorn", cli="search")
    assert r.stdout == (
        f"{path(people_vault, LOG)}  2026-08-28  assignee  Processes/SQR  4 entries\n"
        "    DONE: (Remy Dorn) File it <!--bbbb2222 entry:2026-08-20 end:2026-08-28-->\n")
    r = people_vault.run("notes", "--person", "Bram Halvorsen", cli="search")
    assert r.stdout.splitlines()[1] == "    people: Bram Halvorsen"


def test_text_snippet_wins_over_the_person_line(people_vault):
    rows = found(people_vault, "notes", "--person", "Remy Dorn", "--text", "plan")
    assert [(x["via"], x["snippet"]) for x in rows] == [
        ("link", "Went through the plan with remy dorn. TASK: (Remy Dorn) Send the pack "
                 "<!--aaaa1111 entry:2…")]


def test_person_and_thread_intersect(people_vault):
    rows = found(people_vault, "notes", "--thread", "SQR", "--person", "Remy Dorn")
    assert [x["path"] for x in rows] == [path(people_vault, MEETING)]


# ---------- resolving the name ----------

@pytest.mark.parametrize("given", ["Remy Dorn", "remy dorn", "people/Remy Dorn",
                                   "[[people/Remy Dorn]]", "Remy", "RD"])
def test_name_resolves_to_the_declared_person(people_vault, given):
    assert found(people_vault, "person", given)["person"] == "Remy Dorn"


def test_ambiguous_name_lists_the_candidates(people_vault):
    r = people_vault.run("notes", "--person", "r", cli="search")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == ("search: error: ambiguous person 'r'; "
                        "matches: Bram Halvorsen, Remy Dorn\n")


@pytest.mark.parametrize("argv", [
    ["notes", "--person"], ["logs", "--person"], ["activity", "--person"],
    ["stream", "--person"], ["person"]])
def test_undeclared_person_is_not_found(people_vault, argv):
    """`Una Declared` is in a note's text, but has no file: not a person."""
    r = people_vault.run(*argv, "Una Declared", cli="search")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == ("search: error: person not found: 'Una Declared' has no file "
                        "in people/ (use --text for a name without one)\n")


def test_a_misspelling_is_not_guessed(people_vault):
    """`Remy Doorn` looks like Remy, but a guess could name the wrong person."""
    r = people_vault.run("person", "Remy Doorn", cli="search")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr.startswith("search: error: person not found: 'Remy Doorn'")


# ---------- stream and activity ----------

def test_stream_matches_line_by_line(people_vault):
    rows = found(people_vault, "stream", "--person", "Remy Dorn",
                 "--since", "2026-08-01", "--limit", "0")
    assert sorted((e["date"], e["kind"], e["via"]) for e in rows) == [
        ("2026-08-20", "note", "text"),
        ("2026-08-20", "task", "assignee"),
        ("2026-08-27", "note", "link"),
        ("2026-08-27", "task", "assignee"),
        ("2026-08-28", "done", "assignee"),
        ("2026-08-28", "log", "text"),
        ("2026-08-30", "pending", "assignee")]
    assert all("_ref" not in e for e in rows)


def test_stream_without_person_is_unchanged(people_vault):
    rows = found(people_vault, "stream", "--since", "2026-08-01", "--limit", "0")
    assert all(set(e) == {"kind", "date", "time", "thread", "summary", "path"} for e in rows)


def test_stream_shows_how_each_event_matched(people_vault):
    r = people_vault.run("stream", "--person", "Bram Halvorsen", "--since", "2026-08-01",
                         cli="search")
    assert r.stdout == (
        "\n2026-08-28\n"
        "  log   Processes/SQR   link      [[people/Bram Halvorsen]] introduced\n"
        "\n2026-08-27\n"
        "  note  Processes/SQR   attendee  Kickoff\n"
        "\n2026-08-20\n"
        "  note  Projects/Alpha  link      Fees\n"
        "\n3 event(s); window 2026-08-01 to today\n")


def test_activity_counts_only_what_names_the_person(people_vault):
    rows = found(people_vault, "activity", "--person", "Remy Dorn",
                 "--since", "2026-08-01")
    assert [(r["thread"], r["notes"], r["logs"], r["entries"], r["minutes"])
            for r in rows] == [
        ("Processes/SQR", 1, 1, 2, 0),
        ("Projects/Alpha", 1, 0, 0, 0)]


# ---------- search person ----------

def test_person_summary(people_vault):
    d = found(people_vault, "person", "Remy Dorn", "--limit", "0")
    assert {k: v for k, v in d.items() if k != "recent"} == {
        "person": "Remy Dorn", "first": "2026-08-20", "last": "2026-08-28",
        "notes": 2, "notes_by_type": {"Correspondence": 1, "Meeting": 1},
        "logs": 1, "log_lines": 1,
        "tasks_open": 1, "tasks_done": 1, "tasks_dropped": 0,
        "threads": [{"thread": "Processes/SQR", "count": 2, "last": "2026-08-28"},
                    {"thread": "Projects/Alpha", "count": 1, "last": "2026-08-20"}]}
    assert [(r["path"], r["via"]) for r in d["recent"]] == [
        (path(people_vault, LOG), "assignee"),
        (path(people_vault, MEETING), "link"),
        (path(people_vault, LETTER), "text")]


def test_person_summary_text(people_vault):
    r = people_vault.run("person", "Remy Dorn", "--limit", "1", cli="search")
    assert r.stdout == (
        "Remy Dorn\n\n"
        "  first seen 2026-08-20\n"
        "  last seen  2026-08-28\n"
        "  notes         2   (Correspondence 1, Meeting 1)\n"
        "  logs          1   1 lines\n"
        "  tasks         1 open, 1 done, 0 dropped   (assigned)\n"
        "\n  threads:\n"
        "    Processes/SQR      2  2026-08-28\n"
        "    Projects/Alpha     1  2026-08-20\n"
        "\n  recent:\n"
        f"    {path(people_vault, LOG)}  2026-08-28  Log  assignee  "
        "DONE: (Remy Dorn) File it <!--bbbb2222 entry:2026-08-20 end:2026-08-28-->\n")


def test_person_counts_agree_with_the_filters(people_vault):
    v = people_vault
    d = found(v, "person", "Bram Halvorsen")
    assert d["notes"] == len(found(v, "notes", "--person", "Bram Halvorsen", "--limit", "0"))
    assert d["logs"] == len(found(v, "logs", "--person", "Bram Halvorsen", "--limit", "0"))
    d = found(v, "person", "Remy Dorn")
    stream = found(v, "stream", "--person", "Remy Dorn", "--since", "2000-01-01",
                   "--limit", "0", "--kind", "log,task,done,dropped")
    assigned = [e for e in stream if e["via"] == "assignee"]
    assert d["log_lines"] == sum(1 for e in stream if e["kind"] == "log")
    assert d["tasks_open"] + d["tasks_done"] + d["tasks_dropped"] == sum(
        1 for e in assigned if e["kind"] == "task")
    assert d["tasks_done"] == sum(1 for e in assigned if e["kind"] == "done")
