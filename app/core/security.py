"""Security middleware for X-FAMILY-KEY authentication."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings

# Paths that bypass authentication (for development convenience)
PUBLIC_PATHS: frozenset[str] = frozenset({
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/",
})


class FamilyKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate X-FAMILY-KEY header on all requests.
    
    This provides a lightweight static key authentication suitable for
    home server applications where complex auth flows are not needed.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process each request and validate the API key."""
        # Allow public paths without authentication
        if self._is_public_path(request.url.path):
            return await call_next(request)

        # Extract and validate the API key
        api_key = request.headers.get("X-FAMILY-KEY")

        if not api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Missing X-FAMILY-KEY header",
                    "error_code": "AUTH_MISSING_KEY",
                },
            )

        if api_key != settings.FAMILY_API_KEY:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Invalid X-FAMILY-KEY",
                    "error_code": "AUTH_INVALID_KEY",
                },
            )

        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """Check if the path should bypass authentication."""
        # Exact match for public paths
        if path in PUBLIC_PATHS:
            return True
        
        # Allow OpenAPI schema paths
        if path.startswith("/docs") or path.startswith("/redoc"):
            return True

        return False
