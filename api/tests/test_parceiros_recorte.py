"""Filtro, ordenação, paginação e exportação da lista — H36 e H38 (RF23, RF25).

Ficam em arquivo próprio porque testam uma coisa diferente do `test_parceiros`:
lá é o CRUD, aqui é o **recorte**. O que importa em cada teste é que o valor
pedido chegue até a ordem da lista e até o arquivo — não que a consulta tenha
sido montada de um jeito específico.
"""
from __future__ import annotations

import csv
import io
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db import Sessao
from app.modelos import (
    Categoria,
    Importacao,
    Metrica,
    OrigemImportacao,
    Parceiro,
    Perfil,
    Periodo,
    StatusComercial,
)
from app.servico_segmentacao import reprocessar_tudo

PRIMEIRA_SEMANA = date(2026, 3, 2)


@pytest.fixture
def analista(criar_usuario, autenticar, cliente):
    criar_usuario(login="analista", perfil=Perfil.ANALISTA)
    autenticar("analista")
    return cliente


@pytest.fixture
def rede(criar_usuario):
    """Parceiros com desempenho em duas semanas.

    Cada semana é `{nome: (faturamento, pedidos)}`. O parceiro que não aparece
    numa semana fica sem métrica ali, que é como se produz a linha sem
    desempenho — a que a ordenação precisa jogar para o fim.
    """
    autor_id = criar_usuario(login="semeador", perfil=Perfil.ADMINISTRADOR)

    def montar(*semanas: dict[str, tuple[str, int]]) -> None:
        s = Sessao()
        try:
            parceiros: dict[str, Parceiro] = {p.nome: p for p in s.query(Parceiro)}
            for indice, semana in enumerate(semanas):
                comeco = PRIMEIRA_SEMANA + timedelta(days=7 * indice)
                periodo = Periodo(data_inicio=comeco, data_fim=comeco + timedelta(days=6))
                s.add(periodo)
                s.flush()
                importacao = Importacao(
                    periodo_id=periodo.id,
                    usuario_id=autor_id,
                    origem=OrigemImportacao.TEXTO,
                    total_gravado=len(semana),
                    total_rejeitado=0,
                )
                s.add(importacao)
                s.flush()
                for nome, (faturamento, pedidos) in semana.items():
                    if nome not in parceiros:
                        parceiros[nome] = Parceiro(nome=nome)
                        s.add(parceiros[nome])
                        s.flush()
                    s.add(
                        Metrica(
                            parceiro_id=parceiros[nome].id,
                            periodo_id=periodo.id,
                            importacao_id=importacao.id,
                            faturamento=Decimal(faturamento),
                            pedidos=pedidos,
                        )
                    )
            s.commit()
        finally:
            s.close()

    return montar


def _segmentar():
    s = Sessao()
    try:
        reprocessar_tudo(s)
        s.commit()
    finally:
        s.close()


def _nomes(resposta) -> list[str]:
    return [p["nome"] for p in resposta.json()["itens"]]


# ============================================================ desempenho na lista
def test_a_lista_traz_o_desempenho_do_periodo_mais_recente(analista, rede):
    rede(
        {"Alfa": ("1000.00", 10)},
        {"Alfa": ("1500.00", 20)},
    )

    item = analista.get("/api/parceiros").json()["itens"][0]

    assert item["desempenho"]["faturamento"] == "1500.00"
    assert item["desempenho"]["pedidos"] == 20
    assert item["desempenho"]["ticket_medio"] == "75.00"
    assert item["desempenho"]["variacao_percentual"] == "50.00"


def test_parceiro_sem_metrica_continua_na_lista(analista, rede):
    """Sumir com ele faria a tela esconder justamente quem ainda não vendeu."""
    analista.post("/api/parceiros", json={"nome": "Nunca Vendeu"})
    rede({"Alfa": ("1000.00", 10)})

    itens = {p["nome"]: p["desempenho"] for p in analista.get("/api/parceiros").json()["itens"]}

    assert itens["Nunca Vendeu"]["faturamento"] is None
    assert itens["Nunca Vendeu"]["ticket_medio"] is None


def test_sem_periodo_importado_a_lista_responde_sem_desempenho(analista):
    analista.post("/api/parceiros", json={"nome": "Sozinho"})

    corpo = analista.get("/api/parceiros").json()

    assert corpo["periodo"] is None
    assert corpo["itens"][0]["desempenho"]["faturamento"] is None


# ==================================================================== ordenação
@pytest.mark.parametrize(
    "campo,esperado",
    [
        # A ordem padrão é **crescente**, inclusive nas colunas numéricas. Quem
        # quer o maior primeiro pede `descendente`; a tela faz isso no primeiro
        # clique de uma coluna de número.
        ("nome", ["Alfa", "Beta", "Gama"]),
        ("faturamento", ["Alfa", "Gama", "Beta"]),
        ("pedidos", ["Beta", "Alfa", "Gama"]),
        ("ticket_medio", ["Gama", "Alfa", "Beta"]),
    ],
)
def test_ordena_pelo_campo_pedido(analista, rede, campo, esperado):
    rede(
        {
            "Alfa": ("100.00", 10),  # ticket 10
            "Beta": ("900.00", 9),  # ticket 100
            "Gama": ("400.00", 80),  # ticket 5
        }
    )

    assert _nomes(analista.get("/api/parceiros", params={"ordenar_por": campo})) == esperado


def test_descendente_inverte_a_ordem(analista, rede):
    rede({"Alfa": ("100.00", 1), "Beta": ("900.00", 1)})

    resposta = analista.get(
        "/api/parceiros", params={"ordenar_por": "faturamento", "descendente": True}
    )

    assert _nomes(resposta) == ["Beta", "Alfa"]


def test_ordena_por_variacao(analista, rede):
    rede(
        {"Subiu": ("100.00", 1), "Caiu": ("100.00", 1)},
        {"Subiu": ("200.00", 1), "Caiu": ("50.00", 1)},
    )

    assert _nomes(analista.get("/api/parceiros", params={"ordenar_por": "variacao"})) == [
        "Caiu",  # -50%
        "Subiu",  # +100%
    ]


def test_quem_nao_tem_desempenho_vai_para_o_fim_nos_dois_sentidos(analista, rede):
    """Quem não faturou não é o melhor nem o pior.

    Mantê-lo no topo ao ordenar por faturamento decrescente empurraria para fora
    da primeira página justamente quem a ordenação existe para encontrar.
    """
    analista.post("/api/parceiros", json={"nome": "Zulu Sem Metrica"})
    rede({"Alfa": ("100.00", 1), "Beta": ("900.00", 1)})

    crescente = _nomes(analista.get("/api/parceiros", params={"ordenar_por": "faturamento"}))
    decrescente = _nomes(
        analista.get(
            "/api/parceiros", params={"ordenar_por": "faturamento", "descendente": True}
        )
    )

    assert crescente[-1] == "Zulu Sem Metrica"
    assert decrescente[-1] == "Zulu Sem Metrica"


def test_ordenacao_desconhecida_e_recusada(analista):
    """A coluna entra num `ORDER BY`: aceitar texto livre seria injeção."""
    resposta = analista.get("/api/parceiros", params={"ordenar_por": "senha_hash"})

    assert resposta.status_code == 422


# ======================================================== filtro por segmento
def test_filtra_por_segmento(analista, rede):
    rede(
        {"Caindo": ("1000.00", 1), "Subindo": ("100.00", 1), "Parado": ("500.00", 1)},
        {"Caindo": ("900.00", 1), "Subindo": ("200.00", 1), "Parado": ("500.00", 1)},
        {"Caindo": ("800.00", 1), "Subindo": ("300.00", 1), "Parado": ("500.00", 1)},
    )
    _segmentar()

    assert _nomes(analista.get("/api/parceiros", params={"segmento": "EM_RISCO"})) == ["Caindo"]


def test_o_segmento_aparece_na_linha(analista, rede):
    rede({"Alfa": ("100.00", 1)}, {"Alfa": ("200.00", 1)})
    _segmentar()

    item = analista.get("/api/parceiros").json()["itens"][0]

    # Duas semanas de histórico: recém-chegado é a classificação certa.
    assert item["desempenho"]["segmento"] == "RECEM_CHEGADO"


def test_sem_segmentacao_calculada_o_segmento_vem_nulo(analista, rede):
    rede({"Alfa": ("100.00", 1)})

    item = analista.get("/api/parceiros").json()["itens"][0]

    assert item["desempenho"]["segmento"] is None


# ==================================================================== paginação
def test_pagina_devolve_o_total_e_o_recorte(analista):
    for i in range(7):
        analista.post("/api/parceiros", json={"nome": f"P{i}"})

    corpo = analista.get("/api/parceiros", params={"tamanho": 3, "pagina": 2}).json()

    assert corpo["total"] == 7
    assert [p["nome"] for p in corpo["itens"]] == ["P3", "P4", "P5"]
    assert corpo["pagina"] == 2 and corpo["tamanho"] == 3


def test_o_total_conta_o_filtrado_e_nao_a_base(analista):
    """Total da base inteira faria a paginação prometer páginas vazias."""
    analista.post("/api/parceiros", json={"nome": "Padaria"})
    analista.post("/api/parceiros", json={"nome": "Mercado"})

    corpo = analista.get("/api/parceiros", params={"busca": "pada"}).json()

    assert corpo["total"] == 1


def test_pagina_maior_que_o_teto_e_recusada(analista):
    assert analista.get("/api/parceiros", params={"tamanho": 5000}).status_code == 422


# =================================================================== exportação
def _ler_csv(resposta) -> list[dict]:
    texto = resposta.content.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(texto), delimiter=";"))


def test_exportacao_traz_as_linhas_do_recorte(analista, rede):
    rede({"Padaria Central": ("1000.00", 10), "Mercado Azul": ("500.00", 5)})

    linhas = _ler_csv(analista.get("/api/parceiros/exportacao.csv", params={"busca": "pada"}))

    assert [linha["Parceiro"] for linha in linhas] == ["Padaria Central"]
    assert linhas[0]["Faturamento"] == "1000,00"
    assert linhas[0]["Pedidos"] == "10"


def test_o_arquivo_reflete_exatamente_os_filtros_da_tela(analista, rede):
    """Exportar um recorte diferente do visível é pior que não exportar."""
    rede(
        {"Caindo": ("1000.00", 1), "Subindo": ("100.00", 1), "Parado": ("500.00", 1)},
        {"Caindo": ("900.00", 1), "Subindo": ("200.00", 1), "Parado": ("500.00", 1)},
        {"Caindo": ("800.00", 1), "Subindo": ("300.00", 1), "Parado": ("500.00", 1)},
    )
    _segmentar()
    parametros = {"segmento": "EM_RISCO", "ordenar_por": "faturamento", "descendente": True}

    na_tela = _nomes(analista.get("/api/parceiros", params=parametros))
    no_arquivo = [
        linha["Parceiro"]
        for linha in _ler_csv(analista.get("/api/parceiros/exportacao.csv", params=parametros))
    ]

    assert no_arquivo == na_tela


def test_o_arquivo_abre_em_planilha_com_acentuacao(analista, rede):
    """BOM e vírgula decimal: sem os dois, a planilha mostra "PraÃ§a" e trata a
    coluna de dinheiro como texto."""
    rede({"Casa da Praça": ("1234.56", 3)})

    resposta = analista.get("/api/parceiros/exportacao.csv")

    assert resposta.content.startswith(b"\xef\xbb\xbf")  # BOM de UTF-8
    linha = _ler_csv(resposta)[0]
    assert linha["Parceiro"] == "Casa da Praça"
    assert linha["Faturamento"] == "1234,56"
    assert linha["Ticket medio"] == "411,52"


def test_o_arquivo_usa_rotulo_e_nao_o_valor_interno(analista, rede):
    """Ler "EM_RISCO" numa planilha onde a tela dizia "Em risco" faz parecer que
    são duas coisas diferentes."""
    rede(
        {"Caindo": ("1000.00", 1)},
        {"Caindo": ("900.00", 1)},
        {"Caindo": ("800.00", 1)},
    )
    _segmentar()
    s = Sessao()
    try:
        alvo = s.scalar(select(Parceiro).where(Parceiro.nome == "Caindo"))
        alvo.status = StatusComercial.PROSPECCAO
        s.commit()
    finally:
        s.close()

    linha = _ler_csv(analista.get("/api/parceiros/exportacao.csv"))[0]

    assert linha["Status"] == "Prospecção"
    assert linha["Segmento"] == "Em risco"
    assert linha["Situacao"] == "Ativo"


def test_a_exportacao_vem_como_arquivo_nomeado(analista, rede):
    rede({"Alfa": ("1.00", 1)})

    resposta = analista.get("/api/parceiros/exportacao.csv")

    assert resposta.headers["content-disposition"].startswith("attachment")
    assert "parceiros-2026-03-08.csv" in resposta.headers["content-disposition"]


def test_a_categoria_sai_pelo_nome(analista, rede):
    s = Sessao()
    try:
        categoria = Categoria(nome="Padaria", ativa=True)
        s.add(categoria)
        s.commit()
        categoria_id = categoria.id
    finally:
        s.close()
    analista.post("/api/parceiros", json={"nome": "Com Categoria", "categoria_id": categoria_id})
    rede({"Com Categoria": ("10.00", 1)})

    assert _ler_csv(analista.get("/api/parceiros/exportacao.csv"))[0]["Categoria"] == "Padaria"
