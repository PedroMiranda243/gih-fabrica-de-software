"""mensagens: o lote de geracao, e o que cada mensagem precisa para ser auditada

Sprint 12 interna, historia H60 (UC10, RF36, RF37; ADR-013). A geracao roda em
segundo plano, um lote por vez, como o otimizador e o benchmark. O lote guarda o
publico pedido, quem entra (resolvido no pedido, para a previa ser o que se
gera) e quem falhou, com o motivo.

Na mensagem entram:
- o lote e o segmento do parceiro quando ela foi gerada (o tom, e o filtro da fila);
- os fatos que o codigo calculou para a redacao, os numeros que o texto pode ter (RN08);
- quem redigiu: o modelo de linguagem, com o nome dele, ou o modelo fixo, com o motivo.

A tabela `mensagem` existe desde o esquema inicial e nunca recebeu linha. Os
valores padrao do servidor existem so para a migracao poder acrescentar colunas
obrigatorias; o codigo sempre as preenche.

Cria o tipo `redatormensagem`, e por isso o downgrade o apaga (CLAUDE.md, 7).
Reaproveita `situacaoexecucao` e `segmento`, que continuam com as tabelas donas.

Revision ID: 3e8a6c1f7b52
Revises: 9c1d7e4b2a60
Create Date: 2026-09-27 14:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3e8a6c1f7b52'
down_revision: str | None = '9c1d7e4b2a60'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REDATOR = postgresql.ENUM('MODELO', 'MODELO_FIXO', name='redatormensagem')


def upgrade() -> None:
    op.create_table(
        'lote_mensagens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'situacao', postgresql.ENUM(name='situacaoexecucao', create_type=False), nullable=False
        ),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuario.id'), nullable=True),
        sa.Column('publico', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('alvos', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('falhas', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('modelo', sa.String(length=60), nullable=True),
        sa.Column(
            'iniciado_em',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('concluido_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('motivo', sa.Text(), nullable=True),
        sa.CheckConstraint(
            "situacao <> 'FALHOU' OR motivo IS NOT NULL",
            name='ck_lote_mensagens_falha_tem_motivo',
        ),
    )
    op.create_index(
        'uq_lote_mensagens_um_em_andamento',
        'lote_mensagens',
        ['situacao'],
        unique=True,
        postgresql_where=sa.text("situacao = 'EM_ANDAMENTO'"),
    )

    REDATOR.create(op.get_bind())
    op.add_column(
        'mensagem',
        sa.Column('lote_id', sa.Integer(), sa.ForeignKey('lote_mensagens.id'), nullable=True),
    )
    op.add_column(
        'mensagem',
        sa.Column(
            'segmento', postgresql.ENUM(name='segmento', create_type=False), nullable=True
        ),
    )
    op.add_column(
        'mensagem',
        sa.Column(
            'fatos',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        'mensagem',
        sa.Column(
            'redator',
            postgresql.ENUM(name='redatormensagem', create_type=False),
            server_default='MODELO_FIXO',
            nullable=False,
        ),
    )
    op.add_column('mensagem', sa.Column('modelo', sa.String(length=60), nullable=True))
    op.add_column(
        'mensagem',
        sa.Column(
            'motivo_redator',
            sa.Text(),
            server_default='Gerada antes do registro de quem redige.',
            nullable=True,
        ),
    )
    # Os padrões só serviam às linhas que já existissem; daqui em diante, o código preenche.
    op.alter_column('mensagem', 'fatos', server_default=None)
    op.alter_column('mensagem', 'redator', server_default=None)
    op.alter_column('mensagem', 'motivo_redator', server_default=None)
    op.create_check_constraint(
        'ck_mensagem_redator_explicado',
        'mensagem',
        "(redator = 'MODELO' AND modelo IS NOT NULL)"
        " OR (redator = 'MODELO_FIXO' AND motivo_redator IS NOT NULL)",
    )
    op.create_index('ix_mensagem_lote', 'mensagem', ['lote_id'])


def downgrade() -> None:
    op.drop_index('ix_mensagem_lote', table_name='mensagem')
    op.drop_constraint('ck_mensagem_redator_explicado', 'mensagem', type_='check')
    op.drop_column('mensagem', 'motivo_redator')
    op.drop_column('mensagem', 'modelo')
    op.drop_column('mensagem', 'redator')
    op.drop_column('mensagem', 'fatos')
    op.drop_column('mensagem', 'segmento')
    op.drop_column('mensagem', 'lote_id')
    REDATOR.drop(op.get_bind())
    op.drop_index('uq_lote_mensagens_um_em_andamento', table_name='lote_mensagens')
    op.drop_table('lote_mensagens')
