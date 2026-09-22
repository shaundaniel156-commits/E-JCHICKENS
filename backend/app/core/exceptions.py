"""Domain exceptions and the handlers that turn them into clean API responses."""
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base class for every expected, user-facing error."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "app_error"

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ValidationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "validation_error"


class ConflictError(AppError):
    """Business-rule conflict, e.g. selling more birds than the batch holds."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class DuplicateError(ConflictError):
    code = "duplicate"


class InsufficientStockError(ConflictError):
    code = "insufficient_stock"


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "authentication_error"


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "permission_denied"


def _payload(code: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    body: Dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        logger.warning("%s on %s: %s", exc.code, request.url.path, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else "Request could not be completed."
        return JSONResponse(status_code=exc.status_code, content=_payload("http_error", detail))

    @app.exception_handler(RequestValidationError)
    async def _request_validation(request: Request, exc: RequestValidationError):
        fields = {}
        for error in exc.errors():
            location = [str(part) for part in error["loc"] if part not in ("body", "query", "path")]
            fields[".".join(location) or "request"] = error["msg"]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_payload("validation_error", "Please correct the highlighted fields.", fields),
        )

    @app.exception_handler(IntegrityError)
    async def _integrity(request: Request, exc: IntegrityError):
        logger.error("Integrity error on %s: %s", request.url.path, exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_payload(
                "integrity_error",
                "That operation conflicts with existing data (a duplicate or a record still in use).",
            ),
        )

    @app.exception_handler(OperationalError)
    @app.exception_handler(DBAPIError)
    async def _database_unavailable(request: Request, exc: DBAPIError):
        logger.error("Database error on %s: %s", request.url.path, exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=_payload(
                "database_error",
                "The database is not reachable right now. Please try again in a moment.",
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def _database_error(request: Request, exc: SQLAlchemyError):
        # Not a connectivity problem — a query or mapping fault, i.e. a defect.
        logger.exception("Query error on %s", request.url.path)
        message = str(exc) if settings.DEBUG else "Something went wrong on our side."
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_payload("server_error", message),
        )

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s", request.url.path)
        message = str(exc) if settings.DEBUG else "Something went wrong on our side."
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_payload("server_error", message),
        )
