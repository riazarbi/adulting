"""Functional tests for the `commit` CLI.

Each test builds a throwaway git repo in a tmp dir and points
ADULTING_HOME at it. The identity comes from GIT_AUTHOR_*/GIT_COMMITTER_*
in the environment, mirroring how the agent container is configured (see
the ENV block in the Dockerfile) rather than from any gitconfig on the
machine running the suite.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from harness import command_path

REPO_ROOT = Path(__file__).resolve().parents[2]


class GitVault:
    def __init__(self, home: Path):
        self.home = home
        self.env = dict(os.environ)  # already isolated by conftest
        self.env.update({
            "ADULTING_HOME": str(home),
            "GIT_AUTHOR_NAME": "agent",
            "GIT_AUTHOR_EMAIL": "agent@adulting.local",
            "GIT_COMMITTER_NAME": "agent",
            "GIT_COMMITTER_EMAIL": "agent@adulting.local",
        })

    def git(self, *argv: str) -> str:
        r = subprocess.run(["git", "-C", str(self.home), *argv],
                           capture_output=True, text=True, env=self.env)
        assert r.returncode == 0, f"git {argv}: {r.stderr}"
        return r.stdout

    def write(self, relpath: str, text: str) -> Path:
        p = self.home / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def run(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run([command_path("commit"), *argv],
                              capture_output=True, text=True, env=self.env)

    def log_subjects(self) -> list[str]:
        return self.git("log", "--format=%s").strip().split("\n")


@pytest.fixture
def gitvault(tmp_path: Path) -> GitVault:
    home = tmp_path / "vault"
    (home / "notes").mkdir(parents=True)
    v = GitVault(home)
    v.git("init", "-q", ".")
    v.write("notes/seed.md", "line1\nline2\nline3\n")
    v.git("add", "-A")
    v.git("commit", "-qm", "seed")
    return v


# ---------- save cannot rewrite history ----------

def test_flag_shaped_message_appends_rather_than_rewrites(gitvault):
    """A --message of '--amend' must be committed as a literal subject and
    must append a commit, not rewrite the previous one."""
    before_head = gitvault.git("rev-parse", "HEAD").strip()
    before_count = len(gitvault.log_subjects())
    gitvault.write("notes/new.md", "hello\n")

    r = gitvault.run("save", "--message=--amend")
    assert r.returncode == 0, r.stderr
    assert r.stderr == ""

    assert len(gitvault.log_subjects()) == before_count + 1
    assert gitvault.git("log", "-1", "--format=%s").strip() == "--amend"
    # The new commit sits on top of the old HEAD; nothing was rewritten.
    assert gitvault.git("rev-parse", "HEAD^").strip() == before_head


def test_flag_shaped_message_in_separated_form_is_refused(gitvault):
    """`--message --amend` (space-separated) never reaches git: argparse
    refuses it, so nothing is staged or committed."""
    before_count = len(gitvault.log_subjects())
    gitvault.write("notes/new.md", "hello\n")

    r = gitvault.run("save", "--message", "--amend")
    assert r.returncode != 0
    assert r.stderr != ""
    assert len(gitvault.log_subjects()) == before_count
    assert gitvault.git("diff", "--cached", "--name-only") == ""


# ---------- review ----------

def test_review_is_read_only_and_lists_both_kinds_of_change(gitvault):
    gitvault.write("notes/seed.md", "line1\nCHANGED\nline3\n")
    gitvault.write("notes/brand-new.md", "fresh content\n")

    r = gitvault.run("review")
    assert r.returncode == 0, r.stderr
    assert r.stderr == ""

    assert "notes/seed.md" in r.stdout
    assert "notes/brand-new.md" in r.stdout
    assert "+CHANGED" in r.stdout          # tracked edit shown as a diff
    assert "+fresh content" in r.stdout    # untracked content shown too

    # Read-only: the index is exactly as we left it.
    assert gitvault.git("diff", "--cached", "--name-only") == ""


def test_review_lists_files_inside_a_new_directory_individually(gitvault):
    """Without -uall git collapses a new directory to `assets/`, which
    would under-report what `save` is about to commit."""
    gitvault.write("assets/deep/one.md", "one\n")
    gitvault.write("assets/deep/two.md", "two\n")

    r = gitvault.run("review")
    assert r.returncode == 0, r.stderr
    assert "assets/deep/one.md" in r.stdout
    assert "assets/deep/two.md" in r.stdout


def test_review_truncation_is_configurable_and_announced(gitvault):
    gitvault.write("notes/big.md", "\n".join(str(i) for i in range(400)) + "\n")

    full = gitvault.run("review")
    capped = gitvault.run("review", "--max-file-lines", "5")
    assert capped.returncode == 0, capped.stderr
    assert len(capped.stdout.split("\n")) < len(full.stdout.split("\n"))
    assert "--max-file-lines" in capped.stdout      # truncation announced in-band
    assert "truncated" in capped.stdout

    globally = gitvault.run("review", "--max-lines", "10")
    assert globally.returncode == 0, globally.stderr
    assert "--max-lines" in globally.stdout
    assert len(globally.stdout.strip().split("\n")) <= 12


def test_review_on_clean_tree(gitvault):
    r = gitvault.run("review")
    assert r.returncode == 0
    assert r.stderr == ""
    assert "clean" in r.stdout


# ---------- message handling ----------

def test_multiline_body_round_trips(gitvault):
    gitvault.write("notes/new.md", "hello\n")
    body = "First paragraph.\n\nSecond paragraph,\nwith a second line."

    r = gitvault.run("save", "--message", "Subject line", "--body", body)
    assert r.returncode == 0, r.stderr
    assert r.stderr == ""

    full = gitvault.git("log", "-1", "--format=%B")
    assert full.startswith("Subject line\n\nFirst paragraph.\n\n"
                           "Second paragraph,\nwith a second line.")


def test_multiline_message_is_rejected(gitvault):
    gitvault.write("notes/new.md", "hello\n")
    before_count = len(gitvault.log_subjects())

    r = gitvault.run("save", "--message", "subject\nsneaky second line")
    assert r.returncode != 0
    assert "--body" in r.stderr
    assert len(gitvault.log_subjects()) == before_count
    assert gitvault.git("diff", "--cached", "--name-only") == ""


# ---------- save behaviour ----------

def test_save_commits_every_change(gitvault):
    gitvault.write("notes/seed.md", "edited\n")
    gitvault.write("assets/deep/new.md", "brand new\n")

    r = gitvault.run("save", "--message", "Record the day's work")
    assert r.returncode == 0, r.stderr
    assert r.stderr == ""

    committed = gitvault.git("show", "--name-only", "--format=", "HEAD").split()
    assert "notes/seed.md" in committed
    assert "assets/deep/new.md" in committed
    assert gitvault.git("status", "--porcelain") == ""


def test_dry_run_changes_nothing(gitvault):
    gitvault.write("notes/new.md", "hello\n")
    before_count = len(gitvault.log_subjects())

    r = gitvault.run("save", "--message", "Would commit", "--dry-run")
    assert r.returncode == 0, r.stderr
    assert r.stderr == ""
    assert "notes/new.md" in r.stdout
    assert "Would commit" in r.stdout

    assert len(gitvault.log_subjects()) == before_count
    assert gitvault.git("diff", "--cached", "--name-only") == ""


def test_clean_tree_is_a_success(gitvault):
    r = gitvault.run("save", "--message", "nothing doing")
    assert r.returncode == 0
    assert r.stderr == ""
    assert "nothing to commit" in r.stdout


def test_non_repo_home_fails_cleanly(gitvault, tmp_path):
    gitvault.env["ADULTING_HOME"] = str(tmp_path / "not-a-repo")
    (tmp_path / "not-a-repo").mkdir()

    r = gitvault.run("review")
    assert r.returncode != 0
    assert "not a git repository" in r.stderr
    assert r.stdout == ""


# ---------- characterisation added before the port (refactor unit 1) ----------

def test_home_that_is_not_a_directory_fails_cleanly(gitvault, tmp_path):
    gitvault.env["ADULTING_HOME"] = str(tmp_path / "missing")
    r = gitvault.run("review")
    assert r.returncode == 1
    assert r.stderr.startswith("error: ADULTING_HOME is not a directory:")
    assert r.stdout == ""


def test_home_that_is_a_subdirectory_of_a_repo_is_refused(gitvault):
    """`git add -A` from a subdirectory would sweep in files outside the vault."""
    gitvault.env["ADULTING_HOME"] = str(gitvault.home / "notes")
    gitvault.write("outside.md", "not vault content\n")
    r = gitvault.run("save", "--message", "should not happen")
    assert r.returncode == 1
    assert "is not the root of its git repository" in r.stderr
    assert gitvault.git("diff", "--cached", "--name-only") == ""


def test_empty_message_is_rejected(gitvault):
    gitvault.write("notes/new.md", "hello\n")
    r = gitvault.run("save", "--message", "   ")
    assert r.returncode == 1
    assert r.stderr == "error: --message must not be empty\n"


def test_review_listing_format(gitvault):
    gitvault.write("notes/seed.md", "edited\n")
    gitvault.write("notes/new.md", "hello\n")
    (gitvault.home / "notes" / "gone.md").write_text("x\n")
    gitvault.git("add", "notes/gone.md")
    gitvault.git("commit", "-qm", "add gone")
    (gitvault.home / "notes" / "gone.md").unlink()

    r = gitvault.run("review")
    lines = r.stdout.split("\n")
    assert lines[0] == "Changed paths:"
    assert "  modified    notes/seed.md" in lines
    assert "  deleted     notes/gone.md" in lines
    assert "  untracked   notes/new.md" in lines
    assert "Changes to tracked files:" in lines
    assert "New files:" in lines


def test_review_shows_a_staged_rename_as_old_arrow_new(gitvault):
    gitvault.git("mv", "notes/seed.md", "notes/renamed.md")
    r = gitvault.run("review")
    assert r.returncode == 0, r.stderr
    assert "  renamed     notes/seed.md -> notes/renamed.md" in r.stdout.split("\n")


def test_review_shows_an_empty_new_file_as_a_bare_diff_header(gitvault):
    """git still emits a header for an empty file, so the tool's
    `[new empty file: ...]` fallback is not reached with current git."""
    gitvault.write("notes/empty.md", "")
    r = gitvault.run("review")
    assert "diff --git a/notes/empty.md b/notes/empty.md" in r.stdout
    assert "new file mode 100644" in r.stdout


def test_review_before_the_first_commit_lists_new_files(tmp_path):
    home = tmp_path / "fresh"
    home.mkdir()
    v = GitVault(home)
    v.git("init", "-q", ".")
    v.write("notes/first.md", "first\n")
    r = v.run("review")
    assert r.returncode == 0, r.stderr
    assert "  untracked   notes/first.md" in r.stdout
    assert "+first" in r.stdout
    assert "Changes to tracked files:" not in r.stdout


def test_filenames_with_spaces_and_non_ascii_are_readable(gitvault):
    gitvault.write("people/José Núñez.md", "hola\n")
    r = gitvault.run("review")
    assert "  untracked   people/José Núñez.md" in r.stdout
    s = gitvault.run("save", "--message", "Add José")
    assert s.returncode == 0, s.stderr
    assert "people/José Núñez.md" in gitvault.git(
        "-c", "core.quotepath=false", "show", "--name-only", "--format=", "HEAD")


def test_dry_run_output_format(gitvault):
    gitvault.write("notes/new.md", "hello\n")
    r = gitvault.run("save", "--message", "Subject", "--body", "Line one\nLine two",
                     "--dry-run")
    assert r.stdout == (
        "dry run — nothing staged, nothing committed.\n"
        "\n"
        "Would stage 1 path(s):\n"
        "  untracked   notes/new.md\n"
        "\n"
        "Would commit with message:\n"
        "  Subject\n"
        "\n"
        "  Line one\n"
        "  Line two\n")


def test_save_output_format(gitvault):
    gitvault.write("notes/new.md", "hello\n")
    gitvault.write("notes/seed.md", "edited\n")
    r = gitvault.run("save", "--message", "Two changes")
    sha = gitvault.git("rev-parse", "--short", "HEAD").strip()
    assert r.stdout == (f"committed {sha}: Two changes\n"
                        "2 path(s) staged and committed.\n")


def test_a_failing_git_commit_is_reported(gitvault):
    """A real pre-commit hook that refuses: git's own failure path."""
    hook = gitvault.home / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\necho 'hook says no' >&2\nexit 1\n")
    hook.chmod(0o755)
    gitvault.write("notes/new.md", "hello\n")
    before = len(gitvault.log_subjects())

    r = gitvault.run("save", "--message", "Refused")
    assert r.returncode == 1
    assert r.stderr.startswith("error: git commit failed:")
    assert "hook says no" in r.stderr
    assert len(gitvault.log_subjects()) == before


def test_help_json_describes_both_subcommands(gitvault):
    import json
    r = gitvault.run("--help-json")
    assert r.returncode == 0
    manifest = json.loads(r.stdout)
    assert [s["name"] for s in manifest["subcommands"]] == ["review", "save"]
