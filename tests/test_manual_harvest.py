"""Tests for dev/manual-harvest.

The harvester is a developer tool, but its output is the sole input to the
generated MANUAL.md and the agent tool definitions. A fact it drops is a fact
that silently never reaches either — there is no downstream check that would
notice, which is what makes these worth pinning.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HARVEST = REPO / "dev" / "manual-harvest"


def harvest(fmt="md"):
    r = subprocess.run([sys.executable, str(HARVEST), "--format", fmt],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_subsections_of_a_harvested_section_survive():
    """A `###` under a harvested `##` must come through with its parent.

    Splitting on level 3 made each subsection a section in its own right, so
    it was dropped for not being in README_SECTIONS and its parent was
    truncated at that point. The notes/logs/hours boundary vanished this way.
    """
    corpus = harvest()
    assert "### Conceptual model" in corpus
    assert "Notes, logs and hours" in corpus, \
        "a subsection of Conceptual model was dropped from the corpus"


def test_every_declared_readme_section_is_present():
    corpus = harvest()
    src = HARVEST.read_text()
    declared = src.split("README_SECTIONS = [")[1].split("]")[0]
    for name in [x.strip().strip("'\"") for x in declared.split(",")]:
        if name:
            assert f"### {name}" in corpus, f"README section {name!r} missing"


def test_every_operator_tool_appears():
    data = json.loads(harvest("json"))
    for tool in data["operator_tools"]:
        assert any(t["name"] == tool for t in data["tools"]), tool
        manifest = next(t for t in data["tools"] if t["name"] == tool)
        assert manifest["help_json"], f"{tool} has an empty manifest"


def test_harvest_is_deterministic():
    """Two runs over an unchanged tree must be byte-identical — the whole
    no-pollution argument for the generated artefacts rests on it."""
    assert harvest() == harvest()
