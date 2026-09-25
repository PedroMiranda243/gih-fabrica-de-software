"""treino do modelo preditivo, com metricas, versao em uso e pesos

Sprint 05 da disciplina, historias H42 a H45. O RF27 pede que cada treino
registre a data, o volume de dados e as metricas obtidas; o UC07-A1 pede que a
versao so entre em uso se superar as referencias. As duas coisas moram na mesma
linha: a versao em uso depois de um treino e o que o ultimo treino concluido diz.

Tres decisoes que nao sao obvias (ADR-010):

- **Um treino por vez, travado pelo banco**: indice unico parcial sobre os
  treinos em andamento. Trava em memoria nao serve com mais de um processo.
- **Os pesos ficam na linha** (`bytea`): poucos KB, e a versao em uso sobrevive a
  reinicio sem depender de arquivo num volume.
- **Treino concluido tem versao; treino falho tem motivo** — por `CHECK`. Uma
  linha concluida sem versao deixaria a tela sem resposta para "qual modelo esta
  valendo?".

O indice novo em `previsao` atende a leitura da rede toda por periodo e versao;
a unicidade existente comeca por parceiro e nao serve a ela.

Revision ID: d2c9b1a21c53
Revises: b7d4e1f90c23
Create Date: 2026-09-24 21:10:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd2c9b1a21c53'
down_revision: str | None = 'b7d4e1f90c23'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SITUACAO = sa.Enum('EM_ANDAMENTO', 'CONCLUIDO', 'FALHOU', name='situacaotreino')


def upgrade() -> None:
    op.create_table(
        'treino_modelo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('situacao', SITUACAO, nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('periodo_base_id', sa.Integer(), nullable=False),
        sa.Column('semente', sa.Integer(), nullable=False),
        sa.Column('iniciado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('concluido_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('parceiros', sa.Integer(), nullable=True),
        sa.Column('periodos', sa.Integer(), nullable=True),
        sa.Column('amostras_treino', sa.Integer(), nullable=True),
        sa.Column('amostras_validacao', sa.Integer(), nullable=True),
        sa.Column('amostras_teste', sa.Integer(), nullable=True),
        sa.Column('mape_modelo', sa.Float(), nullable=True),
        sa.Column('mape_ultimo', sa.Float(), nullable=True),
        sa.Column('mape_media_movel', sa.Float(), nullable=True),
        sa.Column('brier_modelo', sa.Float(), nullable=True),
        sa.Column('brier_referencia', sa.Float(), nullable=True),
        sa.Column('calibracao_modelo', sa.Float(), nullable=True),
        sa.Column('calibracao_referencia', sa.Float(), nullable=True),
        sa.Column('detalhes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('promovido', sa.Boolean(), nullable=True),
        sa.Column('versao_em_uso', sa.String(length=40), nullable=True),
        sa.Column('motivo', sa.Text(), nullable=True),
        sa.Column('pesos', sa.LargeBinary(), nullable=True),
        sa.CheckConstraint(
            "situacao <> 'CONCLUIDO' OR (versao_em_uso IS NOT NULL AND promovido IS NOT NULL)",
            name='ck_treino_concluido_tem_versao',
        ),
        sa.CheckConstraint("situacao <> 'FALHOU' OR motivo IS NOT NULL", name='ck_treino_falho_tem_motivo'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id']),
        sa.ForeignKeyConstraint(['periodo_base_id'], ['periodo.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'uq_treino_um_em_andamento',
        'treino_modelo',
        ['situacao'],
        unique=True,
        postgresql_where=sa.text("situacao = 'EM_ANDAMENTO'"),
    )
    op.create_index('ix_previsao_periodo_versao', 'previsao', ['periodo_base_id', 'modelo_versao'])


def downgrade() -> None:
    op.drop_index('ix_previsao_periodo_versao', table_name='previsao')
    op.drop_index('uq_treino_um_em_andamento', table_name='treino_modelo')
    op.drop_table('treino_modelo')
    # O `drop_table` nao leva o tipo junto; sem isto, reaplicar a migracao
    # falha com "type already exists" (CLAUDE.md, secao 7).
    SITUACAO.drop(op.get_bind(), checkfirst=True)
