# Use a slim Python base image
ARG ECR_CACHE=
FROM ${ECR_CACHE}python:3.11-slim


# Prevent Python from writing .pyc files and force stdout/stderr flushing
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a non-root user (good practice)
RUN adduser --disabled-password --gecos "" appuser

WORKDIR /app

# System deps (minimal). Add build tools only if you have packages needing compilation.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (better layer caching)
# If you use requirements.txt:
COPY requirements.txt /app/requirements.txt

# Install Python deps
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy source code
COPY . /app

# Switch to non-root
USER appuser

# Expose MCP/health port
EXPOSE 8000

# Start server (change "main:app" if your file/module path differs)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info", "--access-log"]
