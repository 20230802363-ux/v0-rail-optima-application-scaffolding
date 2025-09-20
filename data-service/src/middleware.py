from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
import time
import logging
import uuid

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Log request
        start_time = time.time()
        logger.info(f"Request {request_id}: {request.method} {request.url}")
        
        # Process request
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(f"Request {request_id}: {response.status_code} - {process_time:.3f}s")
        
        # Add headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response

class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.request_count = 0
        self.request_duration = []
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        # Update metrics
        self.request_count += 1
        duration = time.time() - start_time
        self.request_duration.append(duration)
        
        # Keep only last 1000 requests for memory efficiency
        if len(self.request_duration) > 1000:
            self.request_duration = self.request_duration[-1000:]
        
        return response
    
    def get_metrics(self):
        return {
            "total_requests": self.request_count,
            "avg_response_time": sum(self.request_duration) / len(self.request_duration) if self.request_duration else 0,
            "recent_requests": len(self.request_duration)
        }
