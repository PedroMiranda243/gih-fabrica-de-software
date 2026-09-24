"""Testes de autenticação — histórias H11, H12, H13 e H14.

Requisitos cobertos: RF01, RF02, RNF09, RNF10 e RNF11.
"""
from __future__ import annotations

from app.config import config
from app.db import Sessao
from app.modelos import Perfil, SessaoAcesso, Usuario
from tests.conftest import SENHA_PADRAO

COOKIE = config.sessao_cookie


# --------------------------------------------------------------- H11 · entrar
def test_autentica_com_credenciais_validas(cliente, criar_usuario):
    criar_usuario(login="gestora", perfil=Perfil.GESTOR)

    r = cliente.post("/api/sessao", json={"login": "gestora", "senha": SENHA_PADRAO})

    assert r.status_code == 201, r.text
    assert r.json()["usuario"]["login"] == "gestora"
    assert r.json()["usuario"]["perfil"] == "GESTOR"
    assert cliente.cookies.get(COOKIE)


def test_cookie_de_sessao_tem_as_marcacoes_do_rnf10(cliente, criar_usuario):
    criar_usuario(login="gestora")

    r = cliente.post("/api/sessao", json={"login": "gestora", "senha": SENHA_PADRAO})

    # Lido do cabeçalho bruto, não da jar de cookies: é lá que as marcações
    # existem, e é o cabeçalho que o navegador vê.
    bruto = r.headers["set-cookie"].lower()
    assert "httponly" in bruto
    assert "samesite=lax" in bruto
    assert "path=/" in bruto


def test_senha_errada_e_recusada(cliente, criar_usuario):
    criar_usuario(login="gestora")

    r = cliente.post("/api/sessao", json={"login": "gestora", "senha": "outra-coisa-99"})

    assert r.status_code == 401
    assert not cliente.cookies.get(COOKIE)


def test_usuario_desativado_nao_entra(cliente, criar_usuario):
    criar_usuario(login="afastado", ativo=False)

    r = cliente.post("/api/sessao", json={"login": "afastado", "senha": SENHA_PADRAO})

    assert r.status_code == 401


def test_senha_e_guardada_como_hash_lento(criar_usuario):
    """RNF09 — nenhuma senha em texto claro, e com sal por usuário.

    Dois usuários com a mesma senha precisam ter hashes diferentes; se forem
    iguais, não há sal, e uma tabela pré-calculada quebra os dois de uma vez.
    """
    criar_usuario(login="um")
    criar_usuario(login="dois")

    s = Sessao()
    try:
        hashes = [u.senha_hash for u in s.query(Usuario).order_by(Usuario.login)]
    finally:
        s.close()

    assert all(SENHA_PADRAO not in h for h in hashes)
    assert all(h.startswith("$argon2id$") for h in hashes)
    assert hashes[0] != hashes[1]


def test_resposta_nao_vaza_senha(cliente, criar_usuario):
    criar_usuario(login="gestora")

    r = cliente.post("/api/sessao", json={"login": "gestora", "senha": SENHA_PADRAO})

    corpo = r.text.lower()
    assert "senha" not in corpo
    assert "hash" not in corpo


# --------------------------------------------------------------- H12 · sair
def test_encerrar_invalida_a_sessao_no_servidor(cliente, criar_usuario, autenticar):
    """RF02 — não basta apagar o cookie; quem tem o token na mão precisa cair."""
    criar_usuario(login="gestora")
    autenticar("gestora")
    token = cliente.cookies.get(COOKIE)

    assert cliente.delete("/api/sessao").status_code == 204

    # Devolve o token à jar à mão: o servidor tem que recusar mesmo assim.
    cliente.cookies.set(COOKIE, token)
    assert cliente.get("/api/sessao/atual").status_code == 401


def test_encerrar_remove_o_cookie(cliente, criar_usuario, autenticar):
    criar_usuario(login="gestora")
    autenticar("gestora")

    r = cliente.delete("/api/sessao")

    assert 'gih_sessao=""' in r.headers["set-cookie"] or "gih_sessao=;" in r.headers["set-cookie"]


def test_sem_sessao_nao_se_consulta_nada(cliente):
    assert cliente.get("/api/sessao/atual").status_code == 401


# ------------------------------------------------- H13 · fixação de sessão
def test_novo_login_invalida_o_identificador_anterior(cliente, criar_usuario, autenticar):
    """RNF10 — o identificador é renovado no momento da autenticação.

    É a defesa contra fixação de sessão: quem induz a vítima a usar um
    identificador conhecido não fica com ele depois que ela autentica.
    """
    criar_usuario(login="gestora")
    autenticar("gestora")
    anterior = cliente.cookies.get(COOKIE)

    autenticar("gestora")
    novo = cliente.cookies.get(COOKIE)

    assert novo != anterior

    cliente.cookies.set(COOKIE, anterior)
    assert cliente.get("/api/sessao/atual").status_code == 401


def test_identificador_de_sessao_nao_e_previsivel(cliente, criar_usuario, autenticar):
    criar_usuario(login="gestora")

    tokens = set()
    for _ in range(3):
        autenticar("gestora")
        tokens.add(cliente.cookies.get(COOKIE))

    assert len(tokens) == 3
    assert all(len(t) >= 40 for t in tokens)


def test_banco_guarda_o_hash_do_token_e_nao_o_token(cliente, criar_usuario, autenticar):
    criar_usuario(login="gestora")
    autenticar("gestora")
    token = cliente.cookies.get(COOKIE)

    s = Sessao()
    try:
        guardados = [x.token_hash for x in s.query(SessaoAcesso)]
    finally:
        s.close()

    assert guardados
    assert token not in guardados


# ------------------------------------------------------- H14 · força bruta
def test_bloqueia_apos_cinco_falhas(cliente, criar_usuario):
    """RNF11 — bloqueio temporário após sucessivas falhas da mesma origem."""
    criar_usuario(login="gestora")

    for _ in range(config.login_falhas_para_bloquear):
        r = cliente.post("/api/sessao", json={"login": "gestora", "senha": "errada-mesmo"})
        assert r.status_code == 401

    # A senha agora está certa, e mesmo assim não entra: o bloqueio vem antes
    # da conferência, senão ele não protegeria de nada.
    r = cliente.post("/api/sessao", json={"login": "gestora", "senha": SENHA_PADRAO})
    assert r.status_code == 429


def test_usuario_inexistente_e_senha_errada_respondem_igual(cliente, criar_usuario):
    """RNF11 — respostas indistinguíveis.

    Se diferissem, bastaria varrer uma lista de nomes para descobrir quais
    existem antes de começar a adivinhar senha.
    """
    criar_usuario(login="existe")

    errada = cliente.post("/api/sessao", json={"login": "existe", "senha": "nao-e-essa-1"})
    inexistente = cliente.post("/api/sessao", json={"login": "naoexiste", "senha": "nao-e-essa-1"})

    assert errada.status_code == inexistente.status_code == 401
    assert errada.json() == inexistente.json()


def test_sucesso_zera_o_contador(cliente, criar_usuario):
    """Quem erra, acerta e erra de novo recomeça do zero.

    Sem isso, um usuário desastrado acumularia falhas ao longo do dia e seria
    bloqueado por erros que ele mesmo já corrigiu.
    """
    criar_usuario(login="gestora")

    for _ in range(config.login_falhas_para_bloquear - 1):
        cliente.post("/api/sessao", json={"login": "gestora", "senha": "errada-mesmo"})

    assert cliente.post(
        "/api/sessao", json={"login": "gestora", "senha": SENHA_PADRAO}
    ).status_code == 201

    for _ in range(config.login_falhas_para_bloquear - 1):
        assert cliente.post(
            "/api/sessao", json={"login": "gestora", "senha": "errada-mesmo"}
        ).status_code == 401


def test_o_login_ja_traz_as_telas_do_perfil(cliente, criar_usuario):
    """A interface guarda o usuário que o login devolve. Sem as telas aqui, o
    menu de quem acabou de entrar sairia errado até a página ser recarregada."""
    criar_usuario(login="gestora", perfil=Perfil.GESTOR)

    r = cliente.post("/api/sessao", json={"login": "gestora", "senha": SENHA_PADRAO})

    assert r.status_code == 201
    assert "parceiros" in r.json()["usuario"]["telas"]
    assert "usuarios" not in r.json()["usuario"]["telas"]
