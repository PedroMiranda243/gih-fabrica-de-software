"""sessao de acesso e tentativas de login

Sprint 4. Duas tabelas que a autenticação precisa:

- `sessao_acesso` — estado da sessão no servidor, exigência do RF02 ("invalidando-a
  no servidor"). Guarda o hash do identificador, nunca ele próprio.
- `tentativa_login` — base do bloqueio por força bruta do RNF11. O login é texto
  livre e não chave estrangeira: tentativa contra usuário inexistente também conta.

Nenhum tipo ENUM é criado aqui, então o `downgrade` automático basta — ver a
armadilha do `DROP TYPE` no CLAUDE.md, que vale para as migrações que criam enum.

Revision ID: 77b3651bd03d
Revises: e5c1502cf678
Create Date: 2026-09-15 23:31:25.991711

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '77b3651bd03d'
down_revision: str | None = 'e5c1502cf678'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('tentativa_login',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('login', sa.String(length=60), nullable=False),
    sa.Column('origem', sa.String(length=45), nullable=False),
    sa.Column('sucesso', sa.Boolean(), nullable=False),
    sa.Column('ocorrido_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tentativa_origem_ocorrido', 'tentativa_login', ['origem', 'ocorrido_em'], unique=False)
    op.create_table('sessao_acesso',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('criada_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('expira_em', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revogada_em', sa.DateTime(timezone=True), nullable=True),
    sa.Column('motivo_revogacao', sa.String(length=40), nullable=True),
    sa.Column('origem', sa.String(length=45), nullable=True),
    sa.Column('agente', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_index('ix_sessao_acesso_usuario', 'sessao_acesso', ['usuario_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_sessao_acesso_usuario', table_name='sessao_acesso')
    op.drop_table('sessao_acesso')
    op.drop_index('ix_tentativa_origem_ocorrido', table_name='tentativa_login')
    op.drop_table('tentativa_login')
