"""initial tables: forecasts, knowledge_base, models

Revision ID: 821f93690b12
Revises: 
Create Date: 2026-06-08 12:45:54.634839

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '821f93690b12'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Tables already exist via init.sql. Add IVFFLAT index for pgvector."""
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding "
        "ON knowledge_base USING ivfflat (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("idx_knowledge_base_embedding", table_name="knowledge_base")
