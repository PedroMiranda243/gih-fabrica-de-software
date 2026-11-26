"""Os cabeçalhos dos CSVs exportados escrevem como a tela (#296).

O CSV de parceiros saía com "Situacao", "Ticket medio" e "Variacao %", e o das
mensagens aprovadas com "Acao", enquanto os dos relatórios e a tela diziam
"Situação", "Ticket médio", "Variação %" e "Ação". O arquivo leva o BOM, e a
planilha abre o acento certo: não havia por que tirá-lo. Este teste lê os
cabeçalhos de todas as exportações e reprova a palavra sem o acento dela.
"""
from __future__ import annotations

import re

import pytest

from app.rotas import campanha, mensagens, parceiros, relatorios

CABECALHOS = {
    "parceiros": parceiros.CABECALHO_CSV,
    "mensagens aprovadas": mensagens.CABECALHO_CSV,
    "plano de campanha": campanha.CABECALHO_DO_PLANO,
    "relatório de desempenho": relatorios.CABECALHO_DESEMPENHO,
    "relatório de risco": relatorios.CABECALHO_RISCO,
    "relatório da campanha": relatorios.CABECALHO_CAMPANHA,
    "relatório de operações": relatorios.CABECALHO_OPERACOES,
}

# A palavra sem acento, e como a tela a escreve.
SEM_ACENTO = {
    "acao": "Ação",
    "situacao": "Situação",
    "medio": "médio",
    "variacao": "Variação",
    "operacoes": "Operações",
    "periodo": "Período",
    "usuario": "Usuário",
    "previsao": "Previsão",
}


@pytest.mark.parametrize("nome", CABECALHOS)
def test_o_cabecalho_escreve_com_acento(nome):
    erradas = [
        f"{coluna!r} (a tela diz {SEM_ACENTO[palavra.lower()]!r})"
        for coluna in CABECALHOS[nome]
        for palavra in re.findall(r"\w+", coluna)
        if palavra.lower() in SEM_ACENTO
    ]
    assert erradas == [], f"o CSV de {nome} tem coluna sem acento: {erradas}"


def test_o_csv_de_parceiros_diz_situacao_ticket_medio_e_variacao():
    assert {"Situação", "Ticket médio", "Variação %"} <= set(parceiros.CABECALHO_CSV)
    assert "Ação" in mensagens.CABECALHO_CSV
