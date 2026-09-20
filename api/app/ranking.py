"""A posição de cada parceiro no ranking de um período.

Vive fora das rotas porque **três coisas precisam ler exatamente a mesma
posição**: o ranking do painel (H31), a mobilidade do Top N (H35) e a
segmentação (H33, que decide o segmento Top por ela). Se cada uma calculasse a
sua, um desempate diferente bastaria para o painel dizer que um parceiro saiu do
Top 15 enquanto a tabela ao lado mostra ele dentro.

É também a razão de a mobilidade não poder sair do segmento armazenado (RN02):
como Em Risco vence Top na precedência de RN01, um parceiro entre os N maiores
mas em queda fica gravado como EM_RISCO. A posição é aqui; o segmento é
consequência dela, nunca o contrário.
"""
from __future__ import annotations

from sqlalchemy import Select, func, select

from app.modelos import Metrica, Parceiro


def posicoes(periodo_id: int) -> Select:
    """Ranking do período, com a posição calculada por função de janela.

    **O desempate é explícito e estável**: faturamento decrescente e, em caso de
    empate, nome crescente. Sem o segundo critério o banco fica livre para
    devolver os empatados em qualquer ordem, e a mesma base produziria posições
    diferentes entre duas execuções — o painel anunciaria subida e queda que não
    aconteceram.

    `row_number` em vez de `rank`: posições distintas, sem buracos. A mobilidade
    do Top N compara posição com posição, e posição repetida tornaria "entrou" e
    "saiu" ambíguos.
    """
    return (
        select(
            Metrica.parceiro_id.label("parceiro_id"),
            Metrica.faturamento.label("faturamento"),
            Metrica.pedidos.label("pedidos"),
            func.row_number()
            .over(order_by=(Metrica.faturamento.desc(), Parceiro.nome.asc()))
            .label("posicao"),
        )
        .join(Parceiro, Parceiro.id == Metrica.parceiro_id)
        .where(Metrica.periodo_id == periodo_id)
    )
