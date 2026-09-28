"""A guarda numérica (RN08, RF43, ADR-013): todo número do texto precisa vir dos fatos.

Os fatos daqui têm a forma que o código vai entregar ao modelo: valores já
formatados em português, como a tela os mostraria.
"""

import datetime as dt
from decimal import Decimal

import pytest

from app.guarda_numerica import Tipo, numeros, numeros_sem_origem, permitidos, sentido_trocado

FATOS = {
    "parceiro": "Mercearia Boa Vista",
    "segmento": "Em Risco",
    "categoria": "Mercado",
    "periodo": "08/2026",
    "faturamento": "R$ 12.345,67",
    "variacao": "-12,8%",
    "pedidos": "412",
    "posicao": 3,
    "acao": "Cupom de reativação",
}


# ------------------------------------------------------------------ a leitura
@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("412 pedidos", [("412", Tipo.NUMERO, Decimal(412))]),
        ("1.234 clientes", [("1.234", Tipo.NUMERO, Decimal(1234))]),
        ("R$ 12.345,67", [("R$ 12.345,67", Tipo.NUMERO, Decimal("12345.67"))]),
        ("R$12.345,67", [("R$12.345,67", Tipo.NUMERO, Decimal("12345.67"))]),
        ("R$ 12 mil", [("R$ 12 mil", Tipo.NUMERO, Decimal(12000))]),
        ("3 milhões", [("3 milhões", Tipo.NUMERO, Decimal(3_000_000))]),
        ("12,8%", [("12,8%", Tipo.PERCENTUAL, Decimal("12.8"))]),
        ("-12,8 %", [("-12,8 %", Tipo.PERCENTUAL, Decimal("12.8"))]),
        ("−12,8%", [("−12,8%", Tipo.PERCENTUAL, Decimal("12.8"))]),
        ("12,8 por cento", [("12,8 por cento", Tipo.PERCENTUAL, Decimal("12.8"))]),
        ("3 pontos percentuais", [("3 pontos percentuais", Tipo.PERCENTUAL, Decimal(3))]),
        ("12.8", [("12.8", Tipo.NUMERO, Decimal("12.8"))]),
        ("3º lugar", [("3º", Tipo.NUMERO, Decimal(3))]),
        ("08/2026", [("08/2026", Tipo.DATA, (None, 8, 2026))]),
        ("15/08/2026", [("15/08/2026", Tipo.DATA, (15, 8, 2026))]),
        ("15/08", [("15/08", Tipo.DATA, (15, 8, None))]),
        ("40/50", [("40", Tipo.NUMERO, Decimal(40)), ("50", Tipo.NUMERO, Decimal(50))]),
        ("2026-08-01", [("2026-08-01", Tipo.DATA, (1, 8, 2026))]),
        ("agosto de 2026", [("agosto de 2026", Tipo.DATA, (None, 8, 2026))]),
        ("Março/2026", [("Março/2026", Tipo.DATA, (None, 3, 2026))]),
        ("em agosto", [("agosto", Tipo.DATA, (None, 8, None))]),
        ("14 de setembro", [("14 de setembro", Tipo.DATA, (14, 9, None))]),
        ("14 de setembro de 2026", [("14 de setembro de 2026", Tipo.DATA, (14, 9, 2026))]),
        ("1º de outubro", [("1º de outubro", Tipo.DATA, (1, 10, None))]),
        (
            "de 14 a 20 de setembro",
            [
                ("14 a 20 de setembro", Tipo.DATA, (14, 9, None)),
                ("14 a 20 de setembro", Tipo.DATA, (20, 9, None)),
            ],
        ),
        ("três ações", [("três", Tipo.NUMERO, Decimal(3))]),
        ("tres ações", [("tres", Tipo.NUMERO, Decimal(3))]),
        ("vinte e cinco", [("vinte e cinco", Tipo.NUMERO, Decimal(25))]),
        ("cento e vinte e três", [("cento e vinte e três", Tipo.NUMERO, Decimal(123))]),
        (
            "dois mil trezentos e quarenta",
            [("dois mil trezentos e quarenta", Tipo.NUMERO, Decimal(2340))],
        ),
        ("doze mil e quinhentos", [("doze mil e quinhentos", Tipo.NUMERO, Decimal(12500))]),
        (
            "dois milhões e trezentos mil",
            [("dois milhões e trezentos mil", Tipo.NUMERO, Decimal(2_300_000))],
        ),
        ("vinte e cinco por cento", [("vinte e cinco por cento", Tipo.PERCENTUAL, Decimal(25))]),
        ("cem por cento", [("cem por cento", Tipo.PERCENTUAL, Decimal(100))]),
        ("vinte e um", [("vinte e um", Tipo.NUMERO, Decimal(21))]),
        ("terceiro lugar", [("terceiro", Tipo.NUMERO, Decimal(3))]),
        ("o dobro", [("dobro", Tipo.COMPARACAO, None)]),
        ("a metade", [("metade", Tipo.COMPARACAO, None)]),
    ],
)
def test_le_cada_forma_de_escrever_um_numero(texto, esperado):
    assert [(n.trecho, n.tipo, n.valor) for n in numeros(texto)] == esperado


@pytest.mark.parametrize(
    "texto",
    [
        "uma campanha e um cupom",  # artigos, e não quantidade
        "segundo o relatório",  # "de acordo com"
        "primeiro, obrigado",  # "antes de tudo"
        "até sexta, ou na quarta-feira",  # dias da semana
        "o marco da campanha",  # "marco" sem cedilha não é março
        "o modelo qwen2.5",  # algarismo colado numa palavra
        "Mercearia Boa Vista, Em Risco",
    ],
)
def test_nao_ve_numero_onde_nao_ha(texto):
    assert numeros(texto) == []


def test_cinco_e_seis_sao_dois_numeros():
    """O "e" só junta quando a parte seguinte é menor: "cinco e seis" não é onze."""
    assert [n.valor for n in numeros("entre cinco e seis semanas")] == [Decimal(5), Decimal(6)]


def test_a_pontuacao_da_frase_nao_entra_no_numero():
    trechos = [n.trecho for n in numeros("Foram 412. Depois, 3, e enfim 12,8%.")]
    assert trechos == ["412", "3", "12,8%"]


def test_os_numeros_saem_na_ordem_do_texto():
    texto = "Em agosto de 2026, 412 pedidos e vinte clientes, com 12,8% a menos."
    assert [n.trecho for n in numeros(texto)] == ["agosto de 2026", "412", "vinte", "12,8%"]


# ------------------------------------------------------------------- os fatos
def test_os_fatos_viram_numeros_percentuais_e_datas():
    p = permitidos(FATOS)
    assert p.numeros == {Decimal("12345.67"), Decimal(412), Decimal(3)}
    assert p.percentuais == {Decimal("12.8")}
    assert p.datas == [(None, 8, 2026)]


def test_os_fatos_podem_vir_aninhados_e_em_tipos_do_python():
    fatos = {
        "itens": [{"ganho": Decimal("1500.00")}, {"ganho": 250}],
        "gerado_em": dt.date(2026, 8, 31),
        "ativo": True,  # bool não é número
        "nada": None,
    }
    p = permitidos(fatos)
    assert p.numeros == {Decimal(1500), Decimal(250)}
    assert p.datas == [(31, 8, 2026)]


# ------------------------------------------------------------------ a guarda
def test_texto_so_com_numeros_dos_fatos_passa():
    texto = (
        "Em agosto de 2026, a Mercearia Boa Vista faturou R$ 12.345,67 em 412 pedidos, "
        "uma variação de -12,8% — por isso preparamos um cupom de reativação."
    )
    assert numeros_sem_origem(texto, FATOS) == []


@pytest.mark.parametrize(
    "texto",
    [
        "Vocês ficaram em terceiro lugar em 08/2026.",
        "Foram quatrocentos e doze pedidos.",
        "O faturamento caiu 12,8%.",  # o sinal não conta: "caiu" diz o menos
        "Em 2026, com 3 ações.",  # o ano de uma data dos fatos pode vir sozinho
        "Tudo isso em agosto.",
    ],
)
def test_o_mesmo_numero_escrito_de_outro_jeito_passa(texto):
    assert numeros_sem_origem(texto, FATOS) == []


@pytest.mark.parametrize(
    ("texto", "sem_origem"),
    [
        ("O faturamento caiu 13%.", ["13%"]),  # arredondado
        ("Foram R$ 12,3 mil em agosto.", ["R$ 12,3 mil"]),  # abreviado
        ("Em julho de 2026, 412 pedidos.", ["julho de 2026"]),  # outro mês
        ("Em julho, 412 pedidos.", ["julho"]),
        ("Em 15/08/2026, 412 pedidos.", ["15/08/2026"]),  # mais preciso que o fato
        ("Em 2025, 412 pedidos.", ["2025"]),
        ("Vendeu o dobro de julho.", ["dobro", "julho"]),  # comparar é conta
        ("Mais 5 clientes novos.", ["5"]),
        ("Cerca de quinhentos pedidos.", ["quinhentos"]),
        ("A variação foi de 12,8.", ["12,8"]),  # percentual dos fatos não vira número solto
        ("Faltaram 412%.", ["412%"]),  # nem número vira percentual
        ("Entrega em 24 horas.", ["24"]),
    ],
)
def test_numero_que_nao_veio_dos_fatos_e_apontado(texto, sem_origem):
    assert numeros_sem_origem(texto, FATOS) == sem_origem


def test_numero_do_nome_do_parceiro_esta_nos_fatos():
    fatos = {"parceiro": "Mercadinho 24 Horas", "pedidos": "412"}
    assert numeros_sem_origem("O Mercadinho 24 Horas fez 412 pedidos.", fatos) == []


PERIODO_POR_DIA = [{"fato": "Período", "valor": "14/09/2026 a 20/09/2026"}]


@pytest.mark.parametrize(
    "texto",
    [
        "Na semana de 14 a 20 de setembro.",
        "Entre 14 e 20 de setembro de 2026.",
        "Desde 14 de setembro.",
        "No período de 14/09/2026 a 20/09/2026.",
        "De 14/09 a 20/09.",
        "De 14 a 20/09.",
        "Entre 14 e 20/09/2026.",
        "Em setembro de 2026.",
    ],
)
def test_o_periodo_por_dia_escrito_de_outro_jeito_passa(texto):
    assert numeros_sem_origem(texto, PERIODO_POR_DIA) == []


@pytest.mark.parametrize(
    ("texto", "sem_origem"),
    [
        ("Desde 15 de setembro.", ["15 de setembro"]),
        ("De 14 a 21 de setembro.", ["14 a 21 de setembro"]),
        ("Em 14 de outubro.", ["14 de outubro"]),
        ("De 14/09 a 21/09.", ["21/09"]),
        ("De 14 a 21/09.", ["14 a 21/09"]),
    ],
)
def test_outro_dia_nao_passa(texto, sem_origem):
    assert numeros_sem_origem(texto, PERIODO_POR_DIA) == sem_origem


def test_sem_fatos_nenhum_numero_passa():
    assert numeros_sem_origem("São 3 pedidos.", {}) == ["3"]
    assert numeros_sem_origem("Obrigado pela parceria.", {}) == []


# ------------------------------------------------------------------ o sentido
VARIACOES = [
    {"fato": "Variação do faturamento", "valor": "+12,50%"},
    {"fato": "Variação dos pedidos", "valor": "-7,69%"},
    {"fato": "Probabilidade de entrar em risco", "valor": "13%"},
]


@pytest.mark.parametrize(
    "texto",
    [
        "O faturamento cresceu 12,50%, e os pedidos caíram 7,69%.",
        "Uma alta de 12,50% no faturamento.",
        "Os pedidos tiveram 7,69% de queda.",
        "A variação foi de +12,50%.",
        "Os pedidos variaram -7,69%.",
        "Os pedidos caíram -7,69%.",
        "O faturamento variou 12,50%.",
        "A chance de queda é de 13%.",
    ],
)
def test_a_variacao_no_sentido_certo_passa(texto):
    assert sentido_trocado(texto, VARIACOES) == []


@pytest.mark.parametrize(
    ("texto", "trocados"),
    [
        ("O faturamento caiu 12,50%.", ["12,50%"]),
        ("Uma queda de 12,50% no faturamento.", ["12,50%"]),
        ("O faturamento teve 12,50% de queda.", ["12,50%"]),
        ("A variação foi de -12,50%.", ["-12,50%"]),
        ("Os pedidos cresceram 7,69%.", ["7,69%"]),
        ("O faturamento caiu 12,50% e os pedidos subiram 7,69%.", ["12,50%", "7,69%"]),
    ],
)
def test_a_variacao_no_sentido_contrario_e_apontada(texto, trocados):
    """O valor certo com a notícia invertida: a guarda do valor não pega, esta pega."""
    assert numeros_sem_origem(texto, VARIACOES) == []
    assert sentido_trocado(texto, VARIACOES) == trocados


def test_o_valor_com_os_dois_sinais_nos_fatos_nao_reprova():
    fatos = ["+5,00%", "-5,00%"]
    assert sentido_trocado("Caiu 5,00%.", fatos) == []
    assert sentido_trocado("Subiu 5,00%.", fatos) == []


def test_cada_numero_sabe_onde_esta_no_texto():
    texto = "Em 14/09/2026, caiu 12,50%."
    assert [(n.trecho, texto[n.inicio : n.inicio + len(n.trecho)]) for n in numeros(texto)] == [
        ("14/09/2026", "14/09/2026"),
        ("12,50%", "12,50%"),
    ]
