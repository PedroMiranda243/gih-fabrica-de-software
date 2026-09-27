"""A comparação de dois planos de campanha — RF35, UC08-A3, história H59.

O gestor calcula um plano, muda um parâmetro — mais orçamento, outra cota — e
quer saber **o que mudou por causa disso**. A comparação responde três coisas,
todas decididas aqui, e não na tela (regra 2.4):

- **os parâmetros que mudaram** de um pedido para o outro;
- **o resultado**: a diferença no ganho esperado, no custo e no número de ações;
- **parceiro a parceiro**: quem recebeu ação diferente, quem entrou num plano e
  não no outro, e quem ficou igual.

**E se a comparação é justa.** Dois planos calculados com previsões diferentes —
o modelo foi treinado de novo entre um e outro, ou chegou um período novo —
mudam o ganho de cada parceiro por causa da previsão, e não do parâmetro. A
comparação não recusa: diz, para a tela avisar.

Função pura sobre as duas respostas: não abre o banco.
"""
from __future__ import annotations

from app.esquemas import (
    ComparacaoPlanos,
    CotaCategoria,
    ExecucaoResposta,
    ItemComparado,
    ItemPlanoResposta,
    ParametrosCampanha,
    ResumoComparacao,
    SituacaoNaComparacao,
)

# Os campos do pedido que a tela mostra, na ordem dela.
CAMPOS = (
    "orcamento",
    "maximo_acoes",
    "cota_cauda_longa",
    "cotas_categoria",
    "aplicacao_inicio",
    "aplicacao_fim",
    "modo",
)

_ORDEM = {
    SituacaoNaComparacao.MUDOU: 0,
    SituacaoNaComparacao.SO_A: 1,
    SituacaoNaComparacao.SO_B: 2,
    SituacaoNaComparacao.IGUAL: 3,
}


def _cotas(cotas: list[CotaCategoria]) -> list[tuple]:
    """As cotas sem depender da ordem em que foram digitadas."""
    return sorted((c.categoria_id, c.minimo, c.maximo) for c in cotas)


def parametros_diferentes(a: ParametrosCampanha, b: ParametrosCampanha) -> list[str]:
    """Os campos que mudaram. Os números se comparam como número: 12.000 e 12.000,00 são
    o mesmo orçamento."""
    diferentes = []
    for campo in CAMPOS:
        va, vb = getattr(a, campo), getattr(b, campo)
        if campo == "cotas_categoria":
            va, vb = _cotas(va), _cotas(vb)
        if va != vb:
            diferentes.append(campo)
    return diferentes


def comparar_itens(
    itens_a: list[ItemPlanoResposta], itens_b: list[ItemPlanoResposta]
) -> list[ItemComparado]:
    """Os parceiros dos dois planos, com onde cada um está.

    Primeiro os que mudaram de ação, e entre eles os de maior diferença de ganho;
    depois os que só estão num dos planos e os iguais, do maior ganho para o menor.
    """
    por_a = {i.parceiro_id: i for i in itens_a}
    por_b = {i.parceiro_id: i for i in itens_b}
    comparados = []
    for parceiro_id in por_a.keys() | por_b.keys():
        ia, ib = por_a.get(parceiro_id), por_b.get(parceiro_id)
        if ia and ib:
            mesma_acao = ia.acao_id == ib.acao_id
            situacao = SituacaoNaComparacao.IGUAL if mesma_acao else SituacaoNaComparacao.MUDOU
        else:
            situacao = SituacaoNaComparacao.SO_A if ia else SituacaoNaComparacao.SO_B
        qualquer = ia or ib
        comparados.append(
            ItemComparado(
                parceiro_id=parceiro_id,
                parceiro=qualquer.parceiro,
                segmento=qualquer.segmento,
                situacao=situacao,
                acao_a=ia.acao if ia else None,
                acao_b=ib.acao if ib else None,
                ganho_a=ia.ganho if ia else None,
                ganho_b=ib.ganho if ib else None,
            )
        )

    def chave(item: ItemComparado):
        if item.situacao == SituacaoNaComparacao.MUDOU:
            peso = abs(item.ganho_b - item.ganho_a)
        else:
            peso = item.ganho_a if item.ganho_a is not None else item.ganho_b
        return (_ORDEM[item.situacao], -peso, item.parceiro)

    return sorted(comparados, key=chave)


def comparar(
    a: ExecucaoResposta,
    b: ExecucaoResposta,
    *,
    mesmas_previsoes: bool,
) -> ComparacaoPlanos:
    """Os dois planos — com os itens — e o que difere entre eles."""
    itens = comparar_itens(a.itens or [], b.itens or [])
    contagem = {s: 0 for s in SituacaoNaComparacao}
    for item in itens:
        contagem[item.situacao] += 1
    return ComparacaoPlanos(
        # Os itens já estão juntos em `itens`: repeti-los em cada lado dobraria a resposta.
        a=a.model_copy(update={"itens": None}),
        b=b.model_copy(update={"itens": None}),
        parametros_diferentes=parametros_diferentes(a.parametros, b.parametros),
        mesmas_previsoes=mesmas_previsoes,
        diferenca_uplift=b.uplift_total - a.uplift_total,
        diferenca_custo=b.custo_total - a.custo_total,
        diferenca_acoes=(b.acoes or 0) - (a.acoes or 0),
        resumo=ResumoComparacao(
            mudaram=contagem[SituacaoNaComparacao.MUDOU],
            so_a=contagem[SituacaoNaComparacao.SO_A],
            so_b=contagem[SituacaoNaComparacao.SO_B],
            iguais=contagem[SituacaoNaComparacao.IGUAL],
        ),
        itens=itens,
    )
