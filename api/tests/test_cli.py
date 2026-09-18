"""Testes dos comandos de terminal — administrador inicial, criar usuário e
redefinir senha.

É o caminho que faz o `docker compose up` entregar um sistema em que dá para
entrar (RNF07). Se ele quebrar, ninguém percebe pelos testes de API — todos eles
criam os próprios usuários — e o problema só aparece na hora da demonstração.

`criar-usuario` e `redefinir-senha` existem porque a senha sorteada do
administrador só aparece no log da primeira subida, e importação e parceiros
nem são do Administrador: sem eles, quem clonava o projeto parava no login.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app import cli
from app.cli import criar_admin
from app.config import config
from app.db import Sessao
from app.modelos import Auditoria, Perfil, SessaoAcesso, Usuario
from app.seguranca import conferir_senha


def _administradores() -> list[Usuario]:
    s = Sessao()
    try:
        return list(s.scalars(select(Usuario).where(Usuario.perfil == Perfil.ADMINISTRADOR)))
    finally:
        s.close()


def test_cria_o_administrador_quando_a_base_esta_vazia(capsys):
    assert criar_admin() == 0

    admins = _administradores()
    assert len(admins) == 1
    assert admins[0].login == config.admin_login
    assert admins[0].ativo is True


def test_e_idempotente(capsys):
    """O entrypoint roda a cada subida do contêiner.

    Se não fosse idempotente, cada `docker compose up` tentaria criar de novo e
    estouraria no índice único do login — derrubando a API na partida.
    """
    criar_admin()
    capsys.readouterr()

    assert criar_admin() == 0
    assert len(_administradores()) == 1
    assert "já existe" in capsys.readouterr().out


def test_usa_a_senha_do_ambiente_quando_informada(monkeypatch, capsys):
    monkeypatch.setattr(config, "admin_senha", "senha-vinda-do-ambiente")

    criar_admin()

    assert conferir_senha("senha-vinda-do-ambiente", _administradores()[0].senha_hash)
    # A senha veio de fora: não há o que imprimir, e imprimi-la seria vazá-la
    # no log de quem sobe o sistema.
    assert "Senha sorteada" not in capsys.readouterr().out


def test_sem_senha_no_ambiente_sorteia_uma_e_avisa(monkeypatch, capsys):
    """Não existe senha padrão. O repositório é público (regra 2.1), e um
    `admin/admin` no código seria porta aberta em qualquer implantação que
    esquecesse de trocá-la."""
    monkeypatch.setattr(config, "admin_senha", "")

    criar_admin()

    saida = capsys.readouterr().out
    assert "Senha sorteada" in saida

    sorteada = saida.split("Senha sorteada:")[1].splitlines()[0].strip()
    assert len(sorteada) >= 12
    assert conferir_senha(sorteada, _administradores()[0].senha_hash)


def test_o_administrador_criado_consegue_entrar(monkeypatch, cliente):
    """O teste que fecha o ciclo: não basta a linha existir no banco."""
    monkeypatch.setattr(config, "admin_senha", "senha-do-primeiro-acesso")
    criar_admin()

    r = cliente.post(
        "/api/sessao",
        json={"login": config.admin_login, "senha": "senha-do-primeiro-acesso"},
    )

    assert r.status_code == 201
    assert r.json()["usuario"]["perfil"] == "ADMINISTRADOR"


# ========================================================== criar e redefinir
SENHA_BOA = "uma frase longa de verdade"


@pytest.fixture
def senha(monkeypatch):
    """A senha entra pelo ambiente, como numa automação — nunca por argumento."""

    def definir(valor: str = SENHA_BOA):
        monkeypatch.setenv("GIH_SENHA_NOVA", valor)

    definir()
    return definir


def test_cria_usuario_que_consegue_entrar(senha, cliente):
    """O teste que importa: o usuário criado passa do login."""
    assert cli.criar_usuario(["--login", "pedro", "--nome", "Pedro", "--perfil", "GESTOR"]) == 0

    r = cliente.post("/api/sessao", json={"login": "pedro", "senha": SENHA_BOA})

    assert r.status_code == 201
    assert r.json()["usuario"]["perfil"] == "GESTOR"


def test_perfil_padrao_e_gestor(senha):
    """Gestor e Analista são os perfis que usam importação e parceiros (UC03,
    UC04). O padrão cai no que permite testar o produto inteiro."""
    cli.criar_usuario(["--login", "novo", "--nome", "Novo"])

    with Sessao() as s:
        assert s.scalar(select(Usuario.perfil).where(Usuario.login == "novo")) == "GESTOR"


def test_senha_fraca_e_recusada_pela_mesma_regra_da_api(senha):
    """A política vem de `validar_forca`, a mesma da API. Repeti-la aqui faria as
    duas divergirem na primeira mudança."""
    senha("curta")

    assert cli.criar_usuario(["--login", "fraco", "--nome", "Fraco"]) == 1
    with Sessao() as s:
        assert s.scalar(select(Usuario).where(Usuario.login == "fraco")) is None


def test_login_invalido_e_recusado_pelo_esquema_da_api(senha):
    """Login com maiúscula ou espaço é recusado pelo `NovoUsuario`, como na tela."""
    assert cli.criar_usuario(["--login", "Com Espaco", "--nome", "X Y"]) == 1


def test_login_repetido_aponta_para_redefinir(senha, criar_usuario, capsys):
    criar_usuario(login="existente")

    assert cli.criar_usuario(["--login", "existente", "--nome", "Outro"]) == 1
    assert "redefinir-senha" in capsys.readouterr().err


def test_criacao_pelo_terminal_entra_na_auditoria(senha):
    """Criado pelo terminal continua sendo criado — a trilha precisa responder
    de onde veio este usuário."""
    cli.criar_usuario(["--login", "auditado", "--nome", "Auditado"])

    with Sessao() as s:
        registro = s.scalar(select(Auditoria).where(Auditoria.acao == "USUARIO_CRIADO"))
    assert registro.origem == "cli"
    assert registro.detalhes["login"] == "auditado"


def test_sem_terminal_e_sem_variavel_recusa_em_vez_de_travar(monkeypatch):
    """Esperar digitação sem terminal travaria a automação para sempre."""
    monkeypatch.delenv("GIH_SENHA_NOVA", raising=False)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    assert cli.criar_usuario(["--login", "semterminal", "--nome", "Sem"]) == 1


def test_redefinir_troca_a_senha(senha, criar_usuario, cliente):
    criar_usuario(login="esquecido")
    senha("outra frase bem comprida")

    assert cli.redefinir_senha(["--login", "esquecido"]) == 0

    entrada = cliente.post(
        "/api/sessao", json={"login": "esquecido", "senha": "outra frase bem comprida"}
    )
    assert entrada.status_code == 201


def test_redefinir_derruba_as_sessoes_abertas(senha, criar_usuario, autenticar):
    """Senha redefinida com sessão antiga de pé não revogaria o acesso de quem
    motivou a troca — é o mesmo que a troca pela API faz (H19)."""
    criar_usuario(login="comprometido")
    autenticar("comprometido")

    assert cli.redefinir_senha(["--login", "comprometido"]) == 0

    with Sessao() as s:
        abertas = s.scalars(select(SessaoAcesso).where(SessaoAcesso.revogada_em.is_(None))).all()
    assert abertas == []


def test_redefinir_login_inexistente_e_recusado(senha):
    assert cli.redefinir_senha(["--login", "ninguem"]) == 1
