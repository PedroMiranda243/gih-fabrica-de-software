# Spike de GPU — resultado

**História:** H47 · Sprint 3
**Data:** 15/09/2026
**Objetivo:** retirar o risco **R1** do cronograma — a cadeia de compilação de GPU funcionar nesta máquina.

> **Atualizado em 26/09/2026.** A [parte 3](#parte-3--o-núcleo-dentro-do-contêiner-da-api) leva os dois
> testes para Linux, dentro da imagem da própria API, com a GPU — o que faltava para decidir como a API chama
> o núcleo (issue #123, ADR-012).
>
> **Atualizado em 15/09/2026, à tarde.** O spike original rodou sem compilador C++ e sem CUDA Toolkit,
> compilando o kernel por NVRTC. Depois disso o toolchain nativo foi instalado, e a
> [parte 2](#parte-2--validação-do-toolchain-nativo) valida `cl` + `nvcc` e mede o OpenMP, que o spike
> original não conseguia cobrir. As duas partes estão preservadas: a parte 1 é o que foi medido com o que
> existia na máquina, e as duas juntas contam o que mudou.

---

## Veredito

**O risco está retirado, agora pelos dois caminhos.** O kernel CUDA compila, executa na GPU e produz o
mesmo resultado do cálculo em CPU — por NVRTC (parte 1) e por `nvcc` (parte 2). A meta de *speedup* do
RNF02 (mínimo de 5x sobre o baseline serial) foi **atingida e superada** em medição real, oito semanas
antes de ser necessária. O caminho de CPU paralela do RNF06 também está validado: OpenMP entrega **~9x**
com 16 threads.

---

# Parte 1 — o spike original (NVRTC)

## Ambiente medido

| Item | Valor |
|---|---|
| GPU | NVIDIA GeForce RTX 4060, 8 GB |
| Capacidade de computação | 8.9 (Ada Lovelace) |
| Multiprocessadores | 24 SMs |
| Runtime CUDA | 12.9 |
| Compilação do kernel | NVRTC, em tempo de execução |

### O que não existia na máquina *na hora deste spike*

- **Nenhum compilador C++** — nem MSVC (`cl`), nem `g++`, nem `clang++`
- **CUDA Toolkit não instalado** — `nvcc` ausente

O spike contornou isso: os headers e o runtime do CUDA vieram por `pip install cupy-cuda12x[ctk]`, sem
instalação de sistema. O kernel é **CUDA C de verdade**, compilado pelo NVRTC em tempo de execução — não é
uma abstração que esconde a GPU.

*(Ambos foram instalados depois. Ver parte 2.)*

---

## O kernel não é um exemplo didático

Em vez de somar vetores, o spike implementa **a avaliação de população que a história H54b vai precisar**:
dada uma população de planos candidatos, cada um selecionando um subconjunto de parceiros, calcular o uplift
e o custo de cada plano e zerar a aptidão dos que estouram o orçamento.

Isso significa que o spike não só respondeu "a GPU funciona?", mas também "a GPU funciona **para o nosso
problema**?".

Código em [`spike_gpu.py`](spike_gpu.py).

---

## Medições

Cenário de referência do RNF01: **2.000 parceiros**, população variável, média de 5 execuções.
Baseline de CPU: **NumPy**. Transferência medida **uma vez**, a frio.

| Planos | CPU (ms) | Envio | Kernel | Volta | GPU total | Ganho do kernel | **Ganho total** | Confere |
|---:|---:|---:|---:|---:|---:|---:|---:|:--:|
| 256 | 1,20 | 1,15 | 0,12 | 0,12 | 1,38 | 10,4x | **0,9x** | sim |
| 1.024 | 3,55 | 1,10 | 0,11 | 0,06 | 1,28 | 31,1x | **2,8x** | sim |
| 4.096 | 15,41 | 2,62 | 0,11 | 0,07 | 2,81 | 134,7x | **5,5x** | sim |
| 16.384 | 74,15 | 7,96 | 0,39 | 0,15 | 8,50 | 190,4x | **8,7x** | sim |
| 65.536 | 275,67 | 32,53 | 1,42 | 0,23 | 34,18 | 194,3x | **8,1x** | sim |

---

## Corretude

Todas as linhas conferem contra o cálculo equivalente em NumPy, com tolerância relativa de 0,1%.

A diferença não é zero e não deveria ser: em `float32`, a GPU soma sequencialmente dentro de cada thread
enquanto o NumPy usa BLAS, com ordem de soma diferente. O RNF02 aceita 2% de diferença no uplift, então
0,1% é uma margem confortável.

---

## Como reproduzir

```bash
cd nucleo
python -m venv .venv && .venv/Scripts/activate      # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
python spike/spike_gpu.py
```

Sem GPU compatível, o script falha na importação do CuPy — o que é esperado. A degradação para CPU prevista
no RNF06 é responsabilidade do otimizador (H56), não deste spike.

---

# Parte 2 — validação do toolchain nativo

Com MSVC e CUDA Toolkit instalados, o mesmo trabalho foi reescrito em C++ puro para responder três
perguntas que a parte 1 não podia responder:

1. `nvcc` + MSVC funcionam nesta máquina? (a H54 depende disso)
2. Quanto entrega o **OpenMP**, o caminho do RNF06 que o spike original não cobria?
3. Como a GPU se compara **contra a CPU paralela**, e não só contra a serial?

| Item | Valor |
|---|---|
| Compilador hospedeiro | MSVC 19.44.35229, x64 (Build Tools 2022) |
| CUDA Toolkit | release 13.4, V13.4.59 |
| Threads de CPU | 16 |
| Compilação do kernel | `nvcc -O2 -arch=native`, antecipada |

Código em [`teste_openmp.cpp`](teste_openmp.cpp) e [`teste_cuda.cu`](teste_cuda.cu).
Um comando roda tudo: `construir.bat`.

### O caminho do projeto tem acento, e o `cmd` não gosta

`cl` e `nvcc` só funcionam depois do `vcvars64.bat`, e encadear isso com `&&` numa linha só falha quando o
caminho tem `á`. Por isso existem [`ambiente.bat`](ambiente.bat) (carrega o ambiente do MSVC e põe o CUDA
no `PATH`, nessa ordem — o `nvcc` usa o `cl` como hospedeiro) e [`construir.bat`](construir.bat). **Não
chame `cl` ou `nvcc` soltos**; use o script.

---

## Medição do OpenMP

Serial contra paralelo **no mesmo processo e no mesmo cenário**, para o ganho ser do paralelismo e não de
diferença de linguagem ou de dados. Mediana de 3 execuções.

| Planos | Serial (ms) | OpenMP (ms) | **Ganho** | Confere |
|---:|---:|---:|---:|:--:|
| 256 | 0,53 | 0,05 | **10,4x** | sim |
| 1.024 | 2,37 | 0,24 | **10,0x** | sim |
| 4.096 | 9,39 | 1,07 | **8,7x** | sim |
| 16.384 | 34,40 | 3,93 | **8,7x** | sim |
| 65.536 | 136,97 | 14,98 | **9,3x** | sim |

Com 16 threads, ~9x é o esperado: o ganho cai conforme a população cresce e o trabalho passa a ser limitado
por banda de memória, não por núcleo disponível. A igualdade com o resultado serial é **exata** — cada plano
é somado pela mesma thread na mesma ordem.

**A medição paralela oscila mais que a serial.** O tempo serial repete em 0,1% entre execuções; o paralelo
variou de 3,88 a 5,64 ms nos 16.384 planos (ganho entre 6,1x e 8,9x). É contenção de memória e escalonamento
de threads, não defeito. Por isso a tabela traz mediana de 3, e o benchmark da H57 precisa reportar
dispersão, não um número só.

---

## Medição do CUDA por `nvcc`

Mesmo cenário. Baseline de CPU: **C++ serial**. Transferência medida **repetidamente, a quente** — o
oposto da parte 1, de propósito. Mediana de 3 execuções.

| Planos | CPU serial (ms) | Envio | Kernel | Volta | GPU total | Ganho do kernel | **Ganho total** | Confere |
|---:|---:|---:|---:|---:|---:|---:|---:|:--:|
| 256 | 0,53 | 0,12 | 0,104 | 0,02 | 0,25 | 5,1x | **2,1x** | sim |
| 1.024 | 2,12 | 0,24 | 0,102 | 0,03 | 0,37 | 20,8x | **5,7x** | sim |
| 4.096 | 8,48 | 0,73 | 0,101 | 0,02 | 0,85 | 84,0x | **10,0x** | sim |
| 16.384 | 33,94 | 2,73 | 0,353 | 0,04 | 3,14 | 96,1x | **10,8x** | sim |
| 65.536 | 135,22 | 10,66 | 1,354 | 0,09 | 12,10 | 99,9x | **11,2x** | sim |

**Corretude: erro relativo exatamente zero em todas as linhas.** Aqui CPU e GPU somam na mesma ordem
sequencial, em `float32`, então a igualdade é bit a bit — diferente da parte 1, onde o NumPy soma por BLAS
em outra ordem e produz os 0,1% de diferença.

**Até 4.096 planos o kernel custa os mesmos 0,10 ms.** Não é o cálculo que está sendo medido nessa faixa, é
a latência de lançamento: a GPU está ociosa esperando trabalho. Só a partir de 16.384 o tempo começa a
crescer com o tamanho.

---

## Por que as duas tabelas de GPU não batem

Comparar a linha de 65.536 das duas partes: envio de 32,53 ms na parte 1 contra 10,66 ms na parte 2, CPU de
275,67 ms contra 135,22 ms. Nenhuma das duas está errada — **elas medem coisas diferentes**, e registrar
isso evita alguém "corrigir" a tabela certa daqui a dois meses.

| | Parte 1 (NVRTC) | Parte 2 (`nvcc`) |
|---|---|---|
| Baseline de CPU | NumPy, vetorizado | C++ serial, laço escalar |
| Transferência | uma vez, a frio | repetida, a quente |
| Kernel | idêntico | idêntico |

O baseline de C++ ser **2x mais rápido que o de NumPy** é plausível: o laço escalar mantém as somas em
registrador, enquanto a versão vetorizada materializa arrays intermediários e fica limitada por memória.
Não foi medido diretamente — fica como hipótese, não como fato.

As duas medições de transferência são úteis por motivos diferentes: **a frio** é o que se paga ao enviar a
população uma vez no início de uma execução; **a quente** é o que se pagaria a cada geração, se a população
fosse e voltasse no laço. O segundo número é o que dimensiona a decisão da H54c.

---

## Três conclusões que mudam o plano

### 1. A meta de 5x é atingível — com folga no kernel, apertada no total

O kernel isolado chega a **194x** (parte 1) ou **100x** (parte 2, contra um baseline de CPU duas vezes mais
rápido). Mas o número honesto é o **ganho total**, que inclui transferir os dados para a GPU e trazer o
resultado de volta: **8,7x** e **11,2x** respectivamente. É o que vale para o RNF02, e supera a meta de 5x
nos dois caminhos.

### 2. Com população pequena, a GPU perde — e o concorrente real é o OpenMP, não o serial

O RNF02 mede contra o **baseline serial**, e contra ele a GPU ganha em toda a faixa medida na parte 2. Mas
a pergunta que a banca vai fazer é outra: *vale a pena a GPU se a CPU também está paralela?* Sobrepondo as
duas tabelas:

| Planos | OpenMP (ms) | GPU total (ms) | Kernel só (ms) | GPU total ÷ OpenMP | Kernel ÷ OpenMP |
|---:|---:|---:|---:|:--:|:--:|
| 256 | 0,05 | 0,25 | 0,104 | **0,2x** | 0,5x |
| 1.024 | 0,24 | 0,37 | 0,102 | **0,6x** | 2,4x |
| 4.096 | 1,07 | 0,85 | 0,101 | **1,3x** | 10,6x |
| 16.384 | 3,93 | 3,14 | 0,353 | **1,2x** | 11,1x |
| 65.536 | 14,98 | 12,10 | 1,354 | **1,1x** | 11,1x |

Duas leituras, e a segunda é a que importa:

- **Abaixo de ~4.000 planos, 16 threads de CPU batem a GPU.** Em 256 planos o OpenMP é 5x mais rápido que
  a GPU inteira e 2x mais rápido que o kernel sozinho.
- **Acima disso, a GPU com transferência a cada geração ganha só 1,1x a 1,3x do OpenMP.** Praticamente
  nada. Mas **sem** a transferência — só o kernel — ela ganha **11x**.

Isso confirma empiricamente a armadilha já registrada no `CLAUDE.md`, e dá o número concreto que faltava.
**O benchmark da H57 precisa incluir essa faixa**: mostrar onde a GPU perde é mais honesto, e mais
interessante para a banca, do que mostrar só o ponto em que ela ganha.

### 3. A transferência é o gargalo, não o cálculo — e isso decide a arquitetura da H54c

Com 65.536 planos, a transferência consome **88%** do tempo total de GPU na parte 2 (10,75 ms de 12,10) e
**95%** na parte 1, onde ela era medida a frio. Nos dois casos, a mesma conclusão.

Somada à linha anterior, ela deixa de ser uma observação e vira requisito de projeto: **manter a população
na GPU entre as gerações não é otimização, é a única coisa que justifica usar GPU.** Com a transferência no
laço, a GPU empata com o OpenMP; sem ela, ganha 11x. Transferindo uma vez no início e recuperando só o
melhor plano no fim, o ganho total se aproxima do ganho do kernel.

Sem este spike, essa decisão só apareceria durante a implementação da Sprint 11 — e provavelmente depois de
uma versão já escrita do jeito errado.

---

## Como reproduzir a parte 2

```bash
nucleo/spike/construir.bat
```

Sem argumento compila e roda os dois testes; `construir.bat openmp` ou `construir.bat cuda` roda um só.
Exige MSVC Build Tools com a carga de trabalho C++ e o CUDA Toolkit instalados — os caminhos estão no
`ambiente.bat` e podem precisar de ajuste em outra máquina.

---

## O que fica em aberto

Nada do que a H47 se propôs a responder. Os dois caminhos de paralelismo estão validados nesta máquina, com
resultado conferido contra a CPU.

O que **não** foi validado aqui, e continua sendo trabalho das histórias correspondentes:

- **A metaheurística em si** (H52 a H54). Estes testes avaliam uma população; não a evoluem. Seleção,
  cruzamento e mutação ainda não existem.
- **A degradação automática para CPU sem GPU** (RNF06, H56). A capacidade de CPU paralela está provada, o
  chaveamento não.
- **O empacotamento.** Nada disso roda dentro do container ainda — o `nvcc` é usado na máquina, não na
  imagem. *Respondido na parte 3.*

Decisões registradas em ADR-005 e ADR-006, em
[`docs/07-arquitetura-preliminar.md`](../../docs/07-arquitetura-preliminar.md).

---

# Parte 3 — o núcleo dentro do contêiner da API

**Issue:** #123 · **Data:** 26/09/2026 · **Decisão:** ADR-012

A API roda num contêiner Linux (`python:3.11-slim`); o núcleo em C++ só tinha sido compilado no Windows. A
pergunta, antes da Sprint 10: **o mesmo código compila em Linux e roda dentro da imagem da API, com a GPU
da máquina?** Se não rodasse, o núcleo teria de ficar num serviço à parte, ou fora do Docker.

## Ambiente medido

| Item | Valor |
|---|---|
| Docker Desktop | 29.6.2, backend WSL2 (kernel 6.18), runtime `nvidia` registrado |
| Imagem de compilação | `nvidia/cuda:13.4.1-devel-ubuntu24.04` — a mesma versão do toolkit do Windows |
| Compiladores | `g++ -O2 -fopenmp` e `nvcc -O2 -arch=all-major`, com o `cudart` estático |
| Imagem de execução | `python:3.11-slim` (Debian 13, glibc 2.41), a base da API |
| GPU vista do contêiner | NVIDIA GeForce RTX 4060, driver 616.92, capacidade 8.9 |

## O que funcionou, e como

- **A GPU aparece no contêiner com `--gpus all`**, inclusive numa imagem que não é da NVIDIA. O Docker
  Desktop entrega o driver pelo WSL2; não foi preciso variável de ambiente nem configuração.
- **O binário carrega o runtime do CUDA dentro de si** (`cudart` estático, o padrão do `nvcc`). Por isso
  roda na imagem da API, e não só na da NVIDIA: o `ldd` não lista nenhuma biblioteca CUDA.
- **Sem GPU, o binário recusa de forma limpa**: "CUDA driver version is insufficient", código de saída 1.
  É o sinal que a API precisa para cair para CPU (RNF06). O OpenMP roda normalmente sem GPU.
- **A reserva de GPU pelo Compose funciona num arquivo à parte** (`deploy.resources.reservations.devices`).
  Declarada no `docker-compose.yml` principal, ela impediria o contêiner de subir numa máquina sem placa
  NVIDIA — e o README precisa funcionar em qualquer uma (H72).

## Tamanho

| Imagem | Tamanho |
|---|--:|
| `nvidia/cuda:13.4.1-runtime` com os binários (primeira tentativa) | 5,1 GB |
| `python:3.11-slim` com os binários e o `libgomp1` | **201 MB** — a base sozinha tem 200 MB |
| Os binários: `teste_cuda` (com o código de todas as arquiteturas) e `teste_openmp` | 1,1 MB e 22 KB |

A imagem `runtime` da NVIDIA traz todas as bibliotecas matemáticas do CUDA, que o núcleo não usa. Com o
`cudart` estático, o núcleo acrescenta cerca de 1 MB à imagem da API, que hoje tem 1,6 GB por causa do
PyTorch. A imagem `devel`, com o compilador, só é baixada para compilar.

## Medições

Mesmos programas e cenário das partes 1 e 2, mediana de 3 execuções, dentro do contêiner.

**OpenMP** (16 threads)

| Planos | Serial (ms) | OpenMP (ms) | Ganho | Windows, parte 2 |
|---:|---:|---:|---:|---:|
| 256 | 0,71 | 0,85 | **0,8x** | 10,4x |
| 1.024 | 2,35 | 0,38 | **6,0x** | 10,0x |
| 4.096 | 9,49 | 1,72 | **5,5x** | 8,7x |
| 16.384 | 37,81 | 5,79 | **6,4x** | 8,7x |
| 65.536 | 151,11 | 19,13 | **7,9x** | 9,3x |

**CUDA**

| Planos | CPU serial (ms) | Envio | Kernel | Volta | GPU total | Ganho do kernel | **Ganho total** | Windows |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 0,67 | 0,17 | 0,106 | 0,07 | 0,35 | 6,3x | **1,9x** | 2,1x |
| 1.024 | 2,40 | 0,35 | 0,105 | 0,06 | 0,52 | 22,9x | **4,6x** | 5,7x |
| 4.096 | 9,30 | 1,03 | 0,104 | 0,06 | 1,19 | 89,4x | **7,8x** | 10,0x |
| 16.384 | 36,72 | 3,49 | 0,370 | 0,08 | 3,95 | 99,2x | **9,3x** | 10,8x |
| 65.536 | 150,80 | 14,84 | 1,413 | 0,15 | 16,39 | 106,7x | **9,2x** | 11,2x |

Corretude: **erro relativo zero** em todas as linhas, como no Windows.

## O que os números dizem

1. **O kernel é o mesmo dentro e fora do contêiner**: 1,41 ms contra 1,35 ms nos 65.536 planos. O WSL2 não
   atrapalha o cálculo na GPU.
2. **A transferência custa ~40% a mais no contêiner** (14,8 ms contra 10,7 ms) — a cópia entre a memória e
   a GPU atravessa a camada do WSL2. É mais um motivo para a exigência da H54c: a população **fica na GPU**
   entre gerações, e só o melhor plano volta.
3. **O OpenMP do GCC paga para subir as threads**, e com pouco trabalho isso não se paga: 0,8x em 256
   planos, contra 10,4x do MSVC. Nos tamanhos que importam o ganho volta (7,9x), menor que no Windows. O
   benchmark da Sprint 11 precisa ser medido **no contêiner**, que é onde o sistema roda, e não no Windows.
4. **O serial é ~10% mais lento** com g++ do que com MSVC (151 ms contra 137 ms). O denominador do *speedup*
   do RNF02 é o baseline em Python, e não este, mas a comparação honesta entre os modos precisa dos três
   compilados no mesmo lugar.

## Passar a instância ao núcleo

O núcleo vai ser um **executável chamado pela API**, com a instância na entrada padrão e o plano na saída
(ADR-012). O custo disso foi medido com o cenário de referência — 2.000 parceiros, 5 ações, ganhos em
centavos, 76 KB de texto —, mandado a um programa que só lê e soma (`eco.cpp`, `ida_e_volta.py`):

| Medida | Valor |
|---|---:|
| Ida e volta por subprocesso, 30 vezes | mediana de **1,9 a 2,5 ms** entre duas rodadas |

Contra os 27 s do baseline serial com 2.000 parceiros (`docs/medicoes/otimizador.md`), ou mesmo contra uma
busca de 1 s na GPU, é desprezível.

## Como reproduzir a parte 3

```bash
docker build -t gih-spike nucleo/spike
docker run --rm --gpus all gih-spike teste_cuda
docker run --rm --gpus all gih-spike teste_openmp
docker run --rm gih-spike python /spike/ida_e_volta.py
docker run --rm gih-spike teste_cuda        # sem GPU: a recusa, com saída 1
```

O primeiro build baixa a imagem `devel` da NVIDIA (alguns GB) e levou 137 s nesta máquina. As imagens da
NVIDIA vêm com a licença *NVIDIA Deep Learning Container License*: proprietária, na mesma exceção do CUDA
Toolkit (`CLAUDE.md`, regra 2.8). Nenhuma camada delas vai para a imagem da API — só o binário, com o
`cudart`, que a licença do CUDA permite redistribuir.
