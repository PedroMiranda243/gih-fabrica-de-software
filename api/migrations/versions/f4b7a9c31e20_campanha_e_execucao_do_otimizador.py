"""campanha: efeitos da acao e execucao do otimizador em segundo plano

Sprint 9 interna, historias H48 a H52. Duas mudancas, nas tabelas que o esquema
inicial ja tinha criado e que nenhum codigo tinha usado ainda:

- **`acao_comercial` ganha os dois efeitos da RN10.** O ganho de uma acao soma
  crescimento e perda evitada, e cada parte tem o seu efeito. O antigo
  `uplift_esperado_pct` vira `efeito_crescimento`; entra `efeito_retencao`. Os
  dois passam a `numeric(5,4)`: a API calcula o ganho em centavos inteiros, e
  `float` daria um centavo diferente conforme o arredondamento binario. O custo
  passa a ser positivo, e nao so nao negativo: a violacao de orcamento e medida
  em acoes da mais barata (ADR-011), e acao gratuita dividiria por zero.
- **`execucao_otimizador` passa a registrar uma execucao em segundo plano**, no
  molde do treino do modelo (ADR-010): situacao, inicio e fim, a versao do
  modelo e o periodo das previsoes usadas, a semente, e o resultado so quando
  termina. Um otimizador por vez, travado pelo banco com indice unico parcial.
  Execucao do terminal nao tem autor, e por isso `usuario_id` aceita nulo.

As colunas novas obrigatorias entram sem valor padrao porque a tabela esta
vazia em qualquer banco: nada gravava nela. Se nao estivesse, a migracao falha
alto, em vez de inventar versao de modelo e periodo para execucoes antigas.

Revision ID: f4b7a9c31e20
Revises: d2c9b1a21c53
Create Date: 2026-09-26 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f4b7a9c31e20'
down_revision: str | None = 'd2c9b1a21c53'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SITUACAO = postgresql.ENUM('EM_ANDAMENTO', 'CONCLUIDA', 'FALHOU', name='situacaoexecucao')


def upgrade() -> None:
    # ------------------------------------------------------------ acao_comercial
    op.alter_column(
        'acao_comercial',
        'uplift_esperado_pct',
        type_=sa.Numeric(5, 4),
        existing_type=sa.Float(),
        existing_nullable=False,
        postgresql_using='uplift_esperado_pct::numeric(5,4)',
    )
    op.alter_column('acao_comercial', 'uplift_esperado_pct', new_column_name='efeito_crescimento')
    op.add_column(
        'acao_comercial',
        sa.Column('efeito_retencao', sa.Numeric(5, 4), nullable=False, server_default='0'),
    )
    op.alter_column('acao_comercial', 'efeito_retencao', server_default=None)
    op.drop_constraint('ck_acao_custo_nao_negativo', 'acao_comercial', type_='check')
    op.create_check_constraint('ck_acao_custo_positivo', 'acao_comercial', 'custo_unitario > 0')
    op.create_check_constraint(
        'ck_acao_efeitos_entre_0_e_1',
        'acao_comercial',
        'efeito_crescimento BETWEEN 0 AND 1 AND efeito_retencao BETWEEN 0 AND 1',
    )

    # ------------------------------------------------------- execucao_otimizador
    SITUACAO.create(op.get_bind())
    op.add_column(
        'execucao_otimizador',
        sa.Column(
            'situacao', postgresql.ENUM(name='situacaoexecucao', create_type=False), nullable=False
        ),
    )
    op.alter_column('execucao_otimizador', 'usuario_id', existing_type=sa.Integer(), nullable=True)
    op.alter_column('execucao_otimizador', 'executada_em', new_column_name='iniciada_em')
    op.add_column(
        'execucao_otimizador', sa.Column('concluida_em', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column('execucao_otimizador', sa.Column('periodo_base_id', sa.Integer(), nullable=False))
    op.create_foreign_key(
        'fk_execucao_otimizador_periodo_base',
        'execucao_otimizador',
        'periodo',
        ['periodo_base_id'],
        ['id'],
    )
    op.add_column('execucao_otimizador', sa.Column('modelo_versao', sa.String(40), nullable=False))
    op.add_column('execucao_otimizador', sa.Column('semente', sa.Integer(), nullable=False))
    op.add_column('execucao_otimizador', sa.Column('parcial', sa.Boolean(), nullable=True))
    op.add_column('execucao_otimizador', sa.Column('motivo', sa.Text(), nullable=True))
    op.add_column(
        'execucao_otimizador',
        sa.Column('detalhes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    # Enquanto roda, ainda não há resultado nem tempo.
    op.alter_column('execucao_otimizador', 'viavel', existing_type=sa.Boolean(), nullable=True)
    op.alter_column('execucao_otimizador', 'tempo_ms', existing_type=sa.Integer(), nullable=True)
    op.create_check_constraint(
        'ck_execucao_concluida_tem_resultado',
        'execucao_otimizador',
        "situacao <> 'CONCLUIDA' OR (viavel IS NOT NULL AND tempo_ms IS NOT NULL)",
    )
    op.create_check_constraint(
        'ck_execucao_falha_tem_motivo',
        'execucao_otimizador',
        "situacao <> 'FALHOU' OR motivo IS NOT NULL",
    )
    op.create_index(
        'uq_execucao_uma_em_andamento',
        'execucao_otimizador',
        ['situacao'],
        unique=True,
        postgresql_where=sa.text("situacao = 'EM_ANDAMENTO'"),
    )


def downgrade() -> None:
    # O esquema anterior nao representa execucao sem autor (terminal), sem
    # resultado (em andamento ou falha) nem sem tempo. Sem apaga-las, o
    # `SET NOT NULL` abaixo falha, e com ele o `resetar_banco.py`, que reverte
    # tudo ate a base. Plano so existe para execucao concluida e viavel.
    op.execute(
        'DELETE FROM item_plano WHERE plano_id IN (SELECT p.id FROM plano_campanha p'
        ' JOIN execucao_otimizador e ON e.id = p.execucao_id WHERE e.usuario_id IS NULL)'
    )
    op.execute(
        'DELETE FROM plano_campanha WHERE execucao_id IN'
        ' (SELECT id FROM execucao_otimizador WHERE usuario_id IS NULL)'
    )
    op.execute(
        'DELETE FROM execucao_otimizador'
        ' WHERE usuario_id IS NULL OR viavel IS NULL OR tempo_ms IS NULL'
    )
    op.drop_index('uq_execucao_uma_em_andamento', table_name='execucao_otimizador')
    op.drop_constraint('ck_execucao_falha_tem_motivo', 'execucao_otimizador', type_='check')
    op.drop_constraint('ck_execucao_concluida_tem_resultado', 'execucao_otimizador', type_='check')
    op.alter_column('execucao_otimizador', 'tempo_ms', existing_type=sa.Integer(), nullable=False)
    op.alter_column('execucao_otimizador', 'viavel', existing_type=sa.Boolean(), nullable=False)
    op.drop_column('execucao_otimizador', 'detalhes')
    op.drop_column('execucao_otimizador', 'motivo')
    op.drop_column('execucao_otimizador', 'parcial')
    op.drop_column('execucao_otimizador', 'semente')
    op.drop_column('execucao_otimizador', 'modelo_versao')
    op.drop_constraint(
        'fk_execucao_otimizador_periodo_base', 'execucao_otimizador', type_='foreignkey'
    )
    op.drop_column('execucao_otimizador', 'periodo_base_id')
    op.drop_column('execucao_otimizador', 'concluida_em')
    op.alter_column('execucao_otimizador', 'iniciada_em', new_column_name='executada_em')
    op.alter_column('execucao_otimizador', 'usuario_id', existing_type=sa.Integer(), nullable=False)
    op.drop_column('execucao_otimizador', 'situacao')
    # O `drop_column` nao leva o tipo junto; sem isto, reaplicar a migracao
    # falha com "type already exists" (CLAUDE.md, secao 7).
    SITUACAO.drop(op.get_bind(), checkfirst=True)

    op.drop_constraint('ck_acao_efeitos_entre_0_e_1', 'acao_comercial', type_='check')
    op.drop_constraint('ck_acao_custo_positivo', 'acao_comercial', type_='check')
    op.create_check_constraint(
        'ck_acao_custo_nao_negativo', 'acao_comercial', 'custo_unitario >= 0'
    )
    op.drop_column('acao_comercial', 'efeito_retencao')
    op.alter_column('acao_comercial', 'efeito_crescimento', new_column_name='uplift_esperado_pct')
    op.alter_column(
        'acao_comercial',
        'uplift_esperado_pct',
        type_=sa.Float(),
        existing_type=sa.Numeric(5, 4),
        existing_nullable=False,
        postgresql_using='uplift_esperado_pct::double precision',
    )
