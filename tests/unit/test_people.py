"""Unit tests for adulting.people."""

from adulting import people as P



def test_discover_people_follows_the_vault_and_skips_non_person_files():
    d = P.people_dir()
    d.mkdir(parents=True, exist_ok=True)
    for name in ("B.md", "A.md", ".hidden.md", "notes.txt"):
        (d / name).write_text("x")
    assert [name for name, _ in P.discover_people()] == ["A", "B"]


def test_discover_people_without_a_people_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("ADULTING_HOME", str(tmp_path / "empty"))
    assert list(P.discover_people()) == []
