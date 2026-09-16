"""Testes do administrador inicial.

É o caminho que faz o `docker compose up` entregar um sistema em que dá para
entrar (RNF07). Se ele quebrar, ninguém percebe pelos testes de API — todos eles
criam os próprios usuários — e o problema só aparece na hora da demonstração.
"""
from __future__ import annotations

from sqlalchemy import select

from app.cli import criar_admin
from app.config import config
from app.db import Sessao
from app.modelos import Perfil, Usuario
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
