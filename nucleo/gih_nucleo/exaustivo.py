"""O ótimo exato, por enumeração, para instâncias pequenas (H48).

É a régua do genético: nas instâncias pequenas, o genético precisa chegar ao
mesmo ganho que a enumeração. Não é um solver pronto, que a ADR-002 descarta
para o problema de verdade; é a busca completa, com poda, que só termina em
tempo útil com uma dezena de parceiros — `(A+1)^N` combinações.
"""
from __future__ import annotations

from gih_nucleo.problema import Instancia

LIMITE_PARCEIROS = 12


def otimo(inst: Instancia) -> tuple[int, tuple[int, ...]] | None:
    """O maior ganho viável e um plano que o atinge; `None` se não houver plano viável.

    No empate de ganho, fica o primeiro plano na ordem da enumeração — "sem
    ação" antes de qualquer ação, parceiro a parceiro.
    """
    n, a = inst.parceiros, inst.acoes
    if n > LIMITE_PARCEIROS:
        raise ValueError(f"Enumeração é para até {LIMITE_PARCEIROS} parceiros.")

    # O que ainda dá para ganhar do parceiro i em diante, no melhor caso: poda
    # o ramo que não tem como superar o melhor já encontrado.
    teto = [0] * (n + 1)
    for i in range(n - 1, -1, -1):
        teto[i] = teto[i + 1] + max(inst.ganho[i])

    genes = [0] * n
    por_categoria = [0] * inst.categorias
    melhor_ganho = -1
    melhor_plano: tuple[int, ...] | None = None

    def buscar(i: int, ganho: int, custo: int, acoes: int, cauda: int) -> None:
        nonlocal melhor_ganho, melhor_plano
        if ganho + teto[i] <= melhor_ganho:
            return
        if i == n:
            if cauda >= inst.minimo_cauda and all(
                por_categoria[k] >= inst.minimo_categoria[k] for k in range(inst.categorias)
            ):
                melhor_ganho, melhor_plano = ganho, tuple(genes)
            return

        buscar(i + 1, ganho, custo, acoes, cauda)  # sem ação para o parceiro i
        if acoes >= inst.maximo_acoes:
            return
        k = inst.categoria[i]
        if k >= 0 and por_categoria[k] >= inst.maximo_categoria[k]:
            return
        for acao in range(a):
            if custo + inst.custo[acao] > inst.orcamento:
                continue
            genes[i] = acao + 1
            if k >= 0:
                por_categoria[k] += 1
            buscar(
                i + 1,
                ganho + inst.ganho[i][acao],
                custo + inst.custo[acao],
                acoes + 1,
                cauda + inst.cauda[i],
            )
            if k >= 0:
                por_categoria[k] -= 1
            genes[i] = 0

    buscar(0, 0, 0, 0, 0)
    return None if melhor_plano is None else (melhor_ganho, melhor_plano)
