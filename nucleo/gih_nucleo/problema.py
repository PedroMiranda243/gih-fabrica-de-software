"""O problema da campanha, em números inteiros (`docs/07` §4.1, ADR-011).

O núcleo não sabe o que é um parceiro, uma categoria ou um real. Recebe da API
uma `Instancia` já traduzida:

- o ganho de cada par (parceiro, ação), em centavos (RN10);
- o custo de cada ação, em centavos;
- o orçamento e o máximo de ações K;
- a categoria **confirmada** de cada parceiro, ou -1 (RN11);
- se o parceiro é da cauda longa;
- as cotas, **já em contagem** (RN11).

Uma solução é uma lista de genes, um por parceiro: 0 é "sem ação" e `a + 1` é
a ação `a`.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

SEM_CATEGORIA = -1


class InstanciaInvalida(ValueError):
    """A instância não descreve um problema: formato ou valor impossível."""


@dataclass(frozen=True)
class Instancia:
    ganho: tuple[tuple[int, ...], ...]  # [parceiro][ação], centavos
    custo: tuple[int, ...]  # [ação], centavos
    orcamento: int  # centavos
    maximo_acoes: int  # K
    categoria: tuple[int, ...]  # [parceiro], SEM_CATEGORIA quando não confirmada
    cauda: tuple[bool, ...]  # [parceiro]
    minimo_categoria: tuple[int, ...]  # [categoria], contagem
    maximo_categoria: tuple[int, ...]  # [categoria], contagem
    minimo_cauda: int = 0

    def __post_init__(self) -> None:
        n, a = len(self.ganho), len(self.custo)
        if a == 0:
            raise InstanciaInvalida("O catálogo não tem nenhuma ação.")
        # Custo zero não consome orçamento, e a violação de orçamento é medida
        # em ações da mais barata: dividiria por zero (ADR-011).
        if any(c <= 0 for c in self.custo):
            raise InstanciaInvalida("Toda ação precisa custar mais que zero.")
        if any(len(linha) != a for linha in self.ganho):
            raise InstanciaInvalida("Cada parceiro precisa de um ganho por ação.")
        if any(g < 0 for linha in self.ganho for g in linha):
            raise InstanciaInvalida("Ganho negativo.")
        if len(self.categoria) != n or len(self.cauda) != n:
            raise InstanciaInvalida("Categoria e cauda longa precisam de um valor por parceiro.")
        c = len(self.minimo_categoria)
        if len(self.maximo_categoria) != c:
            raise InstanciaInvalida("Mínimo e máximo por categoria precisam do mesmo tamanho.")
        if any(k != SEM_CATEGORIA and not 0 <= k < c for k in self.categoria):
            raise InstanciaInvalida("Parceiro numa categoria que não tem cota definida.")
        if min(self.orcamento, self.maximo_acoes, self.minimo_cauda) < 0:
            raise InstanciaInvalida("Orçamento, máximo de ações e cotas não podem ser negativos.")
        if any(v < 0 for v in (*self.minimo_categoria, *self.maximo_categoria)):
            raise InstanciaInvalida("Cota negativa.")

    @property
    def parceiros(self) -> int:
        return len(self.ganho)

    @property
    def acoes(self) -> int:
        return len(self.custo)

    @property
    def categorias(self) -> int:
        return len(self.minimo_categoria)

    @cached_property
    def acao_mais_barata(self) -> int:
        """O índice da ação de menor custo; no empate, a de menor índice."""
        return min(range(self.acoes), key=lambda a: (self.custo[a], a))


@dataclass(frozen=True)
class Avaliacao:
    ganho: int
    custo: int
    acoes: int
    por_categoria: tuple[int, ...]
    cauda: int
    violacao: int

    @property
    def viavel(self) -> bool:
        return self.violacao == 0


def avaliar(inst: Instancia, genes: list[int] | tuple[int, ...]) -> Avaliacao:
    """Ganho, custo, contagens e violação de uma solução.

    A violação é inteira e em unidades de ação (ADR-011): o que passa de K e dos
    máximos, o que falta nos mínimos, e o excesso de orçamento em ações da mais
    barata, arredondado para cima. Zero é viável.

    É o trecho mais executado do genético — e o que a GPU vai paralelizar —,
    por isso é um laço só, sem nada que não seja soma e contagem.
    """
    ganho = custo = acoes = cauda = 0
    por_categoria = [0] * inst.categorias
    tabela, custos, categorias, caudas = inst.ganho, inst.custo, inst.categoria, inst.cauda
    for i, g in enumerate(genes):
        if g:
            ganho += tabela[i][g - 1]
            custo += custos[g - 1]
            acoes += 1
            k = categorias[i]
            if k >= 0:
                por_categoria[k] += 1
            if caudas[i]:
                cauda += 1

    violacao = max(0, acoes - inst.maximo_acoes) + max(0, inst.minimo_cauda - cauda)
    for k, n in enumerate(por_categoria):
        violacao += max(0, inst.minimo_categoria[k] - n) + max(0, n - inst.maximo_categoria[k])
    excesso = custo - inst.orcamento
    if excesso > 0:
        barata = inst.custo[inst.acao_mais_barata]
        violacao += -(-excesso // barata)  # divisão arredondada para cima, em inteiros

    return Avaliacao(ganho, custo, acoes, tuple(por_categoria), cauda, violacao)


def melhor(a: Avaliacao, b: Avaliacao) -> bool:
    """`a` é estritamente melhor que `b`, pela comparação por viabilidade.

    Viável vence inviável; entre viáveis, maior ganho; entre inviáveis, menor
    violação e, nela empatada, maior ganho. Empate completo não é "melhor" — e
    quem chama mantém o de menor índice, o que fixa o desempate nas três
    versões (ADR-011).
    """
    if a.viavel != b.viavel:
        return a.viavel
    if a.viavel:
        return a.ganho > b.ganho
    if a.violacao != b.violacao:
        return a.violacao < b.violacao
    return a.ganho > b.ganho


def verificar_plano(inst: Instancia, genes: list[int] | tuple[int, ...]) -> list[str]:
    """As restrições que o plano viola; vazio quando ele pode ser entregue (RN07).

    Escrito de propósito sem reaproveitar `avaliar`: é a segunda chave da
    porta. Um defeito na avaliação que o genético usa não passa por aqui junto.
    """
    problemas = []
    if len(genes) != inst.parceiros:
        return [f"o plano tem {len(genes)} genes para {inst.parceiros} parceiros"]
    if any(not 0 <= g <= inst.acoes for g in genes):
        return ["o plano usa uma ação que não existe no catálogo"]

    escolhidos = [i for i, g in enumerate(genes) if g != 0]
    gasto = sum(inst.custo[genes[i] - 1] for i in escolhidos)
    if gasto > inst.orcamento:
        problemas.append(f"orçamento: gasta {gasto}, o limite é {inst.orcamento}")
    if len(escolhidos) > inst.maximo_acoes:
        problemas.append(f"máximo de ações: {len(escolhidos)}, o limite é {inst.maximo_acoes}")

    for k in range(inst.categorias):
        n = sum(1 for i in escolhidos if inst.categoria[i] == k)
        if n < inst.minimo_categoria[k]:
            problemas.append(f"categoria {k}: {n} ações, o mínimo é {inst.minimo_categoria[k]}")
        if n > inst.maximo_categoria[k]:
            problemas.append(f"categoria {k}: {n} ações, o máximo é {inst.maximo_categoria[k]}")

    na_cauda = sum(1 for i in escolhidos if inst.cauda[i])
    if na_cauda < inst.minimo_cauda:
        problemas.append(f"cauda longa: {na_cauda} ações, o mínimo é {inst.minimo_cauda}")
    return problemas
