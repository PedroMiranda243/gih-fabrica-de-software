# O núcleo em C++ como ele roda no contêiner da API (ADR-012): para medir o
# ganho do OpenMP (H53b) e o da GPU (H54), e para conferir o núcleo em Linux.
#
# Dois estágios, como no spike (parte 3 do `spike/RESULTADO.md`):
# - **compila** na imagem `devel` da NVIDIA, com o nvcc e o g++ dela. Os três
#   modos saem do mesmo executável, compilado no mesmo lugar;
# - **roda** na `python:3.11-slim`, a base da API. É lá que o sistema roda, e é
#   lá que se mede (CLAUDE.md §7).
#
# Uso, da raiz do repositório:
#   docker build -t gih-nucleo nucleo
#   docker run --rm --gpus all gih-nucleo gih-nucleo versao
#   docker run --rm --gpus all gih-nucleo python -m pytest
#   docker run --rm gih-nucleo python -m pytest         # sem GPU: a recusa
#   docker run --rm --gpus all -v "$PWD:/repo" -w /repo gih-nucleo python scripts/medir_nucleo.py

FROM nvidia/cuda:13.4.1-devel-ubuntu24.04 AS compilar

WORKDIR /nucleo
COPY cpp/ cpp/
# Primeiro a versão só de CPU, com os avisos da CI (-Werror): é a que compila em
# qualquer máquina, e o CUDA não pode esconder um aviso nela. Depois a de
# verdade, com os .cu. `-arch=all-major` porque durante o build não há GPU para
# o nvcc perguntar a arquitetura, e a máquina da orientação pode ter outra placa.
# O `cudart` entra estático, o padrão do nvcc: o executável roda numa imagem que
# não é da NVIDIA, e o driver chega pelo `--gpus all`.
RUN g++ -O2 -fopenmp -std=c++17 -Wall -Wextra -Wpedantic -Werror cpp/*.cpp -o /tmp/so-cpu \
 && nvcc -O2 -std=c++17 -arch=all-major -DGIH_COM_CUDA -Xcompiler=-fopenmp,-Wall,-Wextra \
         cpp/*.cpp cpp/*.cu -o gih-nucleo -lgomp

FROM python:3.11-slim

# O OpenMP do GCC é uma biblioteca à parte, que a imagem slim não traz.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/*

COPY --from=compilar /nucleo/gih-nucleo /usr/local/bin/gih-nucleo

# O pacote e os testes, para conferir o executável contra o Python aqui dentro.
# O pytest é só desta imagem: a da API não o leva. O pacote não tem dependência;
# o `--no-deps` vale só para ele, e o pytest precisa das suas.
WORKDIR /nucleo
COPY pyproject.toml ./
COPY gih_nucleo/ gih_nucleo/
COPY tests/ tests/
RUN pip install --no-cache-dir --no-deps . \
 && pip install --no-cache-dir pytest==8.3.4

ENV GIH_NUCLEO=/usr/local/bin/gih-nucleo \
    GIH_NUCLEO_OBRIGATORIO=1
