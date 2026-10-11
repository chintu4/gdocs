"""gdocs - A lightweight Python client for Google Docs."""

from .main import (
    AuthStrategy,
    DefaultAuthStrategy,
    GoogleDocsService,
)

__all__ = [
    "GoogleDocsService",
    "AuthStrategy",
    "DefaultAuthStrategy",
]
