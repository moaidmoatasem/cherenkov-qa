# Stage 1: Build the React UI
FROM node:20-slim AS ui-build
WORKDIR /app/cherenkov/web/ui
COPY cherenkov/web/ui/package*.json ./
RUN npm install
COPY cherenkov/web/ui/ ./
RUN npx vite build

# Stage 2: Main CLI Engine
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Node.js (for Playwright browsers + openapi-typescript)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python package (reads pyproject.toml; registers `cherenkov` CLI entrypoint)
COPY pyproject.toml README.md ./
COPY cherenkov/ ./cherenkov/
RUN pip install --no-cache-dir ".[dev]"

# Playwright browsers
RUN pip install --no-cache-dir playwright && npx playwright install --with-deps chromium

# Copy remaining project files (stubs, demos, docs)
COPY . /app

# Pull in built UI
COPY --from=ui-build /app/cherenkov/web/ui/dist /app/cherenkov/web/ui/dist

ENTRYPOINT ["cherenkov"]
CMD ["--help"]
