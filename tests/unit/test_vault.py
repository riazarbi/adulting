"""Unit tests for adulting.vault's helpers that don't touch the vault.

These pin current behaviour, quirks included, so that deduplicating the
several frontmatter parsers later can't change it unnoticed.
"""

import re
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from adulting import vault as V


# ---------- location ----------

def test_vault_home_follows_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("ADULTING_HOME", str(tmp_path / "elsewhere"))
    assert V.vault_home() == tmp_path / "elsewhere"


# ---------- frontmatter ----------

def test_parse_frontmatter_doc_reads_scalars_and_strips_quotes():
    text = "---\nthread: \"[[Projects/SGB]]\"\ncurrency: 'ZAR'\nClient-2: x\n---\n\n# SGB\n"
    assert V.parse_frontmatter_doc(text) == (
        {"thread": "[[Projects/SGB]]", "currency": "ZAR", "Client-2": "x"}, "\n# SGB\n")


def test_parse_frontmatter_doc_reads_block_lists():
    text = ("---\ntopic: Kickoff\nthreads:\n  - \"[[Projects/SGB]]\"\n"
            "  - [[Topics/Admin]]\npeople:\n  - \"[[people/Riaz Arbi]]\"\n"
            "  - Someone Untracked\n---\n\nBody line\n")
    fm, body = V.parse_frontmatter_doc(text)
    assert fm == {"topic": "Kickoff", "threads": ["[[Projects/SGB]]", "[[Topics/Admin]]"],
                  "people": ["[[people/Riaz Arbi]]", "Someone Untracked"]}
    assert body == "\nBody line\n"


def test_parse_frontmatter_doc_reads_a_list_of_mappings():
    """The shape of a person's or thread's `cadences:`."""
    text = ("---\nstatus: open\ncadences:\n  - key: catch_up\n    frequency: 7\n"
            "    description: Catch up weekly\n  - key: review\n    frequency: 91\n---\n")
    assert V.parse_frontmatter_doc(text)[0] == {"status": "open", "cadences": [
        {"key": "catch_up", "frequency": "7", "description": "Catch up weekly"},
        {"key": "review", "frequency": "91"}]}


def test_parse_frontmatter_doc_empty_field_is_an_empty_string():
    assert V.parse_frontmatter_doc("---\nthreads:\nended:\n---\n")[0] == {"threads": "", "ended": ""}


def test_parse_frontmatter_doc_without_a_block_returns_text_as_body():
    assert V.parse_frontmatter_doc("no frontmatter") == ({}, "no frontmatter")


def test_parse_frontmatter_doc_that_never_closes_reads_every_line():
    assert V.parse_frontmatter_doc("---\nstatus: open\n") == ({"status": "open"}, "---\nstatus: open\n")


def test_unwiki():
    assert V.unwiki("[[Projects/SGB]]") == "Projects/SGB"
    assert V.unwiki("  [[Projects/SGB]]  ") == "Projects/SGB"
    assert V.unwiki("Projects/SGB") == "Projects/SGB"
    assert V.unwiki(None) == ""


def test_fuzzy_score_ranks_closer_matches_first():
    """The order `threads list` and `people list` rank in: an exact name,
    then a prefix, then all the initials, then a substring, then a partial
    run of initials, then nothing like it."""
    ranked = ["riaz arbi", "riaz", "ra", "arbi", "zzz"]
    scores = [V.fuzzy_score(q, "Riaz Arbi") for q in ranked]
    assert scores == sorted(scores, reverse=True) and len(set(scores)) == len(scores)
    name = "Bern Sellmeyer Rhodes"
    assert V.fuzzy_score("bsr", name) > V.fuzzy_score("r", name) > V.fuzzy_score("bs", name)


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
    assert lines[i + 1:j] == ["{", '  "entries": [', "    {", '      "id": "1"', "    }", "  ]", "}"]


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


def test_new_id_draws_again_until_the_id_is_unused():
    """8 hex digits almost never collide, so the draws are given here to
    force one: the first two are taken, the third is free."""
    draws = iter(["aaaa0001", "aaaa0002", "bbbb0003"])
    assert V.new_id({"aaaa0001", "aaaa0002"}, draw=lambda: next(draws)) == "bbbb0003"


def test_note_threads_reads_either_key_and_unwraps_wikilinks():
    note = '---\ntopic: x\nthreads:\n  - "[[Projects/SGB]]"\n  - Topics/Plain\ntype: Log\n---\nthreads: body\n'
    assert V.note_threads(V.parse_frontmatter_doc(note)[0]) == ["Projects/SGB", "Topics/Plain"]
    log = "---\nthread: '[[Topics/zeta]]'\n---\n"
    assert V.note_threads(V.parse_frontmatter_doc(log)[0]) == ["Topics/zeta"]
    assert V.note_threads({}) == []
    assert V.note_threads({"threads": ["", "  ", "Topics/Plain"]}) == ["Topics/Plain"]


def test_read_config_reads_sections_scalars_and_comments():
    """config.yaml is read by the same parser as frontmatter."""
    assert V.read_config() == {}
    cfg = V.vault_home() / ".adulting" / "config.yaml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text('# billing defaults\nbilling:\n  bank_name: "Capitec Bank"\n  x: 1\n\n'
                   'owner: "Riaz Arbi"\nhours:\n  rate: 2500\n')
    assert V.read_config() == {"billing": {"bank_name": "Capitec Bank", "x": "1"},
                               "owner": "Riaz Arbi", "hours": {"rate": "2500"}}


# ---------- actions ----------

def test_parse_action_attrs_keeps_good_values_and_reports_bad_ones():
    attrs, errors = V.parse_action_attrs(
        ["due:2026-09-20", "priority:H", "depends:aaaaaaaa", "depends:bbbbbbbb",
         "scheduled:2026-09-15"])
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


# ---------- billing parties ----------

def client_thread(vault):
    """A billed thread that names its client."""
    p = vault.write_thread("Projects", "SANA Partners", currency="ZAR", rate=2500)
    p.write_text(p.read_text().replace(
        "---\n\n# SANA",
        "client_name: Sana Partners (Pty) Ltd\n"
        "client_address: Unit 301|2 Park Road|Cape Town\n"
        "client_vat: 4220259826\n---\n\n# SANA"), encoding="utf-8")
    return p


def write_billing(vault, **over):
    fields = {"supplier_name": "Riaz Arbi",
              "bank_account_name": "Riaz J Arbi", "bank_name": "Capitec Bank",
              "bank_account_number": "0000000000", "bank_branch_code": "470010",
              "bank_account_type": "Savings"}
    fields.update(over)
    body = "owner: Riaz Arbi\nbilling:\n" + "".join(
        f"  {k}: {v}\n" for k, v in fields.items())
    (vault.home / ".adulting" / "config.yaml").write_text(body, encoding="utf-8")


def test_banking_is_complete_when_every_field_is_set(vault):
    """A document that asks for money must say where to send it."""
    write_billing(vault)
    assert V.banking()["complete"] is True


def test_banking_is_incomplete_while_a_field_is_a_todo_placeholder(vault):
    write_billing(vault, bank_account_number="TODO")
    assert V.banking()["complete"] is False


def test_banking_is_incomplete_when_a_field_is_missing(vault):
    write_billing(vault)
    cfg = vault.home / ".adulting" / "config.yaml"
    cfg.write_text(cfg.read_text().replace("  bank_branch_code: 470010\n", ""),
                   encoding="utf-8")
    assert V.banking()["complete"] is False


def test_supplier_address_is_pipe_separated(vault):
    write_billing(vault, supplier_address="14 Kinnoull Road|Camps Bay|Cape Town")
    assert V.supplier()["lines"] == [
        "14 Kinnoull Road", "Camps Bay", "Cape Town"]


def test_reference_is_the_thread_name_without_its_kind_prefix(vault):
    """Derived, not configured: it cannot drift or carry another client's code."""
    write_billing(vault)
    p = client_thread(vault)
    assert V.client(p)["reference"] == "SANA Partners"


def test_reference_ignores_a_frontmatter_override(vault):
    write_billing(vault)
    p = client_thread(vault)
    p.write_text(p.read_text().replace(
        "client_vat:", "client_reference: SOMETHING ELSE\nclient_vat:"),
        encoding="utf-8")
    assert V.client(p)["reference"] == "SANA Partners"


def test_vault_file_needs_the_exact_spelling_and_stays_in_the_vault():
    home = V.vault_home()
    (home / "people").mkdir(parents=True)
    (home / "people" / "Riaz Arbi.md").write_text("x")
    assert V.vault_file("people/Riaz Arbi.md") == home / "people" / "Riaz Arbi.md"
    assert V.vault_file("people/riaz arbi.md") is None
    assert V.vault_file("people/../people/Riaz Arbi.md") is None
    assert V.vault_file("people") is None            # a folder is not a file
    assert V.vault_file("people/Nobody.md") is None
    assert V.person_exists("Riaz Arbi") and not V.person_exists("riaz arbi")


def test_find_record_returns_the_record_inside_its_files_list():
    path = V.vault_home() / "hours" / "Projects" / "SGB.md"
    V.write_records(path, [{"id": "aaaa0001"}, {"id": "aaaa0002"}], V.HOURS_FENCE, "Projects/SGB", None)
    found_path, ref, records, record = V.find_record("hours", V.HOURS_FENCE, "aaaa0002")
    assert (found_path, ref, record) == (path, "Projects/SGB", {"id": "aaaa0002"})
    assert record is records[1]
    assert V.find_record("hours", V.HOURS_FENCE, "deadbeef") is None
