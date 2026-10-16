FROM python:3.12-slim

WORKDIR /work

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

ENV PYTHONPATH=/work

# Usuário sem privilégio. UID/GID ajustáveis para casar com o dono das pastas montadas no Linux
# (ex.: docker compose build --build-arg UID=$(id -u) --build-arg GID=$(id -g)).
ARG UID=1000
ARG GID=1000
RUN groupadd -g "$GID" app && useradd -m -u "$UID" -g "$GID" app && chown app:app /work
USER app

CMD ["python", "-m", "ml.dados"]
