"""Functional tests for the `commit` CLI.

Each test builds a throwaway git repo in a tmp dir and points
ADULTING_HOME at it. The identity comes from GIT_AUTHOR_*/GIT_COMMITTER_*
in the environment (set by tests/harness.py), as the agent container sets
it, rather than from any gitconfig on the machine running the suite.
"""

import re
import subprocess

import pytest


def git(vault, *argv):
    r = subprocess.run(["git", "-C", str(vault.home), *argv],
                       capture_output=True, text=True, env=vault.env)
    assert r.returncode == 0, f"git {argv}: {r.stderr}"
    return r.stdout


def without_blob_hashes(text):
    """git's `index 0000000..5626abf` lines, blanked. The hashes are git's
    own and encode no requirement of ours; the rest of the diff is ours to
    pin."""
    return re.sub(r'^index \S+$', 'index ...', text, flags=re.M)


def log_subjects(vault):
    return git(vault, "log", "--format=%s").strip().split("\n")


@pytest.fixture
def gitvault(vault):
    """The test vault as a git repo with one commit."""
    git(vault, "init", "-q", ".")
    vault.write("notes/seed.md", "line1\nline2\nline3\n")
    git(vault, "add", "-A")
    git(vault, "commit", "-qm", "seed")
    return vault


# ---------- save cannot rewrite history ----------

def test_flag_shaped_message_appends_rather_than_rewrites(gitvault):
    """A --message of '--amend' must be committed as a literal subject and
    must append a commit, not rewrite the previous one."""
    before_head = git(gitvault, "rev-parse", "HEAD").strip()
    before_count = len(log_subjects(gitvault))
    gitvault.write("notes/new.md", "hello\n")

    r = gitvault.run("save", "--message=--amend", cli="commit")
    assert r.returncode == 0, r.stderr
    assert r.stderr == ""

    assert len(log_subjects(gitvault)) == before_count + 1
    assert git(gitvault, "log", "-1", "--format=%s").strip() == "--amend"
    # The new commit sits on top of the old HEAD; nothing was rewritten.
    assert git(gitvault, "rev-parse", "HEAD^").strip() == before_head


def test_flag_shaped_message_in_separated_form_is_refused(gitvault):
    """`--message --amend` (space-separated) never reaches git: argparse
    refuses it, so nothing is staged or committed."""
    before_count = len(log_subjects(gitvault))
    gitvault.write("notes/new.md", "hello\n")

    r = gitvault.run("save", "--message", "--amend", cli="commit")
    assert (r.returncode, r.stdout) == (2, "")
    assert r.stderr == ("usage: commit save [-h] [--help-json] --message MESSAGE [--body BODY]\n"
                        "                   [--dry-run]\n"
                        "commit save: error: argument --message: expected one argument\n")
    assert len(log_subjects(gitvault)) == before_count
    assert git(gitvault, "diff", "--cached", "--name-only") == ""


# ---------- review ----------

def test_review_is_read_only_and_lists_both_kinds_of_change(gitvault):
    gitvault.write("notes/seed.md", "line1\nCHANGED\nline3\n")
    gitvault.write("notes/brand-new.md", "fresh content\n")

    r = gitvault.run("review", cli="commit")
    assert r.returncode == 0, r.stderr
    assert r.stderr == ""

    assert "notes/seed.md" in r.stdout
    assert "notes/brand-new.md" in r.stdout
    assert "+CHANGED" in r.stdout          # tracked edit shown as a diff
    assert "+fresh content" in r.stdout    # untracked content shown too

    # Read-only: the index is exactly as we left it.
    assert git(gitvault, "diff", "--cached", "--name-only") == ""


def test_review_lists_files_inside_a_new_directory_individually(gitvault):
    """Without -uall git collapses a new directory to `assets/`, which
    would under-report what `save` is about to commit."""
    gitvault.write("assets/deep/one.md", "one\n")
    gitvault.write("assets/deep/two.md", "two\n")

    r = gitvault.run("review", cli="commit")
    assert (r.returncode, r.stderr) == (0, "")
    assert without_blob_hashes(r.stdout) == (
        "Changed paths:\n  untracked   assets/deep/one.md\n  untracked   assets/deep/two.md\n\n"
        "New files:\n\n"
        "diff --git a/assets/deep/one.md b/assets/deep/one.md\nnew file mode 100644\n"
        "index ...\n--- /dev/null\n+++ b/assets/deep/one.md\n@@ -0,0 +1 @@\n+one\n"
        "diff --git a/assets/deep/two.md b/assets/deep/two.md\nnew file mode 100644\n"
        "index ...\n--- /dev/null\n+++ b/assets/deep/two.md\n@@ -0,0 +1 @@\n+two\n")


def test_review_truncation_is_configurable_and_announced(gitvault):
    gitvault.write("notes/big.md", "\n".join(str(i) for i in range(400)) + "\n")

    full = gitvault.run("review", cli="commit")
    capped = gitvault.run("review", "--max-file-lines", "5", cli="commit")
    assert capped.returncode == 0, capped.stderr
    assert len(capped.stdout.split("\n")) < len(full.stdout.split("\n"))
    assert "--max-file-lines" in capped.stdout      # truncation announced in-band
    assert "truncated" in capped.stdout

    globally = gitvault.run("review", "--max-lines", "10", cli="commit")
    assert globally.returncode == 0, globally.stderr
    assert "--max-lines" in globally.stdout
    assert len(globally.stdout.strip().split("\n")) <= 12


def test_review_on_clean_tree(gitvault):
    r = gitvault.run("review", cli="commit")
    assert (r.returncode, r.stdout, r.stderr) == (0, "no uncommitted changes; working tree clean\n", "")


# ---------- message handling ----------

def test_multiline_body_round_trips(gitvault):
    gitvault.write("notes/new.md", "hello\n")
    body = "First paragraph.\n\nSecond paragraph,\nwith a second line."

    r = gitvault.run("save", "--message", "Subject line", "--body", body, cli="commit")
    assert r.returncode == 0, r.stderr
    assert r.stderr == ""

    full = git(gitvault, "log", "-1", "--format=%B")
    assert full.startswith("Subject line\n\nFirst paragraph.\n\n"
                           "Second paragraph,\nwith a second line.")


def test_multiline_message_is_rejected(gitvault):
    gitvault.write("notes/new.md", "hello\n")
    before_count = len(log_subjects(gitvault))

    r = gitvault.run("save", "--message", "subject\nsneaky second line", cli="commit")
    assert r.returncode != 0
    assert "--body" in r.stderr
    assert len(log_subjects(gitvault)) == before_count
    assert git(gitvault, "diff", "--cached", "--name-only") == ""


# ---------- save behaviour ----------

def test_save_commits_every_change(gitvault):
    gitvault.write("notes/seed.md", "edited\n")
    gitvault.write("assets/deep/new.md", "brand new\n")

    r = gitvault.run("save", "--message", "Record the day's work", cli="commit")
    assert r.returncode == 0, r.stderr
    assert r.stderr == ""

    committed = git(gitvault, "show", "--name-only", "--format=", "HEAD").split()
    assert "notes/seed.md" in committed
    assert "assets/deep/new.md" in committed
    assert git(gitvault, "status", "--porcelain") == ""


def test_dry_run_changes_nothing(gitvault):
    gitvault.write("notes/new.md", "hello\n")
    before_count = len(log_subjects(gitvault))

    r = gitvault.run("save", "--message", "Would commit", "--dry-run", cli="commit")
    assert r.returncode == 0, r.stderr
    assert r.stderr == ""
    assert "notes/new.md" in r.stdout
    assert "Would commit" in r.stdout

    assert len(log_subjects(gitvault)) == before_count
    assert git(gitvault, "diff", "--cached", "--name-only") == ""


def test_clean_tree_is_a_success(gitvault):
    before = log_subjects(gitvault)
    r = gitvault.run("save", "--message", "nothing doing", cli="commit")
    assert (r.returncode, r.stdout, r.stderr) == (0, "nothing to commit; working tree clean\n", "")
    assert log_subjects(gitvault) == before


def test_non_repo_home_fails_cleanly(gitvault, tmp_path):
    gitvault.env["ADULTING_HOME"] = str(tmp_path / "not-a-repo")
    (tmp_path / "not-a-repo").mkdir()

    r = gitvault.run("review", cli="commit")
    assert r.returncode != 0
    assert "not a git repository" in r.stderr
    assert r.stdout == ""


# ---------- the vault repo itself: where it may live, and what it refuses ----------

def test_home_that_is_a_subdirectory_of_a_repo_is_refused(gitvault):
    """`git add -A` from a subdirectory would sweep in files outside the vault."""
    gitvault.env["ADULTING_HOME"] = str(gitvault.home / "notes")
    gitvault.write("outside.md", "not vault content\n")
    r = gitvault.run("save", "--message", "should not happen", cli="commit")
    assert r.returncode == 1
    assert "is not the root of its git repository" in r.stderr
    assert git(gitvault, "diff", "--cached", "--name-only") == ""


def test_empty_message_is_rejected(gitvault):
    gitvault.write("notes/new.md", "hello\n")
    r = gitvault.run("save", "--message", "   ", cli="commit")
    assert r.returncode == 1
    assert r.stderr == "commit: error: --message must not be empty\n"


def test_review_listing_format(gitvault):
    gitvault.write("notes/seed.md", "edited\n")
    gitvault.write("notes/new.md", "hello\n")
    (gitvault.home / "notes" / "gone.md").write_text("x\n")
    git(gitvault, "add", "notes/gone.md")
    git(gitvault, "commit", "-qm", "add gone")
    (gitvault.home / "notes" / "gone.md").unlink()

    r = gitvault.run("review", cli="commit")
    lines = r.stdout.split("\n")
    assert lines[0] == "Changed paths:"
    assert "  modified    notes/seed.md" in lines
    assert "  deleted     notes/gone.md" in lines
    assert "  untracked   notes/new.md" in lines
    assert "Changes to tracked files:" in lines
    assert "New files:" in lines


def test_review_shows_a_staged_rename_as_old_arrow_new(gitvault):
    git(gitvault, "mv", "notes/seed.md", "notes/renamed.md")
    r = gitvault.run("review", cli="commit")
    assert (r.returncode, r.stderr) == (0, "")
    assert without_blob_hashes(r.stdout) == (
        "Changed paths:\n  renamed     notes/seed.md -> notes/renamed.md\n\n"
        "Changes to tracked files:\n\n"
        "diff --git a/notes/seed.md b/notes/renamed.md\nsimilarity index 100%\n"
        "rename from notes/seed.md\nrename to notes/renamed.md\n")


def test_review_shows_an_empty_new_file_as_a_bare_diff_header(gitvault):
    """git still emits a header for an empty file, so the tool's
    `[new empty file: ...]` fallback is not reached with current git."""
    gitvault.write("notes/empty.md", "")
    r = gitvault.run("review", cli="commit")
    assert (r.returncode, r.stderr) == (0, "")
    assert without_blob_hashes(r.stdout) == (
        "Changed paths:\n  untracked   notes/empty.md\n\nNew files:\n\n"
        "diff --git a/notes/empty.md b/notes/empty.md\nnew file mode 100644\nindex ...\n")


def test_review_before_the_first_commit_lists_new_files(vault):
    git(vault, "init", "-q", ".")
    vault.write("notes/first.md", "first\n")
    r = vault.run("review", cli="commit")
    assert (r.returncode, r.stderr) == (0, "")
    assert without_blob_hashes(r.stdout) == (
        "Changed paths:\n  untracked   notes/first.md\n\nNew files:\n\n"
        "diff --git a/notes/first.md b/notes/first.md\nnew file mode 100644\n"
        "index ...\n--- /dev/null\n+++ b/notes/first.md\n@@ -0,0 +1 @@\n+first\n")


def test_filenames_with_spaces_and_non_ascii_are_readable(gitvault):
    gitvault.write("people/José Núñez.md", "hola\n")
    r = gitvault.run("review", cli="commit")
    assert "  untracked   people/José Núñez.md" in r.stdout
    s = gitvault.run("save", "--message", "Add José", cli="commit")
    assert s.returncode == 0, s.stderr
    assert "people/José Núñez.md" in git(
        gitvault, "-c", "core.quotepath=false", "show", "--name-only", "--format=", "HEAD")


def test_dry_run_output_format(gitvault):
    gitvault.write("notes/new.md", "hello\n")
    r = gitvault.run("save", "--message", "Subject", "--body", "Line one\nLine two",
                     "--dry-run", cli="commit")
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
    r = gitvault.run("save", "--message", "Two changes", cli="commit")
    sha = git(gitvault, "rev-parse", "--short", "HEAD").strip()
    assert r.stdout == (f"committed {sha}: Two changes\n"
                        "2 path(s) staged and committed.\n")


def test_a_failing_git_commit_is_reported(gitvault):
    """A real pre-commit hook that refuses: git's own failure path."""
    hook = gitvault.home / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\necho 'hook says no' >&2\nexit 1\n")
    hook.chmod(0o755)
    gitvault.write("notes/new.md", "hello\n")
    before = len(log_subjects(gitvault))

    r = gitvault.run("save", "--message", "Refused", cli="commit")
    assert r.returncode == 1
    assert r.stderr.startswith("commit: error: git commit failed:")
    assert "hook says no" in r.stderr
    assert len(log_subjects(gitvault)) == before


def test_a_long_file_is_truncated_at_a_hundred_and_fifty_lines_by_default(gitvault):
    gitvault.write("notes/long.md", "".join(f"line {i}\n" for i in range(200)))
    out = gitvault.run("review", cli="commit").stdout
    # 200 body lines plus the diff's own header lines.
    assert "[truncated: notes/long.md — showing 150 of 206 lines; re-run with --max-file-lines]" in out
    assert "+line 143\n" in out and "+line 144\n" not in out


def test_a_long_tracked_diff_is_truncated_too(gitvault):
    """Only untracked files used to reach the cap in the tests, so the
    tracked branch went unexercised."""
    gitvault.write("notes/seed.md", "".join(f"line {i}\n" for i in range(200)))
    out = gitvault.run("review", cli="commit").stdout
    assert "Changes to tracked files:" in out
    assert "[truncated: notes/seed.md — showing 150 of " in out


def test_the_whole_review_is_capped_at_three_thousand_lines_by_default(gitvault):
    for n in range(40):
        gitvault.write(f"notes/file{n:02d}.md", "".join(f"line {i}\n" for i in range(100)))
    out = gitvault.run("review", cli="commit").stdout
    lines = out.splitlines()
    # The cap counts the lines it emits and stops; the line saying so is
    # extra. `<= 3000` would have passed for any output at all, including an
    # empty one.
    assert len(lines) == 2908
    assert lines[-1].startswith("[truncated: output hit the 3,000-line cap;")
