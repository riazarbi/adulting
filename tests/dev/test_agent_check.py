"""Tests for dev/agent-check, the gate over the agent skills.

The skills ship in the image, so what is committed is what the model is told.
They described commands that prompt on stdin for months after that stopped
being true — this is the check that would have caught it, so it is checked in
turn, against skills written here rather than the committed ones.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def load(path):
    """Import a dev script that has no .py suffix, as a module."""
    spec = importlib.util.spec_from_loader(
        "agent_check", importlib.machinery.SourceFileLoader("agent_check", str(path)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHECK = load(REPO / "dev" / "agent-check")

# What the real CLI has, as `problems()` wants it — written out rather than
# harvested, so these tests say the same thing whatever the CLI gains next.
SURFACES = {
    "subcommands": {c: set() for c in CHECK.COMMANDS}
    | {"tasks": {"list", "add", "done", "ingest"},
       "hours": {"log", "list", "report"},
       "payments": {"log", "list", "statement"},
       "threads": {"new", "delete", "list", "show"},
       "notes": {"list", "cat", "new"}},
    "flags": {("--thread",), ("--due",), ("--minutes", "-m")},
}

FRONT = "---\nname: a-skill\ndescription: When to load it.\n---\n\n"


def problems(body, front=FRONT, folder="a-skill"):
    return CHECK.problems(Path(folder) / "SKILL.md", front + body, SURFACES)


# ---------- the surface that leaks into the prose ----------

def test_a_subcommand_that_does_not_exist_is_reported():
    assert problems("Run `tasks suggest` to guess one.") == [
        "names `tasks suggest`, which is not a subcommand of tasks"]


def test_a_flag_no_command_has_is_reported():
    assert problems("Pass `--urgent` when he says so.") == [
        "names the flag `--urgent`, which no command has"]


def test_a_real_subcommand_and_a_real_flag_pass():
    assert problems("`hours log <thread> --thread x`, then `hours report`.") == []


def test_prose_about_a_command_is_not_read_as_a_subcommand():
    """"notes and logs" is English about notes; `notes list` is a claim."""
    assert problems("Search notes and logs, then read the file.") == []
    assert problems("Use `notes list` first.") == []


def test_a_placeholder_is_not_read_as_a_subcommand():
    assert problems("Call `tasks <uuid>` with the uuid you were given.") == []


# ---------- the claim that something prompts ----------

@pytest.mark.parametrize("stale", [
    "`payments log` without one goes interactive and you cannot answer it.",
    "`hours log` with no thread drops into an interactive capture.",
    "`threads new` prompts for any field you leave out.",
    "-y skips the confirmation prompt.",
    "Every subcommand needs a terminal or opens an application.",
])
def test_a_claim_that_a_command_prompts_is_reported(stale):
    [problem] = problems(stale)
    assert problem.startswith("says a command is interactive, and none of them are:")


@pytest.mark.parametrize("fine", [
    # The agent's own system prompt, and the messages it is sent, are not
    # the CLI prompting anybody. These were all reported until the check
    # learned the difference.
    "Format per the role prompt's mobile rules.",
    "When an automated prompt calls for an end-of-day commit, skip the confirm.",
    "## Automated (non-interactive) runs",
    "The message contains `THIS IS AN AUTOMATED PROMPT` — act without asking.",
    "Nothing prompts; a command given too little exits with an error.",
    "Without -y it refuses, rather than prompting.",
])
def test_prose_about_the_agents_prompt_is_not_a_claim_about_a_command(fine):
    assert problems(fine) == []


# ---------- the shape the agent requires ----------

def test_the_folder_name_must_equal_the_frontmatter_name():
    """The agent rejects the skill outright when they disagree, so a typo
    here is a skill that silently never loads."""
    [problem] = problems("Body.", folder="billing")
    assert problem == ("frontmatter name 'a-skill' is not the folder name "
                       "'billing'; the agent rejects the skill")


def test_a_key_the_agent_does_not_accept_is_reported():
    front = "---\nname: a-skill\ndescription: d\nauthor: riaz\n---\n\n"
    assert problems("Body.", front=front) == [
        "frontmatter key 'author' is not one the agent accepts"]


def test_a_skill_with_no_description_is_reported():
    front = "---\nname: a-skill\n---\n\n"
    [problem] = problems("Body.", front=front)
    assert problem.startswith("frontmatter has no description")


def test_no_frontmatter_at_all_is_reported():
    assert CHECK.problems(Path("a-skill") / "SKILL.md", "# Just a body\n", SURFACES) == [
        "has no frontmatter"]


# ---------- the committed skills ----------

def test_every_committed_skill_has_the_shape_the_agent_wants():
    """Checked without the CLI, so this says the same thing on a machine
    where the commands are not installed."""
    skills = sorted(d for d in (REPO / "agent" / "skills").iterdir() if d.is_dir())
    assert skills, "no skills committed"
    for directory in skills:
        text = (directory / "SKILL.md").read_text(encoding="utf-8")
        front = CHECK.frontmatter(text)
        assert front is not None, directory.name
        assert front["name"] == directory.name
        assert front["description"].strip()
        assert not set(front) - CHECK.ALLOWED_KEYS, directory.name


# ---------- paths in the layout the vault had before thread folders ----------

@pytest.mark.parametrize("stale", [
    "| `logs/<Kind>/<Name>/<date>.md` | the path | the filename |",
    "| `notes/<timestamp>.md` | `threads:` frontmatter |",
    "Read `hours/<Kind>/<Thread>.md` for the added entries.",
    "Notes live in `~/vault/notes/`.",
    "REF: [[hours/Processes/SGB]] 1h 0m",
])
def test_a_path_in_the_old_layout_is_reported(stale):
    found = problems(stale)
    assert len(found) == 1 and "old vault layout" in found[0], found


@pytest.mark.parametrize("fine", [
    "| `threads/<Kind>/<Name>/logs/<date>.md` | the path |",
    "Search notes/logs, then read the file.",
    "Every thread's notes/ and logs/ are walked.",
    "REF: [[Processes/SGB/hours]] 1h 0m",
])
def test_a_path_in_the_thread_folder_layout_passes(fine):
    assert problems(fine) == []
