"""Per-subcommand functionality tests for the `tasks` CLI.

Each test exercises one subcommand end-to-end against a fresh temp vault.
Where a test asserts on rendered output we look at substrings, not exact
text, so the table renderer can evolve without breaking the suite.
"""

import re


# ---------- common fixtures-on-fixture helpers ----------

def _setup_vault(vault, threads=(("Projects", "SGB"),), people=("Riaz Arbi",)):
    for kind, name in threads:
        vault.write_thread(kind, name)
    for p in people:
        vault.write_person(p)


def _seed_anchor(vault, stem, *anchor_lines, threads=("Projects/SGB",)):
    body = "\n".join(anchor_lines)
    return vault.write_note(stem, body, threads=list(threads))


def _find_anchor_lines(vault, relpath):
    """Return all TASK:/DONE: lines in the file, in order. Robust to
    frontmatter layout changes."""
    return [ln for ln in vault.lines(relpath)
            if ln.startswith("TASK:") or ln.startswith("DONE:")]


def _read_anchor_line(vault, relpath, _ignored=None):
    """Return the first TASK:/DONE: line in the file. The legacy
    line_no param is ignored — kept so old call sites compile until
    they're migrated to _find_anchor_lines."""
    lines = _find_anchor_lines(vault, relpath)
    assert lines, f"no TASK:/DONE: line in {relpath}"
    return lines[0]


# ---------- default invocation: ingest ----------

def test_ingest_basic_action(vault):
    _setup_vault(vault)
    vault.write_note("2026-05-27-09-15-22",
        "ACTION: Pick up dry cleaning",
        threads=["Projects/SGB"])
    r = vault.run(cli="tasks")
    assert r.returncode == 0, r.stderr
    note = vault.read("notes/2026-05-27-09-15-22.md")
    assert "ACTION:" not in note
    assert re.search(
        r"^TASK: Pick up dry cleaning <!--[a-f0-9]{8} entry:\d{4}-\d{2}-\d{2}-->$",
        note, re.MULTILINE), note


def test_ingest_with_assignee_and_attrs(vault):
    _setup_vault(vault)
    vault.write_note("2026-05-27-09-15-22",
        "ACTION: (Riaz Arbi) Send report "
        "<!--2026-05-27T09:15:22 due:2026-05-29 priority:H-->",
        threads=["Projects/SGB"])
    r = vault.run(cli="tasks")
    assert r.returncode == 0, r.stderr
    note = vault.read("notes/2026-05-27-09-15-22.md")
    assert re.search(
        r"^TASK: \[#H\] \(Riaz Arbi\) Send report "
        r"<!--[a-f0-9]{8} entry:\d{4}-\d{2}-\d{2} due:2026-05-29-->$",
        note, re.MULTILINE), note


def test_ingest_unresolved_assignee_fails(vault):
    _setup_vault(vault)  # only Riaz Arbi exists
    vault.write_note("2026-05-27-09-15-22",
        "ACTION: (Ghost) Phantom",
        threads=["Projects/SGB"])
    r = vault.run(cli="tasks")
    assert r.returncode != 0
    assert "Ghost" in r.stderr and "does not resolve" in r.stderr
    note = vault.read("notes/2026-05-27-09-15-22.md")
    assert "ACTION: (Ghost) Phantom" in note  # untouched


def test_ingest_unresolved_thread_fails(vault):
    _setup_vault(vault, threads=(("Projects", "SGB"),))
    vault.write_note("2026-05-27-09-15-22",
        "ACTION: Refers to a missing thread",
        threads=["Projects/Nope"])
    r = vault.run(cli="tasks")
    assert r.returncode != 0
    assert "does not resolve" in r.stderr


def test_ingest_dry_run_does_not_write(vault):
    _setup_vault(vault)
    vault.write_note("2026-05-27-09-15-22",
        "ACTION: Pick up dry cleaning",
        threads=["Projects/SGB"])
    r = vault.run("--dry-run", cli="tasks")
    assert r.returncode == 0, r.stderr
    note = vault.read("notes/2026-05-27-09-15-22.md")
    assert "ACTION: Pick up dry cleaning" in note  # unchanged


def test_ingest_idempotent(vault):
    """Re-running ingest on a vault with no ACTION lines is a no-op."""
    _setup_vault(vault)
    vault.write_note("2026-05-27-09-15-22",
        "ACTION: Once",
        threads=["Projects/SGB"])
    vault.run(cli="tasks")
    before = vault.read("notes/2026-05-27-09-15-22.md")
    vault.run(cli="tasks")
    after = vault.read("notes/2026-05-27-09-15-22.md")
    assert before == after


def test_ingest_generates_unique_uuids(vault):
    _setup_vault(vault)
    vault.write_note("2026-05-27-09-15-22",
        "ACTION: First\nACTION: Second\nACTION: Third",
        threads=["Projects/SGB"])
    vault.run(cli="tasks")
    note = vault.read("notes/2026-05-27-09-15-22.md")
    uuids = re.findall(r"<!--([a-f0-9]{8}) ", note)
    assert len(uuids) == 3
    assert len(set(uuids)) == 3


# ---------- done ----------

def test_done_flips_kind_and_stamps_end(vault):
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: Send report <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("done", "abcd1234", cli="tasks")
    assert r.returncode == 0, r.stderr
    line = _read_anchor_line(vault, "notes/2026-05-27-09-15-22.md", 6)
    assert line.startswith("DONE:")
    assert "end:" in line
    assert "<!--abcd1234 entry:2026-05-20 end:" in line


def test_done_is_idempotent(vault):
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "DONE: Already <!--abcd1234 entry:2026-05-20 end:2026-05-25-->")
    r = vault.run("done", "abcd1234", cli="tasks")
    assert r.returncode == 0
    line = _read_anchor_line(vault, "notes/2026-05-27-09-15-22.md", 6)
    assert "end:2026-05-25" in line  # untouched


def test_done_unknown_uuid_fails(vault):
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: T <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("done", "ffffffff", cli="tasks")
    assert r.returncode != 0
    assert "no task found" in r.stderr


def test_done_ambiguous_prefix_fails(vault):
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: A <!--abcd1234 entry:2026-05-20-->\n"
        "TASK: B <!--abcd5678 entry:2026-05-20-->")
    r = vault.run("done", "abcd", cli="tasks")
    assert r.returncode != 0
    assert "ambiguous" in r.stderr


# ---------- set-description ----------

def test_set_description_rewrites_body(vault):
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: old text <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("set-description", "abcd1234", "new text", cli="tasks")
    assert r.returncode == 0
    line = _read_anchor_line(vault, "notes/2026-05-27-09-15-22.md", 6)
    assert "TASK: new text <!--abcd1234" in line


def test_set_description_empty_fails(vault):
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: old <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("set-description", "abcd1234", "  ", cli="tasks")
    assert r.returncode != 0


# ---------- set-assignee ----------

def test_set_assignee_writes_prefix(vault):
    _setup_vault(vault, people=("Riaz Arbi", "Charlie"))
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: shared task <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("set-assignee", "abcd1234", "Charlie", cli="tasks")
    assert r.returncode == 0
    line = _read_anchor_line(vault, "notes/2026-05-27-09-15-22.md", 6)
    assert "TASK: (Charlie) shared task <!--abcd1234" in line


def test_set_assignee_rejects_unknown_person(vault):
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: t <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("set-assignee", "abcd1234", "Ghost", cli="tasks")
    assert r.returncode != 0
    assert "Ghost" in r.stderr


# ---------- set-due / set-scheduled ----------

def test_set_due_inserts_attr(vault):
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: t <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("set-due", "abcd1234", "2026-06-01", cli="tasks")
    assert r.returncode == 0
    line = _read_anchor_line(vault, "notes/2026-05-27-09-15-22.md", 6)
    assert "due:2026-06-01" in line


def test_set_due_replaces_existing(vault):
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: t <!--abcd1234 entry:2026-05-20 due:2026-05-25-->")
    r = vault.run("set-due", "abcd1234", "2026-06-01", cli="tasks")
    assert r.returncode == 0
    line = _read_anchor_line(vault, "notes/2026-05-27-09-15-22.md", 6)
    assert "due:2026-06-01" in line
    assert "due:2026-05-25" not in line


def test_set_due_rejects_bad_date(vault):
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: t <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("set-due", "abcd1234", "tomorrow", cli="tasks")
    assert r.returncode != 0


def test_set_scheduled_inserts_attr(vault):
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: t <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("set-scheduled", "abcd1234", "2026-06-05", cli="tasks")
    assert r.returncode == 0
    line = _read_anchor_line(vault, "notes/2026-05-27-09-15-22.md", 6)
    assert "scheduled:2026-06-05" in line


# ---------- set-priority ----------

def test_set_priority_writes_visible_token(vault):
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: t <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("set-priority", "abcd1234", "H", cli="tasks")
    assert r.returncode == 0
    line = _read_anchor_line(vault, "notes/2026-05-27-09-15-22.md", 6)
    assert line.startswith("TASK: [#H] t <!--abcd1234")
    # Priority must NOT leak into attrs blob:
    assert "priority:H" not in line


def test_set_priority_replaces_existing(vault):
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: [#H] t <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("set-priority", "abcd1234", "M", cli="tasks")
    assert r.returncode == 0
    line = _read_anchor_line(vault, "notes/2026-05-27-09-15-22.md", 6)
    assert "[#M]" in line and "[#H]" not in line


def test_set_priority_rejects_invalid(vault):
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: t <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("set-priority", "abcd1234", "X", cli="tasks")
    assert r.returncode != 0


# ---------- add-depends / rm-depends ----------

def test_add_depends_appends(vault):
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: dep target <!--beef0000 entry:2026-05-20-->\n"
        "TASK: dependent <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("add-depends", "abcd1234", "beef0000", cli="tasks")
    assert r.returncode == 0
    # The dependent is the second TASK line; index 1.
    line = _find_anchor_lines(vault, "notes/2026-05-27-09-15-22.md")[1]
    assert "depends:beef0000" in line


def test_add_depends_rejects_self(vault):
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: t <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("add-depends", "abcd1234", "abcd1234", cli="tasks")
    assert r.returncode != 0


def test_rm_depends_removes(vault):
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: dep <!--beef0000 entry:2026-05-20-->\n"
        "TASK: dependent <!--abcd1234 entry:2026-05-20 depends:beef0000-->")
    r = vault.run("rm-depends", "abcd1234", "beef0000", cli="tasks")
    assert r.returncode == 0
    line = _find_anchor_lines(vault, "notes/2026-05-27-09-15-22.md")[1]
    assert "depends:" not in line


def test_rm_depends_unknown_target_fails(vault):
    """rm-depends needs both anchors to resolve; missing target = error."""
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: t <!--abcd1234 entry:2026-05-20-->")
    r = vault.run("rm-depends", "abcd1234", "deadbeef", cli="tasks")
    assert r.returncode != 0


# ---------- list / next / show ----------

def test_list_shows_only_pending(vault):
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: pending one <!--abcd1234 entry:2026-05-20-->\n"
        "DONE: completed one <!--ef567890 entry:2026-05-20 end:2026-05-25-->")
    r = vault.run("list", cli="tasks")
    assert r.returncode == 0
    assert "pending one" in r.stdout
    assert "completed one" not in r.stdout


def test_list_priority_filter(vault):
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: [#H] high prio <!--abcd1234 entry:2026-05-20-->\n"
        "TASK: [#L] low prio <!--ef567890 entry:2026-05-20-->")
    r = vault.run("list", "--priority", "H", cli="tasks")
    assert "high prio" in r.stdout
    assert "low prio" not in r.stdout


def test_list_assignee_filter(vault):
    _setup_vault(vault, people=("Riaz Arbi", "Charlie"))
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: (Riaz Arbi) mine <!--abcd1234 entry:2026-05-20-->\n"
        "TASK: (Charlie) theirs <!--ef567890 entry:2026-05-20-->")
    r = vault.run("list", "--assignee", "Charlie", cli="tasks")
    assert "theirs" in r.stdout
    assert "mine" not in r.stdout


def test_list_renders_assignee(vault):
    _setup_vault(vault, people=("Riaz Arbi", "Charlie"))
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: (Charlie) theirs <!--abcd1234 entry:2026-05-20-->\n"
        "TASK: unassigned <!--ef567890 entry:2026-05-20-->")
    r = vault.run("list", cli="tasks")
    assert "(Charlie)" in r.stdout
    assert "theirs" in r.stdout
    # unassigned task still renders, just without a parenthetical
    assert "unassigned" in r.stdout


def test_list_overdue_filter(vault):
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: overdue <!--abcd1234 entry:2026-05-20 due:2000-01-01-->\n"
        "TASK: future <!--ef567890 entry:2026-05-20 due:2099-01-01-->\n"
        "TASK: no-due <!--beef0000 entry:2026-05-20-->")
    r = vault.run("list", "--overdue", cli="tasks")
    assert "overdue" in r.stdout
    assert "future" not in r.stdout
    assert "no-due" not in r.stdout


def test_list_thread_filter(vault):
    _setup_vault(vault, threads=(("Projects", "SGB"), ("Projects", "Other")))
    vault.write_note("2026-05-27-09-15-22",
        "TASK: in SGB <!--abcd1234 entry:2026-05-20-->",
        threads=["Projects/SGB"])
    vault.write_note("2026-05-27-10-30-00",
        "TASK: in Other <!--ef567890 entry:2026-05-20-->",
        threads=["Projects/Other"])
    r = vault.run("list", "--thread", "Projects/SGB", cli="tasks")
    assert "in SGB" in r.stdout
    assert "in Other" not in r.stdout


def test_next_returns_at_most_5(vault):
    _setup_vault(vault)
    lines = [f"TASK: t{i} <!--abc1{i:04x} entry:2026-05-20-->" for i in range(8)]
    _seed_anchor(vault, "2026-05-27-09-15-22", "\n".join(lines))
    r = vault.run("next", cli="tasks")
    assert r.returncode == 0
    # Count uuid prefixes in output to verify at most 5 shown.
    shown = re.findall(r"\babc1[0-9a-f]{4}\b", r.stdout)
    assert 0 < len(shown) <= 5


def test_next_sort_priority_first(vault):
    """H sorts before M sorts before L sorts before none."""
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: none <!--abc10000 entry:2026-05-20-->\n"
        "TASK: [#L] low <!--abc10001 entry:2026-05-20-->\n"
        "TASK: [#H] high <!--abc10002 entry:2026-05-20-->\n"
        "TASK: [#M] mid <!--abc10003 entry:2026-05-20-->")
    r = vault.run("next", cli="tasks")
    pos_high = r.stdout.find("high")
    pos_mid = r.stdout.find("mid")
    pos_low = r.stdout.find("low")
    pos_none = r.stdout.find("none")
    assert 0 <= pos_high < pos_mid < pos_low < pos_none


def test_show_renders_all_fields(vault):
    _setup_vault(vault)
    _seed_anchor(vault, "2026-05-27-09-15-22",
        "TASK: [#H] (Riaz Arbi) details "
        "<!--abcd1234 entry:2026-05-20 due:2026-05-29 "
        "scheduled:2026-05-28 depends:ef567890-->\n"
        "TASK: dep <!--ef567890 entry:2026-05-20-->")
    r = vault.run("show", "abcd1234", cli="tasks")
    assert r.returncode == 0
    out = r.stdout
    assert "uuid:        abcd1234" in out
    assert "priority:    H" in out
    assert "assignee:    Riaz Arbi" in out
    assert "body:        details" in out
    assert "entry:       2026-05-20" in out
    assert "due:         2026-05-29" in out
    assert "scheduled:   2026-05-28" in out
    assert "depends:     ef567890" in out
    assert "kind:        TASK" in out


# ---------- end-to-end: ingest then mutate ----------

def test_full_lifecycle(vault):
    """ACTION -> ingest -> set-priority -> set-due -> done."""
    _setup_vault(vault)
    vault.write_note("2026-05-27-09-15-22",
        "ACTION: (Riaz Arbi) lifecycle test",
        threads=["Projects/SGB"])
    r = vault.run(cli="tasks")
    assert r.returncode == 0
    note = vault.read("notes/2026-05-27-09-15-22.md")
    m = re.search(r"<!--([a-f0-9]{8}) entry:", note)
    assert m, note
    u = m.group(1)

    r = vault.run("set-priority", u, "H", cli="tasks")
    assert r.returncode == 0
    r = vault.run("set-due", u, "2026-06-15", cli="tasks")
    assert r.returncode == 0
    r = vault.run("done", u, cli="tasks")
    assert r.returncode == 0

    note = vault.read("notes/2026-05-27-09-15-22.md")
    assert "DONE: [#H] (Riaz Arbi) lifecycle test" in note
    assert "due:2026-06-15" in note
    assert "end:" in note

    # Migrated file passes lint.
    lint = vault.run(cli="lint")
    assert lint.returncode == 0, lint.stdout


# ---------- removed commands ----------

def test_install_subcommand_gone(vault):
    r = vault.run("install", cli="tasks")
    assert r.returncode != 0


def test_rebuild_subcommand_gone(vault):
    r = vault.run("rebuild", cli="tasks")
    assert r.returncode != 0


def test_migrate_layout_subcommand_gone(vault):
    r = vault.run("migrate-layout", cli="tasks")
    assert r.returncode != 0
