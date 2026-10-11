"""gdocs - A lightweight Python client for Google Docs."""

from .main import (
    AuthStrategy,
    DefaultAuthStrategy,
    GoogleDocsClient,
    OAuthAuthStrategy,
    ServiceAccountAuthStrategy,
)

__version__ = "0.1.0"

__all__ = [
    "GoogleDocsClient",
    "AuthStrategy",
    "DefaultAuthStrategy",
    "ServiceAccountAuthStrategy",
    "OAuthAuthStrategy",
]
