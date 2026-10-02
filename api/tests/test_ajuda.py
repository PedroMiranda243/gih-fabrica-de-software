"""Testes da ajuda — história H95, requisito RF55, caso de uso UC16.

O que o requisito promete é que **os valores das regras exibidos vêm da
configuração em vigor**. Um teste que só conferisse o formato da resposta não
provaria isso; por isso os testes mudam o que está em vigor — o limiar, o
modelo — e conferem que a resposta acompanha.
"""
from __future__ import annotations

import pytest
from gih_modelo import JANELA, PERIODOS_MINIMOS
from sqlalchemy import select

from app.db import Sessao
from app.modelos import Auditoria, Parceiro, Perfil, TreinoModelo
from app.servico_previsao import PREFIXO_REFERENCIA
from tests.rede import parceiro

ROTA = "/api/ajuda/regras"


@pytest.fixture
def entrar(criar_usuario, autenticar, cliente):
    def como(perfil: Perfil, **extra):
        login = f"ajuda-{perfil.value.lower()}"
        criar_usuario(login=login, perfil=perfil, **extra)
        autenticar(login)
        return cliente

    return como


def test_sem_configuracao_gravada_valem_os_limiares_de_fabrica(entrar):
    r = entrar(Perfil.ANALISTA).get(ROTA)

    assert r.status_code == 200
    corpo = r.json()
    assert (corpo["top_n"], corpo["periodos_tendencia"], corpo["periodos_novato"]) == (15, 2, 3)


def test_os_segmentos_vem_na_ordem_de_precedencia_da_rn01(entrar):
    """Em Risco antes de Top: é a ordem em que a regra decide, e não a alfabética."""
    corpo = entrar(Perfil.GESTOR).get(ROTA).json()

    assert corpo["segmentos"] == [
        "PROSPECCAO", "RECEM_CHEGADO", "EM_RISCO", "TOP", "EM_ASCENSAO", "ESTAVEL",
    ]


def test_mudar_o_limiar_na_configuracao_muda_o_que_a_ajuda_diz(entrar):
    """O número da ajuda é o da configuração, e não um texto que se esquece de atualizar."""
    administrador = entrar(Perfil.ADMINISTRADOR)
    assert administrador.get(ROTA).json()["top_n"] == 15

    r = administrador.put(
        "/api/configuracao/segmentacao",
        json={"top_n": 10, "periodos_tendencia": 3, "periodos_novato": 4},
    )
    assert r.status_code == 200

    corpo = administrador.get(ROTA).json()
    assert (corpo["top_n"], corpo["periodos_tendencia"], corpo["periodos_novato"]) == (10, 3, 4)


def test_sem_treino_concluido_a_ajuda_diz_que_nao_ha_modelo_e_quanto_falta_de_historico(entrar):
    """UC16, A2. Os mínimos são os do próprio modelo, e não cópias deles."""
    previsao = entrar(Perfil.GESTOR).get(ROTA).json()["previsao"]

    assert previsao == {
        "versao_em_uso": None,
        "origem": None,
        "periodos_minimos_do_treino": PERIODOS_MINIMOS,
        "periodos_minimos_do_parceiro": JANELA,
    }


def test_com_treino_concluido_a_ajuda_diz_a_versao_em_uso(base, entrar):
    base([parceiro("Alfa", "1000")], top_n=12)

    corpo = entrar(Perfil.GESTOR).get(ROTA).json()

    assert corpo["top_n"] == 12
    assert corpo["previsao"]["versao_em_uso"] == "rede-1"
    assert corpo["previsao"]["origem"] == "MODELO"


def test_versao_de_referencia_e_dita_como_referencia(base, entrar):
    """RN09, item 4: sem rede que supere a referência, a previsão sai da referência."""
    base([parceiro("Alfa", "1000")])
    s = Sessao()
    try:
        treino = s.scalar(select(TreinoModelo))
        treino.versao_em_uso = f"{PREFIXO_REFERENCIA}{treino.id}"
        s.commit()
    finally:
        s.close()

    previsao = entrar(Perfil.ANALISTA).get(ROTA).json()["previsao"]

    assert previsao["versao_em_uso"].startswith(PREFIXO_REFERENCIA)
    assert previsao["origem"] == "REFERENCIA"


def test_o_parceiro_nao_recebe_as_regras_da_rede_e_a_tela_dele_nao_as_pede(entrar):
    """RF26, UC16-A1: a classificação da rede é da operação interna.

    A sessão não lista `ajuda_regras` para o Parceiro — é por ela que a tela de
    ajuda sabe que não deve pedir. Quem pede assim mesmo recebe 403, e a
    tentativa entra na trilha.
    """
    s = Sessao()
    try:
        dono = Parceiro(nome="Parceiro de teste")
        s.add(dono)
        s.commit()
        parceiro_id = dono.id
    finally:
        s.close()
    cliente = entrar(Perfil.PARCEIRO, parceiro_id=parceiro_id)

    assert "ajuda_regras" not in cliente.get("/api/sessao/atual").json()["telas"]

    r = cliente.get(ROTA)
    assert r.status_code == 403
    assert "top_n" not in r.text

    s = Sessao()
    try:
        negados = s.scalars(select(Auditoria).where(Auditoria.acao == "ACESSO_NEGADO")).all()
    finally:
        s.close()
    assert [n.detalhes["caminho"] for n in negados] == [ROTA]


@pytest.mark.parametrize(
    ("perfil", "calcula"),
    [(Perfil.GESTOR, True), (Perfil.ANALISTA, False), (Perfil.ADMINISTRADOR, False)],
    ids=str,
)
def test_a_sessao_diz_quem_calcula_a_campanha_que_e_o_que_a_ajuda_mostra(entrar, perfil, calcula):
    """UC16, passo 2: "o que o perfil pode fazer" sai das telas que o servidor dá.

    O Analista abre a Campanha e não a calcula (UC08). Sem esta capacidade na
    sessão, a ajuda dele diria o mesmo que a do Gestor.
    """
    telas = entrar(perfil).get("/api/sessao/atual").json()["telas"]

    assert ("calcular_campanha" in telas) is calcula
    assert "ajuda_regras" in telas
