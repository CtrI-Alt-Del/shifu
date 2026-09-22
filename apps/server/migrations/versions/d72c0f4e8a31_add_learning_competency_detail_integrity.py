"""Add Learning competency detail integrity metadata and hard-score snapshots.

Revision ID: d72c0f4e8a31
Revises: c4d82f1e7a30
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'd72c0f4e8a31'
down_revision: str | None = 'c4d82f1e7a30'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'learning_competency_progresses',
        sa.Column('hard_activity_score', sa.Numeric(precision=5, scale=2)),
    )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM learning_competency_progresses
                    GROUP BY skill_experience_id, competency_id
                    HAVING COUNT(*) > 1
                ) THEN
                    RAISE EXCEPTION
                        'Cannot add competency progress uniqueness: duplicate semantic rows exist';
                END IF;
            END $$;
            """
        )
    )
    connection.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM learning_skill_experiences
                    GROUP BY goal_id, skill_id
                    HAVING COUNT(*) > 1
                ) THEN
                    RAISE EXCEPTION
                        'Cannot add skill experience uniqueness: duplicate goal/skill rows exist';
                END IF;
            END $$;
            """
        )
    )
    connection.execute(
        sa.text(
            """
            UPDATE learning_competency_progresses AS progress
            SET hard_activity_score = mastered_scores.max_score
            FROM (
                SELECT
                    progress.id,
                    MAX(evaluation.score) AS max_score
                FROM learning_competency_progresses AS progress
                JOIN learning_activity_attempts AS attempt
                  ON attempt.skill_experience_id = progress.skill_experience_id
                 AND attempt.competency_id = progress.competency_id
                 AND attempt.kind = 'learning'
                JOIN learning_activity_evaluations AS evaluation
                  ON evaluation.attempt_id = attempt.id
                 AND evaluation.status = 'completed'
                 AND evaluation.score IS NOT NULL
                JOIN curriculum_sequences AS sequence
                  ON sequence.competency_id = progress.competency_id
                JOIN LATERAL json_array_elements(sequence.items) AS item(value)
                  ON TRUE
                JOIN curriculum_activities AS activity
                  ON activity.id = item.value ->> 'activity_id'
                 AND attempt.activity_id = activity.id
                 AND activity.difficulty = 'hard'
                WHERE progress.status = 'mastered'
                  AND evaluation.completed_at IS NOT NULL
                GROUP BY progress.id
            ) AS mastered_scores
            WHERE progress.id = mastered_scores.id;
            """
        )
    )
    connection.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM learning_competency_progresses
                    WHERE status = 'mastered'
                      AND (
                          current_progress IS NULL
                          OR current_progress < 85
                          OR hard_activity_score IS NULL
                          OR hard_activity_score < 80
                          OR mastered_at IS NULL
                      )
                ) THEN
                    RAISE EXCEPTION
                        'Cannot preserve mastered competency invariants during migration';
                END IF;
            END $$;
            """
        )
    )

    op.create_check_constraint(
        'ck_learning_competency_progress_hard_score',
        'learning_competency_progresses',
        'hard_activity_score >= 0 AND hard_activity_score <= 100',
    )
    op.create_unique_constraint(
        'uq_learning_competency_progress_experience_competency',
        'learning_competency_progresses',
        ['skill_experience_id', 'competency_id'],
    )
    op.create_index(
        'ix_learning_competency_progress_experience_competency',
        'learning_competency_progresses',
        ['skill_experience_id', 'competency_id'],
    )
    op.create_unique_constraint(
        'uq_learning_skill_experience_goal_skill',
        'learning_skill_experiences',
        ['goal_id', 'skill_id'],
    )
    op.create_index(
        'ix_learning_skill_experience_goal_id',
        'learning_skill_experiences',
        ['goal_id'],
    )
    op.create_index(
        'ix_learning_goal_account_id',
        'learning_goals',
        ['account_id'],
    )
    op.create_index(
        'ix_learning_attempt_experience_activity_submitted',
        'learning_activity_attempts',
        ['skill_experience_id', 'activity_id', 'submitted_at'],
    )
    op.create_index(
        'ix_curriculum_competency_skill_position',
        'curriculum_competencies',
        ['skill_id', 'position'],
    )
    op.create_index(
        'ix_curriculum_material_skill_id',
        'curriculum_materials',
        ['skill_id'],
    )
    op.create_index(
        'ix_curriculum_activity_competency_id',
        'curriculum_activities',
        ['competency_id'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_curriculum_activity_competency_id',
        table_name='curriculum_activities',
    )
    op.drop_index(
        'ix_curriculum_material_skill_id',
        table_name='curriculum_materials',
    )
    op.drop_index(
        'ix_curriculum_competency_skill_position',
        table_name='curriculum_competencies',
    )
    op.drop_index(
        'ix_learning_attempt_experience_activity_submitted',
        table_name='learning_activity_attempts',
    )
    op.drop_index(
        'ix_learning_goal_account_id',
        table_name='learning_goals',
    )
    op.drop_index(
        'ix_learning_skill_experience_goal_id',
        table_name='learning_skill_experiences',
    )
    op.drop_constraint(
        'uq_learning_skill_experience_goal_skill',
        'learning_skill_experiences',
        type_='unique',
    )
    op.drop_index(
        'ix_learning_competency_progress_experience_competency',
        table_name='learning_competency_progresses',
    )
    op.drop_constraint(
        'uq_learning_competency_progress_experience_competency',
        'learning_competency_progresses',
        type_='unique',
    )
    op.drop_constraint(
        'ck_learning_competency_progress_hard_score',
        'learning_competency_progresses',
        type_='check',
    )
    op.drop_column('learning_competency_progresses', 'hard_activity_score')
