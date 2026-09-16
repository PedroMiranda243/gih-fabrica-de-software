"""Preparação do ambiente de teste.

**Os testes rodam contra um Postgres de verdade, num banco separado.** SQLite em
memória seria mais rápido e mentiria: o modelo usa `JSONB` e tipos `ENUM` do
Postgres, e metade das garantias do esquema — os `CHECK`, o índice único — não
existiria. Teste que não exercita a restrição não prova que ela está lá.

O esquema é criado por `alembic upgrade head`, não por `create_all`. Custa alguns
segundos a mais e cobre a divergência entre modelo e migração, que já mordeu este
projeto uma vez (ver a armadilha do ENUM no CLAUDE.md).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

RAIZ_API = Path(__file__).resolve().parent.parent


def _url_base() -> str:
    """De onde sai a URL do banco, na mesma ordem que a aplicação usa.

    Ler o `.env` à mão parece redundante — `app.config` já faz isso — mas
    importá-lo aqui criaria a configuração apontando para o banco de trabalho
    **antes** de a variável de teste existir, e a engine nasceria ligada ao
    banco errado. Um `.env` com outra senha já fez este arquivo tentar entrar
    com a credencial padrão e falhar sem explicar por quê.
    """
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    for arquivo in (RAIZ_API / ".env", RAIZ_API.parent / ".env"):
        if not arquivo.exists():
            continue
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            chave, _, valor = linha.partition("=")
            if chave.strip() == "DATABASE_URL" and valor.strip():
                return valor.strip().strip('"' + "'")

    return "postgresql+psycopg://gih:gih@localhost:5433/gih"


def _url_de_teste() -> str:
    """Mesma instância do banco de desenvolvimento, outro banco.

    O sufixo `_teste` não é enfeite: o `conftest` trunca todas as tabelas entre
    os testes, e apontar isso para o banco de trabalho apagaria a base de
    demonstração de alguém no meio de uma sessão.
    """
    partes = urlsplit(_url_base())
    nome = partes.path.lstrip("/") or "gih"
    return urlunsplit(partes._replace(path=f"/{nome}_teste"))


# Precisa valer **antes** de qualquer import de `app`: a engine é criada no
# import do módulo, lendo a configuração uma única vez.
URL_TESTE = _url_de_teste()
os.environ["DATABASE_URL"] = URL_TESTE

from sqlalchemy import create_engine, text  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.modelos import Perfil, Usuario  # noqa: E402
from app.seguranca import gerar_hash  # noqa: E402

SENHA_PADRAO = "senha-de-teste-123"


def _criar_banco_se_faltar() -> None:
    partes = urlsplit(URL_TESTE)
    nome = partes.path.lstrip("/")
    manutencao = create_engine(
        urlunsplit(partes._replace(path="/postgres")), isolation_level="AUTOCOMMIT"
    )
    with manutencao.connect() as c:
        existe = c.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": nome})
        if not existe:
            # Sem parâmetro: identificador não pode ser bind. O nome vem da
            # nossa própria configuração, nunca de entrada de usuário.
            c.execute(text(f'CREATE DATABASE "{nome}"'))
    manutencao.dispose()


@pytest.fixture(scope="session", autouse=True)
def esquema():
    _criar_banco_se_faltar()

    r = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=RAIZ_API,
        env={**os.environ, "DATABASE_URL": URL_TESTE},
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        pytest.fail(f"Falha ao aplicar as migrações no banco de teste:\n{r.stdout}\n{r.stderr}")
    yield


@pytest.fixture(autouse=True)
def base_limpa(esquema):
    """Cada teste começa com as tabelas vazias.

    `TRUNCATE ... CASCADE` numa instrução só: apagar tabela a tabela esbarraria
    na ordem das chaves estrangeiras. `RESTART IDENTITY` faz os ids recomeçarem,
    o que mantém os testes independentes da ordem em que rodam.
    """
    tabelas = [t.name for t in Base.metadata.sorted_tables]
    with engine.begin() as c:
        c.execute(text(f'TRUNCATE TABLE {", ".join(tabelas)} RESTART IDENTITY CASCADE'))
    yield


@pytest.fixture
def cliente():
    from fastapi.testclient import TestClient

    from app.main import app

    # `raise_server_exceptions=False` faz o TestClient devolver o 500 do
    # tratador em vez de estourar a exceção — que é o que o usuário real vê.
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def criar_usuario():
    """Fábrica de usuários direto no banco, sem passar pela API.

    Preparar o cenário pela própria API tornaria cada teste dependente do
    endpoint de criação — e um defeito ali reprovaria testes que não têm nada a
    ver com isso.
    """
    from app.db import Sessao

    def fabricar(
        login: str = "fulano",
        perfil: Perfil = Perfil.GESTOR,
        senha: str = SENHA_PADRAO,
        ativo: bool = True,
        nome: str | None = None,
    ) -> int:
        s = Sessao()
        try:
            u = Usuario(
                login=login,
                nome=nome or login.capitalize(),
                senha_hash=gerar_hash(senha),
                perfil=perfil,
                ativo=ativo,
            )
            s.add(u)
            s.commit()
            return u.id
        finally:
            s.close()

    return fabricar


@pytest.fixture
def autenticar(cliente):
    """Autentica e devolve o cliente já com o cookie de sessão."""

    def entrar(login: str = "fulano", senha: str = SENHA_PADRAO):
        r = cliente.post("/api/sessao", json={"login": login, "senha": senha})
        assert r.status_code == 201, r.text
        return cliente

    return entrar
