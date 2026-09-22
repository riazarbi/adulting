"""Unit tests for adulting.suggester: the rules that turn a raw capture into
a structured `buffer add-*` proposal. Dates are relative to a pinned today."""

from datetime import date

import pytest

from adulting import suggester as G

TODAY = date(2026, 5, 19)  # a Tuesday, as in eval/suggester/score.py


@pytest.mark.parametrize("text, due, scheduled", [
    ("do it 2026-06-01", None, "2026-06-01"),
    ("do it by 2026-06-01", "2026-06-01", None),
    ("call tomorrow", None, "2026-05-20"),
    ("call today", None, "2026-05-19"),
    ("call friday", None, "2026-05-22"),
    ("call tuesday", None, "2026-05-26"),          # never today
    ("finish before friday", "2026-05-22", None),
    ("book it for next week", None, "2026-05-25"),
    ("wrap up end of week", None, "2026-05-22"),
    ("renew by june", "2026-06-01", None),
    ("holiday in march", None, "2027-03-01"),      # a past month rolls to next year
    ("no date here", None, None),
])
def test_parse_dates(text, due, scheduled):
    got = G.parse_dates(text, TODAY)
    assert (got["due"], got["scheduled"]) == (due, scheduled)


def test_detect_priority():
    assert G.detect_priority("fix it ASAP") == "H"
    assert G.detect_priority("fix it urgent") == "H"
    # DEFERRED BUG 3: the pattern wraps `!!+` in \b word boundaries, and there
    # is no word boundary around punctuation, so `!!` never marks priority.
    assert G.detect_priority("fix it !!") is None
    assert G.detect_priority("whenever you can") == "L"
    assert G.detect_priority("fix it") is None


@pytest.mark.parametrize("text, intent", [
    ("what is the balance", "add"),
    ("create a new person for Igor", "add"),
    ("see-also the lease note", "add"),            # a REF target cannot be guessed
    ("Bern called about the fund", "add-text"),
    ("Send the report", "add-action"),
    ("Please send the report", "add-action"),
    ("aircon quote", "add-action"),                # short, no full stop
    ("The aircon technician came round and said the unit is fine.", "add-text"),
])
def test_classify_intent(text, intent):
    assert G.classify_intent(text) == intent


def test_match_person_prefers_the_surname_that_appears():
    people = ["Bern Sellmeyer", "Bern Smith", "Riaz Arbi"]
    assert G.match_person("ask Bern Smith and riaz", people) == ["Bern Smith", "Riaz Arbi"]
    assert G.match_person("ask bern about it", people) == ["Bern Sellmeyer"]
    assert G.match_person("nobody here", people) == []


def test_detect_assignee():
    assert G.detect_assignee("Riaz: send it") == ("Riaz", "send it")
    assert G.detect_assignee("send it") == (None, "send it")


def test_detect_explicit_thread_spans_the_directive():
    threads = ["Topics/Relationships", "Projects/SANA Partners"]
    text = "dinner with the family - topics/relationships"
    thread, start, end = G.detect_explicit_thread(text, threads)
    assert thread == "Topics/Relationships"
    assert text[:start] == "dinner with the family"
    assert text[end:] == ""
    thread, start, end = G.detect_explicit_thread("see [[Projects/SANA Partners]] now", threads)
    assert thread == "Projects/SANA Partners"
    assert G.detect_explicit_thread("tech/blogs post", threads) == (None, None, None)


def test_build_body_strips_dates_links_people_and_prefixes_assignee():
    text = "Forward bern the lease by 2026-06-01 ASAP"
    dates = G.parse_dates(text, TODAY)
    spans = [(m.start(), m.end()) for m in G.PRIORITY_HIGH.finditer(text)]
    assert G.build_body(text, ["Bern Sellmeyer"], dates["spans"], spans, assignee="Riaz Arbi") == \
        "(Riaz Arbi) Forward [[people/Bern Sellmeyer]] the lease"


def test_rank_threads_prefers_rare_terms():
    index = {"Processes/SGB": {"lease": 3, "fund": 8, "meeting": 20},
             "Topics/Wellness": {"squash": 2, "meeting": 1}}
    df = G.build_idf(index)
    ranked = G.rank_threads("squash meeting", index, df)
    assert ranked[0][0] == "Topics/Wellness"
    assert G.rank_threads("", index, df) == []


@pytest.fixture
def small_vault():
    home = G.vault_home()
    files = {
        "threads/Processes/SGB.md": "# SGB\nlease fund symonds\n",
        "threads/Topics/Wellness.md": "# Wellness\nsquash gym\n",
        "people/Bern Sellmeyer.md": "x",
        "logs/Processes/SGB/2026-05-01.md": "TEXT: symonds lease renewal\n",
        "notes/2026-05-02-09-00-00.md": '---\nthreads:\n  - "[[Topics/Wellness]]"\n---\nsquash ladder\n',
    }
    for rel, text in files.items():
        (home / rel).parent.mkdir(parents=True, exist_ok=True)
        (home / rel).write_text(text)
    return home


def test_loaders_and_index_read_the_vault(small_vault):
    assert G.load_threads() == ["Processes/SGB", "Topics/Wellness"]
    assert G.load_people() == ["Bern Sellmeyer"]
    index = G.build_thread_index(G.load_threads())
    assert index["Processes/SGB"]["sgb"] == 11       # name weight 10 + heading
    assert index["Processes/SGB"]["symonds"] == 2    # thread file + log
    assert index["Topics/Wellness"]["ladder"] == 1   # from the linked note


def test_suggest_end_to_end(small_vault):
    got = G.suggest("Forward Bern email on Symonds lease by 2026-06-01", today=TODAY)
    assert got == {"subcmd": "add-action", "thread": "Processes/SGB",
                   "body": "Forward [[people/Bern Sellmeyer]] email on Symonds lease",
                   "assignee": None, "due": "2026-06-01", "scheduled": None,
                   "priority": None}


def test_suggest_bails_to_unknown(small_vault):
    for text in ("what is the plan", "zzzz qqqq", "see-also the lease note"):
        assert G.suggest(text, today=TODAY)["subcmd"] == "add", text
