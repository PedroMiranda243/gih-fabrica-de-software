"""Derivações que mais de uma tela mostra — ticket médio e variação.

Vive fora das rotas porque o painel e a lista de parceiros mostram **os mesmos
dois números**. Duas implementações da mesma fórmula divergem no primeiro ajuste
de arredondamento, e o sistema passa a dizer ticket médio de R$ 48,23 numa tela
e R$ 48,24 na outra, sobre o mesmo parceiro e o mesmo período. Não quebra nada,
e destrói a confiança no painel inteiro.

Nada aqui toca o banco: recebe números, devolve números.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

CENTAVOS = Decimal("0.01")


def ticket_medio(faturamento: Decimal | None, pedidos: int | None) -> Decimal | None:
    """Ticket médio, derivado na consulta (RN04).

    Nunca é coluna: guardá-lo faria o valor divergir das parcelas que o originam
    na primeira correção de dado.

    Sem pedidos não há ticket. Devolver zero afirmaria que cada pedido valeu
    nada, quando o que houve foi ausência de pedido.
    """
    if not pedidos or faturamento is None:
        return None
    return (Decimal(faturamento) / Decimal(pedidos)).quantize(CENTAVOS, ROUND_HALF_UP)


def variacao_percentual(atual, anterior) -> Decimal | None:
    """Variação percentual, ou nulo quando ela não é definível.

    Nulo **não** é zero. Zero diz "não mudou"; nulo diz "não dá para dizer" — sem
    período anterior, ou com base anterior zerada, em que a divisão é indefinida.
    Devolver zero nesses casos desenharia estabilidade que ninguém mediu.
    """
    if atual is None or anterior is None or Decimal(anterior) == 0:
        return None
    variacao = (Decimal(atual) - Decimal(anterior)) / Decimal(anterior) * 100
    return variacao.quantize(CENTAVOS, ROUND_HALF_UP)
