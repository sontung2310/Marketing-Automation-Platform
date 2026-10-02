"""Vercel entrypoint: the API project (root directory `backend/`) serves this ASGI app."""

from app.api.main import app

__all__ = ["app"]
