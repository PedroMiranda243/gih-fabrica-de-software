"""O núcleo de otimização do GIH: o plano de campanha de maior ganho (H48, H49, H52).

Otimiza; não decide. Recebe da API uma `Instancia` já em números inteiros —
ganho por parceiro e ação em centavos, custos, orçamento e cotas em contagem —
e devolve o plano. Não conhece banco, FastAPI nem regra de negócio
(`CLAUDE.md` §3): quem diz o que é ganho (RN10), quem é elegível e o que é
cauda longa (RN11) é a API.

Esta é a versão serial em Python, a referência de corretude e o denominador do
*speedup* (RNF02). As versões em C++ com OpenMP e em CUDA (Sprints 10 e 11)
seguem o mesmo algoritmo, sorteio a sorteio (ADR-011).
"""
from gih_nucleo.guloso import guloso
from gih_nucleo.problema import (
    SEM_CATEGORIA,
    Avaliacao,
    Instancia,
    InstanciaInvalida,
    avaliar,
    verificar_plano,
)
from gih_nucleo.serial import Resultado, otimizar
from gih_nucleo.viabilidade import Inviabilidade, Inviavel, verificar_viabilidade

__all__ = [
    "SEM_CATEGORIA",
    "Avaliacao",
    "Instancia",
    "InstanciaInvalida",
    "Inviabilidade",
    "Inviavel",
    "Resultado",
    "avaliar",
    "guloso",
    "otimizar",
    "verificar_plano",
    "verificar_viabilidade",
]
