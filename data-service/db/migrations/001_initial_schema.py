"""Initial schema migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create stations table
    op.create_table('stations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=10), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('platforms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stations_code'), 'stations', ['code'], unique=True)
    op.create_index(op.f('ix_stations_id'), 'stations', ['id'], unique=False)

    # Create tracks table
    op.create_table('tracks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('segment_id', sa.String(length=20), nullable=True),
        sa.Column('from_station_id', sa.Integer(), nullable=True),
        sa.Column('to_station_id', sa.Integer(), nullable=True),
        sa.Column('distance_km', sa.Float(), nullable=True),
        sa.Column('max_speed_kmh', sa.Integer(), nullable=True),
        sa.Column('is_electrified', sa.Boolean(), nullable=True),
        sa.Column('track_type', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['from_station_id'], ['stations.id'], ),
        sa.ForeignKeyConstraint(['to_station_id'], ['stations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tracks_id'), 'tracks', ['id'], unique=False)
    op.create_index(op.f('ix_tracks_segment_id'), 'tracks', ['segment_id'], unique=True)

    # Create trains table
    op.create_table('trains',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('train_number', sa.String(length=10), nullable=True),
        sa.Column('train_name', sa.String(length=100), nullable=True),
        sa.Column('train_type', sa.String(length=20), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('current_station_id', sa.Integer(), nullable=True),
        sa.Column('current_track_id', sa.Integer(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('speed_kmh', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('delay_minutes', sa.Integer(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['current_station_id'], ['stations.id'], ),
        sa.ForeignKeyConstraint(['current_track_id'], ['tracks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trains_id'), 'trains', ['id'], unique=False)
    op.create_index(op.f('ix_trains_train_number'), 'trains', ['train_number'], unique=True)

    # Create train_events table
    op.create_table('train_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('train_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(length=20), nullable=True),
        sa.Column('station_id', sa.Integer(), nullable=True),
        sa.Column('scheduled_time', sa.DateTime(), nullable=True),
        sa.Column('actual_time', sa.DateTime(), nullable=True),
        sa.Column('delay_minutes', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['station_id'], ['stations.id'], ),
        sa.ForeignKeyConstraint(['train_id'], ['trains.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_train_events_id'), 'train_events', ['id'], unique=False)

    # Create timetable_entries table
    op.create_table('timetable_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('train_id', sa.Integer(), nullable=True),
        sa.Column('station_id', sa.Integer(), nullable=True),
        sa.Column('arrival_time', sa.DateTime(), nullable=True),
        sa.Column('departure_time', sa.DateTime(), nullable=True),
        sa.Column('platform_number', sa.Integer(), nullable=True),
        sa.Column('stop_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('distance_from_origin', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['station_id'], ['stations.id'], ),
        sa.ForeignKeyConstraint(['train_id'], ['trains.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_timetable_entries_id'), 'timetable_entries', ['id'], unique=False)

def downgrade():
    op.drop_table('timetable_entries')
    op.drop_table('train_events')
    op.drop_table('trains')
    op.drop_table('tracks')
    op.drop_table('stations')
