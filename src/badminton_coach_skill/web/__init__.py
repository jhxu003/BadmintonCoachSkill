"""Web application runtime for temporary badminton video analysis jobs."""

from .app import create_app
from .settings import Settings

__all__ = ["create_app", "Settings"]
