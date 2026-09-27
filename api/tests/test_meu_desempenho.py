"""O portal do Parceiro — UC13, RF19, RF26, RNF14, história H39.

O Parceiro vê o próprio histórico e nada da rede: nem outro parceiro, nem
ranking, nem comparação. A rota não recebe identificador de parceiro — ele vem
do vínculo da sessão —, e as rotas da rede o recusam no servidor, com a
tentativa na auditoria.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db import Sessao
from app.modelos import (
    Auditoria,
    Categoria,
    Importacao,
    Metrica,
    OrigemCategoria,
    OrigemImportacao,
    Parceiro,
    Perfil,
    Periodo,
    Usuario,
)

SEMANA = date(2026, 8, 3)


@pytest.fixture
def rede(criar_usuario):
    """Cinco semanas. A Mercearia chega na segunda, falta na quarta e está na quinta;
    o Vizinho está em todas, com números bem maiores."""
    autor = criar_usuario(login="importador", perfil=Perfil.ANALISTA)
    s = Sessao()
    try:
        mercado = Categoria(nome="Mercado")
        s.add(mercado)
        s.flush()
        mercearia = Parceiro(
            nome="Mercearia Boa Vista",
            categoria_id=mercado.id,
            origem_categoria=OrigemCategoria.MANUAL,
        )
        vizinho = Parceiro(nome="Vizinho Grande")
        sem_historico = Parceiro(nome="Recém Cadastrado")
        s.add_all([mercearia, vizinho, sem_historico])
        s.flush()
        valores = {
            1: {vizinho.id: ("9000", 90)},
            2: {vizinho.id: ("9100", 91), mercearia.id: ("1000.00", 20)},
            3: {vizinho.id: ("9200", 92), mercearia.id: ("1200.00", 24)},
            4: {vizinho.id: ("9300", 93)},
            5: {vizinho.id: ("9400", 94), mercearia.id: ("1500.00", 25)},
        }
        for semana, metricas in valores.items():
            inicio = SEMANA + timedelta(days=7 * (semana - 1))
            periodo = Periodo(data_inicio=inicio, data_fim=inicio + timedelta(days=6))
            s.add(periodo)
            s.flush()
            importacao = Importacao(
                periodo_id=periodo.id, usuario_id=autor, origem=OrigemImportacao.TEXTO
            )
            s.add(importacao)
            s.flush()
            for parceiro_id, (faturamento, pedidos) in metricas.items():
                s.add(
                    Metrica(
                        parceiro_id=parceiro_id,
                        periodo_id=periodo.id,
                        importacao_id=importacao.id,
                        faturamento=Decimal(faturamento),
                        pedidos=pedidos,
                    )
                )
        s.commit()
        return {"mercearia": mercearia.id, "vizinho": vizinho.id, "novo": sem_historico.id}
    finally:
        s.close()


@pytest.fixture
def parceiro(rede, criar_usuario, autenticar):
    criar_usuario(login="mercearia", perfil=Perfil.PARCEIRO, parceiro_id=rede["mercearia"])
    return autenticar("mercearia")


def test_o_parceiro_ve_so_o_proprio_historico(rede, parceiro):
    corpo = parceiro.get("/api/meu-desempenho").json()
    assert corpo["parceiro"] == "Mercearia Boa Vista"
    assert corpo["categoria"] == "Mercado"
    # Desde a primeira medição dele: a semana 1, antes de ele chegar, não aparece.
    assert [p["periodo"]["data_inicio"] for p in corpo["pontos"]] == [
        "2026-08-10",
        "2026-08-17",
        "2026-08-24",
        "2026-08-31",
    ]
    assert [p["faturamento"] for p in corpo["pontos"]] == ["1000.00", "1200.00", None, "1500.00"]
    # A semana em que ele faltou é lacuna explícita, e não some (RF19).
    assert corpo["pontos"][2] == {
        "periodo": corpo["pontos"][2]["periodo"],
        "faturamento": None,
        "pedidos": None,
        "ticket_medio": None,
    }
    # Nenhum número do vizinho, em lugar nenhum da resposta.
    assert "9" + "400" not in str(corpo)


def test_nada_de_ranking_nem_de_comparacao_com_a_rede(parceiro):
    """RF26: as chaves da resposta são as dele, e só as dele."""
    corpo = parceiro.get("/api/meu-desempenho").json()
    assert set(corpo) == {"parceiro", "categoria", "atual", "anterior", "variacao", "pontos"}
    assert set(corpo["variacao"]) == {"faturamento", "pedidos", "ticket_medio"}


def test_o_periodo_mais_recente_contra_o_anterior_dele(parceiro):
    corpo = parceiro.get("/api/meu-desempenho").json()
    assert corpo["atual"]["faturamento"] == "1500.00"
    assert corpo["atual"]["ticket_medio"] == "60.00"
    assert corpo["anterior"]["data_inicio"] == "2026-08-24"
    # O anterior é a semana em que ele faltou: não há como dizer a variação.
    assert corpo["variacao"] == {"faturamento": None, "pedidos": None, "ticket_medio": None}


def test_a_variacao_quando_ha_os_dois_periodos(rede, criar_usuario, autenticar):
    """Com a quarta semana preenchida, a quinta se compara a ela."""
    with Sessao() as s:
        quarta = s.scalar(
            select(Periodo).where(Periodo.data_inicio == SEMANA + timedelta(days=21))
        )
        importacao = s.scalar(select(Importacao.id).where(Importacao.periodo_id == quarta.id))
        s.add(
            Metrica(
                parceiro_id=rede["mercearia"],
                periodo_id=quarta.id,
                importacao_id=importacao,
                faturamento=Decimal("1250.00"),
                pedidos=25,
            )
        )
        s.commit()
    criar_usuario(login="mercearia", perfil=Perfil.PARCEIRO, parceiro_id=rede["mercearia"])
    corpo = autenticar("mercearia").get("/api/meu-desempenho").json()
    assert corpo["atual"]["faturamento"] == "1500.00"
    assert corpo["variacao"] == {"faturamento": "20.00", "pedidos": "0.00", "ticket_medio": "20.00"}


def test_sem_historico_ainda_a_serie_vem_vazia(rede, criar_usuario, autenticar):
    """UC13-A1: a tela explica que os dados aparecem depois da primeira importação."""
    criar_usuario(login="novo", perfil=Perfil.PARCEIRO, parceiro_id=rede["novo"])
    corpo = autenticar("novo").get("/api/meu-desempenho").json()
    assert (corpo["pontos"], corpo["atual"], corpo["variacao"]) == ([], None, None)


def test_nao_ha_parametro_para_pedir_outro_parceiro(rede, parceiro):
    """UC13-E1: o parceiro vem da sessão; um `parceiro_id` na URL é ignorado."""
    corpo = parceiro.get("/api/meu-desempenho", params={"parceiro_id": rede["vizinho"]}).json()
    assert corpo["parceiro"] == "Mercearia Boa Vista"


@pytest.mark.parametrize(
    "caminho",
    [
        "/api/parceiros/{vizinho}",
        "/api/painel/series?parceiro_id={vizinho}",
        "/api/painel/ranking",
        "/api/parceiros/{vizinho}/previsao",
    ],
)
def test_os_dados_da_rede_sao_recusados_e_a_tentativa_fica_na_auditoria(rede, parceiro, caminho):
    """UC13-E1 e RNF14: negado no servidor, qualquer que seja o caminho."""
    r = parceiro.get(caminho.format(vizinho=rede["vizinho"]))
    assert r.status_code == 403
    with Sessao() as s:
        negados = [
            a.detalhes["caminho"]
            for a in s.scalars(select(Auditoria).where(Auditoria.acao == "ACESSO_NEGADO"))
        ]
    assert caminho.split("?")[0].format(vizinho=rede["vizinho"]) in negados


@pytest.mark.parametrize("perfil", [Perfil.GESTOR, Perfil.ANALISTA, Perfil.ADMINISTRADOR])
def test_os_outros_perfis_nao_tem_o_portal(rede, criar_usuario, autenticar, perfil):
    criar_usuario(login="outro", perfil=perfil)
    assert autenticar("outro").get("/api/meu-desempenho").status_code == 403


def test_o_parceiro_so_tem_a_tela_dele(parceiro):
    telas = parceiro.get("/api/sessao/atual").json()["telas"]
    assert telas == ["meu_desempenho"]


def test_o_vinculo_e_do_usuario_e_nao_da_requisicao(rede, criar_usuario):
    """O banco só aceita o perfil Parceiro com um parceiro vinculado — o que torna a
    rota incapaz de responder sem saber de quem é o histórico."""
    from sqlalchemy.exc import IntegrityError

    with Sessao() as s:
        s.add(Usuario(login="solto", nome="Solto", senha_hash="x", perfil=Perfil.PARCEIRO))
        with pytest.raises(IntegrityError, match="ck_usuario_parceiro_apenas_perfil_parceiro"):
            s.commit()
