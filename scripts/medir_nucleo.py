"""Mede o núcleo em C++: o ganho do OpenMP sobre o serial (H53b), a transferência
para a GPU (H54a), o kernel de avaliação da população (H54b) e a busca inteira
na GPU (H54c), com o RNF01 e o RNF02.

**O ganho é lido contra o C++ serial**, e não contra o Python. O C++ serial já é
dezenas de vezes mais rápido que o mesmo algoritmo em Python (H53a), e comparar
o OpenMP com o Python mediria o compilador junto com o paralelismo (`CLAUDE.md`
§7, ADR-012). A exceção é o RNF02, que pede o ganho da GPU sobre o baseline em
Python: ele é medido aqui, no cenário de referência, na mesma instância.

**A GPU tem um custo fixo**, que o executável informa à parte: iniciar o driver
e criar o contexto, uma vez por processo, antes de qualquer conta. O relatório
mostra o laço sem ele, contra o OpenMP, e a busca inteira com ele.

**Mede-se no contêiner**, que é onde o sistema roda (ADR-012): o OpenMP do GCC
no WSL2 ganha menos que o do MSVC no Windows. Medido fora dele, o relatório diz
isso logo no topo.

**O protocolo** segue as armadilhas de benchmark do `CLAUDE.md` §7:

- uma rodada de aquecimento, descartada;
- várias rodadas, cada uma com todos os modos intercalados — serial, OpenMP com
  1 thread, com 2... —, para que uma oscilação da máquina caia sobre todos;
- mediana, e a faixa do menor ao maior. O ganho de cada rodada é o serial dela
  dividido pelo OpenMP dela, e a faixa do ganho vem daí;
- o tempo é o da busca, medido pelo próprio executável, sem o processo subir e
  ler a entrada; o do processo inteiro vem numa coluna à parte;
- **em toda execução, o plano do OpenMP e o da GPU são conferidos contra o do
  serial**: genes, avaliação e gerações. Se um divergir, o script para sem
  escrever o relatório.

**A instância é sintética, sem banco**: a de `gih_nucleo.cenario`, a mesma
que a tela de benchmark mede (H57), com as cinco ações do catálogo do gerador.
- O ganho segue a RN10, e a campanha tem as cotas da RN11.
- O tempo do genético depende do tamanho da instância, e não dos valores. A
  qualidade do plano, que depende dos valores, é medida pelo caminho de verdade
  em `medir_otimizador.py`.

**A transferência** é medida pelo próprio executável (`gih-nucleo transferir`):
a instância e a população inicial vão para a GPU e voltam, conferidas byte a
byte. **O kernel** também (`gih-nucleo avaliar`): uma população do tamanho da
busca é avaliada na GPU e pelo `avaliar` em C++, uma contra a outra, e cada
avaliação ainda é conferida aqui contra o `avaliar` do Python. Sem GPU — sem
`--gpus all`, ou numa máquina sem placa —, as seções dizem por quê, e o resto
do relatório sai igual.

Uso, da raiz do repositório:

    docker build -t gih-nucleo nucleo
    docker run --rm --gpus all -v "$PWD:/repo" -w /repo gih-nucleo python scripts/medir_nucleo.py
"""
from __future__ import annotations

import argparse
import os
import platform
import random
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "nucleo"))

from gih_nucleo import (  # noqa: E402
    Instancia,
    cenario,
    avaliar,
    nativo,
    verificar_viabilidade,
)
from gih_nucleo import serial as genetico  # noqa: E402

SEMENTE_DA_REDE = cenario.SEMENTE
PARCEIROS = [500, 2000, 10000]  # o cenário de referência e a carga do RNF04 em volta
REPETICOES = 15
BASELINE = 3  # execuções do Python no cenário de referência, para o RNF02


def montar_instancia(parceiros: int) -> Instancia:
    """A campanha de `parceiros` elegíveis e cinco ações do cenário do benchmark."""
    return cenario.sintetico(parceiros, 5, SEMENTE_DA_REDE)


@dataclass
class Medida:
    busca: list[float] = field(default_factory=list)  # segundos, do executável
    processo: list[float] = field(default_factory=list)  # segundos, de fora
    contexto: list[float] = field(default_factory=list)  # segundos, só na GPU: dentro da busca


def _rodar(inst, executavel, modo, threads, referencia=None):
    inicio = time.perf_counter()
    r = nativo.otimizar(inst, modo=modo, threads=threads, executavel=executavel)
    processo = time.perf_counter() - inicio
    if referencia is not None and (
        r.genes != referencia.genes
        or r.avaliacao != referencia.avaliacao
        or r.geracoes != referencia.geracoes
    ):
        como = f"O modo {modo}" + (f" com {threads} threads" if threads else "")
        raise SystemExit(
            f"{como} deu um plano diferente do serial ({inst.parceiros} parceiros). "
            "Relatório não escrito: é defeito."
        )
    return r, processo


def medir(parceiros: int, threads: list[int], repeticoes: int, executavel: str, com_gpu: bool):
    inst = montar_instancia(parceiros)
    if verificar_viabilidade(inst) is not None:
        raise SystemExit(f"A campanha de {parceiros} parceiros saiu inviável; ajuste o script.")
    referencia, _ = _rodar(inst, executavel, "serial", None)
    configuracoes = [("serial", None)] + [("openmp", t) for t in threads]
    # A GPU entra na mesma rodada, intercalada com os outros: parte do repouso,
    # como no uso de verdade, em que ela espera parada pelo próximo cálculo.
    if com_gpu:
        configuracoes.append(("cuda", None))
    medidas = {c: Medida() for c in configuracoes}

    for rodada in range(repeticoes + 1):
        for modo, t in configuracoes:
            r, processo = _rodar(inst, executavel, modo, t, referencia)
            if rodada == 0:
                continue  # aquecimento
            medidas[(modo, t)].busca.append(r.segundos)
            medidas[(modo, t)].processo.append(processo)
            medidas[(modo, t)].contexto.append(r.contexto_s)
        if rodada:
            print(f"  rodada {rodada}/{repeticoes}", flush=True)
    return inst, referencia, medidas


# ------------------------------------------------------------ o relatório
def _mil(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _ms(segundos: float) -> str:
    if segundos >= 1:
        return f"{segundos:.2f} s".replace(".", ",")
    ms = segundos * 1000
    return (f"{ms:.1f}" if ms < 100 else f"{ms:.0f}").replace(".", ",") + " ms"


def _x(v: float) -> str:
    return f"{v:.1f}x".replace(".", ",")


def _lista(itens: list[str]) -> str:
    """'500', '500 e 2.000', '500, 2.000 e 10.000'."""
    return itens[0] if len(itens) == 1 else f"{', '.join(itens[:-1])} e {itens[-1]}"


def _curto(ms: float) -> str:
    """Tempos de transferência: abaixo de um milissegundo, em microssegundos."""
    if ms < 1:
        return f"{ms * 1000:.0f} µs"
    return f"{ms:.2f} ms".replace(".", ",")


def _tamanho(n_bytes: int) -> str:
    if n_bytes < 1024 * 1024:
        return f"{n_bytes / 1024:.0f} KiB"
    return f"{n_bytes / (1024 * 1024):.1f} MiB".replace(".", ",")


def _faixa_curta(valores) -> str:
    return (
        f"**{_curto(statistics.median(valores))}** "
        f"({_curto(min(valores))} a {_curto(max(valores))})"
    )


def populacao_de_medicao(inst, semente: int) -> list[tuple[int, ...]]:
    """Uma população do tamanho da busca, com a densidade de ações da inicial.

    A população inicial sorteia uma ação para cerca de K de cada N parceiros
    (`genetico.hpp`, `sorteado`); aqui é igual, com o gerador do Python — o
    kernel lê todos os genes de qualquer jeito, e o tempo depende de N.
    """
    rng = random.Random(semente)
    densidade = inst.maximo_acoes / inst.parceiros
    return [
        tuple(rng.randint(1, inst.acoes) if rng.random() < densidade else 0
              for _ in range(inst.parceiros))
        for _ in range(genetico.PARTIDAS * genetico.POPULACAO)
    ]


def _secao_kernel(capacidades, avaliacoes, repeticoes) -> list[str]:
    linhas = ["## Avaliação da população na GPU — H54b", ""]
    if capacidades.gpu is None:
        return linhas + [f"Não medida: {capacidades.sem_gpu}", ""]
    individuos = genetico.PARTIDAS * genetico.POPULACAO
    linhas += [
        f"Os {individuos} indivíduos de uma geração de todas as partidas, avaliados de uma vez: "
        "um bloco de 256 threads por indivíduo, com ganho, custo, ações, cauda, contagem por "
        "categoria e violação. A mesma população passa pelo `avaliar` em C++, na CPU, em série — "
        "e as duas são conferidas uma contra a outra no executável, e contra o `avaliar` do "
        f"Python aqui. Mediana de {repeticoes} repetições, e a faixa.",
        "",
        "O kernel é medido pela própria GPU, sem a transferência (que é a seção de cima), e **em "
        "lotes de lançamentos seguidos**, como o laço da H54c lança uma geração depois da "
        "outra: cada medida é a média por lançamento num lote de uns 2 ms. Um lançamento isolado, "
        "com a placa esperando a CPU entre um e outro, mede a latência, e ela oscilou de 11 a "
        "88 µs com 500 parceiros, conforme o relógio da placa subia ou não.",
        "",
        "| Parceiros | Kernel na GPU, por lançamento | `avaliar` na CPU, em série | Ganho do kernel "
        "| Iguais ao Python |",
        "|--:|--:|--:|--:|--:|",
    ]
    for n, r, iguais in avaliacoes:
        ganho = statistics.median(r.cpu_ms) / statistics.median(r.kernel_ms)
        linhas.append(
            f"| {_mil(n)} | {_faixa_curta(r.kernel_ms)} | {_faixa_curta(r.cpu_ms)} "
            f"| **{_x(ganho)}** | {iguais} de {len(r.avaliacoes)} |"
        )
    linhas += [
        "",
        "- **O kernel sozinho não é o modo GPU.** A busca na GPU (H54c) também sorteia, "
        "cruza e muta na placa, dentro do mesmo kernel, e paga o contexto da placa. O ganho "
        "sobre o OpenMP está na seção da busca inteira.",
        "",
    ]
    return linhas


def _secao_gpu(capacidades, transferencias, resultados, threads, repeticoes) -> list[str]:
    linhas = ["## Transferência para a GPU — H54a", ""]
    if capacidades.gpu is None:
        return linhas + [
            f"Não medida: {capacidades.sem_gpu} Com placa NVIDIA, rode o contêiner com "
            "`--gpus all`.",
            "",
        ]
    t_ref = _t_ref(threads)
    busca = {
        inst.parceiros: statistics.median(medidas[("openmp", t_ref)].busca) * 1000
        for inst, _ref, medidas in resultados
    }
    linhas += [
        f"A instância e a população inicial das {genetico.PARTIDAS} partidas "
        f"({genetico.PARTIDAS} × {genetico.POPULACAO} indivíduos, um byte por gene) vão para a "
        f"{capacidades.gpu.nome} e voltam. O executável confere o que voltou byte a byte, e com "
        "uma conta feita na própria GPU, e sai como defeito se não bater. Mediana de "
        f"{repeticoes} repetições, depois de uma de aquecimento, e a faixa.",
        "",
        "| Parceiros | Instância | População | Envio das duas | Volta da população "
        f"| Volta de um indivíduo | Busca no OpenMP, {t_ref} threads |",
        "|--:|--:|--:|--:|--:|--:|--:|",
    ]
    for n, t in transferencias:
        linhas.append(
            f"| {_mil(n)} | {_tamanho(t.bytes_instancia)} | {_tamanho(t.bytes_populacao)} "
            f"| {_faixa_curta(t.envio_ms)} | {_faixa_curta(t.volta_ms)} "
            f"| {_faixa_curta(t.volta_um_ms)} | {_curto(busca[n])} |"
        )
    referencia = next(((n, t) for n, t in transferencias if n == 2000), transferencias[-1])
    n, t = referencia
    por_busca = statistics.median(t.envio_ms) + statistics.median(t.volta_um_ms)
    fracao = f"{por_busca / busca[n] * 100:.1f}".replace(".", ",")
    # A população inteira de volta a cada geração, como no spike: só a volta, sem
    # contar o envio de novo — é o piso do que a residência evita.
    a_cada_geracao = statistics.median(t.volta_ms) * genetico.GERACOES
    fracao_geracao = f"{a_cada_geracao / busca[n] * 100:.0f}"
    linhas += [
        "",
        "- **A busca na GPU (H54c) paga, no máximo, um envio e a volta de um indivíduo**, porque "
        f"a população fica residente entre gerações (ADR-006). Com {_mil(n)} parceiros, "
        f"{_curto(por_busca)}: {fracao}% da busca inteira no OpenMP. Na verdade paga menos: a "
        "população nem vai, porque é sorteada na placa; vão a instância e os dois gulosos.",
        "- **Trazer a população inteira a cada geração**, como no spike, custaria só na volta "
        f"{_curto(a_cada_geracao)} por busca ({genetico.GERACOES} gerações): "
        f"{fracao_geracao}% da busca inteira no OpenMP, antes de o kernel fazer qualquer conta. "
        "É o que a residência evita.",
        "",
    ]
    return linhas


def _cpuinfo(campo: str) -> str | None:
    """Um campo do /proc/cpuinfo, que só existe em Linux — onde se mede."""
    try:
        for linha in Path("/proc/cpuinfo").read_text().splitlines():
            if linha.split(":", 1)[0].strip() == campo:
                return linha.split(":", 1)[1].strip()
    except OSError:
        pass
    return None


def _secao(inst, referencia, medidas) -> list[str]:
    med = statistics.median
    serial = medidas[("serial", None)]
    t_serial = med(serial.busca)
    linhas = [
        f"## {_mil(inst.parceiros)} parceiros",
        "",
        f"{len(inst.custo)} ações · máximo de {inst.maximo_acoes} ações · plano com "
        f"{referencia.avaliacao.acoes} ações · {referencia.geracoes} gerações no total das "
        f"{referencia.partidas} partidas.",
        "",
        "| Modo | Threads | Tempo da busca | Faixa | Ganho sobre o serial | Faixa do ganho "
        "| Ganho por thread | Processo inteiro |",
        "|---|--:|--:|--:|--:|--:|--:|--:|",
        f"| C++ serial | 1 | **{_ms(t_serial)}** | {_ms(min(serial.busca))} a "
        f"{_ms(max(serial.busca))} | — | — | — | {_ms(med(serial.processo))} |",
    ]
    for (modo, t), m in medidas.items():
        if modo == "serial":
            continue
        ganho = t_serial / med(m.busca)
        pares = [s / o for s, o in zip(serial.busca, m.busca, strict=True)]
        # Na GPU, "threads" não se compara com as do processador: são dezenas de
        # milhares, e o ganho por thread não diz nada.
        if modo == "cuda":
            nome, threads, por_thread = "GPU, com o contexto", "—", "—"
        else:
            nome, threads, por_thread = "OpenMP", t, f"{ganho / t:.0%}"
        linhas.append(
            f"| {nome} | {threads} | {_ms(med(m.busca))} | {_ms(min(m.busca))} a "
            f"{_ms(max(m.busca))} | **{_x(ganho)}** | {_x(min(pares))} a {_x(max(pares))} "
            f"| {por_thread} | {_ms(med(m.processo))} |"
        )
    linhas += [""]
    return linhas


def _t_ref(threads: list[int]) -> int:
    """As threads do OpenMP que valem como referência: uma por núcleo físico, se
    foi medida (adendo da ADR-011); senão, a de mais threads."""
    fisicos = nativo.nucleos_fisicos()
    return fisicos if fisicos in threads else max(threads)


def _secao_busca_na_gpu(capacidades, resultados, threads) -> list[str]:
    linhas = ["## A busca inteira na GPU — H54c", ""]
    if capacidades.gpu is None or "cuda" not in capacidades.modos:
        motivo = capacidades.sem_gpu or "o executável não tem o modo cuda."
        return linhas + [f"Não medida: {motivo}", ""]
    med = statistics.median
    t_ref = _t_ref(threads)
    linhas += [
        f"O genético inteiro na {capacidades.gpu.nome}: a população nasce na placa e fica lá "
        "até o fim, e só voltam as avaliações da última geração e o plano vencedor (ADR-006). "
        "Cada geração é um kernel, com um bloco de 256 threads por indivíduo, e a placa parte do "
        "repouso em cada busca, como no uso de verdade. O plano foi conferido contra o do serial "
        "em todas as execuções.",
        "",
        "**O custo fixo, à parte.** Antes de qualquer conta, o processo inicia o driver e cria o "
        "contexto da GPU: é o que cada cálculo paga uma vez. O executável o mede, e a tabela o "
        "separa do laço.",
        "",
        f"| Parceiros | OpenMP, {t_ref} threads | GPU, só o laço | Laço contra o OpenMP "
        "| Contexto da GPU | GPU, a busca inteira | Busca inteira contra o OpenMP |",
        "|--:|--:|--:|--:|--:|--:|--:|",
    ]
    ganha, perde = [], []
    for inst, _ref, medidas in resultados:
        omp = med(medidas[("openmp", t_ref)].busca)
        gpu = medidas[("cuda", None)]
        laco = [b - c for b, c in zip(gpu.busca, gpu.contexto, strict=True)]
        inteira = med(gpu.busca)
        (ganha if inteira < omp else perde).append(_mil(inst.parceiros))
        linhas.append(
            f"| {_mil(inst.parceiros)} | {_ms(omp)} | **{_ms(med(laco))}** "
            f"| **{_x(omp / med(laco))}** "
            f"| {_ms(med(gpu.contexto))} ({_ms(min(gpu.contexto))} a {_ms(max(gpu.contexto))}) "
            f"| {_ms(inteira)} | {_x(omp / inteira)} |"
        )
    linhas += [
        "",
        "- **O laço na GPU é o mais rápido dos modos**, e o ganho cresce com o tamanho: o tempo "
        "de uma geração cresce bem menos que o número de parceiros, porque as threads de um bloco "
        "dividem os genes do indivíduo.",
        "- **Com o contexto, a GPU "
        + (f"perde para o OpenMP com {_lista(perde)} parceiros" if perde else "não perde")
        + (f" e ganha com {_lista(ganha)}" if ganha else "")
        + ".** Abaixo de 1x, o OpenMP termina antes. O contexto é o mesmo em qualquer tamanho, "
        "e só se paga quando o laço é grande.",
        "- **O modo automático escolhe a GPU mesmo assim** (adendo H54c da ADR-012): a diferença é "
        "de décimos de segundo, que a tela não sente, e a tela não promete \"o mais rápido\".",
        "",
    ]
    return linhas


def _secao_requisitos(capacidades, resultados, baseline) -> list[str]:
    """RNF01 e RNF02, no cenário de referência: 2.000 parceiros e 5 ações."""
    linhas = ["## RNF01 e RNF02 — a GPU no cenário de referência", ""]
    referencia = next((r for r in resultados if r[0].parceiros == 2000), None)
    if capacidades.gpu is None or "cuda" not in capacidades.modos or referencia is None:
        return linhas + ["Não medidos: pedem a GPU e o cenário de 2.000 parceiros.", ""]
    med = statistics.median
    inst, plano, medidas = referencia
    python, plano_python = baseline
    gpu = medidas[("cuda", None)]
    processo = med(gpu.processo)
    ganho = med(python) / processo
    ganho_python = plano_python.avaliacao.ganho
    diferenca = abs(plano.avaliacao.ganho - ganho_python) / ganho_python

    def atende(ok: bool) -> str:
        return "atende" if ok else "**não atende**"

    linhas += [
        f"{_mil(inst.parceiros)} parceiros e {len(inst.custo)} ações (`docs/02-requisitos.md`). O "
        "tempo da GPU é o do processo inteiro, da chamada à resposta — escrever a instância, subir "
        "o processo, criar o contexto, buscar e conferir o plano no Python. O do Python é só o da "
        f"busca, dentro do próprio processo, mediana de {len(python)} execuções: a comparação "
        "desfavorece a GPU.",
        "",
        "| Requisito | Meta | Medido | |",
        "|---|---|---|---|",
        f"| RNF01, de ponta a ponta | até 5 s | {_ms(processo)} ({_ms(min(gpu.processo))} a "
        f"{_ms(max(gpu.processo))}) | {atende(max(gpu.processo) <= 5)} |",
        f"| RNF02, speedup sobre o Python | no mínimo 5x | {_ms(med(python))} contra "
        f"{_ms(processo)}: **{_x(ganho)}** | {atende(ganho >= 5)} |",
        f"| RNF02, uplift | dentro de 2% do Python | {f'{diferenca:.1%}'.replace('.', ',')} de "
        f"diferença: o mesmo plano | {atende(diferenca <= 0.02)} |",
        "",
    ]
    return linhas


def montar_relatorio(
    resultados, threads, repeticoes, comando, capacidades, transferencias, avaliacoes, baseline
) -> str:
    no_conteiner = Path("/.dockerenv").exists()
    com_cuda = "cuda" in capacidades.modos
    processador = _cpuinfo("model name") or platform.processor() or platform.machine()
    nucleos = _cpuinfo("cpu cores")
    if nucleos:
        processador += f", {nucleos} núcleos físicos"
        smt = (
            f"Acima de {nucleos} threads, elas passam a dividir núcleos físicos (SMT), e o "
            "número cai por isso também."
        )
    else:
        smt = ""
    linhas = [
        "# Medição do núcleo em C++: serial, OpenMP e GPU — H53b, H54a, H54b, H54c",
        "",
        "> Gerado por `scripts/medir_nucleo.py`. **Não edite à mão**: número escrito à mão "
        "não é evidência. Para atualizar, rode o comando abaixo de novo.",
        "",
    ]
    if not no_conteiner:
        linhas += [
            "> **Medido fora do contêiner. Estes números não valem para o benchmark** (ADR-012): "
            "o sistema roda no contêiner, e lá o OpenMP ganha menos.",
            "",
        ]
    linhas += [
        "O ganho do OpenMP e o da GPU são lidos contra o **C++ serial**, com o mesmo plano: o C++ "
        "serial já é dezenas de vezes mais rápido que o Python (H53a), e o ganho contra o Python "
        "mediria o compilador junto. A exceção é o RNF02, que pede o ganho da GPU sobre o baseline "
        "em Python: ele tem a sua seção, no cenário de referência. As colunas:",
        "",
        "- **Tempo da busca**: medido pelo executável, do começo ao fim do genético, sem o "
        "processo subir e ler a entrada. Na GPU, inclui iniciar o driver e criar o contexto da "
        "placa, que a seção da H54c separa. Mediana, e a faixa do menor ao maior.",
        "- **Faixa do ganho**: o serial de cada rodada dividido pelo modo da mesma rodada.",
        f"- **Ganho por thread**: o ganho dividido pelas threads. {smt}".rstrip(),
        "- **Processo inteiro**: o que a API espera, da chamada à resposta — escrever a "
        "instância, subir o processo, conferir a viabilidade, buscar, e conferir o plano "
        "devolvido no Python (`nativo.py`).",
        "",
        f"**O plano foi o mesmo em todas as execuções**: em cada uma das {repeticoes + 1} "
        f"rodadas de cada tamanho, com cada número de threads e na GPU, os genes, a avaliação e "
        "as gerações foram conferidos contra os do serial. O script para sem escrever este "
        "arquivo se algum divergir.",
        "",
        "## Ambiente",
        "",
        "| Item | Valor |",
        "|---|---|",
        f"| Data | {datetime.now():%d/%m/%Y %H:%M} |",
        f"| Onde | {'contêiner, `python:3.11-slim` (ADR-012)' if no_conteiner else '**fora do contêiner**'} |",  # noqa: E501
        f"| Compilador | {capacidades.compilador}, `-O2 -fopenmp`"
        + ("; os kernels com o `nvcc`, `-O2 -arch=all-major`" if com_cuda else "")
        + " |",
        f"| Processador | {processador}, {os.cpu_count()} threads lógicas |",
        f"| OpenMP | threads medidas: {', '.join(map(str, threads))}; escalonamento dinâmico |",
        "| GPU | "
        + (
            f"{capacidades.gpu.nome}, capacidade {capacidades.gpu.capacidade}, "
            f"{_mil(capacidades.gpu.memoria_mib)} MiB"
            if capacidades.gpu
            else f"nenhuma: {capacidades.sem_gpu}"
        )
        + " |",
        f"| Genético | população {genetico.POPULACAO}, {genetico.GERACOES} gerações, "
        f"{genetico.PARTIDAS} partidas, {genetico.MUTACOES_POR_FILHO} mutação por filho |",
        f"| Rodadas | {repeticoes} por tamanho, depois de uma de aquecimento |",
        "| Instância | sintética, com o catálogo de `gerar_dados_sinteticos.py`, ganho pela RN10 "
        "e cotas pela RN11 |",
        "",
        "## Como reproduzir",
        "",
        "```bash",
        comando,
        "```",
        "",
    ]
    for inst, referencia, medidas in resultados:
        linhas += _secao(inst, referencia, medidas)
    linhas += _secao_busca_na_gpu(capacidades, resultados, threads)
    linhas += _secao_requisitos(capacidades, resultados, baseline)
    linhas += _secao_gpu(capacidades, transferencias, resultados, threads, repeticoes)
    linhas += _secao_kernel(capacidades, avaliacoes, repeticoes)
    return "\n".join(linhas)


def main() -> None:
    p = argparse.ArgumentParser(description="Mede o OpenMP e a GPU contra o C++ serial (H53b, H54)")
    p.add_argument("--parceiros", type=int, nargs="+", default=PARCEIROS)
    p.add_argument("--repeticoes", type=int, default=REPETICOES)
    p.add_argument("--threads", type=int, nargs="+", help="padrão: 1, 2, 4, 8... até o máximo")
    p.add_argument("--executavel", help="padrão: o de `nativo.localizar()`")
    p.add_argument("--relatorio", default=str(RAIZ / "docs" / "medicoes" / "nucleo.md"))
    args = p.parse_args()

    executavel = args.executavel or nativo.localizar()
    capacidades = nativo.capacidades(executavel)
    if "openmp" not in capacidades.modos:
        raise SystemExit("Este executável foi compilado sem OpenMP: não há o que medir.")
    threads = args.threads
    if not threads:
        threads = [t for t in (1, 2, 4, 8, 16, 32, 64) if t < capacidades.threads]
        threads.append(capacidades.threads)

    com_gpu = capacidades.gpu is not None and "cuda" in capacidades.modos
    resultados = []
    for parceiros in args.parceiros:
        print(f"{_mil(parceiros)} parceiros", flush=True)
        resultados.append(medir(parceiros, threads, args.repeticoes, executavel, com_gpu))

    # O baseline do RNF02: o Python, na instância do cenário de referência. Leva
    # dezenas de segundos por execução, e por isso são poucas.
    baseline = None
    referencia = next((r for r in resultados if r[0].parceiros == 2000), None)
    if com_gpu and referencia is not None:
        inst, plano_cpp, _ = referencia
        tempos = []
        for rodada in range(1, BASELINE + 1):
            print(f"baseline em Python, {rodada}/{BASELINE}", flush=True)
            plano_python = genetico.otimizar(inst)
            if plano_python.genes != plano_cpp.genes:
                raise SystemExit("O Python deu um plano diferente do C++. Relatório não escrito.")
            tempos.append(plano_python.segundos)
        baseline = (tempos, plano_python)

    transferencias, avaliacoes = [], []
    if capacidades.gpu is not None:
        for parceiros in args.parceiros:
            print(f"transferência e kernel, {_mil(parceiros)} parceiros", flush=True)
            inst = montar_instancia(parceiros)
            transferencias.append(
                (parceiros, nativo.transferir(inst, repeticoes=args.repeticoes, executavel=executavel))
            )
            populacao = populacao_de_medicao(inst, SEMENTE_DA_REDE + parceiros)
            r = nativo.avaliar_na_gpu(
                inst, populacao, repeticoes=args.repeticoes, executavel=executavel
            )
            iguais = sum(a == avaliar(inst, g) for a, g in zip(r.avaliacoes, populacao, strict=True))
            if iguais != len(populacao):
                raise SystemExit(
                    f"O kernel avaliou {len(populacao) - iguais} indivíduos diferente do Python "
                    f"({parceiros} parceiros). Relatório não escrito: é defeito."
                )
            avaliacoes.append((parceiros, r, iguais))

    opcoes = []
    if args.parceiros != PARCEIROS:
        opcoes += ["--parceiros", *map(str, args.parceiros)]
    if args.repeticoes != REPETICOES:
        opcoes += ["--repeticoes", str(args.repeticoes)]
    if args.threads:
        opcoes += ["--threads", *map(str, args.threads)]
    comando = (
        "docker build -t gih-nucleo nucleo\n"
        'docker run --rm --gpus all -v "$PWD:/repo" -w /repo gih-nucleo '
        "python scripts/medir_nucleo.py " + " ".join(opcoes)
    ).rstrip()
    destino = Path(args.relatorio)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        montar_relatorio(
            resultados,
            threads,
            args.repeticoes,
            comando,
            capacidades,
            transferencias,
            avaliacoes,
            baseline,
        ),
        encoding="utf-8",
    )
    print(f"\nrelatório: {destino}")


if __name__ == "__main__":
    main()
