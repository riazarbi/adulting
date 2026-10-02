#!/bin/sh
# Install the tool definitions this image carries, then hand over to the agent.
#
# The agent seeds its `tools/` directory only if the directory is missing, and
# never touches it again. A long-lived state dir therefore keeps whatever
# generation of the definitions was first copied into it — which is how the
# vault ended up describing commands that prompt on stdin, months after they
# stopped doing so, and missing `notes` entirely.
#
# Shipping them in the image means the definitions and the commands they
# describe arrive as one artifact and cannot disagree. Files this image ships
# are overwritten on every start: the image is the source of truth, so a hand
# edit to one of them does not survive a restart. Anything else in the
# directory — the agent's own builtins, tools from elsewhere — is left alone.
#
# The agent watches the directory, so these writes register within its
# debounce window; nothing below needs a restart to take effect.

set -eu

src=/opt/tools
dest="${AGENT_STATE_DIR:-/state}/tools"
# Overridable only so this script can be exercised outside the image.
agent="${AGENT_BIN:-/usr/local/bin/agent}"

install_definitions() {
    if ! mkdir -p "$dest" 2>/dev/null; then
        printf 'adulting: warning: cannot create %s; tool definitions left alone\n' \
            "$dest" >&2
        return 0
    fi
    if ! cp "$src"/*.json "$dest"/ 2>/dev/null; then
        printf 'adulting: warning: cannot write %s; tool definitions left alone\n' \
            "$dest" >&2
        return 0
    fi
    printf 'adulting: installed %s tool definition(s) into %s\n' \
        "$(ls -1 "$src"/*.json | wc -l | tr -d ' ')" "$dest"

    # A definition naming a command this image does not have would have the
    # model call a binary that is not there. Said, not deleted: the directory
    # is shared with whatever else drops tools into it, and a definition for
    # someone else's binary is not ours to remove.
    for definition in "$dest"/*.json; do
        command_name=$(sed -n \
            's/.*"command"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
            "$definition" | head -1)
        if [ -n "$command_name" ]; then
            if ! command -v "$command_name" >/dev/null 2>&1; then
                printf 'adulting: warning: %s names %s, which is not on PATH\n' \
                    "$(basename "$definition")" "$command_name" >&2
            fi
        fi
    done
}

if [ -d "$src" ]; then
    install_definitions
fi

exec "$agent" "$@"
