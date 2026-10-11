FROM python:3.12-slim

WORKDIR /work

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/work

CMD ["python", "-m", "ml.dados"]
