"""O cenário sintético do benchmark (UC09, RF16, H57).

O benchmark compara os modos num problema que o gestor escolhe pelo tamanho —
parceiros e tipos de ação —, e não na base de trabalho: a base real tem a
escala da operação, pequena demais para mostrar o ganho do paralelismo
(`docs/07` §4.3). A campanha é montada aqui, sem banco, com a mesma forma de uma
campanha de verdade:

- o ganho de cada ação segue a RN10, `F̂·crescimento + F̂·p·retenção`, em
  centavos, com o faturamento previsto e a chance de risco sorteados;
- 1 parceiro em cada 10 ainda sem categoria confirmada: recebe ação, e não
  conta em cota (RN05);
- as restrições apertam, em proporção aos parceiros: o máximo de ações é 1 para
  cada 40, e o orçamento paga R$ 200 por ação, abaixo do custo médio do
  catálogo;
- duas categorias pedem ao menos 10% das ações, nenhuma passa de 40%, e a cauda
  longa — quem está fora do Top 15 — fica com ao menos 30% (RN11), arredondadas
  como a API arredonda.

**O mesmo tamanho dá o mesmo problema.** O sorteio sai da semente e do número
de parceiros, e as ações são as do catálogo do gerador de dados sintéticos, na
ordem dele; além das cinco dele, as seguintes são sorteadas nas mesmas faixas,
com outro gerador — o que não muda os parceiros. Com cinco ações e a semente
padrão, é a campanha que `scripts/medir_nucleo.py` mede.
"""
from __future__ import annotations

import math
import random

from gih_nucleo.problema import SEM_CATEGORIA, Instancia

TOP_N = 15  # quem está fora do Top N no ranking é cauda longa (RN11, RN02)
CATEGORIAS = 5
SEMENTE = 2026

PARCEIROS_MINIMO, PARCEIROS_MAXIMO = 100, 10_000  # a faixa do gerador (RF16)
ACOES_MINIMO, ACOES_MAXIMO = 1, 10

# (custo em centavos, crescimento, retenção): o catálogo de
# `scripts/gerar_dados_sinteticos.py` (`ACOES`), na mesma ordem. Um teste
# confere que os dois continuam iguais.
CATALOGO = (
    (12_000, 0.08, 0.03),  # Cupom de primeira compra
    (26_000, 0.14, 0.05),  # Destaque na vitrine
    (48_000, 0.22, 0.08),  # Campanha de categoria
    (9_000, 0.06, 0.30),  # Visita de relacionamento
    (35_000, 0.18, 0.12),  # Frete subsidiado
)


def _acoes(quantas: int, semente: int) -> list[tuple[int, float, float]]:
    """As do catálogo e, passando dele, sorteadas nas faixas dele."""
    acoes = list(CATALOGO[:quantas])
    rng = random.Random(semente * 31 + quantas)
    custos = [c for c, _, _ in CATALOGO]
    while len(acoes) < quantas:
        acoes.append(
            (
                rng.randrange(min(custos), max(custos) + 1, 500),
                round(rng.uniform(0.06, 0.22), 2),
                round(rng.uniform(0.03, 0.30), 2),
            )
        )
    return acoes


def sintetico(parceiros: int, acoes: int = 5, semente: int = SEMENTE) -> Instancia:
    """Uma campanha de `parceiros` elegíveis e `acoes` tipos de ação, sempre viável."""
    if not PARCEIROS_MINIMO <= parceiros <= PARCEIROS_MAXIMO:
        raise ValueError(
            f"O cenário vai de {PARCEIROS_MINIMO} a {PARCEIROS_MAXIMO} parceiros (RF16)."
        )
    if not ACOES_MINIMO <= acoes <= ACOES_MAXIMO:
        raise ValueError(f"O cenário vai de {ACOES_MINIMO} a {ACOES_MAXIMO} tipos de ação.")
    catalogo = _acoes(acoes, semente)
    rng = random.Random(semente + parceiros)
    previsto, ganho, categoria = [], [], []
    for _ in range(parceiros):
        faturamento = rng.lognormvariate(12.1, 1.0)  # centavos por período
        risco = rng.random() * 0.6
        previsto.append(faturamento)
        # RN10: u = F̂·c + F̂·p·r
        ganho.append(tuple(int(faturamento * c + faturamento * risco * r) for _, c, r in catalogo))
        categoria.append(SEM_CATEGORIA if rng.random() < 0.1 else rng.randrange(CATEGORIAS))
    ordem = sorted(range(parceiros), key=lambda i: -previsto[i])
    no_top = set(ordem[:TOP_N])

    k = parceiros // 40
    minimo = math.ceil(k * 0.1)
    # Com poucas ações, 40% arredondado para baixo fica abaixo do mínimo para
    # cima — com K = 2, zero contra um —, e a campanha seria inviável por
    # construção. O máximo nunca fica abaixo do mínimo; de K = 3 em diante, nada
    # muda.
    maximo = max(math.floor(k * 0.4), minimo)
    return Instancia(
        ganho=tuple(ganho),
        custo=tuple(custo for custo, _, _ in catalogo),
        orcamento=k * 20_000,
        maximo_acoes=k,
        categoria=tuple(categoria),
        cauda=tuple(i not in no_top for i in range(parceiros)),
        minimo_categoria=(minimo, minimo, 0, 0, 0),
        maximo_categoria=(maximo,) * CATEGORIAS,
        minimo_cauda=math.ceil(k * 0.3),
    )
