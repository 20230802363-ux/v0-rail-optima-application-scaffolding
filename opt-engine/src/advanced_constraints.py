from ortools.sat.python import cp_model
from typing import List, Dict, Set, Tuple
from datetime import datetime, timedelta
import logging

from .schemas import TrainData, TrackData

logger = logging.getLogger(__name__)

class AdvancedConstraintBuilder:
    """Builder for complex railway-specific constraints"""
    
    def __init__(self, model: cp_model.CpModel):
        self.model = model
        
    def add_junction_constraints(self, trains: List[TrainData], tracks: List[TrackData], 
                               x: Dict, junction_tracks: Dict[str, List[str]]):
        """Add constraints for railway junctions"""
        time_slots = range(240)  # Assuming 4-hour horizon
        
        for junction_id, track_list in junction_tracks.items():
            for t in time_slots:
                # At most one train can cross junction at any time
                junction_occupancy = []
                
                for track_id in track_list:
                    for train in trains:
                        if track_id in x[train.train_id]:
                            junction_occupancy.append(x[train.train_id][track_id][t])
                
                if junction_occupancy:
                    self.model.Add(sum(junction_occupancy) <= 1)
    
    def add_signal_constraints(self, trains: List[TrainData], tracks: List[TrackData], 
                             x: Dict, signals: Dict[str, Dict]):
        """Add signal-based movement constraints"""
        time_slots = range(240)
        
        for signal_id, signal_data in signals.items():
            controlled_tracks = signal_data.get('controlled_tracks', [])
            signal_type = signal_data.get('type', 'automatic')
            
            if signal_type == 'manual':
                # Manual signals require explicit clearance
                for track_id in controlled_tracks:
                    for train in trains:
                        if track_id in x[train.train_id]:
                            # Add signal clearance variables
                            for t in time_slots:
                                signal_clear = self.model.NewBoolVar(f"signal_clear_{signal_id}_{t}")
                                # Train can only occupy if signal is clear
                                self.model.AddImplication(
                                    x[train.train_id][track_id][t],
                                    signal_clear
                                )
    
    def add_maintenance_window_constraints(self, trains: List[TrainData], tracks: List[TrackData],
                                         x: Dict, maintenance_windows: List[Dict]):
        """Add constraints for maintenance windows"""
        for window in maintenance_windows:
            track_id = window['track_id']
            start_time = window['start_minute']
            end_time = window['end_minute']
            
            # No trains allowed during maintenance
            for train in trains:
                if track_id in x[train.train_id]:
                    for t in range(start_time, min(end_time + 1, 240)):
                        self.model.Add(x[train.train_id][track_id][t] == 0)
    
    def add_speed_restriction_constraints(self, trains: List[TrainData], tracks: List[TrackData],
                                        x: Dict, speed_restrictions: Dict[str, int]):
        """Add constraints for temporary speed restrictions"""
        # This affects travel time calculations
        for track_id, restricted_speed in speed_restrictions.items():
            track = next((t for t in tracks if t.segment_id == track_id), None)
            if not track:
                continue
            
            # Calculate increased travel time due to speed restriction
            normal_time = (track.distance_km / track.max_speed_kmh) * 60  # minutes
            restricted_time = (track.distance_km / restricted_speed) * 60
            additional_time = int(restricted_time - normal_time)
            
            # Extend minimum occupation time for affected trains
            for train in trains:
                if track_id in x[train.train_id]:
                    # Add constraint that train must occupy track for at least additional_time
                    for t in range(240 - additional_time):
                        # If train starts occupying at time t, it must continue for additional_time
                        starting = self.model.NewBoolVar(f"starting_{train.train_id}_{track_id}_{t}")
                        
                        if t > 0:
                            self.model.Add(x[train.train_id][track_id][t - 1] == 0).OnlyEnforceIf(starting)
                        self.model.Add(x[train.train_id][track_id][t] == 1).OnlyEnforceIf(starting)
                        
                        # Must continue occupying for minimum time
                        for dt in range(1, min(additional_time + 1, 240 - t)):
                            self.model.Add(x[train.train_id][track_id][t + dt] == 1).OnlyEnforceIf(starting)
    
    def add_crew_change_constraints(self, trains: List[TrainData], x: Dict, 
                                  crew_change_stations: Set[str]):
        """Add constraints for mandatory crew changes"""
        for train in trains:
            for station in crew_change_stations:
                if station in train.route:
                    # Train must stop at crew change station for minimum time
                    station_tracks = [track_id for track_id in x[train.train_id] 
                                    if station in track_id]  # Simplified station-track mapping
                    
                    for track_id in station_tracks:
                        # Add minimum stop time constraint (e.g., 10 minutes)
                        min_stop_time = 10
                        for t in range(240 - min_stop_time):
                            stopping = self.model.NewBoolVar(f"crew_change_{train.train_id}_{station}_{t}")
                            
                            # If stopping for crew change, must occupy for minimum time
                            for dt in range(min_stop_time):
                                if t + dt < 240:
                                    self.model.Add(x[train.train_id][track_id][t + dt] == 1).OnlyEnforceIf(stopping)
    
    def add_priority_overtaking_constraints(self, trains: List[TrainData], tracks: List[TrackData],
                                          x: Dict, overtaking_stations: Set[str]):
        """Add constraints for priority-based overtaking"""
        time_slots = range(240)
        
        # Sort trains by priority (1 = highest priority)
        sorted_trains = sorted(trains, key=lambda t: t.priority)
        
        for station in overtaking_stations:
            # Find tracks associated with this station
            station_tracks = [track for track in tracks 
                            if station in track.from_station or station in track.to_station]
            
            for track in station_tracks:
                for i, high_priority_train in enumerate(sorted_trains):
                    for j, low_priority_train in enumerate(sorted_trains[i+1:], i+1):
                        if (track.segment_id in x[high_priority_train.train_id] and 
                            track.segment_id in x[low_priority_train.train_id]):
                            
                            # High priority train gets preference
                            for t in time_slots:
                                # If both trains want the track, high priority gets it
                                both_want_track = self.model.NewBoolVar(
                                    f"both_want_{high_priority_train.train_id}_{low_priority_train.train_id}_{track.segment_id}_{t}"
                                )
                                
                                # This is a simplified constraint - real implementation would be more complex
                                self.model.AddImplication(
                                    both_want_track,
                                    x[high_priority_train.train_id][track.segment_id][t]
                                )
                                self.model.AddImplication(
                                    both_want_track,
                                    x[low_priority_train.train_id][track.segment_id][t].Not()
                                )
    
    def add_weather_impact_constraints(self, trains: List[TrainData], tracks: List[TrackData],
                                     x: Dict, weather_conditions: Dict[str, str]):
        """Add constraints for weather impact on operations"""
        weather_speed_factors = {
            'heavy_rain': 0.7,
            'fog': 0.5,
            'snow': 0.6,
            'high_wind': 0.8,
            'normal': 1.0
        }
        
        for track_id, weather in weather_conditions.items():
            speed_factor = weather_speed_factors.get(weather, 1.0)
            
            if speed_factor < 1.0:
                track = next((t for t in tracks if t.segment_id == track_id), None)
                if not track:
                    continue
                
                # Calculate increased travel time
                normal_time = (track.distance_km / track.max_speed_kmh) * 60
                weather_time = normal_time / speed_factor
                additional_time = int(weather_time - normal_time)
                
                # Similar to speed restriction constraints
                for train in trains:
                    if track_id in x[train.train_id]:
                        for t in range(240 - additional_time):
                            starting = self.model.NewBoolVar(f"weather_start_{train.train_id}_{track_id}_{t}")
                            
                            if t > 0:
                                self.model.Add(x[train.train_id][track_id][t - 1] == 0).OnlyEnforceIf(starting)
                            self.model.Add(x[train.train_id][track_id][t] == 1).OnlyEnforceIf(starting)
                            
                            # Extended occupation due to weather
                            for dt in range(1, min(additional_time + 1, 240 - t)):
                                self.model.Add(x[train.train_id][track_id][t + dt] == 1).OnlyEnforceIf(starting)
