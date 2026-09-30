"""O parceiro no último plano de campanha viável — H81.

A rota liga o cadastro à campanha: quem abre o parceiro vê a ação que o último
plano reserva para ele, e dali abre o plano. O que importa em cada teste é que
"o último plano" seja um plano que existe — concluído **e** viável — e que ficar
de fora dele apareça como informação, e não como erro.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

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

INICIO = datetime(2026, 7, 6, 9, 0, tzinfo=UTC)


@pytest.fixture
def analista(criar_usuario, autenticar, cliente):
    criar_usuario(login="analista", perfil=Perfil.ANALISTA)
    autenticar("analista")
    return cliente


@pytest.fixture
def rede(base):
    return base(
        [
            parceiro("Na Campanha", "900.00", previsto="700.00", risco=0.8),
            parceiro("Fora da Campanha", "1500.00", previsto="1600.00", risco=0.1),
        ]
    )


def _execucao(rede, *, horas=0, viavel=True, situacao=SituacaoExecucao.CONCLUIDA, itens=()):
    """Grava uma execução — e, se viável e concluída, o plano com os itens pedidos.

    `itens` são pares (nome do parceiro, nome da ação). Direto no banco, sem rodar
    o otimizador: o que importa aqui é qual plano é "o último", e não como ele saiu.
    """
    s = Sessao()
    try:
        concluida = situacao == SituacaoExecucao.CONCLUIDA
        execucao = ExecucaoOtimizador(
            situacao=situacao,
            modo=ModoExecucao.SERIAL,
            parametros={"orcamento": "5000.00", "maximo_acoes": 30},
            periodo_base_id=rede.base_id,
            modelo_versao="rede-1",
            semente=42,
            iniciada_em=INICIO + timedelta(hours=horas),
            concluida_em=INICIO + timedelta(hours=horas, minutes=1) if concluida else None,
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
            for nome, acao in itens:
                s.add(
                    ItemPlano(
                        plano_id=plano.id,
                        parceiro_id=rede.parceiros[nome],
                        acao_id=acoes[acao],
                        uplift_esperado=Decimal("123.45"),
                        custo=Decimal("90.00"),
                    )
                )
        s.commit()
        return execucao.id
    finally:
        s.close()


def test_sem_plano_calculado_a_resposta_diz_que_nao_ha_plano(analista, rede):
    r = analista.get(f"/api/parceiros/{rede.parceiros['Na Campanha']}/campanha")

    assert r.status_code == 200
    assert r.json() == {
        "plano": None,
        "no_plano": False,
        "acao": None,
        "custo": None,
        "uplift_esperado": None,
    }


def test_o_parceiro_no_plano_ve_a_acao_o_custo_e_o_ganho_esperado(analista, rede):
    execucao_id = _execucao(rede, itens=[("Na Campanha", "Visita de relacionamento")])

    corpo = analista.get(f"/api/parceiros/{rede.parceiros['Na Campanha']}/campanha").json()

    assert corpo["no_plano"] is True
    assert corpo["acao"] == "Visita de relacionamento"
    assert Decimal(corpo["custo"]) == Decimal("90.00")
    assert Decimal(corpo["uplift_esperado"]) == Decimal("123.45")
    assert corpo["plano"]["execucao_id"] == execucao_id
    assert corpo["plano"]["aplicacao_inicio"] == "2026-07-13"
    assert corpo["plano"]["modelo_versao"] == "rede-1"


def test_quem_ficou_de_fora_ve_o_plano_sem_acao(analista, rede):
    """Ficar de fora é informação: a verba desta rodada foi para outros."""
    execucao_id = _execucao(rede, itens=[("Na Campanha", "Visita de relacionamento")])

    corpo = analista.get(f"/api/parceiros/{rede.parceiros['Fora da Campanha']}/campanha").json()

    assert corpo["no_plano"] is False
    assert corpo["acao"] is None
    assert corpo["plano"]["execucao_id"] == execucao_id


def test_vale_o_plano_mais_recente(analista, rede):
    _execucao(rede, horas=0, itens=[("Na Campanha", "Visita de relacionamento")])
    recente = _execucao(rede, horas=2, itens=[("Fora da Campanha", "Destaque na vitrine")])

    corpo = analista.get(f"/api/parceiros/{rede.parceiros['Na Campanha']}/campanha").json()

    assert corpo["plano"]["execucao_id"] == recente
    assert corpo["no_plano"] is False


@pytest.mark.parametrize(
    "outra",
    [
        {"viavel": False},
        {"situacao": SituacaoExecucao.EM_ANDAMENTO},
    ],
    ids=["inviavel", "em-andamento"],
)
def test_execucao_mais_nova_sem_plano_nao_esconde_o_ultimo_plano(analista, rede, outra):
    """A inviável não tem plano (RN07), e a em andamento ainda não tem: vale o último que existe."""
    viavel = _execucao(rede, horas=0, itens=[("Na Campanha", "Visita de relacionamento")])
    _execucao(rede, horas=3, **outra)

    corpo = analista.get(f"/api/parceiros/{rede.parceiros['Na Campanha']}/campanha").json()

    assert corpo["plano"]["execucao_id"] == viavel
    assert corpo["no_plano"] is True


def test_parceiro_inexistente_responde_404(analista, rede):
    r = analista.get("/api/parceiros/999999/campanha")

    assert r.status_code == 404
