"""add Better Auth technical schema

Revision ID: b8f67e3c9a21
Revises: a25a7142d3ff
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'b8f67e3c9a21'
down_revision: str | None = 'a25a7142d3ff'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'better_auth_users',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('email', sa.Text(), nullable=False),
        sa.Column(
            'email_verified',
            sa.Boolean(),
            server_default=sa.text('false'),
            nullable=False,
        ),
        sa.Column('image', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id', name='pk_better_auth_users'),
        sa.UniqueConstraint('email', name='uq_better_auth_users_email'),
    )
    op.create_table(
        'better_auth_sessions',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('token', sa.Text(), nullable=False),
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('access_version', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ip_address', sa.Text(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['better_auth_users.id'],
            name='fk_better_auth_sessions_user',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name='pk_better_auth_sessions'),
        sa.UniqueConstraint('token', name='uq_better_auth_sessions_token'),
        sa.CheckConstraint(
            'access_version >= 1', name='ck_better_auth_sessions_access_version'
        ),
    )
    op.create_index(
        'ix_better_auth_sessions_user_id', 'better_auth_sessions', ['user_id']
    )
    op.create_index(
        'ix_better_auth_sessions_expires_at', 'better_auth_sessions', ['expires_at']
    )

    op.create_table(
        'better_auth_accounts',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('account_id', sa.Text(), nullable=False),
        sa.Column('provider_id', sa.Text(), nullable=False),
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('id_token', sa.Text(), nullable=True),
        sa.Column('scope', sa.Text(), nullable=True),
        sa.Column('password', sa.Text(), nullable=True),
        sa.Column('access_token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'refresh_token_expires_at', sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['better_auth_users.id'],
            name='fk_better_auth_accounts_user',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name='pk_better_auth_accounts'),
        sa.UniqueConstraint(
            'provider_id', 'account_id', name='uq_better_auth_accounts_provider'
        ),
    )
    op.create_index(
        'ix_better_auth_accounts_user_id', 'better_auth_accounts', ['user_id']
    )

    op.create_table(
        'better_auth_verifications',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('identifier', sa.Text(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id', name='pk_better_auth_verifications'),
        sa.UniqueConstraint(
            'identifier', name='uq_better_auth_verifications_identifier'
        ),
    )
    op.create_index(
        'ix_better_auth_verifications_expires_at',
        'better_auth_verifications',
        ['expires_at'],
    )

    op.create_table(
        'better_auth_jwks',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('public_key', sa.Text(), nullable=False),
        sa.Column('private_key', sa.Text(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_better_auth_jwks'),
    )
    op.create_index(
        'ix_better_auth_jwks_expires_at', 'better_auth_jwks', ['expires_at']
    )

    op.create_table(
        'better_auth_rate_limits',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('key', sa.Text(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False),
        sa.Column(
            'last_request',
            sa.BigInteger(),
            server_default=sa.text(
                '(EXTRACT(EPOCH FROM CURRENT_TIMESTAMP) * 1000)::bigint'
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id', name='pk_better_auth_rate_limits'),
        sa.UniqueConstraint('key', name='uq_better_auth_rate_limits_key'),
        sa.CheckConstraint('count >= 0', name='ck_better_auth_rate_limits_count'),
    )


def downgrade() -> None:
    op.drop_table('better_auth_rate_limits')
    op.drop_index('ix_better_auth_jwks_expires_at', table_name='better_auth_jwks')
    op.drop_table('better_auth_jwks')
    op.drop_index(
        'ix_better_auth_verifications_expires_at',
        table_name='better_auth_verifications',
    )
    op.drop_table('better_auth_verifications')
    op.drop_index('ix_better_auth_accounts_user_id', table_name='better_auth_accounts')
    op.drop_table('better_auth_accounts')
    op.drop_index(
        'ix_better_auth_sessions_expires_at', table_name='better_auth_sessions'
    )
    op.drop_index('ix_better_auth_sessions_user_id', table_name='better_auth_sessions')
    op.drop_table('better_auth_sessions')
    op.drop_table('better_auth_users')
