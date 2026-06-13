# Dry-run-only HTTP surface for the d3HL infrastructure orchestrator.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

ENV UV_CACHE_DIR=/tmp/uv-cache \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    D3HL_API_HOST=0.0.0.0 \
    D3HL_API_PORT=8000 \
    # Treat the read-only, host-owned workspace mount as safe for git.
    GIT_CONFIG_COUNT=1 \
    GIT_CONFIG_KEY_0=safe.directory \
    GIT_CONFIG_VALUE_0=*

# git is needed by the repo-state adapter to read target-repo git status/log.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --frozen --no-dev

EXPOSE 8000

# Serves the dry-run-only FastAPI app. Mount the host workspace read-only at
# /home/d3/Github so the container can read target-repo state (see docker-compose.yml).
CMD ["uv", "run", "--no-dev", "serve"]
