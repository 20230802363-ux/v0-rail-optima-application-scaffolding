from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime
from .database import Base

class Station(Base):
    __tablename__ = "stations"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, index=True)
    name = Column(String(100), nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    platforms = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tracks = relationship("Track", back_populates="station")

class Track(Base):
    __tablename__ = "tracks"
    
    id = Column(Integer, primary_key=True, index=True)
    segment_id = Column(String(20), unique=True, index=True)
    from_station_id = Column(Integer, ForeignKey("stations.id"))
    to_station_id = Column(Integer, ForeignKey("stations.id"))
    distance_km = Column(Float)
    max_speed_kmh = Column(Integer, default=100)
    is_electrified = Column(Boolean, default=True)
    track_type = Column(String(20), default="double")  # single, double, multiple
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    station = relationship("Station", back_populates="tracks")

class Train(Base):
    __tablename__ = "trains"
    
    id = Column(Integer, primary_key=True, index=True)
    train_number = Column(String(10), unique=True, index=True)
    train_name = Column(String(100))
    train_type = Column(String(20))  # passenger, freight, express
    priority = Column(Integer, default=1)  # 1=highest, 5=lowest
    current_station_id = Column(Integer, ForeignKey("stations.id"))
    current_track_id = Column(Integer, ForeignKey("tracks.id"))
    latitude = Column(Float)
    longitude = Column(Float)
    speed_kmh = Column(Float, default=0)
    status = Column(String(20), default="scheduled")  # scheduled, running, delayed, cancelled
    delay_minutes = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    events = relationship("TrainEvent", back_populates="train")

class TrainEvent(Base):
    __tablename__ = "train_events"
    
    id = Column(Integer, primary_key=True, index=True)
    train_id = Column(Integer, ForeignKey("trains.id"))
    event_type = Column(String(20))  # arrival, departure, delay, conflict
    station_id = Column(Integer, ForeignKey("stations.id"))
    scheduled_time = Column(DateTime)
    actual_time = Column(DateTime)
    delay_minutes = Column(Integer, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    train = relationship("Train", back_populates="events")

class TimetableEntry(Base):
    __tablename__ = "timetable_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    train_id = Column(Integer, ForeignKey("trains.id"))
    station_id = Column(Integer, ForeignKey("stations.id"))
    arrival_time = Column(DateTime)
    departure_time = Column(DateTime)
    platform_number = Column(Integer)
    stop_duration_minutes = Column(Integer, default=2)
    distance_from_origin = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
