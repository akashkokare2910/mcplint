# MCPLint CLI image. The MCP server you point --server at is spawned as a
# subprocess *inside this container*, so it (and any language runtime it
# needs, e.g. Node) must be available on the image or mounted in. This base
# image ships Python only — extend it if your server needs something else.
FROM python:3.11-slim AS base

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

WORKDIR /workspace

ENTRYPOINT ["mcplint"]
CMD ["--help"]
