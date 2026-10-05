"""Tests for dev/migrate-layout, which moves a vault into thread folders.

It runs once against the real vault, so it is tested here against a small
vault holding every case the real one does: a multi-thread note, a note's
image, path-qualified links in logs and the buffer, and files it must leave
alone.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "dev" / "migrate-layout"


def migrate(vault: Path, *flags: str) -> subprocess.CompletedProcess:
    # ADULTING_HOME is what the script takes for the production vault, and
    # the suite points it at this very vault; aim it elsewhere.
    env = {**os.environ, "ADULTING_HOME": str(vault.parent / "elsewhere")}
    return subprocess.run([sys.executable, str(SCRIPT), str(vault), *flags],
                          capture_output=True, text=True, env=env)


def test_the_production_vault_is_refused_without_the_flag(tmp_path):
    v = small_vault(tmp_path)
    env = {**os.environ, "ADULTING_HOME": str(v)}
    r = subprocess.run([sys.executable, str(SCRIPT), str(v)],
                       capture_output=True, text=True, env=env)
    assert r.returncode != 0 and "--production" in r.stderr
    assert (v / "hours/Projects/A.md").exists()


def write(vault: Path, rel: str, text: str = "") -> Path:
    p = vault / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


NOTE = """---
topic: Kickoff
type: Report
threads:
  - "[[Projects/B]]"
  - "[[Projects/A]]"
timestamp: 2026-05-15-08-26-53
---

![diagram](2026-05-15-08-26-53-diagram.png)
"""

LOG = """---
thread: "[[Projects/A]]"
date: 2026-05-15
type: Log
---

REF: [[hours/Projects/A]] 1h 0m Work (abcd1234)
REF: [[notes/2026-05-15-08-26-53|Kickoff]] Kickoff
REF: [[payments/Projects/A]] 10 ZAR received (beef0001)
REF: [[logs/Projects/A/2026-05-14]] yesterday
REF: [[Projects/A]] the thread itself
"""


def small_vault(tmp_path: Path) -> Path:
    v = tmp_path / "vault"
    write(v, "threads/Projects/A.md", "---\nstatus: open\n---\n")
    write(v, "threads/Projects/B.md", "---\nstatus: open\n---\n")
    write(v, "notes/2026-05-15-08-26-53.md", NOTE)
    write(v, "notes/2026-05-15-08-26-53-diagram.png", "png")
    write(v, "notes/2026-05-16-00-00-00.md", "---\ntopic: Orphan\n---\n")
    write(v, "logs/Projects/A/2026-05-15.md", LOG)
    write(v, "logs/Projects/A/2026-05-14.md", "---\nthread: \"[[Projects/A]]\"\n---\n")
    write(v, "hours/Projects/A.md", "---\nthread: \"[[Projects/A]]\"\n---\n")
    write(v, "payments/Projects/A.md", "---\nthread: \"[[Projects/A]]\"\n---\n")
    write(v, "buffer.md", "- [[Projects/A]] REF: [[hours/Projects/A]] 1h <!--2026-05-15T10:00:00-->\n")
    write(v, "people/Riaz.md", "see [[notes/2026-05-15-08-26-53]]\n")
    return v


def test_files_move_into_their_thread_folders(tmp_path):
    v = small_vault(tmp_path)
    r = migrate(v, "--map", str(tmp_path / "map.json"))
    a = v / "threads" / "Projects" / "A"
    b = v / "threads" / "Projects" / "B"
    # Filed under the FIRST thread, with its image beside it.
    assert (b / "notes" / "2026-05-15-08-26-53.md").read_text() == NOTE
    assert (b / "notes" / "2026-05-15-08-26-53-diagram.png").read_text() == "png"
    assert (a / "logs" / "2026-05-15.md").exists()
    assert (a / "logs" / "2026-05-14.md").exists()
    assert (a / "hours.md").exists() and (a / "payments.md").exists()
    for gone in ("logs", "hours", "payments"):
        assert not (v / gone).exists(), gone
    moves = json.loads((tmp_path / "map.json").read_text())
    assert moves["hours/Projects/A.md"] == "threads/Projects/A/hours.md"
    # The orphan note cannot be filed: reported, left, and the run fails.
    assert (v / "notes" / "2026-05-16-00-00-00.md").exists()
    assert "no threads" in r.stderr and r.returncode == 1


def test_path_qualified_links_are_rewritten_everywhere(tmp_path):
    v = small_vault(tmp_path)
    migrate(v)
    log = (v / "threads/Projects/A/logs/2026-05-15.md").read_text()
    assert "REF: [[Projects/A/hours]] 1h 0m Work (abcd1234)" in log
    assert "REF: [[2026-05-15-08-26-53|Kickoff]] Kickoff" in log
    assert "REF: [[Projects/A/payments]] 10 ZAR" in log
    assert "REF: [[Projects/A/logs/2026-05-14]] yesterday" in log
    assert "REF: [[Projects/A]] the thread itself" in log
    assert "[[Projects/A/hours]]" in (v / "buffer.md").read_text()
    assert "[[2026-05-15-08-26-53]]" in (v / "people/Riaz.md").read_text()


def test_a_second_run_changes_nothing(tmp_path):
    v = small_vault(tmp_path)
    migrate(v)
    before = {p: p.read_bytes() for p in v.rglob("*") if p.is_file()}
    r = migrate(v)
    assert {p: p.read_bytes() for p in v.rglob("*") if p.is_file()} == before
    assert "rewrote 0 link(s)" in r.stdout


def test_dry_run_changes_nothing(tmp_path):
    v = small_vault(tmp_path)
    before = {p: p.read_bytes() for p in v.rglob("*") if p.is_file()}
    r = migrate(v, "--dry-run")
    assert {p: p.read_bytes() for p in v.rglob("*") if p.is_file()} == before
    assert "would move 2 file(s) from notes/" in r.stdout


def test_an_existing_target_is_never_overwritten(tmp_path):
    v = small_vault(tmp_path)
    write(v, "threads/Projects/A/hours.md", "already here")
    r = migrate(v)
    assert (v / "threads/Projects/A/hours.md").read_text() == "already here"
    assert (v / "hours/Projects/A.md").exists()
    assert "already exists" in r.stderr and r.returncode == 1


def test_a_dirty_git_vault_is_refused(tmp_path):
    v = small_vault(tmp_path)
    subprocess.run(["git", "init", "-q", str(v)], check=True)
    r = migrate(v)
    assert r.returncode != 0 and "uncommitted changes" in r.stderr
    assert (v / "hours/Projects/A.md").exists()


def test_a_one_line_threads_list_is_read_as_the_commands_read_it(tmp_path):
    v = small_vault(tmp_path)
    write(v, "notes/2026-05-17-00-00-00.md",
          '---\ntopic: Flow\ntype: Report\n'
          'threads: ["[[Projects/B]]", "[[Projects/A]]"]\n---\n')
    migrate(v)
    assert (v / "threads/Projects/B/notes/2026-05-17-00-00-00.md").exists()
    assert not (v / "notes/2026-05-17-00-00-00.md").exists()


def tree(vault: Path) -> dict:
    """Every file and folder, with each file's bytes: the vault exactly."""
    return {str(p.relative_to(vault)): (p.read_bytes() if p.is_file() else None)
            for p in sorted(vault.rglob("*"))}


@pytest.mark.parametrize("readonly", [
    "logs/Projects/A/2026-05-15.md",    # a file whose links need rewriting
    "people/Riaz.md",                   # one that does not move, but is rewritten
    "notes",                            # a folder files must leave
])
def test_nothing_changes_unless_everything_can(tmp_path, readonly):
    v = small_vault(tmp_path)
    target = v / readonly
    mode = target.stat().st_mode
    target.chmod(0o555 if target.is_dir() else 0o444)
    before = tree(v)
    try:
        r = migrate(v)
        after = tree(v)
    finally:
        target.chmod(mode)
    assert r.returncode == 1
    assert "not writable" in r.stderr and "nothing changed" in r.stderr
    assert "Traceback" not in r.stderr
    assert after == before
