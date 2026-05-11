# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies needed to build Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a separate layer for caching
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Runtime stage 
FROM python:3.12-slim

WORKDIR /app

# Git is required at runtime for cloning repositories
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY api.py main.py auth.py ./
COPY analyzer/ analyzer/
COPY utils/ utils/
COPY src/ src/

# Create runtime directories
RUN mkdir -p repos cache history

# Expose the API port
EXPOSE 8000

# Environment variables (override at runtime)
ENV JWT_SECRET=""
ENV GITHUB_TOKEN=""
ENV OPENAI_API_KEY=""

# Run the server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
