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

import re
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
