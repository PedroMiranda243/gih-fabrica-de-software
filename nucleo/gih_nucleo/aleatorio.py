"""Gerador aleatório sem estado, igual em Python, C++ e CUDA (ADR-011).

Cada sorteio é o SplitMix64 aplicado em cadeia às coordenadas do sorteio —
semente, partida, geração, indivíduo e posição —, e não o próximo número de uma
sequência. Duas consequências, e as duas são o motivo da escolha:

- **O mesmo sorteio em qualquer versão.** O Python, o C++ e o kernel CUDA fazem
  as mesmas operações de 64 bits sem sinal e chegam ao mesmo número. É o que
  deixa as três versões do otimizador no mesmo plano (H53a, RNF02).
- **Nada a compartilhar entre threads.** Uma sequência com estado obrigaria as
  threads a se revezarem nela, ou a cada uma ter a sua — e aí a ordem de
  execução mudaria os números. Aqui cada thread calcula o sorteio que é dela.

As constantes são as do SplitMix64 publicado por Steele, Lea e Flood (2014).
Os valores de referência em `tests/test_aleatorio.py` fixam a sequência: o C++
e o CUDA precisam reproduzi-los antes de qualquer outra coisa.
"""
from __future__ import annotations

MASCARA = (1 << 64) - 1

# Probabilidades são inteiras, em partes por milhão: comparar `float` daria
# resultados diferentes conforme a linguagem arredonda.
MILHAO = 1_000_000


def mistura(z: int) -> int:
    """Um passo do SplitMix64 sobre `z`, em 64 bits sem sinal."""
    z = (z + 0x9E3779B97F4A7C15) & MASCARA
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASCARA
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASCARA
    return z ^ (z >> 31)


def encadear(base: int, chave: int) -> int:
    """Acrescenta uma coordenada ao sorteio: `mistura(base XOR chave)`."""
    return mistura(base ^ (chave & MASCARA))


def sorteio(*coordenadas: int) -> int:
    """O número de 64 bits das coordenadas, na ordem dada.

    `sorteio(s, p, g, j, i)` é igual a encadear, a partir de zero, `s`, `p`,
    `g`, `j` e `i`. O laço do genético calcula o prefixo uma vez por indivíduo
    e encadeia só a posição — o resultado é o mesmo, e custa um passo por gene
    em vez de cinco.
    """
    h = 0
    for c in coordenadas:
        h = encadear(h, c)
    return h
