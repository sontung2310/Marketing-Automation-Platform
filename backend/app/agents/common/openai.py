"""Per-run OpenAI client and model provider built from settings.

The SDK's default provider shares one module-level HTTP client, which stays bound to the
first event loop that used it. An own client per run avoids that and is closed afterwards.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from agents.models.openai_provider import OpenAIProvider
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.errors import UpstreamUnavailableError


@asynccontextmanager
async def model_provider() -> AsyncIterator[OpenAIProvider]:
    key = get_settings().openai_api_key
    if key is None:
        raise UpstreamUnavailableError("OPENAI_API_KEY is not configured")
    async with AsyncOpenAI(api_key=key.get_secret_value()) as client:
        yield OpenAIProvider(openai_client=client)
