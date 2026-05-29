"""Security middleware for X-FAMILY-KEY authentication."""

import hmac

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings

# Paths that bypass authentication for liveness and optional documentation.
PUBLIC_PATHS: frozenset[str] = frozenset(
    {
        "/health",
        "/",
    }
)
DOCS_PATH_PREFIXES: tuple[str, ...] = ("/docs", "/redoc")
DOCS_PATHS: frozenset[str] = frozenset({"/openapi.json"})


class FamilyKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate X-FAMILY-KEY header on protected requests.

    This provides lightweight static-key authentication suitable for home server
    deployments where complex auth flows are not needed.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process each request and validate the API key."""
        if self._is_public_path(request.url.path):
            return await call_next(request)

        configured_key = settings.FAMILY_API_KEY
        if not configured_key:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "API authentication is not configured",
                    "error_code": "AUTH_NOT_CONFIGURED",
                },
            )

        api_key = request.headers.get("X-FAMILY-KEY")
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Missing X-FAMILY-KEY header",
                    "error_code": "AUTH_MISSING_KEY",
                },
            )

        if not hmac.compare_digest(api_key, configured_key):
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
        if path in PUBLIC_PATHS:
            return True

        if settings.docs_enabled and (
            path in DOCS_PATHS or path.startswith(DOCS_PATH_PREFIXES)
        ):
            return True

        return False
