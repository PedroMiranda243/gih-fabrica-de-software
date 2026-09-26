"""O núcleo em C++ chamado a partir do Python (H53a, H53b, ADR-012).

O executável `gih-nucleo` faz o mesmo que `serial.otimizar`, sorteio a sorteio,
e devolve o mesmo `Resultado`, em qualquer um dos seus modos: `serial` e
`openmp` agora, `cuda` depois. É assim que a API vai chegar às versões
compiladas sem conhecer nenhuma delas: escreve a instância, lê o plano.

**O formato é texto, em inteiros**, e é este módulo que o escreve e o lê:

    GIH-NUCLEO 1
    <parceiros> <ações> <categorias>
    <orçamento> <máximo de ações> <cota da cauda>
    <custo de cada ação>
    <mínimo de cada categoria>
    <máximo de cada categoria>
    <categoria> <cauda> <ganho de cada ação>      ← uma linha por parceiro

A resposta é `viavel` com a avaliação, a busca, o modo e os genes, ou
`inviavel` com a restrição, o exigido e o disponível — os mesmos de
`viabilidade.Inviabilidade`.

**O Python confere o que o C++ diz.** A avaliação do plano devolvido é refeita
aqui, com `problema.avaliar`; se ela divergir da que o executável informou, é
defeito do porte, e a chamada falha em vez de entregar o plano.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from gih_nucleo.problema import Instancia, avaliar
from gih_nucleo.serial import GERACOES, MUTACOES_POR_FILHO, PARTIDAS, POPULACAO, Resultado
from gih_nucleo.viabilidade import Inviabilidade, Inviavel

FORMATO = "GIH-NUCLEO 1"
MODOS = ("serial", "openmp")

# Onde o `construir.bat` e o comando de Linux deixam o executável.
_COMPILADO = Path(__file__).resolve().parent.parent / "bin"


class NucleoIndisponivel(RuntimeError):
    """O executável não foi encontrado: não está compilado, ou não está no caminho."""


class NucleoFalhou(RuntimeError):
    """O executável respondeu com erro, ou com algo que não confere com o Python."""


@dataclass(frozen=True)
class Capacidades:
    """O que o executável sabe fazer nesta máquina, e com que compilador foi feito."""

    modos: tuple[str, ...]
    threads: int  # as do OpenMP; 0 quando foi compilado sem ele
    compilador: str


def localizar() -> str | None:
    """O executável: `GIH_NUCLEO`, se definida; senão o do `PATH`; senão o de `nucleo/bin`."""
    if os.environ.get("GIH_NUCLEO"):
        return os.environ["GIH_NUCLEO"]
    no_caminho = shutil.which("gih-nucleo")
    if no_caminho:
        return no_caminho
    for nome in ("gih-nucleo.exe", "gih-nucleo"):
        if (_COMPILADO / nome).is_file():
            return str(_COMPILADO / nome)
    return None


def _executavel(executavel: str | None) -> str:
    executavel = executavel or localizar()
    if executavel is None:
        raise NucleoIndisponivel(
            "O núcleo em C++ não está compilado: rode nucleo/construir.bat, ou o g++ do README."
        )
    return executavel


def capacidades(executavel: str | None = None) -> Capacidades:
    """Pergunta ao executável (`gih-nucleo versao`) quais modos ele tem."""
    r = subprocess.run(
        [_executavel(executavel), "versao"], capture_output=True, text=True, encoding="utf-8"
    )
    linhas = r.stdout.splitlines()
    if r.returncode != 0 or not linhas or linhas[0].strip() != FORMATO:
        resposta = r.stderr.strip() or r.stdout[:80]
        raise NucleoFalhou(f"O núcleo não respondeu à versão: {resposta!r}")
    campos = {linha.split()[0]: linha.split()[1:] for linha in linhas[1:] if linha.strip()}
    return Capacidades(
        tuple(campos["modos"]), int(campos["threads"][0]), " ".join(campos["compilador"])
    )


def serializar(inst: Instancia) -> str:
    linhas = [
        FORMATO,
        f"{inst.parceiros} {inst.acoes} {inst.categorias}",
        f"{inst.orcamento} {inst.maximo_acoes} {inst.minimo_cauda}",
        " ".join(map(str, inst.custo)),
        " ".join(map(str, inst.minimo_categoria)),
        " ".join(map(str, inst.maximo_categoria)),
    ]
    linhas += [
        f"{inst.categoria[i]} {int(inst.cauda[i])} " + " ".join(map(str, inst.ganho[i]))
        for i in range(inst.parceiros)
    ]
    return "\n".join(linhas) + "\n"


def otimizar(
    inst: Instancia,
    *,
    semente: int = 42,
    partidas: int = PARTIDAS,
    populacao: int = POPULACAO,
    geracoes: int = GERACOES,
    mutacoes_por_filho: int = MUTACOES_POR_FILHO,
    limite_s: float | None = None,
    modo: str = "serial",
    threads: int | None = None,
    executavel: str | None = None,
) -> Resultado:
    """O mesmo contrato de `serial.otimizar`, rodando no executável em C++.

    `modo` escolhe a versão; sem limite de tempo, todas dão o mesmo plano.
    `threads` só vale no modo `openmp`, e sem ele vale o padrão do OpenMP.

    Levanta `Inviavel` quando as cotas não cabem, `ValueError` para parâmetro
    impossível ou modo que o executável não tem, `NucleoIndisponivel` sem
    executável e `NucleoFalhou` quando ele erra ou diverge do Python.
    """
    executavel = _executavel(executavel)
    comando = [
        executavel, "otimizar",
        "--modo", modo,
        "--semente", str(semente),
        "--partidas", str(partidas),
        "--populacao", str(populacao),
        "--geracoes", str(geracoes),
        "--mutacoes", str(mutacoes_por_filho),
    ]
    if limite_s is not None:
        comando += ["--limite-ms", str(int(limite_s * 1000))]
    if threads is not None:
        comando += ["--threads", str(threads)]

    r = subprocess.run(
        comando, input=serializar(inst), capture_output=True, text=True, encoding="utf-8"
    )
    if r.returncode == 2:
        raise ValueError(r.stderr.strip())
    if r.returncode != 0:
        raise NucleoFalhou(f"O núcleo saiu com {r.returncode}: {r.stderr.strip()}")
    return _ler(inst, r.stdout, modo)


def _ler(inst: Instancia, saida: str, modo: str) -> Resultado:
    linhas = saida.splitlines()
    if not linhas or linhas[0].strip() != FORMATO:
        raise NucleoFalhou(f"Resposta fora do formato: {saida[:80]!r}")
    campos = {linha.split()[0]: linha.split()[1:] for linha in linhas[1:] if linha.strip()}

    if "inviavel" in campos:
        restricao, exigido, disponivel, categoria = campos["inviavel"]
        raise Inviavel(
            Inviabilidade(
                restricao,
                int(exigido),
                int(disponivel),
                None if int(categoria) < 0 else int(categoria),
            )
        )

    genes = tuple(int(g) for g in campos.get("genes", []))
    ganho, custo, acoes, _cauda, violacao = (int(x) for x in campos["avaliacao"])
    iniciadas, rodadas, parcial, microssegundos = (int(x) for x in campos["busca"])
    # Um executável que calculasse num modo e informasse outro estragaria a
    # medição sem ninguém ver.
    modo_usado, threads = campos["execucao"]
    if modo_usado != modo:
        raise NucleoFalhou(f"Pedido o modo {modo}, o núcleo respondeu {modo_usado}.")

    avaliacao = avaliar(inst, genes)
    if len(genes) != inst.parceiros or (ganho, custo, acoes, violacao) != (
        avaliacao.ganho,
        avaliacao.custo,
        avaliacao.acoes,
        avaliacao.violacao,
    ):
        raise NucleoFalhou("A avaliação do núcleo em C++ diverge da do Python.")
    return Resultado(
        genes, avaliacao, iniciadas, rodadas, bool(parcial), microssegundos / 1e6, int(threads)
    )


def nucleos_fisicos() -> int | None:
    """Os núcleos físicos que este processo pode usar; `None` onde não há `/proc/cpuinfo`.

    É quantas threads a API pede ao modo OpenMP (adendo da ADR-011). No
    contêiner, uma thread por núcleo físico ganhou 6,0x do C++ serial numa faixa
    estreita; todas as threads lógicas ganharam menos e oscilaram de 1,0x a
    6,9x, disputando a CPU com o Windows (`docs/medicoes/nucleo.md`).
    """
    try:
        texto = Path("/proc/cpuinfo").read_text(encoding="utf-8")
    except OSError:
        return None
    permitidos = os.sched_getaffinity(0) if hasattr(os, "sched_getaffinity") else None
    return contar_nucleos(texto, permitidos)


def contar_nucleos(cpuinfo: str, permitidos: set[int] | None = None) -> int | None:
    """Os pares (processador físico, núcleo) distintos entre os processadores permitidos.

    Com SMT, duas threads lógicas dividem um núcleo e repetem o par. Sem o
    campo `core id` — algumas máquinas virtuais não o expõem —, não há como
    saber, e a resposta é `None`: vale o padrão do OpenMP.
    """
    nucleos = set()
    for bloco in cpuinfo.strip().split("\n\n"):
        campos = {}
        for linha in bloco.splitlines():
            if ":" in linha:
                chave, valor = linha.split(":", 1)
                campos[chave.strip()] = valor.strip()
        if "processor" not in campos or "core id" not in campos:
            continue
        if permitidos is not None and int(campos["processor"]) not in permitidos:
            continue
        nucleos.add((campos.get("physical id", "0"), campos["core id"]))
    return len(nucleos) or None
