import pytest
from datetime import datetime, timedelta
from src.optimizer import RailwayOptimizer, OptimizationConfig
from src.schemas import TrainData, TrackData, ConflictData

@pytest.fixture
def sample_trains():
    return [
        TrainData(
            train_id="12004",
            current_position="NDLS",
            scheduled_arrival=datetime.now() + timedelta(hours=1),
            priority=1,
            delay_minutes=0,
            destination="LKO",
            route=["NDLS", "GZB", "MB", "LKO"]
        ),
        TrainData(
            train_id="14006",
            current_position="GZB",
            scheduled_arrival=datetime.now() + timedelta(hours=1, minutes=30),
            priority=2,
            delay_minutes=15,
            destination="LKO",
            route=["GZB", "MB", "LKO"]
        )
    ]

@pytest.fixture
def sample_tracks():
    return [
        TrackData(
            segment_id="NDLS-GZB-001",
            from_station="NDLS",
            to_station="GZB",
            capacity=1,
            headway_minutes=5
        ),
        TrackData(
            segment_id="GZB-MB-001",
            from_station="GZB",
            to_station="MB",
            capacity=1,
            headway_minutes=5
        ),
        TrackData(
            segment_id="MB-LKO-001",
            from_station="MB",
            to_station="LKO",
            capacity=1,
            headway_minutes=5
        )
    ]

@pytest.fixture
def sample_conflicts():
    return [
        ConflictData(
            conflict_id="conflict_001",
            train_ids=["12004", "14006"],
            resource_id="GZB-MB-001",
            conflict_type="track_occupation",
            severity=2
        )
    ]

def test_optimizer_initialization():
    optimizer = RailwayOptimizer()
    assert optimizer.is_ready()
    assert optimizer.solver_type == "ortools"

def test_optimization_with_sample_data(sample_trains, sample_tracks, sample_conflicts):
    optimizer = RailwayOptimizer()
    config = OptimizationConfig(time_horizon_minutes=120, max_solve_time_seconds=10)
    optimizer.config = config
    
    result = optimizer.optimize(
        trains=sample_trains,
        tracks=sample_tracks,
        conflicts=sample_conflicts,
        time_horizon=120
    )
    
    assert result is not None
    assert result.solve_time > 0
    assert len(result.schedule) > 0
    assert result.objective_value >= 0

def test_route_segments_extraction(sample_trains, sample_tracks):
    optimizer = RailwayOptimizer()
    train = sample_trains[0]
    
    segments = optimizer._get_route_segments(train, sample_tracks)
    
    assert len(segments) > 0
    assert "NDLS-GZB-001" in segments
    assert "GZB-MB-001" in segments

def test_optimization_config():
    config = OptimizationConfig(
        time_horizon_minutes=180,
        delay_weight=2.0,
        conflict_weight=150.0
    )
    
    assert config.time_horizon_minutes == 180
    assert config.delay_weight == 2.0
    assert config.conflict_weight == 150.0

def test_empty_input_handling():
    optimizer = RailwayOptimizer()
    
    # Test with empty inputs
    with pytest.raises(Exception):
        optimizer.optimize(trains=[], tracks=[], conflicts=[])

def test_constraint_building():
    optimizer = RailwayOptimizer()
    
    # Test that model creation doesn't crash
    model = optimizer._create_model([], [], [])
    assert model is not None
