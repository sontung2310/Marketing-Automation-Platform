"""Hand the OpenAI key from settings to the Agents SDK (it otherwise reads only os.environ)."""

from functools import cache

from agents import set_default_openai_key

from app.core.config import get_settings
from app.core.errors import UpstreamUnavailableError


@cache
def configure_openai() -> None:
    key = get_settings().openai_api_key
    if key is None:
        raise UpstreamUnavailableError("OPENAI_API_KEY is not configured")
    set_default_openai_key(key.get_secret_value(), use_for_tracing=False)
