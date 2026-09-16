"""Testes da trilha de auditoria — história H18, requisitos RF06 e RF08."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.auditoria import Acao
from app.modelos import Perfil
from tests.conftest import SENHA_PADRAO


@pytest.fixture
def admin(criar_usuario, autenticar, cliente):
    criar_usuario(login="chefia", perfil=Perfil.ADMINISTRADOR)
    autenticar("chefia")
    return cliente


def _acoes(resposta) -> list[str]:
    return [i["acao"] for i in resposta.json()["itens"]]


# ------------------------------------------------------------- autorização
def test_apenas_administrador_consulta(cliente, criar_usuario, autenticar):
    criar_usuario(login="comum", perfil=Perfil.GESTOR)
    autenticar("comum")

    assert cliente.get("/api/auditoria").status_code == 403


def test_sem_sessao_nao_consulta(cliente):
    assert cliente.get("/api/auditoria").status_code == 401


# ------------------------------------------------------------- o que registra
def test_login_bem_sucedido_entra_na_trilha(admin):
    r = admin.get("/api/auditoria", params={"acao": "LOGIN_SUCESSO"})

    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_login_recusado_entra_na_trilha(cliente, criar_usuario, autenticar):
    """**O caso que mais importa.**

    A auditoria grava em transação própria justamente por isto: a falha de login
    termina em 401, e se o registro participasse da mesma transação o
    `rollback` o levaria junto — a trilha só teria sucessos.
    """
    criar_usuario(login="chefia", perfil=Perfil.ADMINISTRADOR)
    cliente.post("/api/sessao", json={"login": "chefia", "senha": "senha-errada-aqui"})

    autenticar("chefia")
    r = cliente.get("/api/auditoria", params={"acao": "LOGIN_FALHA"})

    assert r.json()["total"] == 1


def test_tentativa_com_login_inexistente_tambem_e_registrada(cliente, criar_usuario, autenticar):
    criar_usuario(login="chefia", perfil=Perfil.ADMINISTRADOR)
    cliente.post("/api/sessao", json={"login": "ninguem", "senha": "chute-qualquer-1"})

    autenticar("chefia")
    r = cliente.get("/api/auditoria", params={"acao": "LOGIN_FALHA"})

    registro = r.json()["itens"][0]
    assert registro["usuario_id"] is None  # não existe usuário para apontar
    assert registro["detalhes"]["login"] == "ninguem"


def test_acesso_negado_entra_na_trilha(cliente, criar_usuario, autenticar):
    criar_usuario(login="comum", perfil=Perfil.GESTOR)
    criar_usuario(login="chefia", perfil=Perfil.ADMINISTRADOR)

    autenticar("comum")
    cliente.get("/api/usuarios")  # 403

    cliente.cookies.clear()
    autenticar("chefia")
    r = cliente.get("/api/auditoria", params={"acao": "ACESSO_NEGADO"})

    assert r.json()["total"] == 1
    assert r.json()["itens"][0]["detalhes"]["caminho"] == "/api/usuarios"


def test_alteracao_de_usuario_entra_na_trilha(admin, criar_usuario):
    alvo = criar_usuario(login="alguem", perfil=Perfil.ANALISTA)
    admin.patch(f"/api/usuarios/{alvo}", json={"perfil": "GESTOR"})

    r = admin.get("/api/auditoria", params={"acao": "PERFIL_ALTERADO"})

    detalhes = r.json()["itens"][0]["detalhes"]
    assert detalhes["de"] == "ANALISTA"
    assert detalhes["para"] == "GESTOR"


def test_trilha_nunca_guarda_senha(admin, criar_usuario):
    """RF08 deixa a trilha visível ao administrador; gravar segredo aqui seria
    transformar o registro de segurança em brecha de segurança."""
    admin.post(
        "/api/usuarios",
        json={"login": "novo", "nome": "Novo", "senha": SENHA_PADRAO, "perfil": "GESTOR"},
    )

    corpo = admin.get("/api/auditoria", params={"tamanho": 200}).text

    assert SENHA_PADRAO not in corpo
    assert "senha_hash" not in corpo
    assert "token" not in corpo


# ------------------------------------------------------------------ filtros
def test_filtra_por_autor(admin, cliente, criar_usuario, autenticar):
    outro = criar_usuario(login="segunda", perfil=Perfil.ADMINISTRADOR)
    cliente.cookies.clear()
    autenticar("segunda")

    r = cliente.get("/api/auditoria", params={"autor": outro})

    assert r.json()["total"] >= 1
    assert all(i["usuario_id"] == outro for i in r.json()["itens"])


def test_filtra_por_intervalo_de_datas(admin):
    hoje = date.today()

    de_hoje = admin.get("/api/auditoria", params={"de": hoje.isoformat(), "ate": hoje.isoformat()})
    de_ontem = admin.get(
        "/api/auditoria",
        params={
            "de": (hoje - timedelta(days=2)).isoformat(),
            "ate": (hoje - timedelta(days=1)).isoformat(),
        },
    )

    # "até hoje" precisa incluir o dia de hoje inteiro. Comparar com o início do
    # dia excluiria tudo o que acabou de acontecer — que é o erro fácil aqui.
    assert de_hoje.json()["total"] >= 1
    assert de_ontem.json()["total"] == 0


def test_pagina_os_resultados(admin, criar_usuario):
    for i in range(6):
        criar_usuario(login=f"pessoa{i}", perfil=Perfil.ANALISTA)
        admin.patch(f"/api/usuarios/{i + 2}", json={"nome": f"Nome {i}"})

    primeira = admin.get("/api/auditoria", params={"pagina": 1, "tamanho": 3})
    segunda = admin.get("/api/auditoria", params={"pagina": 2, "tamanho": 3})

    assert len(primeira.json()["itens"]) == 3
    assert primeira.json()["total"] > 3
    ids_primeira = {i["id"] for i in primeira.json()["itens"]}
    ids_segunda = {i["id"] for i in segunda.json()["itens"]}
    assert not (ids_primeira & ids_segunda)


def test_tamanho_de_pagina_tem_teto(admin):
    """Sem teto, `?tamanho=999999` devolve a tabela inteira e derruba a API."""
    assert admin.get("/api/auditoria", params={"tamanho": 10_000}).status_code == 422


def test_ordena_do_mais_recente_para_o_mais_antigo(admin, criar_usuario):
    alvo = criar_usuario(login="alguem")
    admin.patch(f"/api/usuarios/{alvo}", json={"nome": "Depois"})

    acoes = _acoes(admin.get("/api/auditoria"))

    # A investigação começa pelo que acabou de acontecer.
    assert acoes[0] == Acao.USUARIO_EDITADO
    assert acoes[-1] == Acao.LOGIN_SUCESSO


def test_lista_as_acoes_possiveis_para_o_filtro(admin):
    """Vem do enum, não de um SELECT DISTINCT: a opção precisa existir mesmo que
    nunca tenha ocorrido — que é o caso mais interessante de procurar."""
    r = admin.get("/api/auditoria/acoes")

    assert r.status_code == 200
    assert "USUARIO_DESATIVADO" in r.json()
