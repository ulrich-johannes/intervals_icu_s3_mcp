# Two-stage build. vendor/intervals-icu-mcp is a git submodule and must be
# checked out (git submodule update --init) before `docker build` runs --
# see SPECIFICATION.md §03/§09/§11 open item #1 on whether Fly's native
# GitHub-integration builder does this for us automatically.
FROM python:3.11-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY vendor/ ./vendor/

RUN uv sync --frozen --no-dev

FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/vendor /app/vendor
COPY src/ ./src/
COPY pyproject.toml ./

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).status==200 else 1)"

EXPOSE 8080

ENTRYPOINT ["python", "-m", "intervals_icu_s3_mcp.server", "--host", "0.0.0.0"]
