"""O histórico do cadastro do parceiro — história H90, requisito RF50.

O cadastro mostra o que mudou nele, quando e por quem. Sai da trilha de
auditoria, mas só os eventos do próprio parceiro: a trilha inteira continua do
Administrador (RF08).
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db import Sessao
from app.modelos import Auditoria, Perfil


@pytest.fixture
def analista(criar_usuario, autenticar, cliente):
    criar_usuario(login="ana", perfil=Perfil.ANALISTA, nome="Ana Analista")
    autenticar("ana")
    return cliente


def _criar(cliente, nome: str) -> int:
    r = cliente.post("/api/parceiros", json={"nome": nome})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_o_historico_conta_o_que_mudou_quando_e_por_quem(analista):
    parceiro = _criar(analista, "Padaria Lua")
    analista.patch(f"/api/parceiros/{parceiro}", json={"nome": "Padaria Sol"})
    analista.patch(f"/api/parceiros/{parceiro}", json={"ativo": False})

    r = analista.get(f"/api/parceiros/{parceiro}/historico")

    assert r.status_code == 200
    eventos = r.json()
    # Do mais recente para o mais antigo.
    assert [e["acao"] for e in eventos] == [
        "PARCEIRO_DESATIVADO", "PARCEIRO_EDITADO", "PARCEIRO_CRIADO",
    ]
    assert [e["rotulo"] for e in eventos] == [
        "Parceiro desativado", "Cadastro de parceiro editado", "Parceiro cadastrado",
    ]
    # Só a mudança: o nome do parceiro é o título da página em que isso aparece.
    assert [e["resumo"] for e in eventos] == ["", "nome de Padaria Lua para Padaria Sol", ""]
    assert {e["autor"] for e in eventos} == {"Ana Analista"}
    assert all(e["ocorrido_em"] for e in eventos)


def test_o_historico_diz_de_que_categoria_para_qual(analista):
    """Pelo nome que a categoria tinha na hora: o identificador não se lê."""
    padaria = analista.post("/api/categorias", json={"nome": "Padaria"}).json()["id"]
    mercado = analista.post("/api/categorias", json={"nome": "Mercado"}).json()["id"]
    parceiro = _criar(analista, "Pão da Praça")

    analista.patch(f"/api/parceiros/{parceiro}", json={"categoria_id": padaria})
    analista.patch(f"/api/parceiros/{parceiro}", json={"categoria_id": mercado})
    analista.patch(f"/api/parceiros/{parceiro}", json={"categoria_id": None})

    eventos = analista.get(f"/api/parceiros/{parceiro}/historico").json()
    assert [e["resumo"] for e in eventos if e["acao"] == "PARCEIRO_CLASSIFICADO"] == [
        "categoria de Mercado para sem categoria",
        "categoria de Padaria para Mercado",
        "categoria de sem categoria para Padaria",
    ]


def test_o_contato_entra_como_alterado_e_o_valor_fica_fora_da_trilha(analista):
    """O contato é dado de uma pessoa, e a trilha não se apaga: grava-se que
    mudou, e não de quê para quê."""
    parceiro = _criar(analista, "Padaria Lua")

    analista.patch(f"/api/parceiros/{parceiro}", json={"contato": "compras@exemplo.test"})

    evento = analista.get(f"/api/parceiros/{parceiro}/historico").json()[0]
    assert evento["acao"] == "PARCEIRO_EDITADO"
    assert evento["resumo"] == "contato alterado"
    with Sessao() as s:
        gravado = s.scalars(select(Auditoria).where(Auditoria.acao == "PARCEIRO_EDITADO")).one()
    assert gravado.detalhes["contato_alterado"] is True
    assert "compras@exemplo.test" not in str(gravado.detalhes)


def test_so_os_eventos_do_proprio_parceiro(analista):
    """Dois cadastros, e cada histórico com os eventos do seu: o alvo é o id, e
    não o nome — nem um id que só começa igual."""
    um = _criar(analista, "Mercado Um")
    outro = _criar(analista, "Mercado Outro")
    analista.patch(f"/api/parceiros/{outro}", json={"nome": "Mercado Outro Lado"})

    assert [e["acao"] for e in analista.get(f"/api/parceiros/{um}/historico").json()] == [
        "PARCEIRO_CRIADO"
    ]
    assert len(analista.get(f"/api/parceiros/{outro}/historico").json()) == 2


def test_o_historico_nao_traz_a_origem_nem_os_parametros_crus(analista):
    """A trilha inteira é do Administrador. O cadastro mostra a frase; o endereço
    de quem fez e o JSON gravado ficam na auditoria."""
    parceiro = _criar(analista, "Padaria Lua")

    evento = analista.get(f"/api/parceiros/{parceiro}/historico").json()[0]

    assert set(evento) == {"acao", "rotulo", "resumo", "autor", "ocorrido_em"}


def test_parceiro_inexistente_responde_404(analista):
    assert analista.get("/api/parceiros/999999/historico").status_code == 404
