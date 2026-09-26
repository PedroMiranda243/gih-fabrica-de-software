# O núcleo em C++ (ADR-012) compila num estágio à parte, que leva o compilador;
# para a imagem final vai só o executável. Dois estágios, e o argumento NUCLEO
# escolhe um (H56):
# - `cpu`, o padrão: na mesma base da API, para que o executável encontre lá a
#   mesma glibc e o mesmo OpenMP com que foi compilado. Não baixa nada da NVIDIA,
#   e o sistema sobe em qualquer máquina (RNF06);
# - `cuda`, que o docker-compose.gpu.yml pede: na imagem de compilação da NVIDIA,
#   com o nvcc, e o `cudart` estático dentro do executável.
# O BuildKit só constrói o estágio que é usado: no build padrão, a imagem da
# NVIDIA, de alguns GB, nem é baixada.
ARG NUCLEO=cpu

FROM python:3.11-slim AS nucleo-cpu

RUN apt-get update \
 && apt-get install -y --no-install-recommends g++ \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /nucleo
COPY --from=nucleo cpp/ cpp/
# Os avisos são cobrados na CI (-Werror); aqui, um aviso novo de outra versão do
# g++ não deve impedir o sistema de subir.
RUN g++ -O2 -fopenmp -std=c++17 cpp/*.cpp -o gih-nucleo \
 && ./gih-nucleo versao

FROM nvidia/cuda:13.4.1-devel-ubuntu24.04 AS nucleo-cuda

WORKDIR /nucleo
COPY --from=nucleo cpp/ cpp/
# `-arch=all-major`: durante o build não há GPU para o nvcc perguntar a
# arquitetura, e a máquina da orientação pode ter outra placa. O `versao` aqui
# diz "sem placa" — o build não vê GPU —, e confere que o executável roda.
RUN nvcc -O2 -std=c++17 -arch=all-major -DGIH_COM_CUDA -Xcompiler=-fopenmp \
         cpp/*.cpp cpp/*.cu -o gih-nucleo -lgomp \
 && ./gih-nucleo versao

FROM nucleo-${NUCLEO} AS nucleo-escolhido

FROM python:3.11-slim

# O OpenMP do GCC é uma biblioteca à parte, que a imagem slim não traz.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependências primeiro: cada camada só é reconstruída quando o requirements
# dela muda. As do modelo vêm antes das da API porque o PyTorch é a maior de
# todas e a que menos muda.
#
# O modelo preditivo chega como **contexto adicional** de build (`modelo`, no
# docker-compose.yml — ADR-010). Construir a partir da raiz do repositório
# resolveria o mesmo problema e levaria web/node_modules e docs/ para dentro
# do build.
COPY --from=modelo requirements.txt /modelo/requirements.txt
RUN pip install --no-cache-dir -r /modelo/requirements.txt

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# `--no-deps`: as dependências do pacote já estão acima, com a versão fixa e a
# roda CPU. Deixar o pip resolvê-las pelo pyproject traria o PyTorch do PyPI.
COPY --from=modelo pyproject.toml /modelo/pyproject.toml
COPY --from=modelo gih_modelo /modelo/gih_modelo
RUN pip install --no-cache-dir --no-deps /modelo

# O otimizador serial (ADR-011) chega do mesmo jeito, como contexto `nucleo`.
# Só o pacote Python: `spike/` e o `requirements.txt` da pasta são do spike de
# GPU, e trariam o CuPy para uma imagem que não o usa.
COPY --from=nucleo pyproject.toml /nucleo/pyproject.toml
COPY --from=nucleo gih_nucleo /nucleo/gih_nucleo
RUN pip install --no-cache-dir --no-deps /nucleo

# O executável, no PATH: é onde `gih_nucleo.nativo` o procura (H55, ADR-012).
COPY --from=nucleo-escolhido /nucleo/gih-nucleo /usr/local/bin/gih-nucleo

COPY alembic.ini .
COPY app ./app
COPY migrations ./migrations
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
