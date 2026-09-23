"""The harness itself. If these fail, no other result can be trusted."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from harness import (PRODUCTION_VAULT, REPO_ROOT, clean_path,
                     command_path, isolated_env)


TOOLS = ["tasks", "buffer", "notes", "search", "threads", "people",
         "hours", "payments", "lint", "commit"]


def test_every_command_is_this_checkouts_console_script():
    for name in TOOLS:
        assert command_path(name) == str(REPO_ROOT / ".venv" / "bin" / name)


def test_a_child_process_finds_this_repos_commands_too():
    """A child process inherits the isolated PATH, so a command that looks
    another up by name finds this checkout's copy."""
    code = "import shutil; print(shutil.which('buffer')); print(shutil.which('tasks'))"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                         text=True, env=dict(os.environ)).stdout.split()
    assert out == [str(REPO_ROOT / ".venv" / "bin" / "buffer"),
                   str(REPO_ROOT / ".venv" / "bin" / "tasks")]


def test_environment_points_away_from_production(tmp_path):
    assert Path(os.environ["ADULTING_HOME"]).resolve() == (tmp_path / "vault").resolve()
    assert Path(os.environ["HOME"]).resolve() == (tmp_path / "home").resolve()
    assert not Path(os.environ["ADULTING_HOME"]).resolve().is_relative_to(PRODUCTION_VAULT)


def test_isolated_env_refuses_the_production_vault(tmp_path):
    with pytest.raises(RuntimeError):
        isolated_env(home=tmp_path, vault=PRODUCTION_VAULT)
    with pytest.raises(RuntimeError):
        isolated_env(home=tmp_path, vault=PRODUCTION_VAULT / "notes")


def test_clean_path_drops_other_copies_of_adulting(tmp_path):
    other = tmp_path / "other-install"
    other.mkdir()
    (other / "tasks").write_text("#!/bin/sh\n")
    system = tmp_path / "system"
    system.mkdir()
    path = clean_path(os.pathsep.join([str(other), str(system)]))
    entries = path.split(os.pathsep)
    assert str(other) not in entries
    assert str(system) in entries
    assert entries[:2] == [str(REPO_ROOT / ".venv" / "bin"), str(REPO_ROOT)]


def test_command_path_rejects_a_command_from_outside_the_repo(tmp_path):
    other = tmp_path / "bin"
    other.mkdir()
    fake = other / "lint"
    fake.write_text("#!/bin/sh\n")
    fake.chmod(0o755)
    with pytest.raises(RuntimeError):
        command_path("lint", env={"PATH": str(other)})


def test_a_cross_command_write_lands_in_the_test_vault(vault):
    """`tasks add` shells out to `buffer`; the entry must reach this vault."""
    vault.write_thread("Projects", "SGB")
    r = vault.run("add", "Projects/SGB", "Draft the scope note", cli="tasks")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Draft the scope note" in vault.read("buffer.md")


