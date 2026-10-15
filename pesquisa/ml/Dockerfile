FROM python:3.12-slim

# /work espelha a raiz do repositório: os comandos usam os mesmos caminhos que no host.
WORKDIR /work

# Rodas do PyTorch: CPU por padrão; o compose.gpu.yaml troca pelas de CUDA (make ... GPU=1).
ARG TORCH_INDEX=https://download.pytorch.org/whl/cpu

COPY requirements.txt requirements-treino.txt /tmp/
RUN pip install --no-cache-dir --extra-index-url ${TORCH_INDEX} -r /tmp/requirements-treino.txt
