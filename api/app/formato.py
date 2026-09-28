"""Os números como a tela os mostra — para o texto que a API escreve.

As mensagens (H60) e o assistente (H65) escrevem números em frases, e esses
números precisam sair **iguais aos da tela**: o gestor lê "R$ 1.234,50" no
painel e tem de ler o mesmo na resposta. Por isso a formatação é uma só, e
segue `web/src/formato.js`. Não dá para compartilhar a fonte entre Python e
JavaScript; dá para deixar o aviso aqui.

É também o que a guarda numérica confere (RN08): ela compara o número do texto
com o dos fatos na forma escrita, e os dois lados precisam sair daqui.
"""
from __future__ import annotations

import math
from datetime import date
from decimal import Decimal


def data(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def intervalo(inicio: date, fim: date) -> str:
    return f"{data(inicio)} a {data(fim)}"


def reais(valor: Decimal) -> str:
    texto = f"{valor:,.2f}"
    return "R$ " + texto.replace(",", "_").replace(".", ",").replace("_", ".")


def inteiro(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def percentual(valor: Decimal) -> str:
    """Duas casas, e o sinal sempre."""
    sinal = "+" if valor > 0 else ""
    return f"{sinal}{valor:.2f}".replace(".", ",") + "%"


def probabilidade(valor: float) -> str:
    """Em porcentagem inteira, e sem afirmar certeza que o modelo não tem.

    Abaixo de 0,5%, "0%" diria que é impossível; acima de 99,5%, "100%", que é
    certo. Nenhum dos dois é o que o modelo diz.

    Arredonda como o `Math.round` da tela, e não como o `round` do Python, que
    arredonda o meio para o par: 12,5% viraria 12% aqui e 13% na tela.
    """
    if valor < 0.005:
        return "menos de 1%"
    if valor >= 0.995:
        return "mais de 99%"
    return f"{math.floor(valor * 100 + 0.5)}%"


def ordinal(n: int) -> str:
    return f"{n}º"
