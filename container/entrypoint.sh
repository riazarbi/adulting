#!/bin/sh
# Install the tool definitions and skills this image carries, then hand over
# to the agent.
#
# The agent seeds its state directory only if a directory is missing, and
# never touches it again. A long-lived state dir therefore keeps whatever
# generation was first copied into it — which is how the vault ended up
# describing commands that prompt on stdin, months after they stopped doing
# so, and missing `notes` entirely.
#
# Shipping them in the image means the definitions, the skills and the
# commands they describe arrive as one artifact and cannot disagree. Files
# this image ships are overwritten on every start: the image is the source of
# truth, so a hand edit to one of them does not survive a restart. Anything
# else in those directories — the agent's own builtins, tools and skills from
# another image — is left alone, and nothing is ever deleted: an overlay that
# stops being run leaves its files behind, to be pruned by hand.
#
# The system prompt is not installed. Tools and skills are capabilities and
# compose; a prompt is the agent's identity, and belongs to whoever runs it.
#
# Both tiers start at once and write the same shared directories, and the
# agent watches them for changes, so each file is written to a temporary name
# and renamed into place. A rename is atomic, so a watcher never reads half a
# file.

set -eu

state="${AGENT_STATE_DIR:-/state}"
# These three are overridable only so this script can be exercised outside
# the image; inside it they are always the defaults.
agent="${AGENT_BIN:-/usr/local/bin/agent}"
tools_src="${ADULTING_TOOLS_DIR:-/opt/tools}"
skills_src="${ADULTING_SKILLS_DIR:-/opt/skills}"

# install <source dir> <destination dir> <what to call them>
#
# Copies files, and whole directories one level down (a skill is a folder
# holding SKILL.md), overwriting what it ships and leaving the rest.
install() {
    src=$1
    dest=$2
    noun=$3

    if ! mkdir -p "$dest" 2>/dev/null; then
        printf 'adulting: warning: cannot create %s; %s left alone\n' \
            "$dest" "$noun" >&2
        return 0
    fi

    # Asked once rather than failing per file: a read-only mount should say
    # so in one line, not once for every definition it carries.
    if ! touch "$dest/.adulting-probe" 2>/dev/null; then
        printf 'adulting: warning: cannot write %s; %s left alone\n' \
            "$dest" "$noun" >&2
        return 0
    fi
    rm -f "$dest/.adulting-probe"

    count=0
    for item in "$src"/*; do
        [ -e "$item" ] || continue
        name=$(basename "$item")
        if [ -d "$item" ]; then
            # A directory cannot be renamed over a directory that exists, so
            # the old one goes after the new one is fully staged beside it.
            if cp -R "$item" "$dest/.$name.incoming" 2>/dev/null \
               && rm -rf "$dest/$name" 2>/dev/null \
               && mv "$dest/.$name.incoming" "$dest/$name" 2>/dev/null; then
                count=$((count + 1))
            else
                rm -rf "$dest/.$name.incoming" 2>/dev/null || true
                printf 'adulting: warning: cannot install %s into %s\n' \
                    "$name" "$dest" >&2
            fi
        elif cp "$item" "$dest/.$name.incoming" 2>/dev/null \
             && mv "$dest/.$name.incoming" "$dest/$name" 2>/dev/null; then
            count=$((count + 1))
        else
            rm -f "$dest/.$name.incoming" 2>/dev/null || true
            printf 'adulting: warning: cannot install %s into %s\n' \
                "$name" "$dest" >&2
        fi
    done
    printf 'adulting: installed %s %s into %s\n' "$count" "$noun" "$dest"
}

report_missing_commands() {
    for definition in "$1"/*.json; do
        [ -e "$definition" ] || continue
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

if [ -d "$tools_src" ]; then
    install "$tools_src" "$state/tools" "tool definition(s)"
    # A definition naming a command this image does not have would have the
    # model call a binary that is not there. Said, not deleted: the directory
    # is shared with whatever else drops tools into it, and a definition for
    # someone else's binary is not ours to remove.
    report_missing_commands "$state/tools"
fi

if [ -d "$skills_src" ]; then
    install "$skills_src" "$state/skills" "skill(s)"
fi

exec "$agent" "$@"
