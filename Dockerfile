# Stage 1: Build the React UI
FROM node:20-slim AS ui-build
WORKDIR /app/cherenkov/web/ui
COPY cherenkov/web/ui/package*.json ./
RUN npm install
COPY cherenkov/web/ui/ ./
RUN npx vite build

# Stage 2: Main CLI Engine
FROM python:3.14-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python package
COPY pyproject.toml README.md ./
COPY cherenkov/ ./cherenkov/
RUN pip install --no-cache-dir ".[dev]"

# Playwright browsers
RUN pip install --no-cache-dir playwright && npx playwright install --with-deps chromium

# Copy remaining project files
COPY . /app

# Pull in built UI
COPY --from=ui-build /app/cherenkov/web/ui/dist /app/cherenkov/web/ui/dist

# Non-root user for security
RUN adduser --system --group --uid 1000 cherenkov && chown -R cherenkov:cherenkov /app
USER cherenkov

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)" || exit 1

ENTRYPOINT ["cherenkov"]
CMD ["--help"]
