"""Unit tests for adulting.threads. conftest points ADULTING_HOME at tmp_path/vault."""

import pytest

from adulting import threads as T


@pytest.fixture
def home():
    base = T.threads_dir()
    for rel in ("Projects/SGB.md", "Projects/Alpha.md", "Topics/SGB.md",
                "Processes/.hidden.md", "Processes/notes.txt", "People/Riaz.md"):
        (base / rel).parent.mkdir(parents=True, exist_ok=True)
        (base / rel).write_text("---\nstatus: open\n---\n")
    return base


def test_discover_threads_walks_kinds_in_order_and_skips_other_files(home):
    assert [(k, n) for k, n, _ in T.discover_threads()] == [
        ("project", "Alpha"), ("project", "SGB"), ("topic", "SGB")]


def test_resolve_thread_by_path_and_wikilink(home):
    assert T.resolve_thread("Projects/Alpha") == ("project", "Alpha", home / "Projects/Alpha.md")
    assert T.resolve_thread(" [[Topics/SGB]] ")[:2] == ("topic", "SGB")


def test_resolve_thread_unique_bare_name(home):
    assert T.resolve_thread("Alpha")[:2] == ("project", "Alpha")


def test_resolve_thread_misses_return_none(home):
    for ref in ("Nope", "Projects/Nope", "People/Riaz", "alpha"):
        assert T.resolve_thread(ref) is None, ref


def test_resolve_thread_ambiguous_bare_name_raises(home):
    with pytest.raises(ValueError, match="matches in: Projects, Topics"):
        T.resolve_thread("SGB")


def test_read_frontmatter(tmp_path):
    f = tmp_path / "t.md"
    f.write_text("---\nstatus: 'paused'\ncurrency: ZAR\n---\n# body\n")
    assert T.read_frontmatter(f) == {"status": "paused", "currency": "ZAR"}
