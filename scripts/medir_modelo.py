"""Mede o modelo preditivo contra as referências — histórias H42, H43 e H46.

A H46 pede a tabela comparativa com pelo menos dois baselines, publicada na
documentação; a H42, o MAPE abaixo do baseline; a H43, a métrica do risco. Este
script produz os três números, e produz de um jeito que outra pessoa consegue
repetir.

**O caminho é o de verdade**: o gerador sintético grava no banco, a segmentação
classifica, e a série de cada parceiro sai de `servico_previsao.historico` —
a mesma leitura do treino pela tela, com o rótulo de risco da RN01. Só o treino
é chamado direto, sem gravar versão: medir não pode trocar o modelo em uso.

**Banco separado**, como na medição do painel: gerar a massa apaga o banco, e o
de trabalho tem a base de demonstração e os usuários da equipe.

**Várias redes e várias sementes, e o relatório traz a faixa.** Um número só,
de uma rede e uma semente, não diz se a vantagem se sustenta — e é exatamente
o que se quer saber. A armadilha está no `CLAUDE.md` §7: medição de execução
única já deu 7,5x numa corrida e 13,9x na seguinte.

Uso:

    api/.venv/Scripts/python scripts/medir_modelo.py
    api/.venv/Scripts/python scripts/medir_modelo.py --parceiros 500 --sementes 3
"""
from __future__ import annotations

import argparse
import os
import platform
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "api"))
sys.path.insert(0, str(RAIZ / "scripts"))

# A preparação do banco é a mesma da medição do painel — criar, migrar, gerar,
# segmentar e atualizar estatísticas —, e duplicá-la faria as duas divergirem.
from medir_painel import _mil, _url_base, _url_medicao, preparar  # noqa: E402

REDES_PADRAO = (42, 7, 2026)  # sementes do gerador: três redes diferentes
PERIODOS = 12


@dataclass(frozen=True)
class Execucao:
    parceiros: int
    rede: int
    semente: int
    mape_modelo: float
    mape_ultimo: float
    mape_media_movel: float
    brier_modelo: float
    brier_referencia: float
    calibracao_modelo: float
    calibracao_referencia: float
    supera: bool
    epocas: int
    segundos: float
    amostras_teste: int


def _porcento(x: float) -> str:
    return f"{x * 100:.1f}%".replace(".", ",")


def _decimal(x: float, casas: int = 3) -> str:
    return f"{x:.{casas}f}".replace(".", ",")


def _pontos(x: float) -> str:
    """Em ponto percentual, com a concordância do português: plural a partir de 2."""
    return f"{_decimal(x, 1)} {'ponto percentual' if abs(x) < 2 else 'pontos percentuais'}"


def _faixa(valores: list[float], formato) -> str:
    return f"{formato(min(valores))} a {formato(max(valores))}"


def medir_rede(parceiros: int, rede: int, sementes: list[int], url: str) -> list[Execucao]:
    preparar(url, parceiros, PERIODOS, rede)

    # Importados aqui: `app` só pode ser importado depois de `DATABASE_URL`
    # apontar para o banco de medição.
    import gih_modelo

    from app.db import Sessao
    from app.servico_previsao import historico, supera_referencias

    s = Sessao()
    try:
        series = historico(s).series
    finally:
        s.close()

    execucoes = []
    for semente in sementes:
        r = gih_modelo.treinar(series, semente=semente)
        m = r.metricas
        execucoes.append(
            Execucao(
                parceiros=parceiros,
                rede=rede,
                semente=semente,
                mape_modelo=m.mape_modelo,
                mape_ultimo=m.mape_ultimo,
                mape_media_movel=m.mape_media_movel,
                brier_modelo=m.brier_modelo,
                brier_referencia=m.brier_referencia,
                calibracao_modelo=m.calibracao_modelo,
                calibracao_referencia=m.calibracao_referencia,
                supera=supera_referencias(m),
                epocas=r.epocas,
                segundos=r.segundos,
                amostras_teste=r.volume.teste,
            )
        )
        print(
            f"  rede {rede}, semente {semente}: MAPE {_porcento(m.mape_modelo)} "
            f"(média móvel {_porcento(m.mape_media_movel)}), Brier {_decimal(m.brier_modelo)} "
            f"(referência {_decimal(m.brier_referencia)}), {r.segundos:.1f} s"
        )
    return execucoes


def _secao(parceiros: int, execucoes: list[Execucao]) -> list[str]:
    def col(nome: str) -> list[float]:
        return [getattr(e, nome) for e in execucoes]

    med = statistics.median
    vantagem = [min(e.mape_ultimo, e.mape_media_movel) - e.mape_modelo for e in execucoes]
    vitorias = sum(e.supera for e in execucoes)
    linhas = [
        f"## {_mil(parceiros)} parceiros",
        "",
        f"{len(execucoes)} treinos: {len({e.rede for e in execucoes})} redes geradas × "
        f"{len({e.semente for e in execucoes})} sementes de treino. Mediana, e entre parênteses "
        "a faixa do menor ao maior.",
        "",
        "| Métrica | Rede | Repetir o último | Média móvel dos últimos 4 |",
        "|---|--:|--:|--:|",
        f"| MAPE do faturamento | **{_porcento(med(col('mape_modelo')))}** "
        f"({_faixa(col('mape_modelo'), _porcento)}) "
        f"| {_porcento(med(col('mape_ultimo')))} ({_faixa(col('mape_ultimo'), _porcento)}) "
        f"| {_porcento(med(col('mape_media_movel')))} "
        f"({_faixa(col('mape_media_movel'), _porcento)}) |",
        "",
        "| Métrica | Rede | Taxa observada |",
        "|---|--:|--:|",
        f"| Brier do risco | **{_decimal(med(col('brier_modelo')))}** "
        f"({_faixa(col('brier_modelo'), _decimal)}) "
        f"| {_decimal(med(col('brier_referencia')))} "
        f"({_faixa(col('brier_referencia'), _decimal)}) |",
        f"| Erro de calibração | {_decimal(med(col('calibracao_modelo')))} "
        f"({_faixa(col('calibracao_modelo'), _decimal)}) "
        f"| {_decimal(med(col('calibracao_referencia')))} "
        f"({_faixa(col('calibracao_referencia'), _decimal)}) |",
        "",
        f"- **Supera as referências nas duas saídas (UC07-A1): {vitorias} de {len(execucoes)} "
        "treinos.**",
        f"- Vantagem no MAPE sobre a melhor referência de cada treino: mediana de "
        f"{_pontos(med(vantagem) * 100)} "
        f"({_decimal(min(vantagem) * 100, 1)} a {_decimal(max(vantagem) * 100, 1)}).",
        f"- O risco da rede **separa melhor** quem cai de quem não cai (Brier menor) e é **menos "
        f"calibrado** que a referência: em média, {_pontos(med(col('calibracao_modelo')) * 100)} "
        f"entre o previsto e o observado, contra "
        f"{_decimal(med(col('calibracao_referencia')) * 100, 1)}. A referência é calibrada por "
        "construção — é a própria taxa observada, em dois grupos —, e por isso não distingue ninguém "
        "dentro de cada grupo.",
        f"- Tempo de treino: mediana de {_decimal(med(col('segundos')), 1)} s "
        f"({_faixa(col('segundos'), lambda x: _decimal(x, 1))} s), uma thread.",
        f"- Amostras de teste por treino: {_mil(int(med(col('amostras_teste'))))} "
        "(o último período da base).",
        "",
        "<details><summary>Cada treino</summary>",
        "",
        "| Rede | Semente | MAPE rede | Último | Média móvel | Brier rede | Referência "
        "| Épocas | Tempo | Supera |",
        "|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--:|",
    ]
    for e in execucoes:
        linhas.append(
            f"| {e.rede} | {e.semente} | {_porcento(e.mape_modelo)} | {_porcento(e.mape_ultimo)} "
            f"| {_porcento(e.mape_media_movel)} | {_decimal(e.brier_modelo)} "
            f"| {_decimal(e.brier_referencia)} | {e.epocas} | {_decimal(e.segundos, 1)} s "
            f"| {'sim' if e.supera else 'não'} |"
        )
    linhas += ["", "</details>", ""]
    return linhas


def montar_relatorio(resultados: dict[int, list[Execucao]], redes, sementes, comando) -> str:
    import numpy
    import torch

    linhas = [
        "# Medição do modelo preditivo — H42, H43, H46",
        "",
        "> Gerado por `scripts/medir_modelo.py`. **Não edite à mão**: número escrito à mão não "
        "é evidência. Para atualizar, rode o comando abaixo de novo.",
        "",
        "A rede é comparada, **no mesmo conjunto de teste**, com as referências da `docs/07` "
        "§4.4: para o faturamento, repetir o último período e a média móvel dos últimos 4; para "
        "o risco (RN09), a taxa observada no treino, separada por \"caiu no último período\". "
        "O teste é o último período da base; o penúltimo valida; os anteriores treinam.",
        "",
        "## Ambiente",
        "",
        "| Item | Valor |",
        "|---|---|",
        f"| Data | {datetime.now():%d/%m/%Y %H:%M} |",
        f"| Massa | `scripts/gerar_dados_sinteticos.py`, {PERIODOS} semanas, redes geradas com "
        f"as sementes {', '.join(map(str, redes))} |",
        f"| Sementes de treino | {', '.join(map(str, sementes))} |",
        "| Caminho | gerador → banco `gih_medicao` → segmentação → "
        "`servico_previsao.historico` → treino |",
        f"| Python | {platform.python_version()} |",
        f"| PyTorch | {torch.__version__} (CPU, uma thread) |",
        f"| NumPy | {numpy.__version__} |",
        f"| Processador | {platform.processor() or platform.machine()} |",
        "",
        "## Como reproduzir",
        "",
        "```bash",
        comando,
        "```",
        "",
    ]
    for parceiros, execucoes in resultados.items():
        linhas += _secao(parceiros, execucoes)
    return "\n".join(linhas)


def main() -> None:
    p = argparse.ArgumentParser(description="Mede o modelo contra as referências (H46).")
    p.add_argument("--parceiros", type=int, nargs="+", default=[500, 5000])
    p.add_argument("--redes", type=int, nargs="+", default=list(REDES_PADRAO))
    p.add_argument("--sementes", type=int, default=5, help="sementes de treino (padrão: 5)")
    p.add_argument("--banco", default="gih_medicao")
    p.add_argument("--relatorio", default=str(RAIZ / "docs" / "medicoes" / "modelo.md"))
    args = p.parse_args()

    url = _url_medicao(args.banco)
    if urlsplit(url).path.lstrip("/") == urlsplit(_url_base()).path.lstrip("/"):
        raise SystemExit("O banco de medição não pode ser o banco de trabalho.")
    os.environ["DATABASE_URL"] = url

    sementes = list(range(1, args.sementes + 1))
    resultados: dict[int, list[Execucao]] = {}
    for parceiros in args.parceiros:
        resultados[parceiros] = []
        for rede in args.redes:
            print(f"{_mil(parceiros)} parceiros, rede {rede}")
            resultados[parceiros] += medir_rede(parceiros, rede, sementes, url)

    comando = (
        "api/.venv/Scripts/python scripts/medir_modelo.py "
        f"--parceiros {' '.join(map(str, args.parceiros))} "
        f"--redes {' '.join(map(str, args.redes))} --sementes {args.sementes}"
    )
    destino = Path(args.relatorio)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        montar_relatorio(resultados, args.redes, sementes, comando), encoding="utf-8"
    )
    print(f"\nrelatório: {destino.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
