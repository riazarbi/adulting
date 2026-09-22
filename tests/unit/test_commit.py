"""Unit tests for adulting.commit.

The parsing helpers are pure. The git-facing functions run against a real
throwaway repo: conftest has already pointed ADULTING_HOME at tmp_path/vault.
"""

import subprocess

import pytest

from adulting import commit as C


# ---------- pure helpers ----------

def test_describe_pads_the_label_and_shows_renames():
    assert C.describe("M", "notes/a.md", None) == "  modified    notes/a.md"
    assert C.describe("R", "new.md", "old.md") == "  renamed     old.md -> new.md"
    assert C.describe("X", "odd.md", None) == "  X           odd.md"


def test_split_diff_separates_files_and_takes_the_b_side_path():
    text = ("diff --git a/one.md b/one.md\n+one\n"
            "diff --git a/old.md b/new.md\n+two\n")
    assert C.split_diff(text) == [
        ("one.md", ["diff --git a/one.md b/one.md", "+one"]),
        ("new.md", ["diff --git a/old.md b/new.md", "+two"]),
    ]


def test_split_diff_ignores_text_before_the_first_header():
    assert C.split_diff("noise\n") == []


def test_cap_block_leaves_short_blocks_alone():
    assert C.cap_block("a.md", ["1", "2"], 2) == ["1", "2"]


def test_cap_block_truncates_and_says_so():
    capped = C.cap_block("a.md", [str(i) for i in range(1500)], 3)
    assert capped[:3] == ["0", "1", "2"]
    assert capped[3] == ("[truncated: a.md — showing 3 of 1,500 lines; "
                         "re-run with --max-file-lines]")


# ---------- against a real repo ----------

@pytest.fixture
def repo():
    home = C.vault_home()
    home.mkdir(parents=True, exist_ok=True)

    def git(*args):
        subprocess.run(["git", "-C", str(home), *args], check=True,
                       capture_output=True)

    git("init", "-q", ".")
    (home / "seed.md").write_text("seed\n")
    git("add", "-A")
    git("commit", "-qm", "seed")
    return home, git


def test_vault_home_follows_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("ADULTING_HOME", str(tmp_path / "elsewhere"))
    assert C.vault_home() == tmp_path / "elsewhere"


def test_status_entries_parses_every_kind_of_change(repo):
    home, git = repo
    (home / "seed.md").write_text("changed\n")
    (home / "with space é.md").write_text("new\n")
    (home / "moved.md").write_text("m\n")
    git("add", "moved.md")
    git("commit", "-qm", "add moved")
    git("mv", "moved.md", "renamed.md")

    entries = sorted(C.status_entries())
    assert entries == [
        ("?", "with space é.md", None),
        ("M", "seed.md", None),
        ("R", "renamed.md", "moved.md"),
    ]


def test_has_head_is_true_only_once_there_is_a_commit(repo, tmp_path, monkeypatch):
    assert C.has_head() is True
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    subprocess.run(["git", "-C", str(fresh), "init", "-q"], check=True)
    monkeypatch.setenv("ADULTING_HOME", str(fresh))
    assert C.has_head() is False


def test_require_repo_accepts_the_root_and_refuses_a_plain_directory(repo, tmp_path, monkeypatch, capsys):
    C.require_repo()  # returns without exiting
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.setenv("ADULTING_HOME", str(plain))
    monkeypatch.setattr("sys.argv", ["commit"])
    with pytest.raises(SystemExit) as exc:
        C.require_repo()
    assert exc.value.code == 1
    assert capsys.readouterr().err == f"commit: error: not a git repository: {plain}\n"


def test_require_repo_refuses_a_subdirectory(repo, monkeypatch):
    home, _ = repo
    (home / "sub").mkdir()
    monkeypatch.setenv("ADULTING_HOME", str(home / "sub"))
    with pytest.raises(SystemExit) as exc:
        C.require_repo()
    assert exc.value.code == 1
