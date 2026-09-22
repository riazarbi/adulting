"""Thread names are checked one way everywhere (review finding A5).

Every command resolves a thread through vault.resolve_thread, which matches
names exactly against the files in threads/, rather than asking the
filesystem whether a path exists. macOS ignores case, so the old way let
`Projects/sgb` through there and wrote a wikilink that breaks on Linux.
"""

import pytest


@pytest.fixture
def sgb_vault(vault):
    vault.write_thread("Projects", "SGB")
    return vault


def test_buffer_refuses_a_wrongly_cased_thread(sgb_vault):
    r = sgb_vault.run("add-text", "Projects/sgb", "wrong case", cli="buffer")
    assert r.returncode == 1
    assert r.stderr == "buffer: error: thread 'Projects/sgb' does not resolve to a thread file\n"
    assert not (sgb_vault.home / "buffer.md").exists()


def test_buffer_accepts_any_form_and_stores_the_canonical_name(sgb_vault):
    for form in ("SGB", "[[Projects/SGB]]", "Projects/SGB"):
        r = sgb_vault.run("add-text", form, f"via {form}", cli="buffer")
        assert r.returncode == 0, r.stderr
    lines = sgb_vault.read("buffer.md").splitlines()
    assert [line.split(" TEXT:")[0] for line in lines] == ["- [[Projects/SGB]]"] * 3


def test_tend_flags_a_hand_written_wrongly_cased_thread(sgb_vault):
    (sgb_vault.home / "buffer.md").write_text(
        "- [[Projects/sgb]] TEXT: hand written <!--2026-09-10T09:00:00-->\n", encoding="utf-8")
    r = sgb_vault.run("tend", cli="buffer")
    assert r.returncode == 1
    assert "buffer.md:1: thread 'Projects/sgb' does not resolve" in r.stderr


def test_tasks_will_not_ingest_under_a_wrongly_cased_thread(sgb_vault):
    note = sgb_vault.write_note("2026-09-10-14-30-00", "ACTION: do it", threads=["Projects/sgb"])
    r = sgb_vault.run(cli="tasks")
    assert r.returncode == 1
    assert f"{note}:9: thread 'Projects/sgb' does not resolve" in r.stderr
    assert "ACTION: do it" in note.read_text(encoding="utf-8")


def test_threads_show_does_not_find_a_wrongly_cased_thread(sgb_vault):
    r = sgb_vault.run("show", "Projects/sgb", cli="threads")
    assert (r.returncode, r.stderr) == (1, "threads: error: thread 'Projects/sgb' does not resolve to a thread file\n")


def test_threads_reports_an_ambiguous_bare_name_like_every_other_command(sgb_vault):
    sgb_vault.write_thread("Topics", "SGB")
    r = sgb_vault.run("show", "SGB", cli="threads")
    assert r.returncode == 1
    assert r.stderr == "threads: error: ambiguous thread 'SGB'; matches: Projects/SGB, Topics/SGB\n"
