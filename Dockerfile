# QuickCall SuperTrace Dockerfile
#
# Build: docker build -t quickcall-supertrace .
# Run:   docker run -p 7845:7845 -v ~/.claude/projects:/root/.claude/projects:ro quickcall-supertrace

FROM node:20-slim AS frontend-builder

WORKDIR /app/web
COPY packages/web/package*.json ./
RUN npm ci
COPY packages/web/ ./
RUN npm run build

FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy Python package
COPY packages/server/pyproject.toml packages/server/uv.lock ./
RUN uv sync --frozen --no-dev

# Copy source code
COPY packages/server/src ./src

# Copy built frontend
COPY --from=frontend-builder /app/web/dist ./src/quickcall_supertrace/static

# Expose port
EXPOSE 7845

# Run server
ENV QUICKCALL_SUPERTRACE_HOST=0.0.0.0
ENV QUICKCALL_SUPERTRACE_PORT=7845

CMD ["uv", "run", "quickcall-supertrace"]
