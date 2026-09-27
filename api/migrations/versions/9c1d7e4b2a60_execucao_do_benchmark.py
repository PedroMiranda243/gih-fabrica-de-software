"""benchmark: cada execucao, com as medidas cruas de cada modo

Sprint 11 interna, historia H57 (UC09, RF33). O benchmark roda o mesmo problema
sintetico em cada modo de execucao, repetido, em segundo plano e um por vez,
como o otimizador. A tabela guarda o cenario (parceiros, acoes, repeticoes e a
semente), o andamento enquanto roda, e, quando termina, as medidas cruas de
cada modo: o tempo de cada repeticao, e nao so a media, porque o grafico de
escalabilidade junta execucoes de tamanhos diferentes.

Reaproveita o tipo `situacaoexecucao`, criado para o otimizador: as mesmas tres
situacoes. Por isso o downgrade apaga so a tabela, e nao o tipo.

Revision ID: 9c1d7e4b2a60
Revises: f4b7a9c31e20
Create Date: 2026-09-27 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9c1d7e4b2a60'
down_revision: str | None = 'f4b7a9c31e20'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'execucao_benchmark',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'situacao', postgresql.ENUM(name='situacaoexecucao', create_type=False), nullable=False
        ),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuario.id'), nullable=True),
        sa.Column('parceiros', sa.Integer(), nullable=False),
        sa.Column('acoes', sa.Integer(), nullable=False),
        sa.Column('repeticoes', sa.Integer(), nullable=False),
        sa.Column('semente', sa.Integer(), nullable=False),
        sa.Column(
            'iniciada_em',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('concluida_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('progresso', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('resultados', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ambiente', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('disputada', sa.Boolean(), nullable=True),
        sa.Column('motivo', sa.Text(), nullable=True),
        sa.CheckConstraint('parceiros BETWEEN 100 AND 10000', name='ck_benchmark_parceiros'),
        sa.CheckConstraint('acoes BETWEEN 1 AND 10', name='ck_benchmark_acoes'),
        sa.CheckConstraint('repeticoes BETWEEN 1 AND 10', name='ck_benchmark_repeticoes'),
        sa.CheckConstraint(
            "situacao <> 'CONCLUIDA' OR resultados IS NOT NULL",
            name='ck_benchmark_concluido_tem_resultado',
        ),
        sa.CheckConstraint(
            "situacao <> 'FALHOU' OR motivo IS NOT NULL", name='ck_benchmark_falha_tem_motivo'
        ),
    )
    op.create_index(
        'uq_benchmark_um_em_andamento',
        'execucao_benchmark',
        ['situacao'],
        unique=True,
        postgresql_where=sa.text("situacao = 'EM_ANDAMENTO'"),
    )


def downgrade() -> None:
    op.drop_index('uq_benchmark_um_em_andamento', table_name='execucao_benchmark')
    op.drop_table('execucao_benchmark')
