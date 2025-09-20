from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging
import time

from .database import get_db, engine
from .models import Base
from .schemas import (
    TopologyUpload, TimetableUpload, PositionUpdate, 
    StatusResponse, TopologyResponse
)
from .crud import (
    create_topology, create_timetable_entry, 
    update_train_position, get_system_status
)
from .middleware import LoggingMiddleware, MetricsMiddleware
from .metrics import record_request_metrics, get_metrics
from .utils import generate_train_status_summary

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="RailOptima Data Service",
    description="Data ingestion and management service for railway operations",
    version="1.0.0"
)

# Add middleware
metrics_middleware = MetricsMiddleware(app)
app.add_middleware(LoggingMiddleware)

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

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Record metrics
    record_request_metrics(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code,
        duration=process_time
    )
    
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.get("/")
async def root():
    return {"message": "RailOptima Data Service", "version": "1.0.0"}

@app.post("/topology", response_model=TopologyResponse)
async def upload_topology(
    topology: TopologyUpload,
    db: Session = Depends(get_db)
):
    """Upload network topology (stations, signals, tracks)"""
    try:
        result = create_topology(db, topology)
        logger.info(f"Topology uploaded: {len(topology.stations)} stations, {len(topology.tracks)} tracks")
        return result
    except Exception as e:
        logger.error(f"Error uploading topology: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/timetable")
async def upload_timetable(
    timetable: TimetableUpload,
    db: Session = Depends(get_db)
):
    """Upload static timetable data"""
    try:
        result = create_timetable_entry(db, timetable)
        logger.info(f"Timetable uploaded: {len(timetable.entries)} entries")
        return {"message": "Timetable uploaded successfully", "entries_count": len(timetable.entries)}
    except Exception as e:
        logger.error(f"Error uploading timetable: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/positions")
async def ingest_positions(
    positions: List[PositionUpdate],
    db: Session = Depends(get_db)
):
    """Ingest real-time GPS/SCADA feed"""
    try:
        updated_count = 0
        for position in positions:
            update_train_position(db, position)
            updated_count += 1
        
        logger.info(f"Updated positions for {updated_count} trains")
        return {"message": f"Updated {updated_count} train positions"}
    except Exception as e:
        logger.error(f"Error updating positions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status", response_model=StatusResponse)
async def get_status(db: Session = Depends(get_db)):
    """Get system health and current counts"""
    try:
        status = get_system_status(db)
        return status
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/summary")
async def get_summary(db: Session = Depends(get_db)):
    """Get detailed system summary with train status breakdown"""
    try:
        summary = generate_train_status_summary(db)
        return summary
    except Exception as e:
        logger.error(f"Error getting summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return get_metrics()

@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "data-service",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
