"""auditoria: os indices dos filtros da tela e do historico do parceiro

Sprint 07 da disciplina, historias H89 e H90 (UC14, RF08, RF49, RF50). A trilha
so cresce: recebe uma linha por login, por importacao, por execucao do
otimizador e por decisao de mensagem. Ate aqui ela so era lida pela API, sempre
pela data; com a tela, passa a ser filtrada por acao e por autor, e o cadastro
do parceiro le os eventos dele.

Tres indices:
- por acao e por autor, cada um com o momento, que e a ordenacao da lista;
- pelo alvo dentro do JSON (`detalhes->>'alvo'`), para o historico de um
  cadastro: a consulta compara como texto, que e a expressao indexada.

Nenhuma coluna muda, e nenhum dado: o downgrade so remove os indices.

Revision ID: 5b2e9d47a1c8
Revises: 3e8a6c1f7b52
Create Date: 2026-10-01 05:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5b2e9d47a1c8'
down_revision: str | None = '3e8a6c1f7b52'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index('ix_auditoria_acao', 'auditoria', ['acao', 'ocorrido_em'])
    op.create_index('ix_auditoria_usuario', 'auditoria', ['usuario_id', 'ocorrido_em'])
    op.create_index('ix_auditoria_alvo', 'auditoria', [sa.text("(detalhes->>'alvo')")])


def downgrade() -> None:
    op.drop_index('ix_auditoria_alvo', table_name='auditoria')
    op.drop_index('ix_auditoria_usuario', table_name='auditoria')
    op.drop_index('ix_auditoria_acao', table_name='auditoria')
