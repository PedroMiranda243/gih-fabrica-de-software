"""Ambiente do Alembic.

A URL do banco vem do `.env` pela configuração da aplicação, nunca do
`alembic.ini` — assim não existe uma segunda fonte de verdade capaz de
apontar para um banco diferente daquele em que a API está trabalhando.
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.modelos  # noqa: F401  — registra as tabelas no metadata
from app.config import config as config_app
from app.db import Base

config = context.config
config.set_main_option("sqlalchemy.url", config_app.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config_app.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    conectavel = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with conectavel.connect() as conexao:
        context.configure(
            connection=conexao,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
