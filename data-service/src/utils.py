from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import logging
from sqlalchemy.orm import Session
from .models import Station, Track, Train

logger = logging.getLogger(__name__)

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    Returns distance in kilometers
    """
    from math import radians, cos, sin, asin, sqrt
    
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r

def find_nearest_station(db: Session, latitude: float, longitude: float, max_distance_km: float = 50) -> Optional[Station]:
    """Find the nearest station to given coordinates"""
    stations = db.query(Station).filter(
        Station.latitude.isnot(None),
        Station.longitude.isnot(None)
    ).all()
    
    nearest_station = None
    min_distance = float('inf')
    
    for station in stations:
        distance = calculate_distance(latitude, longitude, station.latitude, station.longitude)
        if distance < min_distance and distance <= max_distance_km:
            min_distance = distance
            nearest_station = station
    
    return nearest_station

def get_route_between_stations(db: Session, from_station_code: str, to_station_code: str) -> List[Dict[str, Any]]:
    """
    Find the route between two stations
    Returns list of track segments
    """
    from_station = db.query(Station).filter(Station.code == from_station_code).first()
    to_station = db.query(Station).filter(Station.code == to_station_code).first()
    
    if not from_station or not to_station:
        return []
    
    # Simple direct route finding - in reality this would use graph algorithms
    tracks = db.query(Track).filter(
        ((Track.from_station_id == from_station.id) & (Track.to_station_id == to_station.id)) |
        ((Track.from_station_id == to_station.id) & (Track.to_station_id == from_station.id))
    ).all()
    
    route = []
    for track in tracks:
        route.append({
            "segment_id": track.segment_id,
            "from_station": from_station.code if track.from_station_id == from_station.id else to_station.code,
            "to_station": to_station.code if track.to_station_id == to_station.id else from_station.code,
            "distance_km": track.distance_km,
            "max_speed_kmh": track.max_speed_kmh
        })
    
    return route

def estimate_travel_time(distance_km: float, max_speed_kmh: int, train_type: str = "passenger") -> int:
    """
    Estimate travel time in minutes based on distance and train type
    """
    # Speed factors based on train type
    speed_factors = {
        "express": 0.85,  # Express trains run at 85% of max speed
        "passenger": 0.65,  # Passenger trains run at 65% of max speed
        "freight": 0.45,   # Freight trains run at 45% of max speed
    }
    
    factor = speed_factors.get(train_type, 0.65)
    effective_speed = max_speed_kmh * factor
    
    # Add buffer time for acceleration/deceleration and stops
    base_time_hours = distance_km / effective_speed
    buffer_minutes = distance_km * 0.5  # 0.5 minutes per km for stops/delays
    
    total_minutes = (base_time_hours * 60) + buffer_minutes
    return int(total_minutes)

def validate_timetable_consistency(timetable_entries: List[Dict[str, Any]]) -> List[str]:
    """
    Validate timetable entries for consistency
    Returns list of validation errors
    """
    errors = []
    
    # Group by train
    trains = {}
    for entry in timetable_entries:
        train_id = entry.get("train_number")
        if train_id not in trains:
            trains[train_id] = []
        trains[train_id].append(entry)
    
    for train_id, entries in trains.items():
        # Sort by departure time
        entries.sort(key=lambda x: x.get("departure_time", ""))
        
        # Check for time consistency
        for i in range(len(entries) - 1):
            current = entries[i]
            next_entry = entries[i + 1]
            
            current_dep = datetime.fromisoformat(current.get("departure_time", ""))
            next_arr = datetime.fromisoformat(next_entry.get("arrival_time", ""))
            
            if current_dep >= next_arr:
                errors.append(f"Train {train_id}: Departure from {current.get('station_code')} "
                            f"is after arrival at {next_entry.get('station_code')}")
    
    return errors

def format_delay_message(delay_minutes: int) -> str:
    """Format delay message for display"""
    if delay_minutes <= 0:
        return "On time"
    elif delay_minutes <= 5:
        return f"{delay_minutes} min delay"
    elif delay_minutes <= 60:
        return f"{delay_minutes} min delay"
    else:
        hours = delay_minutes // 60
        minutes = delay_minutes % 60
        return f"{hours}h {minutes}m delay"

def generate_train_status_summary(db: Session) -> Dict[str, Any]:
    """Generate a summary of current train statuses"""
    total_trains = db.query(Train).count()
    running_trains = db.query(Train).filter(Train.status == "running").count()
    delayed_trains = db.query(Train).filter(Train.delay_minutes > 5).count()
    
    # Calculate average delay
    trains_with_delay = db.query(Train).filter(Train.delay_minutes > 0).all()
    avg_delay = sum(t.delay_minutes for t in trains_with_delay) / len(trains_with_delay) if trains_with_delay else 0
    
    return {
        "total_trains": total_trains,
        "running_trains": running_trains,
        "delayed_trains": delayed_trains,
        "on_time_trains": total_trains - delayed_trains,
        "average_delay_minutes": round(avg_delay, 1),
        "on_time_percentage": round(((total_trains - delayed_trains) / total_trains * 100), 1) if total_trains > 0 else 100
    }
