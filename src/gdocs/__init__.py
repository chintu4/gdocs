"""gdocs - A lightweight Python client for Google Docs."""

from .main import (
    AuthStrategy,
    DefaultAuthStrategy,
    GoogleDocsError,
    GoogleDocsService,
)

__all__ = [
    "GoogleDocsService",
    "AuthStrategy",
    "DefaultAuthStrategy",
    "GoogleDocsError",
]
