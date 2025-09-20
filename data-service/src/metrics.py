from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Response
import time

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_TRAINS = Gauge('active_trains_total', 'Number of active trains')
DELAYED_TRAINS = Gauge('delayed_trains_total', 'Number of delayed trains')
DATABASE_CONNECTIONS = Gauge('database_connections_active', 'Active database connections')

def record_request_metrics(method: str, endpoint: str, status_code: int, duration: float):
    """Record request metrics"""
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=str(status_code)).inc()
    REQUEST_DURATION.observe(duration)

def update_train_metrics(active_count: int, delayed_count: int):
    """Update train-related metrics"""
    ACTIVE_TRAINS.set(active_count)
    DELAYED_TRAINS.set(delayed_count)

def get_metrics():
    """Return Prometheus metrics"""
    return Response(generate_latest(), media_type="text/plain")
