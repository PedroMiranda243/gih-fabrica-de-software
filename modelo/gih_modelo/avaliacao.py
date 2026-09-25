"""As métricas de avaliação — H42 (faturamento) e H43 (risco).

- **MAPE** para o faturamento: o erro médio em porcentagem do valor real. É a
  métrica da `docs/07` §4.4, e é a que o gestor entende — "erra 8% em média".
- **Brier** para o risco: o erro quadrático médio entre a probabilidade dada e
  o que aconteceu (0 ou 1). Premia estar certo **e** saber o quanto: dizer 90%
  para o que acontece metade das vezes custa caro.
- **Erro de calibração** para o risco: nos parceiros a quem o modelo deu ~30%,
  ~30% entraram em risco? É a média, ponderada pelo tamanho de cada faixa, da
  distância entre o previsto e o observado. Probabilidade descalibrada engana o
  otimizador, que multiplica por ela.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

FAIXAS = 10


def mape(previsto: np.ndarray, real: np.ndarray) -> float:
    """Erro percentual absoluto médio, em fração (0,08 = 8%).

    Alvos com faturamento zero ficam de fora: o erro percentual sobre zero não
    existe, e um único zero dominaria a média.
    """
    validos = real > 0
    if not validos.any():
        return float("nan")
    return float(np.mean(np.abs(previsto[validos] - real[validos]) / real[validos]))


def brier(probabilidade: np.ndarray, rotulo: np.ndarray) -> float:
    return float(np.mean((probabilidade - rotulo) ** 2)) if len(rotulo) else float("nan")


@dataclass(frozen=True)
class Faixa:
    inicio: float
    fim: float
    previsto: float  # probabilidade média dada às amostras da faixa
    observado: float  # fração delas que entrou em risco
    amostras: int


def curva_calibracao(probabilidade: np.ndarray, rotulo: np.ndarray) -> list[Faixa]:
    """As faixas de probabilidade com pelo menos uma amostra."""
    faixa = np.minimum((probabilidade * FAIXAS).astype(int), FAIXAS - 1)
    curva = []
    for f in range(FAIXAS):
        dentro = faixa == f
        if dentro.any():
            curva.append(
                Faixa(
                    inicio=f / FAIXAS,
                    fim=(f + 1) / FAIXAS,
                    previsto=float(probabilidade[dentro].mean()),
                    observado=float(rotulo[dentro].mean()),
                    amostras=int(dentro.sum()),
                )
            )
    return curva


def erro_calibracao(probabilidade: np.ndarray, rotulo: np.ndarray) -> float:
    total = len(rotulo)
    if not total:
        return float("nan")
    return sum(
        f.amostras / total * abs(f.previsto - f.observado)
        for f in curva_calibracao(probabilidade, rotulo)
    )
