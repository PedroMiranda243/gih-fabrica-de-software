"""O otimizador serial em Python: o baseline de corretude e de tempo (H49, ADR-011).

Algoritmo genético com partidas independentes. Em cada partida:

- **geração 0:** as duas soluções gulosas, por razão e por ganho (viáveis por
  construção), e indivíduos sorteados;
- **cada geração seguinte:** o melhor da anterior passa intacto (elitismo); os
  demais filhos saem de dois torneios de dois, cruzamento uniforme e mutação
  que sorteia outro valor para o gene;
- a comparação é por viabilidade (`problema.melhor`), sem penalidade para
  calibrar.

O melhor entre as partidas é o plano. Como as soluções gulosas estão em toda
partida e o elitismo nunca perde a melhor delas, o plano devolvido é viável
sempre que a campanha for — e é pelo menos tão bom quanto os dois gulosos.

**Python puro, sem NumPy no laço.** Este é o denominador do *speedup* (RNF02).
Vetorizá-lo deixaria o baseline mais rápido e o ganho medido menos honesto.

**Por que cada sorteio tem coordenadas, e não uma sequência.** O filho `j` da
geração `g` depende só da geração anterior e dos sorteios
`(semente, partida, g, j, posição)`. O C++ com OpenMP e o CUDA vão calcular os
filhos em paralelo, em qualquer ordem, e chegar à mesma população — portanto
ao mesmo plano. As posições `0..N-1` são os genes; `N..N+3`, os quatro
sorteios dos torneios.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from gih_nucleo.aleatorio import MILHAO, encadear, sorteio
from gih_nucleo.guloso import GANHO, RAZAO, guloso
from gih_nucleo.problema import Avaliacao, Instancia, avaliar, melhor

POPULACAO = 48
GERACOES = 150
PARTIDAS = 4
# Mutações esperadas por filho, e não por gene: com 500 ou com 2.000
# parceiros, cada filho muda em média um gene. Uma taxa fixa por gene mudaria
# 4x mais genes na base de 2.000 do que na de 500. Um é o medido: com dois ou
# quatro, o genético não saiu dos planos gulosos em duas de três campanhas de
# teste; com um, os superou em até 13% (`docs/medicoes/otimizador.md`).
MUTACOES_POR_FILHO = 1


@dataclass(frozen=True)
class Resultado:
    genes: tuple[int, ...]
    avaliacao: Avaliacao
    partidas: int  # quantas começaram
    geracoes: int  # quantas gerações rodaram, somando as partidas
    parcial: bool  # o limite de tempo interrompeu a busca (UC08, E2)
    segundos: float
    threads: int = 1  # as que calcularam os filhos: mais de uma só no modo OpenMP


def _torneio(avaliacoes: list[Avaliacao], h1: int, h2: int) -> int:
    """O vencedor entre dois sorteados; no empate, o primeiro sorteado."""
    p = len(avaliacoes)
    r1, r2 = h1 % p, h2 % p
    return r2 if melhor(avaliacoes[r2], avaliacoes[r1]) else r1


def _indice_do_melhor(avaliacoes: list[Avaliacao]) -> int:
    """O melhor da população; no empate, o de menor índice."""
    escolhido = 0
    for j in range(1, len(avaliacoes)):
        if melhor(avaliacoes[j], avaliacoes[escolhido]):
            escolhido = j
    return escolhido


def _sorteado(inst: Instancia, base: int, densidade: int) -> list[int]:
    """Um indivíduo da geração 0: cada parceiro recebe ação com chance densidade/N."""
    n, a = inst.parceiros, inst.acoes
    genes = [0] * n
    for i in range(n):
        h = encadear(base, i)
        if h % n < densidade:
            genes[i] = 1 + (h >> 32) % a
    return genes


def _filho(pai: list[int], mae: list[int], base: int, taxa_ppm: int, valores: int) -> list[int]:
    """Cruzamento uniforme e mutação, gene a gene, com um sorteio por gene.

    Os bits do sorteio se dividem: o mais baixo escolhe o pai, os seguintes
    decidem se há mutação, e os do meio dão o valor novo.
    """
    filho = [0] * len(pai)
    for i in range(len(pai)):
        h = encadear(base, i)
        gene = mae[i] if h & 1 else pai[i]
        if (h >> 1) % MILHAO < taxa_ppm:
            gene = (h >> 21) % valores
        filho[i] = gene
    return filho


def otimizar(
    inst: Instancia,
    *,
    semente: int = 42,
    partidas: int = PARTIDAS,
    populacao: int = POPULACAO,
    geracoes: int = GERACOES,
    mutacoes_por_filho: int = MUTACOES_POR_FILHO,
    limite_s: float | None = None,
    relogio: Callable[[], float] = time.perf_counter,
) -> Resultado:
    """O melhor plano encontrado; levanta `Inviavel` quando as cotas não cabem (RN07).

    Com `limite_s`, a busca para ao estourar o tempo e devolve o melhor viável
    até ali, marcado como parcial (UC08, E2). Sem limite, o resultado depende
    só da instância e dos parâmetros: a mesma semente dá o mesmo plano.
    """
    if populacao < 2 or partidas < 1 or geracoes < 0:
        raise ValueError("A busca precisa de ao menos 2 indivíduos, 1 partida e 0 gerações.")

    inicio = relogio()
    iniciais = [guloso(inst, RAZAO), guloso(inst, GANHO)]  # levantam Inviavel antes da busca
    n = inst.parceiros
    if n == 0:
        return Resultado((), avaliar(inst, ()), 0, 0, False, relogio() - inicio)

    taxa_ppm = max(1, mutacoes_por_filho * MILHAO // n)
    # Quantas ações um indivíduo sorteado recebe, em média: o que o orçamento
    # paga ao custo médio do catálogo, sem passar de K. Sortear mais nasceria
    # quase tudo estourando o orçamento; menos, quase tudo vazio.
    densidade = min(inst.maximo_acoes, inst.orcamento * inst.acoes // sum(inst.custo))
    valores = inst.acoes + 1

    avaliacoes_iniciais = [avaliar(inst, g) for g in iniciais]
    primeiro = _indice_do_melhor(avaliacoes_iniciais)
    vencedor, avaliacao_vencedor = iniciais[primeiro], avaliacoes_iniciais[primeiro]
    rodadas = 0
    parcial = False
    iniciadas = 0

    for p in range(partidas):
        iniciadas += 1
        pop = [list(g) for g in iniciais][:populacao] + [
            _sorteado(inst, sorteio(semente, p, 0, j), densidade)
            for j in range(len(iniciais), populacao)
        ]
        avaliacoes = [avaliar(inst, g) for g in pop]

        for g in range(1, geracoes + 1):
            if limite_s is not None and relogio() - inicio > limite_s:
                parcial = True
                break
            elite = _indice_do_melhor(avaliacoes)
            nova, novas_avaliacoes = [pop[elite]], [avaliacoes[elite]]
            for j in range(1, populacao):
                base = sorteio(semente, p, g, j)
                pai = _torneio(avaliacoes, encadear(base, n), encadear(base, n + 1))
                mae = _torneio(avaliacoes, encadear(base, n + 2), encadear(base, n + 3))
                filho = _filho(pop[pai], pop[mae], base, taxa_ppm, valores)
                nova.append(filho)
                novas_avaliacoes.append(avaliar(inst, filho))
            pop, avaliacoes = nova, novas_avaliacoes
            rodadas += 1

        melhor_da_partida = _indice_do_melhor(avaliacoes)
        if melhor(avaliacoes[melhor_da_partida], avaliacao_vencedor):
            vencedor, avaliacao_vencedor = pop[melhor_da_partida], avaliacoes[melhor_da_partida]
        if parcial:
            break

    # As soluções gulosas são viáveis e o elitismo nunca perde a melhor delas:
    # chegar aqui com um vencedor inviável seria defeito do algoritmo, e não da
    # campanha.
    if not avaliacao_vencedor.viavel:
        raise AssertionError("O genético terminou com um plano inviável.")
    return Resultado(
        tuple(vencedor), avaliacao_vencedor, iniciadas, rodadas, parcial, relogio() - inicio
    )
