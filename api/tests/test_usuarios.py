"""Testes de gestão de usuários e perfis — histórias H15 e H16.

Requisitos: RF03, RF04 e RNF14 (autorização verificada no servidor).
"""
from __future__ import annotations

import pytest

from app.config import config
from app.db import Sessao
from app.modelos import Perfil, Usuario

COOKIE = config.sessao_cookie
SENHA_NOVA = "senha-de-quem-entra"


@pytest.fixture
def admin(criar_usuario, autenticar, cliente):
    """Um administrador autenticado, que é o pré-requisito de tudo aqui."""
    criar_usuario(login="chefia", perfil=Perfil.ADMINISTRADOR)
    autenticar("chefia")
    return cliente


# ------------------------------------------------------------- autorização
def test_sem_sessao_nao_lista_usuarios(cliente):
    assert cliente.get("/api/usuarios").status_code == 401


@pytest.mark.parametrize("perfil", [Perfil.GESTOR, Perfil.ANALISTA])
def test_perfil_sem_permissao_recebe_403(cliente, criar_usuario, autenticar, perfil):
    """RNF14 e regra 2.5 — a barreira é o servidor, não a interface.

    O frontend nem desenha a tela de usuários para estes perfis; isto prova que
    chamar a rota direto também não funciona.
    """
    criar_usuario(login="comum", perfil=perfil)
    autenticar("comum")

    assert cliente.get("/api/usuarios").status_code == 403
    assert cliente.post("/api/usuarios", json={}).status_code == 403


# ------------------------------------------------------------------- criar
def test_administrador_cria_usuario(admin):
    r = admin.post(
        "/api/usuarios",
        json={
            "login": "nova.analista",
            "nome": "Nova Analista",
            "senha": SENHA_NOVA,
            "perfil": "ANALISTA",
        },
    )

    assert r.status_code == 201, r.text
    corpo = r.json()
    assert corpo["login"] == "nova.analista"
    assert corpo["ativo"] is True
    assert "senha" not in r.text.lower()


def test_usuario_criado_consegue_entrar(admin, cliente):
    admin.post(
        "/api/usuarios",
        json={"login": "novo", "nome": "Novo", "senha": SENHA_NOVA, "perfil": "GESTOR"},
    )
    cliente.delete("/api/sessao")

    r = cliente.post("/api/sessao", json={"login": "novo", "senha": SENHA_NOVA})

    assert r.status_code == 201


def test_login_repetido_e_recusado(admin, criar_usuario):
    criar_usuario(login="ocupado")

    r = admin.post(
        "/api/usuarios",
        json={"login": "ocupado", "nome": "Outro", "senha": SENHA_NOVA, "perfil": "GESTOR"},
    )

    assert r.status_code == 409


def test_login_com_formato_invalido_e_recusado(admin):
    r = admin.post(
        "/api/usuarios",
        json={"login": "Com Espaço", "nome": "Fulano", "senha": SENHA_NOVA, "perfil": "GESTOR"},
    )
    assert r.status_code == 422


def test_senha_fraca_e_recusada_na_criacao(admin):
    r = admin.post(
        "/api/usuarios",
        json={"login": "fraco", "nome": "Fraco", "senha": "123", "perfil": "GESTOR"},
    )
    assert r.status_code == 400


# ------------------------------------------------------------------ perfis
def test_perfil_parceiro_exige_parceiro_vinculado(admin):
    """RF04 e o CHECK do banco: só o perfil Parceiro se vincula a um parceiro."""
    r = admin.post(
        "/api/usuarios",
        json={"login": "parceiro1", "nome": "Parceiro", "senha": SENHA_NOVA, "perfil": "PARCEIRO"},
    )
    assert r.status_code == 422


def test_perfil_nao_parceiro_nao_aceita_vinculo(admin):
    r = admin.post(
        "/api/usuarios",
        json={
            "login": "gestor1",
            "nome": "Gestor",
            "senha": SENHA_NOVA,
            "perfil": "GESTOR",
            "parceiro_id": 1,
        },
    )
    assert r.status_code == 422


def test_troca_de_perfil_vale_na_requisicao_seguinte(admin, cliente, criar_usuario, autenticar):
    """A permissão é lida do usuário a cada requisição, não congelada no login.

    Promover alguém precisa ter efeito agora; rebaixar, mais ainda.
    """
    alvo = criar_usuario(login="promovida", perfil=Perfil.ANALISTA)

    autenticar("promovida")
    assert cliente.get("/api/usuarios").status_code == 403

    # O administrador promove usando a própria sessão, noutro "dispositivo".
    token_analista = cliente.cookies.get(COOKIE)
    cliente.cookies.clear()
    autenticar("chefia")
    assert cliente.patch(
        f"/api/usuarios/{alvo}", json={"perfil": "ADMINISTRADOR"}
    ).status_code == 200

    cliente.cookies.set(COOKIE, token_analista)
    assert cliente.get("/api/usuarios").status_code == 200


# ------------------------------------------------------------------ editar
def test_edita_nome(admin, criar_usuario):
    alvo = criar_usuario(login="alguem", nome="Nome Antigo")

    r = admin.patch(f"/api/usuarios/{alvo}", json={"nome": "Nome Novo"})

    assert r.status_code == 200
    assert r.json()["nome"] == "Nome Novo"


def test_edicao_vazia_e_recusada(admin, criar_usuario):
    alvo = criar_usuario(login="alguem")
    assert admin.patch(f"/api/usuarios/{alvo}", json={}).status_code == 422


def test_usuario_inexistente_da_404(admin):
    assert admin.patch("/api/usuarios/9999", json={"nome": "Fantasma"}).status_code == 404


def test_desativar_derruba_as_sessoes_abertas(admin, cliente, criar_usuario, autenticar):
    """Tirar o acesso precisa valer agora, não no fim da sessão em curso."""
    alvo = criar_usuario(login="afastada")

    cliente.cookies.clear()
    autenticar("afastada")
    token = cliente.cookies.get(COOKIE)
    assert cliente.get("/api/sessao/atual").status_code == 200

    cliente.cookies.clear()
    autenticar("chefia")
    assert admin.patch(f"/api/usuarios/{alvo}", json={"ativo": False}).status_code == 200

    cliente.cookies.set(COOKIE, token)
    assert cliente.get("/api/sessao/atual").status_code == 401


def test_desativado_nao_e_apagado(admin, criar_usuario):
    """A auditoria referencia o autor de cada ação; apagar a linha deixaria a
    trilha apontando para o nada."""
    alvo = criar_usuario(login="afastada")
    admin.patch(f"/api/usuarios/{alvo}", json={"ativo": False})

    s = Sessao()
    try:
        assert s.get(Usuario, alvo) is not None
    finally:
        s.close()


def test_ultimo_administrador_ativo_nao_pode_cair(admin, cliente):
    """Sem esta trava, uma edição distraída deixa o sistema sem ninguém capaz
    de criar usuários — e o RF03 vira impossível sem mexer no banco à mão."""
    eu = cliente.get("/api/sessao/atual").json()["id"]

    assert admin.patch(f"/api/usuarios/{eu}", json={"ativo": False}).status_code == 409
    assert admin.patch(f"/api/usuarios/{eu}", json={"perfil": "ANALISTA"}).status_code == 409


def test_com_outro_administrador_a_alteracao_passa(admin, cliente, criar_usuario):
    eu = cliente.get("/api/sessao/atual").json()["id"]
    criar_usuario(login="reserva", perfil=Perfil.ADMINISTRADOR)

    assert admin.patch(f"/api/usuarios/{eu}", json={"perfil": "ANALISTA"}).status_code == 200


# ------------------------------------------------------------------ listar
def test_lista_e_filtra(admin, criar_usuario):
    criar_usuario(login="ativa", perfil=Perfil.GESTOR)
    criar_usuario(login="inativa", perfil=Perfil.GESTOR, ativo=False)

    todos = admin.get("/api/usuarios").json()
    apenas_ativos = admin.get("/api/usuarios", params={"ativo": True}).json()
    apenas_gestores = admin.get("/api/usuarios", params={"perfil": "GESTOR"}).json()

    assert len(todos) == 3  # os dois acima mais o administrador da fixture
    assert {u["login"] for u in apenas_ativos} == {"chefia", "ativa"}
    assert {u["login"] for u in apenas_gestores} == {"ativa", "inativa"}


def test_listagem_nunca_devolve_o_hash(admin, criar_usuario):
    criar_usuario(login="alguem")

    corpo = admin.get("/api/usuarios").text

    assert "senha" not in corpo.lower()
    assert "argon2" not in corpo.lower()
