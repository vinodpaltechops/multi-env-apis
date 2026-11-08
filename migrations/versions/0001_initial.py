"""initial baseline (no-op)

Revision ID: 0001
Revises:

Migrations MUST be backward compatible (expand/contract): the previous app
version keeps running during rollout and after a rollback.
"""
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
