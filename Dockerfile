# -------- Backend + FastAPI --------
FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev git && \
    rm -rf /var/lib/apt/lists/*

# Large wheels (e.g. torch via sentence-transformers) need a longer read timeout.
ENV PIP_DEFAULT_TIMEOUT=1000
ENV PIP_RETRIES=10

# Install backend dependencies
COPY requirements.txt requirements-optional.txt ./
RUN pip install --no-cache-dir --default-timeout=1000 \
    -r requirements.txt -r requirements-optional.txt

# Copy backend source
COPY . .

# Pre-compile FAQ so runtime can use KAI_STARTUP_COMPILE=auto
RUN python3 -m kai.cli compile

ENV KAI_STARTUP_COMPILE=auto

# Create persistent dirs
RUN mkdir -p /app/media /app/logs /app/data

# Internal FastAPI port
EXPOSE 8000

# Start FastAPI
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
