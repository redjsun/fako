FROM python:3.12-slim

# supercronic: cron para containers, usado pelo serviço agendador (pesquisa/crontab).
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

# /work espelha a raiz do repositório: os comandos usam os mesmos caminhos que no host.
WORKDIR /work

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Usuário sem privilégio. UID/GID ajustáveis para casar com o dono das pastas montadas no Linux
# (ex.: docker compose build --build-arg UID=$(id -u) --build-arg GID=$(id -g)).
ARG UID=1000
ARG GID=1000
RUN groupadd -g "$GID" app && useradd -m -u "$UID" -g "$GID" app && chown app:app /work
USER app

# Sem --ServerApp.token: o Jupyter usa JUPYTER_TOKEN (do .env) ou gera um token aleatório e o
# imprime no log do container.
EXPOSE 8888
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--notebook-dir=/work/pesquisa/notebooks"]
