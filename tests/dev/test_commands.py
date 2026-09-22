"""dev/commands.py is the one list of operator commands the dev scripts share."""

import sys
import tomllib

from harness import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "dev"))
from commands import COMMANDS  # noqa: E402


def test_the_command_list_is_every_console_script_once():
    scripts = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["project"]["scripts"]
    assert sorted(COMMANDS) == sorted(scripts)
