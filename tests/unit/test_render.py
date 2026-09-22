"""Unit tests for adulting.render: each rule on its own."""

import pytest

from adulting import render as R

NOTE = ['---', 'topic: "a \\"quoted\\" \\\\ topic"', "type: Meeting", "people:",
        '  - "[[people/Riaz Arbi]]"', "  - Plain Name", "  -", "timestamp: 2026-09-10-14-30-00",
        '---', "", "body: not frontmatter"]


def test_split_lines_and_join_lines_round_trip():
    assert R.split_lines("a\nb\n") == ["a", "b"]
    assert R.split_lines("a\nb") == ["a", "b"]
    assert R.split_lines("") == []
    assert R.join_lines(["a", "b"]) == "a\nb\n"


def test_extract_meta_unescapes_quoted_values():
    assert R.extract_meta(NOTE, "topic") == 'a "quoted" \\ topic'
    assert R.extract_meta(NOTE, "type") == "Meeting"
    assert R.extract_meta(NOTE, "body") == ""        # body lines are not frontmatter
    assert R.extract_meta(NOTE, "missing") == ""
    assert R.extract_meta(["no frontmatter"], "topic") == ""
    assert R.extract_meta(["---", "topic: 'it''s'", "---"], "topic") == "it's"


def test_extract_people_unwraps_only_people_links():
    # `  -` with nothing after it is not an item: an item needs a space after the dash.
    assert R.extract_people(NOTE) == ["Riaz Arbi", "Plain Name"]
    assert R.extract_people(["---", "people:", "  - A", "other: x", "  - B", "---"]) == ["A"]


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


def test_matching_lines_drops_a_repeat_of_the_line_kept_before():
    """Unmatched lines between two equal matches do not keep them apart."""
    assert R.matching_lines(["AGREED: a", "AGREED: a", "x", "AGREED: a", "no match"],
                            "AGREED:", "AGREED: ") == ["a"]
    assert R.matching_lines(["AGREED: a", "AGREED: b", "AGREED: a"],
                            "AGREED:", "AGREED: ") == ["a", "b", "a"]


def test_action_rows_mark_each_action_open_or_done():
    rows = R.action_rows([
        "ACTION: (Bern) Get quotes <!--due:2026-10-01-->",
        "ACTION: (Bern) Get quotes",
        "TASK: Circulate minutes <!--abcd1234 entry:2026-09-10-->",
        "- [ ] ABC12 (Bob) Old open task",
        "DONE: Book the venue <!--aaaa0001 entry:2026-09-01 end:2026-09-05-->",
        "- [x] Old done task",
        "DONE: (Bern) Get quotes <!--aaaa0002 entry:2026-09-01 end:2026-09-06-->",
        "not an action",
    ], owner="Riaz Arbi")
    assert rows == [
        "| Bern | Get quotes | Open |",
        "| Riaz Arbi | Circulate minutes | Open |",
        "| Bob | Old open task | Open |",
        "| Riaz Arbi | Book the venue | Done |",
        "| Riaz Arbi | Old done task | Done |",
        # The same task open and done in one note is listed both ways.
        "| Bern | Get quotes | Done |",
    ]


def test_the_action_table_has_a_status_column():
    note = "---\ntopic: t\ntype: Meeting\n---\n\n# Action Items\n\n" + "-" * 68 + "\n\n# Content\nDONE: Booked\n"
    header = "| Assignee | Task | Status |\n|----------|--------------------------------------------------|--------|\n"
    for rendered in (R.pdf_markdown(note, "Riaz Arbi"), R.minutes_markdown(note, "Riaz Arbi")):
        assert header + "| Riaz Arbi | Booked | Done |\n" in rendered
    empty = R.minutes_markdown("---\ntopic: t\ntype: Meeting\n---\n\n# Content\nbody\n", "Riaz Arbi")
    assert header + "| None | None | None |\n" in empty


def test_strip_empty_headers_keeps_h1_h2_and_headed_bodies():
    assert R.strip_empty_headers([
        "# One", "### Empty", "#### Also empty", "### Has body", "text", "## Two", "###Notaheading",
    ]) == ["# One", "### Has body", "text", "## Two", "###Notaheading"]


def test_found_block():
    assert R.found_block(["a", ""], "none") == ["", "a", "", ""]
    assert R.found_block(["", ""], "none") == ["none", ""]
    assert R.found_block([], "none") == ["none", ""]


def test_minutes_insert_the_summary_once_before_the_content_heading():
    """Only a `# Content` heading gets the Summary block. A line that merely
    contains the words, like `## Content notes`, used to get a second one."""
    note = "---\ntopic: t\ntype: Workshop\n---\n\n# Content\n\n## Content notes\nbody\n"
    rendered = R.minutes_markdown(note, owner="Riaz Arbi")
    assert rendered.count("# Summary") == 1
    assert rendered.index("# Summary") < rendered.index("\n# Content\n")


@pytest.mark.parametrize("heading", ["# Content", "# Contents", "# Content and notes"])
def test_minutes_insert_the_summary_before_a_content_heading_of_any_wording(heading):
    """Any level-1 heading that starts `# Content` gets the Summary block,
    once, however many such headings follow; a `##` heading never does."""
    note = f"---\ntopic: t\ntype: Workshop\n---\n\n## Content first\n\n{heading}\n\n# Content again\nbody\n"
    rendered = R.minutes_markdown(note, owner="Riaz Arbi")
    assert rendered.count("# Summary") == 1
    assert rendered.index("## Content first") < rendered.index("# Summary") < rendered.index(f"\n{heading}\n")


def test_a_note_with_no_type_gets_a_plain_details_heading():
    for render in (lambda t: R.pdf_markdown(t, ""), R.agenda_markdown,
                   lambda t: R.minutes_markdown(t, "")):
        rendered = render("# Content\nbody\n")
        assert "\n# Details\n" in rendered
        assert "#  Details" not in rendered


# ---------- deferred bugs, pinned as they behave today ----------

def test_a_task_with_a_priority_credits_the_owner():
    # DEFERRED BUG 2: `[#H]` stops the assignee matching, so the name stays in
    # the task text and the row is credited to the vault owner.
    rows = R.action_rows(["TASK: [#H] (Bern) Circulate minutes <!--abcd1234 entry:2026-09-10-->"],
                         owner="Riaz Arbi")
    assert rows == ["| Riaz Arbi | [#H] (Bern) Circulate minutes | Open |"]


def test_the_pdf_replaces_a_notes_own_summary_section():
    # DEFERRED BUG 10: the PDF puts its callouts after `# Summary` and drops
    # everything up to the next rule, so a minutes-style Summary loses its
    # `## Minuted Agreements` heading. 2 notes in the vault have a Summary.
    note = ("---\ntopic: t\ntype: Meeting\n---\n\n# Summary\n\n## Minuted Agreements\n\n"
            + "-" * 68 + "\n\n# Content\n")
    rendered = R.pdf_markdown(note, owner="")
    assert "# Summary" in rendered
    assert "## Minuted Agreements" not in rendered


def test_a_non_person_link_is_listed_as_an_attendee():
    # DEFERRED BUG 11: only `[[people/...]]` links are unwrapped; any other
    # link in `people:` is listed as an attendee as written.
    lines = ["---", "type: Meeting", "people:", '  - "[[Projects/Not A Person]]"', "---"]
    assert "- [[Projects/Not A Person]]" in R.header(lines, "minutes")


# ---------- each renderer, whole output, on one small note ----------

HR = "-" * 68
KICKOFF = ('---\ntopic: Kickoff\ntype: Meeting\nlocation: Cape Town\ntimestamp: 2026-09-10-14-30-00\n'
           'people:\n  - "[[people/Riaz Arbi]]"\n  - Sam\n---\n\n'
           + R.MINUTES_SUMMARY +
           "# Content\n\n## Scope\n\nAGREED: Ship in May\nRESOLVED: Hire a PM\n"
           "!: Budget is tight\nACTION: (Sam) Draft the plan\nDONE: Book the room\n\n"
           "### Empty\n\n# Timesheet\n\n09:00 start\n")
PREAMBLE = ("mainfont: Arial\nheader-includes:\n  - \\usepackage{geometry}\ngeometry:\n"
            "- top=30mm\n- left=20mm\n- heightrounded\n---\n\n\\newpage\n\n"
            "# Meeting Details\n\n**Location**: Cape Town  \n\n**Attendees**:  \n\n- Riaz Arbi\n- Sam\n")
ACTIONS = ("| Assignee | Task | Status |\n"
           "|----------|--------------------------------------------------|--------|\n"
           "| Sam | Draft the plan | Open |\n"
           "| Riaz Arbi | Book the room | Done |\n")
CONTENT = ("# Content\n\n## Scope\n\nAGREED: Ship in May\nRESOLVED: Hire a PM\n"
           "!: Budget is tight\nACTION: (Sam) Draft the plan\nDONE: Book the room\n\n")


def test_header_for_each_kind():
    lines = R.split_lines(KICKOFF)
    assert R.join_lines(R.header(lines, "pdf")) == (
        "---\ntitle: Kickoff\ndate: 2026-09-10 \ntoc: false\n" + PREAMBLE)
    assert R.join_lines(R.header(lines, "minutes")) == (
        "---\ntitle: Minutes\nsubtitle: Kickoff\ndate: 2026-09-10 \ntoc: true\ntoc-depth: 2\n" + PREAMBLE)
    assert R.join_lines(R.header(lines, "agenda")) == (
        "---\ntitle: Agenda\nsubtitle: Kickoff\ndate: 2026-09-10 \ntoc: false\n" + PREAMBLE)


def test_pdf_markdown():
    """Callouts (`!:`) fill the Summary up to its first rule. The action
    table fills Action Items; everything from `# Timesheet` goes."""
    # DEFERRED BUG 10: filling the Summary drops the note's own
    # `## Minuted Agreements` heading along with the rest of that section.
    body = R.pdf_markdown(KICKOFF, "Riaz Arbi").split(PREAMBLE, 1)[1]
    assert body == (
        f"\n# Summary\n\nBudget is tight\n\n{HR}\n\n## Resolutions\n\n{HR}\n\n"
        f"\\newpage\n## Action Items\n\n{ACTIONS}\n{HR}\n\n\\newpage\n\n"
        + CONTENT + "### Empty\n\n")


def test_minutes_markdown():
    """Agreements, resolutions and actions are gathered into the Summary; an
    action with no assignee is the owner's."""
    body = R.minutes_markdown(KICKOFF, "Riaz Arbi").split(PREAMBLE, 1)[1]
    assert body == (
        f"\n# Summary\n\n## Minuted Agreements\n\nShip in May\n\n{HR}\n\n"
        f"## Resolutions\n\nHire a PM\n\n{HR}\n\n"
        f"\\newpage\n## Action Items\n\n{ACTIONS}\n{HR}\n\n\\newpage\n\n"
        + CONTENT + "### Empty\n\n")


def test_agenda_markdown():
    """The Summary sections are emptied, the empty `### Empty` heading is
    dropped, and the note stops at `# Timesheet`."""
    body = R.agenda_markdown(KICKOFF).split(PREAMBLE, 1)[1]
    assert body == (
        f"\n# Summary\n\n## Minuted Agreements\n\n{HR}\n\n## Resolutions\n\n{HR}\n\n"
        f"\\newpage\n## Action Items\n\n{HR}\n\n\\newpage\n\n" + CONTENT + "\n")
