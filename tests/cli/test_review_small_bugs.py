"""Small bugs from the refactor review (finding A9), each written to fail
before its fix. A9.4, the `?` date padding, turned out not to be a bug: the
padding applies exactly when the date is missing."""

import json

import pytest


def test_rm_depends_removes_a_dependency_on_a_deleted_task(vault):
    """The depended-on task no longer exists, so looking it up failed and the
    dangling dependency could never be removed."""
    vault.write_thread("Projects", "SGB")
    note = vault.write_note("2026-09-10-14-30-00",
                            "TASK: needs gone <!--bbbb0001 entry:2026-09-01 depends:dead0001-->",
                            threads=["Projects/SGB"])
    r = vault.run("rm-depends", "bbbb0001", "dead", cli="tasks")
    assert (r.returncode, r.stdout, r.stderr) == (0, "bbbb0001 no longer depends on dead0001\n", "")
    assert "TASK: needs gone <!--bbbb0001 entry:2026-09-01-->  " in note.read_text(encoding="utf-8")


def test_one_unreadable_file_does_not_stop_the_ingest(vault):
    """A log that is not valid UTF-8 used to abort the whole ingest with a
    traceback. It is now reported as failed, and everything else ingests."""
    vault.write_thread("Projects", "SGB")
    bad = vault.home / "logs" / "Projects" / "SGB" / "2026-09-12.md"
    bad.parent.mkdir(parents=True)
    bad.write_bytes(b"---\nthread: x\n---\n\xff\xfe bad bytes\nACTION: unreachable\n")
    good = vault.write_note("2026-09-10-14-30-00", "ACTION: do it", threads=["Projects/SGB"])
    r = vault.run(cli="tasks")
    assert r.returncode == 1
    assert r.stdout.endswith("Ingested: 1.  Failed: 1.\n")
    assert f"  {bad}: file is not valid UTF-8; skipped\n" in r.stderr
    assert "TASK: do it <!--" in good.read_text(encoding="utf-8")
    assert vault.run("list", cli="tasks").returncode == 0


def test_search_overview_limit_zero_means_all(vault):
    vault.write_thread("Projects", "SGB")
    for day in range(1, 8):
        vault.write_note(f"2026-09-0{day}-09-00-00", "body", threads=["Projects/SGB"])
    d = json.loads(vault.run("overview", "SGB", "--limit", "0", "--json", cli="search").stdout)
    assert len(d["recent"]) == 7


@pytest.mark.parametrize("cli, path", [("buffer", ["add-action"]), ("tasks", ["add"])])
def test_depends_help_says_a_whole_uuid(vault, cli, path):
    """--depends must be exactly 8 hex characters, so calling it a prefix
    invites a shorter one that is then refused."""
    manifest = json.loads(vault.run("--help-json", cli=cli).stdout)
    [sub] = [s for s in manifest["subcommands"] if s["name"] == path[0]]
    [flag] = [f for f in sub["flags"] if f["name"] == "--depends"]
    assert flag["description"] == "A task's 8-character uuid, from `tasks list`; repeatable."
