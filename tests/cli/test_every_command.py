"""Contracts every command keeps: the surface `--help-json` describes, and
refusing a vault that is not there."""

import json

import pytest

SURFACE = {
    "tasks": (["--dry-run", "--quiet"],
              ["add", "done", "set-description", "set-assignee", "set-due", "set-scheduled",
               "set-priority", "add-depends", "rm-depends", "list", "next", "show"]),
    "notes": ([], ["new", "list", "cat", "last", "copy", "delete", "pdf", "minutes", "agenda"]),
    "search": ([], ["notes", "logs", "activity", "overview", "stream"]),
    "threads": ([], ["list", "show", "new", "delete"]),
    "people": ([], ["list", "show", "new", "delete"]),
    "hours": ([], ["log", "list", "report", "show", "edit", "rm"]),
    "payments": ([], ["log", "list", "statement", "show", "edit", "rm"]),
    "buffer": (["--quiet"], ["add", "suggest", "add-text", "add-ref", "add-action",
                             "list", "rm", "tend", "flush"]),
    "lint": (["--schemas", "--quiet"], []),
    "commit": ([], ["review", "save"]),
}


@pytest.mark.parametrize("cli", SURFACE)
def test_help_json_describes_the_command(vault, cli):
    """The manual and the agent tool definitions are built from this."""
    r = vault.run("--help-json", cli=cli)
    assert (r.returncode, r.stderr) == (0, "")
    manifest = json.loads(r.stdout)
    flags, subcommands = SURFACE[cli]
    assert manifest["name"] == cli
    assert [f["name"] for f in manifest.get("flags", [])] == flags
    assert [s["name"] for s in manifest.get("subcommands", [])] == subcommands


# One ordinary use of each command: a read for most, a write for those
# that used to create a vault wherever ADULTING_HOME pointed.
USES = [
    ("tasks", ["list"]), ("notes", ["list"]), ("search", ["notes"]), ("threads", ["list"]),
    ("people", ["list"]), ("hours", ["list"]), ("payments", ["list"]), ("lint", []),
    ("commit", ["review"]), ("buffer", ["add", "x"]),
    ("people", ["new", "--name", "A", "--category", "personal"]),
    ("threads", ["new", "--kind", "topic", "--category", "personal", "--name", "T"]),
]


@pytest.mark.parametrize("what", ["missing", "a file"])
@pytest.mark.parametrize("cli, argv", USES, ids=[" ".join([c, *a]) for c, a in USES])
def test_a_vault_that_is_not_a_directory_is_refused(vault, tmp_path, cli, argv, what):
    """Reads used to report an empty vault and writes used to start a new
    one wherever ADULTING_HOME pointed, so a mistyped path went unnoticed.
    A file there crashed with a traceback."""
    home = tmp_path / "elsewhere"
    if what == "a file":
        home.write_text("not a vault")
    vault.env["ADULTING_HOME"] = str(home)
    r = vault.run(*argv, cli=cli)
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == f"{cli}: error: ADULTING_HOME is not a directory: {home}\n"
    assert home.exists() == (what == "a file")
    if what == "a file":
        assert home.read_text() == "not a vault"
