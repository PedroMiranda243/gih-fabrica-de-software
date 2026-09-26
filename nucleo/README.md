# `nucleo/` — o otimizador do plano de campanha

Pacote `gih_nucleo`: dado o ganho esperado de cada ação em cada parceiro, escolhe o plano de maior ganho que
respeita o orçamento, o máximo de ações e as cotas (H48, H49, H52). **Otimiza; não decide.** Recebe da API
uma instância já em números inteiros e devolve o plano. Não conhece banco, FastAPI nem regra de negócio:
o que é ganho (RN10), quem é elegível e o que é cauda longa (RN11) são decididos pela API.

O problema está formalizado em [`docs/07`](../docs/07-arquitetura-preliminar.md) §4.1. O algoritmo, e o que
deixa as quatro versões — Python, C++ serial, OpenMP e CUDA — no mesmo plano, estão na ADR-011.

| Arquivo | O que faz |
|---|---|
| `problema.py` | A instância, em centavos e contagens. A avaliação de uma solução, com a violação em unidades de ação. O verificador independente das restrições (RN07) |
| `viabilidade.py` | Decide **com exatidão**, antes da busca, se as cotas cabem; se não, diz qual restrição falha e quanto falta (H52) |
| `guloso.py` | Os planos gulosos, por razão ganho/custo e por ganho: soluções iniciais do genético e referência de qualidade |
| `serial.py` | O genético com partidas independentes, em Python puro: o baseline de corretude e de tempo (H49, RNF02) |
| `aleatorio.py` | O gerador sem estado (SplitMix64 por coordenadas), igual em Python, C++ e CUDA |
| `exaustivo.py` | O ótimo por enumeração, para instâncias pequenas: a régua dos testes |
| `nativo.py` | Chama o executável em C++ com o mesmo contrato de `serial.otimizar`, em qualquer modo, e confere a avaliação que ele devolve (ADR-012) |

**O mesmo algoritmo em C++** (`cpp/`, H53a): o executável `gih-nucleo` lê a instância em texto e devolve o
plano **idêntico** ao do Python — mesmos genes, mesma avaliação, mesmas gerações —, porque o sorteio é por
coordenadas e a aritmética é inteira (ADR-011). No contêiner, com 2.000 parceiros, leva 0,34 s contra 25,5 s
do Python: 76x.

| Arquivo | O que faz |
|---|---|
| `cpp/genetico.hpp` | Os passos que as versões fazem igual: sorteio, torneio, filho, a preparação e o relógio. O sorteio, o torneio, a elite e a fórmula de cada gene são compilados também para a GPU: é a mesma função nos dois lados |
| `cpp/serial.cpp` | O genético serial, uma partida depois da outra (H53a) |
| `cpp/openmp.cpp` | O genético com OpenMP: as partidas avançam juntas, e os filhos de cada geração são calculados em paralelo (H53b). O mesmo plano da serial com qualquer número de threads |
| `cpp/gpu.hpp` | A GPU vista do resto do núcleo, sem nada do CUDA: achar a placa, a ida e volta, a avaliação e a busca inteira |
| `cpp/gpu.cuh` | As estruturas na GPU (H54a): a memória com dono, a instância no layout da CPU, e a população em dois buffers — a geração atual e a seguinte —, que ficam na placa a busca inteira (ADR-006). E o que é falta de GPU e o que é defeito, numa falha do CUDA |
| `cpp/gpu.cu` | A ida e volta, conferida byte a byte e por uma conta feita na própria GPU. Compilado só com CUDA |
| `cpp/gpu_avaliacao.cuh` | A avaliação de um indivíduo por um bloco de threads, com as contas de `avaliar` em inteiros (H54b). É o que o laço da H54c chama para cada filho |
| `cpp/avaliacao.cu` | O kernel que avalia a população inteira, um bloco por indivíduo, e mede o próprio tempo. Compilado só com CUDA |
| `cpp/busca.cu` | O genético inteiro na GPU (H54c): a população nasce na placa e fica lá; cada geração é um kernel, com um bloco por indivíduo; só as avaliações da última geração e o plano vencedor voltam. O mesmo plano das outras versões. Compilado só com CUDA |
| `cpp/sem_gpu.cpp` | O núcleo sem CUDA: diz que não há GPU, e por quê |
| `cpp/main.cpp` | O executável: `otimizar --modo serial\|openmp\|cuda [--threads N]`, `sorteio`, `gpu`, `transferir`, `avaliar` e `versao`, que diz os modos, as threads, o compilador e a GPU |

O ganho do OpenMP e o da GPU, a transferência e o kernel são medidos no contêiner:
[`docs/medicoes/nucleo.md`](../docs/medicoes/nucleo.md). **A GPU tem um custo fixo**: iniciar o driver e criar o
contexto, uma vez por processo, antes de qualquer conta. O modo `cuda` o informa à parte, e a medição mostra o
laço sem ele e a busca inteira com ele.

**Sem GPU, o executável recusa o que precisa dela com a saída 1**, e diz o motivo: compilado sem CUDA, nenhuma
placa visível, driver antigo — ou a placa que fica sem memória ou some no meio da busca. É o sinal para a API
cair para a CPU (RNF06, H56). Para ver a recusa numa máquina com placa, esconda-a:
`CUDA_VISIBLE_DEVICES=-1 bin/gih-nucleo gpu`. A campanha inviável é respondida antes, na CPU, em qualquer modo.

**O pacote Python não tem dependência.** O baseline serial é o denominador do *speedup*, e vetorizá-lo com NumPy
deixaria o ganho medido menos honesto. `spike/` guarda a validação do toolchain de GPU (H47), e o
`requirements.txt` desta pasta é dele, não do pacote.

## Rodando os testes

No mesmo ambiente virtual da API, de dentro de `nucleo/`:

```bash
pip install --no-deps -e .
construir.bat                                                            # Windows: com CUDA, se houver
construir.bat cpu                                                        # Windows: só a CPU
g++ -O2 -fopenmp -std=c++17 -Wall -Wextra cpp/*.cpp -o bin/gih-nucleo    # Linux, sem CUDA
pytest
```

Sem o executável compilado, ou compilado sem OpenMP, os testes que comparam o C++ com o Python são pulados;
na CI, reprovam. Os que precisam de placa — a ida e volta, o kernel e a busca na GPU — pulam sem ela, porque a
CI não tem placa nem CUDA, e reprovam com `GIH_GPU_OBRIGATORIA=1`. Os da recusa sem GPU rodam em qualquer
máquina.

**No contêiner**, como o sistema roda (ADR-012), da raiz do repositório:

```bash
docker build -t gih-nucleo nucleo
docker run --rm --gpus all gih-nucleo python -m pytest          # os mesmos testes, em Linux, com a GPU
docker run --rm gih-nucleo python -m pytest                     # sem GPU: o que precisa de placa pula
docker run --rm --gpus all -v "$PWD:/repo" -w /repo gih-nucleo python scripts/medir_nucleo.py
```

A imagem compila com o nvcc e o g++ da imagem de compilação da NVIDIA e roda na `python:3.11-slim`, a base da
API. O `cudart` vai estático dentro do executável; o driver chega pelo `--gpus all`.

Os testes conferem o genético contra a enumeração exata em 40 instâncias pequenas sorteadas e a
verificação de viabilidade contra a enumeração em 150. Também mostram onde o guloso fica abaixo do ótimo e
fixam os valores do gerador que o C++ e o CUDA vão precisar reproduzir.
