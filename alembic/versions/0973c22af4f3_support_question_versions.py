"""Support question versions

Revision ID: 0973c22af4f3
Revises: 239454175b60
Create Date: 2026-10-21 15:42:36.942665

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0973c22af4f3'
down_revision: Union[str, Sequence[str], None] = '239454175b60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.add_column(
        "assessment_questions",
        sa.Column("version_number", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "assessment_questions",
        sa.Column("is_current", sa.Boolean(), server_default=sa.true(), nullable=False),
    )

    op.drop_constraint(
        "uq_assessment_questions_display_number",
        "assessment_questions",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_assessment_question_slot_version",
        "assessment_questions",
        ["assessment_id", "display_number", "version_number"],
    )

    op.create_check_constraint(
        "ck_assessment_question_version_number",
        "assessment_questions",
        "version_number BETWEEN 1 AND 3",
    )

    op.create_index(
        "uq_assessment_question_current_version",
        "assessment_questions",
        ["assessment_id", "display_number"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_assessment_question_current_version",
        table_name="assessment_questions",
    )

    op.drop_constraint(
        "ck_assessment_question_version_number",
        "assessment_questions",
        type_="check",
    )

    op.drop_constraint(
        "uq_assessment_question_slot_version",
        "assessment_questions",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_assessment_questions_display_number",
        "assessment_questions",
        ["assessment_id", "display_number"],
    )

    op.drop_column("assessment_questions", "is_current")
    op.drop_column("assessment_questions", "version_number")

