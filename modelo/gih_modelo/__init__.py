"""Modelo preditivo do GIH: faturamento do próximo período e risco de queda.

Prevê; não decide. Recebe séries numéricas e devolve números — não conhece
banco, FastAPI nem regra de negócio (`CLAUDE.md` §3, ADR-010). Quem decide se
uma versão entra em uso, e o que conta como queda, é a API.
"""
from gih_modelo.baselines import BASELINES, ReferenciaRisco
from gih_modelo.treino import (
    HistoricoInsuficiente,
    Metricas,
    Previsao,
    Resultado,
    Volume,
    prever,
    prever_referencia,
    treinar,
)
from gih_modelo.variaveis import JANELA, PERIODOS_MINIMOS, Serie, colunas

__all__ = [
    "BASELINES",
    "JANELA",
    "PERIODOS_MINIMOS",
    "HistoricoInsuficiente",
    "Metricas",
    "Previsao",
    "ReferenciaRisco",
    "Resultado",
    "Serie",
    "Volume",
    "colunas",
    "prever",
    "prever_referencia",
    "treinar",
]
