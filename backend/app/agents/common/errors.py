"""Turn any exception raised during an agent run into the API error codes (api-contract)."""

import httpx2
import openai

from app.core.errors import DomainError, UpstreamUnavailableError

# OpenAI or the Intelligence MCP could not be reached or is overloaded.
UPSTREAM_ERRORS: tuple[type[Exception], ...] = (
    openai.APIConnectionError,  # includes APITimeoutError
    openai.RateLimitError,
    openai.InternalServerError,
    httpx2.HTTPError,  # the transport used by the MCP client
    ConnectionError,
)


class CancelledRunError(DomainError):
    code = "CANCELLED"


class UngroundedOutputError(DomainError):
    """Cited evidence was not retrieved in the run, even after the repair."""

    code = "UNGROUNDED_OUTPUT"


class InvalidOutputError(DomainError):
    """The output broke its contract, even after the repair."""

    code = "INVALID_OUTPUT"


def run_error(exc: Exception) -> DomainError:
    """A domain error with a user-safe message; unexpected errors never leak their text."""
    if isinstance(exc, DomainError):
        return exc
    if isinstance(exc, openai.APIStatusError):  # a bad key, no quota, a rejected request
        return UpstreamUnavailableError(f"OpenAI request failed: {exc.message}")
    upstream = isinstance(exc, UPSTREAM_ERRORS) or (
        isinstance(exc, ExceptionGroup) and exc.subgroup(UPSTREAM_ERRORS) is not None
    )
    if upstream:
        return UpstreamUnavailableError(
            f"OpenAI or the Intelligence MCP is unavailable ({type(exc).__name__})"
        )
    return DomainError("The run failed unexpectedly. The error has been logged.")


class UnoriginalOutputError(DomainError):
    """The deliverable still copies its source after the repair; no copy is returned."""

    code = "UNORIGINAL_OUTPUT"
