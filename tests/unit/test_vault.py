"""Unit tests for adulting.vault's helpers that don't touch the vault.

These pin current behaviour, quirks included, so that deduplicating the
several frontmatter parsers later can't change it unnoticed.
"""

import json
from datetime import datetime, timezone
from decimal import Decimal

from adulting import vault as V


# ---------- frontmatter ----------

def test_parse_frontmatter_reads_scalars_and_strips_quotes():
    text = '---\nthread: "[[Projects/SGB]]"\ncurrency: ZAR\n---\n\n# SGB\n'
    fm, body_start = V.parse_frontmatter(text)
    assert fm == {"thread": "[[Projects/SGB]]", "currency": "ZAR"}
    assert text.split("\n")[body_start] == ""


def test_parse_frontmatter_without_a_block_is_empty():
    assert V.parse_frontmatter("# just a heading\n") == ({}, 0)


def test_parse_frontmatter_that_never_closes_is_treated_as_no_body():
    fm, body_start = V.parse_frontmatter("---\nstatus: open\n")
    assert fm == {"status": "open"}
    assert body_start == 0


def test_parse_frontmatter_ignores_keys_with_capitals_or_digits():
    fm, _ = V.parse_frontmatter("---\nTopic: x\nclient_name: Acme\nkey2: y\n---\n")
    assert fm == {"client_name": "Acme"}


def test_parse_frontmatter_doc_reads_block_lists():
    text = ("---\ntopic: Kickoff\nthreads:\n  - \"[[Projects/SGB]]\"\n"
            "  - [[Topics/Admin]]\npeople:\n  - \"[[people/Riaz Arbi]]\"\n"
            "  - Someone Untracked\n---\n\nBody line\n")
    fm, body = V.parse_frontmatter_doc(text)
    assert fm["topic"] == "Kickoff"
    assert fm["threads"] == ["[[Projects/SGB]]", "[[Topics/Admin]]"]
    assert fm["people"] == ["[[people/Riaz Arbi]]", "Someone Untracked"]
    assert body == "\nBody line\n"


def test_parse_frontmatter_doc_empty_scalar_becomes_empty_list():
    fm, _ = V.parse_frontmatter_doc("---\nthreads:\n---\n")
    assert fm == {"threads": []}


def test_parse_frontmatter_doc_without_a_block_returns_text_as_body():
    assert V.parse_frontmatter_doc("no frontmatter") == ({}, "no frontmatter")


def test_unwiki():
    assert V.unwiki("[[Projects/SGB]]") == "Projects/SGB"
    assert V.unwiki("  [[Projects/SGB]]  ") == "Projects/SGB"
    assert V.unwiki("Projects/SGB") == "Projects/SGB"
    assert V.unwiki(None) == ""


def test_read_frontmatter_reads_scalars_by_path(tmp_path):
    f = tmp_path / "t.md"
    f.write_text("---\nstatus: 'paused'\ncurrency: \"ZAR\"\nBad Key: x\n---\n# body\nstatus: not frontmatter\n")
    assert V.read_frontmatter(f) == {"status": "paused", "currency": "ZAR"}
    f.write_text("no frontmatter\n")
    assert V.read_frontmatter(f) == {}


def test_fuzzy_score_ladder():
    """The ladder `threads list` and `people list` rank with."""
    assert V.fuzzy_score("riaz arbi", "Riaz Arbi") == 1.0
    assert V.fuzzy_score("riaz", "Riaz Arbi") == 0.9
    assert V.fuzzy_score("ra", "Riaz Arbi") == 0.85
    assert V.fuzzy_score("arbi", "Riaz Arbi") == 0.7
    assert V.fuzzy_score("bsr", "Bern Sellmeyer Rhodes") == 0.85
    assert V.fuzzy_score("bs", "Bern Sellmeyer Rhodes") == 0.6
    assert V.fuzzy_score("r", "Bern Sellmeyer Rhodes") == 0.7   # substring beats initials
    assert V.fuzzy_score("zzz", "Riaz Arbi") < 0.3


# ---------- record blocks ----------

FENCE = "```simple-time-tracker"


def test_find_block_locates_fence_and_close():
    lines = ["# x", FENCE, "{}", "```", ""]
    assert V.find_block(lines, FENCE) == (1, 3)


def test_find_block_unclosed_or_missing_is_none():
    assert V.find_block([FENCE, "{}"], FENCE) is None
    assert V.find_block(["# x"], FENCE) is None


def test_write_then_read_records_round_trips(tmp_path):
    path = tmp_path / "hours" / "Projects" / "SGB.md"
    records = [{"name": 'semi;colon, "quote" [[link]]', "id": "abcd1234", "rate": 0}]
    V.write_records(path, records, FENCE, "Projects/SGB", "ZAR", heading=" — hours")
    text = path.read_text(encoding="utf-8")
    assert text.startswith('---\nthread: "[[Projects/SGB]]"\ncurrency: ZAR\n---\n\n# SGB — hours\n')
    assert V.read_records(path, FENCE) == records


def test_write_records_without_currency_omits_it(tmp_path):
    path = tmp_path / "SGB.md"
    V.write_records(path, [], FENCE, "Projects/SGB", None)
    assert "currency" not in path.read_text(encoding="utf-8")


def test_write_records_replaces_only_the_block(tmp_path):
    path = tmp_path / "SGB.md"
    path.write_text(f"---\nthread: x\n---\n\nKeep me.\n\n{FENCE}\n{{}}\n```\n\nAfter.\n",
                    encoding="utf-8")
    V.write_records(path, [{"id": "1"}], FENCE, "Projects/SGB", "ZAR")
    text = path.read_text(encoding="utf-8")
    assert "Keep me." in text and "After." in text
    assert V.read_records(path, FENCE) == [{"id": "1"}]


def test_write_records_json_is_pretty_printed(tmp_path):
    path = tmp_path / "SGB.md"
    V.write_records(path, [{"id": "1"}], FENCE, "Projects/SGB", "ZAR")
    lines = path.read_text(encoding="utf-8").split("\n")
    i, j = V.find_block(lines, FENCE)
    assert lines[i + 1:j] == json.dumps({"entries": [{"id": "1"}]}, indent=2).split("\n")


def test_write_records_sorts_when_asked(tmp_path):
    path = tmp_path / "SGB.md"
    V.write_records(path, [{"id": "b"}, {"id": "a"}], FENCE, "P/S", "ZAR",
                    sort_key=lambda r: r["id"])
    assert [r["id"] for r in V.read_records(path, FENCE)] == ["a", "b"]


def test_read_records_of_a_missing_file_is_empty(tmp_path):
    assert V.read_records(tmp_path / "nope.md", FENCE) == []


# ---------- ids ----------

def test_new_id_is_eight_hex_and_avoids_existing():
    first = V.new_id(set())
    assert len(first) == 8 and int(first, 16) >= 0
    assert V.new_id({first}) != first


# ---------- time ----------

def test_to_iso_and_from_iso_round_trip():
    dt = datetime(2026, 9, 10, 14, 30, tzinfo=timezone.utc)
    assert V.to_iso(dt) == "2026-09-10T14:30:00.000Z"
    assert V.from_iso("2026-09-10T14:30:00.000Z") == dt


def test_when_from_flags_combines_date_and_time():
    assert V.when_from_flags("hours", "2026-09-10", "14:30") == datetime(2026, 9, 10, 14, 30)


# ---------- money and duration ----------

def test_dec_avoids_float_artefacts():
    assert V.dec(0.1) + V.dec(0.2) == Decimal("0.3")


def test_fmt_money():
    assert V.fmt_money(Decimal("2500.00"), "ZAR") == "2500 ZAR"
    assert V.fmt_money(Decimal("10.50"), "ZAR") == "10.5 ZAR"
    assert V.fmt_money(Decimal("162966.666"), "BWP") == "162966.67 BWP"
    assert V.fmt_money(Decimal("0"), "ZAR") == "0 ZAR"
    assert V.fmt_money(Decimal("100"), None) == "unbilled"


def test_fmt_duration():
    assert V.fmt_duration(0) == "0h 0m"
    assert V.fmt_duration(125) == "2h 5m"
