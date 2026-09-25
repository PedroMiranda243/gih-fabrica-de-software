"""A rede — histórias H42 e H43.

Uma rede só, com duas saídas: o faturamento do próximo período e o risco de
entrar em Em Risco nele. As duas perguntas olham o mesmo movimento — quem vem
caindo, com que força, de que tamanho é — e dividir o corpo deixa uma saída
aproveitar o que a outra aprendeu.

**Pequena de propósito.** Com 500 parceiros e 12 semanas há alguns milhares de
amostras; uma rede grande decoraria o treino e erraria o teste. Duas camadas de
32 são poucos milhares de parâmetros — cabem numa linha do banco (ADR-010).
"""
from __future__ import annotations

import torch
from torch import nn

OCULTAS = 32


class RedePrevisao(nn.Module):
    def __init__(self, entradas: int, ocultas: int = OCULTAS) -> None:
        super().__init__()
        self.corpo = nn.Sequential(
            nn.Linear(entradas, ocultas),
            nn.ReLU(),
            nn.Linear(ocultas, ocultas),
            nn.ReLU(),
        )
        # O faturamento sai como a variação em relação ao último período,
        # normalizada; o risco sai em logito, antes da sigmoide.
        self.faturamento = nn.Linear(ocultas, 1)
        self.risco = nn.Linear(ocultas, 1)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        h = self.corpo(x)
        return self.faturamento(h).squeeze(-1), self.risco(h).squeeze(-1)
