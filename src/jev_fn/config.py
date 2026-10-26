"""Configuration for jev-fn."""

from dataclasses import dataclass, replace
from threading import RLock
from typing import Any

from .exceptions import ConfigurationError


@dataclass
class JevConfig:
    model: str = "jev-latest"
    api_key: str | None = None
    base_url: str | None = None   # e.g. "https://openrouter.ai/api" to route via OpenRouter
    cache_enabled: bool = False
    cache_ttl: int = 300
    timeout: float = 30.0


_config = JevConfig()
_config_lock = RLock()


def configure(**kwargs: Any) -> None:
    """Update process-wide configuration.

    Supported keys: model, api_key, base_url, cache_enabled, cache_ttl, timeout.

    - ``model``    — Jev model ID, e.g. ``"jev-latest"`` or ``"jev-1.13"``.
    - ``api_key``  — API key; pass ``None`` to fall back to env-var detection.
    - ``base_url`` — Override the SDK base URL, e.g. ``"https://openrouter.ai/api"``.
                     Pass ``None`` to restore the default (TypeSafe direct).
                     Not needed when using ``OPENROUTER_API_KEY`` — auto-detected.
    - ``cache_enabled`` / ``cache_ttl`` — process-local result cache.
    - ``timeout``  — network timeout in seconds for each SDK call.
    """
    valid_fields = set(JevConfig.__dataclass_fields__)
    unknown = set(kwargs) - valid_fields
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ConfigurationError(f"Unknown configuration key(s): {names}")

    with _config_lock:
        candidate = replace(_config, **kwargs)
        if candidate.model is not None and not candidate.model.strip():
            raise ConfigurationError("model must be a non-empty string or None")
        if candidate.api_key is not None and not candidate.api_key.strip():
            raise ConfigurationError("api_key must be a non-empty string or None")
        if candidate.base_url is not None and not candidate.base_url.strip():
            raise ConfigurationError("base_url must be a non-empty string or None")
        if not isinstance(candidate.cache_enabled, bool):
            raise ConfigurationError("cache_enabled must be a bool")
        if not isinstance(candidate.cache_ttl, int) or isinstance(candidate.cache_ttl, bool) or candidate.cache_ttl < 1:
            raise ConfigurationError("cache_ttl must be a positive integer")
        if not isinstance(candidate.timeout, (int, float)) or isinstance(candidate.timeout, bool) or candidate.timeout <= 0:
            raise ConfigurationError("timeout must be a positive number")
        _config.__dict__.update(candidate.__dict__)


def get_config() -> JevConfig:
    """Return a snapshot so a call uses a consistent configuration."""
    with _config_lock:
        return replace(_config)
