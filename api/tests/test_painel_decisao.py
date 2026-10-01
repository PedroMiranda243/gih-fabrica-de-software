"""A previsão e a campanha dentro do painel — história H83, UC05-A5 (RF28, RF30).

O painel mostra o que os outros dois módulos dizem: o previsto ao lado do medido,
quem tem o maior risco e o resumo do último plano. O que importa em cada teste é
que o painel leia **o mesmo** que o cadastro do parceiro e a campanha leem — a
versão em uso, o último plano viável —, que o previsto e o medido somem os mesmos
parceiros, e que faltar modelo ou plano apareça como informação.
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import event, select
from sqlalchemy.engine import Engine

from app.db import Sessao
from app.modelos import (
    AcaoComercial,
    ExecucaoOtimizador,
    ItemPlano,
    ModoExecucao,
    Perfil,
    PlanoCampanha,
    SituacaoExecucao,
)
from tests.rede import parceiro

CONCLUIDA_EM = datetime(2026, 7, 6, 9, 1, tzinfo=UTC)


@pytest.fixture
def analista(criar_usuario, autenticar, cliente):
    criar_usuario(login="analista", perfil=Perfil.ANALISTA)
    autenticar("analista")
    return cliente


def _rede(base, **extra):
    return base(
        [
            parceiro("Alto Risco", "900.00", previsto="700.00", risco=0.81, categoria="Padaria"),
            parceiro("Medio Risco", "500.00", previsto="520.00", risco=0.40, categoria="Padaria"),
            parceiro("Baixo Risco", "1500.00", previsto="1600.00", risco=0.04, categoria="Mercado"),
            # Sem `previsto`: fatura, mas não tem previsão — fica fora das duas somas.
            parceiro("Sem Previsao", "300.00", categoria="Mercado"),
        ],
        **extra,
    )


def _plano(rede, itens, *, viavel=True) -> int:
    """Uma execução concluída e, se viável, o plano com os itens (parceiro, custo, ganho)."""
    s = Sessao()
    try:
        execucao = ExecucaoOtimizador(
            situacao=SituacaoExecucao.CONCLUIDA,
            modo=ModoExecucao.SERIAL,
            parametros={"orcamento": "5000.00", "maximo_acoes": 30},
            periodo_base_id=rede.base_id,
            modelo_versao="rede-1",
            semente=42,
            iniciada_em=CONCLUIDA_EM,
            concluida_em=CONCLUIDA_EM,
            viavel=viavel,
            restricao_violada=None if viavel else "orcamento",
            tempo_ms=1200,
        )
        s.add(execucao)
        s.flush()
        if viavel:
            plano = PlanoCampanha(
                execucao_id=execucao.id,
                aplicacao_inicio=date(2026, 7, 13),
                aplicacao_fim=date(2026, 7, 19),
            )
            s.add(plano)
            s.flush()
            acao = s.scalars(select(AcaoComercial)).first()
            for nome, custo, ganho in itens:
                s.add(
                    ItemPlano(
                        plano_id=plano.id,
                        parceiro_id=rede.parceiros[nome],
                        acao_id=acao.id,
                        custo=Decimal(custo),
                        uplift_esperado=Decimal(ganho),
                    )
                )
        s.commit()
        return execucao.id
    finally:
        s.close()


# ----------------------------------------------------------------- a previsão
def test_o_previsto_e_o_medido_somam_os_mesmos_parceiros(analista, base):
    """Quem não tem previsão fica fora das **duas** somas. Somar o previsto de
    três contra o medido de quatro faria a rede parecer em queda."""
    rede = _rede(base)

    previsao = analista.get("/api/painel/decisao").json()["previsao"]

    assert previsao["disponivel"] is True
    assert previsao["parceiros"] == 3
    assert previsao["faturamento_previsto"] == "2820.00"  # 700 + 520 + 1600
    assert previsao["faturamento_medido"] == "2900.00"  # 900 + 500 + 1500, sem os 300
    assert previsao["variacao_percentual"] == "-2.76"
    assert previsao["modelo_versao"] == "rede-1"
    assert previsao["origem"] == "MODELO"
    assert previsao["periodo_base"]["id"] == rede.base_id
    assert previsao["desatualizada"] is False


def test_o_maior_risco_vem_primeiro_com_o_medido_e_o_previsto_de_cada_um(analista, base):
    rede = _rede(base)

    maior_risco = analista.get("/api/painel/decisao").json()["previsao"]["maior_risco"]

    assert [p["nome"] for p in maior_risco] == ["Alto Risco", "Medio Risco", "Baixo Risco"]
    primeiro = maior_risco[0]
    assert primeiro["parceiro_id"] == rede.parceiros["Alto Risco"]
    assert primeiro["categoria"] == "Padaria"
    assert primeiro["probabilidade_queda"] == pytest.approx(0.81)
    assert primeiro["faturamento"] == "900.00"
    assert primeiro["faturamento_previsto"] == "700.00"


def test_a_lista_de_maior_risco_tem_teto_e_o_nome_desempata(analista, base):
    base([parceiro(f"Parceiro {i:02d}", "100.00", previsto="90.00", risco=0.5) for i in range(8)])

    maior_risco = analista.get("/api/painel/decisao").json()["previsao"]["maior_risco"]

    assert [p["nome"] for p in maior_risco] == [f"Parceiro {i:02d}" for i in range(5)]


def test_o_risco_do_painel_e_o_mesmo_do_cadastro_do_parceiro(analista, base):
    """Duas escolhas de versão fariam as duas telas mostrarem dois riscos para o mesmo parceiro."""
    rede = _rede(base)

    do_painel = analista.get("/api/painel/decisao").json()["previsao"]["maior_risco"][0]
    do_cadastro = analista.get(f"/api/parceiros/{do_painel['parceiro_id']}/previsao").json()

    assert do_painel["parceiro_id"] == rede.parceiros["Alto Risco"]
    assert do_painel["probabilidade_queda"] == pytest.approx(do_cadastro["probabilidade_queda"])
    assert do_painel["faturamento_previsto"] == do_cadastro["faturamento_previsto"]


def test_sem_modelo_treinado_o_bloco_diz_o_que_falta(analista, base):
    _rede(base, treinado=False)

    previsao = analista.get("/api/painel/decisao").json()["previsao"]

    assert previsao["disponivel"] is False
    assert previsao["motivo"] == "O modelo ainda não foi treinado."
    assert "tela Modelo" in previsao["ajuda"]
    assert previsao["maior_risco"] == []
    assert previsao["faturamento_previsto"] is None


def test_na_categoria_a_previsao_soma_so_a_categoria(analista, base):
    rede = _rede(base)

    corpo = analista.get(
        "/api/painel/decisao", params={"categoria_id": rede.categorias["Padaria"]}
    ).json()

    assert corpo["categoria"]["nome"] == "Padaria"
    assert corpo["previsao"]["parceiros"] == 2
    assert corpo["previsao"]["faturamento_previsto"] == "1220.00"
    assert corpo["previsao"]["faturamento_medido"] == "1400.00"
    assert [p["nome"] for p in corpo["previsao"]["maior_risco"]] == ["Alto Risco", "Medio Risco"]


def test_categoria_sem_previsao_diz_isso_e_ainda_diz_de_que_modelo(analista, base):
    rede = base(
        [
            parceiro("Com Previsao", "900.00", previsto="700.00", risco=0.8, categoria="Padaria"),
            parceiro("Sem Previsao", "300.00", categoria="Mercado"),
        ]
    )

    previsao = analista.get(
        "/api/painel/decisao", params={"categoria_id": rede.categorias["Mercado"]}
    ).json()["previsao"]

    assert previsao["disponivel"] is False
    assert previsao["motivo"] == "Nenhum parceiro deste recorte tem previsão."
    assert previsao["modelo_versao"] == "rede-1"
    assert previsao["periodo_base"]["id"] == rede.base_id


# ----------------------------------------------------------------- a campanha
def test_sem_plano_calculado_o_bloco_diz_que_nao_ha_plano(analista, base):
    _rede(base)

    campanha = analista.get("/api/painel/decisao").json()["campanha"]

    assert campanha == {"plano": None, "acoes": 0, "custo": None, "ganho_esperado": None}


def test_o_resumo_do_ultimo_plano_soma_os_itens_dele(analista, base):
    rede = _rede(base)
    execucao_id = _plano(
        rede, [("Alto Risco", "90.00", "210.50"), ("Baixo Risco", "260.00", "300.00")]
    )

    campanha = analista.get("/api/painel/decisao").json()["campanha"]

    assert campanha["plano"]["execucao_id"] == execucao_id
    assert campanha["plano"]["aplicacao_inicio"] == "2026-07-13"
    assert campanha["plano"]["aplicacao_fim"] == "2026-07-19"
    assert campanha["plano"]["modelo_versao"] == "rede-1"
    assert campanha["acoes"] == 2
    assert campanha["custo"] == "350.00"
    assert campanha["ganho_esperado"] == "510.50"


def test_o_plano_do_painel_e_o_mesmo_do_cadastro_do_parceiro(analista, base):
    rede = _rede(base)
    _plano(rede, [("Alto Risco", "90.00", "210.50")])

    do_painel = analista.get("/api/painel/decisao").json()["campanha"]["plano"]
    do_cadastro = analista.get(
        f"/api/parceiros/{rede.parceiros['Alto Risco']}/campanha"
    ).json()["plano"]

    assert do_painel == do_cadastro


def test_execucao_inviavel_nao_e_o_ultimo_plano(analista, base):
    """Inviável não tem plano (RN07): o painel continua no último que dá para aplicar."""
    rede = _rede(base)
    viavel = _plano(rede, [("Alto Risco", "90.00", "210.50")])
    _plano(rede, [], viavel=False)

    campanha = analista.get("/api/painel/decisao").json()["campanha"]

    assert campanha["plano"]["execucao_id"] == viavel


def test_na_categoria_a_campanha_soma_so_as_acoes_da_categoria(analista, base):
    rede = _rede(base)
    _plano(rede, [("Alto Risco", "90.00", "210.50"), ("Baixo Risco", "260.00", "300.00")])

    campanha = analista.get(
        "/api/painel/decisao", params={"categoria_id": rede.categorias["Padaria"]}
    ).json()["campanha"]

    assert campanha["acoes"] == 1
    assert campanha["custo"] == "90.00"
    assert campanha["ganho_esperado"] == "210.50"


def test_categoria_fora_do_plano_tem_zero_acoes_e_o_plano_continua_la(analista, base):
    rede = _rede(base)
    _plano(rede, [("Baixo Risco", "260.00", "300.00")])

    campanha = analista.get(
        "/api/painel/decisao", params={"categoria_id": rede.categorias["Padaria"]}
    ).json()["campanha"]

    assert campanha["plano"] is not None
    assert campanha["acoes"] == 0
    assert campanha["custo"] == "0.00"
    assert campanha["ganho_esperado"] == "0.00"


# ------------------------------------------------------------ quem vê, e o custo
def test_o_administrador_nao_ve_o_bloco_e_o_menu_dele_diz_isso(
    cliente, criar_usuario, autenticar, base
):
    _rede(base)
    criar_usuario(login="chefia", perfil=Perfil.ADMINISTRADOR)
    autenticar("chefia")

    assert cliente.get("/api/painel/indicadores").status_code == 200
    assert cliente.get("/api/painel/decisao").status_code == 403
    assert "painel_decisao" not in cliente.get("/api/sessao/atual").json()["telas"]


def test_o_gestor_e_o_analista_recebem_o_bloco_nas_telas(analista):
    telas = analista.get("/api/sessao/atual").json()["telas"]

    assert "painel" in telas and "painel_decisao" in telas


@pytest.mark.parametrize("quantos", [5, 60])
def test_o_bloco_nao_faz_uma_consulta_por_parceiro(analista, base, quantos):
    """Somas e uma lista de cinco: o número de consultas não cresce com a rede (RNF03)."""
    rede = base(
        [
            parceiro(f"Parceiro {i:03d}", "100.00", previsto="90.00", risco=i / 100)
            for i in range(quantos)
        ]
    )
    _plano(rede, [(f"Parceiro {i:03d}", "90.00", "10.00") for i in range(5)])

    consultas: list[str] = []

    def anotar(conn, cursor, texto, parametros, contexto, muitos):  # noqa: ANN001
        consultas.append(texto)

    event.listen(Engine, "before_cursor_execute", anotar)
    try:
        r = analista.get("/api/painel/decisao")
    finally:
        event.remove(Engine, "before_cursor_execute", anotar)

    assert r.json()["previsao"]["parceiros"] == quantos
    do_bloco = [
        c for c in consultas if any(t in c.lower() for t in ("previsao", "item_plano", "treino"))
    ]
    assert len(do_bloco) <= 4, f"{len(do_bloco)} consultas para {quantos} parceiros"
