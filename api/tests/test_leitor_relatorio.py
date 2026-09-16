"""Testes do interpretador do relatório, isolados da API e do banco.

A tolerância do formato é a decisão da ADR-009, e é justamente o que precisa de
teste: cada variação aqui corresponde a uma forma real de o relatório chegar —
colado de planilha, exportado em CSV, com cifrão, com coluna fora de ordem.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.leitor_relatorio import (
    FormatoNaoReconhecido,
    interpretar,
    ler_decimal,
    ler_inteiro,
)


def um_reconhecido(texto: str):
    leitura = interpretar(texto)
    assert len(leitura.reconhecidos) == 1, leitura.rejeitados
    return leitura.reconhecidos[0]


# --------------------------------------------------------------- separadores
def test_aceita_ponto_e_virgula():
    linha = um_reconhecido("Parceiro;Faturamento;Pedidos\nComércio Alfa;1000,00;10\n")
    assert linha.nome == "Comércio Alfa"
    assert linha.faturamento == Decimal("1000.00")


def test_aceita_tabulacao_que_e_o_que_sai_ao_colar_de_planilha():
    linha = um_reconhecido("Parceiro\tFaturamento\tPedidos\nComércio Alfa\t1000,00\t10\n")
    assert linha.pedidos == 10


def test_aceita_virgula_quando_nao_ha_outro_separador():
    linha = um_reconhecido("Parceiro,Faturamento,Pedidos\nComércio Alfa,1000.00,10\n")
    assert linha.faturamento == Decimal("1000.00")


def test_ponto_e_virgula_vence_a_virgula():
    """Com os dois presentes, a vírgula é decimal, não separador de coluna.

    É por isso que a vírgula é o último separador testado: em `1.000,50` ela
    partiria o número ao meio.
    """
    linha = um_reconhecido("Parceiro;Faturamento;Pedidos\nComércio Alfa;1.000,50;10\n")
    assert linha.faturamento == Decimal("1000.50")


# ------------------------------------------------------------------- colunas
def test_a_ordem_das_colunas_nao_importa():
    linha = um_reconhecido("Pedidos;Parceiro;Faturamento\n10;Comércio Alfa;1000,00\n")
    assert linha.nome == "Comércio Alfa"
    assert linha.pedidos == 10


def test_aceita_sinonimos_de_cabecalho():
    linha = um_reconhecido("Estabelecimento;Vendas;Quantidade\nComércio Alfa;1000,00;10\n")
    assert linha.nome == "Comércio Alfa"


def test_cabecalho_com_acento_e_caixa_diferente():
    linha = um_reconhecido("PARCEIRO;FATURAMENTO;PEDIDOS\nComércio Alfa;1000,00;10\n")
    assert linha.pedidos == 10


def test_colunas_extras_sao_ignoradas():
    """Exportação real vem cheia de coluna que não interessa."""
    texto = "Parceiro;Cidade;Faturamento;Pedidos;Observação\nComércio Alfa;Recife;1000,00;10;ok\n"
    assert um_reconhecido(texto).faturamento == Decimal("1000.00")


def test_cabecalho_sem_as_colunas_necessarias():
    with pytest.raises(FormatoNaoReconhecido, match="colunas necessárias"):
        interpretar("Parceiro;Cidade\nComércio Alfa;Recife\n")


# ------------------------------------------------------------------- números
@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        ("12.500,40", "12500.40"),
        ("12500,40", "12500.40"),
        ("12500.40", "12500.40"),
        ("R$ 12.500,40", "12500.40"),
        ("1.234.567,89", "1234567.89"),
        ("0,00", "0.00"),
        ("1,234.56", "1234.56"),  # formato em inglês
    ],
)
def test_le_valor_monetario(bruto, esperado):
    assert ler_decimal(bruto) == Decimal(esperado)


@pytest.mark.parametrize("bruto", ["312", " 312 ", "1.312", "312 pedidos"])
def test_le_quantidade(bruto):
    assert ler_inteiro(bruto) > 0


# ------------------------------------------------------------------ rejeições
def test_linha_ruim_nao_interrompe_a_leitura():
    """Uma célula errada não pode esconder as outras noventa e nove (UC03, A5)."""
    texto = (
        "Parceiro;Faturamento;Pedidos\n"
        "Comércio Alfa;1000,00;10\n"
        "Comércio Beta;abacaxi;20\n"
        "Comércio Gama;3000,00;30\n"
    )
    leitura = interpretar(texto)

    assert len(leitura.reconhecidos) == 2
    assert len(leitura.rejeitados) == 1
    assert leitura.rejeitados[0].linha == 3


def test_valor_negativo_e_rejeitado():
    texto = "Parceiro;Faturamento;Pedidos\nComércio Alfa;-100,00;10\n"
    leitura = interpretar(texto)

    assert not leitura.reconhecidos
    assert "negativos" in leitura.rejeitados[0].motivo


def test_parceiro_repetido_aponta_a_primeira_ocorrencia():
    """Gravar as duas violaria a unicidade (parceiro, período) e perderia uma
    delas em silêncio."""
    texto = (
        "Parceiro;Faturamento;Pedidos\n"
        "Comércio Alfa;1000,00;10\n"
        "comercio alfa;2000,00;20\n"
    )
    leitura = interpretar(texto)

    assert len(leitura.reconhecidos) == 1
    assert "linha 2" in leitura.rejeitados[0].motivo


def test_numero_da_linha_conta_as_linhas_em_branco():
    """O usuário procura no texto que colou, onde a linha em branco ocupa espaço."""
    texto = "Parceiro;Faturamento;Pedidos\n\nComércio Alfa;abacaxi;10\n"
    leitura = interpretar(texto)

    assert leitura.rejeitados[0].linha == 3


def test_texto_vazio():
    with pytest.raises(FormatoNaoReconhecido, match="vazio"):
        interpretar("   \n\n")


def test_cabecalho_sozinho_sem_dados():
    with pytest.raises(FormatoNaoReconhecido, match="nenhuma linha de dados"):
        interpretar("Parceiro;Faturamento;Pedidos\n")


def test_quebra_de_linha_do_windows():
    """Colar do Bloco de Notas traz CR LF; dividir só por LF deixaria um CR
    grudado no último campo e o número viraria texto."""
    leitura = interpretar("Parceiro;Faturamento;Pedidos\r\nComércio Alfa;1000,00;10\r\n")

    assert leitura.reconhecidos[0].pedidos == 10
