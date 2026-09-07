"""Test harness for the adulting CLIs.

The `vault` fixture builds a clean temp vault per test, pointed at by
ADULTING_HOME, with the standard subdirs (notes/, logs/, threads/,
people/, .adulting/) pre-created. It exposes small helpers for adding
content and for invoking the in-repo CLIs (`tasks`, `lint`, `buffer`)
against the temp vault.

CLIs run as subprocesses so we exercise the same argv/env path the user
hits — no monkey-patching of internal functions.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


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
        p.write_text(
            f"---\nstatus: {status}\nkind: {kind.rstrip('s').lower()}\n"
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
        import json as _json
        p = self.home / "hours" / kind / f"{name}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = _json.dumps({"entries": entries or []}, indent=2)
        p.write_text(
            f'---\nthread: "[[{kind}/{name}]]"\ncurrency: {currency}\n---\n\n'
            f"# {name} — hours\n\n```simple-time-tracker\n{payload}\n```\n",
            encoding="utf-8")
        return p

    def entries(self, kind: str, name: str) -> list:
        """Parse the tracker block out of a time file."""
        import json as _json
        text = self.read(f"hours/{kind}/{name}.md")
        lines = text.split("\n")
        i = lines.index("```simple-time-tracker")
        j = lines.index("```", i + 1)
        return _json.loads("\n".join(lines[i + 1:j])).get("entries", [])

    def write_payments_file(self, kind: str, name: str,
                            payments: list | None = None,
                            currency: str = "ZAR"):
        import json as _json
        p = self.home / "payments" / kind / f"{name}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = _json.dumps({"payments": payments or []}, indent=2)
        p.write_text(
            f'---\nthread: "[[{kind}/{name}]]"\ncurrency: {currency}\n---\n\n'
            f"# {name} — payments\n\n```adulting-payments\n{payload}\n```\n",
            encoding="utf-8")
        return p

    def payments(self, kind: str, name: str) -> list:
        import json as _json
        text = self.read(f"payments/{kind}/{name}.md")
        lines = text.split("\n")
        i = lines.index("```adulting-payments")
        j = lines.index("```", i + 1)
        return _json.loads("\n".join(lines[i + 1:j])).get("payments", [])

    def read(self, relpath: str) -> str:
        return (self.home / relpath).read_text(encoding="utf-8")

    def lines(self, relpath: str) -> list[str]:
        return self.read(relpath).split("\n")

    # ---- CLI helpers ----

    def run(self, *argv: str, cli: str = "tasks", check: bool = False,
            input: str | None = None) -> subprocess.CompletedProcess:
        """Run a CLI from the repo against this vault. Returns the
        CompletedProcess; stdout/stderr are text-decoded."""
        cmd = [sys.executable, str(REPO_ROOT / cli), *argv]
        return subprocess.run(cmd, capture_output=True, text=True,
                              env=self.env, check=check, input=input)


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Vault:
    home = tmp_path / "vault"
    for sub in ("notes", "logs", "threads", "people", "hours", "payments", ".adulting"):
        (home / sub).mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["ADULTING_HOME"] = str(home)
    return Vault(home=home, env=env)
