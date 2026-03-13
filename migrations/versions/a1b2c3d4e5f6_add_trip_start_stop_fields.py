"""Add trip start/stop fields

Revision ID: a1b2c3d4e5f6
Revises: 613be8af4376
Create Date: 2026-03-11 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '613be8af4376'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('trips', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=20), nullable=True, server_default='completed'))
        batch_op.add_column(sa.Column('driver_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))
        batch_op.add_column(sa.Column('started_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('stopped_at', sa.DateTime(), nullable=True))
        batch_op.alter_column('start_odometer',
               existing_type=sa.FLOAT(),
               nullable=True)
        batch_op.alter_column('end_odometer',
               existing_type=sa.FLOAT(),
               nullable=True)
        batch_op.alter_column('purpose',
               existing_type=sa.String(length=20),
               nullable=True)


def downgrade():
    with op.batch_alter_table('trips', schema=None) as batch_op:
        batch_op.alter_column('purpose',
               existing_type=sa.String(length=20),
               nullable=False)
        batch_op.alter_column('end_odometer',
               existing_type=sa.FLOAT(),
               nullable=False)
        batch_op.alter_column('start_odometer',
               existing_type=sa.FLOAT(),
               nullable=False)
        batch_op.drop_column('stopped_at')
        batch_op.drop_column('started_at')
        batch_op.drop_column('driver_id')
        batch_op.drop_column('status')
