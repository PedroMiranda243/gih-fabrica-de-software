"""A redefinição de senha pelo Administrador e a conta de perfil Parceiro — H93 e H101.

Requisitos: RF54 (redefinir a senha de outra conta), RF56 (achar o parceiro pelo
nome, para o vínculo) e RF04 (o perfil Parceiro). E a #227: o parceiro que não
existe é erro do campo, e não "login em uso" nem erro 500.
"""
from __future__ import annotations

import pytest

from app.config import config
from app.db import Sessao
from app.modelos import Parceiro, Perfil, Usuario
from app.rotas.usuarios import PARCEIROS_NA_BUSCA
from tests.conftest import SENHA_PADRAO

COOKIE = config.sessao_cookie
SENHA_NOVA = "senha-que-o-admin-escolheu"


@pytest.fixture
def admin(criar_usuario, autenticar, cliente):
    criar_usuario(login="chefia", perfil=Perfil.ADMINISTRADOR)
    autenticar("chefia")
    return cliente


@pytest.fixture
def parceiros():
    """Três parceiros, um deles desativado, direto no banco. Devolve nome → id."""
    with Sessao() as s:
        linhas = [
            Parceiro(nome="Empório da Praça"),
            Parceiro(nome="Padaria Praça Nova", ativo=False),
            Parceiro(nome="Mercado do Vale", contato="dono@exemplo.test"),
        ]
        s.add_all(linhas)
        s.commit()
        return {p.nome: p.id for p in linhas}


def _redefinir(admin, usuario_id: int, senha: str = SENHA_NOVA):
    return admin.post(f"/api/usuarios/{usuario_id}/senha", json={"senha_nova": senha})


def _entrar(cliente, login: str, senha: str):
    return cliente.post("/api/sessao", json={"login": login, "senha": senha})


def _trilha(admin, acao: str) -> list[dict]:
    r = admin.get("/api/auditoria", params={"acao": acao})
    assert r.status_code == 200, r.text
    return r.json()["itens"]


# ------------------------------------------------- redefinição de senha (RF54)
def test_o_administrador_redefine_a_senha_e_a_pessoa_entra_com_a_nova(
    admin, cliente, criar_usuario
):
    alvo = criar_usuario(login="esquecida", perfil=Perfil.ANALISTA)

    r = admin.post(f"/api/usuarios/{alvo}/senha", json={"senha_nova": SENHA_NOVA})
    assert r.status_code == 204, r.text

    cliente.cookies.clear()
    antiga = cliente.post("/api/sessao", json={"login": "esquecida", "senha": SENHA_PADRAO})
    assert antiga.status_code == 401
    nova = cliente.post("/api/sessao", json={"login": "esquecida", "senha": SENHA_NOVA})
    assert nova.status_code == 201, nova.text


def test_a_redefinicao_derruba_todas_as_sessoes_da_conta(
    admin, cliente, criar_usuario, autenticar
):
    """Quem trocou a senha não é o dono: nenhuma sessão dele é preservada."""
    alvo = criar_usuario(login="esquecida", perfil=Perfil.ANALISTA)
    cliente.cookies.clear()
    autenticar("esquecida")
    token = cliente.cookies.get(COOKIE)
    assert cliente.get("/api/sessao/atual").status_code == 200

    cliente.cookies.clear()
    autenticar("chefia")
    assert _redefinir(admin, alvo).status_code == 204

    cliente.cookies.set(COOKIE, token)
    assert cliente.get("/api/sessao/atual").status_code == 401


def test_a_redefinicao_entra_na_trilha_sem_a_senha(admin, criar_usuario):
    alvo = criar_usuario(login="esquecida", perfil=Perfil.ANALISTA)
    assert _redefinir(admin, alvo).status_code == 204

    [registro] = _trilha(admin, "SENHA_REDEFINIDA")
    assert registro["rotulo"] == "Senha redefinida pelo administrador"
    assert registro["resumo"].startswith("esquecida")
    assert "sessão(ões) encerrada(s)" in registro["resumo"]
    assert registro["autor"] == "Chefia"
    assert registro["detalhes"]["alvo"] == alvo
    assert SENHA_NOVA not in str(registro)


def test_senha_fraca_na_redefinicao_e_erro_do_campo(admin, criar_usuario):
    alvo = criar_usuario(login="esquecida", perfil=Perfil.ANALISTA)

    r = admin.post(f"/api/usuarios/{alvo}/senha", json={"senha_nova": "123"})

    assert r.status_code == 422, r.text
    [erro] = r.json()["campos"]
    assert erro["campo"] == "senha_nova"
    assert "123" not in r.text


def test_a_propria_senha_nao_se_redefine_por_aqui(admin, cliente):
    """A própria tem o caminho dela, que exige a atual (RF07)."""
    eu = admin.get("/api/sessao/atual").json()["id"]

    r = admin.post(f"/api/usuarios/{eu}/senha", json={"senha_nova": SENHA_NOVA})

    assert r.status_code == 409, r.text
    assert "Minha conta" in r.json()["detail"]["ajuda"]
    cliente.cookies.clear()
    assert _entrar(cliente, "chefia", SENHA_PADRAO).status_code == 201


def test_redefinir_a_senha_de_quem_nao_existe_da_404(admin):
    assert _redefinir(admin, 9999).status_code == 404


@pytest.mark.parametrize("perfil", [Perfil.GESTOR, Perfil.ANALISTA])
def test_so_o_administrador_redefine(cliente, criar_usuario, autenticar, perfil):
    alvo = criar_usuario(login="esquecida", perfil=Perfil.ANALISTA)
    criar_usuario(login="comum", perfil=perfil)
    autenticar("comum")

    r = cliente.post(f"/api/usuarios/{alvo}/senha", json={"senha_nova": SENHA_NOVA})

    assert r.status_code == 403
    cliente.cookies.clear()
    assert _entrar(cliente, "esquecida", SENHA_PADRAO).status_code == 201


# ------------------------------------------- a busca de nomes, para o vínculo (RF56)
def test_a_busca_devolve_so_o_nome_e_a_situacao(admin, parceiros):
    r = admin.get("/api/usuarios/parceiros", params={"busca": "vale"})

    assert r.status_code == 200, r.text
    [achado] = r.json()
    assert achado == {"id": parceiros["Mercado do Vale"], "nome": "Mercado do Vale", "ativo": True}
    # O contato, a categoria e o status comercial são do cadastro, que não é dele.
    assert "exemplo.test" not in r.text


def test_a_busca_ignora_maiuscula_e_acento_e_vem_por_nome(admin, parceiros):
    r = admin.get("/api/usuarios/parceiros", params={"busca": "PRACA"})

    assert [p["nome"] for p in r.json()] == ["Empório da Praça", "Padaria Praça Nova"]
    assert [p["ativo"] for p in r.json()] == [True, False]


@pytest.mark.parametrize("consulta", [{}, {"busca": ""}, {"busca": "a"}])
def test_sem_busca_o_administrador_nao_recebe_a_lista(admin, parceiros, consulta):
    """A rota acha um parceiro pelo nome; a lista de parceiros continua não sendo dele (UC04)."""
    assert admin.get("/api/usuarios/parceiros", params=consulta).status_code == 422


def test_a_busca_para_num_teto(admin):
    with Sessao() as s:
        s.add_all(Parceiro(nome=f"Comércio {i:03d}") for i in range(PARCEIROS_NA_BUSCA + 5))
        s.commit()

    r = admin.get("/api/usuarios/parceiros", params={"busca": "comercio"})

    assert len(r.json()) == PARCEIROS_NA_BUSCA


def test_o_curinga_da_busca_e_texto(admin, parceiros):
    assert admin.get("/api/usuarios/parceiros", params={"busca": "%%"}).json() == []


# --------------------------------------------- a conta de perfil Parceiro (RF04, H101)
def test_cria_a_conta_parceiro_e_a_trilha_diz_de_quem(admin, parceiros):
    r = admin.post(
        "/api/usuarios",
        json={
            "login": "emporio.praca",
            "nome": "Conta do Empório",
            "senha": SENHA_NOVA,
            "perfil": "PARCEIRO",
            "parceiro_id": parceiros["Empório da Praça"],
        },
    )

    assert r.status_code == 201, r.text
    criado = _trilha(admin, "USUARIO_CRIADO")[0]
    assert criado["resumo"] == "emporio.praca, perfil PARCEIRO, do parceiro Empório da Praça"


def test_a_conta_aberta_traz_o_parceiro_pelo_nome(admin, criar_usuario, parceiros):
    conta = criar_usuario(
        login="mercado", perfil=Perfil.PARCEIRO, parceiro_id=parceiros["Mercado do Vale"]
    )
    comum = criar_usuario(login="comum", perfil=Perfil.ANALISTA)

    assert admin.get(f"/api/usuarios/{conta}").json()["parceiro"] == {
        "id": parceiros["Mercado do Vale"], "nome": "Mercado do Vale", "ativo": True,
    }
    assert admin.get(f"/api/usuarios/{comum}").json()["parceiro"] is None


def test_a_conta_parceiro_entra_e_ve_so_o_portal_dela(admin, cliente, parceiros):
    admin.post(
        "/api/usuarios",
        json={"login": "emporio.praca", "nome": "Conta do Empório", "senha": SENHA_NOVA,
              "perfil": "PARCEIRO", "parceiro_id": parceiros["Empório da Praça"]},
    )

    cliente.cookies.clear()
    entrada = cliente.post("/api/sessao", json={"login": "emporio.praca", "senha": SENHA_NOVA})

    assert entrada.status_code == 201, entrada.text
    assert cliente.get("/api/sessao/atual").json()["telas"] == ["meu_desempenho"]


def test_trocar_o_vinculo_registra_o_parceiro_de_antes_e_o_de_depois(
    admin, criar_usuario, parceiros
):
    conta = criar_usuario(
        login="mercado", perfil=Perfil.PARCEIRO, parceiro_id=parceiros["Mercado do Vale"]
    )

    r = admin.patch(f"/api/usuarios/{conta}", json={"parceiro_id": parceiros["Empório da Praça"]})

    assert r.status_code == 200, r.text
    [editado] = _trilha(admin, "USUARIO_EDITADO")
    assert editado["resumo"] == "mercado: parceiro de Mercado do Vale para Empório da Praça"


# -------------------------------------------------- o parceiro que não existe (#227)
def test_criar_com_parceiro_inexistente_e_erro_do_campo_e_nao_login_em_uso(admin):
    r = admin.post(
        "/api/usuarios",
        json={"login": "fantasma", "nome": "Conta Fantasma", "senha": SENHA_NOVA,
              "perfil": "PARCEIRO", "parceiro_id": 999999},
    )

    assert r.status_code == 422, r.text
    [erro] = r.json()["campos"]
    assert (erro["campo"], erro["mensagem"]) == ("parceiro_id", "Parceiro não encontrado.")
    with Sessao() as s:
        assert s.query(Usuario).filter_by(login="fantasma").count() == 0


def test_editar_para_parceiro_inexistente_e_erro_do_campo_e_nao_erro_500(admin, criar_usuario):
    conta = criar_usuario(login="comum", perfil=Perfil.ANALISTA)

    r = admin.patch(f"/api/usuarios/{conta}", json={"perfil": "PARCEIRO", "parceiro_id": 999999})

    assert r.status_code == 422, r.text
    [erro] = r.json()["campos"]
    assert (erro["campo"], erro["mensagem"]) == ("parceiro_id", "Parceiro não encontrado.")
    assert admin.get(f"/api/usuarios/{conta}").json()["perfil"] == "ANALISTA"


def test_o_login_repetido_continua_sendo_login_em_uso(admin, criar_usuario, parceiros):
    criar_usuario(login="emporio.praca", perfil=Perfil.ANALISTA)

    r = admin.post(
        "/api/usuarios",
        json={"login": "emporio.praca", "nome": "Conta do Empório", "senha": SENHA_NOVA,
              "perfil": "PARCEIRO", "parceiro_id": parceiros["Empório da Praça"]},
    )

    assert r.status_code == 409, r.text
    assert "emporio.praca" in r.json()["detail"]["erro"]
