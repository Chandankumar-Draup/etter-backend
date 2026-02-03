"""
Middleware to log HTTP requests to Datadog with structured fields.
This provides detailed request/response logging similar to Jaeger traces.
"""
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger("etter_app")


class DatadogLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs HTTP requests to Datadog with structured fields.
    Similar to how Jaeger traces work, this provides detailed request/response info.
    """
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Extract request details
        method = request.method
        path = request.url.path
        query_params = str(request.query_params) if request.query_params else ""
        client_ip = request.client.host if request.client else "unknown"
        client_port = request.client.port if request.client else 0
        
        # Skip health checks (too noisy)
        if path == "/health" or path == "/api/health":
            response = await call_next(request)
            return response
        
        # Log request start (using extra dict for structured logging)
        logger.info(
            f"{method} {path}",
            extra={
                "http.method": method,
                "http.url": path,
                "http.url_details.path": path,
                "http.url_details.query_string": query_params,
                "http.client_ip": client_ip,
                "http.client_port": client_port,
                "http.request_id": request.headers.get("X-Request-ID", ""),
                "event_type": "http_request_start",
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            duration_ms = (time.time() - start_time) * 1000
            
            # Log request completion with response details
            logger.info(
                f"{method} {path} {status_code}",
                extra={
                    "http.method": method,
                    "http.url": path,
                    "http.url_details.path": path,
                    "http.url_details.query_string": query_params,
                    "http.status_code": status_code,
                    "http.client_ip": client_ip,
                    "http.client_port": client_port,
                    "http.request_id": request.headers.get("X-Request-ID", ""),
                    "duration_ms": round(duration_ms, 2),
                    "event_type": "http_request_complete",
                }
            )
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            status_code = 500
            
            # Log error
            logger.error(
                f"{method} {path} {status_code} - {str(e)}",
                extra={
                    "http.method": method,
                    "http.url": path,
                    "http.url_details.path": path,
                    "http.status_code": status_code,
                    "http.client_ip": client_ip,
                    "http.client_port": client_port,
                    "duration_ms": round(duration_ms, 2),
                    "error.message": str(e),
                    "error.type": type(e).__name__,
                    "event_type": "http_request_error",
                },
                exc_info=True
            )
            
            raise

