"""Isolation rules shared by the test suite and dev/testbed.

Two things can make a test lie about which code or which data it touched:

1. PATH. Your shell finds `tasks`, `buffer`, `notes` ... in ~/bin/adulting
   (the production checkout, pinned to main). Several commands call each
   other by name, so a test that runs *this* repo's `buffer` could silently
   have it call *production's* `tasks`.

2. ADULTING_HOME / HOME. Your shell exports ADULTING_HOME=~/vault. Anything
   that inherits the environment without overriding it writes to the real
   vault.

`isolated_env()` builds an environment that closes both holes: PATH holds
this repo's commands and system tools only, and HOME / ADULTING_HOME point
at directories the caller chose. Nothing here is a mock: the commands run
for real, against real files, in a place that is not production.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_BIN = REPO_ROOT / ".venv" / "bin"

# Every command name the project has ever put on PATH. A PATH directory that
# holds any of these, and is not one of ours, belongs to another copy of
# adulting (~/bin/adulting, a pipx install, ...) and is dropped.
COMMANDS = [
    "tasks", "buffer", "notes", "search", "threads", "people", "hours",
    "payments", "stats", "lint", "commit",
    "notes_new", "notes_pdf", "notes_minutes", "notes_agenda", "notes_strip",
]

# The production vault, as your shell sees it. Only used to refuse it.
PRODUCTION_VAULT = Path(
    os.environ.get("ADULTING_HOME", os.path.expanduser("~/vault"))
).resolve()


def own_bin_dirs(repo_root: Path = REPO_ROOT) -> list[Path]:
    """Where a checkout's commands live, most preferred first.

    This checkout's commands are console scripts in .venv/bin. The root is
    kept for dev/testbed, whose old implementation is a directory of root
    scripts; this checkout has none (tests/unit/test_harness.py checks).
    """
    return [repo_root / ".venv" / "bin", repo_root]


def clean_path(original: str, repo_root: Path = REPO_ROOT) -> str:
    """Return a PATH with our dirs first and other adulting copies removed."""
    ours = [str(d) for d in own_bin_dirs(repo_root)]
    kept = []
    for entry in original.split(os.pathsep):
        if not entry or entry in ours or entry in kept:
            continue
        if any((Path(entry) / name).exists() for name in COMMANDS):
            continue
        kept.append(entry)
    return os.pathsep.join(ours + kept)


def is_inside(path: Path, parent: Path) -> bool:
    path, parent = Path(path).resolve(), Path(parent).resolve()
    return path == parent or parent in path.parents


def isolated_env(home: Path, vault: Path, repo_root: Path = REPO_ROOT,
                 base: dict | None = None) -> dict:
    """A copy of `base` (default os.environ) that is safe to run commands in."""
    if is_inside(vault, PRODUCTION_VAULT) or is_inside(PRODUCTION_VAULT, vault):
        raise RuntimeError(f"refusing to use the production vault: {vault}")
    env = dict(os.environ if base is None else base)
    env["HOME"] = str(home)
    env["ADULTING_HOME"] = str(vault)
    env["PATH"] = clean_path(env.get("PATH", ""), repo_root)
    # Commits made by `commit save` in a test vault get a fixed identity
    # instead of whatever gitconfig the real HOME would have provided.
    env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = "adulting-test"
    env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = "test@adulting.local"
    env.pop("EXPORT_DIR", None)
    return env


def without_program(env: dict, program: str) -> dict:
    """A copy of `env` whose PATH has no directory holding `program`. Used to
    make a real tool fail for real, e.g. pandoc with no xelatex to call."""
    kept = [d for d in env["PATH"].split(os.pathsep)
            if d and not (Path(d) / program).exists()]
    return {**env, "PATH": os.pathsep.join(kept)}


def command_path(name: str, env: dict | None = None) -> str:
    """Absolute path of `name` as the isolated PATH resolves it.

    Fails loudly if the command would come from outside this checkout.
    """
    path_var = (env or os.environ).get("PATH", "")
    found = shutil.which(name, path=path_var)
    if found is None:
        raise FileNotFoundError(f"{name} is not on the isolated PATH")
    if not is_inside(Path(found), REPO_ROOT):
        raise RuntimeError(f"{name} resolves outside this repo: {found}")
    return found
