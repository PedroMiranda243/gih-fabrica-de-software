"""Instâncias de teste: pequenas o bastante para a enumeração conferir o ótimo."""
from __future__ import annotations

import random

import pytest

from gih_nucleo import SEM_CATEGORIA, Instancia


def sortear_instancia(
    semente: int, parceiros: int = 7, acoes: int = 3, categorias: int = 2
) -> Instancia:
    """Uma campanha pequena sorteada, com cotas — viável ou não, conforme o sorteio.

    Os números seguem a escala da base de demonstração em centavos: ações de
    R$ 1 a R$ 9 e ganhos de até R$ 50, com orçamento para algumas ações só.
    """
    rng = random.Random(semente)
    custo = tuple(rng.randint(100, 900) for _ in range(acoes))
    ganho = tuple(
        tuple(rng.choice([0, rng.randint(50, 5000)]) for _ in range(acoes))
        for _ in range(parceiros)
    )
    categoria = tuple(rng.choice([SEM_CATEGORIA, *range(categorias)]) for _ in range(parceiros))
    cauda = tuple(rng.random() < 0.5 for _ in range(parceiros))
    maximo_acoes = rng.randint(1, parceiros)
    minimo = tuple(rng.choice([0, 0, 1, 2]) for _ in range(categorias))
    maximo = tuple(m + rng.choice([0, 1, 2, maximo_acoes]) for m in minimo)
    return Instancia(
        ganho=ganho,
        custo=custo,
        orcamento=rng.randint(min(custo), sum(custo) * 2),
        maximo_acoes=maximo_acoes,
        categoria=categoria,
        cauda=cauda,
        minimo_categoria=minimo,
        maximo_categoria=maximo,
        minimo_cauda=rng.choice([0, 0, 1, 2, 3]),
    )


def sortear_viavel(
    parceiros: int, acoes: int = 3, categorias: int = 2, a_partir: int = 0
) -> Instancia:
    """A primeira instância sorteada viável a partir de `a_partir`: o teste que a usa
    não depende da sorte de o sorteio cair num caso com plano."""
    from gih_nucleo import verificar_viabilidade

    for semente in range(a_partir, a_partir + 1000):
        inst = sortear_instancia(semente, parceiros, acoes, categorias)
        if verificar_viabilidade(inst) is None:
            return inst
    raise AssertionError("Nenhuma instância viável em mil sorteios.")


@pytest.fixture
def mochila() -> Instancia:
    """O contraexemplo do guloso, o da mochila: a ação barata ocupa o orçamento.

    Pela razão ganho/custo, o guloso dá a ação barata aos dois (60 + 55 = 115,
    custo 20) e não cabe mais nada. O ótimo é a ação cara para os dois:
    100 + 95 = 195, custo 50.
    """
    return Instancia(
        ganho=((60, 100), (55, 95)),
        custo=(10, 25),
        orcamento=50,
        maximo_acoes=2,
        categoria=(SEM_CATEGORIA, SEM_CATEGORIA),
        cauda=(False, False),
        minimo_categoria=(),
        maximo_categoria=(),
    )
