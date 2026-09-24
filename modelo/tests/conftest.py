"""Uma rede sintética em memória, para testar o modelo sem banco.

Segue a trajetória de `scripts/gerar_dados_sinteticos.py` — perfis, tendência,
sazonalidade de 4 semanas com fase por parceiro, ruído e cauda longa — sem
passar pelo banco, que este pacote não conhece. **Não é a massa da medição
oficial**: essa sai do gerador de verdade, pela API (`scripts/medir_modelo.py`).
Aqui basta ter o formato certo e movimento para aprender.

O rótulo de risco é a contagem de quedas seguidas, como na RN01 com o limiar
padrão. Na API ele vem da própria função da segmentação; aqui é uma cópia de
teste, porque o pacote não importa a API.
"""
from __future__ import annotations

import math
import random

import pytest

from gih_modelo import Serie

PERFIS = [  # rótulo, peso, tendência por período, volatilidade — os do gerador
    ("estavel", 52, 0.000, 0.06),
    ("ascensao", 16, 0.045, 0.07),
    ("queda", 14, -0.040, 0.07),
    ("volatil", 12, 0.000, 0.22),
    ("recem_chegado", 6, 0.060, 0.10),
]
CATEGORIAS = {"Restaurante": 48.0, "Lanchonete": 32.0, "Pizzaria": 62.0, "Mercado": 85.0}
LIMIAR = 2


def rotular(faturamento: list[float]) -> list[bool]:
    """Em cada ponto, se a sequência de quedas até ali chegou ao limiar."""
    rotulos, quedas = [], 0
    for i, f in enumerate(faturamento):
        quedas = quedas + 1 if i and f < faturamento[i - 1] else 0
        rotulos.append(quedas >= LIMIAR)
    return rotulos


def rede_sintetica(parceiros: int, periodos: int, semente: int = 42) -> list[Serie]:
    rng = random.Random(semente)
    series = []
    for parceiro in range(1, parceiros + 1):
        categoria = rng.choice(list(CATEGORIAS))
        perfil, _, tendencia, volatilidade = rng.choices(
            PERFIS, weights=[p[1] for p in PERFIS]
        )[0]
        base = rng.lognormvariate(7.6, 1.15)
        fase = rng.uniform(0, 2 * math.pi)
        entra = rng.randint(max(0, periodos - 3), periodos - 1) if perfil == "recem_chegado" else 0
        pontos, faturamento, pedidos = [], [], []
        for i in range(entra, periodos):
            sazonal = 1 + 0.08 * math.cos(2 * math.pi * i / 4 + fase)
            crescimento = (1 + tendencia) ** (i - entra)
            valor = max(50.0, base * crescimento * sazonal * rng.gauss(1, volatilidade))
            pontos.append(i)
            faturamento.append(round(valor, 2))
            pedidos.append(max(1, round(valor / CATEGORIAS[categoria])))
        series.append(
            Serie(
                parceiro=parceiro,
                categoria=categoria,
                periodos=tuple(pontos),
                faturamento=tuple(faturamento),
                pedidos=tuple(pedidos),
                em_risco=tuple(rotular(faturamento)),
            )
        )
    return series


@pytest.fixture(scope="session")
def rede() -> list[Serie]:
    """300 parceiros e 10 semanas: pequena para o teste ser rápido, grande o
    bastante para haver amostra em cada parte da separação."""
    return rede_sintetica(300, 10)
