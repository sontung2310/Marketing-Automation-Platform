"""Domain errors. The API maps them to the error envelope in docs/api-contract.md."""

from typing import Any


class DomainError(Exception):
    code = "INTERNAL"
    http_status = 500

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    code = "NOT_FOUND"
    http_status = 404


class ValidationError(DomainError):
    code = "VALIDATION_ERROR"
    http_status = 422


class ConflictError(DomainError):
    code = "CONFLICT"
    http_status = 409


class UpstreamUnavailableError(DomainError):
    code = "UPSTREAM_UNAVAILABLE"
    http_status = 503
