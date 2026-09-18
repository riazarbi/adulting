# syntax=docker/dockerfile:1
#
# Adulting's runtime + the agent binary. We layer the agent into our own
# debian-slim base because the agent image itself is distroless (no shell,
# no apt), so adding python on top of it is not possible — we pull the
# binary out and rebuild the runtime ourselves.
#
# The source is bind-mounted at runtime (see docker-compose.yml) so edits to
# the repo on the host flow through immediately, without a rebuild. The
# commands are wrappers around `python3 -m adulting.<name>`; see below.
#
# The agent base image must exist locally. Build it via the `agent-base`
# profile in the staging vault's compose file:
#
#   docker compose -f /home/riaz/vault/docker-compose.yml \
#       --profile build build agent-base
#
# or directly:
#
#   docker build -t agent:local \
#       -f /home/riaz/projects/agent/docker/Dockerfile \
#       /home/riaz/projects/agent

FROM agent:local AS agent_bin

# sid was chosen when the image still needed taskwarrior 3.x; it no longer
# does, but sid is a current, working base and changing it is a separate
# decision from this refactor.
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

# /opt/adulting is filled at runtime by a bind mount from
# /home/riaz/projects/adulting on the host. Pre-create the directory so
# the mount has a target and so PATH resolves cleanly even if the mount is
# ever omitted (the dir is just empty in that case).
# /state and /workspace match the agent base image's layout — bind mounts
# land there and need to be writable by the container UID.
RUN mkdir -p /opt/adulting /state /workspace && chmod 0777 /state /workspace

# The commands are console scripts of the `adulting` package, which a pipx or
# pip install would create. This image cannot install it: the source arrives
# at runtime as a bind mount, after the build. So each command gets a wrapper
# that runs its module, and PYTHONPATH points at the mounted source. Edits on
# the host still take effect immediately, with no rebuild.
RUN for cmd in tasks notes search threads people hours payments buffer lint commit; do \
      printf '#!/bin/sh\nexec python3 -m adulting.%s "$@"\n' "$cmd" > /usr/local/bin/$cmd; \
      chmod 0755 /usr/local/bin/$cmd; \
    done

# ADULTING_HOME points at the bind-mounted vault.
ENV PYTHONPATH=/opt/adulting/src \
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
ENTRYPOINT ["/usr/local/bin/agent"]
