FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# supercronic: cron para containers, usado pelo serviço agendador-api (api/crontab).
ARG TARGETARCH=amd64
ARG SUPERCRONIC_VERSAO=v0.2.49
RUN set -eux; \
    apt-get update; apt-get install -y --no-install-recommends curl tzdata; rm -rf /var/lib/apt/lists/*; \
    case "$TARGETARCH" in \
      amd64) sha1=e63c11a9726b775a6a11801e81af4f3fb926aa68 ;; \
      arm64) sha1=0b6c5bb743e0b0dafed1132198c81807927ac413 ;; \
      *) echo "arquitetura sem supercronic: $TARGETARCH"; exit 1 ;; \
    esac; \
    curl -fsSLo /usr/local/bin/supercronic \
      "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSAO}/supercronic-linux-${TARGETARCH}"; \
    echo "${sha1}  /usr/local/bin/supercronic" | sha1sum -c -; \
    chmod +x /usr/local/bin/supercronic

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini crontab ./
COPY migrations ./migrations
COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
