"""
Request ID Middleware

Adds unique request IDs to all requests for log correlation.
Also extracts session ID from headers if provided by frontend.
"""

import uuid
import logging
import contextvars
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variables for request-scoped values
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('request_id', default='')
session_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('session_id', default='')

logger = logging.getLogger(__name__)


def get_request_id() -> str:
    """Get current request ID from context."""
    return request_id_var.get()


def get_session_id() -> str:
    """Get current session ID from context (if provided by frontend)."""
    return session_id_var.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds request ID to all requests.
    
    Features:
    - Generates UUID for each request
    - Extracts session ID from X-Session-ID header (if provided)
    - Stores both in context variables for logging
    - Adds X-Request-ID to response headers
    
    Usage:
        app.add_middleware(RequestIDMiddleware)
        
        # In any handler or function:
        from api.utils.request_id import get_request_id, get_session_id
        logger.info(f"[{get_request_id()}] Processing request")
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())[:8]
        
        # Extract session ID if provided by frontend
        session_id = request.headers.get('X-Session-ID', '')
        
        # Set context variables
        request_id_token = request_id_var.set(request_id)
        session_id_token = session_id_var.set(session_id)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add request ID to response headers
            response.headers['X-Request-ID'] = request_id
            
            return response
        finally:
            # Reset context variables
            request_id_var.reset(request_id_token)
            session_id_var.reset(session_id_token)


class RequestIDLogFilter(logging.Filter):
    """
    Logging filter that adds request_id and session_id to log records.
    
    Usage:
        handler = logging.StreamHandler()
        handler.addFilter(RequestIDLogFilter())
        handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(request_id)s] %(levelname)s: %(message)s'
        ))
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or '-'
        record.session_id = get_session_id() or '-'
        return True


def setup_request_id_logging(log_format: Optional[str] = None):
    """
    Configure root logger to include request IDs.
    
    Args:
        log_format: Custom format string. Use %(request_id)s and %(session_id)s.
                   Default: '%(asctime)s [%(request_id)s] %(name)s %(levelname)s: %(message)s'
    """
    if log_format is None:
        log_format = '%(asctime)s [%(request_id)s] %(name)s %(levelname)s: %(message)s'
    
    # Get root logger
    root_logger = logging.getLogger()
    
    # Add filter to all handlers
    log_filter = RequestIDLogFilter()
    for handler in root_logger.handlers:
        handler.addFilter(log_filter)
        handler.setFormatter(logging.Formatter(log_format))
    
    # If no handlers, add one
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.addFilter(log_filter)
        handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(handler)
