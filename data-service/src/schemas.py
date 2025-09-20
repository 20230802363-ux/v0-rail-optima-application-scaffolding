from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class StationData(BaseModel):
    code: str
    name: str
    latitude: float
    longitude: float
    platforms: int = 1

class TrackData(BaseModel):
    segment_id: str
    from_station: str
    to_station: str
    distance_km: float
    max_speed_kmh: int = 100
    is_electrified: bool = True
    track_type: str = "double"

class TopologyUpload(BaseModel):
    stations: List[StationData]
    tracks: List[TrackData]

class TopologyResponse(BaseModel):
    message: str
    stations_created: int
    tracks_created: int

class TimetableEntryData(BaseModel):
    train_number: str
    station_code: str
    arrival_time: Optional[datetime]
    departure_time: datetime
    platform_number: Optional[int]
    stop_duration_minutes: int = 2

class TimetableUpload(BaseModel):
    entries: List[TimetableEntryData]

class PositionUpdate(BaseModel):
    train_number: str
    latitude: float
    longitude: float
    speed_kmh: float
    current_station: Optional[str]
    status: str = "running"
    delay_minutes: int = 0
    timestamp: datetime

class StatusResponse(BaseModel):
    status: str
    total_stations: int
    total_tracks: int
    active_trains: int
    total_events: int
    last_updated: datetime
