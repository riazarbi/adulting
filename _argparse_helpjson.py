"""Walk an argparse parser tree, emit a structured JSON manifest.

Usage in any tool:
    from _argparse_helpjson import emit_helpjson_if_requested
    parser = argparse.ArgumentParser(...)
    ...
    emit_helpjson_if_requested(parser)  # exits 0 if --help-json was passed
    args = parser.parse_args()

Output shape:
    {
      "name": "tasks",
      "description": "...",
      "args": [{"name": "...", "description": "...", "required": bool, "nargs": str|None}, ...],
      "flags": [{"name": "--quiet", "description": "...", "choices": [...]|None}, ...],
      "subcommands": [ <recursive> ]
    }
"""

import argparse
import json
import sys


def _action_to_arg(action):
    return {
        "name": action.dest,
        "description": action.help or "",
        "required": action.nargs not in ('?', '*'),
        "nargs": action.nargs if action.nargs is not None else None,
    }


def _action_to_flag(action):
    out = {
        "name": action.option_strings[0],
        "description": action.help or "",
    }
    if action.choices:
        out["choices"] = list(action.choices)
    if isinstance(action, argparse._StoreTrueAction) or isinstance(action, argparse._StoreFalseAction):
        out["takes_value"] = False
    else:
        out["takes_value"] = True
    if action.required:
        out["required"] = True
    return out


def parser_to_dict(parser, name=None):
    args = []
    flags = []
    subcommands = []
    for action in parser._actions:
        if isinstance(action, argparse._HelpAction):
            continue
        if isinstance(action, argparse._SubParsersAction):
            # `add_parser('name', help='...')` stores the help text on a
            # separate action in _choices_actions, not on the subparser
            # itself. Pull it out so we can use it as fallback description.
            help_map = {ca.dest: (ca.help or "") for ca in action._choices_actions}
            for sub_name, sub_parser in action.choices.items():
                if any(s.get("_id") == id(sub_parser) for s in subcommands):
                    continue
                sub = parser_to_dict(sub_parser, name=sub_name)
                if not sub.get("description") and sub_name in help_map:
                    sub["description"] = help_map[sub_name]
                sub["_id"] = id(sub_parser)
                subcommands.append(sub)
            continue
        if action.option_strings:
            flags.append(_action_to_flag(action))
        else:
            args.append(_action_to_arg(action))
    out = {
        "name": name or parser.prog,
        "description": (parser.description or "").strip(),
    }
    if args:
        out["args"] = args
    if flags:
        out["flags"] = flags
    if subcommands:
        for s in subcommands:
            s.pop("_id", None)
        out["subcommands"] = subcommands
    return out


def emit_helpjson_if_requested(parser):
    """Check sys.argv for --help-json. If present, dump JSON and exit 0."""
    if '--help-json' in sys.argv:
        print(json.dumps(parser_to_dict(parser), indent=2))
        sys.exit(0)
