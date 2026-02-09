"""Custom exceptions and exception handlers for the API."""

from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class FamilyCentralException(Exception):
    """Base exception for FamilyCentralAPI."""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(FamilyCentralException):
    """Resource not found."""

    def __init__(
        self,
        resource: str,
        identifier: Any,
    ) -> None:
        super().__init__(
            message=f"{resource} with id '{identifier}' not found",
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
            details={"resource": resource, "identifier": str(identifier)},
        )


class DuplicateError(FamilyCentralException):
    """Resource already exists."""

    def __init__(
        self,
        resource: str,
        field: str,
        value: Any,
    ) -> None:
        super().__init__(
            message=f"{resource} with {field}='{value}' already exists",
            error_code="RESOURCE_DUPLICATE",
            status_code=409,
            details={"resource": resource, "field": field, "value": str(value)},
        )


class ValidationError(FamilyCentralException):
    """Validation error."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )


async def family_central_exception_handler(
    request: Request,
    exc: FamilyCentralException,
) -> JSONResponse:
    """Handle FamilyCentralException instances."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
        },
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """Handle standard HTTPException instances."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": "HTTP_ERROR",
        },
    )
