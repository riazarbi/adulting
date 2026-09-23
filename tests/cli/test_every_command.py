"""Contracts every command keeps: the surface `--help-json` describes, and
refusing a vault that is not there."""

import json
import subprocess
import sys

import pytest

# Every command is built by vault.command_parser, so --help-json comes first.
SURFACE = {
    "tasks": (["--help-json", "--dry-run", "--quiet"],
              ["ingest", "add", "done", "set-description", "set-assignee", "set-due", "set-scheduled",
               "set-priority", "add-depends", "rm-depends", "list", "next", "show"]),
    "notes": (["--help-json"], ["new", "list", "cat", "last", "copy", "delete", "pdf", "minutes", "agenda"]),
    "search": (["--help-json"], ["notes", "logs", "activity", "overview", "stream"]),
    "threads": (["--help-json"], ["list", "show", "new", "delete"]),
    "people": (["--help-json"], ["list", "show", "new", "delete"]),
    "hours": (["--help-json"], ["log", "list", "report", "show", "edit", "rm"]),
    "payments": (["--help-json"], ["log", "list", "statement", "show", "edit", "rm"]),
    "buffer": (["--help-json", "--quiet"], ["add", "add-text", "add-ref", "add-action",
                             "list", "rm", "tend", "flush"]),
    "lint": (["--help-json", "--schemas", "--quiet"], []),
    "commit": (["--help-json"], ["review", "save"]),
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


@pytest.mark.parametrize("cli, argv", USES, ids=[" ".join([c, *a]) for c, a in USES])
def test_a_missing_vault_is_refused(vault, tmp_path, cli, argv):
    check_refused(vault, tmp_path, cli, argv, "missing")


# One command of each kind is enough for the second shape: the check itself
# is the same one.
@pytest.mark.parametrize("cli, argv", [("tasks", ["list"]), ("buffer", ["add", "x"])])
def test_a_vault_that_is_a_file_is_refused(vault, tmp_path, cli, argv):
    check_refused(vault, tmp_path, cli, argv, "a file")


def check_refused(vault, tmp_path, cli, argv, what):
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


# One command per shape: a name that differs from its file (notes.py), one
# with no subcommands (lint), and one with a subcommand (tasks).
@pytest.mark.parametrize("cli", ["notes", "lint", "tasks"])
def test_errors_name_the_command_even_under_python_m(vault, tmp_path, cli):
    """The `<command>:` prefix used to come from argv[0], so under
    `python -m adulting.notes` errors read `notes.py: error: ...`."""
    env = dict(vault.env, ADULTING_HOME=str(tmp_path / "missing"))
    argv = {"lint": [], "commit": ["review"], "search": ["notes"]}.get(cli, ["list"])
    r = subprocess.run([sys.executable, "-m", f"adulting.{cli}", *argv],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 1
    assert r.stderr == f"{cli}: error: ADULTING_HOME is not a directory: {tmp_path / 'missing'}\n"



@pytest.mark.parametrize("cli, argv", [
    ("hours", ["list"]), ("hours", ["report"]), ("payments", ["list"]), ("payments", ["statement"]),
    ("search", ["notes"]), ("search", ["stream"]),
])
@pytest.mark.parametrize("flag, value", [("--since", "x"), ("--until", "2026-13-01")])
def test_a_window_date_must_be_a_real_date(vault, cli, argv, flag, value):
    """`hours list --since x` used to be accepted, and bounded nothing."""
    r = vault.run(*argv, flag, value, cli=cli)
    assert (r.returncode, r.stdout) == (2, "")
    assert r.stderr.splitlines()[-1] == (
        f"{cli} {argv[0]}: error: argument {flag}: expected a date as YYYY-MM-DD, got {value!r}")


# Data that says `--help-json`, written the two ways a flag-shaped value is
# passed: after `--`, and as `--flag=value`.
WRITES = [
    ("buffer", ["add-text", "Projects/SGB", "--", "--help-json"], "buffer.md"),
    ("buffer", ["add", "--", "--help-json"], "buffer.md"),
    ("notes", ["new", "--type", "Log", "--thread", "Projects/SGB", "--topic=--help-json"], None),
    ("commit", ["save", "--message=--help-json"], None),
]


@pytest.mark.parametrize("cli, argv, wrote", WRITES, ids=[" ".join([c, *a]) for c, a, _ in WRITES])
def test_help_json_as_data_does_not_hijack_a_write(vault, cli, argv, wrote):
    """It used to be scanned out of sys.argv before parsing, so a command
    whose data said `--help-json` printed the manifest and exited 0 without
    writing anything: silent data loss, reported as success."""
    vault.write_thread("Projects", "SGB")
    if cli == "commit":
        subprocess.run(["git", "-C", str(vault.home), "init", "-q"], check=True, env=vault.env)
        vault.write("notes/seed.md", "seed\n")
    r = vault.run(*argv, cli=cli)
    assert r.returncode == 0, r.stderr
    assert not r.stdout.startswith("{")
    if wrote:
        assert "--help-json" in vault.read(wrote)


@pytest.mark.parametrize("cli", SURFACE)
def test_help_json_is_a_documented_flag(vault, cli):
    manifest = json.loads(vault.run("--help-json", cli=cli).stdout)
    [flag] = [f for f in manifest["flags"] if f["name"] == "--help-json"]
    assert flag["description"] == "Print this command's arguments as JSON, and exit."


@pytest.mark.parametrize("cli, subcommand", [("buffer", "add-action"), ("tasks", "add")])
def test_depends_help_says_a_whole_uuid(vault, cli, subcommand):
    """--depends must be exactly 8 hex characters, so calling it a prefix
    invites a shorter one that is then refused."""
    manifest = json.loads(vault.run("--help-json", cli=cli).stdout)
    [sub] = [s for s in manifest["subcommands"] if s["name"] == subcommand]
    [flag] = [f for f in sub["flags"] if f["name"] == "--depends"]
    assert flag["description"] == "A task's 8-character uuid, from `tasks list`; repeatable."
