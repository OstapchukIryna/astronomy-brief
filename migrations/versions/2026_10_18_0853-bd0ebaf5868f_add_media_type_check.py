"""add media type check

Revision ID: bd0ebaf5868f
Revises: 5642957c2b5d
Create Date: 2026-10-18 08:53:24.479948+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bd0ebaf5868f"
down_revision: str | Sequence[str] | None = "5642957c2b5d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        op.f("ck_briefs_mediatype"),
        "briefs",
        "media_type IN ('image', 'video', 'other')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f("ck_briefs_mediatype"), "briefs", type_="check")
