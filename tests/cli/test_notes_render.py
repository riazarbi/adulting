"""`notes pdf|minutes|agenda`: the markdown each renderer produces.

tests/fixtures/render/<name>.md are synthetic notes covering every rule the
three renderers have, and each `<name>.<kind>.expected.md` beside them is
the output pinned byte for byte. tests/fixtures/render/README.md says where
that output came from and which of it is known to be wrong.

Three differences from the pinned output were decided deliberately:

- no_summary_with_content_twice.minutes: the Summary block is inserted once,
  before the `# Content` heading, not also before `## Content notes`.
- no_frontmatter.*: a note with no type gets `# Details`, not `#  Details`.
- every action table has a Status column saying whether each action is
  Open or Done (decided 2026-09-22).

Old bugs these files still carry are marked DEFERRED BUG in the tests below
and listed in stories/2026-09-17-python-package-refactor.md.
"""

import shutil
from pathlib import Path

import pytest

from harness import without_program

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "render"
KINDS = ("pdf", "minutes", "agenda")
NOTES = sorted(p for p in FIXTURES.glob("*.md")
               if ".expected." not in p.name and p.name != "README.md")
HAS_PANDOC = shutil.which("pandoc") is not None and shutil.which("xelatex") is not None


@pytest.fixture
def render_vault(vault):
    (vault.home / ".adulting" / "config.yaml").write_text('owner: "Riaz Arbi"\n', encoding="utf-8")
    # The fixtures are filed under the one thread any of them names.
    folder = vault.home / "threads" / "Projects" / "SGB" / "notes"
    folder.mkdir(parents=True)
    for note in NOTES:
        shutil.copy(note, folder / note.name)
    return vault


@pytest.mark.parametrize("note", NOTES, ids=lambda p: p.stem)
@pytest.mark.parametrize("kind", KINDS)
def test_markdown_matches_the_old_renderer(render_vault, kind, note, tmp_path):
    out = tmp_path / "out"
    r = render_vault.run(kind, note.stem, "--out", str(out), cli="notes")
    written = out / note.name
    expected = (FIXTURES / f"{note.stem}.{kind}.expected.md").read_text(encoding="utf-8")
    assert written.read_text(encoding="utf-8") == expected
    assert r.stdout.splitlines()[0] == str(written)


@pytest.mark.skipif(not HAS_PANDOC, reason="needs pandoc and xelatex")
def test_a_render_writes_a_pdf_and_prints_both_paths(render_vault, tmp_path):
    out = tmp_path / "out"
    r = render_vault.run("minutes", "with_summary", "--out", str(out), cli="notes")
    assert r.returncode == 0, r.stderr
    assert r.stdout == f"{out / 'with_summary.md'}\n{out / 'with_summary.md.pdf'}\n"
    assert (out / "with_summary.md.pdf").stat().st_size > 1000


@pytest.mark.skipif(not HAS_PANDOC, reason="needs pandoc and xelatex")
def test_a_topic_with_quotes_still_breaks_the_pdf(render_vault, tmp_path):
    # DEFERRED BUG 1
    """The topic goes into the metadata unquoted, so a topic
    containing quotes and a colon is invalid YAML and pandoc refuses it. The
    markdown is still written."""
    out = tmp_path / "out"
    r = render_vault.run("pdf", "meeting_full", "--out", str(out), cli="notes")
    assert r.returncode == 1
    assert r.stdout == f"{out / 'meeting_full.md'}\n"
    assert r.stderr.startswith("notes: error: PDF render failed:")
    assert "YAML" in r.stderr
    assert (out / "meeting_full.md").exists()
    assert not (out / "meeting_full.md.pdf").exists()


@pytest.mark.skipif(not HAS_PANDOC, reason="needs pandoc")
def test_a_failed_render_leaves_no_stale_pdf(render_vault, tmp_path):
    """A PDF left from an earlier render must not pass for this one. The
    render fails for real: pandoc runs, but there is no xelatex to call."""
    out = tmp_path / "out"
    out.mkdir()
    stale = out / "with_summary.md.pdf"
    stale.write_text("not a pdf")
    render_vault.env = without_program(render_vault.env, "xelatex")
    r = render_vault.run("pdf", "with_summary", "--out", str(out), cli="notes")
    assert r.returncode == 1
    assert r.stdout == f"{out / 'with_summary.md'}\n"
    assert r.stderr.startswith("notes: error: PDF render failed:")
    assert not stale.exists()
    assert (out / "with_summary.md").exists()


def test_renders_default_to_downloads(render_vault):
    r = render_vault.run("agenda", "correspondence", cli="notes")
    downloads = Path(render_vault.env["HOME"]) / "Downloads"
    assert r.stdout.splitlines()[0] == str(downloads / "correspondence.md")
    assert (downloads / "correspondence.md").exists()


def test_render_of_a_missing_note(render_vault):
    r = render_vault.run("minutes", "nope", cli="notes")
    assert r.returncode == 1
    assert r.stderr == "notes: error: no note 'nope'\n"


@pytest.mark.skipif(not HAS_PANDOC, reason="needs pandoc and xelatex")
def test_a_relative_out_dir_is_relative_to_where_you_run_it(render_vault, tmp_path):
    """pandoc runs in a scratch directory, so a relative --out used to point
    it at a file that wasn't there, and the PDF was never written."""
    cwd = tmp_path / "work"
    cwd.mkdir()
    r = render_vault.run("minutes", "with_summary", "--out", "rel", cwd=cwd, cli="notes")
    assert r.returncode == 0, r.stderr
    assert r.stdout == f"{cwd / 'rel' / 'with_summary.md'}\n{cwd / 'rel' / 'with_summary.md.pdf'}\n"
    assert (cwd / "rel" / "with_summary.md.pdf").stat().st_size > 1000


def test_an_out_dir_that_cannot_be_made_is_an_error_not_a_traceback(render_vault, tmp_path):
    blocker = tmp_path / "a-file"
    blocker.write_text("")
    r = render_vault.run("pdf", "with_summary", "--out", str(blocker / "out"), cli="notes")
    assert (r.returncode, r.stdout) == (1, "")
    assert r.stderr == f"notes: error: cannot create {blocker / 'out'}: Not a directory\n"
