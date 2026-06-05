# Stage 1: Build the React UI
FROM node:20-slim AS ui-build
WORKDIR /app/cherenkov/web/ui
COPY cherenkov/web/ui/package*.json ./
RUN npm install
COPY cherenkov/web/ui/ ./
RUN npx vite build

# Stage 2: Main CLI Engine
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (for Playwright and openapi-typescript)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and its browsers
RUN pip install --no-cache-dir playwright
RUN npx playwright install --with-deps

# Copy application source
COPY . /app

# Copy the built UI into the application
COPY --from=ui-build /app/cherenkov/web/ui/dist /app/cherenkov/web/ui/dist

# Set the entrypoint
ENTRYPOINT ["python", "cherenkov.py"]
