"""Esquema base de NeuroLift: todas las tablas de backend/models.py.

Reemplaza a la cadena anterior de migraciones, que solo agregaba columnas sobre un esquema base
que creaba `create_all()` al arrancar la API. Desde aquí el esquema nace SOLO con
`alembic upgrade head` (la API ya no crea tablas).

Un ambiente que ya tenía el esquema (QA) no la ejecuta: se marca con `alembic stamp 0001`
después de comprobar que coincide con los modelos (`alembic check`).

Revision ID: 0001
Revises:
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('audit_logs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('level', sa.String(length=10), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)
    op.create_table('boxes',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('address', sa.String(length=255), nullable=True),
    sa.Column('city', sa.String(length=100), nullable=True),
    sa.Column('state', sa.String(length=100), nullable=True),
    sa.Column('country', sa.String(length=100), nullable=True),
    sa.Column('logo_filename', sa.String(length=255), nullable=True),
    sa.Column('accent_color', sa.String(length=7), nullable=True),
    sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
    sa.Column('invite_code', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('approved_at', sa.DateTime(), nullable=True),
    sa.Column('kind', sa.String(length=10), server_default='box', nullable=False),
    sa.Column('plan', sa.String(length=20), server_default='basic', nullable=False),
    sa.Column('trial_ends_at', sa.DateTime(), nullable=True),
    sa.Column('paid_until', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_boxes_invite_code'), 'boxes', ['invite_code'], unique=True)
    op.create_table('exercises',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('category', sa.String(length=50), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('full_name', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.String(), nullable=False),
    sa.Column('role', sa.String(), server_default='athlete', nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('body_weight', sa.Float(), nullable=True),
    sa.Column('sex', sa.String(length=10), nullable=True),
    sa.Column('age', sa.Integer(), nullable=True),
    sa.Column('category', sa.String(length=10), nullable=True),
    sa.Column('weight_unit', sa.String(length=10), nullable=True),
    sa.Column('has_25kg_plates', sa.Boolean(), nullable=True),
    sa.Column('show_in_ranking', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('token_version', sa.Integer(), server_default='0', nullable=False),
    sa.Column('avatar_filename', sa.String(length=255), nullable=True),
    sa.Column('coach_id', sa.UUID(), nullable=True),
    sa.Column('box_id', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['box_id'], ['boxes.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['coach_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_box_id'), 'users', ['box_id'], unique=False)
    op.create_index(op.f('ix_users_coach_id'), 'users', ['coach_id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_full_name'), 'users', ['full_name'], unique=False)
    op.create_table('box_classes',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('box_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('coach_id', sa.UUID(), nullable=True),
    sa.Column('weekdays', sa.String(length=20), nullable=False),
    sa.Column('start_time', sa.Time(), nullable=False),
    sa.Column('duration_minutes', sa.Integer(), server_default='60', nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['box_id'], ['boxes.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['coach_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_box_classes_box_id'), 'box_classes', ['box_id'], unique=False)
    op.create_index(op.f('ix_box_classes_coach_id'), 'box_classes', ['coach_id'], unique=False)
    op.create_table('fitness_benchmarks',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('metric_key', sa.String(length=50), nullable=False),
    sa.Column('value', sa.Float(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'metric_key', name='uq_fitness_benchmark_user_metric')
    )
    op.create_index(op.f('ix_fitness_benchmarks_user_id'), 'fitness_benchmarks', ['user_id'], unique=False)
    op.create_table('groups',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('coach_id', sa.UUID(), nullable=False),
    sa.Column('box_id', sa.UUID(), nullable=True),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('cover_image_filename', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['box_id'], ['boxes.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['coach_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_groups_box_id'), 'groups', ['box_id'], unique=False)
    op.create_index(op.f('ix_groups_coach_id'), 'groups', ['coach_id'], unique=False)
    op.create_table('personal_records',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('exercise_name', sa.String(), nullable=False),
    sa.Column('max_weight_kg', sa.Float(), nullable=False),
    sa.Column('last_updated', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_personal_records_exercise_name'), 'personal_records', ['exercise_name'], unique=False)
    op.create_index(op.f('ix_personal_records_user_id'), 'personal_records', ['user_id'], unique=False)
    op.create_table('group_members',
    sa.Column('group_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('group_id', 'user_id')
    )
    op.create_table('mesocycles',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('group_id', sa.UUID(), nullable=True),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('discipline', sa.String(length=50), nullable=True),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('ai_prompt_context', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('is_self_managed', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('class_id', sa.UUID(), nullable=True),
    sa.Column('is_class_log', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('is_template', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('is_published', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('created_by_coach_id', sa.UUID(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('level', sa.String(length=20), nullable=True),
    sa.Column('price', sa.Float(), nullable=True),
    sa.Column('source_plan_id', sa.UUID(), nullable=True),
    sa.Column('cover_image_filename', sa.String(length=255), nullable=True),
    sa.Column('box_id', sa.UUID(), nullable=True),
    sa.Column('plan_visibility', sa.String(length=10), server_default='box', nullable=False),
    sa.ForeignKeyConstraint(['box_id'], ['boxes.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['class_id'], ['box_classes.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['created_by_coach_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['source_plan_id'], ['mesocycles.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mesocycles_box_id'), 'mesocycles', ['box_id'], unique=False)
    op.create_index(op.f('ix_mesocycles_class_id'), 'mesocycles', ['class_id'], unique=False)
    op.create_index(op.f('ix_mesocycles_created_by_coach_id'), 'mesocycles', ['created_by_coach_id'], unique=False)
    op.create_index(op.f('ix_mesocycles_group_id'), 'mesocycles', ['group_id'], unique=False)
    op.create_index(op.f('ix_mesocycles_user_id'), 'mesocycles', ['user_id'], unique=False)
    op.create_table('sessions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('mesocycle_id', sa.UUID(), nullable=True),
    sa.Column('scheduled_date', sa.Date(), nullable=False),
    sa.Column('completed_date', sa.DateTime(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('athlete_notes', sa.Text(), nullable=True),
    sa.Column('ai_feedback', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('parent_session_id', sa.UUID(), nullable=True),
    sa.Column('duration_minutes', sa.Integer(), nullable=True),
    sa.Column('day_offset', sa.Integer(), nullable=True),
    sa.Column('block_order', sa.String(length=200), nullable=True),
    sa.Column('warmup_notes', sa.Text(), nullable=True),
    sa.Column('wod_notes', sa.Text(), nullable=True),
    sa.Column('wod_format', sa.String(length=20), nullable=True),
    sa.Column('wod_time_cap_seconds', sa.Integer(), nullable=True),
    sa.Column('wod_time_seconds', sa.Integer(), nullable=True),
    sa.Column('wod_rounds', sa.Integer(), nullable=True),
    sa.Column('wod_extra_reps', sa.Integer(), nullable=True),
    sa.Column('wod_emom_completed', sa.Boolean(), nullable=True),
    sa.Column('wod_calories', sa.Float(), nullable=True),
    sa.Column('wod_distance_meters', sa.Float(), nullable=True),
    sa.Column('wod_watts', sa.Float(), nullable=True),
    sa.Column('class_session_id', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['class_session_id'], ['sessions.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['mesocycle_id'], ['mesocycles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['parent_session_id'], ['sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sessions_class_session_id'), 'sessions', ['class_session_id'], unique=False)
    op.create_index(op.f('ix_sessions_mesocycle_id'), 'sessions', ['mesocycle_id'], unique=False)
    op.create_index('ix_sessions_mesocycle_scheduled_date', 'sessions', ['mesocycle_id', 'scheduled_date'], unique=False)
    op.create_index(op.f('ix_sessions_parent_session_id'), 'sessions', ['parent_session_id'], unique=False)
    op.create_table('sets',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=True),
    sa.Column('exercise_id', sa.UUID(), nullable=True),
    sa.Column('set_order', sa.Integer(), nullable=False),
    sa.Column('block', sa.String(length=30), nullable=True),
    sa.Column('prescribed_reps', sa.Integer(), nullable=True),
    sa.Column('prescribed_weight', sa.Float(), nullable=True),
    sa.Column('actual_reps', sa.Integer(), nullable=True),
    sa.Column('actual_weight', sa.Float(), nullable=True),
    sa.Column('rpe', sa.Integer(), nullable=True),
    sa.Column('video_url', sa.String(length=255), nullable=True),
    sa.Column('technique_score', sa.Float(), nullable=True),
    sa.Column('technique_feedback', sa.Text(), nullable=True),
    sa.Column('coach_note', sa.Text(), nullable=True),
    sa.Column('is_pr_attempt', sa.Boolean(), nullable=True),
    sa.Column('prescribed_percentage', sa.Float(), nullable=True),
    sa.Column('reference_exercise', sa.String(length=100), nullable=True),
    sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sets_exercise_id'), 'sets', ['exercise_id'], unique=False)
    op.create_index(op.f('ix_sets_session_id'), 'sets', ['session_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_sets_session_id'), table_name='sets')
    op.drop_index(op.f('ix_sets_exercise_id'), table_name='sets')
    op.drop_table('sets')
    op.drop_index(op.f('ix_sessions_parent_session_id'), table_name='sessions')
    op.drop_index('ix_sessions_mesocycle_scheduled_date', table_name='sessions')
    op.drop_index(op.f('ix_sessions_mesocycle_id'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_class_session_id'), table_name='sessions')
    op.drop_table('sessions')
    op.drop_index(op.f('ix_mesocycles_user_id'), table_name='mesocycles')
    op.drop_index(op.f('ix_mesocycles_group_id'), table_name='mesocycles')
    op.drop_index(op.f('ix_mesocycles_created_by_coach_id'), table_name='mesocycles')
    op.drop_index(op.f('ix_mesocycles_class_id'), table_name='mesocycles')
    op.drop_index(op.f('ix_mesocycles_box_id'), table_name='mesocycles')
    op.drop_table('mesocycles')
    op.drop_table('group_members')
    op.drop_index(op.f('ix_personal_records_user_id'), table_name='personal_records')
    op.drop_index(op.f('ix_personal_records_exercise_name'), table_name='personal_records')
    op.drop_table('personal_records')
    op.drop_index(op.f('ix_groups_coach_id'), table_name='groups')
    op.drop_index(op.f('ix_groups_box_id'), table_name='groups')
    op.drop_table('groups')
    op.drop_index(op.f('ix_fitness_benchmarks_user_id'), table_name='fitness_benchmarks')
    op.drop_table('fitness_benchmarks')
    op.drop_index(op.f('ix_box_classes_coach_id'), table_name='box_classes')
    op.drop_index(op.f('ix_box_classes_box_id'), table_name='box_classes')
    op.drop_table('box_classes')
    op.drop_index(op.f('ix_users_full_name'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_coach_id'), table_name='users')
    op.drop_index(op.f('ix_users_box_id'), table_name='users')
    op.drop_table('users')
    op.drop_table('exercises')
    op.drop_index(op.f('ix_boxes_invite_code'), table_name='boxes')
    op.drop_table('boxes')
    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_table('audit_logs')
