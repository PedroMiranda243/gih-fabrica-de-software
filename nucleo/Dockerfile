# O núcleo em C++ como ele roda no contêiner da API (ADR-012): para medir o
# ganho do OpenMP (H53b) e para conferir o núcleo em Linux.
#
# Dois estágios, como no spike (parte 3 do `spike/RESULTADO.md`):
# - **compila** na imagem `devel` da NVIDIA, com o g++ que vai compilar também a
#   versão CUDA (H54). Os três modos são medidos com o mesmo compilador, no mesmo
#   lugar;
# - **roda** na `python:3.11-slim`, a base da API. É lá que o sistema roda, e é
#   lá que se mede (CLAUDE.md §7).
#
# O estágio de compilação é o que a H56 leva para o Dockerfile da API.
#
# Uso, da raiz do repositório:
#   docker build -t gih-nucleo nucleo
#   docker run --rm gih-nucleo gih-nucleo versao
#   docker run --rm gih-nucleo python -m pytest
#   docker run --rm -v "$PWD:/repo" -w /repo gih-nucleo python scripts/medir_nucleo.py

FROM nvidia/cuda:13.4.1-devel-ubuntu24.04 AS compilar

WORKDIR /nucleo
COPY cpp/ cpp/
# Os mesmos avisos da CI: aviso ignorado no núcleo é defeito que aparece só na
# GPU, onde é mais caro de achar.
RUN g++ -O2 -fopenmp -std=c++17 -Wall -Wextra -Wpedantic -Werror cpp/*.cpp -o gih-nucleo

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
