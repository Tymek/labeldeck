## Multi-stage Dockerfile for labeldeck
## Goals:
##  - Fast iterative dev on Raspberry Pi by building once on faster machine
##  - Allow overriding / extending the app at runtime by mounting a volume with custom code / scripts
##  - Provide minimal base with printing related system deps (cups, libusb) while keeping image slim
##  - Support optional Python dependencies via requirements.txt (ARG) and runtime dynamic installs

ARG PYTHON_VERSION=3.13-slim
FROM python:${PYTHON_VERSION} AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/app

WORKDIR ${APP_HOME}

## Install system packages (adjust as needed for specific printer drivers)
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      libcups2-dev cups-client libusb-1.0-0 wget bash ca-certificates \
      imagemagick && \
    rm -rf /var/lib/apt/lists/*## Optional: allow build-time requirements injection
ARG REQUIREMENTS=requirements.txt
# Copy requirements only if file exists at build context (Docker does not support conditional COPY directly).
# Strategy: first try copying a known fallback empty file if user didn't provide one.
RUN echo "# empty" > /tmp/empty-reqs.txt
COPY ${REQUIREMENTS} /tmp/requirements.txt
RUN if [ -s /tmp/requirements.txt ]; then \
			echo "Installing build-time Python dependencies from ${REQUIREMENTS}" && \
			pip install --no-cache-dir -r /tmp/requirements.txt ; \
		else \
			echo "No build-time requirements provided (file empty)"; \
		fi || true

## Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

## Default healthcheck: ensure python responds
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import sys; sys.exit(0)" || exit 1

VOLUME ["${APP_HOME}"]

## Default command can be overridden; entrypoint decides what to run.
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-c", "print('labeldeck base container - mount your app code to /app')"]
