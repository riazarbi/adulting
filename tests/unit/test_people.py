"""Unit tests for adulting.people."""

from adulting import people as P


def test_fuzzy_score_ladder():
    assert P.fuzzy_score("riaz arbi", "Riaz Arbi") == 1.0
    assert P.fuzzy_score("riaz", "Riaz Arbi") == 0.9
    assert P.fuzzy_score("ra", "Riaz Arbi") == 0.85
    assert P.fuzzy_score("arbi", "Riaz Arbi") == 0.7
    assert P.fuzzy_score("r", "Bern Sellmeyer Rhodes") == 0.7   # substring beats initials
    assert P.fuzzy_score("bsr", "Bern Sellmeyer Rhodes") == 0.85
    assert P.fuzzy_score("bs", "Bern Sellmeyer Rhodes") == 0.6
    assert P.fuzzy_score("zzz", "Riaz Arbi") < 0.3


def test_resolve_person_strips_the_wikilink_prefix():
    assert P._resolve_person("  people/Riaz Arbi ") == "Riaz Arbi"
    assert P._resolve_person("Riaz Arbi") == "Riaz Arbi"


def test_read_frontmatter(tmp_path):
    f = tmp_path / "p.md"
    f.write_text("---\nstatus: 'open'\ncategory: \"personal\"\nBad Key: x\n---\n\nstatus: body\n")
    assert P.read_frontmatter(f) == {"status": "open", "category": "personal"}
    f.write_text("no frontmatter\n")
    assert P.read_frontmatter(f) == {}


def test_discover_people_follows_the_vault_and_skips_non_person_files():
    d = P.people_dir()
    d.mkdir(parents=True, exist_ok=True)
    for name in ("B.md", "A.md", ".hidden.md", "notes.txt"):
        (d / name).write_text("x")
    assert [name for name, _ in P.discover_people()] == ["A", "B"]


def test_discover_people_without_a_people_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("ADULTING_HOME", str(tmp_path / "empty"))
    assert list(P.discover_people()) == []
