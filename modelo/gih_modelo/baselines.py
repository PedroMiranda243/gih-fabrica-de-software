"""As referências que o modelo precisa superar — história H46.

Uma rede que não bate uma conta de cabeça não agrega nada, e só dá para saber
se ela bate comparando no mesmo conjunto de teste. São três referências, todas
triviais de propósito: é contra o trivial que o aprendizado precisa se provar.

- **Repetir o último período** — "semana que vem será como esta".
- **Média móvel dos últimos 4** — alisa o ruído, mas chega atrasada quando há
  tendência.
- **Risco pela taxa observada** — a fração de amostras de treino que terminou
  em risco, separada por "caiu no último período". É o que um analista diria
  olhando o histórico: quem acabou de cair tem mais chance de cair de novo.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from gih_modelo.variaveis import Amostras

BASELINES = ("ultimo", "media_movel")


def prever_faturamento(amostras: Amostras, baseline: str) -> np.ndarray:
    """O faturamento previsto pela referência, em reais."""
    if baseline == "ultimo":
        return amostras.ultimo
    if baseline == "media_movel":
        return amostras.media_movel
    raise ValueError(f"Referência desconhecida: {baseline}")


@dataclass(frozen=True)
class ReferenciaRisco:
    se_caiu: float
    se_nao_caiu: float

    @classmethod
    def ajustar(cls, treino: Amostras) -> ReferenciaRisco:
        """As duas taxas, medidas no treino.

        Grupo vazio cai na taxa geral: sem nenhuma amostra que caiu, não há
        como medir a taxa de quem caiu, e zero seria uma certeza inventada.
        """
        geral = float(treino.em_risco.mean()) if len(treino) else 0.0

        def taxa(grupo: np.ndarray) -> float:
            return float(treino.em_risco[grupo].mean()) if grupo.any() else geral

        return cls(se_caiu=taxa(treino.caiu), se_nao_caiu=taxa(~treino.caiu))

    def prever(self, amostras: Amostras) -> np.ndarray:
        return np.where(amostras.caiu, self.se_caiu, self.se_nao_caiu)
