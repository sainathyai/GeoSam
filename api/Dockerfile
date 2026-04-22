FROM python:3.11-slim

WORKDIR /app

# System deps for segyio (C extension)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY pyproject.toml .
RUN pip install --no-cache-dir ".[sam,gcp]" uvicorn fastapi

# Copy source
COPY geosam/ geosam/
COPY api/main.py api/main.py

# Cloud Run sets PORT env var; default 8080
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
