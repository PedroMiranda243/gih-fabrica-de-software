"""configuracao da segmentacao, com os limiares de RN01

Sprint 7, historia H34. A RF21 pede que o tamanho do Top N, o numero de periodos
de queda para caracterizar risco e o numero de periodos para caracterizar
parceiro novo mudem **sem alteracao de codigo**.

Uma linha so, garantida por `CHECK id = 1`. Configuracao global sem essa trava
vira duas linhas na primeira gravacao concorrente, e a regra passa a depender de
qual delas o `SELECT` devolver primeiro — defeito que nao quebra nada na hora e
classifica errado para sempre.

Os tres valores estao **escritos aqui**, e nao importados de
`app.servico_segmentacao`. Migracao e retrato de um momento: se ela importasse o
codigo da aplicacao, mudar o padrao amanha reescreveria o passado. Hoje eles
coincidem com `Limiares()`; divergir e o comportamento correto.

De onde vem cada um:

- `top_n = 15` — "Top 15" esta em `docs/01-visao-do-produto.md`, no problema e no
  glossario, e e o que o prototipo aprovado mostra
- `periodos_tendencia = 2` — RN01, com essas palavras: "queda de faturamento em
  2 ou mais periodos consecutivos"
- `periodos_novato = 3` — **nao esta em docs/**; vem da premissa de
  `docs/01-visao-do-produto.md` secao 6, e a lacuna esta aberta na issue #59

Revision ID: b7d4e1f90c23
Revises: a41f9c2be107
Create Date: 2026-09-20 03:05:11.204817

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b7d4e1f90c23'
down_revision: str | None = 'a41f9c2be107'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELA = "configuracao_segmentacao"


def upgrade() -> None:
    op.create_table(
        TABELA,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("top_n", sa.Integer(), nullable=False),
        sa.Column("periodos_tendencia", sa.Integer(), nullable=False),
        sa.Column("periodos_novato", sa.Integer(), nullable=False),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("atualizado_por_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["atualizado_por_id"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("id = 1", name="ck_configuracao_linha_unica"),
        sa.CheckConstraint("top_n >= 1", name="ck_configuracao_top_n"),
        sa.CheckConstraint("periodos_tendencia >= 1", name="ck_configuracao_tendencia"),
        sa.CheckConstraint("periodos_novato >= 1", name="ck_configuracao_novato"),
    )

    # A linha nasce com a migracao, e nao na primeira leitura da aplicacao:
    # criar sob demanda daria duas gravacoes concorrentes na primeira subida com
    # mais de um processo, e o `CHECK` recusaria a segunda com erro 500 numa
    # rota de leitura.
    op.execute(
        sa.text(
            f"INSERT INTO {TABELA} (id, top_n, periodos_tendencia, periodos_novato)"
            " VALUES (1, 15, 2, 3)"
        )
    )


def downgrade() -> None:
    op.drop_table(TABELA)
