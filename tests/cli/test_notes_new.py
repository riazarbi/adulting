"""`notes new`: the note it writes and the buffer REF it leaves behind, for
every combination of flags. Nothing is asked for; a missing value is an
error."""

import re

import pytest


STEM = r"\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}"




# Typed answers wait on stdin, so a prompt would find them and go ahead.
TYPED = "1\n1\n\nTyped topic\n"


@pytest.fixture
def new_note_vault(vault):
    for t in ("Projects/SGB", "Topics/Zeta", "Processes/Admin"):
        vault.write_thread(*t.split("/"))
    vault.write_person("Riaz Arbi")
    return vault


def created(vault, r):
    """The stem of the note a successful `notes new` reports on its last line."""
    path = r.stdout.splitlines()[-1]
    m = re.fullmatch(rf"{re.escape(str(vault.home / 'notes'))}/({STEM})\.md", path)
    assert m, r.stdout
    return m.group(1)


def test_meeting_with_every_field(new_note_vault):
    r = new_note_vault.run("new", "--type", "Meeting", "--topic", 'Q3 "review": plan',
              "--thread", "Projects/SGB", "--thread", "Zeta",
              "--person", "Riaz Arbi", "--person", ' Bern "B" Sellmeyer ',
              "--counterparty", "ACME Corp", "--location", "Boardroom", cli="notes", input=TYPED)
    assert (r.returncode, r.stderr) == (0, "")
    stem = created(new_note_vault, r)
    assert new_note_vault.read(f"notes/{stem}.md") == (
        "---\n"
        'topic: Q3 "review": plan\n'
        "type: Meeting\n"
        "threads:\n"
        '  - "[[Projects/SGB]]"\n'
        '  - "[[Topics/Zeta]]"\n'
        f"timestamp: {stem}\n"
        'aliases: ["Q3 \\"review\\": plan"]\n'
        "counterparty: ACME Corp\n"
        "location: Boardroom\n"
        "people:\n"
        '  - "[[people/Riaz Arbi]]"\n'
        '  - "Bern \\"B\\" Sellmeyer"\n'
        "---\n"
        "\n"
        "# Content\n"
        "\n")


def test_each_thread_gets_a_buffer_ref_in_order(new_note_vault):
    r = new_note_vault.run("new", "--type", "Meeting", "--topic", "Kickoff",
              "--thread", "Projects/SGB", "--thread", "[[Topics/Zeta]]", cli="notes", input=TYPED)
    stem = created(new_note_vault, r)
    ts = r"<!--\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}-->"
    lines = r.stdout.splitlines()
    assert len(lines) == 3
    assert re.fullmatch(rf"buffered: - \[\[Projects/SGB\]\] REF: \[\[notes/{stem}\]\] Kickoff {ts}", lines[0])
    assert re.fullmatch(rf"buffered: - \[\[Topics/Zeta\]\] REF: \[\[notes/{stem}\]\] Kickoff {ts}", lines[1])
    assert new_note_vault.read("buffer.md").count(f"[[notes/{stem}]]") == 2


def test_a_meeting_always_has_a_location_line(new_note_vault):
    stem = created(new_note_vault, new_note_vault.run("new", "--type", "Meeting", "--topic", "No place",
                            "--thread", "Processes/Admin", cli="notes", input=TYPED))
    text = new_note_vault.read(f"notes/{stem}.md")
    assert "\nlocation: \n---\n" in text
    assert "counterparty" not in text and "people" not in text


@pytest.mark.parametrize("type_", ["Correspondence", "Workshop", "Report", "Log", "Research", "Recipe"])
def test_other_types_have_only_the_common_fields(new_note_vault, type_):
    stem = created(new_note_vault, new_note_vault.run("new", "--type", type_, "--topic", "Daily log", "--thread", "Topics/Zeta", cli="notes", input=TYPED))
    assert new_note_vault.read(f"notes/{stem}.md") == (
        f'---\ntopic: Daily log\ntype: {type_}\nthreads:\n  - "[[Topics/Zeta]]"\n'
        f'timestamp: {stem}\naliases: ["Daily log"]\n---\n\n# Content\n\n')


def test_correspondence_takes_people(new_note_vault):
    stem = created(new_note_vault, new_note_vault.run("new", "--type", "Correspondence", "--topic", "Email",
                            "--thread", "Topics/Zeta", "--person", "Riaz Arbi", cli="notes", input=TYPED))
    assert new_note_vault.read(f"notes/{stem}.md").endswith(
        'people:\n  - "[[people/Riaz Arbi]]"\n---\n\n# Content\n\n')


def test_a_repeated_thread_is_written_once(new_note_vault):
    r = new_note_vault.run("new", "--type", "Log", "--topic", "x", "--thread", "Topics/Zeta", "--thread", "Zeta", cli="notes", input=TYPED)
    stem = created(new_note_vault, r)
    assert new_note_vault.read(f"notes/{stem}.md").count("[[Topics/Zeta]]") == 1
    assert r.stdout.count("buffered:") == 1


def test_the_new_note_passes_lint(new_note_vault):
    stem = created(new_note_vault, new_note_vault.run("new", "--type", "Meeting", "--topic", "Linted",
                            "--thread", "Projects/SGB", "--person", "Riaz Arbi",
                            "--person", "Someone Untracked", "--location", "Online", cli="notes", input=TYPED))
    r = new_note_vault.run(str(new_note_vault.home / "notes" / f"{stem}.md"), cli="lint")
    assert r.returncode == 0, r.stdout


@pytest.mark.parametrize("argv, message", [
    (["--type", "Log", "--topic", "  ", "--thread", "Topics/Zeta"], "notes: error: --topic is empty\n"),
    (["--type", "Log", "--topic", "x", "--thread", "Nope"],
     "notes: error: thread 'Nope' does not resolve to a thread file\n"),
    (["--type", "Log", "--topic", "x", "--thread", "Topics/Zeta", "--person", "Riaz Arbi"],
     "notes: error: --person is only for Meeting and Correspondence notes\n"),
    (["--type", "Report", "--topic", "x", "--thread", "Topics/Zeta", "--counterparty", "ACME"],
     "notes: error: --counterparty and --location are only for Meeting notes\n"),
    (["--type", "Correspondence", "--topic", "x", "--thread", "Topics/Zeta", "--location", "Online"],
     "notes: error: --counterparty and --location are only for Meeting notes\n"),
])
def test_errors_write_nothing(new_note_vault, argv, message):
    r = new_note_vault.run("new", *argv, cli="notes", input=TYPED)
    assert (r.returncode, r.stdout, r.stderr) == (1, "", message)
    assert list((new_note_vault.home / "notes").iterdir()) == []
    assert not (new_note_vault.home / "buffer.md").exists()


@pytest.mark.parametrize("missing", ["--type", "--topic", "--thread"])
def test_required_flags_never_fall_back_to_prompts(new_note_vault, missing):
    given = {"--type": "Log", "--topic": "x", "--thread": "Topics/Zeta"}
    argv = [x for k, val in given.items() if k != missing for x in (k, val)]
    r = new_note_vault.run("new", *argv, cli="notes", input=TYPED)
    assert r.returncode == 2
    assert missing in r.stderr
    assert list((new_note_vault.home / "notes").iterdir()) == []


def test_new_does_not_run_the_ingest_pre_pass(new_note_vault):
    new_note_vault.write_note("2026-09-10-14-30-00", "ACTION: leave me", threads=["Topics/Zeta"])
    new_note_vault.run("new", "--type", "Log", "--topic", "x", "--thread", "Topics/Zeta", cli="notes", input=TYPED)
    assert "ACTION: leave me" in new_note_vault.read("notes/2026-09-10-14-30-00.md")


def test_a_buffer_it_cannot_write_does_not_stop_the_note(new_note_vault):
    """The REF is best-effort: the note is written, nothing is said on
    stderr, and there is simply no `buffered:` line."""
    buffer = new_note_vault.write("buffer.md", "")
    buffer.chmod(0o444)
    try:
        r = new_note_vault.run("new", "--type", "Log", "--topic", "Quiet", "--thread", "Projects/SGB", cli="notes", input=TYPED)
    finally:
        buffer.chmod(0o644)
    assert (r.returncode, r.stderr) == (0, "")
    stem = created(new_note_vault, r)
    assert r.stdout == f"{new_note_vault.home / 'notes' / stem}.md\n"
    assert buffer.read_text() == ""
