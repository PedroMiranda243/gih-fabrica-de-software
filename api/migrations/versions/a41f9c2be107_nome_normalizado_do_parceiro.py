"""nome normalizado do parceiro, com indice de trigrama

Sprint 6, historia H37. A busca por nome precisa ignorar acento (RF24) e ainda
usar indice: com 10.000 parceiros (RNF04) e 2 s de teto (RNF03), nao cabe
varredura completa.

`unaccent(lower(nome))` na consulta resolveria o acento e **impediria qualquer
indice de servir**, porque a funcao e aplicada linha a linha. Por isso a forma
normalizada vira coluna, e o indice e GIN de trigrama: e o unico que faz
`LIKE '%termo%'` usar indice em posicao qualquer do nome.

A normalizacao esta **copiada** para dentro desta migracao, e nao importada de
`app.texto`. Migracao e retrato de um momento: se ela importasse codigo da
aplicacao, mudar aquela funcao amanha reescreveria o passado. A copia diverge de
proposito no futuro — quem muda a regra precisa escrever outra migracao.

Nao e igual a `unaccent(lower(...))` do Postgres, e a diferenca importa: se o
preenchimento usasse a regra do banco e a aplicacao gravasse com a do Python, a
base ficaria com duas convencoes misturadas e a busca falharia so para alguns
nomes.

Revision ID: a41f9c2be107
Revises: 77b3651bd03d
Create Date: 2026-09-17 17:41:02.118433

"""
import unicodedata
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a41f9c2be107'
down_revision: str | None = '77b3651bd03d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDICE = "ix_parceiro_nome_normalizado_trgm"


def _normalizar(texto: str) -> str:
    """Copia de `app.texto.normalizar`, congelada nesta revisao."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).strip().casefold()


def upgrade() -> None:
    # Disponivel na imagem postgres:16; licenca PostgreSQL, permissiva.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Entra anulavel: as linhas existentes ainda nao tem valor, e NOT NULL
    # falharia antes do preenchimento.
    op.add_column("parceiro", sa.Column("nome_normalizado", sa.String(length=160), nullable=True))

    conexao = op.get_bind()
    parceiros = conexao.execute(sa.text("SELECT id, nome FROM parceiro")).fetchall()
    for identificador, nome in parceiros:
        conexao.execute(
            sa.text("UPDATE parceiro SET nome_normalizado = :valor WHERE id = :id"),
            {"valor": _normalizar(nome), "id": identificador},
        )

    op.alter_column("parceiro", "nome_normalizado", nullable=False)

    op.create_index(
        INDICE,
        "parceiro",
        ["nome_normalizado"],
        postgresql_using="gin",
        postgresql_ops={"nome_normalizado": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_index(INDICE, table_name="parceiro")
    op.drop_column("parceiro", "nome_normalizado")
    # A extensao sai por ultimo: o indice depende do operador que ela instala.
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
