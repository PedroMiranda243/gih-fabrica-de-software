"""Mede o núcleo em C++: o ganho do OpenMP sobre o serial (H53b).

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

Uso, da raiz do repositório:

    docker build -t gih-nucleo nucleo
    docker run --rm -v "$PWD:/repo" -w /repo gih-nucleo python scripts/medir_nucleo.py
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

from gih_nucleo import SEM_CATEGORIA, Instancia, nativo, verificar_viabilidade  # noqa: E402
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


def montar_relatorio(resultados, threads, repeticoes, comando, capacidades) -> str:
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
        "# Medição do núcleo em C++: serial e OpenMP — H53b",
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

    opcoes = []
    if args.parceiros != PARCEIROS:
        opcoes += ["--parceiros", *map(str, args.parceiros)]
    if args.repeticoes != REPETICOES:
        opcoes += ["--repeticoes", str(args.repeticoes)]
    if args.threads:
        opcoes += ["--threads", *map(str, args.threads)]
    comando = (
        "docker build -t gih-nucleo nucleo\n"
        'docker run --rm -v "$PWD:/repo" -w /repo gih-nucleo python scripts/medir_nucleo.py '
        + " ".join(opcoes)
    ).rstrip()
    destino = Path(args.relatorio)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        montar_relatorio(resultados, threads, args.repeticoes, comando, capacidades),
        encoding="utf-8",
    )
    print(f"\nrelatório: {destino}")


if __name__ == "__main__":
    main()
