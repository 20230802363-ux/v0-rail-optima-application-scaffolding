import pytest
from src.utils import calculate_distance, estimate_travel_time, validate_timetable_consistency

def test_calculate_distance():
    # Distance between New Delhi and Ghaziabad (approximately 46 km)
    distance = calculate_distance(28.6448, 77.2097, 28.6692, 77.4538)
    assert 40 <= distance <= 50  # Allow some tolerance

def test_estimate_travel_time():
    # Test express train
    time_express = estimate_travel_time(100, 120, "express")
    assert 60 <= time_express <= 120  # Should be reasonable
    
    # Test passenger train (should be slower)
    time_passenger = estimate_travel_time(100, 120, "passenger")
    assert time_passenger > time_express

def test_validate_timetable_consistency():
    # Valid timetable
    valid_entries = [
        {
            "train_number": "12004",
            "station_code": "NDLS",
            "departure_time": "2024-01-01T06:00:00",
            "arrival_time": "2024-01-01T06:00:00"
        },
        {
            "train_number": "12004",
            "station_code": "GZB",
            "departure_time": "2024-01-01T07:00:00",
            "arrival_time": "2024-01-01T06:45:00"
        }
    ]
    
    errors = validate_timetable_consistency(valid_entries)
    assert len(errors) == 0
    
    # Invalid timetable (departure before arrival)
    invalid_entries = [
        {
            "train_number": "12004",
            "station_code": "NDLS",
            "departure_time": "2024-01-01T08:00:00",
            "arrival_time": "2024-01-01T06:00:00"
        },
        {
            "train_number": "12004",
            "station_code": "GZB",
            "departure_time": "2024-01-01T07:00:00",
            "arrival_time": "2024-01-01T06:45:00"
        }
    ]
    
    errors = validate_timetable_consistency(invalid_entries)
    assert len(errors) > 0
