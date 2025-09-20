import time
import logging
from typing import Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
import json

logger = logging.getLogger(__name__)

@dataclass
class OptimizationMetrics:
    """Metrics for optimization performance monitoring"""
    start_time: datetime
    end_time: datetime = None
    solve_time_seconds: float = 0.0
    objective_value: float = 0.0
    num_trains: int = 0
    num_tracks: int = 0
    num_conflicts: int = 0
    conflicts_resolved: int = 0
    total_delay_minutes: int = 0
    solver_status: str = ""
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    variables_count: int = 0
    constraints_count: int = 0
    
class PerformanceMonitor:
    """Monitor and track optimization performance"""
    
    def __init__(self):
        self.metrics_history: List[OptimizationMetrics] = []
        self.current_metrics: OptimizationMetrics = None
        
    def start_optimization(self, num_trains: int, num_tracks: int, num_conflicts: int):
        """Start monitoring an optimization run"""
        self.current_metrics = OptimizationMetrics(
            start_time=datetime.now(),
            num_trains=num_trains,
            num_tracks=num_tracks,
            num_conflicts=num_conflicts
        )
        
        logger.info(f"Started optimization monitoring: {num_trains} trains, {num_tracks} tracks, {num_conflicts} conflicts")
    
    def end_optimization(self, objective_value: float, conflicts_resolved: int, 
                        total_delay: int, solver_status: str):
        """End monitoring and record final metrics"""
        if not self.current_metrics:
            return
        
        self.current_metrics.end_time = datetime.now()
        self.current_metrics.solve_time_seconds = (
            self.current_metrics.end_time - self.current_metrics.start_time
        ).total_seconds()
        self.current_metrics.objective_value = objective_value
        self.current_metrics.conflicts_resolved = conflicts_resolved
        self.current_metrics.total_delay_minutes = total_delay
        self.current_metrics.solver_status = solver_status
        
        # Record system metrics
        self.current_metrics.memory_usage_mb = self._get_memory_usage()
        self.current_metrics.cpu_usage_percent = self._get_cpu_usage()
        
        # Add to history
        self.metrics_history.append(self.current_metrics)
        
        # Keep only last 100 runs
        if len(self.metrics_history) > 100:
            self.metrics_history = self.metrics_history[-100:]
        
        logger.info(f"Optimization completed in {self.current_metrics.solve_time_seconds:.2f}s")
        
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics"""
        if not self.metrics_history:
            return {"message": "No optimization runs recorded"}
        
        recent_runs = self.metrics_history[-10:]  # Last 10 runs
        
        avg_solve_time = sum(m.solve_time_seconds for m in recent_runs) / len(recent_runs)
        avg_objective = sum(m.objective_value for m in recent_runs) / len(recent_runs)
        avg_conflicts_resolved = sum(m.conflicts_resolved for m in recent_runs) / len(recent_runs)
        
        success_rate = sum(1 for m in recent_runs if m.solver_status in ["OPTIMAL", "FEASIBLE"]) / len(recent_runs)
        
        return {
            "total_runs": len(self.metrics_history),
            "recent_runs": len(recent_runs),
            "average_solve_time_seconds": round(avg_solve_time, 2),
            "average_objective_value": round(avg_objective, 2),
            "average_conflicts_resolved": round(avg_conflicts_resolved, 1),
            "success_rate_percent": round(success_rate * 100, 1),
            "last_run": {
                "solve_time": self.metrics_history[-1].solve_time_seconds,
                "objective": self.metrics_history[-1].objective_value,
                "status": self.metrics_history[-1].solver_status,
                "trains": self.metrics_history[-1].num_trains,
                "conflicts_resolved": self.metrics_history[-1].conflicts_resolved
            }
        }
    
    def get_detailed_metrics(self) -> List[Dict[str, Any]]:
        """Get detailed metrics for all runs"""
        return [
            {
                "timestamp": m.start_time.isoformat(),
                "solve_time_seconds": m.solve_time_seconds,
                "objective_value": m.objective_value,
                "num_trains": m.num_trains,
                "num_tracks": m.num_tracks,
                "num_conflicts": m.num_conflicts,
                "conflicts_resolved": m.conflicts_resolved,
                "total_delay_minutes": m.total_delay_minutes,
                "solver_status": m.solver_status,
                "memory_usage_mb": m.memory_usage_mb,
                "variables_count": m.variables_count,
                "constraints_count": m.constraints_count
            }
            for m in self.metrics_history
        ]
    
    def export_metrics(self, filename: str):
        """Export metrics to JSON file"""
        metrics_data = {
            "export_timestamp": datetime.now().isoformat(),
            "total_runs": len(self.metrics_history),
            "summary": self.get_performance_summary(),
            "detailed_metrics": self.get_detailed_metrics()
        }
        
        with open(filename, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        
        logger.info(f"Metrics exported to {filename}")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except ImportError:
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except ImportError:
            return 0.0
    
    def set_model_complexity(self, variables_count: int, constraints_count: int):
        """Set model complexity metrics"""
        if self.current_metrics:
            self.current_metrics.variables_count = variables_count
            self.current_metrics.constraints_count = constraints_count

# Global performance monitor instance
performance_monitor = PerformanceMonitor()
