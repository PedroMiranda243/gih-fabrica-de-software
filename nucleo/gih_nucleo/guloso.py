"""Os planos gulosos: os mínimos das cotas, e depois o que parece melhor a cada passo.

Dois critérios, porque cada um erra onde o outro acerta:

- **Por razão ganho/custo** (`RAZAO`), que é o certo quando o orçamento aperta.
  Quando quem aperta é o máximo de ações K, ele gasta as vagas em ações baratas
  e deixa orçamento sobrando.
- **Por ganho** (`GANHO`), que é o certo quando K aperta, e erra quando o
  orçamento acaba em poucas ações caras.

Servem a duas coisas:

- **Soluções iniciais do genético.** Viáveis por construção, elas garantem, com
  o elitismo, que o genético nunca devolve algo pior que elas nem inviável
  (ADR-011).
- **Referência de qualidade.** É o que uma planilha faria, e o genético precisa
  superá-lo onde ele erra (H48). O erro é ser míope: escolhe um par por vez e
  não volta atrás.
"""
from __future__ import annotations

from functools import cmp_to_key

from gih_nucleo.problema import Instancia
from gih_nucleo.viabilidade import conjunto_minimo

RAZAO = "razao"
GANHO = "ganho"


def completar(inst: Instancia, genes: list[int], criterio: str = RAZAO) -> list[int]:
    """Acrescenta pares (parceiro, ação) pelo critério, sem violar nada.

    Não tira nem troca o que já está em `genes`: só preenche parceiros sem ação,
    enquanto couber no orçamento, em K e no máximo da categoria.
    """
    genes = list(genes)
    custo = sum(inst.custo[g - 1] for g in genes if g)
    acoes = sum(1 for g in genes if g)
    por_categoria = [0] * inst.categorias
    for i, g in enumerate(genes):
        if g and inst.categoria[i] >= 0:
            por_categoria[inst.categoria[i]] += 1

    pares = [
        (i, a)
        for i in range(inst.parceiros)
        if not genes[i]
        for a in range(inst.acoes)
        if inst.ganho[i][a] > 0
    ]

    # Razão comparada em inteiros, por produto cruzado: dividir daria `float`,
    # e o desempate mudaria conforme a linguagem arredonda. Um critério desempata
    # o outro; depois, menor parceiro e menor ação.
    def pela_razao(p: tuple[int, int], q: tuple[int, int]) -> int:
        (i, a), (j, b) = p, q
        esquerda, direita = inst.ganho[i][a] * inst.custo[b], inst.ganho[j][b] * inst.custo[a]
        return (esquerda < direita) - (esquerda > direita)

    def pelo_ganho(p: tuple[int, int], q: tuple[int, int]) -> int:
        (i, a), (j, b) = p, q
        return (inst.ganho[i][a] < inst.ganho[j][b]) - (inst.ganho[i][a] > inst.ganho[j][b])

    primeiro, segundo = (pela_razao, pelo_ganho) if criterio == RAZAO else (pelo_ganho, pela_razao)

    def comparar(p: tuple[int, int], q: tuple[int, int]) -> int:
        return primeiro(p, q) or segundo(p, q) or (p > q) - (p < q)

    for i, a in sorted(pares, key=cmp_to_key(comparar)):
        if genes[i] or acoes >= inst.maximo_acoes:
            continue
        if custo + inst.custo[a] > inst.orcamento:
            continue
        k = inst.categoria[i]
        if k >= 0 and por_categoria[k] >= inst.maximo_categoria[k]:
            continue
        genes[i] = a + 1
        custo += inst.custo[a]
        acoes += 1
        if k >= 0:
            por_categoria[k] += 1
    return genes


def guloso(inst: Instancia, criterio: str = RAZAO) -> list[int]:
    """O plano guloso completo; levanta `Inviavel` quando as cotas não cabem."""
    if criterio not in (RAZAO, GANHO):
        raise ValueError(f"Critério desconhecido: {criterio!r}")
    genes = [0] * inst.parceiros
    barata = inst.acao_mais_barata
    for i in conjunto_minimo(inst):
        genes[i] = barata + 1
    return completar(inst, genes, criterio)
