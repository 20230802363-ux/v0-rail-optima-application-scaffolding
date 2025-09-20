from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import List

from .models import Station, Track, Train, TrainEvent, TimetableEntry
from .schemas import TopologyUpload, TimetableUpload, PositionUpdate, StatusResponse

def create_topology(db: Session, topology: TopologyUpload):
    stations_created = 0
    tracks_created = 0
    
    # Create stations
    for station_data in topology.stations:
        existing = db.query(Station).filter(Station.code == station_data.code).first()
        if not existing:
            station = Station(
                code=station_data.code,
                name=station_data.name,
                latitude=station_data.latitude,
                longitude=station_data.longitude,
                platforms=station_data.platforms
            )
            db.add(station)
            stations_created += 1
    
    db.commit()
    
    # Create tracks
    for track_data in topology.tracks:
        existing = db.query(Track).filter(Track.segment_id == track_data.segment_id).first()
        if not existing:
            from_station = db.query(Station).filter(Station.code == track_data.from_station).first()
            to_station = db.query(Station).filter(Station.code == track_data.to_station).first()
            
            if from_station and to_station:
                track = Track(
                    segment_id=track_data.segment_id,
                    from_station_id=from_station.id,
                    to_station_id=to_station.id,
                    distance_km=track_data.distance_km,
                    max_speed_kmh=track_data.max_speed_kmh,
                    is_electrified=track_data.is_electrified,
                    track_type=track_data.track_type
                )
                db.add(track)
                tracks_created += 1
    
    db.commit()
    
    return {
        "message": "Topology uploaded successfully",
        "stations_created": stations_created,
        "tracks_created": tracks_created
    }

def create_timetable_entry(db: Session, timetable: TimetableUpload):
    for entry_data in timetable.entries:
        # Get or create train
        train = db.query(Train).filter(Train.train_number == entry_data.train_number).first()
        if not train:
            train = Train(
                train_number=entry_data.train_number,
                train_type="passenger",
                status="scheduled"
            )
            db.add(train)
            db.commit()
        
        # Get station
        station = db.query(Station).filter(Station.code == entry_data.station_code).first()
        if station:
            entry = TimetableEntry(
                train_id=train.id,
                station_id=station.id,
                arrival_time=entry_data.arrival_time,
                departure_time=entry_data.departure_time,
                platform_number=entry_data.platform_number,
                stop_duration_minutes=entry_data.stop_duration_minutes
            )
            db.add(entry)
    
    db.commit()
    return {"message": "Timetable entries created"}

def update_train_position(db: Session, position: PositionUpdate):
    train = db.query(Train).filter(Train.train_number == position.train_number).first()
    if not train:
        train = Train(
            train_number=position.train_number,
            train_type="passenger",
            status=position.status
        )
        db.add(train)
    
    # Update position
    train.latitude = position.latitude
    train.longitude = position.longitude
    train.speed_kmh = position.speed_kmh
    train.status = position.status
    train.delay_minutes = position.delay_minutes
    train.last_updated = position.timestamp
    
    # Update current station if provided
    if position.current_station:
        station = db.query(Station).filter(Station.code == position.current_station).first()
        if station:
            train.current_station_id = station.id
    
    db.commit()

def get_system_status(db: Session) -> StatusResponse:
    total_stations = db.query(func.count(Station.id)).scalar()
    total_tracks = db.query(func.count(Track.id)).scalar()
    active_trains = db.query(func.count(Train.id)).filter(Train.status == "running").scalar()
    total_events = db.query(func.count(TrainEvent.id)).scalar()
    
    return StatusResponse(
        status="healthy",
        total_stations=total_stations,
        total_tracks=total_tracks,
        active_trains=active_trains,
        total_events=total_events,
        last_updated=datetime.utcnow()
    )
