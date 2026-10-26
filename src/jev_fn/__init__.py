"""A small Python wrapper for TypeSafe's Jev semantic scoring function."""

from .config import configure
from .core import ajev, context, jev
from .exceptions import ConfigurationError, JevError, ParseError, ProviderError

__all__ = [
    "jev",
    "ajev",
    "configure",
    "context",
    "JevError",
    "ConfigurationError",
    "ParseError",
    "ProviderError",
]
__version__ = "0.1.0"
