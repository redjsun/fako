FROM python:3.12-slim

# /work espelha a raiz do repositório: os comandos usam os mesmos caminhos que no host.
WORKDIR /work

COPY requirements.txt requirements-treino.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements-treino.txt
