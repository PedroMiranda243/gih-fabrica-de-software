"""Modelo preditivo do GIH: faturamento do próximo período e risco de queda.

Prevê; não decide. Recebe séries numéricas e devolve números — não conhece
banco, FastAPI nem regra de negócio (`CLAUDE.md` §3, ADR-010). Quem decide se
uma versão entra em uso, e o que conta como queda, é a API.

**O PyTorch só é importado quando se treina ou prevê.** A API importa este
pacote para ler `JANELA` e `PERIODOS_MINIMOS` a cada subida; carregar o PyTorch
ali custaria segundos de subida e algumas centenas de MB de memória a um
processo que, na maior parte do tempo, só serve telas.
"""
from gih_modelo.baselines import BASELINES, ReferenciaRisco
from gih_modelo.variaveis import JANELA, PERIODOS_MINIMOS, Serie, colunas

_DO_TREINO = {
    "HistoricoInsuficiente",
    "Metricas",
    "Previsao",
    "Resultado",
    "Volume",
    "prever",
    "prever_referencia",
    "treinar",
}


def __getattr__(nome: str):
    if nome in _DO_TREINO:
        from gih_modelo import treino

        return getattr(treino, nome)
    raise AttributeError(f"module 'gih_modelo' has no attribute {nome!r}")


__all__ = [
    "BASELINES",
    "JANELA",
    "PERIODOS_MINIMOS",
    "ReferenciaRisco",
    "Serie",
    "colunas",
    *sorted(_DO_TREINO),
]
