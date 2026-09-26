# Medição do núcleo em C++: serial, OpenMP e transferência para a GPU — H53b, H54a

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
| Data | 26/09/2026 17:59 |
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
| C++ serial | 1 | **83,0 ms** | 81,5 ms a 94,6 ms | — | — | — | 85,4 ms |
| OpenMP | 1 | 78,0 ms | 77,0 ms a 90,7 ms | **1,1x** | 0,9x a 1,2x | 106% | 80,9 ms |
| OpenMP | 2 | 42,3 ms | 40,9 ms a 46,2 ms | **2,0x** | 1,8x a 2,3x | 98% | 45,4 ms |
| OpenMP | 4 | 23,5 ms | 21,8 ms a 25,5 ms | **3,5x** | 3,2x a 3,9x | 88% | 26,3 ms |
| OpenMP | 8 | 14,7 ms | 13,5 ms a 15,6 ms | **5,7x** | 5,2x a 6,3x | 71% | 17,0 ms |
| OpenMP | 16 | 17,5 ms | 13,8 ms a 177 ms | **4,7x** | 0,5x a 6,2x | 30% | 19,7 ms |

## 2.000 parceiros

5 ações · máximo de 50 ações · plano com 45 ações · 600 gerações no total das 4 partidas.

| Modo | Threads | Tempo da busca | Faixa | Ganho sobre o serial | Faixa do ganho | Ganho por thread | Processo inteiro |
|---|--:|--:|--:|--:|--:|--:|--:|
| C++ serial | 1 | **322 ms** | 314 ms a 360 ms | — | — | — | 327 ms |
| OpenMP | 1 | 308 ms | 298 ms a 320 ms | **1,0x** | 1,0x a 1,2x | 105% | 312 ms |
| OpenMP | 2 | 161 ms | 155 ms a 186 ms | **2,0x** | 1,8x a 2,2x | 100% | 166 ms |
| OpenMP | 4 | 85,8 ms | 81,6 ms a 91,5 ms | **3,8x** | 3,6x a 4,2x | 94% | 90,3 ms |
| OpenMP | 8 | 51,2 ms | 48,9 ms a 52,5 ms | **6,3x** | 6,0x a 7,0x | 79% | 55,8 ms |
| OpenMP | 16 | 44,9 ms | 40,3 ms a 163 ms | **7,2x** | 2,0x a 8,7x | 45% | 49,7 ms |

## 10.000 parceiros

5 ações · máximo de 250 ações · plano com 206 ações · 600 gerações no total das 4 partidas.

| Modo | Threads | Tempo da busca | Faixa | Ganho sobre o serial | Faixa do ganho | Ganho por thread | Processo inteiro |
|---|--:|--:|--:|--:|--:|--:|--:|
| C++ serial | 1 | **1,61 s** | 1,56 s a 1,69 s | — | — | — | 1,62 s |
| OpenMP | 1 | 1,55 s | 1,51 s a 1,60 s | **1,0x** | 1,0x a 1,1x | 103% | 1,57 s |
| OpenMP | 2 | 807 ms | 777 ms a 855 ms | **2,0x** | 1,9x a 2,1x | 99% | 822 ms |
| OpenMP | 4 | 417 ms | 404 ms a 439 ms | **3,8x** | 3,6x a 4,1x | 96% | 433 ms |
| OpenMP | 8 | 245 ms | 240 ms a 266 ms | **6,5x** | 5,9x a 7,0x | 82% | 260 ms |
| OpenMP | 16 | 202 ms | 178 ms a 286 ms | **7,9x** | 5,7x a 9,3x | 50% | 219 ms |

## Transferência para a GPU — H54a

A instância e a população inicial das 4 partidas (4 × 48 indivíduos, um byte por gene) vão para a NVIDIA GeForce RTX 4060 e voltam. O executável confere o que voltou byte a byte, e com uma conta feita na própria GPU, e sai como defeito se não bater. Mediana de 15 repetições, depois de uma de aquecimento, e a faixa.

| Parceiros | Instância | População | Envio das duas | Volta da população | Volta de um indivíduo | Busca no OpenMP, 8 threads |
|--:|--:|--:|--:|--:|--:|--:|
| 500 | 22 KiB | 94 KiB | **207 µs** (180 µs a 691 µs) | **47 µs** (43 µs a 70 µs) | **29 µs** (24 µs a 49 µs) | 14,69 ms |
| 2.000 | 88 KiB | 375 KiB | **290 µs** (229 µs a 704 µs) | **101 µs** (97 µs a 117 µs) | **38 µs** (25 µs a 59 µs) | 51,23 ms |
| 10.000 | 440 KiB | 1,8 MiB | **843 µs** (765 µs a 969 µs) | **413 µs** (397 µs a 534 µs) | **81 µs** (78 µs a 114 µs) | 245,16 ms |

- **O laço na GPU (H54c) paga, por busca, um envio e a volta de um indivíduo**, porque a população fica residente entre gerações (ADR-006). Com 2.000 parceiros, 328 µs: 0,6% da busca inteira no OpenMP.
- **Trazer a população inteira a cada geração**, como no spike, custaria só na volta 15,09 ms por busca (150 gerações): 29% da busca inteira no OpenMP, antes de o kernel fazer qualquer conta. É o que a residência evita.
