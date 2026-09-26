"""Mede o núcleo em C++: o ganho do OpenMP sobre o serial (H53b), a transferência
para a GPU (H54a) e o kernel de avaliação da população (H54b).

**O ganho é lido contra o C++ serial**, e não contra o Python. O C++ serial já é
dezenas de vezes mais rápido que o mesmo algoritmo em Python (H53a), e comparar
o OpenMP com o Python mediria o compilador junto com o paralelismo (`CLAUDE.md`
§7, ADR-012). O baseline em Python do RNF02 está em `docs/medicoes/otimizador.md`.

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
- **em toda execução, o plano do OpenMP é conferido contra o do serial**: genes,
  avaliação e gerações. Se um divergir, o script para sem escrever o relatório.

**A instância é sintética e montada aqui, sem banco.**
- As ações, com custo e efeitos, são as do catálogo do gerador
  (`gerar_dados_sinteticos.ACOES`), lidas do próprio arquivo.
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
import ast
import math
import os
import platform
import random
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "nucleo"))

from gih_nucleo import (  # noqa: E402
    SEM_CATEGORIA,
    Instancia,
    avaliar,
    nativo,
    verificar_viabilidade,
)
from gih_nucleo import serial as genetico  # noqa: E402

TOP_N = 15  # quem está fora do Top N no ranking é cauda longa (RN11, RN02)
CATEGORIAS = 5
SEMENTE_DA_REDE = 2026
PARCEIROS = [500, 2000, 10000]  # o cenário de referência e a carga do RNF04 em volta
REPETICOES = 15


def _acoes_do_catalogo() -> list[tuple[int, float, float]]:
    """(custo em centavos, crescimento, retenção) de cada ação do gerador.

    Lido da árvore sintática: importar o gerador exigiria o banco.
    """
    arvore = ast.parse((RAIZ / "scripts" / "gerar_dados_sinteticos.py").read_text(encoding="utf-8"))
    for no in arvore.body:
        if isinstance(no, ast.Assign) and any(
            isinstance(alvo, ast.Name) and alvo.id == "ACOES" for alvo in no.targets
        ):
            return [
                (int(Decimal(custo) * 100), float(crescimento), float(retencao))
                for _nome, custo, crescimento, retencao in ast.literal_eval(no.value)
            ]
    raise SystemExit("O catálogo ACOES não foi encontrado em gerar_dados_sinteticos.py.")


def montar_instancia(parceiros: int) -> Instancia:
    """Uma campanha de `parceiros` elegíveis, com as restrições em proporção a eles.

    O máximo de ações é 1 para cada 40 parceiros (50 no cenário de referência), e
    o orçamento paga R$ 200 por ação, abaixo do custo médio do catálogo: as duas
    restrições apertam. Duas categorias pedem ao menos 10% das ações, nenhuma
    passa de 40%, e a cauda longa fica com ao menos 30% — frações do máximo de
    ações, arredondadas como a API arredonda (RN11).
    """
    rng = random.Random(SEMENTE_DA_REDE + parceiros)
    acoes = _acoes_do_catalogo()
    previsto, ganho, categoria = [], [], []
    for _ in range(parceiros):
        faturamento = rng.lognormvariate(12.1, 1.0)  # centavos por período
        risco = rng.random() * 0.6
        previsto.append(faturamento)
        # RN10: u = F̂·c + F̂·p·r
        ganho.append(tuple(int(faturamento * c + faturamento * risco * r) for _, c, r in acoes))
        # 1 em 10 ainda pendente de classificação: recebe ação, não conta em cota.
        categoria.append(SEM_CATEGORIA if rng.random() < 0.1 else rng.randrange(CATEGORIAS))
    ordem = sorted(range(parceiros), key=lambda i: -previsto[i])
    no_top = set(ordem[:TOP_N])

    k = parceiros // 40
    return Instancia(
        ganho=tuple(ganho),
        custo=tuple(custo for custo, _, _ in acoes),
        orcamento=k * 20_000,
        maximo_acoes=k,
        categoria=tuple(categoria),
        cauda=tuple(i not in no_top for i in range(parceiros)),
        minimo_categoria=(math.ceil(k * 0.1), math.ceil(k * 0.1), 0, 0, 0),
        maximo_categoria=(math.floor(k * 0.4),) * CATEGORIAS,
        minimo_cauda=math.ceil(k * 0.3),
    )


@dataclass
class Medida:
    busca: list[float] = field(default_factory=list)  # segundos, do executável
    processo: list[float] = field(default_factory=list)  # segundos, de fora


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


def medir(parceiros: int, threads: list[int], repeticoes: int, executavel: str):
    inst = montar_instancia(parceiros)
    if verificar_viabilidade(inst) is not None:
        raise SystemExit(f"A campanha de {parceiros} parceiros saiu inviável; ajuste o script.")
    referencia, _ = _rodar(inst, executavel, "serial", None)
    configuracoes = [("serial", None)] + [("openmp", t) for t in threads]
    medidas = {c: Medida() for c in configuracoes}

    for rodada in range(repeticoes + 1):
        for modo, t in configuracoes:
            r, processo = _rodar(inst, executavel, modo, t, referencia)
            if rodada == 0:
                continue  # aquecimento
            medidas[(modo, t)].busca.append(r.segundos)
            medidas[(modo, t)].processo.append(processo)
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
        "lotes de lançamentos seguidos**, como o laço da H54c vai lançar uma geração depois da "
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
        "cruza e muta na placa, e paga o lançamento de um kernel por geração. O ganho da GPU "
        "sobre o OpenMP só se mede com o laço inteiro, e esta tabela não o antecipa.",
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
    # A busca de referência: uma thread por núcleo físico, se foi medida (adendo
    # da ADR-011); senão, a de mais threads.
    fisicos = nativo.nucleos_fisicos()
    t_ref = fisicos if fisicos in threads else max(threads)
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
        "- **O laço na GPU (H54c) paga, por busca, um envio e a volta de um indivíduo**, porque "
        f"a população fica residente entre gerações (ADR-006). Com {_mil(n)} parceiros, "
        f"{_curto(por_busca)}: {fracao}% da busca inteira no OpenMP.",
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
        linhas.append(
            f"| OpenMP | {t} | {_ms(med(m.busca))} | {_ms(min(m.busca))} a {_ms(max(m.busca))} "
            f"| **{_x(ganho)}** | {_x(min(pares))} a {_x(max(pares))} "
            f"| {ganho / t:.0%} | {_ms(med(m.processo))} |"
        )
    linhas += [""]
    return linhas


def montar_relatorio(
    resultados, threads, repeticoes, comando, capacidades, transferencias, avaliacoes
) -> str:
    no_conteiner = Path("/.dockerenv").exists()
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
        "# Medição do núcleo em C++: serial, OpenMP e GPU — H53b, H54a, H54b",
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
        "O ganho do OpenMP é lido contra o **C++ serial**, com o mesmo plano: o C++ serial já é "
        "dezenas de vezes mais rápido que o Python (H53a), e o ganho contra o Python mediria o "
        "compilador junto. O baseline do RNF02, em Python, está em "
        "[`otimizador.md`](otimizador.md). As colunas:",
        "",
        "- **Tempo da busca**: medido pelo executável, do começo ao fim do genético, sem o "
        "processo subir e ler a entrada. Mediana, e a faixa do menor ao maior.",
        "- **Faixa do ganho**: o serial de cada rodada dividido pelo OpenMP da mesma rodada.",
        f"- **Ganho por thread**: o ganho dividido pelas threads. {smt}".rstrip(),
        "- **Processo inteiro**: o que a API espera, da chamada à resposta — escrever a "
        "instância, subir o processo, conferir a viabilidade, buscar, e conferir o plano "
        "devolvido no Python (`nativo.py`).",
        "",
        f"**O plano foi o mesmo em todas as execuções**: em cada uma das {repeticoes + 1} "
        f"rodadas de cada tamanho, com cada número de threads, os genes, a avaliação e as "
        "gerações do OpenMP foram conferidos contra os do serial. O script para sem escrever "
        "este arquivo se algum divergir.",
        "",
        "## Ambiente",
        "",
        "| Item | Valor |",
        "|---|---|",
        f"| Data | {datetime.now():%d/%m/%Y %H:%M} |",
        f"| Onde | {'contêiner, `python:3.11-slim` (ADR-012)' if no_conteiner else '**fora do contêiner**'} |",  # noqa: E501
        f"| Compilador | {capacidades.compilador}, `-O2 -fopenmp` |",
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
    linhas += _secao_gpu(capacidades, transferencias, resultados, threads, repeticoes)
    linhas += _secao_kernel(capacidades, avaliacoes, repeticoes)
    return "\n".join(linhas)


def main() -> None:
    p = argparse.ArgumentParser(description="Mede o ganho do OpenMP sobre o C++ serial (H53b).")
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

    resultados = []
    for parceiros in args.parceiros:
        print(f"{_mil(parceiros)} parceiros", flush=True)
        resultados.append(medir(parceiros, threads, args.repeticoes, executavel))

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
            resultados, threads, args.repeticoes, comando, capacidades, transferencias, avaliacoes
        ),
        encoding="utf-8",
    )
    print(f"\nrelatório: {destino}")


if __name__ == "__main__":
    main()
