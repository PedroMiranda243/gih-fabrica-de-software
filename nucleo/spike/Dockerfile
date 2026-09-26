# Os testes do spike (H47) compilados em Linux e rodados na imagem da própria
# API — parte 3 do RESULTADO.md, issue #123, ADR-012.
#
# A pergunta que esta imagem responde: o núcleo em C++ com OpenMP e CUDA, que
# até aqui só foi compilado no Windows (ADR-006), roda **dentro do contêiner da
# API**, com a GPU da máquina? A API é `python:3.11-slim`; se o núcleo só
# rodasse numa imagem da NVIDIA, a Sprint 10 teria de chamá-lo em outro serviço.
#
# **Dois estágios.** A imagem `devel` da NVIDIA traz o nvcc e pesa alguns GB, e
# só compila. O binário sai com o runtime do CUDA embutido (`cudart` estático, o
# padrão do nvcc), e por isso roda numa imagem que não é da NVIDIA: o driver
# chega pelo `--gpus all`. Rodar na imagem `runtime` da NVIDIA daria 5,1 GB.
#
# Uso, da raiz do repositório:
#   docker build -t gih-spike nucleo/spike
#   docker run --rm --gpus all gih-spike teste_cuda
#   docker run --rm --gpus all gih-spike teste_openmp
#   docker run --rm gih-spike python /spike/ida_e_volta.py
#   docker run --rm gih-spike teste_cuda          # sem GPU: recusa, saída 1

FROM nvidia/cuda:13.4.1-devel-ubuntu24.04 AS compilar

WORKDIR /spike
COPY teste_openmp.cpp teste_cuda.cu eco.cpp ./

# `-arch=native` do Windows não serve aqui: durante o build não há GPU para o
# nvcc perguntar a arquitetura. `all-major` gera código para todas as famílias
# que o CUDA 13 suporta — a máquina da orientação pode não ter esta placa.
RUN g++ -O2 -fopenmp -std=c++17 teste_openmp.cpp -o teste_openmp \
 && nvcc -O2 -std=c++17 -arch=all-major teste_cuda.cu -o teste_cuda \
 && g++ -O2 -std=c++17 eco.cpp -o eco

# A mesma base da imagem da API.
FROM python:3.11-slim

# O OpenMP do GCC é uma biblioteca à parte, que a imagem slim não traz.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/*

COPY --from=compilar /spike/teste_openmp /spike/teste_cuda /spike/eco /usr/local/bin/
COPY ida_e_volta.py /spike/ida_e_volta.py
