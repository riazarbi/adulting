"""Unit tests for adulting.render: the individual awk, grep and sed rules."""

from adulting import render as R

NOTE = ['---', 'topic: "a \\"quoted\\" \\\\ topic"', "type: Meeting", "people:",
        '  - "[[people/Riaz Arbi]]"', "  - Plain Name", "  -", "timestamp: 2026-09-10-14-30-00",
        '---', "", "body: not frontmatter"]


def test_records_and_joined_match_awk():
    assert R.records("a\nb\n") == ["a", "b"]
    assert R.records("a\nb") == ["a", "b"]
    assert R.records("") == []
    assert R.joined(["a", "b"]) == "a\nb\n"


def test_extract_meta_unescapes_quoted_values():
    assert R.extract_meta(NOTE, "topic") == 'a "quoted" \\ topic'
    assert R.extract_meta(NOTE, "type") == "Meeting"
    assert R.extract_meta(NOTE, "body") == ""        # body lines are not frontmatter
    assert R.extract_meta(NOTE, "missing") == ""
    assert R.extract_meta(["no frontmatter"], "topic") == ""
    assert R.extract_meta(["---", "topic: 'it''s'", "---"], "topic") == "it's"


def test_extract_people_unwraps_only_people_links():
    # `  -` with nothing after it is not an item: awk wants a space after the dash.
    assert R.extract_people(NOTE) == ["Riaz Arbi", "Plain Name"]
    assert R.extract_people(["---", "people:", "  - A", "other: x", "  - B", "---"]) == ["A"]


def test_read_owner(tmp_path):
    assert R.read_owner(tmp_path / "missing.yaml") == ""
    cfg = tmp_path / "config.yaml"
    cfg.write_text('billing:\n  x: 1\nowner: "Riaz Arbi"\nowner: Second\n')
    assert R.read_owner(cfg) == "Riaz Arbi"


def test_is_hr_and_pad_rules():
    assert R.is_hr("---") and R.is_hr(" * * * ") and R.is_hr("___")
    assert not R.is_hr("--") and not R.is_hr("-- text")
    assert R.pad_rules(["---", "title: x", "---", "text", "---", "more", "", "***", ""]) == [
        "---", "title: x", "---", "text", "", "---", "", "more", "", "***", ""]


def test_cut_and_fill_sections():
    body = ["# Action Items", "old", "-" * 11, "keep"]
    assert R.cut_sections(body, ("# Action Items",), ()) == ["# Action Items", "-" * 11, "keep"]
    assert R.cut_sections(body + ["# Timesheet", "gone"], ("# Action Items",), ("# Timesheet",)) == [
        "# Action Items", "-" * 11, "keep"]
    assert R.fill_sections(body, {"# Action Items": ["new"]}) == [
        "# Action Items", "new", "-" * 11, "keep"]
    # Ten hyphens are not a section end; eleven are.
    assert R.cut_sections(["# Action Items", "-" * 10, "still gone"], ("# Action Items",), ()) == [
        "# Action Items"]


def test_grep_sed_uniq_drops_adjacent_duplicates():
    """uniq runs after grep, so a non-matching line between two duplicates
    does not keep them apart."""
    assert R.grep_sed_uniq(["AGREED: a", "AGREED: a", "x", "AGREED: a", "no match"],
                           "AGREED:", "AGREED: ") == ["a"]
    assert R.grep_sed_uniq(["AGREED: a", "AGREED: b", "AGREED: a"],
                           "AGREED:", "AGREED: ") == ["a", "b", "a"]


def test_action_rows_dedupes_and_falls_back_to_the_owner():
    rows = R.action_rows([
        "ACTION: (Bern) Get quotes <!--due:2026-10-01-->",
        "ACTION: (Bern) Get quotes",
        "DONE: Book the venue <!--aaaa0001 entry:2026-09-01-->",
        "- [x] ABC12 (Bob) Old task",
        "not an action",
    ], owner="Riaz Arbi")
    assert rows == ["| Bern | Get quotes |", "| Riaz Arbi | Book the venue |", "| Bob | Old task |"]


def test_strip_empty_headers_keeps_h1_h2_and_headed_bodies():
    assert R.strip_empty_headers([
        "# One", "### Empty", "#### Also empty", "### Has body", "text", "## Two", "###Notaheading",
    ]) == ["# One", "### Has body", "text", "## Two", "###Notaheading"]


def test_found_block():
    assert R.found_block(["a", ""], "none") == ["", "a", "", ""]
    assert R.found_block(["", ""], "none") == ["none", ""]
    assert R.found_block([], "none") == ["none", ""]
