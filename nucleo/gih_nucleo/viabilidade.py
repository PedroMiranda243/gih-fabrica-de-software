"""Decide se a campanha tem solução antes de procurar uma (H52, RF31, RN07).

Com as cotas em contagem (RN11), a pergunta tem resposta exata, e não
heurística. Toda ação custa pelo menos o que custa a mais barata, e todo
parceiro pode recebê-la; então os mínimos cabem na campanha se, e somente se,
o **menor conjunto de parceiros que os cumpre** couber no máximo de ações e no
orçamento pagando a ação mais barata para cada um.

O menor conjunto se monta em dois passos:

1. Em cada categoria, o mínimo é preenchido primeiro com parceiros da cauda
   longa: cada um conta para as duas cotas ao mesmo tempo.
2. O que ainda faltar de cauda longa sai das categorias que têm folga no
   máximo, ou de quem não tem categoria confirmada.

Nenhum conjunto que cumpra as cotas é menor que esse. E ele é também o começo
da solução inicial do genético, que por isso nasce viável (ADR-011).

Quando falha, a recusa diz qual restrição e quanto falta: `exigido` contra
`disponivel`. O texto para a pessoa é montado pela API, que sabe o nome da
categoria e formata dinheiro; o núcleo só conhece índices e centavos.
"""
from __future__ import annotations

from dataclasses import dataclass

from gih_nucleo.problema import Instancia

# Qual restrição impede a campanha, na ordem em que são conferidas.
COTA_CATEGORIA = "cota_categoria"  # o mínimo passa do máximo
ELEGIVEIS_CATEGORIA = "elegiveis_categoria"  # a categoria não tem parceiros para o mínimo
CAUDA_LONGA = "cauda_longa"  # não há cauda longa que caiba nas cotas
MAXIMO_ACOES = "maximo_acoes"  # os mínimos somam mais que K
ORCAMENTO = "orcamento"  # os mínimos não cabem no orçamento nem com a ação mais barata


@dataclass(frozen=True)
class Inviabilidade:
    restricao: str
    exigido: int  # contagem, ou centavos quando a restrição é o orçamento
    disponivel: int
    categoria: int | None = None

    @property
    def falta(self) -> int:
        return self.exigido - self.disponivel


class Inviavel(Exception):
    """A campanha não tem solução; `motivo` diz por quê. Nenhum plano é devolvido (RN07)."""

    def __init__(self, motivo: Inviabilidade) -> None:
        super().__init__(motivo.restricao)
        self.motivo = motivo


def _diagnosticar(inst: Instancia) -> tuple[list[int], Inviabilidade | None]:
    barata = inst.acao_mais_barata

    # Dentro de cada grupo, os de maior ganho com a ação mais barata primeiro:
    # o conjunto mínimo já sai com os melhores candidatos, e o desempate pelo
    # índice o deixa igual em qualquer versão.
    def prioridade(i: int) -> tuple[int, int]:
        return (-inst.ganho[i][barata], i)

    membros: list[list[int]] = [[] for _ in range(inst.categorias)]
    cauda_sem_categoria = []
    for i, k in enumerate(inst.categoria):
        if k >= 0:
            membros[k].append(i)
        elif inst.cauda[i]:
            cauda_sem_categoria.append(i)

    minimos, maximos = inst.minimo_categoria, inst.maximo_categoria
    for k in range(inst.categorias):
        if minimos[k] > maximos[k]:
            return [], Inviabilidade(COTA_CATEGORIA, minimos[k], maximos[k], k)
    for k in range(inst.categorias):
        if minimos[k] > len(membros[k]):
            return [], Inviabilidade(ELEGIVEIS_CATEGORIA, minimos[k], len(membros[k]), k)

    escolhidos: list[int] = []
    cobertura = 0  # quanto da cota da cauda os mínimos de categoria já cobrem
    reserva_cauda = list(cauda_sem_categoria)
    for k in range(inst.categorias):
        ordem = sorted(membros[k], key=prioridade)
        da_cauda = [i for i in ordem if inst.cauda[i]]
        fora_da_cauda = [i for i in ordem if not inst.cauda[i]]
        usados = min(minimos[k], len(da_cauda))
        escolhidos += da_cauda[:usados]
        escolhidos += fora_da_cauda[: minimos[k] - usados]
        cobertura += usados
        # A cauda que sobra nesta categoria só completa a cota até o máximo dela.
        reserva_cauda += da_cauda[usados:][: maximos[k] - minimos[k]]

    falta_cauda = max(0, inst.minimo_cauda - cobertura)
    if falta_cauda > len(reserva_cauda):
        return [], Inviabilidade(CAUDA_LONGA, inst.minimo_cauda, cobertura + len(reserva_cauda))
    escolhidos += sorted(reserva_cauda, key=prioridade)[:falta_cauda]

    if len(escolhidos) > inst.maximo_acoes:
        return [], Inviabilidade(MAXIMO_ACOES, len(escolhidos), inst.maximo_acoes)
    custo = len(escolhidos) * inst.custo[barata]
    if custo > inst.orcamento:
        return [], Inviabilidade(ORCAMENTO, custo, inst.orcamento)
    return sorted(escolhidos), None


def verificar_viabilidade(inst: Instancia) -> Inviabilidade | None:
    """`None` quando a campanha tem solução; senão, a primeira restrição que a impede."""
    return _diagnosticar(inst)[1]


def conjunto_minimo(inst: Instancia) -> list[int]:
    """Os parceiros do menor conjunto que cumpre as cotas; levanta `Inviavel` se não houver."""
    escolhidos, motivo = _diagnosticar(inst)
    if motivo is not None:
        raise Inviavel(motivo)
    return escolhidos
