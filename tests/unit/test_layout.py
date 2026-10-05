"""vault.LAYOUT: the one statement of where vault files live.

The schemas say where their files live too, and lint matches files by what
they say, so the two statements are held to each other here.
"""

from __future__ import annotations

from pathlib import Path

from adulting import lint as L
from adulting import vault as V


def test_every_file_schema_lives_somewhere_in_the_layout():
    schemas = L.load_schemas(L.SCHEMAS_DIR)
    places = {s['name']: s['where'] for s in schemas.values() if s['scope'] == 'file'}
    assert places, "no file schemas loaded"
    for name, where in places.items():
        assert where in V.LAYOUT.values(), f"{name}: path {where!r} is not in vault.LAYOUT"


def test_the_layout_names_each_record_kind_in_a_thread_folder():
    for kind in ('note', 'log', 'hours', 'payments'):
        assert V.LAYOUT[kind].startswith('threads/<Kind>/<Name>/'), kind
    assert V.LAYOUT['thread'] == 'threads/<Kind>/<Name>.md'


def test_layout_regex_matches_only_its_own_shape():
    note = V.layout_regex(V.LAYOUT['note'])
    assert note.match('threads/Projects/SGB/notes/2026-09-10-14-30-00.md')
    assert not note.match('notes/2026-09-10-14-30-00.md')
    assert not note.match('threads/Things/SGB/notes/2026-09-10-14-30-00.md')
    assert not note.match('threads/Projects/SGB/notes/meeting.md')
    thread = V.layout_regex(V.LAYOUT['thread'])
    assert thread.match('threads/Processes/Equal Experts.md')
    assert not thread.match('threads/Processes/SGB/hours.md')
    assert not thread.match('threads/Processes/.hidden.md')


def test_store_paths_follow_the_layout():
    assert V.HOURS.path('project', 'SGB') == V.threads_root() / 'Projects' / 'SGB' / 'hours.md'
    assert V.PAYMENTS.path('topic', 'X') == V.threads_root() / 'Topics' / 'X' / 'payments.md'


def test_thread_of_is_the_folder_a_file_is_in():
    root = V.threads_root()
    assert V.thread_of(root / 'Projects' / 'SGB' / 'notes' / 'n.md') == 'Projects/SGB'
    assert V.thread_of(root / 'Topics' / 'X' / 'hours.md') == 'Topics/X'
    assert V.thread_of(root / 'Projects' / 'SGB.md') is None
    assert V.thread_of(V.vault_home() / 'people' / 'A.md') is None


def write(path: Path, text: str = 'x') -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_discover_threads_skips_the_thread_folders():
    root = V.threads_root()
    write(root / 'Projects' / 'SGB.md')
    write(root / 'Projects' / 'SGB' / 'hours.md')
    assert [(k, n) for k, n, _ in V.discover_threads()] == [('project', 'SGB')]


def test_note_and_log_files_are_walked_across_thread_folders():
    root = V.threads_root()
    a = write(root / 'Projects' / 'A' / 'notes' / '2026-01-01-00-00-00.md')
    b = write(root / 'Topics' / 'B' / 'notes' / '2026-01-02-00-00-00.md')
    write(root / 'Topics' / 'B' / 'notes' / '.hidden.md')
    log = write(root / 'Topics' / 'B' / 'logs' / '2026-01-02.md')
    assert list(V.note_files()) == [a, b]
    assert list(V.log_files()) == [log]
    assert V.find_note('2026-01-02-00-00-00') == b
    assert V.find_note('2026-01-03-00-00-00') is None


def test_a_folder_is_never_a_thread_whatever_its_name():
    write(V.threads_root() / 'Projects' / 'Odd.md' / 'hours.md')
    assert list(V.discover_threads()) == []


def test_a_new_record_file_is_titled_by_its_thread_not_its_filename():
    path = V.HOURS.path('project', 'SANA Partners')
    V.write_records(path, [], V.HOURS, 'Projects/SANA Partners', 'ZAR')
    assert path.name == 'hours.md'
    assert '\n# SANA Partners — hours\n' in path.read_text()
