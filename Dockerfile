# syntax=docker/dockerfile:1
#
# Derives from agent-offline:local — the agent project's image — and adds
# the runtime dependencies the adulting CLIs need. The CLIs themselves are
# bind-mounted at runtime (see docker-compose.yml) so edits to the repo on
# the host flow through immediately, without a rebuild.
#
# The base image must already exist locally. Build it via the `agent-base`
# profile in /Users/riaz/projects/agent/docker-compose.yml:
#
#   docker compose -f /Users/riaz/projects/agent/docker-compose.yml \
#       --profile build build agent-base
#
# or directly:
#
#   docker build -t agent-offline:local \
#       -f /Users/riaz/projects/agent/docker/Dockerfile \
#       /Users/riaz/projects/agent

FROM agent-offline:local

USER root

# python3 runs the adulting CLIs (stdlib only). taskwarrior provides the
# `task` binary that `tasks install` copies into ADULTING_HOME/.adulting/bin/.
# pandoc + a LaTeX engine for `notes pdf|minutes|agenda` are deferred —
# add later if PDF rendering becomes necessary (adds ~1GB).
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 taskwarrior \
 && rm -rf /var/lib/apt/lists/*

# /opt/adulting is filled at runtime by a bind mount from
# /Users/riaz/projects/adulting on the host. Pre-create the directory so
# the mount has a target and so PATH resolves cleanly even if the mount is
# ever omitted (the dir is just empty in that case).
RUN mkdir -p /opt/adulting

# Prepend /opt/adulting to the inherited PATH so `notes`, `tasks`, `lint`,
# etc. resolve directly. ADULTING_HOME points at the bind-mounted vault.
ENV PATH=/opt/adulting:$PATH \
    ADULTING_HOME=/vault

USER 1000:0
