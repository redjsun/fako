FROM python:3.12-slim

# /work espelha a raiz do repositório: os comandos usam os mesmos caminhos que no host.
WORKDIR /work

COPY requirements.txt requirements-treino.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements-treino.txt

# Usuário sem privilégio. UID/GID ajustáveis para casar com o dono das pastas montadas no Linux
# (ex.: docker compose build --build-arg UID=$(id -u) --build-arg GID=$(id -g)).
ARG UID=1000
ARG GID=1000
RUN groupadd -g "$GID" app && useradd -m -u "$UID" -g "$GID" app && chown app:app /work
USER app
