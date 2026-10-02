"""The container installs the package; it used to mount it.

The image now builds a venv at /opt/venv and installs the package into it, so
the ten commands inside the container are the same console scripts the tests
run here. What has to hold is that the install is the *only* way the package
gets there: no PYTHONPATH, no wrappers around `python3 -m`, and nothing
expected at a mount point. An image that quietly went back to mounting source
would work on the host and fail wherever the repo is not checked out.

No Docker is needed for any of this: the Dockerfile is read as text, and the
install it performs is reproduced with a wheel built from the same sources.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tomllib

import pytest

from harness import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "dev"))
from commands import COMMANDS

DOCKERFILE = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
VENV = "/opt/venv"


def test_the_package_is_installed_into_a_venv_on_path():
    """The whole point of the change: the image carries the package rather
    than expecting to find it mounted."""
    assert re.search(rf"python3 -m venv --copies {VENV}", DOCKERFILE)
    assert re.search(rf"{VENV}/bin/pip install .*/src", DOCKERFILE)
    assert f"COPY --from=build {VENV} {VENV}" in DOCKERFILE
    assert f"ENV PATH={VENV}/bin:$PATH" in DOCKERFILE


def instructions(text=None):
    """The Dockerfile's instructions, without its prose. The comments name
    the things this file deliberately no longer does, so a check for those
    has to read what the build runs, not what it explains."""
    lines = (text if text is not None else DOCKERFILE).splitlines()
    return "\n".join(ln for ln in lines if not ln.lstrip().startswith("#"))


def runtime_stage():
    """The shipped stage: everything after the last `FROM`. The build stage
    before it may do things the runtime must not, such as putting Debian's
    setuptools on PYTHONPATH for the install."""
    return DOCKERFILE.split("\nFROM ")[-1]


def test_nothing_is_expected_at_a_mount_point_or_on_pythonpath():
    """`PYTHONPATH` and the `/opt/adulting` mount were how the old image
    found the source. Either one coming back means the image depends on the
    host repo again, and the commands would vanish without it."""
    assert "PYTHONPATH" not in instructions(runtime_stage())
    assert "/opt/adulting" not in instructions()
    # Wrappers around `python3 -m adulting.<name>` are gone with it.
    assert "-m adulting." not in instructions()


def test_the_build_runs_a_command_before_shipping():
    """A broken install should fail the build, not the agent's first tool
    call, so the Dockerfile runs one command itself."""
    assert re.search(rf"RUN {VENV}/bin/\w+ --help-json", DOCKERFILE)


def test_the_build_copies_what_the_install_needs_and_no_more():
    """`readme` in pyproject.toml points at README.md, so the install fails
    without it; tests, stories and the host's own .venv have no business in
    the image."""
    copied = re.findall(r"^COPY (?!--from)(.+) /src", DOCKERFILE, re.M)
    assert copied == ["pyproject.toml README.md", "src"]


def test_the_wheel_is_configured_to_carry_the_schemas():
    """`lint` reads its schemas from the installed package, and the image has
    no repo to fall back on. They ship only because pyproject says so, and
    nothing else here would notice if that line went."""
    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    assert config["tool"]["setuptools"]["package-data"] == {"adulting": ["schemas/*.md"]}
    on_disk = sorted(p.name for p in (REPO_ROOT / "src" / "adulting" / "schemas").glob("*.md"))
    assert on_disk, "no schemas to ship"


@pytest.mark.parametrize("command", COMMANDS)
def test_every_command_is_a_console_script_the_install_creates(command):
    """In the container these are the only way to run a command: there is no
    source tree to `python3 -m`, so one missing from [project.scripts] exists
    on the host, where the dev venv is editable, and nowhere else."""
    scripts = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["project"]["scripts"]
    assert scripts[command] == f"adulting.{command}:main"


# ---------- the entrypoint that installs the tool definitions ----------

ENTRYPOINT = REPO_ROOT / "container" / "entrypoint.sh"
TOOLS = sorted(p.name for p in (REPO_ROOT / "dev" / "tools").glob("*.json"))


def test_the_image_ships_the_definitions_and_runs_them_through_the_entrypoint():
    assert "COPY dev/tools /opt/tools" in instructions()
    assert "COPY container/entrypoint.sh /usr/local/bin/adulting-entrypoint" in instructions()
    assert 'ENTRYPOINT ["/usr/local/bin/adulting-entrypoint"]' in instructions()


@pytest.fixture
def entrypoint(tmp_path):
    """Run the shim as the image would, with a stub for the agent binary and
    the shipped definitions where the image puts them."""
    src = tmp_path / "opt" / "tools"
    src.mkdir(parents=True)
    for name in TOOLS:
        (src / name).write_text(((REPO_ROOT / "dev" / "tools" / name).read_text()),
                                encoding="utf-8")
    state = tmp_path / "state"
    stub = tmp_path / "agent"
    stub.write_text('#!/bin/sh\necho "agent ran with: $*"\n', encoding="utf-8")
    stub.chmod(0o755)

    skills = tmp_path / "opt" / "skills"
    (skills / "a-skill").mkdir(parents=True)
    (skills / "a-skill" / "SKILL.md").write_text("---\nname: a-skill\n---\n",
                                                 encoding="utf-8")

    def run():
        return subprocess.run([str(ENTRYPOINT), "-mailbox"], capture_output=True, text=True,
                              env={**os.environ, "AGENT_STATE_DIR": str(state),
                                   "AGENT_BIN": str(stub),
                                   "ADULTING_TOOLS_DIR": str(src),
                                   "ADULTING_SKILLS_DIR": str(skills)})

    run.state = state
    run.src = src
    run.skills = skills
    return run


def test_the_definitions_are_installed_and_the_agent_gets_its_arguments(entrypoint):
    r = entrypoint()
    assert r.returncode == 0, r.stderr
    assert sorted(p.name for p in (entrypoint.state / "tools").glob("*.json")) == TOOLS
    assert f"adulting: installed {len(TOOLS)} tool definition(s)" in r.stdout
    assert "agent ran with: -mailbox" in r.stdout


def test_a_stale_definition_is_overwritten_and_a_foreign_one_is_left_alone(entrypoint):
    """The image is the source of truth for the files it ships, and nothing
    else: the agent seeds its own builtins into this directory."""
    tools = entrypoint.state / "tools"
    tools.mkdir(parents=True)
    (tools / "tasks.json").write_text('{"command": "tasks", "description": "stale"}',
                                      encoding="utf-8")
    (tools / "read_file.json").write_text('{"builtin": true, "description": "the agent\'s own"}',
                                          encoding="utf-8")

    r = entrypoint()
    assert r.returncode == 0, r.stderr
    assert "stale" not in (tools / "tasks.json").read_text(encoding="utf-8")
    assert (tools / "tasks.json").read_text(encoding="utf-8") == \
        (REPO_ROOT / "dev" / "tools" / "tasks.json").read_text(encoding="utf-8")
    assert "the agent's own" in (tools / "read_file.json").read_text(encoding="utf-8")


def test_a_definition_naming_a_missing_command_is_reported_not_deleted(entrypoint):
    """The directory is shared, so a definition for someone else's binary is
    not ours to remove — but the model would call it and fail, so it is said."""
    tools = entrypoint.state / "tools"
    tools.mkdir(parents=True)
    (tools / "frobnicate.json").write_text('{"command": "frobnicate", "description": "x"}',
                                           encoding="utf-8")

    r = entrypoint()
    assert r.returncode == 0, r.stderr
    assert "adulting: warning: frobnicate.json names frobnicate, which is not on PATH" in r.stderr
    assert (tools / "frobnicate.json").is_file()
    # A builtin has no `command` and is not reported.
    assert "read_file" not in r.stderr


def test_the_agent_still_starts_when_the_state_directory_cannot_be_written(entrypoint, tmp_path):
    """A read-only mount is a reason to say so, not to leave the mailbox
    unattended."""
    entrypoint.state.mkdir(parents=True)
    (entrypoint.state / "tools").mkdir()
    (entrypoint.state / "tools").chmod(0o500)
    try:
        r = entrypoint()
    finally:
        (entrypoint.state / "tools").chmod(0o700)
    assert r.returncode == 0, r.stderr
    assert "cannot write" in r.stderr
    assert "agent ran with: -mailbox" in r.stdout


SKILLS = sorted(d.name for d in (REPO_ROOT / "agent" / "skills").iterdir() if d.is_dir())


def test_the_image_ships_the_skills_too():
    assert "COPY agent/skills /opt/skills" in instructions()
    assert SKILLS, "no skills committed"


def test_the_skills_are_installed_as_folders(entrypoint):
    """A skill is a folder holding SKILL.md, so the install has to copy a
    tree, not a file."""
    r = entrypoint()
    assert r.returncode == 0, r.stderr
    assert "adulting: installed 1 skill(s)" in r.stdout
    assert (entrypoint.skills / "a-skill" / "SKILL.md").is_file()
    installed = entrypoint.state / "skills" / "a-skill" / "SKILL.md"
    assert installed.read_text(encoding="utf-8") == "---\nname: a-skill\n---\n"


def test_a_stale_skill_is_replaced_whole_and_a_foreign_one_is_kept(entrypoint):
    """Replaced, not merged: a file the new version of a skill no longer has
    would otherwise linger inside it. Another image's skill is untouched."""
    skills = entrypoint.state / "skills"
    (skills / "a-skill").mkdir(parents=True)
    (skills / "a-skill" / "SKILL.md").write_text("stale", encoding="utf-8")
    (skills / "a-skill" / "references").mkdir()
    (skills / "a-skill" / "references" / "gone.md").write_text("old", encoding="utf-8")
    (skills / "someone-elses").mkdir()
    (skills / "someone-elses" / "SKILL.md").write_text("theirs", encoding="utf-8")

    r = entrypoint()
    assert r.returncode == 0, r.stderr
    assert "stale" not in (skills / "a-skill" / "SKILL.md").read_text(encoding="utf-8")
    assert not (skills / "a-skill" / "references").exists()
    assert (skills / "someone-elses" / "SKILL.md").read_text(encoding="utf-8") == "theirs"


def test_nothing_is_left_behind_when_an_install_is_interrupted(entrypoint):
    """Each file is staged under a dotted name and renamed into place, so a
    watcher never reads half of one. Nothing dotted should survive."""
    r = entrypoint()
    assert r.returncode == 0, r.stderr
    for directory in (entrypoint.state / "tools", entrypoint.state / "skills"):
        assert [p.name for p in directory.iterdir() if p.name.startswith(".")] == []
