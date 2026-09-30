"""The container runs the package a different way from everything else.

The image bind-mounts the source at runtime, so nothing is installed: each
command is a wrapper around `python3 -m adulting.<name>`, with PYTHONPATH
pointing at the mounted `src/`. Every other test here runs the venv's console
scripts, so nothing else exercises that path — a module that lost its
`__main__` guard, or that imports something only an install provides, would
break the container and leave CI green.

No Docker is needed: the Dockerfile is read as text, and the invocation it
builds is run directly.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

import pytest

from harness import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "dev"))
from commands import COMMANDS

DOCKERFILE = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
SRC = str(REPO_ROOT / "src")


def wrapped_commands():
    """The command names the image writes wrappers for."""
    [names] = re.findall(r"for cmd in ([^;]+);", DOCKERFILE)
    return names.split()


def run_as_a_module(command, path=SRC):
    """Run one command the way the container's wrapper does.

    `-S` keeps site-packages out, so the venv's own editable install cannot
    answer: what runs is the source `path` points at, exactly as it is for a
    bind mount into an image with nothing installed.
    """
    env = {**os.environ, "PYTHONPATH": path}
    return subprocess.run([sys.executable, "-S", "-m", f"adulting.{command}", "--help-json"],
                          capture_output=True, text=True, env=env, cwd=REPO_ROOT)


def test_the_image_wraps_every_command_and_only_those():
    """The names are written out in the Dockerfile, away from the one list
    the dev scripts share, so an eleventh command would be missing from the
    container with nothing to say so."""
    assert wrapped_commands() == COMMANDS


def test_the_wrappers_run_the_module_against_the_mounted_source():
    """If this ever became a console script or an install step, the test
    below would be testing something the image no longer does."""
    assert 'exec python3 -m adulting.%s "$@"' in DOCKERFILE
    assert "ENV PYTHONPATH=/opt/adulting/src" in DOCKERFILE


@pytest.mark.parametrize("command", COMMANDS)
def test_every_command_runs_as_a_module_with_only_the_source_on_the_path(command):
    r = run_as_a_module(command)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["name"] == command


def test_without_the_source_on_the_path_there_is_nothing_to_run(tmp_path):
    """Proves the test above is not passing on an installed copy: point
    PYTHONPATH somewhere empty and the same call cannot find the package."""
    r = run_as_a_module(COMMANDS[0], path=str(tmp_path))
    assert r.returncode != 0
    assert "No module named 'adulting'" in r.stderr
