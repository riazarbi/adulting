"""The `--help-json` manifest, which `MANUAL.md` and `dev/tools/` are built
from. The CLI tests check that every command answers; these check what the
answer contains, because a description or a choice list that goes missing
here goes missing from the manual and from what the agent is told."""

import json

import pytest

from adulting import helpjson as H
from adulting import vault as V


@pytest.fixture(autouse=True)
def keep_the_program_name():
    """`command_parser` records the name errors start with. These tests build
    parsers for commands that do not exist, so the name is put back."""
    was = V._program
    yield
    V._program = was


def sample_parser():
    parser = V.command_parser('sample', "A sample command.")
    parser.add_argument('--quiet', action='store_true', help="Say less.")
    sub = parser.add_subparsers(dest='subcommand')
    p = sub.add_parser('log', help="Append an entry.")
    p.add_argument('thread', help="Thread name.")
    p.add_argument('note', nargs='?', default='', help="Optional words.")
    p.add_argument('--priority', choices=('H', 'M', 'L'), help="How urgent.")
    p.add_argument('--out', required=True, help="Where to write.")
    return parser


def test_manifest_carries_descriptions_choices_and_shapes():
    manifest = H.parser_to_dict(sample_parser())
    assert manifest['name'] == 'sample'
    assert manifest['description'] == "A sample command."
    assert manifest['flags'] == [
        {'name': '--help-json', 'takes_value': False,
         'description': "Print this command's arguments as JSON, and exit."},
        {'name': '--quiet', 'description': "Say less.", 'takes_value': False},
    ]
    [log] = manifest['subcommands']
    assert log['name'] == 'log'
    # add_parser's `help=` is the description when the subparser has none.
    assert log['description'] == "Append an entry."
    assert log['args'] == [
        {'name': 'thread', 'description': "Thread name.", 'required': True, 'nargs': None},
        {'name': 'note', 'description': "Optional words.", 'required': False, 'nargs': '?'},
    ]
    assert log['flags'] == [
        {'name': '--priority', 'description': "How urgent.",
         'choices': ['H', 'M', 'L'], 'takes_value': True},
        {'name': '--out', 'description': "Where to write.", 'takes_value': True,
         'required': True},
    ]


def test_a_command_with_nothing_but_its_name_still_answers():
    manifest = H.parser_to_dict(V.command_parser('bare', ""))
    assert manifest == {
        'name': 'bare', 'description': '',
        'flags': [{'name': '--help-json', 'takes_value': False,
                   'description': "Print this command's arguments as JSON, and exit."}],
    }
    assert 'args' not in manifest and 'subcommands' not in manifest


def test_the_manifest_survives_json(vault):
    """The manifest is printed as JSON, so it has to be serialisable: a
    `choices` tuple or a Path in it would raise here and nowhere else."""
    assert json.loads(json.dumps(H.parser_to_dict(sample_parser()))) == \
        H.parser_to_dict(sample_parser())
