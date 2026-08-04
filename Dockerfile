# syntax=docker/dockerfile:1
#
# Adulting's runtime + the agent binary. We layer the agent into our own
# debian-slim base because the agent image itself is distroless (no shell,
# no apt), so adding python/taskwarrior on top of it is not possible — we
# pull the binary out and rebuild the runtime ourselves.
#
# The CLIs are bind-mounted at runtime (see docker-compose.yml) so edits to
# the repo on the host flow through immediately, without a rebuild.
#
# The agent base image must exist locally. Build it via the `agent-base`
# profile in the staging vault's compose file:
#
#   docker compose -f /Users/riaz/vault/docker-compose.yml \
#       --profile build build agent-base
#
# or directly:
#
#   docker build -t agent:local \
#       -f /Users/riaz/projects/agent/docker/Dockerfile \
#       /Users/riaz/projects/agent

FROM agent:local AS agent_bin

# sid (not trixie) because trixie ships taskwarrior 2.6.2, which uses the
# legacy flat-file DB and can't read the taskchampion sqlite3 store written
# by 3.x. The host runs 3.x (brew); the container must match or the agent's
# `tasks` calls silently return zero rows against the wrong DB format.
FROM debian:sid-slim

# python3 runs the adulting CLIs (stdlib only). taskwarrior provides the
# `task` binary that `tasks install` copies into ADULTING_HOME/.adulting/bin/.
# ca-certificates is needed for the agent's outbound TLS to the LLM API.
# pandoc + a LaTeX engine for `notes pdf|minutes|agenda` are deferred —
# add later if PDF rendering becomes necessary (adds ~1GB).
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 taskwarrior ca-certificates ripgrep \
 && rm -rf /var/lib/apt/lists/*

COPY --from=agent_bin /usr/local/bin/agent /usr/local/bin/agent

# /opt/adulting is filled at runtime by a bind mount from
# /Users/riaz/projects/adulting on the host. Pre-create the directory so
# the mount has a target and so PATH resolves cleanly even if the mount is
# ever omitted (the dir is just empty in that case).
# /state and /workspace match the agent base image's layout — bind mounts
# land there and need to be writable by the container UID.
RUN mkdir -p /opt/adulting /state /workspace && chmod 0777 /state /workspace

# Prepend /opt/adulting to PATH so `notes`, `tasks`, `lint`, etc. resolve
# directly. ADULTING_HOME points at the bind-mounted vault.
ENV PATH=/opt/adulting:$PATH \
    ADULTING_HOME=/vault \
    ADULTING_TASK_BIN=/usr/bin/task \
    AGENT_STATE_DIR=/state \
    HOME=/tmp

WORKDIR /workspace
USER 1000:0
ENTRYPOINT ["/usr/local/bin/agent"]
