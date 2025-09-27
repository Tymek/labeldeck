#!/usr/bin/env bash
set -euo pipefail

APP_HOME="/app"
LOG_PREFIX="[labeldeck]"

info() { echo "${LOG_PREFIX} $*"; }
warn() { echo "${LOG_PREFIX} WARNING: $*" >&2; }

# If requirements.txt present in mounted app directory and requirements hash not cached, install.
if [ -f "${APP_HOME}/requirements.txt" ]; then
  if [ ! -f "/tmp/.app-reqs.sha256" ] || ! sha256sum -c /tmp/.app-reqs.sha256 >/dev/null 2>&1; then
    info "Installing requirements from ${APP_HOME}/requirements.txt"
    pip install --no-cache-dir -r "${APP_HOME}/requirements.txt"
    sha256sum "${APP_HOME}/requirements.txt" > /tmp/.app-reqs.sha256
  else
    info "Requirements unchanged; skipping install"
  fi
fi

# Determine target command logic:
# Priority:
#  1. If arguments passed to container (after entrypoint) -> run them.
#  2. If start.sh exists in /app -> run it.
#  3. If main.py exists in /app -> python main.py
#  4. Fallback: provided CMD (already in "$@") or message.

if [ $# -gt 0 ]; then
  info "Executing provided container arguments: $*"
  exec "$@"
fi

if [ -x "${APP_HOME}/start.sh" ]; then
  info "Running start.sh"
  exec "${APP_HOME}/start.sh"
fi

if [ -f "${APP_HOME}/main.py" ]; then
  info "Running main.py"
  exec python "${APP_HOME}/main.py"
fi

info "No application found. Sleeping (override by passing a command)."
exec sleep infinity
