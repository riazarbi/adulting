"""Unit tests for adulting.threads: what `threads new` writes, and what it
refuses to write."""

import pytest

from adulting import threads as T


class Args:
    """A parsed command line, without argparse."""

    def __init__(self, **fields):
        self.__dict__.update(fields)


def new_args(**over):
    fields = dict(kind='project', category='work', name='SGB',
                  currency=None, rate=None)
    fields.update(over)
    return Args(**fields)


def test_new_writes_the_frontmatter_and_the_heading(capsys):
    assert T.cmd_new(new_args()) == 0
    path = T.threads_dir() / "Projects" / "SGB.md"
    text = path.read_text(encoding="utf-8")
    assert text == (f"---\nstatus: open\nkind: project\ncategory: work\n"
                    f"started: {T.V.today()}\n---\n\n# SGB\n")
    assert capsys.readouterr().out == f"created: {path}\n"


def test_new_writes_billing_only_when_given(capsys):
    T.cmd_new(new_args(name="Billed", currency="zar", rate=1800))
    text = (T.threads_dir() / "Projects" / "Billed.md").read_text(encoding="utf-8")
    assert "currency: ZAR\nrate: 1800\n" in text

    T.cmd_new(new_args(name="Unbilled"))
    plain = (T.threads_dir() / "Projects" / "Unbilled.md").read_text(encoding="utf-8")
    assert "currency" not in plain and "rate" not in plain


@pytest.mark.parametrize("over, message", [
    (dict(name="   "), "threads: error: empty name\n"),
    (dict(name="a/b"), "threads: error: name 'a/b' cannot contain '/' or start with '.'\n"),
    (dict(name=".hidden"), "threads: error: name '.hidden' cannot contain '/' or start with '.'\n"),
    (dict(rate=1800), "threads: error: --rate needs a --currency\n"),
    (dict(currency="rands"), "threads: error: currency 'RANDS' is not a 3-letter ISO code\n"),
])
def test_new_refuses_bad_arguments(over, message, capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["threads"])
    with pytest.raises(SystemExit) as exc:
        T.cmd_new(new_args(**over))
    assert exc.value.code == 1
    assert capsys.readouterr().err == message


def test_new_refuses_a_name_already_taken_in_any_case(capsys, monkeypatch):
    """On macOS `sgb` would overwrite `SGB`, so the filesystem is asked."""
    monkeypatch.setattr("sys.argv", ["threads"])
    T.cmd_new(new_args())
    capsys.readouterr()
    with pytest.raises(SystemExit):
        T.cmd_new(new_args())
    assert capsys.readouterr().err.startswith("threads: error: already exists: ")


def test_delete_needs_yes(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["threads"])
    T.cmd_new(new_args())
    capsys.readouterr()
    path = T.threads_dir() / "Projects" / "SGB.md"
    with pytest.raises(SystemExit):
        T.cmd_delete(Args(thread="Projects/SGB", yes=False))
    assert capsys.readouterr().err == f"threads: error: refusing to delete {path} without -y\n"
    assert path.exists()

    assert T.cmd_delete(Args(thread="Projects/SGB", yes=True)) == 0
    assert capsys.readouterr().out == f"deleted: {path}\n"
    assert not path.exists()
