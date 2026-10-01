"""Os relatórios — histórias H84 a H88, caso de uso UC15 (RF44 a RF48).

Os relatórios não calculam regra nova: resumem o que as outras telas mostram. Por
isso o que importa em cada teste é a **conferência contra a fonte** — o total do
desempenho é o indicador do painel, a linha de uma categoria é o painel filtrado
por ela, o risco é o do cadastro do parceiro, o custo é o do plano, e as
operações são as da trilha de auditoria — e que o CSV traga o recorte da tela.
"""
from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import event, select
from sqlalchemy.engine import Engine

from app.db import Sessao
from app.modelos import (
    AcaoComercial,
    Auditoria,
    ExecucaoOtimizador,
    ItemPlano,
    ModoExecucao,
    Parceiro,
    Perfil,
    PlanoCampanha,
    Segmento,
    SituacaoExecucao,
)
from tests.rede import parceiro
from tests.semeadura import categorizar, segmentar

CONCLUIDA_EM = datetime(2026, 7, 6, 9, 1, tzinfo=UTC)


@pytest.fixture
def analista(criar_usuario, autenticar, cliente):
    criar_usuario(login="analista", perfil=Perfil.ANALISTA, nome="Ana Analista")
    autenticar("analista")
    return cliente


@pytest.fixture
def admin(criar_usuario, autenticar, cliente):
    criar_usuario(login="chefia", perfil=Perfil.ADMINISTRADOR, nome="Chefia")
    autenticar("chefia")
    return cliente


def _csv(resposta) -> list[list[str]]:
    assert resposta.status_code == 200, resposta.text
    assert resposta.headers["content-type"].startswith("text/csv")
    # O BOM é o que faz a planilha abrir como UTF-8; sem ele, "Açaí" vira "AÃ§aÃ­".
    assert resposta.content.startswith(b"\xef\xbb\xbf")
    texto = resposta.content.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(texto), delimiter=";"))


def _contar_consultas(chamar, *tabelas: str) -> int:
    consultas: list[str] = []

    def anotar(conn, cursor, texto, parametros, contexto, muitos):  # noqa: ANN001
        consultas.append(texto)

    event.listen(Engine, "before_cursor_execute", anotar)
    try:
        chamar()
    finally:
        event.remove(Engine, "before_cursor_execute", anotar)
    return len([c for c in consultas if any(t in c.lower() for t in tabelas)])


# ================================================== 1. desempenho (RF44, H84)
@pytest.fixture
def rede(semear):
    """Duas semanas, cinco parceiros, duas categorias — e o Gama sem categoria.

    A segunda semana tem o Épsilon, que não vendeu na primeira: o estreante que
    mostra a diferença entre "o mesmo grupo no período anterior" e outra conta.
    """
    periodos = semear(
        {"Alfa": ("1000.00", 10), "Beta": ("800.00", 8), "Gama": ("600.00", 6),
         "Delta": ("400.00", 4)},
        {"Alfa": ("900.00", 9), "Beta": ("880.00", 8), "Gama": ("300.00", 5),
         "Delta": ("500.00", 5), "Epsilon": ("120.00", 3)},
    )
    categorias = categorizar(Padaria=["Beta", "Delta", "Epsilon"], Mercado=["Alfa"])
    return {"periodos": periodos, **categorias}


def test_o_total_do_relatorio_e_o_indicador_do_painel(analista, rede):
    relatorio = analista.get("/api/relatorios/desempenho").json()
    painel = analista.get("/api/painel/indicadores").json()

    total = relatorio["total"]
    assert total["faturamento"] == painel["faturamento"] == "2700.00"
    assert total["pedidos"] == painel["pedidos"]
    assert total["parceiros"] == painel["parceiros_ativos"]
    assert total["ticket_medio"] == painel["ticket_medio"]
    assert total["variacao_percentual"] == painel["variacao"]["faturamento"]
    assert relatorio["periodo"] == painel["periodo"]
    assert relatorio["periodo_anterior"] == painel["periodo_anterior"]


def test_cada_categoria_do_relatorio_e_o_painel_filtrado_por_ela(analista, rede):
    relatorio = analista.get("/api/relatorios/desempenho").json()

    por_rotulo = {linha["rotulo"]: linha for linha in relatorio["por_categoria"]}
    assert set(por_rotulo) == {"Padaria", "Mercado", "Sem categoria"}
    for nome in ("Padaria", "Mercado"):
        painel = analista.get(
            "/api/painel/indicadores", params={"categoria_id": rede[nome]}
        ).json()
        linha = por_rotulo[nome]
        assert linha["chave"] == str(rede[nome])
        assert linha["faturamento"] == painel["faturamento"]
        assert linha["pedidos"] == painel["pedidos"]
        assert linha["parceiros"] == painel["parceiros_ativos"]
        assert linha["ticket_medio"] == painel["ticket_medio"]
        assert linha["variacao_percentual"] == painel["variacao"]["faturamento"]


def test_as_categorias_vem_da_maior_para_a_menor_e_somam_o_total(analista, rede):
    relatorio = analista.get("/api/relatorios/desempenho").json()

    linhas = relatorio["por_categoria"]
    assert [linha["rotulo"] for linha in linhas] == ["Padaria", "Mercado", "Sem categoria"]
    assert linhas[0]["faturamento"] == "1500.00"  # Beta 880 + Delta 500 + Épsilon 120
    # Contra a Padaria da semana anterior (800 + 400): o Épsilon entra na soma de agora.
    assert linhas[0]["variacao_percentual"] == "25.00"
    assert linhas[2]["chave"] is None
    assert sum(Decimal(linha["faturamento"]) for linha in linhas) == Decimal(
        relatorio["total"]["faturamento"]
    )
    assert sum(linha["parceiros"] for linha in linhas) == relatorio["total"]["parceiros"]


def test_o_ticket_medio_e_a_razao_dos_totais_e_nao_a_media_dos_tickets(analista, semear):
    """RN04. Um parceiro com 1 pedido de R$ 100 e outro com 99 de R$ 1: o ticket
    da rede é 1,99, e não os 50,50 da média das médias."""
    semear({"Caro": ("100.00", 1), "Barato": ("99.00", 99)})

    total = analista.get("/api/relatorios/desempenho").json()["total"]

    assert total["ticket_medio"] == "1.99"


def test_periodo_sem_segmentacao_nao_inventa_o_agrupamento_por_segmento(analista, rede):
    relatorio = analista.get("/api/relatorios/desempenho").json()

    assert relatorio["segmentado"] is False
    assert relatorio["por_segmento"] == []


def test_por_segmento_soma_o_total_e_compara_com_o_segmento_do_periodo_anterior(
    analista, semear
):
    semear(
        {"Caindo": ("1000.00", 1), "Parado": ("500.00", 1), "Subindo": ("100.00", 1)},
        {"Caindo": ("900.00", 1), "Parado": ("500.00", 1), "Subindo": ("200.00", 1)},
        {"Caindo": ("800.00", 1), "Parado": ("500.00", 1), "Subindo": ("300.00", 1)},
    )
    segmentar()

    relatorio = analista.get("/api/relatorios/desempenho").json()
    distribuicao = analista.get("/api/painel/segmentos").json()

    assert relatorio["segmentado"] is True
    por_segmento = {linha["chave"]: linha for linha in relatorio["por_segmento"]}
    # Os mesmos parceiros que o painel conta em cada segmento.
    assert {s: linha["parceiros"] for s, linha in por_segmento.items()} == {
        fatia["segmento"]: fatia["total"] for fatia in distribuicao["itens"]
    }
    assert por_segmento["EM_RISCO"]["rotulo"] == "Em risco"
    assert por_segmento["EM_RISCO"]["faturamento"] == "800.00"
    assert sum(Decimal(linha["faturamento"]) for linha in por_segmento.values()) == Decimal(
        relatorio["total"]["faturamento"]
    )
    # Dos mesmos parceiros: o Caindo foi de 900 para 800; o Parado e o Subindo, de 700 para 800.
    assert por_segmento["EM_RISCO"]["variacao_percentual"] == "-11.11"
    assert por_segmento["TOP"]["variacao_percentual"] == "14.29"
    assert relatorio["mesmos_parceiros"] is False


def test_a_variacao_do_segmento_e_a_dos_parceiros_dele_e_nao_a_de_quem_entrou(analista, semear):
    """O defeito que a base de demonstração mostrou: o Em risco "crescendo 47%".

    Na semana anterior só o Caindo estava em risco; nesta, o Tombou também. O
    segmento fatura mais porque tem mais gente — e os dois parceiros dele caíram.
    Comparar o segmento de agora com o de antes daria alta; a dos mesmos
    parceiros dá a queda, que é o que aconteceu.
    """
    semear(
        {"Caindo": ("1000.00", 1), "Tombou": ("2000.00", 1), "Parado": ("500.00", 1)},
        {"Caindo": ("900.00", 1), "Tombou": ("2100.00", 1), "Parado": ("500.00", 1)},
        {"Caindo": ("800.00", 1), "Tombou": ("1900.00", 1), "Parado": ("500.00", 1)},
        {"Caindo": ("700.00", 1), "Tombou": ("1700.00", 1), "Parado": ("500.00", 1)},
    )
    segmentar()

    relatorio = analista.get("/api/relatorios/desempenho").json()

    em_risco = next(g for g in relatorio["por_segmento"] if g["chave"] == "EM_RISCO")
    assert em_risco["parceiros"] == 2
    assert em_risco["faturamento"] == "2400.00"
    # 800 + 1900 = 2700 na semana anterior, dos mesmos dois: queda de 11,11%.
    assert em_risco["variacao_percentual"] == "-11.11"


def test_estreante_fica_fora_das_duas_somas_da_variacao_dos_mesmos_parceiros(analista, semear):
    """Quem não vendeu no período anterior não tem de onde variar — como no
    ranking, em que a variação dele é nula. Entrar na soma de agora sem entrar
    na de antes inflaria a variação do segmento."""
    semear(
        {"Antigo": ("100.00", 1)},
        {"Antigo": ("110.00", 1), "Estreante": ("5000.00", 1)},
    )
    segmentar()

    relatorio = analista.get("/api/relatorios/desempenho").json()

    assert len(relatorio["por_segmento"]) == 1  # os dois são recém-chegados
    assert relatorio["por_segmento"][0]["faturamento"] == "5110.00"
    assert relatorio["por_segmento"][0]["variacao_percentual"] == "10.00"
    # O total continua sendo o do painel, que conta o estreante.
    assert relatorio["total"]["variacao_percentual"] == "5010.00"


def test_os_filtros_do_desempenho_recortam_e_a_resposta_diz_o_recorte(analista, semear):
    periodos = semear(
        {"Caindo": ("1000.00", 1), "Parado": ("500.00", 1), "Subindo": ("100.00", 1)},
        {"Caindo": ("900.00", 1), "Parado": ("500.00", 1), "Subindo": ("200.00", 1)},
        {"Caindo": ("800.00", 1), "Parado": ("500.00", 1), "Subindo": ("300.00", 1)},
    )
    categorias = categorizar(Padaria=["Caindo", "Parado"])
    segmentar()

    por_periodo = analista.get(
        "/api/relatorios/desempenho", params={"periodo_id": periodos[1]}
    ).json()
    por_categoria = analista.get(
        "/api/relatorios/desempenho", params={"categoria_id": categorias["Padaria"]}
    ).json()
    por_segmento = analista.get(
        "/api/relatorios/desempenho", params={"segmento": "EM_RISCO"}
    ).json()

    assert por_periodo["periodo"]["id"] == periodos[1]
    assert por_periodo["total"]["faturamento"] == "1600.00"
    assert por_categoria["categoria"]["nome"] == "Padaria"
    assert por_categoria["total"]["faturamento"] == "1300.00"
    assert [linha["rotulo"] for linha in por_categoria["por_categoria"]] == ["Padaria"]
    assert por_segmento["segmento"] == "EM_RISCO"
    assert por_segmento["total"]["faturamento"] == "800.00"
    assert [linha["chave"] for linha in por_segmento["por_segmento"]] == ["EM_RISCO"]
    # Com filtro de segmento, o total e as categorias também são dos mesmos parceiros.
    assert por_segmento["mesmos_parceiros"] is True
    assert por_segmento["total"]["variacao_percentual"] == "-11.11"
    assert por_segmento["por_categoria"][0]["variacao_percentual"] == "-11.11"
    assert por_categoria["mesmos_parceiros"] is False


def test_base_vazia_devolve_o_relatorio_vazio_e_nao_erro(analista):
    relatorio = analista.get("/api/relatorios/desempenho").json()

    assert relatorio["periodo"] is None
    assert relatorio["total"] is None
    assert relatorio["por_categoria"] == []


@pytest.mark.parametrize(
    ("parametros", "trecho"),
    [({"periodo_id": 999999}, "período"), ({"categoria_id": 999999}, "categoria")],
)
def test_recorte_que_nao_existe_e_recusa_com_ajuda(analista, rede, parametros, trecho):
    r = analista.get("/api/relatorios/desempenho", params=parametros)

    assert r.status_code == 404
    assert trecho in r.json()["detail"]["erro"]
    assert r.json()["detail"]["ajuda"]


def test_o_desempenho_nao_faz_uma_consulta_por_parceiro(analista, semear):
    semana = {f"P{i:03d}": (f"{1000 - i}.00", 1) for i in range(60)}
    semear(semana, semana)
    categorizar(Padaria=[f"P{i:03d}" for i in range(0, 60, 2)])

    consultas = _contar_consultas(
        lambda: analista.get("/api/relatorios/desempenho"), "metrica", "historico_segmento"
    )

    # Dois agrupamentos em dois períodos, e se o período foi segmentado.
    assert consultas <= 5, f"{consultas} consultas para 60 parceiros"


def test_o_csv_do_desempenho_traz_as_categorias_os_segmentos_e_o_total(analista, rede):
    segmentar()
    relatorio = analista.get("/api/relatorios/desempenho").json()

    r = analista.get("/api/relatorios/desempenho/exportacao.csv")

    linhas = _csv(r)
    assert linhas[0] == [
        "Agrupamento", "Grupo", "Parceiros", "Faturamento", "Pedidos", "Ticket médio",
        "Variação %",
    ]
    assert linhas[1] == ["Categoria", "Padaria", "3", "1500,00", "16", "93,75", "25,00"]
    assert [linha[0] for linha in linhas[1:]] == (
        ["Categoria"] * 3 + ["Segmento"] * len(relatorio["por_segmento"]) + ["Total"]
    )
    assert linhas[-1][:4] == ["Total", "Total", "5", "2700,00"]
    assert "relatorio-desempenho-" in r.headers["content-disposition"]


def test_o_csv_do_desempenho_leva_o_recorte_da_tela(analista, rede):
    linhas = _csv(
        analista.get(
            "/api/relatorios/desempenho/exportacao.csv", params={"categoria_id": rede["Mercado"]}
        )
    )

    assert [linha[1] for linha in linhas[1:] if linha[0] == "Categoria"] == ["Mercado"]
    assert linhas[-1][3] == "900,00"


def test_categoria_com_nome_de_formula_nao_vira_formula_na_planilha(analista, semear):
    semear({"Alfa": ("100.00", 1)})
    categorizar(**{"=HYPERLINK(\"http://exemplo.test\")": ["Alfa"]})

    linhas = _csv(analista.get("/api/relatorios/desempenho/exportacao.csv"))

    assert linhas[1][1].startswith("'=HYPERLINK")


# ======================================================= 2. risco (RF45, H85)
def _rede_com_previsao(base, **extra):
    return base(
        [
            parceiro("Alto Risco", "900.00", previsto="700.00", risco=0.81, categoria="Padaria",
                     segmento=Segmento.EM_RISCO),
            parceiro("Medio Risco", "500.00", previsto="520.00", risco=0.40, categoria="Padaria",
                     segmento=Segmento.ESTAVEL),
            parceiro("Baixo Risco", "1500.00", previsto="1600.00", risco=0.04, categoria="Mercado",
                     segmento=Segmento.TOP),
            # Só dois períodos de histórico: sem previsão, pelo motivo da RN09.
            parceiro("Recem Chegado", "300.00", categoria="Mercado", periodos=2,
                     segmento=Segmento.RECEM_CHEGADO),
        ],
        **extra,
    )


def _plano(rede, itens, *, viavel=True, situacao=SituacaoExecucao.CONCLUIDA, minutos=0) -> int:
    """Uma execução e, se viável, o plano: parceiro, ação, custo e ganho de cada item."""
    s = Sessao()
    try:
        concluida = situacao == SituacaoExecucao.CONCLUIDA
        quando = CONCLUIDA_EM + timedelta(minutes=minutos)
        execucao = ExecucaoOtimizador(
            situacao=situacao,
            modo=ModoExecucao.SERIAL,
            parametros={"orcamento": "5000.00", "maximo_acoes": 30},
            periodo_base_id=rede.base_id,
            modelo_versao="rede-1",
            semente=42,
            iniciada_em=quando,
            concluida_em=quando if concluida else None,
            viavel=viavel if concluida else None,
            restricao_violada=None if viavel or not concluida else "orcamento",
            tempo_ms=1200 if concluida else None,
        )
        s.add(execucao)
        s.flush()
        if concluida and viavel:
            plano = PlanoCampanha(
                execucao_id=execucao.id,
                aplicacao_inicio=date(2026, 7, 13),
                aplicacao_fim=date(2026, 7, 19),
            )
            s.add(plano)
            s.flush()
            acoes = {a.nome: a.id for a in s.scalars(select(AcaoComercial))}
            for nome, acao, custo, ganho in itens:
                s.add(
                    ItemPlano(
                        plano_id=plano.id,
                        parceiro_id=rede.parceiros[nome],
                        acao_id=acoes[acao],
                        custo=Decimal(custo),
                        uplift_esperado=Decimal(ganho),
                    )
                )
        s.commit()
        return execucao.id
    finally:
        s.close()


VISITA, VITRINE = "Visita de relacionamento", "Destaque na vitrine"


def test_o_risco_vem_do_maior_para_o_menor_e_quem_nao_tem_previsao_fica_no_fim(analista, base):
    _rede_com_previsao(base)

    relatorio = analista.get("/api/relatorios/risco").json()

    assert relatorio["disponivel"] is True
    assert [i["nome"] for i in relatorio["itens"]] == [
        "Alto Risco", "Medio Risco", "Baixo Risco", "Recem Chegado",
    ]
    alto = relatorio["itens"][0]
    assert alto["categoria"] == "Padaria"
    assert alto["segmento"] == "EM_RISCO"
    assert alto["faturamento"] == "900.00"
    assert alto["faturamento_previsto"] == "700.00"
    assert alto["probabilidade_queda"] == pytest.approx(0.81)
    assert alto["variacao_percentual"] == "0.00"
    assert alto["sem_previsao"] is None


def test_quem_nao_tem_previsao_aparece_com_o_motivo_e_nao_com_zero(analista, base):
    """RN09, UC15-A1: o mesmo motivo que o cadastro do parceiro mostra."""
    rede = _rede_com_previsao(base)

    novato = analista.get("/api/relatorios/risco").json()["itens"][-1]
    do_cadastro = analista.get(
        f"/api/parceiros/{rede.parceiros['Recem Chegado']}/previsao"
    ).json()

    assert novato["probabilidade_queda"] is None
    assert novato["faturamento_previsto"] is None
    assert novato["sem_previsao"] == do_cadastro["motivo"]
    assert "2 períodos" in novato["sem_previsao"]


def test_o_risco_do_relatorio_e_o_do_cadastro_e_diz_de_que_modelo(analista, base):
    rede = _rede_com_previsao(base)

    relatorio = analista.get("/api/relatorios/risco").json()
    do_cadastro = analista.get(f"/api/parceiros/{rede.parceiros['Alto Risco']}/previsao").json()

    assert relatorio["itens"][0]["probabilidade_queda"] == pytest.approx(
        do_cadastro["probabilidade_queda"]
    )
    assert relatorio["modelo_versao"] == do_cadastro["modelo_versao"] == "rede-1"
    assert relatorio["periodo_base"]["id"] == rede.base_id
    assert relatorio["origem"] == "MODELO"
    assert relatorio["desatualizada"] is False


def test_o_resumo_do_risco_soma_os_mesmos_parceiros_e_e_o_do_painel(analista, base):
    _rede_com_previsao(base)

    relatorio = analista.get("/api/relatorios/risco").json()
    painel = analista.get("/api/painel/decisao").json()["previsao"]

    assert relatorio["total"] == 4
    assert relatorio["com_previsao"] == painel["parceiros"] == 3
    assert relatorio["faturamento_previsto"] == painel["faturamento_previsto"] == "2820.00"
    assert relatorio["faturamento_medido"] == painel["faturamento_medido"] == "2900.00"


def test_o_risco_minimo_e_filtro_de_quem_consulta(analista, base):
    _rede_com_previsao(base)

    relatorio = analista.get("/api/relatorios/risco", params={"risco_minimo": 0.4}).json()

    assert [i["nome"] for i in relatorio["itens"]] == ["Alto Risco", "Medio Risco"]
    assert relatorio["risco_minimo"] == 0.4
    assert relatorio["total"] == relatorio["com_previsao"] == 2


@pytest.mark.parametrize("valor", [-0.1, 1.5])
def test_risco_minimo_fora_de_zero_a_um_e_recusado(analista, base, valor):
    _rede_com_previsao(base)

    assert analista.get("/api/relatorios/risco", params={"risco_minimo": valor}).status_code == 422


def test_os_filtros_de_categoria_e_de_segmento_recortam_o_risco(analista, base):
    rede = _rede_com_previsao(base)

    da_padaria = analista.get(
        "/api/relatorios/risco", params={"categoria_id": rede.categorias["Padaria"]}
    ).json()
    em_risco = analista.get("/api/relatorios/risco", params={"segmento": "EM_RISCO"}).json()

    assert [i["nome"] for i in da_padaria["itens"]] == ["Alto Risco", "Medio Risco"]
    assert da_padaria["categoria"]["nome"] == "Padaria"
    assert [i["nome"] for i in em_risco["itens"]] == ["Alto Risco"]
    assert em_risco["segmento"] == "EM_RISCO"


def test_o_relatorio_traz_a_acao_de_cada_parceiro_no_ultimo_plano(analista, base):
    rede = _rede_com_previsao(base)
    execucao_id = _plano(rede, [("Alto Risco", VISITA, "90.00", "210.50")])

    relatorio = analista.get("/api/relatorios/risco").json()
    do_cadastro = analista.get(f"/api/parceiros/{rede.parceiros['Alto Risco']}/campanha").json()

    alto, medio = relatorio["itens"][0], relatorio["itens"][1]
    assert alto["acao"] == do_cadastro["acao"] == VISITA
    assert alto["custo"] == do_cadastro["custo"] == "90.00"
    assert medio["acao"] is None and medio["custo"] is None
    assert relatorio["plano"]["execucao_id"] == execucao_id
    assert relatorio["no_plano"] == 1


def test_sem_plano_o_risco_sai_sem_a_coluna_da_acao_preenchida(analista, base):
    _rede_com_previsao(base)

    relatorio = analista.get("/api/relatorios/risco").json()

    assert relatorio["plano"] is None
    assert relatorio["no_plano"] == 0
    assert all(i["acao"] is None for i in relatorio["itens"])


def test_sem_modelo_treinado_o_relatorio_de_risco_diz_o_que_falta(analista, base):
    _rede_com_previsao(base, treinado=False)

    relatorio = analista.get("/api/relatorios/risco").json()

    assert relatorio["disponivel"] is False
    assert relatorio["motivo"] == "O modelo ainda não foi treinado."
    assert "tela Modelo" in relatorio["ajuda"]
    assert relatorio["itens"] == []


def test_o_risco_pagina_e_o_resumo_continua_sendo_do_recorte_inteiro(analista, base):
    _rede_com_previsao(base)

    relatorio = analista.get("/api/relatorios/risco", params={"tamanho": 2, "pagina": 2}).json()

    assert [i["nome"] for i in relatorio["itens"]] == ["Baixo Risco", "Recem Chegado"]
    assert relatorio["total"] == 4
    assert relatorio["faturamento_previsto"] == "2820.00"


@pytest.mark.parametrize("quantos", [5, 60])
def test_o_risco_nao_faz_uma_consulta_por_parceiro(analista, base, quantos):
    base(
        [
            parceiro(f"Parceiro {i:03d}", "100.00", previsto="90.00", risco=i / 100)
            for i in range(quantos)
        ]
    )

    consultas = _contar_consultas(
        lambda: analista.get("/api/relatorios/risco", params={"tamanho": 200}),
        "previsao", "metrica", "item_plano",
    )

    # O período mais recente, o resumo e a página — com 5 ou com 60.
    assert consultas <= 4, f"{consultas} consultas para {quantos} parceiros"


def test_o_csv_do_risco_e_o_recorte_inteiro_com_o_mesmo_texto_da_tela(analista, base):
    rede = _rede_com_previsao(base)
    _plano(rede, [("Alto Risco", VISITA, "90.00", "210.50")])

    r = analista.get("/api/relatorios/risco/exportacao.csv")

    linhas = _csv(r)
    assert linhas[0] == [
        "Parceiro", "Categoria", "Segmento", "Faturamento", "Variação %", "Faturamento previsto",
        "Risco de queda", "Sem previsão", "Ação no último plano", "Custo da ação",
    ]
    assert linhas[1] == [
        "Alto Risco", "Padaria", "Em risco", "900,00", "0,00", "700,00", "81%", "", VISITA,
        "90,00",
    ]
    assert linhas[4][0] == "Recem Chegado"
    assert linhas[4][6] == "" and "2 períodos" in linhas[4][7]
    assert len(linhas) == 5
    assert "relatorio-risco-" in r.headers["content-disposition"]


def test_o_csv_do_risco_leva_os_filtros_e_recusa_sem_modelo(analista, base):
    rede = _rede_com_previsao(base)

    linhas = _csv(
        analista.get(
            "/api/relatorios/risco/exportacao.csv",
            params={"categoria_id": rede.categorias["Padaria"], "risco_minimo": 0.5},
        )
    )

    assert [linha[0] for linha in linhas[1:]] == ["Alto Risco"]


def test_sem_modelo_o_csv_do_risco_e_recusado_com_o_motivo(analista, base):
    _rede_com_previsao(base, treinado=False)

    r = analista.get("/api/relatorios/risco/exportacao.csv")

    assert r.status_code == 409
    assert r.json()["detail"]["erro"] == "O modelo ainda não foi treinado."


# ==================================================== 3. campanha (RF46, H86)
def _rede_com_plano(base):
    rede = _rede_com_previsao(base)
    execucao_id = _plano(
        rede,
        [
            ("Alto Risco", VISITA, "90.00", "210.50"),
            ("Medio Risco", VISITA, "90.00", "40.00"),
            ("Baixo Risco", VITRINE, "260.00", "300.00"),
        ],
    )
    return rede, execucao_id


def test_o_relatorio_da_campanha_soma_o_plano_gravado(analista, base):
    _rede, execucao_id = _rede_com_plano(base)

    relatorio = analista.get("/api/relatorios/campanha").json()
    s = Sessao()
    try:
        gravado = s.execute(
            select(ItemPlano.custo, ItemPlano.uplift_esperado)
            .join(PlanoCampanha, PlanoCampanha.id == ItemPlano.plano_id)
            .where(PlanoCampanha.execucao_id == execucao_id)
        ).all()
    finally:
        s.close()

    total = relatorio["total"]
    assert total["parceiros"] == len(gravado) == 3
    assert Decimal(total["custo"]) == sum(custo for custo, _ in gravado) == Decimal("440.00")
    assert Decimal(total["ganho_esperado"]) == sum(ganho for _, ganho in gravado)
    assert relatorio["plano"]["execucao_id"] == execucao_id
    assert relatorio["plano"]["modelo_versao"] == "rede-1"
    assert relatorio["orcamento"] == "5000.00"


def test_a_campanha_por_acao_por_categoria_e_por_segmento(analista, base):
    rede, _ = _rede_com_plano(base)

    relatorio = analista.get("/api/relatorios/campanha").json()

    por_acao = {linha["rotulo"]: linha for linha in relatorio["por_acao"]}
    assert por_acao[VISITA]["parceiros"] == 2
    assert por_acao[VISITA]["custo"] == "180.00"
    assert por_acao[VISITA]["ganho_esperado"] == "250.50"
    assert por_acao[VITRINE]["custo"] == "260.00"
    # O maior ganho primeiro.
    assert [linha["rotulo"] for linha in relatorio["por_acao"]] == [VITRINE, VISITA]

    por_categoria = {linha["rotulo"]: linha for linha in relatorio["por_categoria"]}
    assert por_categoria["Padaria"]["parceiros"] == 2
    assert por_categoria["Padaria"]["chave"] == str(rede.categorias["Padaria"])
    assert por_categoria["Mercado"]["custo"] == "260.00"

    por_segmento = {linha["chave"]: linha for linha in relatorio["por_segmento"]}
    assert por_segmento["EM_RISCO"]["rotulo"] == "Em risco"
    assert por_segmento["EM_RISCO"]["ganho_esperado"] == "210.50"
    assert set(por_segmento) == {"EM_RISCO", "ESTAVEL", "TOP"}
    assert relatorio["periodo_base"]["id"] == rede.base_id


def test_cada_agrupamento_da_campanha_soma_o_total(analista, base):
    _rede_com_plano(base)

    relatorio = analista.get("/api/relatorios/campanha").json()

    for agrupamento in ("por_acao", "por_categoria", "por_segmento"):
        linhas = relatorio[agrupamento]
        assert sum(Decimal(linha["custo"]) for linha in linhas) == Decimal(
            relatorio["total"]["custo"]
        ), agrupamento
        assert sum(linha["parceiros"] for linha in linhas) == relatorio["total"]["parceiros"]


def test_sem_escolha_vale_o_ultimo_plano_viavel_e_da_para_escolher_outro(analista, base):
    rede = _rede_com_previsao(base)
    primeiro = _plano(rede, [("Alto Risco", VISITA, "90.00", "210.50")])
    segundo = _plano(rede, [("Baixo Risco", VITRINE, "260.00", "300.00")], minutos=10)
    _plano(rede, [], viavel=False, minutos=20)

    padrao = analista.get("/api/relatorios/campanha").json()
    escolhido = analista.get("/api/relatorios/campanha", params={"execucao_id": primeiro}).json()

    assert padrao["plano"]["execucao_id"] == segundo
    assert escolhido["plano"]["execucao_id"] == primeiro
    assert escolhido["total"]["custo"] == "90.00"


def test_os_planos_para_escolher_sao_so_os_viaveis_do_mais_recente(analista, base):
    rede = _rede_com_previsao(base)
    primeiro = _plano(rede, [("Alto Risco", VISITA, "90.00", "210.50")])
    segundo = _plano(rede, [("Baixo Risco", VITRINE, "260.00", "300.00")], minutos=10)
    _plano(rede, [], viavel=False, minutos=20)
    _plano(rede, [], situacao=SituacaoExecucao.EM_ANDAMENTO, minutos=30)

    planos = analista.get("/api/relatorios/campanha/planos").json()

    assert [p["execucao_id"] for p in planos] == [segundo, primeiro]
    assert planos[0]["aplicacao_inicio"] == "2026-07-13"
    # O primeiro da lista é o que o relatório abre sem escolha.
    padrao = analista.get("/api/relatorios/campanha").json()
    assert padrao["plano"] == planos[0]


def test_sem_plano_calculado_o_relatorio_da_campanha_diz_isso(analista, base):
    _rede_com_previsao(base)

    relatorio = analista.get("/api/relatorios/campanha").json()

    assert relatorio["plano"] is None
    assert relatorio["total"] is None
    assert relatorio["por_acao"] == []


def test_execucao_sem_plano_e_recusada_com_o_porque(analista, base):
    rede = _rede_com_previsao(base)
    inviavel = _plano(rede, [], viavel=False)
    em_andamento = _plano(rede, [], situacao=SituacaoExecucao.EM_ANDAMENTO, minutos=5)

    r_inviavel = analista.get("/api/relatorios/campanha", params={"execucao_id": inviavel})
    r_andamento = analista.get("/api/relatorios/campanha", params={"execucao_id": em_andamento})
    r_inexistente = analista.get("/api/relatorios/campanha", params={"execucao_id": 999999})

    assert r_inviavel.status_code == 409
    assert "sem plano viável" in r_inviavel.json()["detail"]["erro"]
    assert r_andamento.status_code == 409
    assert "não foi concluída" in r_andamento.json()["detail"]["erro"]
    assert r_inexistente.status_code == 404


def test_o_csv_da_campanha_traz_os_tres_agrupamentos_e_o_total(analista, base):
    _rede, execucao_id = _rede_com_plano(base)

    r = analista.get("/api/relatorios/campanha/exportacao.csv")

    linhas = _csv(r)
    assert linhas[0] == ["Agrupamento", "Grupo", "Parceiros", "Custo", "Ganho esperado"]
    assert linhas[1] == ["Ação", VITRINE, "1", "260,00", "300,00"]
    assert [linha[0] for linha in linhas[1:]] == (
        ["Ação"] * 2 + ["Categoria"] * 2 + ["Segmento"] * 3 + ["Total"]
    )
    assert linhas[-1] == ["Total", "Total", "3", "440,00", "550,50"]
    assert f"execucao-{execucao_id}" in r.headers["content-disposition"]


def test_sem_plano_o_csv_da_campanha_e_recusado_com_o_motivo(analista, base):
    _rede_com_previsao(base)

    r = analista.get("/api/relatorios/campanha/exportacao.csv")

    assert r.status_code == 409
    assert "Nenhum plano" in r.json()["detail"]["erro"]


# =================================================== 4. operações (RF47, H87)
def _hoje() -> date:
    return datetime.now().astimezone().date()


def _recuar(dias: int, *, acao: str) -> None:
    """Empurra para trás, no relógio, os registros de uma ação — para haver mais de um dia."""
    s = Sessao()
    try:
        for registro in s.scalars(select(Auditoria).where(Auditoria.acao == acao)):
            registro.ocorrido_em = registro.ocorrido_em - timedelta(days=dias)
        s.commit()
    finally:
        s.close()


@pytest.fixture
def trilha(admin, criar_usuario):
    """O administrador entrou, criou um usuário e mudou o perfil dele; alguém errou a senha."""
    novo = {"login": "novato", "nome": "Novato", "senha": "senha-bem-comprida-1"}
    admin.post("/api/usuarios", json={**novo, "perfil": "ANALISTA"})
    novato = admin.get("/api/usuarios").json()
    alvo = next(u["id"] for u in novato if u["login"] == "novato")
    admin.patch(f"/api/usuarios/{alvo}", json={"perfil": "GESTOR"})
    admin.post("/api/sessao", json={"login": "ninguem", "senha": "chute-qualquer-1"})
    return admin


def test_as_operacoes_somam_a_trilha_no_mesmo_recorte(trilha):
    relatorio = trilha.get("/api/relatorios/operacoes").json()
    da_trilha = trilha.get(
        "/api/auditoria", params={"de": relatorio["de"], "ate": relatorio["ate"]}
    ).json()

    assert relatorio["total"] == da_trilha["total"]
    for agrupamento in ("por_acao", "por_usuario", "por_dia"):
        assert sum(linha["total"] for linha in relatorio[agrupamento]) == relatorio["total"]
    assert relatorio["outras_pessoas"] is None


def test_as_operacoes_por_acao_trazem_o_rotulo_da_trilha(trilha):
    relatorio = trilha.get("/api/relatorios/operacoes").json()

    por_acao = {linha["chave"]: linha for linha in relatorio["por_acao"]}
    assert por_acao["USUARIO_CRIADO"]["rotulo"] == "Usuário criado"
    assert por_acao["USUARIO_CRIADO"]["total"] == 1
    assert por_acao["PERFIL_ALTERADO"]["total"] == 1
    assert por_acao["LOGIN_FALHA"]["rotulo"] == "Entrada recusada"
    totais = [linha["total"] for linha in relatorio["por_acao"]]
    assert totais == sorted(totais, reverse=True)


def test_as_operacoes_por_usuario_dizem_quem_e_contam_o_que_nao_tem_usuario(trilha):
    relatorio = trilha.get("/api/relatorios/operacoes").json()

    por_usuario = {linha["rotulo"]: linha for linha in relatorio["por_usuario"]}
    assert "Chefia (chefia)" in por_usuario
    # A entrada recusada com login que não existe não tem usuário para apontar.
    assert por_usuario["sem usuário"]["total"] == 1
    assert por_usuario["sem usuário"]["chave"] is None


def test_a_tela_lista_as_pessoas_que_mais_fizeram_e_soma_as_outras(trilha, criar_usuario):
    """A base de demonstração guarda os usuários de cada verificação, e "por
    pessoa" tinha duzentas linhas. A soma continua a do total; o CSV traz todas."""
    # Direto na trilha: vinte entradas recusadas seguidas esbarrariam no bloqueio de login.
    s = Sessao()
    try:
        for i in range(20):
            pessoa = criar_usuario(
                login=f"pessoa{i:02d}", perfil=Perfil.ANALISTA, nome=f"Pessoa {i:02d}"
            )
            s.add(Auditoria(usuario_id=pessoa, acao="LOGIN_SUCESSO", origem="teste"))
        s.commit()
    finally:
        s.close()

    relatorio = trilha.get("/api/relatorios/operacoes").json()
    arquivo = _csv(trilha.get("/api/relatorios/operacoes/exportacao.csv"))

    assert len(relatorio["por_usuario"]) == 15
    # A Chefia, o "sem usuário" e as vinte pessoas: sete ficam na linha das outras.
    assert relatorio["pessoas"] == 22
    assert relatorio["outras_pessoas"]["rotulo"] == "Outras 7 pessoas"
    listadas = sum(linha["total"] for linha in relatorio["por_usuario"])
    assert listadas + relatorio["outras_pessoas"]["total"] == relatorio["total"]
    assert len([linha for linha in arquivo if linha[0] == "Usuário"]) == 22


def test_com_poucas_pessoas_nao_ha_linha_das_outras(trilha):
    relatorio = trilha.get("/api/relatorios/operacoes").json()

    assert relatorio["outras_pessoas"] is None
    assert relatorio["pessoas"] == len(relatorio["por_usuario"]) == 2


def test_sem_datas_valem_os_ultimos_trinta_dias_com_hoje_dentro(trilha):
    relatorio = trilha.get("/api/relatorios/operacoes").json()

    assert relatorio["ate"] == _hoje().isoformat()
    assert relatorio["de"] == (_hoje() - timedelta(days=29)).isoformat()
    assert [linha["chave"] for linha in relatorio["por_dia"]] == [_hoje().isoformat()]


def test_as_operacoes_por_dia_separam_os_dias_e_o_intervalo_recorta(trilha):
    _recuar(3, acao="USUARIO_CRIADO")
    _recuar(40, acao="PERFIL_ALTERADO")

    padrao = trilha.get("/api/relatorios/operacoes").json()
    so_hoje = trilha.get(
        "/api/relatorios/operacoes", params={"de": _hoje().isoformat()}
    ).json()

    dias = [linha["chave"] for linha in padrao["por_dia"]]
    assert dias == [(_hoje() - timedelta(days=3)).isoformat(), _hoje().isoformat()]
    # O de 40 dias atrás ficou fora dos trinta.
    assert "PERFIL_ALTERADO" not in {linha["chave"] for linha in padrao["por_acao"]}
    assert "USUARIO_CRIADO" not in {linha["chave"] for linha in so_hoje["por_acao"]}
    assert so_hoje["de"] == so_hoje["ate"] == _hoje().isoformat()


def test_os_filtros_de_autor_e_de_acao_recortam_as_operacoes(trilha):
    chefia = next(u["id"] for u in trilha.get("/api/usuarios").json() if u["login"] == "chefia")

    do_autor = trilha.get("/api/relatorios/operacoes", params={"autor": chefia}).json()
    da_acao = trilha.get("/api/relatorios/operacoes", params={"acao": "LOGIN_FALHA"}).json()

    assert [linha["rotulo"] for linha in do_autor["por_usuario"]] == ["Chefia (chefia)"]
    assert do_autor["autor"] == chefia
    assert [linha["chave"] for linha in da_acao["por_acao"]] == ["LOGIN_FALHA"]
    assert da_acao["total"] == 1


def test_datas_invertidas_sao_recusa_e_nao_um_relatorio_vazio(trilha):
    r = trilha.get("/api/relatorios/operacoes", params={"de": "2026-10-10", "ate": "2026-10-01"})

    assert r.status_code == 422
    assert r.json()["detail"]["erro"] == "A data inicial é depois da final."
    assert r.json()["detail"]["ajuda"]


def test_o_csv_das_operacoes_traz_os_tres_agrupamentos_e_o_total(trilha):
    relatorio = trilha.get("/api/relatorios/operacoes").json()

    r = trilha.get("/api/relatorios/operacoes/exportacao.csv")

    linhas = _csv(r)
    assert linhas[0] == ["Agrupamento", "Grupo", "Operações"]
    assert {linha[0] for linha in linhas[1:-1]} == {"Ação", "Usuário", "Dia"}
    assert ["Ação", "Usuário criado", "1"] in linhas
    # A exportação não audita: o total do arquivo é o da tela de antes dele.
    assert linhas[-1] == ["Total", "", str(relatorio["total"])]
    assert "relatorio-operacoes-" in r.headers["content-disposition"]


# ------------------------------------------------------------ quem abre o quê
DA_REDE = [
    "/api/relatorios/campanha/planos",
    "/api/relatorios/desempenho",
    "/api/relatorios/desempenho/exportacao.csv",
    "/api/relatorios/risco",
    "/api/relatorios/risco/exportacao.csv",
    "/api/relatorios/campanha",
    "/api/relatorios/campanha/exportacao.csv",
]
DA_TRILHA = ["/api/relatorios/operacoes", "/api/relatorios/operacoes/exportacao.csv"]


@pytest.mark.parametrize("rota", DA_REDE)
def test_o_administrador_nao_abre_os_relatorios_da_rede(admin, rota):
    assert admin.get(rota).status_code == 403


@pytest.mark.parametrize("rota", DA_TRILHA)
def test_o_gestor_e_o_analista_nao_abrem_o_relatorio_de_operacoes(analista, rota):
    assert analista.get(rota).status_code == 403


def test_o_menu_de_cada_perfil_tem_os_relatorios_que_ele_abre(admin, criar_usuario, autenticar):
    do_admin = admin.get("/api/sessao/atual").json()["telas"]
    criar_usuario(login="gestora", perfil=Perfil.GESTOR)
    autenticar("gestora")
    da_gestora = admin.get("/api/sessao/atual").json()["telas"]

    assert "relatorio_operacoes" in do_admin and "relatorios" not in do_admin
    assert "relatorios" in da_gestora and "relatorio_operacoes" not in da_gestora


def test_os_relatorios_nao_entram_na_trilha(analista, rede):
    """Consulta não audita: a trilha registra o que muda o sistema."""
    antes = _registros()
    analista.get("/api/relatorios/desempenho")
    analista.get("/api/relatorios/desempenho/exportacao.csv")

    assert _registros() == antes


def _registros() -> int:
    s = Sessao()
    try:
        return len(s.scalars(select(Auditoria.id)).all())
    finally:
        s.close()


def test_o_nome_do_parceiro_com_formula_nao_vira_formula_no_csv_do_risco(analista, base):
    base([parceiro("=cmd|' /C calc'!A0", "900.00", previsto="700.00", risco=0.8)])

    linhas = _csv(analista.get("/api/relatorios/risco/exportacao.csv"))

    assert linhas[1][0].startswith("'=cmd")
    s = Sessao()
    try:
        assert s.scalars(select(Parceiro.nome)).one().startswith("=cmd")
    finally:
        s.close()
