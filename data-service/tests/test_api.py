import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from src.app import app
from src.database import get_db, Base

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "RailOptima Data Service"

def test_upload_topology():
    topology_data = {
        "stations": [
            {
                "code": "NDLS",
                "name": "New Delhi",
                "latitude": 28.6448,
                "longitude": 77.2097,
                "platforms": 16
            }
        ],
        "tracks": [
            {
                "segment_id": "NDLS-GZB-001",
                "from_station": "NDLS",
                "to_station": "GZB",
                "distance_km": 46.0,
                "max_speed_kmh": 130
            }
        ]
    }
    
    response = client.post("/topology", json=topology_data)
    assert response.status_code == 200
    data = response.json()
    assert data["stations_created"] >= 0
    assert data["tracks_created"] >= 0

def test_get_status():
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "total_stations" in data
    assert "total_tracks" in data
