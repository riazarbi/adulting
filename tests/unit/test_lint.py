"""Unit tests for adulting.lint: parsers, the schema DSL and graph checks."""

from pathlib import Path

from adulting import lint as L


# ---------- scalar helpers ----------

def test_unquote():
    assert L.unquote('"say \\"hi\\""') == 'say "hi"'
    assert L.unquote("'it''s'") == "it's"
    assert L.unquote("  bare  ") == "bare"
    assert L.unquote('"') == '"'


def test_unwiki_returns_none_for_non_links():
    """Unlike vault.unwiki, lint's version distinguishes 'not a link'."""
    assert L.unwiki("[[Projects/SGB]]") == "Projects/SGB"
    assert L.unwiki("Projects/SGB") is None


# ---------- frontmatter ----------

def test_parse_frontmatter_scalars_lists_and_mappings():
    text = ("---\ntopic: \"Kickoff\"\nthreads:\n  - \"[[Projects/SGB]]\"\n"
            "  - '[[Topics/Admin]]'\ncadences:\n  - key: weekly\n"
            "    frequency: 7\n  - key: monthly\n    frequency: 30\n---\nbody\n")
    fm, body_start = L.parse_frontmatter(text)
    assert fm == {
        "topic": "Kickoff",
        "threads": ["[[Projects/SGB]]", "[[Topics/Admin]]"],
        "cadences": [{"key": "weekly", "frequency": "7"},
                     {"key": "monthly", "frequency": "30"}],
    }
    assert text.split("\n")[body_start] == "body"


def test_parse_frontmatter_empty_list_and_no_block():
    assert L.parse_frontmatter("---\nthreads:\n---\n")[0] == {"threads": []}
    assert L.parse_frontmatter("no frontmatter") == ({}, 0)


# ---------- schema DSL ----------

def test_parse_md_table_drops_separators_and_unescapes_pipes():
    lines = ["| name | constraint |", "|---|---|",
             "| threads | regex=(a\\|b) |", "not a table"]
    rows, end = L.parse_md_table(lines, 0)
    assert rows == [["name", "constraint"], ["threads", "regex=(a|b)"]]
    assert end == 3


def test_parse_constraint_forms():
    assert L.parse_constraint("") == {}
    assert L.parse_constraint("regex=\\d+") == {"regex": "\\d+"}
    assert L.parse_constraint("min=1") == {"min_length": 1}
    assert L.parse_constraint("open, paused") == {"enum": ["open", "paused"]}
    assert L.parse_constraint("must_contain_digit") == {"flags": {"must_contain_digit"}}


def test_parse_constraint_reads_prose_as_an_enum():
    """The known trap from CHANGELOG 2026-09-07: prose in a constraint cell
    silently becomes an enum. Pinned so a rewrite doesn't change it quietly."""
    assert L.parse_constraint("wikilink to Projects/X; must resolve") == {
        "enum": ["must resolve"]}


def test_every_packaged_schema_loads():
    schemas = L.load_schemas(L.SCHEMAS_DIR)
    assert sorted(schemas) == [
        "hours_file", "log", "note_correspondence", "note_meeting",
        "note_simple", "payments_file", "person", "task_anchor", "thread",
        "thread_entry"]
    thread = schemas["thread"]
    assert thread["scope"] == "file" and thread["directory"] == "threads"
    assert thread["fields"]["status"] == {
        "required": True, "type": "enum",
        "constraint": {"enum": ["open", "paused", "closed"]}}
    assert schemas["thread_entry"]["scope"] == "line"


def test_eval_when():
    assert L.eval_when("type == Meeting", {"type": "Meeting"})
    assert not L.eval_when("type == Meeting", {"type": "Log"})
    assert L.eval_when("type in [Log, Report]", {"type": "Report"})
    assert L.eval_when("line =~ ^- \\d{4}", {"line": "- 2026 x"})
    assert not L.eval_when("line =~ ([", {"line": "x"})  # bad regex is False
    assert not L.eval_when("", {})
    assert not L.eval_when("nonsense", {})


def test_validate_value():
    spec = {"constraint": {"enum": ["a"], "regex": "[a-z]", "min_length": 2,
                           "flags": {"must_contain_digit"}}}
    assert list(L.validate_value("f", "", spec)) == []
    assert list(L.validate_value("f", "B", spec)) == [
        "f: value 'B' not in ['a']",
        "f: value 'B' does not match /[a-z]/",
        "f: value 'B' shorter than min=2",
        "f: value 'B' must contain a digit",
    ]
    list_errors = list(L.validate_value("f", ["a", {"k": "v"}, "zz"],
                                        {"constraint": {"enum": ["a"]}}))
    assert list_errors == ["f[2]: value 'zz' not in ['a']"]


def test_validate_cadences():
    assert list(L.validate_cadences("not a list")) == []
    errors = list(L.validate_cadences([
        {"key": "ok", "frequency": "7", "description": "d"},
        {"key": "ok", "frequency": "x"},
        "skipped",
    ]))
    assert errors == [
        "cadences[1]: missing description",
        "cadences[1]: duplicate key 'ok'",
        "cadences[1]: frequency 'x' must be an integer",
    ]


# ---------- vault-relative ----------

def test_resolve_wikilink_uses_the_current_vault(tmp_path, monkeypatch):
    monkeypatch.setenv("ADULTING_HOME", str(tmp_path))
    assert L.resolve_wikilink("Projects/SGB") == tmp_path / "threads" / "Projects/SGB.md"
    assert L.resolve_wikilink("people/Riaz") == tmp_path / "people/Riaz.md"
    assert L.resolve_wikilink("Elsewhere/X") is None


def test_find_file_schema_matches_directory_and_filename(tmp_path, monkeypatch):
    monkeypatch.setenv("ADULTING_HOME", str(tmp_path))
    schemas = L.load_schemas(L.SCHEMAS_DIR)
    note = tmp_path / "notes" / "2026-09-10-14-30-00.md"
    assert L.find_file_schema(note, {"type": "Meeting"}, schemas)["name"] == "note_meeting"
    assert L.find_file_schema(note, {"type": "Report"}, schemas)["name"] == "note_simple"
    log = tmp_path / "logs" / "Projects" / "SGB" / "2026-09-10.md"
    assert L.find_file_schema(log, {}, schemas)["name"] == "log"
    assert L.find_file_schema(tmp_path / "threads" / "x.y.md", {}, schemas) is None


def test_discover_files_walks_known_dirs_only(tmp_path, monkeypatch):
    monkeypatch.setenv("ADULTING_HOME", str(tmp_path))
    for rel in ["notes/a.md", "threads/Projects/b.md", "assets/c.md",
                "notes/.hidden.md", "notes/d.md.bak", "notes/.obsidian/e.md"]:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x")
    found = [p.relative_to(tmp_path).as_posix() for p in L.discover_files()]
    assert found == ["notes/a.md", "threads/Projects/b.md"]


# ---------- task graph ----------

def registry_with(edges):
    reg = {"by_uuid": {}, "depends_edges": [], "hours_ids": {}}
    for i, (src, deps) in enumerate(edges):
        reg["by_uuid"].setdefault(src, []).append((Path("n.md"), i + 1))
        if deps:
            reg["depends_edges"].append((src, deps, Path("n.md"), i + 1))
    return reg


def test_rotate_to_min():
    assert L._rotate_to_min(["c", "a", "b"]) == ["a", "b", "c"]
    assert L._rotate_to_min([]) == []


def test_find_cycles():
    graph = {"a": ["b"], "b": ["c"], "c": ["a"], "d": ["d"], "e": ["zzz"]}
    assert list(L._find_cycles(graph)) == [["a", "b", "c"], ["d"]]


def test_cross_check_tasks():
    reg = registry_with([("aaaa0001", ["aaaa0002"]), ("aaaa0002", ["aaaa0001"]),
                         ("aaaa0003", ["deadbeef"]), ("aaaa0003", None)])
    assert list(L.cross_check_tasks(reg)) == [
        (Path("n.md"), 3, "task_anchor.uuid: 'aaaa0003' duplicated at n.md:4"),
        (Path("n.md"), 4, "task_anchor.uuid: 'aaaa0003' duplicated at n.md:3"),
        (Path("n.md"), 3, "task_anchor.depends: 'deadbeef' does not resolve to any anchor"),
        (Path("n.md"), 1, "task_anchor.depends: cycle: aaaa0001 -> aaaa0002 -> aaaa0001"),
    ]


def test_a_cycle_reached_twice_is_reported_once():
    """A task listing the same dependency twice (`depends:x,x`) makes the
    search meet the cycle twice; it is still one cycle."""
    reg = registry_with([("aaaa0001", ["aaaa0002"]), ("aaaa0002", ["aaaa0001", "aaaa0001"])])
    assert [msg for _, _, msg in L.cross_check_tasks(reg)] == [
        "task_anchor.depends: cycle: aaaa0001 -> aaaa0002 -> aaaa0001"]


def test_cross_check_hours_points_each_duplicate_at_the_others():
    reg = {"hours_ids": {"abcd1234": [(Path("a.md"), 7), (Path("b.md"), 9)],
                         "unique00": [(Path("a.md"), 7)]}}
    assert list(L.cross_check_hours(reg)) == [
        (Path("a.md"), 7, "record id 'abcd1234' duplicated at b.md:9"),
        (Path("b.md"), 9, "record id 'abcd1234' duplicated at a.md:7"),
    ]
