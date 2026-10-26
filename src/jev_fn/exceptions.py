"""Exceptions raised by jev-fn."""


class JevError(Exception):
    """Base exception for the library."""


class ConfigurationError(JevError, ValueError):
    """Raised when configuration is invalid or incomplete."""


class ParseError(JevError, ValueError):
    """Raised when a provider response does not contain a valid score."""


class ProviderError(JevError, RuntimeError):
    """Raised when a provider SDK fails to return a usable response."""
