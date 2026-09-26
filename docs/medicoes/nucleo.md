# Medição do núcleo em C++: serial, OpenMP e GPU — H53b, H54a, H54b, H54c

> Gerado por `scripts/medir_nucleo.py`. **Não edite à mão**: número escrito à mão não é evidência. Para atualizar, rode o comando abaixo de novo.

O ganho do OpenMP e o da GPU são lidos contra o **C++ serial**, com o mesmo plano: o C++ serial já é dezenas de vezes mais rápido que o Python (H53a), e o ganho contra o Python mediria o compilador junto. A exceção é o RNF02, que pede o ganho da GPU sobre o baseline em Python: ele tem a sua seção, no cenário de referência. As colunas:

- **Tempo da busca**: medido pelo executável, do começo ao fim do genético, sem o processo subir e ler a entrada. Na GPU, inclui iniciar o driver e criar o contexto da placa, que a seção da H54c separa. Mediana, e a faixa do menor ao maior.
- **Faixa do ganho**: o serial de cada rodada dividido pelo modo da mesma rodada.
- **Ganho por thread**: o ganho dividido pelas threads. Acima de 8 threads, elas passam a dividir núcleos físicos (SMT), e o número cai por isso também.
- **Processo inteiro**: o que a API espera, da chamada à resposta — escrever a instância, subir o processo, conferir a viabilidade, buscar, e conferir o plano devolvido no Python (`nativo.py`).

**O plano foi o mesmo em todas as execuções**: em cada uma das 16 rodadas de cada tamanho, com cada número de threads e na GPU, os genes, a avaliação e as gerações foram conferidos contra os do serial. O script para sem escrever este arquivo se algum divergir.

## Ambiente

| Item | Valor |
|---|---|
| Data | 26/09/2026 22:46 |
| Onde | contêiner, `python:3.11-slim` (ADR-012) |
| Compilador | g++ 13.3.0, `-O2 -fopenmp`; os kernels com o `nvcc`, `-O2 -arch=all-major` |
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
| C++ serial | 1 | **82,2 ms** | 79,2 ms a 85,5 ms | — | — | — | 85,1 ms |
| OpenMP | 1 | 81,5 ms | 79,2 ms a 90,7 ms | **1,0x** | 0,9x a 1,1x | 101% | 84,5 ms |
| OpenMP | 2 | 43,3 ms | 41,8 ms a 48,2 ms | **1,9x** | 1,7x a 2,0x | 95% | 46,2 ms |
| OpenMP | 4 | 23,5 ms | 22,7 ms a 26,1 ms | **3,5x** | 3,1x a 3,7x | 87% | 26,2 ms |
| OpenMP | 8 | 14,3 ms | 13,9 ms a 15,5 ms | **5,7x** | 5,3x a 6,1x | 72% | 16,8 ms |
| OpenMP | 16 | 56,6 ms | 16,3 ms a 180 ms | **1,5x** | 0,5x a 5,2x | 9% | 59,1 ms |
| GPU, com o contexto | — | 190 ms | 176 ms a 216 ms | **0,4x** | 0,4x a 0,5x | — | 235 ms |

## 2.000 parceiros

5 ações · máximo de 50 ações · plano com 45 ações · 600 gerações no total das 4 partidas.

| Modo | Threads | Tempo da busca | Faixa | Ganho sobre o serial | Faixa do ganho | Ganho por thread | Processo inteiro |
|---|--:|--:|--:|--:|--:|--:|--:|
| C++ serial | 1 | **322 ms** | 312 ms a 358 ms | — | — | — | 327 ms |
| OpenMP | 1 | 319 ms | 310 ms a 359 ms | **1,0x** | 0,9x a 1,1x | 101% | 324 ms |
| OpenMP | 2 | 171 ms | 161 ms a 178 ms | **1,9x** | 1,8x a 2,1x | 94% | 176 ms |
| OpenMP | 4 | 88,9 ms | 84,3 ms a 95,8 ms | **3,6x** | 3,3x a 4,0x | 90% | 93,6 ms |
| OpenMP | 8 | 54,5 ms | 49,1 ms a 75,0 ms | **5,9x** | 4,2x a 6,8x | 74% | 59,1 ms |
| OpenMP | 16 | 75,8 ms | 42,2 ms a 310 ms | **4,2x** | 1,0x a 7,8x | 27% | 81,3 ms |
| GPU, com o contexto | — | 195 ms | 177 ms a 236 ms | **1,6x** | 1,4x a 1,9x | — | 248 ms |

## 10.000 parceiros

5 ações · máximo de 250 ações · plano com 206 ações · 600 gerações no total das 4 partidas.

| Modo | Threads | Tempo da busca | Faixa | Ganho sobre o serial | Faixa do ganho | Ganho por thread | Processo inteiro |
|---|--:|--:|--:|--:|--:|--:|--:|
| C++ serial | 1 | **1,60 s** | 1,57 s a 1,64 s | — | — | — | 1,61 s |
| OpenMP | 1 | 1,59 s | 1,57 s a 1,61 s | **1,0x** | 1,0x a 1,0x | 100% | 1,61 s |
| OpenMP | 2 | 822 ms | 813 ms a 835 ms | **1,9x** | 1,9x a 2,0x | 97% | 838 ms |
| OpenMP | 4 | 427 ms | 420 ms a 450 ms | **3,7x** | 3,5x a 3,8x | 93% | 442 ms |
| OpenMP | 8 | 251 ms | 246 ms a 279 ms | **6,4x** | 5,8x a 6,5x | 79% | 266 ms |
| OpenMP | 16 | 191 ms | 183 ms a 306 ms | **8,4x** | 5,2x a 9,0x | 52% | 206 ms |
| GPU, com o contexto | — | 231 ms | 214 ms a 253 ms | **6,9x** | 6,3x a 7,4x | — | 288 ms |

## A busca inteira na GPU — H54c

O genético inteiro na NVIDIA GeForce RTX 4060: a população nasce na placa e fica lá até o fim, e só voltam as avaliações da última geração e o plano vencedor (ADR-006). Cada geração é um kernel, com um bloco de 256 threads por indivíduo, e a placa parte do repouso em cada busca, como no uso de verdade. O plano foi conferido contra o do serial em todas as execuções.

**O custo fixo, à parte.** Antes de qualquer conta, o processo inicia o driver e cria o contexto da GPU: é o que cada cálculo paga uma vez. O executável o mede, e a tabela o separa do laço.

| Parceiros | OpenMP, 8 threads | GPU, só o laço | Laço contra o OpenMP | Contexto da GPU | GPU, a busca inteira | Busca inteira contra o OpenMP |
|--:|--:|--:|--:|--:|--:|--:|
| 500 | 14,3 ms | **4,8 ms** | **3,0x** | 185 ms (172 ms a 211 ms) | 190 ms | 0,1x |
| 2.000 | 54,5 ms | **7,3 ms** | **7,4x** | 188 ms (170 ms a 227 ms) | 195 ms | 0,3x |
| 10.000 | 251 ms | **27,0 ms** | **9,3x** | 203 ms (188 ms a 227 ms) | 231 ms | 1,1x |

- **O laço na GPU é o mais rápido dos modos**, e o ganho cresce com o tamanho: o tempo de uma geração cresce bem menos que o número de parceiros, porque as threads de um bloco dividem os genes do indivíduo.
- **Com o contexto, a GPU perde para o OpenMP com 500 e 2.000 parceiros e ganha com 10.000.** Abaixo de 1x, o OpenMP termina antes. O contexto é o mesmo em qualquer tamanho, e só se paga quando o laço é grande.
- **O modo automático escolhe a GPU mesmo assim** (adendo H54c da ADR-012): a diferença é de décimos de segundo, que a tela não sente, e a tela não promete "o mais rápido".

## RNF01 e RNF02 — a GPU no cenário de referência

2.000 parceiros e 5 ações (`docs/02-requisitos.md`). O tempo da GPU é o do processo inteiro, da chamada à resposta — escrever a instância, subir o processo, criar o contexto, buscar e conferir o plano no Python. O do Python é só o da busca, dentro do próprio processo, mediana de 3 execuções: a comparação desfavorece a GPU.

| Requisito | Meta | Medido | |
|---|---|---|---|
| RNF01, de ponta a ponta | até 5 s | 248 ms (223 ms a 287 ms) | atende |
| RNF02, speedup sobre o Python | no mínimo 5x | 26,29 s contra 248 ms: **106,0x** | atende |
| RNF02, uplift | dentro de 2% do Python | 0,0% de diferença: o mesmo plano | atende |

## Transferência para a GPU — H54a

A instância e a população inicial das 4 partidas (4 × 48 indivíduos, um byte por gene) vão para a NVIDIA GeForce RTX 4060 e voltam. O executável confere o que voltou byte a byte, e com uma conta feita na própria GPU, e sai como defeito se não bater. Mediana de 15 repetições, depois de uma de aquecimento, e a faixa.

| Parceiros | Instância | População | Envio das duas | Volta da população | Volta de um indivíduo | Busca no OpenMP, 8 threads |
|--:|--:|--:|--:|--:|--:|--:|
| 500 | 22 KiB | 94 KiB | **557 µs** (491 µs a 860 µs) | **134 µs** (93 µs a 159 µs) | **81 µs** (74 µs a 117 µs) | 14,35 ms |
| 2.000 | 88 KiB | 375 KiB | **239 µs** (221 µs a 478 µs) | **102 µs** (94 µs a 208 µs) | **29 µs** (24 µs a 52 µs) | 54,53 ms |
| 10.000 | 440 KiB | 1,8 MiB | **556 µs** (474 µs a 986 µs) | **353 µs** (306 µs a 526 µs) | **46 µs** (36 µs a 78 µs) | 250,95 ms |

- **A busca na GPU (H54c) paga, no máximo, um envio e a volta de um indivíduo**, porque a população fica residente entre gerações (ADR-006). Com 2.000 parceiros, 268 µs: 0,5% da busca inteira no OpenMP. Na verdade paga menos: a população nem vai, porque é sorteada na placa; vão a instância e os dois gulosos.
- **Trazer a população inteira a cada geração**, como no spike, custaria só na volta 15,27 ms por busca (150 gerações): 28% da busca inteira no OpenMP, antes de o kernel fazer qualquer conta. É o que a residência evita.

## Avaliação da população na GPU — H54b

Os 192 indivíduos de uma geração de todas as partidas, avaliados de uma vez: um bloco de 256 threads por indivíduo, com ganho, custo, ações, cauda, contagem por categoria e violação. A mesma população passa pelo `avaliar` em C++, na CPU, em série — e as duas são conferidas uma contra a outra no executável, e contra o `avaliar` do Python aqui. Mediana de 15 repetições, e a faixa.

O kernel é medido pela própria GPU, sem a transferência (que é a seção de cima), e **em lotes de lançamentos seguidos**, como o laço da H54c lança uma geração depois da outra: cada medida é a média por lançamento num lote de uns 2 ms. Um lançamento isolado, com a placa esperando a CPU entre um e outro, mede a latência, e ela oscilou de 11 a 88 µs com 500 parceiros, conforme o relógio da placa subia ou não.

| Parceiros | Kernel na GPU, por lançamento | `avaliar` na CPU, em série | Ganho do kernel | Iguais ao Python |
|--:|--:|--:|--:|--:|
| 500 | **10 µs** (9 µs a 18 µs) | **73 µs** (73 µs a 76 µs) | **7,1x** | 192 de 192 |
| 2.000 | **12 µs** (11 µs a 14 µs) | **225 µs** (223 µs a 278 µs) | **18,9x** | 192 de 192 |
| 10.000 | **22 µs** (21 µs a 37 µs) | **1,21 ms** (1,17 ms a 1,28 ms) | **55,1x** | 192 de 192 |

- **O kernel sozinho não é o modo GPU.** A busca na GPU (H54c) também sorteia, cruza e muta na placa, dentro do mesmo kernel, e paga o contexto da placa. O ganho sobre o OpenMP está na seção da busca inteira.
