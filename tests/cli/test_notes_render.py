"""Tests for `notes pdf|minutes|agenda` (refactor unit 12).

tests/fixtures/render/<name>.md are synthetic notes covering every rule the
three renderers have. Each `<name>.<kind>.expected.md` beside them is the
markdown the OLD bash renderer produced for that note, captured by feeding
its picker, and the port reproduces it byte for byte, with three deliberate
exceptions made after the port:

- no_summary_with_content_twice.minutes: the Summary block is inserted once,
  before the `# Content` heading, not also before `## Content notes`.
- no_frontmatter.*: a note with no type gets `# Details`, not `#  Details`.
- every action table has a Status column saying whether each action is
  Open or Done (decided 2026-09-22).

Old bugs these files still carry are marked DEFERRED BUG in the tests below
and listed in stories/2026-09-17-python-package-refactor.md.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from harness import command_path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "render"
KINDS = ("pdf", "minutes", "agenda")
NOTES = sorted(p for p in FIXTURES.glob("*.md") if ".expected." not in p.name)
HAS_PANDOC = shutil.which("pandoc") is not None and shutil.which("xelatex") is not None


def notes(vault, *argv):
    return subprocess.run([command_path("notes", vault.env), *argv], capture_output=True,
                          text=True, env=vault.env, input="")


@pytest.fixture
def v(vault):
    (vault.home / ".adulting" / "config.yaml").write_text('owner: "Riaz Arbi"\n', encoding="utf-8")
    for note in NOTES:
        shutil.copy(note, vault.home / "notes" / note.name)
    return vault


@pytest.mark.parametrize("note", NOTES, ids=lambda p: p.stem)
@pytest.mark.parametrize("kind", KINDS)
def test_markdown_matches_the_old_renderer(v, kind, note, tmp_path):
    out = tmp_path / "out"
    r = notes(v, kind, note.stem, "--out", str(out))
    written = out / note.name
    expected = (FIXTURES / f"{note.stem}.{kind}.expected.md").read_text(encoding="utf-8")
    assert written.read_text(encoding="utf-8") == expected
    assert r.stdout.splitlines()[0] == str(written)


@pytest.mark.skipif(not HAS_PANDOC, reason="needs pandoc and xelatex")
def test_a_render_writes_a_pdf_and_prints_both_paths(v, tmp_path):
    out = tmp_path / "out"
    r = notes(v, "minutes", "with_summary", "--out", str(out))
    assert r.returncode == 0, r.stderr
    assert r.stdout == f"{out / 'with_summary.md'}\n{out / 'with_summary.md.pdf'}\n"
    assert (out / "with_summary.md.pdf").stat().st_size > 1000


@pytest.mark.skipif(not HAS_PANDOC, reason="needs pandoc and xelatex")
def test_a_topic_with_quotes_still_breaks_the_pdf(v, tmp_path):
    """Old bug, pinned: the topic goes into the metadata unquoted, so a topic
    containing quotes and a colon is invalid YAML and pandoc refuses it. The
    markdown is still written."""
    out = tmp_path / "out"
    r = notes(v, "pdf", "meeting_full", "--out", str(out))
    assert r.returncode == 1
    assert r.stdout == f"{out / 'meeting_full.md'}\n"
    assert r.stderr.startswith("notes: PDF render failed:")
    assert "YAML" in r.stderr
    assert (out / "meeting_full.md").exists()
    assert not (out / "meeting_full.md.pdf").exists()


@pytest.mark.skipif(not HAS_PANDOC, reason="needs pandoc and xelatex")
def test_a_stale_pdf_is_removed_before_rendering(v, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    stale = out / "meeting_full.md.pdf"
    stale.write_text("not a pdf")
    notes(v, "pdf", "meeting_full", "--out", str(out))
    assert not stale.exists()


def test_renders_default_to_downloads(v):
    r = notes(v, "agenda", "correspondence")
    downloads = Path(v.env["HOME"]) / "Downloads"
    assert r.stdout.splitlines()[0] == str(downloads / "correspondence.md")
    assert (downloads / "correspondence.md").exists()


def test_render_of_a_missing_note(v):
    r = notes(v, "minutes", "nope")
    assert r.returncode == 1
    assert r.stderr == f"notes: no note 'nope' in {v.home / 'notes'}\n"


def test_help_json_lists_the_renderers(vault):
    manifest = json.loads(notes(vault, "--help-json").stdout)
    names = [s["name"] for s in manifest["subcommands"]]
    assert names[-3:] == ["pdf", "minutes", "agenda"]
    flags = {f["name"] for s in manifest["subcommands"] if s["name"] == "pdf" for f in s["flags"]}
    assert flags == {"--out"}


@pytest.mark.skipif(not HAS_PANDOC, reason="needs pandoc and xelatex")
def test_a_relative_out_dir_is_relative_to_where_you_run_it(v, tmp_path):
    """pandoc runs in a scratch directory, so a relative --out used to point
    it at a file that wasn't there, and the PDF was never written."""
    cwd = tmp_path / "work"
    cwd.mkdir()
    r = subprocess.run([command_path("notes", v.env), "minutes", "with_summary", "--out", "rel"],
                       capture_output=True, text=True, env=v.env, cwd=cwd)
    assert r.returncode == 0, r.stderr
    assert r.stdout == f"{cwd / 'rel' / 'with_summary.md'}\n{cwd / 'rel' / 'with_summary.md.pdf'}\n"
    assert (cwd / "rel" / "with_summary.md.pdf").stat().st_size > 1000
