from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class TrainData(BaseModel):
    train_id: str
    current_position: str  # station or track segment
    scheduled_arrival: datetime
    actual_arrival: Optional[datetime]
    priority: int  # 1=highest, 5=lowest
    delay_minutes: int = 0
    destination: str
    route: List[str]  # list of station/track codes

class TrackData(BaseModel):
    segment_id: str
    from_station: str
    to_station: str
    capacity: int = 1  # number of trains that can occupy simultaneously
    headway_minutes: int = 5  # minimum time between trains

class ConflictData(BaseModel):
    conflict_id: str
    train_ids: List[str]
    resource_id: str  # track or platform
    conflict_type: str  # "track_occupation", "platform_conflict", "junction_crossing"
    severity: int  # 1=critical, 5=minor

class ScheduleEntry(BaseModel):
    train_id: str
    segment_id: str
    start_time: datetime
    end_time: datetime
    platform: Optional[int]

class ScheduleRequest(BaseModel):
    trains: List[TrainData]
    tracks: List[TrackData]
    conflicts: List[ConflictData]
    time_horizon_minutes: int = 240  # 4 hours
    warm_start_solution: Optional[List[ScheduleEntry]] = None

class OptimizationResult(BaseModel):
    schedule: List[ScheduleEntry]
    objective_value: float
    solve_time: float
    conflicts_resolved: int
    total_delay_minutes: int

class ScheduleResponse(BaseModel):
    success: bool
    optimized_schedule: List[ScheduleEntry]
    objective_value: float
    solve_time_seconds: float
    conflicts_resolved: int
    total_delay_minutes: int
    message: Optional[str] = None
