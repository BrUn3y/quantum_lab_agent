FROM python:3.13-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.7.15 /uv /bin/

ENV UV_LINK_MODE=copy \
    PRODUCTION_MODE=true

ADD . /app
WORKDIR /app

RUN uv sync --no-cache --locked --link-mode copy

ENV PRODUCTION_MODE=True \
    PATH="/app/.venv/bin:$PATH" \
    HOME=/tmp \
    LAB_HOST=0.0.0.0 \
    DEVELOPER_HOST=host.docker.internal \
    STATUS_HOST=host.docker.internal \
    COMPUTING_HOST=host.docker.internal

CMD ["uv", "run", "--no-sync", "server"]
