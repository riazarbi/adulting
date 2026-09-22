"""The operator's commands, in the order the manual presents them.

The one list the dev scripts share. tests/dev/test_commands.py checks it
against the console scripts in pyproject.toml, so a new command cannot be
left out of the manual or the CI checks.
"""

COMMANDS = ['tasks', 'notes', 'search', 'threads', 'people', 'hours',
            'payments', 'buffer', 'lint', 'commit']
