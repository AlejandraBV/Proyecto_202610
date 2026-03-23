"""
Custom error handling middleware
"""
import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handler middleware for unhandled exceptions"""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except ValueError as e:
            logger.warning(f"Validation error on {request.url}: {e}")
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": str(e)},
            )
        except PermissionError as e:
            logger.warning(f"Permission denied on {request.url}: {e}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": str(e)},
            )
        except Exception as e:
            logger.error(f"Unhandled error on {request.url}: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"},
            )
