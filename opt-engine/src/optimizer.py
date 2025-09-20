from ortools.sat.python import cp_model
import numpy as np
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum

from .schemas import TrainData, TrackData, ConflictData, ScheduleEntry, OptimizationResult

logger = logging.getLogger(__name__)

class ConflictType(Enum):
    TRACK_OCCUPATION = "track_occupation"
    PLATFORM_CONFLICT = "platform_conflict"
    JUNCTION_CROSSING = "junction_crossing"
    HEADWAY_VIOLATION = "headway_violation"

@dataclass
class OptimizationConfig:
    time_horizon_minutes: int = 240
    time_step_minutes: int = 1
    max_solve_time_seconds: int = 30
    delay_weight: float = 1.0
    conflict_weight: float = 100.0
    priority_multiplier: float = 2.0
    headway_buffer_minutes: int = 2

class RailwayOptimizer:
    def __init__(self, solver_type: str = "ortools", config: OptimizationConfig = None):
        self.solver_type = solver_type
        self.config = config or OptimizationConfig()
        self.model = None
        self.solver = None
        self.variables = {}
        self.constraints = []
        
    def is_ready(self) -> bool:
        return True
    
    def optimize(
        self,
        trains: List[TrainData],
        tracks: List[TrackData],
        conflicts: List[ConflictData],
        time_horizon: int = 240,
        warm_start: Optional[List[ScheduleEntry]] = None
    ) -> OptimizationResult:
        """
        Main optimization method using CP-SAT solver with advanced constraints
        """
        start_time = datetime.now()
        logger.info(f"Starting optimization for {len(trains)} trains, {len(tracks)} tracks")
        
        # Update configuration
        self.config.time_horizon_minutes = time_horizon
        
        # Create and solve model
        model = self._create_model(trains, tracks, conflicts)
        solution = self._solve_model(model, warm_start)
        
        solve_time = (datetime.now() - start_time).total_seconds()
        
        if solution:
            schedule = self._extract_schedule(solution, trains, tracks)
            metrics = self._calculate_metrics(solution, trains, conflicts)
            
            return OptimizationResult(
                schedule=schedule,
                objective_value=metrics['objective_value'],
                solve_time=solve_time,
                conflicts_resolved=metrics['conflicts_resolved'],
                total_delay_minutes=metrics['total_delay']
            )
        else:
            raise Exception("Optimization failed - no feasible solution found")
    
    def _create_model(self, trains: List[TrainData], tracks: List[TrackData], 
                     conflicts: List[ConflictData]) -> cp_model.CpModel:
        """Create the constraint programming model"""
        model = cp_model.CpModel()
        self.variables = {}
        
        # Time discretization
        time_slots = range(self.config.time_horizon_minutes)
        
        # Decision Variables
        
        # 1. Train-Track-Time occupancy: x[train_id][track_id][time] = 1 if train occupies track at time
        x = {}
        for train in trains:
            x[train.train_id] = {}
            for track in tracks:
                x[train.train_id][track.segment_id] = {}
                for t in time_slots:
                    x[train.train_id][track.segment_id][t] = model.NewBoolVar(
                        f"occupy_{train.train_id}_{track.segment_id}_{t}"
                    )
        
        # 2. Start delay variables: s[train_id] = delay in minutes from scheduled start
        s = {}
        for train in trains:
            max_delay = min(120, self.config.time_horizon_minutes // 2)  # Max 2 hours delay
            s[train.train_id] = model.NewIntVar(0, max_delay, f"start_delay_{train.train_id}")
        
        # 3. Conflict occurrence: c[conflict_id] = 1 if conflict occurs
        c = {}
        for conflict in conflicts:
            c[conflict.conflict_id] = model.NewBoolVar(f"conflict_{conflict.conflict_id}")
        
        # 4. Platform assignment: p[train_id][station_id] = platform number
        p = {}
        for train in trains:
            p[train.train_id] = {}
            for station_code in set(train.route):
                # Assume max 10 platforms per station
                p[train.train_id][station_code] = model.NewIntVar(1, 10, f"platform_{train.train_id}_{station_code}")
        
        # 5. Journey completion time: j[train_id] = time when train completes journey
        j = {}
        for train in trains:
            j[train.train_id] = model.NewIntVar(0, self.config.time_horizon_minutes, f"journey_time_{train.train_id}")
        
        self.variables = {'x': x, 's': s, 'c': c, 'p': p, 'j': j}
        
        # Add Constraints
        self._add_capacity_constraints(model, trains, tracks, x)
        self._add_route_continuity_constraints(model, trains, tracks, x)
        self._add_headway_constraints(model, trains, tracks, x)
        self._add_platform_constraints(model, trains, p)
        self._add_conflict_constraints(model, trains, tracks, conflicts, x, c)
        self._add_timing_constraints(model, trains, x, s, j)
        
        # Set Objective
        self._set_objective(model, trains, conflicts, s, c, j)
        
        return model
    
    def _add_capacity_constraints(self, model: cp_model.CpModel, trains: List[TrainData], 
                                tracks: List[TrackData], x: Dict):
        """Add track capacity constraints"""
        time_slots = range(self.config.time_horizon_minutes)
        
        for track in tracks:
            for t in time_slots:
                # Track capacity constraint: sum of trains on track <= capacity
                occupancy_vars = []
                for train in trains:
                    if track.segment_id in x[train.train_id]:
                        occupancy_vars.append(x[train.train_id][track.segment_id][t])
                
                if occupancy_vars:
                    model.Add(sum(occupancy_vars) <= track.capacity)
    
    def _add_route_continuity_constraints(self, model: cp_model.CpModel, trains: List[TrainData], 
                                        tracks: List[TrackData], x: Dict):
        """Add constraints for route continuity and train movement"""
        time_slots = range(self.config.time_horizon_minutes)
        
        for train in trains:
            route_segments = self._get_route_segments(train, tracks)
            
            if len(route_segments) < 2:
                continue
            
            # Sequential segment occupation
            for i in range(len(route_segments) - 1):
                current_segment = route_segments[i]
                next_segment = route_segments[i + 1]
                
                for t in range(len(time_slots) - 1):
                    # If train leaves current segment at time t, it must enter next segment at t+1
                    if (current_segment in x[train.train_id] and 
                        next_segment in x[train.train_id]):
                        
                        # Leaving current segment
                        leaving_current = model.NewBoolVar(f"leaving_{train.train_id}_{current_segment}_{t}")
                        model.Add(x[train.train_id][current_segment][t] == 1).OnlyEnforceIf(leaving_current)
                        model.Add(x[train.train_id][current_segment][t + 1] == 0).OnlyEnforceIf(leaving_current)
                        
                        # Must enter next segment
                        model.Add(x[train.train_id][next_segment][t + 1] == 1).OnlyEnforceIf(leaving_current)
            
            # Train must complete its route
            if route_segments:
                last_segment = route_segments[-1]
                if last_segment in x[train.train_id]:
                    # Train must occupy last segment at some point
                    model.Add(sum(x[train.train_id][last_segment][t] for t in time_slots) >= 1)
    
    def _add_headway_constraints(self, model: cp_model.CpModel, trains: List[TrainData], 
                               tracks: List[TrackData], x: Dict):
        """Add minimum headway constraints between trains"""
        time_slots = range(self.config.time_horizon_minutes)
        headway = self.config.headway_buffer_minutes + 3  # Base headway + buffer
        
        for track in tracks:
            for i, train1 in enumerate(trains):
                for j, train2 in enumerate(trains):
                    if i >= j:  # Avoid duplicate constraints
                        continue
                    
                    if (track.segment_id in x[train1.train_id] and 
                        track.segment_id in x[train2.train_id]):
                        
                        for t in range(len(time_slots) - headway):
                            # If train1 occupies at time t, train2 cannot occupy for headway period
                            for h in range(1, headway + 1):
                                if t + h < len(time_slots):
                                    model.AddImplication(
                                        x[train1.train_id][track.segment_id][t],
                                        x[train2.train_id][track.segment_id][t + h].Not()
                                    )
    
    def _add_platform_constraints(self, model: cp_model.CpModel, trains: List[TrainData], p: Dict):
        """Add platform assignment constraints"""
        # Group trains by station and time windows
        station_trains = {}
        
        for train in trains:
            for station in train.route:
                if station not in station_trains:
                    station_trains[station] = []
                station_trains[station].append(train)
        
        # Platform conflict constraints
        for station, station_train_list in station_trains.items():
            for i, train1 in enumerate(station_train_list):
                for j, train2 in enumerate(station_train_list):
                    if i >= j:
                        continue
                    
                    # If trains are at station simultaneously, they need different platforms
                    if (train1.train_id in p and station in p[train1.train_id] and
                        train2.train_id in p and station in p[train2.train_id]):
                        
                        # This is a simplified constraint - in reality, you'd need time overlap detection
                        same_platform = model.NewBoolVar(f"same_platform_{train1.train_id}_{train2.train_id}_{station}")
                        model.Add(p[train1.train_id][station] == p[train2.train_id][station]).OnlyEnforceIf(same_platform)
                        model.Add(p[train1.train_id][station] != p[train2.train_id][station]).OnlyEnforceIf(same_platform.Not())
                        
                        # If trains overlap in time at station, they cannot use same platform
                        # This would require more complex time overlap detection in practice
    
    def _add_conflict_constraints(self, model: cp_model.CpModel, trains: List[TrainData], 
                                tracks: List[TrackData], conflicts: List[ConflictData], 
                                x: Dict, c: Dict):
        """Add conflict detection and resolution constraints"""
        time_slots = range(self.config.time_horizon_minutes)
        
        for conflict in conflicts:
            if conflict.conflict_type == ConflictType.TRACK_OCCUPATION.value:
                # Track occupation conflict
                conflict_trains = conflict.train_ids
                resource_id = conflict.resource_id
                
                # Find the track
                track = next((t for t in tracks if t.segment_id == resource_id), None)
                if not track:
                    continue
                
                for t in time_slots:
                    # Count trains occupying the resource
                    occupancy_vars = []
                    for train_id in conflict_trains:
                        if (train_id in x and resource_id in x[train_id]):
                            occupancy_vars.append(x[train_id][resource_id][t])
                    
                    if len(occupancy_vars) > 1:
                        # Conflict occurs if more than capacity trains occupy resource
                        total_occupancy = sum(occupancy_vars)
                        
                        # No conflict if occupancy <= capacity
                        model.Add(total_occupancy <= track.capacity).OnlyEnforceIf(c[conflict.conflict_id].Not())
                        
                        # Conflict if occupancy > capacity
                        model.Add(total_occupancy >= track.capacity + 1).OnlyEnforceIf(c[conflict.conflict_id])
    
    def _add_timing_constraints(self, model: cp_model.CpModel, trains: List[TrainData], 
                              x: Dict, s: Dict, j: Dict):
        """Add timing and scheduling constraints"""
        time_slots = range(self.config.time_horizon_minutes)
        
        for train in trains:
            # Journey completion time constraint
            route_segments = self._get_route_segments_from_train(train)
            
            if route_segments:
                last_segment = route_segments[-1]
                if last_segment in x[train.train_id]:
                    # Journey completion time is when train exits last segment
                    for t in time_slots:
                        # If train is in last segment at time t but not at t+1, journey completes at t+1
                        if t < len(time_slots) - 1:
                            completing = model.NewBoolVar(f"completing_{train.train_id}_{t}")
                            model.Add(x[train.train_id][last_segment][t] == 1).OnlyEnforceIf(completing)
                            model.Add(x[train.train_id][last_segment][t + 1] == 0).OnlyEnforceIf(completing)
                            model.Add(j[train.train_id] == t + 1).OnlyEnforceIf(completing)
            
            # Start delay constraint - train cannot start before its scheduled time + delay
            scheduled_start_minutes = self._get_scheduled_start_minutes(train)
            if scheduled_start_minutes is not None:
                # First segment occupation must be after scheduled start + delay
                route_segments = self._get_route_segments_from_train(train)
                if route_segments:
                    first_segment = route_segments[0]
                    if first_segment in x[train.train_id]:
                        for t in time_slots:
                            if t < scheduled_start_minutes:
                                model.Add(x[train.train_id][first_segment][t] == 0)
                            elif t >= scheduled_start_minutes:
                                # Can start at scheduled time + delay
                                can_start = model.NewBoolVar(f"can_start_{train.train_id}_{t}")
                                model.Add(t >= scheduled_start_minutes + s[train.train_id]).OnlyEnforceIf(can_start)
    
    def _set_objective(self, model: cp_model.CpModel, trains: List[TrainData], 
                      conflicts: List[ConflictData], s: Dict, c: Dict, j: Dict):
        """Set the optimization objective"""
        objective_terms = []
        
        # 1. Minimize delays (weighted by priority)
        for train in trains:
            priority_weight = self.config.delay_weight * (6 - train.priority) * self.config.priority_multiplier
            objective_terms.append(priority_weight * s[train.train_id])
        
        # 2. Minimize journey times
        for train in trains:
            journey_weight = self.config.delay_weight * 0.1  # Small weight for journey time
            objective_terms.append(journey_weight * j[train.train_id])
        
        # 3. Penalize conflicts (heavily weighted)
        for conflict in conflicts:
            conflict_penalty = self.config.conflict_weight * (6 - conflict.severity)
            objective_terms.append(conflict_penalty * c[conflict.conflict_id])
        
        # 4. Minimize total system disruption
        total_delay = sum(s[train.train_id] for train in trains)
        objective_terms.append(self.config.delay_weight * 0.01 * total_delay)
        
        model.Minimize(sum(objective_terms))
    
    def _solve_model(self, model: cp_model.CpModel, warm_start: Optional[List[ScheduleEntry]] = None) -> Optional[cp_model.CpSolver]:
        """Solve the optimization model"""
        solver = cp_model.CpSolver()
        
        # Solver parameters
        solver.parameters.max_time_in_seconds = self.config.max_solve_time_seconds
        solver.parameters.num_search_workers = 4  # Parallel search
        solver.parameters.log_search_progress = True
        
        # Apply warm start if provided
        if warm_start:
            self._apply_warm_start(solver, warm_start)
        
        # Solve
        status = solver.Solve(model)
        
        if status == cp_model.OPTIMAL:
            logger.info(f"Optimal solution found. Objective: {solver.ObjectiveValue()}")
            return solver
        elif status == cp_model.FEASIBLE:
            logger.info(f"Feasible solution found. Objective: {solver.ObjectiveValue()}")
            return solver
        else:
            logger.error(f"Solver failed with status: {solver.StatusName(status)}")
            return None
    
    def _extract_schedule(self, solver: cp_model.CpSolver, trains: List[TrainData], 
                         tracks: List[TrackData]) -> List[ScheduleEntry]:
        """Extract the optimized schedule from solver solution"""
        schedule = []
        x = self.variables['x']
        p = self.variables['p']
        base_time = datetime.now().replace(second=0, microsecond=0)
        
        for train in trains:
            for track in tracks:
                if track.segment_id in x[train.train_id]:
                    start_time = None
                    end_time = None
                    
                    # Find continuous occupation period
                    for t in range(self.config.time_horizon_minutes):
                        if solver.Value(x[train.train_id][track.segment_id][t]) == 1:
                            if start_time is None:
                                start_time = base_time + timedelta(minutes=t)
                            end_time = base_time + timedelta(minutes=t + 1)
                        elif start_time is not None:
                            # End of occupation period
                            break
                    
                    if start_time and end_time:
                        # Get platform assignment if available
                        platform = None
                        for station_code in train.route:
                            if (train.train_id in p and station_code in p[train.train_id]):
                                platform = solver.Value(p[train.train_id][station_code])
                                break
                        
                        schedule.append(ScheduleEntry(
                            train_id=train.train_id,
                            segment_id=track.segment_id,
                            start_time=start_time,
                            end_time=end_time,
                            platform=platform
                        ))
        
        return sorted(schedule, key=lambda x: x.start_time)
    
    def _calculate_metrics(self, solver: cp_model.CpSolver, trains: List[TrainData], 
                          conflicts: List[ConflictData]) -> Dict[str, float]:
        """Calculate optimization metrics"""
        s = self.variables['s']
        c = self.variables['c']
        j = self.variables['j']
        
        total_delay = sum(solver.Value(s[train.train_id]) for train in trains)
        conflicts_resolved = sum(1 for conflict in conflicts if solver.Value(c[conflict.conflict_id]) == 0)
        objective_value = solver.ObjectiveValue()
        
        return {
            'objective_value': objective_value,
            'total_delay': total_delay,
            'conflicts_resolved': conflicts_resolved,
            'average_delay': total_delay / len(trains) if trains else 0,
            'average_journey_time': sum(solver.Value(j[train.train_id]) for train in trains) / len(trains) if trains else 0
        }
    
    def _get_route_segments(self, train: TrainData, tracks: List[TrackData]) -> List[str]:
        """Get route segments for a train based on its route and available tracks"""
        segments = []
        route_stations = train.route
        
        for i in range(len(route_stations) - 1):
            from_station = route_stations[i]
            to_station = route_stations[i + 1]
            
            # Find track segment connecting these stations
            for track in tracks:
                if ((track.from_station == from_station and track.to_station == to_station) or
                    (track.from_station == to_station and track.to_station == from_station)):
                    segments.append(track.segment_id)
                    break
        
        return segments
    
    def _get_route_segments_from_train(self, train: TrainData) -> List[str]:
        """Extract route segments from train data"""
        # This is a simplified version - in practice, you'd have more complex route mapping
        return [f"{train.route[i]}-{train.route[i+1]}" for i in range(len(train.route) - 1)]
    
    def _get_scheduled_start_minutes(self, train: TrainData) -> Optional[int]:
        """Get scheduled start time in minutes from base time"""
        if train.scheduled_arrival:
            base_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            return int((train.scheduled_arrival - base_time).total_seconds() / 60)
        return None
    
    def _apply_warm_start(self, solver: cp_model.CpSolver, warm_start: List[ScheduleEntry]):
        """Apply warm start solution to solver"""
        # This is a placeholder for warm start implementation
        # In practice, you'd map the warm start solution to decision variables
        logger.info(f"Applying warm start with {len(warm_start)} schedule entries")
        pass

class GurobiOptimizer(RailwayOptimizer):
    """Alternative optimizer using Gurobi (if available)"""
    
    def __init__(self, config: OptimizationConfig = None):
        super().__init__("gurobi", config)
        try:
            import gurobipy as gp
            self.gurobi_available = True
        except ImportError:
            self.gurobi_available = False
            logger.warning("Gurobi not available, falling back to OR-Tools")
    
    def is_ready(self) -> bool:
        return self.gurobi_available
    
    def optimize(self, trains: List[TrainData], tracks: List[TrackData], 
                conflicts: List[ConflictData], time_horizon: int = 240,
                warm_start: Optional[List[ScheduleEntry]] = None) -> OptimizationResult:
        """Optimize using Gurobi MILP solver"""
        if not self.gurobi_available:
            # Fall back to OR-Tools
            return super().optimize(trains, tracks, conflicts, time_horizon, warm_start)
        
        # Gurobi implementation would go here
        # For now, fall back to OR-Tools
        logger.info("Using Gurobi optimizer (placeholder - falling back to OR-Tools)")
        return super().optimize(trains, tracks, conflicts, time_horizon, warm_start)
