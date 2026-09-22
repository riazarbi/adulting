"""Test harness for the adulting CLIs.

Isolation (see tests/harness.py for the why):

- At session start, os.environ is replaced with an isolated copy: HOME and
  ADULTING_HOME point at a throwaway directory and PATH holds only this
  repo's commands plus system tools. Nothing the suite does can reach
  ~/vault or ~/bin/adulting, even code that reads os.environ at import time.
- Every test then gets its own HOME and ADULTING_HOME under tmp_path.
- At session end, the production vault's adulting-managed files are
  compared with a snapshot taken at session start. Any difference fails
  the run and names the files.

The `vault` fixture builds a clean temp vault per test with the standard
subdirs (notes/, logs/, threads/, people/, .adulting/) pre-created. It
exposes small helpers for adding content and for invoking this repo's CLIs
against the temp vault.

CLIs run as subprocesses so we exercise the same argv/env path the user
hits. Nothing is mocked.
"""

from __future__ import annotations

import json
import os
import pty
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from harness import (PRODUCTION_VAULT, command_path,
                     isolated_env)


@dataclass
class Vault:
    home: Path
    env: dict = field(default_factory=dict)

    # ---- file helpers ----

    def write_thread(self, kind: str, name: str, status: str = "open",
                     category: str = "professional",
                     started: str = "2026-01-01",
                     currency: str | None = None,
                     rate: int | None = None) -> Path:
        """kind in {Projects, Processes, Topics}. Returns the file path."""
        p = self.home / "threads" / kind / f"{name}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        extra = ""
        if currency:
            extra += f"currency: {currency}\n"
        if rate is not None:
            extra += f"rate: {rate}\n"
        kind_value = {"Projects": "project", "Processes": "process", "Topics": "topic"}[kind]
        p.write_text(
            f"---\nstatus: {status}\nkind: {kind_value}\n"
            f"category: {category}\nstarted: {started}\n{extra}---\n\n"
            f"# {name}\n", encoding="utf-8")
        return p

    def write_person(self, name: str, status: str = "open",
                     category: str = "professional",
                     started: str = "2026-01-01") -> Path:
        p = self.home / "people" / f"{name}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            f"---\nstatus: {status}\ncategory: {category}\n"
            f"started: {started}\n---\n\n# {name}\n", encoding="utf-8")
        return p

    def write_note(self, stem: str, body: str, threads: list[str] | None = None,
                   topic: str = "Test note", type_: str = "Log") -> Path:
        """Write notes/<stem>.md with the minimum frontmatter for the
        note_simple file-scope schema. `stem` must match the timestamp
        filename shape (YYYY-MM-DD-HH-MM-SS) or lint will skip it.

        threads: list of wikilink targets like 'Projects/SGB'. Body is
        appended as-is after the frontmatter.
        """
        p = self.home / "notes" / f"{stem}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        fm = ["---", f"topic: {topic}", f"type: {type_}",
              f"timestamp: {stem}"]
        if threads:
            fm.append("threads:")
            for t in threads:
                fm.append(f"  - [[{t}]]")
        fm.append("---")
        p.write_text("\n".join(fm) + "\n\n" + body + ("\n" if not body.endswith("\n") else ""),
                     encoding="utf-8")
        return p

    def write_hours_file(self, kind: str, name: str, entries: list | None = None,
                        currency: str = "ZAR") -> Path:
        """kind in {Projects, Processes, Topics}. entries is a list of entry
        dicts; None writes an empty tracker block."""
        p = self.home / "hours" / kind / f"{name}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"entries": entries or []}, indent=2)
        p.write_text(
            f'---\nthread: "[[{kind}/{name}]]"\ncurrency: {currency}\n---\n\n'
            f"# {name} — hours\n\n```simple-time-tracker\n{payload}\n```\n",
            encoding="utf-8")
        return p

    def entries(self, kind: str, name: str) -> list:
        """Parse the tracker block out of a time file."""
        text = self.read(f"hours/{kind}/{name}.md")
        lines = text.split("\n")
        i = lines.index("```simple-time-tracker")
        j = lines.index("```", i + 1)
        return json.loads("\n".join(lines[i + 1:j])).get("entries", [])

    def write_payments_file(self, kind: str, name: str,
                            payments: list | None = None,
                            currency: str = "ZAR"):
        p = self.home / "payments" / kind / f"{name}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"payments": payments or []}, indent=2)
        p.write_text(
            f'---\nthread: "[[{kind}/{name}]]"\ncurrency: {currency}\n---\n\n'
            f"# {name} — payments\n\n```adulting-payments\n{payload}\n```\n",
            encoding="utf-8")
        return p

    def payments(self, kind: str, name: str) -> list:
        text = self.read(f"payments/{kind}/{name}.md")
        lines = text.split("\n")
        i = lines.index("```adulting-payments")
        j = lines.index("```", i + 1)
        return json.loads("\n".join(lines[i + 1:j])).get("payments", [])

    def write(self, relpath: str, text: str) -> Path:
        """Write a file in the vault, making its folders. Returns the path."""
        p = self.home / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def read(self, relpath: str) -> str:
        return (self.home / relpath).read_text(encoding="utf-8")

    def lines(self, relpath: str) -> list[str]:
        return self.read(relpath).split("\n")

    # ---- CLI helpers ----

    def run(self, *argv: str, cli: str = "tasks", input: str | None = None,
            cwd: Path | None = None) -> subprocess.CompletedProcess:
        """Run a CLI from the repo against this vault. Returns the
        CompletedProcess; stdout/stderr are text-decoded."""
        cmd = [command_path(cli, self.env), *argv]
        return subprocess.run(cmd, capture_output=True, text=True,
                              env=self.env, input=input, cwd=cwd)

    def run_on_a_terminal(self, *argv: str, cli: str, typed: str = "y\n"):
        """Run a CLI with stdin attached to a real pseudo-terminal, with
        `typed` already waiting on it, so a prompt that only appears on a
        terminal would read it. stdout and stderr stay as pipes. A command
        that waits for more input than `typed` times out and fails the test."""
        parent, child = pty.openpty()
        try:
            os.write(parent, typed.encode())
            return subprocess.run([command_path(cli, self.env), *argv], stdin=child,
                                  capture_output=True, text=True, env=self.env, timeout=30)
        finally:
            os.close(child)
            os.close(parent)

    def snapshot(self) -> dict:
        """Every file in the vault and its contents."""
        return {str(p.relative_to(self.home)): p.read_bytes()
                for p in sorted(self.home.rglob("*")) if p.is_file()}


# Isolation happens twice, on purpose. pytest_configure (below) isolates
# os.environ once for the whole session, which covers code that runs at
# import or collection time, before any fixture exists. This fixture then
# gives each test its own HOME and vault, so no two tests share files.
@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Give every test its own HOME and ADULTING_HOME, in os.environ too."""
    env = isolated_env(home=tmp_path / "home", vault=tmp_path / "vault")
    (tmp_path / "home").mkdir(exist_ok=True)
    for key in ("HOME", "ADULTING_HOME", "PATH", "GIT_AUTHOR_NAME",
                "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"):
        monkeypatch.setenv(key, env[key])
    return env


@pytest.fixture
def vault(tmp_path: Path, isolated: dict) -> Vault:
    home = tmp_path / "vault"
    for sub in ("notes", "logs", "threads", "people", "hours", "payments", ".adulting"):
        (home / sub).mkdir(parents=True, exist_ok=True)
    return Vault(home=home, env=dict(isolated))


# ---- session-wide isolation and the production-vault tripwire ----

# The parts of a vault the adulting tools read or write.
MANAGED = ["notes", "logs", "threads", "people", "hours", "payments",
           ".adulting", "buffer.md"]


def fingerprint(vault: Path) -> dict:
    """(size, mtime) of every managed file. Cheap, and catches any write."""
    prints = {}
    for name in MANAGED:
        top = vault / name
        files = [top] if top.is_file() else (top.rglob("*") if top.is_dir() else [])
        for f in files:
            if f.is_file() and f.name != ".DS_Store":
                st = f.stat()
                prints[str(f.relative_to(vault))] = (st.st_size, st.st_mtime_ns)
    return prints


def pytest_configure(config):
    import tempfile
    config._production_before = fingerprint(PRODUCTION_VAULT)
    base = Path(tempfile.mkdtemp(prefix="adulting-tests-"))
    env = isolated_env(home=base / "home", vault=base / "no-vault-selected")
    os.environ.clear()
    os.environ.update(env)


def pytest_sessionfinish(session, exitstatus):
    before = session.config._production_before
    after = fingerprint(PRODUCTION_VAULT)
    changed = sorted(k for k in before.keys() | after.keys()
                     if before.get(k) != after.get(k))
    if changed:
        print(f"\n\nPRODUCTION VAULT CHANGED DURING THE TEST RUN "
              f"({PRODUCTION_VAULT}):")
        for k in changed[:20]:
            print(f"  {k}")
        print("If you (or Obsidian/sync) edited the vault meanwhile, rerun. "
              "Otherwise a test leaked.")
        session.exitstatus = 1
