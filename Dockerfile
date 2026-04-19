# ─── Stage 1: Build frontend ─────────────────────────────────────────────────
FROM node:20-alpine AS frontend-build

WORKDIR /build/web

# Install dependencies first (cached layer)
COPY web/package.json web/package-lock.json* ./
RUN npm ci

# Copy source and build
COPY web/ ./
RUN npm run build

# ─── Stage 2: Production image ───────────────────────────────────────────────
FROM python:3.11-slim AS production

# System deps (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire football_intel package
COPY . ./football_intel/

# Copy built frontend from stage 1 into the package location
COPY --from=frontend-build /build/web/dist ./football_intel/web/dist/

# Copy example config as reference (real config is volume-mounted at runtime)
# (already included via the COPY . above, but make it explicit)

# Create data and logs directories
RUN mkdir -p /app/football_intel/data /app/football_intel/logs

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the API server
CMD ["uvicorn", "football_intel.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
