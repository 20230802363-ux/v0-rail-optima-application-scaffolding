from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import logging
import os

from .schemas import ScheduleRequest, ScheduleResponse, OptimizationResult
from .optimizer import RailwayOptimizer

app = FastAPI(
    title="RailOptima Optimization Engine",
    description="Railway scheduling optimization service using OR-Tools",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize optimizer
SOLVER_TYPE = os.getenv("SOLVER_TYPE", "ortools")  # ortools or gurobi
optimizer = RailwayOptimizer(solver_type=SOLVER_TYPE)

@app.get("/")
async def root():
    return {"message": "RailOptima Optimization Engine", "version": "1.0.0", "solver": SOLVER_TYPE}

@app.post("/schedule", response_model=ScheduleResponse)
async def optimize_schedule(request: ScheduleRequest):
    """
    Optimize railway schedule based on current positions, delays, and priorities
    """
    try:
        logger.info(f"Received optimization request for {len(request.trains)} trains")
        
        # Run optimization
        result = optimizer.optimize(
            trains=request.trains,
            tracks=request.tracks,
            conflicts=request.conflicts,
            time_horizon=request.time_horizon_minutes,
            warm_start=request.warm_start_solution
        )
        
        logger.info(f"Optimization completed. Objective value: {result.objective_value}")
        
        return ScheduleResponse(
            success=True,
            optimized_schedule=result.schedule,
            objective_value=result.objective_value,
            solve_time_seconds=result.solve_time,
            conflicts_resolved=result.conflicts_resolved,
            total_delay_minutes=result.total_delay_minutes
        )
        
    except Exception as e:
        logger.error(f"Optimization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "solver": SOLVER_TYPE,
        "optimizer_ready": optimizer.is_ready()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
