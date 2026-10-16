FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/app/.local/bin:$PATH

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY migrations ./migrations
COPY app ./app

# Sem root. UID 1000, o do usuário comum na maioria dos hosts Linux, para o código montado em
# /app (compose) continuar legível e gravável. Com a pasta home, o `pip install` do `make test`
# cai na instalação do usuário (~/.local, no PATH acima).
RUN useradd --create-home --uid 1000 app
USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
