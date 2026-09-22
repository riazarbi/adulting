"""Tests for `notes new`, driven entirely by flags (refactor unit 11).

The old bash `notes new` asked for everything through prompts. The note it
wrote, and the buffer REFs, were captured by feeding those prompts on stdin;
these tests pin the same output for the same answers given as flags.

`notes` is this package's command.
"""

import json
import re
import subprocess

import pytest

from harness import command_path

STEM = r"\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}"


def notes(vault, *argv):
    return subprocess.run([command_path("notes", vault.env), *argv], capture_output=True,
                          text=True, env=vault.env, input="1\n1\n\nTyped topic\n")


@pytest.fixture
def v(vault):
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


def test_meeting_with_every_field(v):
    r = notes(v, "new", "--type", "Meeting", "--topic", 'Q3 "review": plan',
              "--thread", "Projects/SGB", "--thread", "Zeta",
              "--person", "Riaz Arbi", "--person", ' Bern "B" Sellmeyer ',
              "--counterparty", "ACME Corp", "--location", "Boardroom")
    assert (r.returncode, r.stderr) == (0, "")
    stem = created(v, r)
    assert v.read(f"notes/{stem}.md") == (
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


def test_each_thread_gets_a_buffer_ref_in_order(v):
    r = notes(v, "new", "--type", "Meeting", "--topic", "Kickoff",
              "--thread", "Projects/SGB", "--thread", "[[Topics/Zeta]]")
    stem = created(v, r)
    ts = r"<!--\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}-->"
    lines = r.stdout.splitlines()
    assert len(lines) == 3
    assert re.fullmatch(rf"buffered: - \[\[Projects/SGB\]\] REF: \[\[notes/{stem}\]\] Kickoff {ts}", lines[0])
    assert re.fullmatch(rf"buffered: - \[\[Topics/Zeta\]\] REF: \[\[notes/{stem}\]\] Kickoff {ts}", lines[1])
    assert v.read("buffer.md").count(f"[[notes/{stem}]]") == 2


def test_a_meeting_always_has_a_location_line(v):
    stem = created(v, notes(v, "new", "--type", "Meeting", "--topic", "No place",
                            "--thread", "Processes/Admin"))
    text = v.read(f"notes/{stem}.md")
    assert "\nlocation: \n---\n" in text
    assert "counterparty" not in text and "people" not in text


@pytest.mark.parametrize("type_", ["Correspondence", "Workshop", "Report", "Log", "Research", "Recipe"])
def test_other_types_have_only_the_common_fields(v, type_):
    stem = created(v, notes(v, "new", "--type", type_, "--topic", "Daily log", "--thread", "Topics/Zeta"))
    assert v.read(f"notes/{stem}.md") == (
        f'---\ntopic: Daily log\ntype: {type_}\nthreads:\n  - "[[Topics/Zeta]]"\n'
        f'timestamp: {stem}\naliases: ["Daily log"]\n---\n\n# Content\n\n')


def test_correspondence_takes_people(v):
    stem = created(v, notes(v, "new", "--type", "Correspondence", "--topic", "Email",
                            "--thread", "Topics/Zeta", "--person", "Riaz Arbi"))
    assert v.read(f"notes/{stem}.md").endswith(
        'people:\n  - "[[people/Riaz Arbi]]"\n---\n\n# Content\n\n')


def test_a_repeated_thread_is_written_once(v):
    r = notes(v, "new", "--type", "Log", "--topic", "x", "--thread", "Topics/Zeta", "--thread", "Zeta")
    stem = created(v, r)
    assert v.read(f"notes/{stem}.md").count("[[Topics/Zeta]]") == 1
    assert r.stdout.count("buffered:") == 1


def test_the_new_note_passes_lint(v):
    stem = created(v, notes(v, "new", "--type", "Meeting", "--topic", "Linted",
                            "--thread", "Projects/SGB", "--person", "Riaz Arbi",
                            "--person", "Someone Untracked", "--location", "Online"))
    r = v.run(str(v.home / "notes" / f"{stem}.md"), cli="lint")
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
def test_errors_write_nothing(v, argv, message):
    r = notes(v, "new", *argv)
    assert (r.returncode, r.stdout, r.stderr) == (1, "", message)
    assert list((v.home / "notes").iterdir()) == []
    assert not (v.home / "buffer.md").exists()


@pytest.mark.parametrize("missing", ["--type", "--topic", "--thread"])
def test_required_flags_never_fall_back_to_prompts(v, missing):
    given = {"--type": "Log", "--topic": "x", "--thread": "Topics/Zeta"}
    argv = [x for k, val in given.items() if k != missing for x in (k, val)]
    r = notes(v, "new", *argv)
    assert r.returncode == 2
    assert missing in r.stderr
    assert list((v.home / "notes").iterdir()) == []


def test_unknown_type_is_rejected(v):
    r = notes(v, "new", "--type", "Diary", "--topic", "x", "--thread", "Topics/Zeta")
    assert r.returncode == 2 and "invalid choice: 'Diary'" in r.stderr


def test_new_does_not_run_the_ingest_pre_pass(v):
    v.write_note("2026-09-10-14-30-00", "ACTION: leave me", threads=["Topics/Zeta"])
    notes(v, "new", "--type", "Log", "--topic", "x", "--thread", "Topics/Zeta")
    assert "ACTION: leave me" in v.read("notes/2026-09-10-14-30-00.md")


def test_help_json_lists_new(vault):
    manifest = json.loads(notes(vault, "--help-json").stdout)
    assert [s["name"] for s in manifest["subcommands"]][0] == "new"
