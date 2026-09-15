"""Acesso ao banco.

Toda consulta usa SQLAlchemy com parâmetros — nunca concatenação de entrada do
usuário (RNF13).
"""
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import config

engine = create_engine(config.database_url, pool_pre_ping=True, future=True)
Sessao = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base das entidades. O modelo de dados entra na história H07."""


@contextmanager
def sessao() -> Iterator[Session]:
    """Sessão com commit ao final e rollback em caso de erro.

    A ingestão depende disso: ou o período inteiro entra, ou nada entra (UC03, E2).
    """
    s = Sessao()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
