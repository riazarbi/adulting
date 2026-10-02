# syntax=docker/dockerfile:1
#
# Adulting's runtime + the agent binary. We layer the agent into our own
# debian-slim base because the agent image itself is distroless (no shell,
# no apt), so adding python on top of it is not possible — we pull the
# binary out and rebuild the runtime ourselves.
#
# The adulting package is installed into a venv at build time, so the image
# is self-contained: the ten commands are its own console scripts and the
# container needs nothing mounted at /opt to run them. Changing the CLI means
# rebuilding (`docker compose up -d --build`), which is quick — the package
# has no third-party dependencies to fetch.
#
# The agent is published, so there is nothing to build first — the build
# pulls it. For a private package, authenticate once:
#
#   echo $GITHUB_TOKEN | docker login ghcr.io -u riazarbi --password-stdin
#
# `:latest` moves. Pin a release tag or a digest when a rebuild has to
# produce the same image twice:
#
#   FROM ghcr.io/riazarbi/agent@sha256:<digest> AS agent_bin

FROM ghcr.io/riazarbi/agent:latest AS agent_bin

# sid was chosen when the image still needed taskwarrior 3.x; it no longer
# does, but sid is a current, working base and changing it is a separate
# decision from this refactor.
# The package is installed in its own stage so that pip, ensurepip and
# setuptools do not end up in the shipped image. `--copies` gives the venv a
# real interpreter binary rather than a symlink into this stage, which the
# final stage does not have; the stdlib it loads comes from the identical
# base below.
FROM debian:sid-slim AS build

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-venv python3-setuptools \
 && rm -rf /var/lib/apt/lists/*

# Only what the build needs: `readme` in pyproject.toml points at README.md,
# so the install fails without it. Tests, stories and the host's .venv stay
# out of the image.
COPY pyproject.toml README.md /src/
COPY src /src/src

# --no-build-isolation keeps the build off PyPI: the backend comes from
# apt's setuptools, which a venv cannot see on its own, so PYTHONPATH points
# at Debian's dist-packages for this one command rather than making the
# shipped venv a --system-site-packages one. There are no runtime
# dependencies, so this is the whole install.
RUN python3 -m venv --copies /opt/venv \
 && PYTHONPATH=/usr/lib/python3/dist-packages \
    /opt/venv/bin/pip install --no-cache-dir --no-build-isolation /src


FROM debian:sid-slim

# python3 runs the adulting package (standard library only). taskwarrior is
# gone: task state lives in the notes themselves and no command shells out to
# `task` any more.
# ca-certificates is needed for the agent's outbound TLS to the LLM API.
# git backs the `commit` CLI (~50MB with its deps) — the vault's only sync
# mechanism, so the agent cannot record its work without it.
# pandoc + a LaTeX engine for `notes pdf|minutes|agenda` are deferred —
# add later if PDF rendering becomes necessary (adds ~1GB). Without them
# those three subcommands write the markdown and report that pandoc is
# missing; every other command is unaffected.
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 ca-certificates git ripgrep \
 && rm -rf /var/lib/apt/lists/*

COPY --from=agent_bin /usr/local/bin/agent /usr/local/bin/agent

# /state and /workspace match the agent base image's layout — bind mounts
# land there and need to be writable by the container UID.
RUN mkdir -p /state /workspace && chmod 0777 /state /workspace

# The venv, holding the package and its ten console scripts. /opt/venv, not
# /opt/adulting: the old image had the host repo bind-mounted at the latter,
# and a mount left behind in a compose file would otherwise shadow the
# install and break every command.
COPY --from=build /opt/venv /opt/venv

# One command run at build time, so a broken install fails the build rather
# than the agent's first tool call.
RUN /opt/venv/bin/lint --help-json > /dev/null

# The agent tool definitions and skills ride with the commands they describe,
# so they cannot drift apart from them. The entrypoint installs both into the
# agent's state directory on every start; see container/entrypoint.sh for
# what that means for a file edited by hand.
#
# The system prompt is deliberately not here. Tools and skills are
# capabilities and compose — one file or folder each, installed side by side
# with another image's — while a prompt is the agent's identity. An overlay
# agent can be general-purpose and still load these.
COPY dev/tools /opt/tools
COPY agent/skills /opt/skills
COPY container/entrypoint.sh /usr/local/bin/adulting-entrypoint

# PATH puts the venv first, so `tasks` and friends are the installed scripts.
# No PYTHONPATH: there is nothing to point it at.
ENV PATH=/opt/venv/bin:$PATH \
    ADULTING_HOME=/vault \
    AGENT_STATE_DIR=/state \
    HOME=/tmp

# Git identity for `commit save`. Set explicitly because git otherwise
# derives an author silently from the container UID and hostname — with
# HOME=/tmp there is no gitconfig to read, so commits would land as
# `1000@<container-id>` with no error. Both AUTHOR and COMMITTER are
# needed: setting only AUTHOR still leaves the committer auto-derived.
ENV GIT_AUTHOR_NAME=agent \
    GIT_AUTHOR_EMAIL=agent@sprite.local \
    GIT_COMMITTER_NAME=agent \
    GIT_COMMITTER_EMAIL=agent@sprite.local

WORKDIR /workspace
USER 1000:0
ENTRYPOINT ["/usr/local/bin/adulting-entrypoint"]
