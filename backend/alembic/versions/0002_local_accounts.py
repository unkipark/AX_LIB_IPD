"""local accounts

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-22 11:07:40.225017
"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('login_id', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('password_hash', sa.String(length=200), nullable=True))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))
    op.alter_column('users', 'external_id',
               existing_type=sa.VARCHAR(length=200),
               nullable=True)
    op.alter_column('users', 'last_login_at',
               existing_type=sa.DateTime(timezone=True),
               nullable=True)
    # downgrade 때 채운 임시 값은 지워야 SSO 전환 시 사번으로 다시 연결됩니다.
    op.execute("UPDATE users SET external_id = NULL WHERE external_id LIKE 'local:%'")
    op.create_index(op.f('ix_users_emp_no'), 'users', ['emp_no'], unique=False)
    op.create_unique_constraint('uq_users_login_id', 'users', ['login_id'])


def downgrade() -> None:
    op.drop_constraint('uq_users_login_id', 'users', type_='unique')
    op.drop_index(op.f('ix_users_emp_no'), table_name='users')
    # local 계정은 external_id 가 없으므로, 되돌릴 때 사번 기반 임시 값으로 채웁니다.
    op.execute("UPDATE users SET external_id = 'local:' || login_id WHERE external_id IS NULL")
    op.execute("UPDATE users SET last_login_at = created_at WHERE last_login_at IS NULL")
    op.alter_column('users', 'last_login_at',
               existing_type=sa.DateTime(timezone=True),
               nullable=False)
    op.alter_column('users', 'external_id',
               existing_type=sa.VARCHAR(length=200),
               nullable=False)
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'password_hash')
    op.drop_column('users', 'login_id')
