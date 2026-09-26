# Medição do núcleo em C++: serial e OpenMP — H53b

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
| Data | 26/09/2026 07:15 |
| Onde | contêiner, `python:3.11-slim` (ADR-012) |
| Compilador | g++ 13.3.0, `-O2 -fopenmp` |
| Processador | AMD Ryzen 7 5700X 8-Core Processor, 8 núcleos físicos, 16 threads lógicas |
| OpenMP | threads medidas: 1, 2, 4, 8, 16; escalonamento dinâmico |
| Genético | população 48, 150 gerações, 4 partidas, 1 mutação por filho |
| Rodadas | 15 por tamanho, depois de uma de aquecimento |
| Instância | sintética, com o catálogo de `gerar_dados_sinteticos.py`, ganho pela RN10 e cotas pela RN11 |

## Como reproduzir

```bash
docker build -t gih-nucleo nucleo
docker run --rm -v "$PWD:/repo" -w /repo gih-nucleo python scripts/medir_nucleo.py
```

## 500 parceiros

5 ações · máximo de 12 ações · plano com 12 ações · 600 gerações no total das 4 partidas.

| Modo | Threads | Tempo da busca | Faixa | Ganho sobre o serial | Faixa do ganho | Ganho por thread | Processo inteiro |
|---|--:|--:|--:|--:|--:|--:|--:|
| C++ serial | 1 | **86,1 ms** | 80,7 ms a 103 ms | — | — | — | 88,9 ms |
| OpenMP | 1 | 86,2 ms | 81,6 ms a 106 ms | **1,0x** | 0,8x a 1,1x | 100% | 89,1 ms |
| OpenMP | 2 | 45,3 ms | 42,7 ms a 49,9 ms | **1,9x** | 1,7x a 2,4x | 95% | 47,9 ms |
| OpenMP | 4 | 25,6 ms | 23,0 ms a 30,7 ms | **3,4x** | 2,7x a 4,0x | 84% | 28,6 ms |
| OpenMP | 8 | 16,5 ms | 14,5 ms a 19,3 ms | **5,2x** | 4,5x a 6,2x | 65% | 19,1 ms |
| OpenMP | 16 | 44,7 ms | 15,5 ms a 192 ms | **1,9x** | 0,5x a 5,2x | 12% | 47,1 ms |

## 2.000 parceiros

5 ações · máximo de 50 ações · plano com 45 ações · 600 gerações no total das 4 partidas.

| Modo | Threads | Tempo da busca | Faixa | Ganho sobre o serial | Faixa do ganho | Ganho por thread | Processo inteiro |
|---|--:|--:|--:|--:|--:|--:|--:|
| C++ serial | 1 | **333 ms** | 317 ms a 347 ms | — | — | — | 338 ms |
| OpenMP | 1 | 334 ms | 324 ms a 362 ms | **1,0x** | 0,9x a 1,1x | 100% | 338 ms |
| OpenMP | 2 | 174 ms | 167 ms a 179 ms | **1,9x** | 1,8x a 2,0x | 96% | 179 ms |
| OpenMP | 4 | 90,7 ms | 87,6 ms a 97,5 ms | **3,7x** | 3,3x a 3,9x | 92% | 95,4 ms |
| OpenMP | 8 | 55,3 ms | 52,5 ms a 61,2 ms | **6,0x** | 5,3x a 6,5x | 75% | 59,7 ms |
| OpenMP | 16 | 72,3 ms | 46,0 ms a 319 ms | **4,6x** | 1,0x a 6,9x | 29% | 77,0 ms |

## 10.000 parceiros

5 ações · máximo de 250 ações · plano com 206 ações · 600 gerações no total das 4 partidas.

| Modo | Threads | Tempo da busca | Faixa | Ganho sobre o serial | Faixa do ganho | Ganho por thread | Processo inteiro |
|---|--:|--:|--:|--:|--:|--:|--:|
| C++ serial | 1 | **1,61 s** | 1,58 s a 1,71 s | — | — | — | 1,63 s |
| OpenMP | 1 | 1,66 s | 1,60 s a 1,73 s | **1,0x** | 0,9x a 1,0x | 97% | 1,67 s |
| OpenMP | 2 | 855 ms | 829 ms a 891 ms | **1,9x** | 1,8x a 2,0x | 94% | 871 ms |
| OpenMP | 4 | 439 ms | 431 ms a 462 ms | **3,7x** | 3,6x a 3,9x | 92% | 453 ms |
| OpenMP | 8 | 261 ms | 255 ms a 268 ms | **6,2x** | 6,0x a 6,7x | 77% | 276 ms |
| OpenMP | 16 | 213 ms | 194 ms a 331 ms | **7,6x** | 4,8x a 8,7x | 47% | 229 ms |
