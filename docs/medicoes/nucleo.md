# Medição do núcleo em C++: serial, OpenMP e GPU — H53b, H54a, H54b

> Gerado por `scripts/medir_nucleo.py`. **Não edite à mão**: número escrito à mão não é evidência. Para atualizar, rode o comando abaixo de novo.

O ganho do OpenMP é lido contra o **C++ serial**, com o mesmo plano: o C++ serial já é dezenas de vezes mais rápido que o Python (H53a), e o ganho contra o Python mediria o compilador junto. O baseline do RNF02, em Python, está em [`otimizador.md`](otimizador.md). As colunas:

- **Tempo da busca**: medido pelo executável, do começo ao fim do genético, sem o processo subir e ler a entrada. Mediana, e a faixa do menor ao maior.
- **Faixa do ganho**: o serial de cada rodada dividido pelo OpenMP da mesma rodada.
- **Ganho por thread**: o ganho dividido pelas threads. Acima de 8 threads, elas passam a dividir núcleos físicos (SMT), e o número cai por isso também.
- **Processo inteiro**: o que a API espera, da chamada à resposta — escrever a instância, subir o processo, conferir a viabilidade, buscar, e conferir o plano devolvido no Python (`nativo.py`).

**O plano foi o mesmo em todas as execuções**: em cada uma das 16 rodadas de cada tamanho, com cada número de threads, os genes, a avaliação e as gerações do OpenMP foram conferidos contra os do serial. O script para sem escrever este arquivo se algum divergir.

## Ambiente

| Item | Valor |
|---|---|
| Data | 26/09/2026 18:50 |
| Onde | contêiner, `python:3.11-slim` (ADR-012) |
| Compilador | g++ 13.3.0, `-O2 -fopenmp` |
| Processador | AMD Ryzen 7 5700X 8-Core Processor, 8 núcleos físicos, 16 threads lógicas |
| OpenMP | threads medidas: 1, 2, 4, 8, 16; escalonamento dinâmico |
| GPU | NVIDIA GeForce RTX 4060, capacidade 8.9, 8.187 MiB |
| Genético | população 48, 150 gerações, 4 partidas, 1 mutação por filho |
| Rodadas | 15 por tamanho, depois de uma de aquecimento |
| Instância | sintética, com o catálogo de `gerar_dados_sinteticos.py`, ganho pela RN10 e cotas pela RN11 |

## Como reproduzir

```bash
docker build -t gih-nucleo nucleo
docker run --rm --gpus all -v "$PWD:/repo" -w /repo gih-nucleo python scripts/medir_nucleo.py
```

## 500 parceiros

5 ações · máximo de 12 ações · plano com 12 ações · 600 gerações no total das 4 partidas.

| Modo | Threads | Tempo da busca | Faixa | Ganho sobre o serial | Faixa do ganho | Ganho por thread | Processo inteiro |
|---|--:|--:|--:|--:|--:|--:|--:|
| C++ serial | 1 | **81,9 ms** | 80,3 ms a 87,1 ms | — | — | — | 84,6 ms |
| OpenMP | 1 | 82,4 ms | 79,3 ms a 91,0 ms | **1,0x** | 0,9x a 1,1x | 99% | 85,0 ms |
| OpenMP | 2 | 43,6 ms | 42,3 ms a 46,2 ms | **1,9x** | 1,8x a 2,0x | 94% | 46,6 ms |
| OpenMP | 4 | 23,4 ms | 22,8 ms a 26,1 ms | **3,5x** | 3,1x a 3,8x | 87% | 26,2 ms |
| OpenMP | 8 | 15,0 ms | 13,8 ms a 17,5 ms | **5,5x** | 4,6x a 5,9x | 68% | 17,2 ms |
| OpenMP | 16 | 18,3 ms | 15,6 ms a 201 ms | **4,5x** | 0,4x a 5,4x | 28% | 20,9 ms |

## 2.000 parceiros

5 ações · máximo de 50 ações · plano com 45 ações · 600 gerações no total das 4 partidas.

| Modo | Threads | Tempo da busca | Faixa | Ganho sobre o serial | Faixa do ganho | Ganho por thread | Processo inteiro |
|---|--:|--:|--:|--:|--:|--:|--:|
| C++ serial | 1 | **318 ms** | 309 ms a 348 ms | — | — | — | 323 ms |
| OpenMP | 1 | 315 ms | 308 ms a 337 ms | **1,0x** | 0,9x a 1,1x | 101% | 320 ms |
| OpenMP | 2 | 166 ms | 161 ms a 188 ms | **1,9x** | 1,6x a 2,1x | 96% | 171 ms |
| OpenMP | 4 | 89,0 ms | 84,7 ms a 95,1 ms | **3,6x** | 3,3x a 4,1x | 89% | 93,9 ms |
| OpenMP | 8 | 53,2 ms | 52,4 ms a 55,9 ms | **6,0x** | 5,6x a 6,6x | 75% | 57,8 ms |
| OpenMP | 16 | 48,1 ms | 46,1 ms a 165 ms | **6,6x** | 1,9x a 7,2x | 41% | 52,5 ms |

## 10.000 parceiros

5 ações · máximo de 250 ações · plano com 206 ações · 600 gerações no total das 4 partidas.

| Modo | Threads | Tempo da busca | Faixa | Ganho sobre o serial | Faixa do ganho | Ganho por thread | Processo inteiro |
|---|--:|--:|--:|--:|--:|--:|--:|
| C++ serial | 1 | **1,59 s** | 1,54 s a 1,66 s | — | — | — | 1,61 s |
| OpenMP | 1 | 1,59 s | 1,54 s a 1,67 s | **1,0x** | 0,9x a 1,1x | 100% | 1,60 s |
| OpenMP | 2 | 840 ms | 803 ms a 869 ms | **1,9x** | 1,8x a 2,0x | 95% | 855 ms |
| OpenMP | 4 | 436 ms | 424 ms a 443 ms | **3,6x** | 3,5x a 3,9x | 91% | 451 ms |
| OpenMP | 8 | 257 ms | 251 ms a 274 ms | **6,2x** | 5,8x a 6,4x | 77% | 272 ms |
| OpenMP | 16 | 219 ms | 189 ms a 339 ms | **7,3x** | 4,8x a 8,3x | 45% | 234 ms |

## Transferência para a GPU — H54a

A instância e a população inicial das 4 partidas (4 × 48 indivíduos, um byte por gene) vão para a NVIDIA GeForce RTX 4060 e voltam. O executável confere o que voltou byte a byte, e com uma conta feita na própria GPU, e sai como defeito se não bater. Mediana de 15 repetições, depois de uma de aquecimento, e a faixa.

| Parceiros | Instância | População | Envio das duas | Volta da população | Volta de um indivíduo | Busca no OpenMP, 8 threads |
|--:|--:|--:|--:|--:|--:|--:|
| 500 | 22 KiB | 94 KiB | **282 µs** (170 µs a 513 µs) | **49 µs** (39 µs a 91 µs) | **29 µs** (19 µs a 44 µs) | 14,98 ms |
| 2.000 | 88 KiB | 375 KiB | **338 µs** (236 µs a 399 µs) | **97 µs** (94 µs a 128 µs) | **27 µs** (25 µs a 64 µs) | 53,21 ms |
| 10.000 | 440 KiB | 1,8 MiB | **509 µs** (432 µs a 1,02 ms) | **328 µs** (307 µs a 352 µs) | **36 µs** (30 µs a 50 µs) | 256,94 ms |

- **O laço na GPU (H54c) paga, por busca, um envio e a volta de um indivíduo**, porque a população fica residente entre gerações (ADR-006). Com 2.000 parceiros, 366 µs: 0,7% da busca inteira no OpenMP.
- **Trazer a população inteira a cada geração**, como no spike, custaria só na volta 14,60 ms por busca (150 gerações): 27% da busca inteira no OpenMP, antes de o kernel fazer qualquer conta. É o que a residência evita.

## Avaliação da população na GPU — H54b

Os 192 indivíduos de uma geração de todas as partidas, avaliados de uma vez: um bloco de 256 threads por indivíduo, com ganho, custo, ações, cauda, contagem por categoria e violação. A mesma população passa pelo `avaliar` em C++, na CPU, em série — e as duas são conferidas uma contra a outra no executável, e contra o `avaliar` do Python aqui. Mediana de 15 repetições, e a faixa.

O kernel é medido pela própria GPU, sem a transferência (que é a seção de cima), e **em lotes de lançamentos seguidos**, como o laço da H54c vai lançar uma geração depois da outra: cada medida é a média por lançamento num lote de uns 2 ms. Um lançamento isolado, com a placa esperando a CPU entre um e outro, mede a latência, e ela oscilou de 11 a 88 µs com 500 parceiros, conforme o relógio da placa subia ou não.

| Parceiros | Kernel na GPU, por lançamento | `avaliar` na CPU, em série | Ganho do kernel | Iguais ao Python |
|--:|--:|--:|--:|--:|
| 500 | **12 µs** (9 µs a 14 µs) | **59 µs** (58 µs a 63 µs) | **4,9x** | 192 de 192 |
| 2.000 | **13 µs** (12 µs a 15 µs) | **224 µs** (223 µs a 258 µs) | **17,2x** | 192 de 192 |
| 10.000 | **31 µs** (22 µs a 33 µs) | **1,18 ms** (1,16 ms a 1,47 ms) | **38,7x** | 192 de 192 |

- **O kernel sozinho não é o modo GPU.** A busca na GPU (H54c) também sorteia, cruza e muta na placa, e paga o lançamento de um kernel por geração. O ganho da GPU sobre o OpenMP só se mede com o laço inteiro, e esta tabela não o antecipa.
