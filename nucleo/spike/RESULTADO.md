# Spike de GPU — resultado

**História:** H47 · Sprint 3
**Data:** 15/09/2026
**Objetivo:** retirar o risco **R1** do cronograma — a cadeia de compilação de GPU funcionar nesta máquina.

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
  imagem.

Decisões registradas em ADR-005 e ADR-006, em
[`docs/07-arquitetura-preliminar.md`](../../docs/07-arquitetura-preliminar.md).
