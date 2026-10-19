"""Tests for dev/tools-check, the gate over the agent tool definitions.

The definitions are written by a model and committed. `tools-check` already
compared their *shape* with the code; these cover the check that compares a
claim in the prose with the truth — that nothing in this package prompts.

The stale sentences below are the real ones, taken from the definitions as
they stood before they were regenerated on 2026-09-23. They survived six
rounds of review because nothing read them.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def load(path):
    """Import a dev script that has no .py suffix, as a module."""
    spec = importlib.util.spec_from_loader(
        "tools_check", importlib.machinery.SourceFileLoader("tools_check", str(path)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHECK = load(REPO / "dev" / "tools-check")
claims = lambda text: list(CHECK.interactivity_claims(text))   # noqa: E731


@pytest.mark.parametrize("stale, reported", [
    ("Never call `log` without THREAD — with no thread it enters interactive "
     "capture and reads from stdin.",
     "Never call `log` without THREAD — with no thread it enters interactive "
     "capture and reads from stdin."),
    # Reported by the clause, not the whole line: that is the part to fix.
    ("`new` prompts on stdin for any of --name and --category not supplied; "
     "always pass both.",
     "`new` prompts on stdin for any of --name and --category not supplied;"),
    ("delete: -y skips the confirmation prompt.",
     "delete: -y skips the confirmation prompt."),
    ("Run it interactively to pick a note.",
     "Run it interactively to pick a note."),
])
def test_a_claim_that_a_command_prompts_is_reported(stale, reported):
    assert claims(stale) == [reported]


@pytest.mark.parametrize("true_statement", [
    "Nothing prompts and nothing opens an application.",
    "No command prompts; every value comes from a flag.",
    "It never reads stdin.",
    "Without -y it refuses and exits 1, rather than prompting.",
    "delete is permanent. Without -y it refuses and exits 1.",
])
def test_saying_that_it_does_not_prompt_is_not_a_claim_that_it_does(true_statement):
    """The denial is the sentence these definitions should carry, so a check
    that flagged it would make the right wording unwriteable."""
    assert claims(true_statement) == []


def test_only_the_offending_sentence_is_reported():
    """The message has to name the sentence to fix, not the whole file."""
    description = ("Track consulting hours.\n\n"
                   "log THREAD DESCRIPTION — append an entry.\n"
                   "Never call `log` without THREAD — it enters interactive capture.\n"
                   "rm is permanent and needs -y.\n")
    assert claims(description) == [
        "Never call `log` without THREAD — it enters interactive capture."]


def test_the_committed_definitions_make_no_such_claim():
    """The four that did — hours, payments, people, threads — described the
    pre-port commands, which told an agent to avoid a command that is safe."""
    for path in sorted((REPO / "dev" / "tools").glob("*.json")):
        description = json.loads(path.read_text(encoding="utf-8"))["description"]
        assert claims(description) == [], path.name
