"""Public evaluation functions — sync and async."""

import os
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator

from typesafe_sdk import AsyncTypeSafeClient, Noul, TypeSafeClient

from .cache import get_cached, make_key, set_cached
from .config import get_config
from .exceptions import ConfigurationError, ParseError, ProviderError

_context_var: ContextVar[str | None] = ContextVar("jev_fn_context", default=None)


@contextmanager
def context(value: str) -> Iterator[None]:
    """Temporarily set context for calls to ``jev`` / ``ajev`` inside the with-block."""
    if not isinstance(value, str):
        raise TypeError("context value must be a string")
    token: Token[str | None] = _context_var.set(value)
    try:
        yield
    finally:
        _context_var.reset(token)


def _resolve(
    query: str,
    context_arg: str | None,
    ctx: str | None,
) -> tuple[str, str | None]:
    """Validate inputs and resolve the final context value."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if context_arg is not None and ctx is not None:
        raise TypeError("Pass either context= or ctx=, not both")
    explicit = ctx if ctx is not None else context_arg
    if explicit is not None and not isinstance(explicit, str):
        raise TypeError("context must be a string or None")
    resolved = explicit if explicit is not None else _context_var.get()
    return query, resolved


_OPENROUTER_BASE_URL = "https://openrouter.ai/api"


def _resolve_backend(config) -> tuple[str, str | None]:
    """Return (api_key, base_url).

    Priority:
    1. Explicit configure(api_key=..., base_url=...) — full user control.
    2. OPENROUTER_API_KEY env var — auto-routes to OpenRouter.
    3. TYPESAFE_API_KEY env var — routes to TypeSafe directly.

    The base_url is returned as None when using TypeSafe directly (SDK default).
    """
    if config.api_key:
        # User was explicit — respect whatever base_url they set (or None).
        return config.api_key, config.base_url

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        # OPENROUTER_API_KEY present → auto-point at OpenRouter, unless the
        # user already set a custom base_url via configure().
        return openrouter_key, config.base_url or _OPENROUTER_BASE_URL

    typesafe_key = os.getenv("TYPESAFE_API_KEY")
    if typesafe_key:
        return typesafe_key, config.base_url

    raise ConfigurationError(
        "No API key found. "
        "Set OPENROUTER_API_KEY (for OpenRouter) or TYPESAFE_API_KEY (for TypeSafe), "
        "or pass api_key=... to configure()."
    )


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------

def jev(query: str, context: str | None = None, *, ctx: str | None = None) -> float:
    """Score how strongly a natural-language predicate applies to the context.

    Uses TypeSafe's Jev model via the official SDK. Jev returns a calibrated
    noul probability — no prompt engineering or response parsing needed.

    Args:
        query:   Yes/no question or predicate to evaluate.
        context: Optional text (the "state") to evaluate the predicate against.
        ctx:     Alias for ``context``. Cannot be used together with context=.

    Returns:
        A calibrated probability in [0.0, 1.0].
    """
    query, resolved_context = _resolve(query, context, ctx)
    config = get_config()
    cache_key = make_key(config.model, query, resolved_context)

    if config.cache_enabled:
        cached = get_cached(cache_key)
        if cached is not None:
            return cached

    api_key, base_url = _resolve_backend(config)

    extra = {"base_url": base_url} if base_url else {}
    try:
        with TypeSafeClient(
            api_key=api_key,
            timeout=config.timeout,
            **extra,
        ) as client:
            response = client.system_one(
                model=config.model,
                state=resolved_context or "",
                questions={"q": Noul(instructions=query)},
            )
    except Exception as exc:
        raise ProviderError(f"TypeSafe SDK error: {type(exc).__name__}: {exc}") from exc

    try:
        score = float(response.nouls["q"].noul)
    except (KeyError, AttributeError, TypeError, ValueError) as exc:
        raise ParseError(f"Unexpected response shape from SDK: {exc}") from exc

    if config.cache_enabled:
        set_cached(cache_key, score, config.cache_ttl)
    return score


# ---------------------------------------------------------------------------
# Async
# ---------------------------------------------------------------------------

async def ajev(query: str, context: str | None = None, *, ctx: str | None = None) -> float:
    """Async version of ``jev``.

    Uses ``AsyncTypeSafeClient`` — safe to call directly on an event loop
    without a thread pool.

    Args:
        query:   Yes/no question or predicate to evaluate.
        context: Optional text (the "state") to evaluate the predicate against.
        ctx:     Alias for ``context``. Cannot be used together with context=.

    Returns:
        A calibrated probability in [0.0, 1.0].
    """
    query, resolved_context = _resolve(query, context, ctx)
    config = get_config()
    cache_key = make_key(config.model, query, resolved_context)

    if config.cache_enabled:
        cached = get_cached(cache_key)
        if cached is not None:
            return cached

    api_key, base_url = _resolve_backend(config)

    extra = {"base_url": base_url} if base_url else {}
    try:
        async with AsyncTypeSafeClient(
            api_key=api_key,
            timeout=config.timeout,
            **extra,
        ) as client:
            response = await client.system_one(
                model=config.model,
                state=resolved_context or "",
                questions={"q": Noul(instructions=query)},
            )
    except Exception as exc:
        raise ProviderError(f"TypeSafe SDK error: {type(exc).__name__}: {exc}") from exc

    try:
        score = float(response.nouls["q"].noul)
    except (KeyError, AttributeError, TypeError, ValueError) as exc:
        raise ParseError(f"Unexpected response shape from SDK: {exc}") from exc

    if config.cache_enabled:
        set_cached(cache_key, score, config.cache_ttl)
    return score


# Attach the elegant ``jev.context(...)`` / ``ajev.context(...)`` form.
jev.context = context   # type: ignore[attr-defined]
ajev.context = context  # type: ignore[attr-defined]
