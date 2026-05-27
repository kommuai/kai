# -------- Kai engine (tenant content via KAI_HOME volume) --------
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc git && \
    rm -rf /var/lib/apt/lists/*

ENV PIP_DEFAULT_TIMEOUT=1000
ENV PIP_RETRIES=10

COPY requirements.txt ./
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt

COPY . .

ENV KAI_STARTUP_COMPILE=auto
ENV KAI_HOME=/kai-home
ENV SESSION_DB_PATH=/kai-home/data/sessions.db

RUN mkdir -p /app/logs && chmod +x /app/scripts/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
