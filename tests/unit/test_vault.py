"""Unit tests for adulting.vault's helpers that don't touch the vault.

These pin current behaviour, quirks included, so that deduplicating the
several frontmatter parsers later can't change it unnoticed.
"""

import json
import re
from datetime import datetime, timezone
from decimal import Decimal

import pytest

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

def test_new_id_is_eight_lowercase_hex_characters():
    for _ in range(50):
        assert re.fullmatch(r"[0-9a-f]{8}", V.new_id(set()))


def test_note_threads_reads_either_key_and_unwraps_wikilinks():
    note = '---\ntopic: x\nthreads:\n  - "[[Projects/SGB]]"\n  - Topics/Plain\ntype: Log\n---\nthreads: body\n'
    assert V.note_threads(V.parse_frontmatter_doc(note)[0]) == ["Projects/SGB", "Topics/Plain"]
    log = "---\nthread: '[[Topics/zeta]]'\n---\n"
    assert V.note_threads(V.parse_frontmatter_doc(log)[0]) == ["Topics/zeta"]
    assert V.note_threads({}) == []
    assert V.note_threads({"threads": ["", "  ", "Topics/Plain"]}) == ["Topics/Plain"]


def test_read_config_reads_the_owner_without_quotes():
    assert V.read_config() == {}
    cfg = V.vault_home() / ".adulting" / "config.yaml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text('billing:\n  x: 1\nowner: "Riaz Arbi"\n')
    assert V.read_config().get("owner") == "Riaz Arbi"


# ---------- actions ----------

def test_parse_action_attrs_keeps_good_values_and_reports_bad_ones():
    attrs, errors = V.parse_action_attrs(
        ["due:2026-09-20", "priority:H", "depends:aaaaaaaa", "depends:bbbbbbbb",
         "scheduled:2026-09-15", ""])
    assert attrs == {"depends": ["aaaaaaaa", "bbbbbbbb"], "due": "2026-09-20",
                     "priority": "H", "scheduled": "2026-09-15"}
    assert errors == []
    _, errors = V.parse_action_attrs(["due:soon", "priority:X", "depends:XYZ", "foo", "bar:1"])
    assert errors == ["due must be YYYY-MM-DD; got 'soon'",
                      "priority must be H, M, or L; got 'X'",
                      "depends must be 8 hex chars; got 'XYZ'",
                      "unknown attr token 'foo'",
                      "unknown attr 'bar'"]


def test_parse_action_attrs_tolerates_the_buffer_timestamp():
    attrs, errors = V.parse_action_attrs("2026-09-10T08:00:00 due:2026-09-20 depends:aaaa0001".split())
    assert attrs == {"depends": ["aaaa0001"], "due": "2026-09-20"}
    assert errors == []
    attrs, errors = V.parse_action_attrs(["due:soon", "priority:H"])
    assert attrs == {"depends": [], "priority": "H"}  # bad values are not kept
    assert errors == ["due must be YYYY-MM-DD; got 'soon'"]


def test_person_exists_is_true_for_no_one_and_for_a_person_file():
    people = V.vault_home() / "people"
    people.mkdir(parents=True)
    (people / "Riaz Arbi.md").write_text("x")
    assert V.person_exists("") and V.person_exists(None)
    assert V.person_exists("Riaz Arbi")
    assert not V.person_exists("Ghost")


# ---------- time ----------

def test_to_iso_and_from_iso_round_trip():
    dt = datetime(2026, 9, 10, 14, 30, tzinfo=timezone.utc)
    assert V.to_iso(dt) == "2026-09-10T14:30:00.000Z"
    assert V.from_iso("2026-09-10T14:30:00.000Z") == dt


def test_when_from_flags_combines_date_and_time():
    assert V.when_from_flags("2026-09-10", "14:30") == datetime(2026, 9, 10, 14, 30)


# ---------- errors ----------

def test_die_names_the_running_command_as_argparse_does(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["/some/bin/hours", "log"])
    with pytest.raises(SystemExit) as exc:
        V.die("empty description")
    assert exc.value.code == 1
    assert capsys.readouterr().err == "hours: error: empty description\n"
    with pytest.raises(SystemExit) as exc:
        V.die("no schemas", code=2)
    assert exc.value.code == 2


def test_warn_names_the_command_and_carries_on(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["/some/bin/payments"])
    V.warn("banking details incomplete")
    assert capsys.readouterr() == ("", "payments: warning: banking details incomplete\n")


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


# ---------- threads ----------

@pytest.fixture
def threads_dir():
    base = V.vault_home() / "threads"
    for rel in ("Projects/SGB.md", "Projects/Alpha.md", "Topics/SGB.md",
                "Processes/.hidden.md", "Processes/notes.txt", "People/Riaz.md"):
        (base / rel).parent.mkdir(parents=True, exist_ok=True)
        (base / rel).write_text("---\nstatus: open\n---\n")
    return base


def test_discover_threads_walks_kinds_in_order_and_skips_other_files(threads_dir):
    assert [(k, n) for k, n, _ in V.discover_threads()] == [
        ("project", "Alpha"), ("project", "SGB"), ("topic", "SGB")]


def test_resolve_thread_by_path_wikilink_and_unique_name(threads_dir):
    assert V.resolve_thread("Projects/Alpha") == ("project", "Alpha", threads_dir / "Projects/Alpha.md")
    assert V.resolve_thread(" [[Topics/SGB]] ")[:2] == ("topic", "SGB")
    assert V.resolve_thread("Alpha")[:2] == ("project", "Alpha")


def test_resolve_thread_misses_return_none_whatever_the_filesystem(threads_dir):
    """`Projects/sgb` exists as a path on macOS, which ignores case. It must
    still miss, as it does on Linux."""
    for ref in ("Nope", "Projects/Nope", "People/Riaz", "alpha", "Projects/sgb"):
        assert V.resolve_thread(ref) is None, ref


def test_resolve_thread_ambiguous_bare_name_raises(threads_dir):
    with pytest.raises(ValueError, match="matches: Projects/SGB, Topics/SGB"):
        V.resolve_thread("SGB")


def test_is_thread_wants_the_exact_kind_and_name(threads_dir):
    assert V.is_thread("Projects/SGB") and V.is_thread("Topics/SGB")
    for ref in ("SGB", "projects/SGB", "Projects/sgb", "People/Riaz", "Projects/Alpha.md", ""):
        assert not V.is_thread(ref), ref


def test_is_plain_name():
    for name in ("SGB", "Riaz Arbi", "AXA DORA", "José Núñez", "a.b"):
        assert V.is_plain_name(name), name
    for name in ("../x", "a/b", "/abs", ".hidden", "."):
        assert not V.is_plain_name(name), name


def test_minutes_of_counts_whole_minutes_and_is_zero_without_both_ends():
    e = {"startTime": "2026-08-04T07:00:00.000Z", "endTime": "2026-08-04T08:30:59.000Z"}
    assert V.minutes_of(e) == 90
    assert V.minutes_of({"startTime": e["startTime"]}) == 0
    assert V.minutes_of({"endTime": e["endTime"]}) == 0


def test_in_window_includes_both_bounds_and_treats_empty_as_open():
    assert V.in_window("2026-08-04", "2026-08-04", "2026-08-04")
    assert not V.in_window("2026-08-03", "2026-08-04", "")
    assert not V.in_window("2026-08-05", None, "2026-08-04")
    assert V.in_window("2026-08-05", None, None)


def test_is_currency_code_wants_three_capitals():
    assert V.is_currency_code("ZAR")
    assert not V.is_currency_code("zar")
    assert not V.is_currency_code("ZA")
    assert not V.is_currency_code("ZARR")
