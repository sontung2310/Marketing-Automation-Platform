"""Run failures map to the api-contract error codes without leaking raw text."""

import httpx2
import openai

from app.agents.common.errors import run_error
from app.core.errors import NotFoundError


def test_domain_errors_pass_through() -> None:
    error = NotFoundError("act_1 was not found")
    assert run_error(error) is error


def test_outages_are_upstream_unavailable() -> None:
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    for exc in (
        openai.APIConnectionError(request=request),
        httpx2.ConnectError("refused"),
        ExceptionGroup("mcp", [httpx2.ReadTimeout("slow")]),
    ):
        assert run_error(exc).code == "UPSTREAM_UNAVAILABLE"


def test_an_openai_rejection_is_shown_verbatim() -> None:
    """Roadmap 8-B: an invalid key reads "OpenAI request failed: ..." and not a generic failure."""
    response = httpx2.Response(401, request=httpx2.Request("POST", "https://api.openai.com/v1"))
    error = run_error(
        openai.AuthenticationError(
            "Incorrect API key provided: sk-...abcd", response=response, body=None
        )
    )
    assert error.code == "UPSTREAM_UNAVAILABLE"
    assert error.message == "OpenAI request failed: Incorrect API key provided: sk-...abcd"


def test_unexpected_errors_hide_their_message() -> None:
    error = run_error(ValueError("secret-ish internal detail https://internal"))
    assert error.code == "INTERNAL"
    assert "internal detail" not in error.message
