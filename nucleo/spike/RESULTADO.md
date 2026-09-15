# Spike de GPU — resultado

**História:** H47 · Sprint 3
**Data:** 15/09/2026
**Objetivo:** retirar o risco **R1** do cronograma — a cadeia de compilação de GPU funcionar nesta máquina.

---

## Veredito

**O risco está retirado.** Kernel CUDA compila, executa na GPU, é invocado a partir do Python e produz o
mesmo resultado do cálculo em CPU. A meta de *speedup* do RNF02 (mínimo de 5x) foi **atingida e superada**
em medição real, oito semanas antes de ser necessária.

---

## Ambiente medido

| Item | Valor |
|---|---|
| GPU | NVIDIA GeForce RTX 4060, 8 GB |
| Capacidade de computação | 8.9 (Ada Lovelace) |
| Multiprocessadores | 24 SMs |
| Runtime CUDA | 12.9 |
| Compilação do kernel | NVRTC, em tempo de execução |

### O que **não** existe nesta máquina

- **Nenhum compilador C++** — nem MSVC (`cl`), nem `g++`, nem `clang++`
- **CUDA Toolkit não instalado** — `nvcc` ausente

O spike contornou isso: os headers e o runtime do CUDA vieram por `pip install cupy-cuda12x[ctk]`, sem
instalação de sistema. O kernel é **CUDA C de verdade**, compilado pelo NVRTC em tempo de execução — não é
uma abstração que esconde a GPU.

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

| Planos | CPU (ms) | Envio | Kernel | Volta | GPU total | Ganho do kernel | **Ganho total** | Confere |
|---:|---:|---:|---:|---:|---:|---:|---:|:--:|
| 256 | 1,20 | 1,15 | 0,12 | 0,12 | 1,38 | 10,4x | **0,9x** | sim |
| 1.024 | 3,55 | 1,10 | 0,11 | 0,06 | 1,28 | 31,1x | **2,8x** | sim |
| 4.096 | 15,41 | 2,62 | 0,11 | 0,07 | 2,81 | 134,7x | **5,5x** | sim |
| 16.384 | 74,15 | 7,96 | 0,39 | 0,15 | 8,50 | 190,4x | **8,7x** | sim |
| 65.536 | 275,67 | 32,53 | 1,42 | 0,23 | 34,18 | 194,3x | **8,1x** | sim |

---

## Três conclusões que mudam o plano

### 1. A meta de 5x é atingível — com folga no kernel, apertada no total

O kernel isolado chega a **194x**. Mas o número honesto é o **ganho total**, que inclui transferir os dados
para a GPU e trazer o resultado de volta: **8,7x** no melhor ponto. É o que vale para o RNF02, e ainda assim
supera a meta de 5x.

### 2. Com população pequena, a GPU **perde** — e isso foi medido, não suposto

Com 256 planos o ganho total é **0,9x**: a GPU é mais lenta que a CPU. O custo de transferência domina, e o
kernel não tem trabalho suficiente para compensá-lo.

O ponto de virada fica em torno de **1.000 planos**. Abaixo disso, usar GPU piora o desempenho.

Isso confirma empiricamente a armadilha já registrada no `CLAUDE.md` — e dá o número concreto que faltava.
**O benchmark da H57 precisa incluir essa faixa**: mostrar onde a GPU perde é mais honesto, e mais
interessante para a banca, do que mostrar só o ponto em que ela ganha.

### 3. A transferência é o gargalo, não o cálculo

Com 65.536 planos: 32,5 ms transferindo contra 1,4 ms calculando. **A transferência consome 95% do tempo.**

Isso define a arquitetura da H54c: a população precisa **permanecer na GPU entre as gerações** da
metaheurística, em vez de ir e voltar a cada iteração. Transferindo uma vez no início e recuperando só o
melhor plano no fim, o ganho total se aproxima do ganho do kernel.

Sem este spike, essa decisão só apareceria durante a implementação da Sprint 11 — e provavelmente depois de
uma versão já escrita do jeito errado.

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

## O que fica em aberto

O spike provou o caminho **CUDA via NVRTC**. Ele **não** cobre a história H53, que pede o otimizador em
**C++ com OpenMP** — e para isso ainda falta um compilador C++ na máquina, que hoje não existe em nenhuma
forma.

Decisão registrada em ADR-005, em [`docs/07-arquitetura-preliminar.md`](../../docs/07-arquitetura-preliminar.md).
