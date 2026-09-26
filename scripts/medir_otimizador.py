"""Mede o otimizador serial — o tempo da H49 e a qualidade que justifica a H48.

Dois números saem daqui, e os dois precisam poder ser repetidos por outra pessoa:

- **Tempo do baseline serial**, com 500 e com 2.000 parceiros (o cenário de
  referência da `docs/07` §4.3). É o denominador do *speedup* das Sprints 10 e
  11 (RNF02).
- **Qualidade**: quanto o genético ganha sobre o melhor dos dois planos gulosos,
  em campanhas grandes; e se ele chega ao ótimo da enumeração, em recortes
  pequenos da mesma base.

**O caminho é o de verdade**: o gerador grava no banco, a segmentação
classifica, o modelo treina e grava as previsões, e a instância sai de
`servico_otimizacao.montar` — a mesma da tela. Só a busca é chamada direto, sem
gravar execução.

**Banco separado**, como nas outras medições: gerar a massa apaga o banco.

**Várias redes e várias sementes, e o relatório traz a faixa** — a armadilha do
`CLAUDE.md` §7 é a mesma de qualquer medição.

Uso:

    api/.venv/Scripts/python scripts/medir_otimizador.py
    api/.venv/Scripts/python scripts/medir_otimizador.py --parceiros 500 --sementes 3
"""
from __future__ import annotations

import argparse
import os
import platform
import random
import statistics
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "api"))
sys.path.insert(0, str(RAIZ / "scripts"))

from medir_painel import _mil, _url_base, _url_medicao, preparar  # noqa: E402

REDES_PADRAO = (42, 7, 2026)
PERIODOS = 12
RECORTES = 25  # instâncias pequenas por rede, para a enumeração
PARCEIROS_NO_RECORTE = 8

# As campanhas medidas. Cada uma aperta uma restrição diferente, porque cada
# guloso erra num caso: o de razão ganho/custo quando o máximo de ações aperta,
# o de ganho quando o orçamento aperta.
CENARIOS = (
    ("orçamento aperta", {"orcamento": "3000.00", "maximo_acoes": 60}),
    ("máximo de ações aperta", {"orcamento": "50000.00", "maximo_acoes": 30}),
    (
        "com cotas",
        {"orcamento": "12000.00", "maximo_acoes": 45, "cota_cauda_longa": "0.3"},
    ),
)


@dataclass(frozen=True)
class Busca:
    cenario: str
    rede: int
    semente: int
    elegiveis: int
    acoes: int
    ganho: int  # centavos
    guloso: int  # centavos, o melhor dos dois
    teto: int  # centavos, o limite superior lagrangiano
    segundos: float

    @property
    def melhora(self) -> float:
        return (self.ganho - self.guloso) / self.guloso if self.guloso else 0.0

    @property
    def distancia(self) -> float:
        """Quanto falta, no máximo, para o ótimo: ele fica entre o ganho e o teto."""
        return (self.teto - self.ganho) / self.teto if self.teto else 0.0


def _reais(centavos: float) -> str:
    texto = f"{centavos / 100:,.0f}"
    return "R$ " + texto.replace(",", ".")


def _porcento(x: float) -> str:
    return f"{x * 100:.1f}%".replace(".", ",")


def _decimal(x: float, casas: int = 1) -> str:
    return f"{x:.{casas}f}".replace(".", ",")


def _faixa(valores: list[float], formato) -> str:
    return f"{formato(min(valores))} a {formato(max(valores))}"


def limite_superior(inst) -> int:
    """Um teto para o ganho de qualquer plano, em centavos, por relaxação lagrangiana.

    Relaxa o orçamento e o máximo de ações com multiplicadores λ e μ, e ignora as
    cotas. Para **quaisquer** λ, μ ≥ 0,

        λ·B + μ·K + Σᵢ max(0, maxₐ(uᵢₐ − λ·cₐ − μ))

    é maior ou igual ao ganho de todo plano viável (dualidade fraca). A busca
    abaixo só procura o menor teto; se parar longe do mínimo, o número continua
    sendo um teto, apenas mais folgado. É o que permite dizer quão perto do
    ótimo fica um plano grande demais para enumerar. NumPy aqui é da medição, e
    não do baseline, que continua em Python puro.
    """
    import numpy as np

    u = np.array(inst.ganho, dtype=np.float64).reshape(inst.parceiros, inst.acoes)
    c = np.array(inst.custo, dtype=np.float64)
    b, k = float(inst.orcamento), float(inst.maximo_acoes)

    def teto(lam: float, mu: float) -> float:
        folga = np.maximum(0.0, (u - lam * c - mu).max(axis=1)) if u.size else np.zeros(0)
        return lam * b + mu * k + folga.sum()

    def minimizar(f, alto: float) -> tuple[float, float]:
        # Seção áurea: a função é convexa em cada multiplicador.
        a, z = 0.0, alto
        razao = (5**0.5 - 1) / 2
        for _ in range(80):
            x1, x2 = z - razao * (z - a), a + razao * (z - a)
            if f(x1) <= f(x2):
                z = x2
            else:
                a = x1
        melhor = (a + z) / 2
        return melhor, f(melhor)

    mu_max = float(u.max()) if u.size else 0.0
    lam_max = mu_max / float(c.min())
    _mu, valor = minimizar(lambda mu: minimizar(lambda lam: teto(lam, mu), lam_max)[1], mu_max)
    # Arredonda para cima: o teto não pode ficar abaixo por causa do centavo.
    return int(-(-valor // 1))


def _treinar() -> None:
    """O treino pelo serviço, como o `resetar_banco.py`: grava versão e previsões."""
    from app import servico_previsao
    from app.db import Sessao

    s = Sessao()
    try:
        treino = servico_previsao.iniciar(s, usuario_id=None)
        s.commit()
        treino_id = treino.id
    finally:
        s.close()
    servico_previsao.executar(treino_id)


def _parametros(s, base: dict):
    """Os parâmetros do cenário; o de cotas ganha um mínimo na maior categoria."""
    from app.esquemas import ParametrosCampanha

    dados = {**base, "aplicacao_inicio": date(2026, 10, 5), "aplicacao_fim": date(2026, 10, 11)}
    if "cota_cauda_longa" in base:
        from sqlalchemy import func, select

        from app.modelos import OrigemCategoria, Parceiro

        maior = s.execute(
            select(Parceiro.categoria_id, func.count())
            .where(Parceiro.origem_categoria == OrigemCategoria.MANUAL)
            .group_by(Parceiro.categoria_id)
            .order_by(func.count().desc())
        ).first()
        if maior:
            dados["cotas_categoria"] = [{"categoria_id": maior[0], "minimo": "0.1"}]
    return ParametrosCampanha.model_validate(dados)


def _recorte(inst, indices: list[int]):
    """Uma instância pequena com os parceiros `indices` da grande, para a enumeração."""
    import gih_nucleo

    return gih_nucleo.Instancia(
        ganho=tuple(inst.ganho[i] for i in indices),
        custo=inst.custo,
        orcamento=60_000,  # R$ 600: poucas ações cabem, e o orçamento aperta
        maximo_acoes=4,
        categoria=tuple(gih_nucleo.SEM_CATEGORIA for _ in indices),
        cauda=tuple(inst.cauda[i] for i in indices),
        minimo_categoria=(),
        maximo_categoria=(),
        minimo_cauda=1,
    )


def medir_rede(
    parceiros: int, rede: int, sementes: list[int], url: str
) -> tuple[list[Busca], tuple[int, int]]:
    preparar(url, parceiros, PERIODOS, rede)
    print("  treinando o modelo")
    _treinar()

    import gih_nucleo
    from gih_nucleo.exaustivo import otimo
    from gih_nucleo.guloso import GANHO, RAZAO

    from app import servico_otimizacao, servico_previsao
    from app.db import Sessao
    from app.modelos import ExecucaoOtimizador, ModoExecucao

    buscas: list[Busca] = []
    s = Sessao()
    try:
        concluido = servico_previsao.ultimo_concluido(s)
        instancias = {}
        for nome, base in CENARIOS:
            execucao = ExecucaoOtimizador(
                modo=ModoExecucao.SERIAL,
                parametros=_parametros(s, base).model_dump(mode="json"),
                periodo_base_id=concluido.periodo_base_id,
                modelo_versao=concluido.versao_em_uso,
                semente=0,
            )
            instancias[nome] = servico_otimizacao.montar(s, execucao).instancia
    finally:
        s.close()

    for nome, inst in instancias.items():
        if gih_nucleo.verificar_viabilidade(inst) is not None:
            print(f"  {nome}: inviável nesta rede — fora da medição")
            continue
        guloso = max(
            gih_nucleo.avaliar(inst, gih_nucleo.guloso(inst, c)).ganho for c in (RAZAO, GANHO)
        )
        teto = limite_superior(inst)
        for semente in sementes:
            r = gih_nucleo.otimizar(inst, semente=semente)
            buscas.append(
                Busca(nome, rede, semente, inst.parceiros, r.avaliacao.acoes,
                      r.avaliacao.ganho, guloso, teto, r.segundos)
            )
            print(
                f"  {nome}, semente {semente}: {_reais(r.avaliacao.ganho)} contra "
                f"{_reais(guloso)} do guloso e teto de {_reais(teto)}, {r.segundos:.1f} s"
            )

    # Recortes pequenos da mesma base: o ótimo exato existe e é comparável.
    rng = random.Random(rede)
    grande = next(iter(instancias.values()))
    acertos = total = 0
    while total < RECORTES:
        recorte = _recorte(grande, rng.sample(range(grande.parceiros), PARCEIROS_NO_RECORTE))
        if gih_nucleo.verificar_viabilidade(recorte) is not None:
            continue
        total += 1
        acertos += gih_nucleo.otimizar(recorte).avaliacao.ganho == otimo(recorte)[0]
    print(f"  recortes: o genético achou o ótimo em {acertos} de {total}")
    return buscas, (acertos, total)


def _secao(parceiros: int, buscas: list[Busca], recortes: list[tuple[int, int]]) -> list[str]:
    med = statistics.median
    acertos = sum(a for a, _ in recortes)
    total = sum(t for _, t in recortes)
    linhas = [
        f"## {_mil(parceiros)} parceiros",
        "",
        f"{len({b.rede for b in buscas})} redes geradas × {len({b.semente for b in buscas})} "
        "sementes de busca, com os parâmetros padrão do genético. Mediana, e entre parênteses a "
        "faixa do menor ao maior.",
        "",
        "| Campanha | Elegíveis | Ações no plano | Ganho do genético | Sobre o melhor guloso "
        "| Abaixo do teto, no máximo | Tempo da busca |",
        "|---|--:|--:|--:|--:|--:|--:|",
    ]
    for nome, _base in CENARIOS:
        daqui = [b for b in buscas if b.cenario == nome]
        if not daqui:
            linhas.append(f"| {nome} | — | — | inviável nas redes medidas | — | — | — |")
            continue
        melhoras = [b.melhora for b in daqui]
        distancias = [b.distancia for b in daqui]
        tempos = [b.segundos for b in daqui]
        linhas.append(
            f"| {nome} | {_mil(int(med(b.elegiveis for b in daqui)))} "
            f"| {int(med(b.acoes for b in daqui))} "
            f"| {_reais(med(b.ganho for b in daqui))} "
            f"| **+{_porcento(med(melhoras))}** ({_faixa(melhoras, _porcento)}) "
            f"| {_porcento(med(distancias))} ({_faixa(distancias, _porcento)}) "
            f"| {_decimal(med(tempos))} s ({_faixa(tempos, _decimal)} s) |"
        )
    empates = sum(b.ganho == b.guloso for b in buscas)
    linhas += [
        "",
        f"- **Recortes de {PARCEIROS_NO_RECORTE} parceiros da mesma base**, com orçamento curto e "
        f"cota de cauda longa: o genético chegou ao ótimo da enumeração em **{acertos} de "
        f"{total}**.",
        f"- O genético **empatou com o guloso** em {empates} de {len(buscas)} buscas; nas demais, "
        "ficou acima. Nunca abaixo: os dois planos gulosos estão na população inicial, e o elitismo "
        "não os perde (ADR-011).",
        "- **Abaixo do teto, no máximo** é quanto o plano pode estar abaixo do ótimo: o ótimo "
        "fica entre o ganho do plano e um limite superior por relaxação lagrangiana, que relaxa "
        "o orçamento e o máximo de ações e ignora as cotas. Com cotas, o teto é mais folgado, e "
        "a distância real é menor que a mostrada.",
        "",
        "<details><summary>Cada busca</summary>",
        "",
        "| Campanha | Rede | Semente | Ganho | Guloso | Teto | Melhora | Abaixo do teto | Tempo |",
        "|---|--:|--:|--:|--:|--:|--:|--:|--:|",
    ]
    for b in buscas:
        linhas.append(
            f"| {b.cenario} | {b.rede} | {b.semente} | {_reais(b.ganho)} | {_reais(b.guloso)} "
            f"| {_reais(b.teto)} | {_porcento(b.melhora)} | {_porcento(b.distancia)} "
            f"| {_decimal(b.segundos)} s |"
        )
    linhas += ["", "</details>", ""]
    return linhas


def montar_relatorio(resultados, redes, sementes, comando) -> str:
    from gih_nucleo import serial

    linhas = [
        "# Medição do otimizador serial — H48, H49",
        "",
        "> Gerado por `scripts/medir_otimizador.py`. **Não edite à mão**: número escrito à mão "
        "não é evidência. Para atualizar, rode o comando abaixo de novo.",
        "",
        "O genético (ADR-011) é comparado com o **melhor dos dois planos gulosos** — por razão "
        "ganho/custo e por ganho —, que é o que uma planilha faria. O tempo é o do baseline serial "
        "em Python puro: o denominador do *speedup* das versões em C++ e CUDA (RNF02).",
        "",
        "## Ambiente",
        "",
        "| Item | Valor |",
        "|---|---|",
        f"| Data | {datetime.now():%d/%m/%Y %H:%M} |",
        f"| Massa | `scripts/gerar_dados_sinteticos.py`, {PERIODOS} semanas, redes geradas com "
        f"as sementes {', '.join(map(str, redes))} |",
        "| Caminho | gerador → banco `gih_medicao` → segmentação → treino → "
        "`servico_otimizacao.montar` → busca |",
        f"| Genético | população {serial.POPULACAO}, {serial.GERACOES} gerações, "
        f"{serial.PARTIDAS} partidas, {serial.MUTACOES_POR_FILHO} mutação por filho |",
        f"| Sementes de busca | {', '.join(map(str, sementes))} |",
        f"| Python | {platform.python_version()}, uma thread |",
        f"| Processador | {platform.processor() or platform.machine()} |",
        "",
        "## Como reproduzir",
        "",
        "```bash",
        comando,
        "```",
        "",
    ]
    for parceiros, (buscas, recortes) in resultados.items():
        linhas += _secao(parceiros, buscas, recortes)
    return "\n".join(linhas)


def main() -> None:
    p = argparse.ArgumentParser(description="Mede o otimizador serial (H48, H49).")
    p.add_argument("--parceiros", type=int, nargs="+", default=[500, 2000])
    p.add_argument("--redes", type=int, nargs="+", default=list(REDES_PADRAO))
    p.add_argument("--sementes", type=int, default=3, help="sementes de busca (padrão: 3)")
    p.add_argument("--banco", default="gih_medicao")
    p.add_argument("--relatorio", default=str(RAIZ / "docs" / "medicoes" / "otimizador.md"))
    args = p.parse_args()

    url = _url_medicao(args.banco)
    if urlsplit(url).path.lstrip("/") == urlsplit(_url_base()).path.lstrip("/"):
        raise SystemExit("O banco de medição não pode ser o banco de trabalho.")
    os.environ["DATABASE_URL"] = url

    sementes = list(range(1, args.sementes + 1))
    resultados = {}
    for parceiros in args.parceiros:
        buscas, recortes = [], []
        for rede in args.redes:
            print(f"{_mil(parceiros)} parceiros, rede {rede}")
            b, r = medir_rede(parceiros, rede, sementes, url)
            buscas += b
            recortes.append(r)
        resultados[parceiros] = (buscas, recortes)

    comando = (
        "api/.venv/Scripts/python scripts/medir_otimizador.py "
        f"--parceiros {' '.join(map(str, args.parceiros))} "
        f"--redes {' '.join(map(str, args.redes))} --sementes {args.sementes}"
    )
    destino = Path(args.relatorio)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(montar_relatorio(resultados, args.redes, sementes, comando), encoding="utf-8")
    print(f"\nrelatório: {destino}")


if __name__ == "__main__":
    main()
